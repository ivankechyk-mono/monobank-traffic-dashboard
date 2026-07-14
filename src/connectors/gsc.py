import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import pandas as pd
from config.page_filters import BUSINESS_PAGES


class GSCConnector:
    def __init__(self, site_url: str, credentials: Credentials):
        self.site_url = site_url
        self.service = build("searchconsole", "v1", credentials=credentials)

    def _query(self, start_date: str, end_date: str, page_prefix: str, row_limit: int) -> list:
        result = self.service.searchanalytics().query(
            siteUrl=self.site_url,
            body={
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": ["query", "page"],
                "dimensionFilterGroups": [{
                    "filters": [{
                        "dimension": "page",
                        "operator": "contains",
                        "expression": page_prefix,
                    }]
                }],
                "rowLimit": row_limit,
            },
        ).execute()
        return result.get("rows", [])

    def get_keywords(
        self,
        date_range: tuple[str, str],
        row_limit: int = 200,
    ) -> pd.DataFrame:
        start_date, end_date = date_range
        all_rows = []
        seen = set()

        for page_prefix in BUSINESS_PAGES:
            rows = self._query(start_date, end_date, page_prefix, row_limit=50)
            for row in rows:
                key = (row["keys"][0], row["keys"][1])
                if key not in seen:
                    seen.add(key)
                    all_rows.append({
                        "query": row["keys"][0],
                        "page": row["keys"][1],
                        "clicks": row.get("clicks", 0),
                        "impressions": row.get("impressions", 0),
                        "ctr": round(row.get("ctr", 0) * 100, 2),
                        "position": round(row.get("position", 0), 1),
                    })

        if not all_rows:
            return pd.DataFrame(columns=["query", "page", "clicks", "impressions", "ctr", "position"])

        return (
            pd.DataFrame(all_rows)
            .sort_values("clicks", ascending=False)
            .reset_index(drop=True)
        )
