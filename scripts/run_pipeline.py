"""
Оркестратор pipeline. Запуск: python3.11 scripts/run_pipeline.py
"""
import os
import sys
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.connectors.ga4 import GA4Connector, _get_credentials
from src.transforms.traffic import normalize_channels, add_week_start
from src.loaders.sheets import upsert_weekly_snapshot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


def get_week_start() -> str:
    today = datetime.today()
    monday = today - timedelta(days=today.weekday() + 7)
    return monday.strftime("%Y-%m-%d")


def run():
    property_id = os.getenv("GA4_PROPERTY_ID")
    sheet_id = os.getenv("GOOGLE_SHEETS_ID")

    if not property_id:
        raise ValueError("GA4_PROPERTY_ID не встановлено")
    if not sheet_id:
        raise ValueError("GOOGLE_SHEETS_ID не встановлено")

    week_start = get_week_start()
    week_end = (datetime.strptime(week_start, "%Y-%m-%d") + timedelta(days=6)).strftime("%Y-%m-%d")

    log.info(f"Запуск pipeline за тиждень {week_start} → {week_end}")

    creds = _get_credentials()

    log.info("GA4: отримую трафік по каналах...")
    connector = GA4Connector(property_id=property_id, credentials=creds)
    df = connector.get_channel_traffic(date_range=(week_start, week_end))
    df = normalize_channels(df)
    df = add_week_start(df, week_start)
    upsert_weekly_snapshot(df, tab_name="traffic_by_channel", credentials=creds, sheet_id=sheet_id)
    log.info(f"GA4 трафік: записано {len(df)} рядків")

    log.info("GA4: отримую engagement метрики...")
    df_eng = connector.get_engagement_metrics(date_range=(week_start, week_end))
    df_eng = add_week_start(df_eng, week_start)
    upsert_weekly_snapshot(df_eng, tab_name="engagement", credentials=creds, sheet_id=sheet_id)
    log.info(f"GA4 engagement: записано {len(df_eng)} рядків")

    log.info("GA4: отримую топ сторінок...")
    df_pages = connector.get_page_paths(date_range=(week_start, week_end))
    df_pages = add_week_start(df_pages, week_start)
    upsert_weekly_snapshot(df_pages, tab_name="engagement", credentials=creds, sheet_id=sheet_id)
    log.info(f"GA4 сторінки: записано {len(df_pages)} рядків")

    log.info("Pipeline завершено успішно.")


if __name__ == "__main__":
    run()
