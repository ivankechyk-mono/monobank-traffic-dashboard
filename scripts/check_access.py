"""
Тестовий скрипт — перевіряє доступи до GA4 і GSC.
Запуск: python3.11 scripts/check_access.py
"""
import os
import glob
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Dimension, Metric

SCOPES = [
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/webmasters.readonly",
]

GA4_PROPERTY_ID = os.getenv("GA4_PROPERTY_ID", "")
GSC_SITE_URL = os.getenv("GSC_SITE_URL", "https://monobank.ua/")


def get_credentials():
    token_path = "token.json"
    creds = None

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        secret_files = glob.glob("client_secret*.json")
        if not secret_files:
            raise FileNotFoundError("client_secret*.json не знайдено в поточній директорії")
        flow = InstalledAppFlow.from_client_secrets_file(secret_files[0], SCOPES)
        creds = flow.run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())
        print("Токен збережено у token.json")

    return creds


def check_ga4(creds):
    print("\n--- GA4 ---")
    if not GA4_PROPERTY_ID:
        print("ПРОПУЩЕНО: встанови GA4_PROPERTY_ID у .env або передай через env")
        return

    client = BetaAnalyticsDataClient(credentials=creds)
    request = RunReportRequest(
        property=f"properties/{GA4_PROPERTY_ID}",
        dimensions=[Dimension(name="sessionDefaultChannelGroup")],
        metrics=[Metric(name="sessions")],
        date_ranges=[DateRange(start_date="7daysAgo", end_date="yesterday")],
        dimension_filter={
            "filter": {
                "field_name": "pagePath",
                "string_filter": {"match_type": "BEGINS_WITH", "value": "/business/"},
            }
        },
        limit=5,
    )
    response = client.run_report(request)
    print(f"OK — отримано {len(response.rows)} рядків (топ-5 каналів за 7 днів):")
    for row in response.rows:
        channel = row.dimension_values[0].value
        sessions = row.metric_values[0].value
        print(f"  {channel}: {sessions} сесій")


def check_gsc(creds):
    print("\n--- Google Search Console ---")
    service = build("searchconsole", "v1", credentials=creds)
    result = service.searchanalytics().query(
        siteUrl=GSC_SITE_URL,
        body={
            "startDate": "2025-07-07",
            "endDate": "2025-07-13",
            "dimensions": ["query"],
            "dimensionFilterGroups": [{
                "filters": [{
                    "dimension": "page",
                    "operator": "contains",
                    "expression": "/business/",
                }]
            }],
            "rowLimit": 5,
        },
    ).execute()
    rows = result.get("rows", [])
    print(f"OK — отримано {len(rows)} ключових слів (топ-5 за 7 днів):")
    for row in rows:
        print(f"  {row['keys'][0]}: {row.get('clicks', 0)} кліків")


if __name__ == "__main__":
    print("Отримую OAuth токен (відкриється браузер)...")
    creds = get_credentials()
    print("Авторизація успішна.")

    check_ga4(creds)
    check_gsc(creds)

    print("\nГотово. Якщо бачиш дані вище — доступи працюють.")
