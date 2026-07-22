import os
import sys
from urllib.parse import urlparse
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import pandas as pd
from config.page_filters import BUSINESS_PAGES, get_product_by_url
from src.transforms.traffic import classify_keyword


def _fmt_date(iso_date: str) -> str:
    """Конвертує '2026-07-06' → '06.07.2026'."""
    return datetime.strptime(iso_date, "%Y-%m-%d").strftime("%d.%m.%Y")


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
                "dimensions": ["date", "query", "page"],
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
        pages_with_traffic = set()

        for page_prefix in BUSINESS_PAGES:
            rows = self._query(start_date, end_date, page_prefix, row_limit=50)
            for row in rows:
                date_val = row["keys"][0]
                query = row["keys"][1]
                page = row["keys"][2]
                page_path = urlparse(page).path

                key = (date_val, query, page_path)
                if key not in seen:
                    seen.add(key)
                    pages_with_traffic.add((date_val, page_path))

                    product, sub_product = get_product_by_url(page_path)
                    all_rows.append({
                        "date": _fmt_date(date_val),
                        "query": query,
                        "page": page_path,
                        "clicks": row.get("clicks", 0),
                        "impressions": row.get("impressions", 0),
                        "ctr": round(row.get("ctr", 0) * 100, 2),
                        "position": round(row.get("position", 0), 1),
                        "keyword_type": classify_keyword(query),
                        "product": product,
                        "sub_product": sub_product,
                    })

        # zero-fill: сторінки без трафіку за весь діапазон
        for page_prefix in BUSINESS_PAGES:
            matched = any(p == page_prefix or p.startswith(page_prefix + "/")
                          for _, p in pages_with_traffic)
            if not matched:
                product, sub_product = get_product_by_url(page_prefix)
                all_rows.append({
                    "date": _fmt_date(end_date),
                    "query": "",
                    "page": page_prefix,
                    "clicks": 0,
                    "impressions": 0,
                    "ctr": 0.0,
                    "position": 0.0,
                    "keyword_type": "",
                    "product": product,
                    "sub_product": sub_product,
                })

        cols = ["date", "query", "page", "clicks", "impressions", "ctr", "position",
                "keyword_type", "product", "sub_product"]

        if not all_rows:
            return pd.DataFrame(columns=cols)

        df = pd.DataFrame(all_rows, columns=cols)
        df_real = df[df["query"] != ""].sort_values(["date", "clicks"], ascending=[True, False])
        df_zero = df[df["query"] == ""]
        return pd.concat([df_real, df_zero], ignore_index=True)
