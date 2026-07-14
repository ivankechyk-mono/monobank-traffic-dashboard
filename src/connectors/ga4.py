import os
import glob
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, DateRange, Dimension, Metric
)
import pandas as pd

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


class GA4Connector:
    def __init__(self, property_id: str, credentials: Credentials = None):
        self.property_id = property_id
        self.credentials = credentials or _get_credentials()
        self.client = BetaAnalyticsDataClient(credentials=self.credentials)

    def get_channel_traffic(self, date_range: tuple[str, str]) -> pd.DataFrame:
        start_date, end_date = date_range
        request = RunReportRequest(
            property=f"properties/{self.property_id}",
            dimensions=[Dimension(name="sessionDefaultChannelGroup")],
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
                "channel": row.dimension_values[0].value,
                "sessions": int(row.metric_values[0].value),
                "users": int(row.metric_values[1].value),
                "pageviews": int(row.metric_values[2].value),
            })

        df = pd.DataFrame(rows, columns=["channel", "sessions", "users", "pageviews"])
        if df.empty:
            return df

        total_sessions = df["sessions"].sum()
        df["pct_of_total"] = (
            (df["sessions"] / total_sessions * 100).round(2) if total_sessions > 0 else 0.0
        )
        return df.sort_values("sessions", ascending=False).reset_index(drop=True)

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

        return pd.DataFrame(
            rows, columns=["channel", "bounce_rate", "avg_session_duration", "pages_per_session"]
        )

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

        return pd.DataFrame(
            rows, columns=["page_path", "sessions", "pageviews"]
        ).sort_values("pageviews", ascending=False).reset_index(drop=True)
