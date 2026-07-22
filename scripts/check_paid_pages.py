"""Перевіряє куди реально йдуть Paid Search сесії в GA4."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv; load_dotenv()

from google.oauth2.credentials import Credentials
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, DateRange, Dimension, Metric,
    FilterExpression, Filter
)

SCOPES = ['https://www.googleapis.com/auth/analytics.readonly',
          'https://www.googleapis.com/auth/webmasters.readonly',
          'https://www.googleapis.com/auth/spreadsheets',
          'https://www.googleapis.com/auth/drive.file']

creds = Credentials.from_authorized_user_file('token.json', SCOPES)
client = BetaAnalyticsDataClient(credentials=creds)

req = RunReportRequest(
    property=f'properties/{os.environ["GA4_PROPERTY_ID"]}',
    dimensions=[Dimension(name='pagePath'), Dimension(name='sessionCampaignName')],
    metrics=[Metric(name='sessions')],
    date_ranges=[DateRange(start_date='2026-07-13', end_date='2026-07-19')],
    dimension_filter=FilterExpression(filter=Filter(
        field_name='sessionDefaultChannelGroup',
        string_filter=Filter.StringFilter(
            value='Paid Search',
            match_type=Filter.StringFilter.MatchType.EXACT
        )
    )),
    limit=30,
)
resp = client.run_report(req)
rows = sorted(resp.rows, key=lambda r: -int(r.metric_values[0].value))
print(f"{'page_path':<45} {'campaign':<40} sessions")
print('-'*95)
for r in rows:
    print(f"{r.dimension_values[0].value:<45} {r.dimension_values[1].value:<40} {r.metric_values[0].value}")
