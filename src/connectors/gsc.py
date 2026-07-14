import os
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import pandas as pd


class GSCConnector:
    def __init__(self, site_url: str, credentials: Credentials):
        self.site_url = site_url
        self.service = build("searchconsole", "v1", credentials=credentials)

    def get_keywords(self, date_range: tuple[str, str], row_limit: int = 100) -> pd.DataFrame:
        start_date, end_date = date_range
        result = self.service.searchanalytics().query(
            siteUrl=self.site_url,
            body={
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": ["query", "page"],
                "rowLimit": row_limit,
            },
        ).execute()

        rows = []
        for row in result.get("rows", []):
            rows.append({
                "query": row["keys"][0],
                "page": row["keys"][1],
                "clicks": row.get("clicks", 0),
                "impressions": row.get("impressions", 0),
                "ctr": round(row.get("ctr", 0) * 100, 2),
                "position": round(row.get("position", 0), 1),
            })

        return pd.DataFrame(
            rows, columns=["query", "page", "clicks", "impressions", "ctr", "position"]
        ).sort_values("clicks", ascending=False).reset_index(drop=True)
