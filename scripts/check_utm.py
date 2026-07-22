"""Quick UTM check — чи є utm_source/utm_medium в GA4 даних за останні 7 днів."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.oauth2.credentials import Credentials
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Dimension, Metric

SCOPES = [
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

creds = Credentials.from_authorized_user_file("token.json", SCOPES)
client = BetaAnalyticsDataClient(credentials=creds)
property_id = os.getenv("GA4_PROPERTY_ID", "394536299")

request = RunReportRequest(
    property=f"properties/{property_id}",
    dimensions=[
        Dimension(name="sessionDefaultChannelGroup"),
        Dimension(name="sessionSource"),
        Dimension(name="sessionMedium"),
        Dimension(name="sessionCampaignName"),
    ],
    metrics=[Metric(name="sessions")],
    date_ranges=[DateRange(start_date="7daysAgo", end_date="yesterday")],
    limit=50,
)

response = client.run_report(request)

print(f"{'channel':<25} {'source':<20} {'medium':<20} {'campaign':<30} {'sessions'}")
print("-" * 120)
rows = sorted(response.rows, key=lambda r: -int(r.metric_values[0].value))
for row in rows:
    channel  = row.dimension_values[0].value
    source   = row.dimension_values[1].value
    medium   = row.dimension_values[2].value
    campaign = row.dimension_values[3].value
    sessions = row.metric_values[0].value
    print(f"{channel:<25} {source:<20} {medium:<20} {campaign:<30} {sessions}")
