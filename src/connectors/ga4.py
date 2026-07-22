import os
import glob
import sys
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, DateRange, Dimension, Metric, FilterExpression, Filter
)
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.page_filters import get_product_by_url

SCOPES = [
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]


def _get_credentials(token_path: str = "token.json") -> Credentials:
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        secret_files = glob.glob("client_secret*.json")
        if not secret_files:
            raise FileNotFoundError("client_secret*.json не знайдено")
        flow = InstalledAppFlow.from_client_secrets_file(secret_files[0], SCOPES)
        creds = flow.run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())
    return creds


def _fmt_date(ga4_date: str) -> str:
    """Конвертує GA4 формат '20260706' → '06.07.2026'."""
    from datetime import datetime
    return datetime.strptime(ga4_date, "%Y%m%d").strftime("%d.%m.%Y")


class GA4Connector:
    def __init__(self, property_id: str, credentials: Credentials = None):
        self.property_id = property_id
        self.credentials = credentials or _get_credentials()
        self.client = BetaAnalyticsDataClient(credentials=self.credentials)

    def get_channel_traffic(self, date_range: tuple[str, str]) -> pd.DataFrame:
        start_date, end_date = date_range
        request = RunReportRequest(
            property=f"properties/{self.property_id}",
            dimensions=[
                Dimension(name="date"),
                Dimension(name="sessionDefaultChannelGroup"),
            ],
            metrics=[
                Metric(name="sessions"),
                Metric(name="totalUsers"),
                Metric(name="screenPageViews"),
            ],
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        )
        response = self.client.run_report(request)

        rows = []
        for row in response.rows:
            rows.append({
                "date": _fmt_date(row.dimension_values[0].value),
                "channel": row.dimension_values[1].value,
                "sessions": int(row.metric_values[0].value),
                "users": int(row.metric_values[1].value),
                "pageviews": int(row.metric_values[2].value),
            })

        df = pd.DataFrame(rows, columns=["date", "channel", "sessions", "users", "pageviews"])
        if df.empty:
            return df

        # pct_of_total рахуємо в межах кожного дня
        daily_totals = df.groupby("date")["sessions"].transform("sum")
        df["pct_of_total"] = (df["sessions"] / daily_totals * 100).round(2)

        return df.sort_values(["date", "sessions"], ascending=[True, False]).reset_index(drop=True)

    def get_engagement_full(self, date_range: tuple[str, str], limit: int = 10000) -> pd.DataFrame:
        """Сторінка × канал × джерело × день. Тільки бізнес-сторінки."""
        start_date, end_date = date_range
        request = RunReportRequest(
            property=f"properties/{self.property_id}",
            dimensions=[
                Dimension(name="date"),
                Dimension(name="pagePath"),
                Dimension(name="sessionDefaultChannelGroup"),
                Dimension(name="sessionSource"),
                Dimension(name="sessionMedium"),
                Dimension(name="sessionCampaignName"),
            ],
            metrics=[
                Metric(name="sessions"),
                Metric(name="totalUsers"),
                Metric(name="screenPageViews"),
                Metric(name="bounceRate"),
                Metric(name="averageSessionDuration"),
                Metric(name="screenPageViewsPerSession"),
            ],
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            limit=limit,
        )
        response = self.client.run_report(request)

        rows = []
        for row in response.rows:
            page_path = row.dimension_values[1].value
            product, sub_product = get_product_by_url(page_path)
            if product == "Unknown":
                continue
            rows.append({
                "date": _fmt_date(row.dimension_values[0].value),
                "page_path": page_path,
                "channel": row.dimension_values[2].value,
                "source": row.dimension_values[3].value,
                "medium": row.dimension_values[4].value,
                "campaign": row.dimension_values[5].value,
                "product": product,
                "sub_product": sub_product,
                "sessions": int(row.metric_values[0].value),
                "users": int(row.metric_values[1].value),
                "pageviews": int(row.metric_values[2].value),
                "bounce_rate": round(float(row.metric_values[3].value) * 100, 2),
                "avg_session_duration": round(float(row.metric_values[4].value), 1),
                "pages_per_session": round(float(row.metric_values[5].value), 2),
            })

        cols = ["date", "page_path", "channel", "source", "medium", "campaign",
                "product", "sub_product", "sessions", "users", "pageviews",
                "bounce_rate", "avg_session_duration", "pages_per_session"]
        if not rows:
            return pd.DataFrame(columns=cols)

        return (
            pd.DataFrame(rows, columns=cols)
            .sort_values(["date", "sessions"], ascending=[True, False])
            .reset_index(drop=True)
        )

    def get_product_events(self, date_range: tuple[str, str]) -> pd.DataFrame:
        """
        Тягне продуктову активність через GA4 custom events.
        Потрібно бо SPA-додаток не генерує page_view для більшості продуктів —
        ЮО, ЗП-проект, МСА/Аванс живуть всередині /mono-business і видні тільки через events.

        Повертає: date, product, channel, users, event_count, event_name
        """
        # event → продукт. Беремо найрелевантніший event що означає "юзер бачив продукт"
        EVENT_PRODUCT_MAP = {
            "business_fop_page_view":           "ФОП",
            "business_legal_entity_page_view":  "ЮО",
            "business_salary_shown":            "ЗП-проект",
            "business_mca_banner_shown":        "Аванс",
        }

        start_date, end_date = date_range
        rows = []

        for event_name, product in EVENT_PRODUCT_MAP.items():
            request = RunReportRequest(
                property=f"properties/{self.property_id}",
                dimensions=[
                    Dimension(name="date"),
                    Dimension(name="sessionDefaultChannelGroup"),
                ],
                metrics=[
                    Metric(name="eventCount"),
                    Metric(name="totalUsers"),
                ],
                date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
                dimension_filter=FilterExpression(
                    filter=Filter(
                        field_name="eventName",
                        string_filter=Filter.StringFilter(
                            value=event_name,
                            match_type=Filter.StringFilter.MatchType.EXACT,
                        ),
                    )
                ),
                limit=500,
            )
            response = self.client.run_report(request)
            for row in response.rows:
                rows.append({
                    "date": _fmt_date(row.dimension_values[0].value),
                    "channel": row.dimension_values[1].value,
                    "product": product,
                    "event_name": event_name,
                    "event_count": int(row.metric_values[0].value),
                    "users": int(row.metric_values[1].value),
                })

        cols = ["date", "product", "event_name", "channel", "users", "event_count"]
        if not rows:
            return pd.DataFrame(columns=cols)

        return (
            pd.DataFrame(rows, columns=cols)
            .sort_values(["date", "product", "event_count"], ascending=[True, True, False])
            .reset_index(drop=True)
        )

    # Залишаємо старі методи для зворотної сумісності з тестами
    def get_engagement_metrics(self, date_range: tuple[str, str]) -> pd.DataFrame:
        start_date, end_date = date_range
        request = RunReportRequest(
            property=f"properties/{self.property_id}",
            dimensions=[Dimension(name="sessionDefaultChannelGroup")],
            metrics=[
                Metric(name="bounceRate"),
                Metric(name="averageSessionDuration"),
                Metric(name="screenPageViewsPerSession"),
            ],
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
        )
        response = self.client.run_report(request)
        rows = []
        for row in response.rows:
            rows.append({
                "channel": row.dimension_values[0].value,
                "bounce_rate": round(float(row.metric_values[0].value) * 100, 2),
                "avg_session_duration": round(float(row.metric_values[1].value), 1),
                "pages_per_session": round(float(row.metric_values[2].value), 2),
            })
        return pd.DataFrame(rows, columns=["channel", "bounce_rate", "avg_session_duration", "pages_per_session"])

    def get_page_paths(self, date_range: tuple[str, str], limit: int = 50) -> pd.DataFrame:
        start_date, end_date = date_range
        request = RunReportRequest(
            property=f"properties/{self.property_id}",
            dimensions=[Dimension(name="pagePath")],
            metrics=[
                Metric(name="sessions"),
                Metric(name="screenPageViews"),
            ],
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            limit=limit,
        )
        response = self.client.run_report(request)
        rows = []
        for row in response.rows:
            rows.append({
                "page_path": row.dimension_values[0].value,
                "sessions": int(row.metric_values[0].value),
                "pageviews": int(row.metric_values[1].value),
            })
        return pd.DataFrame(rows, columns=["page_path", "sessions", "pageviews"]).sort_values("pageviews", ascending=False).reset_index(drop=True)
