import os
import sys
from datetime import datetime
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.page_filters import BRANDED_KEYWORDS


def _fmt_date(iso_date: str) -> str:
    """Конвертує '2026-07-06' → '06.07.2026'."""
    return datetime.strptime(iso_date, "%Y-%m-%d").strftime("%d.%m.%Y")


def _classify_keyword(keyword: str) -> str:
    kw = keyword.lower()
    for branded in BRANDED_KEYWORDS:
        if branded in kw:
            return "branded"
    return "non-branded"


def _build_client() -> GoogleAdsClient:
    return GoogleAdsClient.load_from_dict({
        "developer_token": os.environ["GOOGLE_ADS_TOKEN"],
        "client_id": os.environ["GOOGLE_ADS_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_ADS_CLIENT_SECRET"],
        "refresh_token": os.environ["GOOGLE_ADS_REFRESH_TOKEN"],
        "use_proto_plus": True,
    })


class GoogleAdsConnector:
    def __init__(self, customer_id: str = None, client: GoogleAdsClient = None):
        self.customer_id = customer_id or os.environ["GOOGLE_ADS_CUSTOMER_ID"]
        self.client = client or _build_client()

    def _get_ad_group_urls(self) -> dict[str, str]:
        """
        Повертає {ad_group_name: landing_url_path} з першого активного оголошення в кожній групі.
        Береться з ad_group_ad — єдиний ресурс де є final_urls на рівні оголошення.
        """
        from urllib.parse import urlparse
        ga_service = self.client.get_service("GoogleAdsService")
        query = """
            SELECT
                ad_group.name,
                ad_group_ad.ad.final_urls
            FROM ad_group_ad
            WHERE ad_group_ad.status = 'ENABLED'
              AND campaign.status = 'ENABLED'
              AND ad_group.status = 'ENABLED'
        """
        result = {}
        try:
            response = ga_service.search(customer_id=self.customer_id, query=query)
            for row in response:
                ag_name = row.ad_group.name
                if ag_name in result:
                    continue
                urls = row.ad_group_ad.ad.final_urls
                if urls:
                    path = urlparse(urls[0]).path or urls[0]
                    result[ag_name] = path
        except GoogleAdsException:
            pass  # якщо не вдалось — повертаємо порожній dict, landing_url буде ""
        return result

    def get_keywords_performance(self, date_range: tuple[str, str]) -> pd.DataFrame:
        """
        Щоденна статистика по ключових словах.
        date_range: ('YYYY-MM-DD', 'YYYY-MM-DD')
        Повертає DataFrame(date, keyword, match_type, campaign, ad_group,
                           clicks, impressions, cost_uah, keyword_type, landing_url)
        """
        start_date, end_date = date_range
        ga_service = self.client.get_service("GoogleAdsService")

        # спочатку отримуємо landing_url по ad_group
        ad_group_urls = self._get_ad_group_urls()

        query = f"""
            SELECT
                segments.date,
                ad_group_criterion.keyword.text,
                ad_group_criterion.keyword.match_type,
                ad_group_criterion.final_urls,
                campaign.name,
                ad_group.name,
                metrics.clicks,
                metrics.impressions,
                metrics.cost_micros
            FROM keyword_view
            WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
              AND campaign.status = 'ENABLED'
              AND ad_group.status = 'ENABLED'
              AND ad_group_criterion.status = 'ENABLED'
              AND metrics.impressions > 0
            ORDER BY segments.date DESC, metrics.clicks DESC
        """

        rows = []
        try:
            response = ga_service.search(customer_id=self.customer_id, query=query)
            for row in response:
                keyword = row.ad_group_criterion.keyword.text
                match_type = row.ad_group_criterion.keyword.match_type.name
                ad_group_name = row.ad_group.name

                # keyword-level final_url має пріоритет, fallback → ad_group url
                kw_urls = row.ad_group_criterion.final_urls
                if kw_urls:
                    from urllib.parse import urlparse
                    landing_url = urlparse(kw_urls[0]).path or kw_urls[0]
                else:
                    landing_url = ad_group_urls.get(ad_group_name, "")

                rows.append({
                    "date": _fmt_date(row.segments.date),
                    "keyword": keyword,
                    "match_type": match_type,
                    "campaign": row.campaign.name,
                    "ad_group": ad_group_name,
                    "landing_url": landing_url,
                    "clicks": row.metrics.clicks,
                    "impressions": row.metrics.impressions,
                    "cost_uah": round(row.metrics.cost_micros / 1_000_000, 2),
                    "keyword_type": _classify_keyword(keyword),
                })
        except GoogleAdsException as e:
            for error in e.failure.errors:
                raise RuntimeError(f"Google Ads API error: {error.message}") from e

        cols = ["date", "keyword", "match_type", "campaign", "ad_group", "landing_url",
                "clicks", "impressions", "cost_uah", "keyword_type"]
        if not rows:
            return pd.DataFrame(columns=cols)

        return (
            pd.DataFrame(rows, columns=cols)
            .sort_values(["date", "clicks"], ascending=[True, False])
            .reset_index(drop=True)
        )

    def get_campaigns(self, date_range: tuple[str, str]) -> pd.DataFrame:
        """
        Щоденна статистика по кампаніях (агрегована).
        Повертає DataFrame(date, campaign, clicks, impressions, cost_uah)
        """
        start_date, end_date = date_range
        ga_service = self.client.get_service("GoogleAdsService")

        query = f"""
            SELECT
                segments.date,
                campaign.name,
                campaign.advertising_channel_type,
                metrics.clicks,
                metrics.impressions,
                metrics.cost_micros
            FROM campaign
            WHERE segments.date BETWEEN '{start_date}' AND '{end_date}'
              AND campaign.status = 'ENABLED'
              AND metrics.impressions > 0
            ORDER BY segments.date DESC, metrics.clicks DESC
        """

        rows = []
        try:
            response = ga_service.search(customer_id=self.customer_id, query=query)
            for row in response:
                rows.append({
                    "date": _fmt_date(row.segments.date),
                    "campaign": row.campaign.name,
                    "channel_type": row.campaign.advertising_channel_type.name,
                    "clicks": row.metrics.clicks,
                    "impressions": row.metrics.impressions,
                    "cost_uah": round(row.metrics.cost_micros / 1_000_000, 2),
                })
        except GoogleAdsException as e:
            for error in e.failure.errors:
                raise RuntimeError(f"Google Ads API error: {error.message}") from e

        cols = ["date", "campaign", "channel_type", "clicks", "impressions", "cost_uah"]
        if not rows:
            return pd.DataFrame(columns=cols)

        return (
            pd.DataFrame(rows, columns=cols)
            .sort_values(["date", "clicks"], ascending=[True, False])
            .reset_index(drop=True)
        )
