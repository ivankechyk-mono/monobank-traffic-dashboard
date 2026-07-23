"""
Оркестратор pipeline. Запуск: python3.11 scripts/run_pipeline.py
"""
import os
import sys
import logging
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
    build_traffic_by_channel,
    aggregate_gsc_keywords,
    aggregate_ads_keywords,
    aggregate_engagement,
    aggregate_meta_ads,
    aggregate_conversions,
)
from src.transforms.product_matrix import build_product_matrix
from src.loaders.sheets import upsert_weekly_snapshot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)


def get_week_range() -> tuple[str, str, str, str]:
    """
    Повертає (api_start, api_end, display_start, display_end) для попереднього повного тижня пн–нд.
    api: YYYY-MM-DD для Google API
    display: DD.MM.YYYY для Google Sheets
    """
    today = datetime.today()
    last_monday = today - timedelta(days=today.weekday() + 7)
    last_sunday = last_monday + timedelta(days=6)
    return (
        last_monday.strftime("%Y-%m-%d"),
        last_sunday.strftime("%Y-%m-%d"),
        last_monday.strftime("%d.%m.%Y"),
        last_sunday.strftime("%d.%m.%Y"),
    )


def run():
    property_id = os.getenv("GA4_PROPERTY_ID")
    sheet_id = os.getenv("GOOGLE_SHEETS_ID")

    if not property_id:
        raise ValueError("GA4_PROPERTY_ID не встановлено")
    if not sheet_id:
        raise ValueError("GOOGLE_SHEETS_ID не встановлено")

    week_start_api, week_end_api, week_start_display, week_end_display = get_week_range()
    log.info(f"Запуск pipeline за тиждень {week_start_display} → {week_end_display}")

    creds = _get_credentials()
    connector = GA4Connector(property_id=property_id, credentials=creds)

    log.info("GA4: отримую трафік по каналах...")
    df_channel = connector.get_channel_traffic(date_range=(week_start_api, week_end_api))

    log.info("GA4: отримую engagement (сторінки × канали)...")
    df_eng = connector.get_engagement_full(date_range=(week_start_api, week_end_api))

    log.info("GA4: отримую product events (ЮО, ЗП-проект, Аванс)...")
    df_events = connector.get_product_events(date_range=(week_start_api, week_end_api))

    log.info("GA4: отримую конверсії (ФОП, ЮО, Аванс)...")
    df_conv_raw = connector.get_conversions(date_range=(week_start_api, week_end_api))
    df_conv = aggregate_conversions(df_conv_raw, week_start_display)
    upsert_weekly_snapshot(df_conv, tab_name="conversions", date_col="week_start",
                           credentials=creds, sheet_id=sheet_id,
                           week_start=week_start_display, week_end=week_end_display)
    log.info(f"GA4 конверсії: записано {len(df_conv)} рядків")

    df_traffic = build_traffic_by_channel(df_channel, df_eng, week_start_display, df_events)
    upsert_weekly_snapshot(df_traffic, tab_name="traffic_by_channel", date_col="week_start",
                           credentials=creds, sheet_id=sheet_id,
                           week_start=week_start_display, week_end=week_end_display)
    log.info(f"GA4 трафік: записано {len(df_traffic)} рядків")

    df_eng_agg = aggregate_engagement(df_eng, week_start_display, df_events)
    upsert_weekly_snapshot(df_eng_agg, tab_name="engagement", date_col="week_start",
                           credentials=creds, sheet_id=sheet_id,
                           week_start=week_start_display, week_end=week_end_display)
    log.info(f"GA4 engagement: записано {len(df_eng_agg)} рядків")

    log.info("GSC: отримую ключові слова...")
    gsc_site_url = os.getenv("GSC_SITE_URL", "https://monobank.ua/")
    gsc = GSCConnector(site_url=gsc_site_url, credentials=creds)
    df_gsc_raw = gsc.get_keywords(date_range=(week_start_api, week_end_api))
    df_gsc = aggregate_gsc_keywords(df_gsc_raw, week_start_display)
    upsert_weekly_snapshot(df_gsc, tab_name="gsc_keywords", date_col="week_start",
                           credentials=creds, sheet_id=sheet_id,
                           week_start=week_start_display, week_end=week_end_display)
    log.info(f"GSC: записано {len(df_gsc)} рядків")

    df_meta_raw = pd.DataFrame()
    df_meta = pd.DataFrame()
    log.info("Meta Ads: отримую статистику кампаній...")
    meta_token = os.getenv("META_TOKEN")
    meta_account_id = os.getenv("META_AD_ACCOUNT_ID", "act_455699156062655")
    if meta_token:
        meta = MetaAdsConnector(access_token=meta_token, ad_account_id=meta_account_id)
        df_meta_raw = meta.get_campaigns(date_range=(week_start_api, week_end_api))
        df_meta = aggregate_meta_ads(df_meta_raw, week_start_display)
        upsert_weekly_snapshot(df_meta, tab_name="meta_ads", date_col="week_start",
                               credentials=creds, sheet_id=sheet_id,
                               week_start=week_start_display, week_end=week_end_display)
        log.info(f"Meta Ads: записано {len(df_meta)} рядків")
    else:
        log.warning("META_TOKEN не знайдено — пропускаємо Meta Ads")

    df_ads_raw = pd.DataFrame()
    df_ads_kw = pd.DataFrame()
    log.info("Google Ads: отримую ключові слова і кампанії...")
    ads_customer_id = os.getenv("GOOGLE_ADS_CUSTOMER_ID")
    if ads_customer_id and os.getenv("GOOGLE_ADS_TOKEN"):
        ads = GoogleAdsConnector(customer_id=ads_customer_id)
        df_ads_raw = ads.get_keywords_performance(date_range=(week_start_api, week_end_api))
        df_ads_kw = aggregate_ads_keywords(df_ads_raw, week_start_display)
        upsert_weekly_snapshot(df_ads_kw, tab_name="ads_keywords", date_col="week_start",
                               credentials=creds, sheet_id=sheet_id,
                               week_start=week_start_display, week_end=week_end_display)
        log.info(f"Google Ads ключові слова: записано {len(df_ads_kw)} рядків")
    else:
        log.warning("GOOGLE_ADS_TOKEN або GOOGLE_ADS_CUSTOMER_ID не знайдено — пропускаємо Google Ads")

    log.info("Product matrix: будую зведену матрицю Продукт × Канал...")
    df_matrix = build_product_matrix(
        df_engagement=df_eng,
        df_gsc=df_gsc_raw,
        df_ads=df_ads_kw,
        df_meta=df_meta if meta_token else pd.DataFrame(),
        week_start=week_start_display,
    )
    upsert_weekly_snapshot(df_matrix, tab_name="product_matrix", date_col="week_start",
                           credentials=creds, sheet_id=sheet_id,
                           week_start=week_start_display, week_end=week_end_display)
    log.info(f"Product matrix: записано {len(df_matrix)} рядків")

    log.info("Pipeline завершено успішно.")


if __name__ == "__main__":
    run()
