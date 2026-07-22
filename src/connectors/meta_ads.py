import os
import requests
from datetime import datetime
import pandas as pd


def _fmt_date(iso_date: str) -> str:
    """Конвертує '2026-07-06' → '06.07.2026'."""
    return datetime.strptime(iso_date, "%Y-%m-%d").strftime("%d.%m.%Y")


class MetaAdsConnector:
    BASE_URL = "https://graph.facebook.com/v20.0"

    def __init__(self, access_token: str, ad_account_id: str):
        self.token = access_token
        self.ad_account_id = ad_account_id

    def get_campaigns(self, date_range: tuple[str, str]) -> pd.DataFrame:
        """
        Повертає щоденну статистику по кампаніях за вказаний діапазон дат.
        date_range: (YYYY-MM-DD, YYYY-MM-DD)
        """
        start_date, end_date = date_range
        rows = []
        url = f"{self.BASE_URL}/{self.ad_account_id}/insights"
        params = {
            "access_token": self.token,
            "fields": "campaign_name,impressions,clicks,spend",
            "time_range": f'{{"since":"{start_date}","until":"{end_date}"}}',
            "level": "campaign",
            "time_increment": 1,
            "limit": 500,
        }

        while True:
            resp = requests.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            if "error" in data:
                raise RuntimeError(f"Meta API error: {data['error']['message']}")

            for row in data.get("data", []):
                rows.append({
                    "date": _fmt_date(row["date_start"]),
                    "campaign_name": row.get("campaign_name", ""),
                    "impressions": int(row.get("impressions", 0)),
                    "clicks": int(row.get("clicks", 0)),
                    "spend": round(float(row.get("spend", 0)), 2),
                })

            # пагінація
            next_url = data.get("paging", {}).get("next")
            if not next_url:
                break
            url = next_url
            params = {}

        cols = ["date", "campaign_name", "impressions", "clicks", "spend"]
        if not rows:
            return pd.DataFrame(columns=cols)

        return (
            pd.DataFrame(rows, columns=cols)
            .sort_values(["date", "spend"], ascending=[True, False])
            .reset_index(drop=True)
        )
