"""
Прямой запрос к GA4: проверяем соотношение users vs sessions.
Запрашиваем totalUsers, activeUsers, sessions за одну неделю
чтобы понять какая метрика корректна.
"""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()

from src.connectors.ga4 import _get_credentials
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    RunReportRequest, DateRange, Dimension, Metric, FilterExpression,
    Filter, FilterExpressionList
)

PROPERTY_ID = os.getenv("GA4_PROPERTY_ID")
creds = _get_credentials()
client = BetaAnalyticsDataClient(credentials=creds)

# Страницы Еквайринг (самый показательный случай: 739 sessions / 6891 users)
ACQUIRING_PAGES = ["/acquiring", "/plata-by-mono", "/pos", "/terminal"]
page_filter = FilterExpression(
    or_group=FilterExpressionList(
        expressions=[
            FilterExpression(filter=Filter(
                field_name="pagePath",
                string_filter=Filter.StringFilter(
                    value=p,
                    match_type=Filter.StringFilter.MatchType.BEGINS_WITH
                )
            )) for p in ACQUIRING_PAGES
        ]
    )
)

req = RunReportRequest(
    property=f"properties/{PROPERTY_ID}",
    date_ranges=[DateRange(start_date="2026-07-07", end_date="2026-07-13")],  # тиждень
    dimensions=[Dimension(name="sessionDefaultChannelGroup")],
    metrics=[
        Metric(name="sessions"),
        Metric(name="totalUsers"),
        Metric(name="activeUsers"),
    ],
    dimension_filter=page_filter,
)

resp = client.run_report(req)

print("=== Еквайринг: sessions vs totalUsers vs activeUsers (07–13.07.2026) ===")
print(f"{'Канал':<25} {'sessions':>10} {'totalUsers':>12} {'activeUsers':>13}")
print("-" * 65)
for row in resp.rows:
    ch = row.dimension_values[0].value
    s  = row.metric_values[0].value
    tu = row.metric_values[1].value
    au = row.metric_values[2].value
    print(f"{ch:<25} {s:>10} {tu:>12} {au:>13}")

print()

# То же самое для ФОП
FOP_PAGES = ["/fop", "/business/fop"]
page_filter_fop = FilterExpression(
    or_group=FilterExpressionList(
        expressions=[
            FilterExpression(filter=Filter(
                field_name="pagePath",
                string_filter=Filter.StringFilter(
                    value=p,
                    match_type=Filter.StringFilter.MatchType.BEGINS_WITH
                )
            )) for p in FOP_PAGES
        ]
    )
)

req2 = RunReportRequest(
    property=f"properties/{PROPERTY_ID}",
    date_ranges=[DateRange(start_date="2026-07-07", end_date="2026-07-13")],
    dimensions=[Dimension(name="sessionDefaultChannelGroup")],
    metrics=[
        Metric(name="sessions"),
        Metric(name="totalUsers"),
        Metric(name="activeUsers"),
    ],
    dimension_filter=page_filter_fop,
)

resp2 = client.run_report(req2)

print("=== ФОП: sessions vs totalUsers vs activeUsers (07–13.07.2026) ===")
print(f"{'Канал':<25} {'sessions':>10} {'totalUsers':>12} {'activeUsers':>13}")
print("-" * 65)
for row in resp2.rows:
    ch = row.dimension_values[0].value
    s  = row.metric_values[0].value
    tu = row.metric_values[1].value
    au = row.metric_values[2].value
    print(f"{ch:<25} {s:>10} {tu:>12} {au:>13}")
