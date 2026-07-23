"""
Завантажує дані за N попередніх тижнів у Google Sheets.
Використання: python3.11 scripts/backfill.py --weeks 12
"""
import os, sys, logging, argparse
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pandas as pd

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.connectors.ga4 import GA4Connector, _get_credentials
from src.connectors.gsc import GSCConnector
from src.connectors.meta_ads import MetaAdsConnector
from src.connectors.google_ads import GoogleAdsConnector
from src.transforms.traffic import (
    build_traffic_by_channel, aggregate_gsc_keywords,
    aggregate_ads_keywords, aggregate_engagement, aggregate_meta_ads,
    aggregate_conversions,
)
from src.transforms.product_matrix import build_product_matrix
from src.loaders.sheets import upsert_weekly_snapshot

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def week_ranges(n_weeks: int) -> list[tuple[str, str, str, str]]:
    """Повертає список (api_start, api_end, display_start, display_end) за останні n тижнів."""
    today = datetime.today()
    # останній завершений тиждень — попередній пн
    last_monday = today - timedelta(days=today.weekday() + 7)
    weeks = []
    for i in range(n_weeks):
        monday = last_monday - timedelta(weeks=i)
        sunday = monday + timedelta(days=6)
        weeks.append((
            monday.strftime("%Y-%m-%d"),
            sunday.strftime("%Y-%m-%d"),
            monday.strftime("%d.%m.%Y"),
            sunday.strftime("%d.%m.%Y"),
        ))
    return weeks  # від новіших до старіших


def _snap(df, tab, creds, sheet_id, disp_start, disp_end):
    upsert_weekly_snapshot(
        df, tab_name=tab, date_col="week_start",
        week_start=disp_start, week_end=disp_end,
        credentials=creds, sheet_id=sheet_id,
    )


def run_week(connector, gsc, meta, ads, sheet_id, creds, week):
    api_start, api_end, disp_start, disp_end = week
    log.info(f"  Тиждень {disp_start} → {disp_end}")

    df_channel = connector.get_channel_traffic(date_range=(api_start, api_end))
    df_eng = connector.get_engagement_full(date_range=(api_start, api_end))
    df_events = connector.get_product_events(date_range=(api_start, api_end))

    df_conv_raw = connector.get_conversions(date_range=(api_start, api_end))
    df_conv = aggregate_conversions(df_conv_raw, disp_start)
    _snap(df_conv, "conversions", creds, sheet_id, disp_start, disp_end)

    df_traffic = build_traffic_by_channel(df_channel, df_eng, disp_start, df_events)
    _snap(df_traffic, "traffic_by_channel", creds, sheet_id, disp_start, disp_end)

    df_eng_agg = aggregate_engagement(df_eng, disp_start, df_events)
    _snap(df_eng_agg, "engagement", creds, sheet_id, disp_start, disp_end)

    df_gsc_raw = gsc.get_keywords(date_range=(api_start, api_end))
    df_gsc = aggregate_gsc_keywords(df_gsc_raw, disp_start)
    _snap(df_gsc, "gsc_keywords", creds, sheet_id, disp_start, disp_end)

    df_meta = pd.DataFrame()
    df_meta_raw = pd.DataFrame()
    if meta and os.getenv("META_TOKEN"):
        df_meta_raw = meta.get_campaigns(date_range=(api_start, api_end))
        df_meta = aggregate_meta_ads(df_meta_raw, disp_start)
        _snap(df_meta, "meta_ads", creds, sheet_id, disp_start, disp_end)

    df_ads_kw = pd.DataFrame()
    df_ads_raw = pd.DataFrame()
    if ads:
        df_ads_raw = ads.get_keywords_performance(date_range=(api_start, api_end))
        df_ads_kw = aggregate_ads_keywords(df_ads_raw, disp_start)
        _snap(df_ads_kw, "ads_keywords", creds, sheet_id, disp_start, disp_end)

    df_matrix = build_product_matrix(
        df_engagement=df_eng,
        df_gsc=df_gsc_raw,
        df_ads=df_ads_kw,
        df_meta=df_meta if not df_meta.empty else df_meta_raw,
        week_start=disp_start,
    )
    _snap(df_matrix, "product_matrix", creds, sheet_id, disp_start, disp_end)

    log.info(f"  ✓ traffic={len(df_traffic)} gsc={len(df_gsc)} meta={len(df_meta)} ads={len(df_ads_kw)} matrix={len(df_matrix)}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--weeks", type=int, default=52, help="Кількість тижнів для backfill (default: 52 = 12 місяців)")
    parser.add_argument("--from-date", type=str, default=None, help="Дата початку у форматі YYYY-MM-DD (замість --weeks)")
    args = parser.parse_args()

    if args.from_date:
        from_dt = datetime.strptime(args.from_date, "%Y-%m-%d")
        today = datetime.today()
        last_monday = today - timedelta(days=today.weekday() + 7)
        delta_weeks = max(1, int((last_monday - from_dt).days / 7) + 1)
        args.weeks = delta_weeks
        log.info(f"--from-date {args.from_date} → {args.weeks} тижнів")

    property_id = os.getenv("GA4_PROPERTY_ID")
    sheet_id = os.getenv("GOOGLE_SHEETS_ID")
    if not property_id or not sheet_id:
        raise ValueError("Потрібні GA4_PROPERTY_ID і GOOGLE_SHEETS_ID")

    # Гарантуємо що loader не видалить дані старші за WEEKS_TO_KEEP
    os.environ.setdefault("WEEKS_TO_KEEP", str(args.weeks + 4))

    creds = _get_credentials()
    connector = GA4Connector(property_id=property_id, credentials=creds)
    gsc = GSCConnector(site_url=os.getenv("GSC_SITE_URL", "https://monobank.ua/"), credentials=creds)

    meta = None
    if os.getenv("META_TOKEN"):
        meta = MetaAdsConnector(
            access_token=os.getenv("META_TOKEN"),
            ad_account_id=os.getenv("META_AD_ACCOUNT_ID", "act_455699156062655"),
        )

    ads = None
    if os.getenv("GOOGLE_ADS_CUSTOMER_ID") and os.getenv("GOOGLE_ADS_TOKEN"):
        ads = GoogleAdsConnector(customer_id=os.getenv("GOOGLE_ADS_CUSTOMER_ID"))

    weeks = week_ranges(args.weeks)
    log.info(f"Backfill: {args.weeks} тижнів, від {weeks[-1][2]} до {weeks[0][2]}")

    for week in reversed(weeks):  # від старіших до новіших
        try:
            run_week(connector, gsc, meta, ads, sheet_id, creds, week)
        except Exception as e:
            log.error(f"  ✗ Помилка за тиждень {week[2]}: {e}")
            continue

    log.info("Backfill завершено.")


if __name__ == "__main__":
    main()
