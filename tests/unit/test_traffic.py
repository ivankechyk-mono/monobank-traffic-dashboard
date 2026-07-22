"""
Unit-тести для src/transforms/traffic.py
Покриття: build_traffic_by_channel, aggregate_engagement,
          aggregate_gsc_keywords, classify_keyword, classify_funnel_stage,
          normalize_channels, aggregate_meta_ads, aggregate_ads_keywords
"""
import pytest
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.transforms.traffic import (
    classify_keyword,
    classify_funnel_stage,
    normalize_channels,
    build_traffic_by_channel,
    aggregate_gsc_keywords,
    aggregate_ads_keywords,
    aggregate_engagement,
    aggregate_meta_ads,
)


# ─── classify_keyword ────────────────────────────────────────────────────────

def test_classify_keyword_branded():
    assert classify_keyword("монобанк фоп") == "branded"
    assert classify_keyword("monobank acquiring") == "branded"
    assert classify_keyword("plata by mono") == "branded"

def test_classify_keyword_non_branded():
    assert classify_keyword("відкрити фоп") == "non-branded"
    assert classify_keyword("еквайринг для малого бізнесу") == "non-branded"
    assert classify_keyword("зарплатний проект банк") == "non-branded"


# ─── classify_funnel_stage ────────────────────────────────────────────────────

def test_classify_funnel_stage_decision():
    assert classify_funnel_stage("підключити еквайринг") == "decision"
    assert classify_funnel_stage("ціна на термінал") == "decision"
    assert classify_funnel_stage("відкрити фоп онлайн") == "decision"

def test_classify_funnel_stage_consideration():
    assert classify_funnel_stage("кращий банк для фоп") == "consideration"
    assert classify_funnel_stage("порівняння еквайрингу") == "consideration"

def test_classify_funnel_stage_awareness():
    assert classify_funnel_stage("що таке еквайринг") == "awareness"
    assert classify_funnel_stage("фоп банк") == "awareness"


# ─── normalize_channels ──────────────────────────────────────────────────────

def test_normalize_channels_maps_known():
    df = pd.DataFrame({
        "channel": ["Organic Search", "Paid Search", "Organic Social", "Paid Social"],
        "sessions": [100, 50, 30, 20],
        "users": [90, 40, 25, 18],
        "pageviews": [200, 80, 60, 35],
    })
    result = normalize_channels(df)
    assert "Organic Search" in result["channel"].values
    assert "Meta Ads" in result["channel"].values
    assert "Social" in result["channel"].values

def test_normalize_channels_unknown_becomes_other():
    df = pd.DataFrame({
        "channel": ["SomeUnknownChannel"],
        "sessions": [10],
        "users": [8],
        "pageviews": [15],
    })
    result = normalize_channels(df)
    assert result["channel"].iloc[0] == "Other"

def test_normalize_channels_pct_sums_to_100():
    df = pd.DataFrame({
        "channel": ["Organic Search", "Direct", "Paid Search"],
        "sessions": [60, 30, 10],
        "users": [55, 28, 9],
        "pageviews": [120, 60, 20],
    })
    result = normalize_channels(df)
    assert abs(result["pct_of_total"].sum() - 100.0) < 0.1

def test_normalize_channels_empty():
    df = pd.DataFrame(columns=["channel", "sessions", "users", "pageviews"])
    result = normalize_channels(df)
    assert result.empty


# ─── build_traffic_by_channel ────────────────────────────────────────────────

def _make_engagement_df():
    return pd.DataFrame([
        {"date": "13.07.2026", "page_path": "/fop", "channel": "Organic Search",
         "source": "google", "medium": "organic", "campaign": "(not set)",
         "product": "ФОП", "sub_product": "Відкрити ФОП",
         "sessions": 60, "users": 55, "pageviews": 120,
         "bounce_rate": 30.0, "avg_session_duration": 45.0, "pages_per_session": 2.0},
        {"date": "13.07.2026", "page_path": "/acquiring", "channel": "Paid Search",
         "source": "google", "medium": "cpc", "campaign": "acquiring_main",
         "product": "Еквайринг", "sub_product": "Еквайринг загальне",
         "sessions": 30, "users": 28, "pageviews": 60,
         "bounce_rate": 50.0, "avg_session_duration": 30.0, "pages_per_session": 2.0},
        # Кабінет — повинен бути виключений
        {"date": "13.07.2026", "page_path": "/mono-business", "channel": "Direct",
         "source": "direct", "medium": "(none)", "campaign": "(not set)",
         "product": "Кабінет", "sub_product": "Головна кабінету",
         "sessions": 500, "users": 400, "pageviews": 1000,
         "bounce_rate": 10.0, "avg_session_duration": 120.0, "pages_per_session": 5.0},
        # Unknown — повинен бути виключений
        {"date": "13.07.2026", "page_path": "/some-random", "channel": "Direct",
         "source": "direct", "medium": "(none)", "campaign": "(not set)",
         "product": "Unknown", "sub_product": "Unknown",
         "sessions": 5, "users": 4, "pageviews": 8,
         "bounce_rate": 80.0, "avg_session_duration": 5.0, "pages_per_session": 1.0},
    ])

def test_build_traffic_excludes_cabinet_and_unknown():
    df_eng = _make_engagement_df()
    result = build_traffic_by_channel(pd.DataFrame(), df_eng, "13.07.2026")
    assert "Кабінет" not in result["product"].values
    assert "Unknown" not in result["product"].values

def test_build_traffic_users_leq_sessions():
    df_eng = _make_engagement_df()
    result = build_traffic_by_channel(pd.DataFrame(), df_eng, "13.07.2026")
    bad = result[result["users"].astype(int) > result["sessions"].astype(int)]
    assert len(bad) == 0, f"users > sessions в строках:\n{bad}"

def test_build_traffic_has_required_columns():
    df_eng = _make_engagement_df()
    result = build_traffic_by_channel(pd.DataFrame(), df_eng, "13.07.2026")
    required = ["week_start", "product", "channel", "sessions", "users", "pct_of_total", "top_page", "source_note"]
    for col in required:
        assert col in result.columns, f"Отсутствует колонка: {col}"

def test_build_traffic_week_start_value():
    df_eng = _make_engagement_df()
    result = build_traffic_by_channel(pd.DataFrame(), df_eng, "13.07.2026")
    assert (result["week_start"] == "13.07.2026").all()

def test_build_traffic_empty_engagement_fallback():
    df_ch = pd.DataFrame({
        "date": ["13.07.2026"],
        "channel": ["Organic Search"],
        "sessions": [100],
        "users": [90],
        "pageviews": [200],
        "pct_of_total": [100.0],
    })
    result = build_traffic_by_channel(df_ch, pd.DataFrame(), "13.07.2026")
    assert not result.empty


# ─── aggregate_engagement ────────────────────────────────────────────────────

def test_aggregate_engagement_excludes_cabinet():
    df_eng = _make_engagement_df()
    result = aggregate_engagement(df_eng, "13.07.2026")
    assert "Кабінет" not in result["product"].values

def test_aggregate_engagement_users_leq_sessions():
    df_eng = _make_engagement_df()
    result = aggregate_engagement(df_eng, "13.07.2026")
    bad = result[result["users"].astype(int) > result["sessions"].astype(int)]
    assert len(bad) == 0

def test_aggregate_engagement_bounce_rate_range():
    df_eng = _make_engagement_df()
    result = aggregate_engagement(df_eng, "13.07.2026")
    assert (result["bounce_rate"] >= 0).all()
    assert (result["bounce_rate"] <= 100).all()

def test_aggregate_engagement_required_columns():
    df_eng = _make_engagement_df()
    result = aggregate_engagement(df_eng, "13.07.2026")
    required = ["week_start", "product", "channel", "sessions", "users",
                "bounce_rate", "avg_session_duration"]
    for col in required:
        assert col in result.columns

def test_aggregate_engagement_empty():
    result = aggregate_engagement(pd.DataFrame(), "13.07.2026")
    assert result.empty


# ─── aggregate_gsc_keywords ──────────────────────────────────────────────────

def _make_gsc_df():
    return pd.DataFrame([
        {"date": "2026-07-13", "query": "монобанк фоп", "page": "/fop",
         "clicks": 50, "impressions": 500, "ctr": 10.0, "position": 1.5,
         "keyword_type": "branded", "product": "ФОП", "sub_product": "Відкрити ФОП"},
        {"date": "2026-07-13", "query": "відкрити фоп онлайн", "page": "/fop",
         "clicks": 20, "impressions": 400, "ctr": 5.0, "position": 3.2,
         "keyword_type": "non-branded", "product": "ФОП", "sub_product": "Відкрити ФОП"},
        {"date": "2026-07-13", "query": "monobank acquiring", "page": "/acquiring",
         "clicks": 30, "impressions": 300, "ctr": 10.0, "position": 2.0,
         "keyword_type": "branded", "product": "Еквайринг", "sub_product": "Еквайринг загальне"},
        {"date": "2026-07-13", "query": "еквайринг для кафе", "page": "/acquiring",
         "clicks": 5, "impressions": 200, "ctr": 2.5, "position": 6.0,
         "keyword_type": "non-branded", "product": "Еквайринг", "sub_product": "Еквайринг загальне"},
    ])

def test_aggregate_gsc_weighted_ctr():
    """CTR має бути clicks/impressions, не середнє по запитах."""
    df = _make_gsc_df()
    result = aggregate_gsc_keywords(df, "13.07.2026")
    fop_branded = result[(result["product"] == "ФОП") & (result["keyword_type"] == "branded")]
    assert len(fop_branded) == 1
    expected_ctr = round(50 / 500 * 100, 2)  # 10.0%
    assert abs(float(fop_branded["avg_ctr"].iloc[0]) - expected_ctr) < 0.1

def test_aggregate_gsc_clicks_leq_impressions():
    df = _make_gsc_df()
    result = aggregate_gsc_keywords(df, "13.07.2026")
    bad = result[result["total_clicks"].astype(int) > result["total_impressions"].astype(int)]
    assert len(bad) == 0

def test_aggregate_gsc_ctr_range():
    df = _make_gsc_df()
    result = aggregate_gsc_keywords(df, "13.07.2026")
    assert (result["avg_ctr"] >= 0).all()
    assert (result["avg_ctr"] <= 100).all()

def test_aggregate_gsc_only_known_products():
    df = _make_gsc_df()
    # Додаємо невідомий продукт
    extra = pd.DataFrame([{
        "date": "2026-07-13", "query": "random query", "page": "/unknown-page",
        "clicks": 1, "impressions": 10, "ctr": 10.0, "position": 5.0,
        "keyword_type": "non-branded", "product": "Невідомий", "sub_product": "x",
    }])
    df2 = pd.concat([df, extra], ignore_index=True)
    result = aggregate_gsc_keywords(df2, "13.07.2026")
    assert "Невідомий" not in result["product"].values

def test_aggregate_gsc_required_columns():
    df = _make_gsc_df()
    result = aggregate_gsc_keywords(df, "13.07.2026")
    required = ["week_start", "product", "keyword_type", "total_clicks",
                "total_impressions", "avg_ctr", "avg_position", "top_keyword"]
    for col in required:
        assert col in result.columns

def test_aggregate_gsc_empty():
    result = aggregate_gsc_keywords(pd.DataFrame(), "13.07.2026")
    assert result.empty


# ─── aggregate_ads_keywords ──────────────────────────────────────────────────

def _make_ads_df():
    return pd.DataFrame([
        {"keyword": "підключити еквайринг", "clicks": 40, "impressions": 400,
         "cost_uah": 200.0, "landing_url": "https://monobank.ua/acquiring"},
        {"keyword": "еквайринг для бізнесу", "clicks": 20, "impressions": 300,
         "cost_uah": 120.0, "landing_url": "https://monobank.ua/acquiring"},
        {"keyword": "відкрити фоп", "clicks": 15, "impressions": 200,
         "cost_uah": 80.0, "landing_url": "https://monobank.ua/fop"},
    ])

def test_aggregate_ads_clicks_leq_impressions():
    df = _make_ads_df()
    result = aggregate_ads_keywords(df, "13.07.2026")
    bad = result[result["total_clicks"].astype(int) > result["total_impressions"].astype(int)]
    assert len(bad) == 0

def test_aggregate_ads_cost_nonnegative():
    df = _make_ads_df()
    result = aggregate_ads_keywords(df, "13.07.2026")
    assert (result["total_cost_uah"] >= 0).all()

def test_aggregate_ads_funnel_stages_valid():
    df = _make_ads_df()
    result = aggregate_ads_keywords(df, "13.07.2026")
    valid = {"awareness", "consideration", "decision"}
    assert set(result["funnel_stage"].unique()).issubset(valid)

def test_aggregate_ads_required_columns():
    df = _make_ads_df()
    result = aggregate_ads_keywords(df, "13.07.2026")
    required = ["week_start", "product", "funnel_stage", "total_clicks",
                "total_impressions", "avg_ctr", "total_cost_uah", "landing_url"]
    for col in required:
        assert col in result.columns

def test_aggregate_ads_empty():
    result = aggregate_ads_keywords(pd.DataFrame(), "13.07.2026")
    assert result.empty


# ─── aggregate_meta_ads ──────────────────────────────────────────────────────

def _make_meta_df():
    return pd.DataFrame([
        {"campaign_name": "FOP_PR_app_reg_android_UA", "impressions": 5000,
         "clicks": 100, "spend": 300.0},
        {"campaign_name": "Acquiring_traffic_UA", "impressions": 3000,
         "clicks": 60, "spend": 180.0},
        {"campaign_name": "FOP_leads_UA", "impressions": 2000,
         "clicks": 40, "spend": 120.0},
    ])

def test_aggregate_meta_ctr_computed_correctly():
    df = _make_meta_df()
    result = aggregate_meta_ads(df, "13.07.2026")
    fop = result[result["product"] == "ФОП"].iloc[0]
    expected_ctr = round((100 + 40) / (5000 + 2000) * 100, 2)
    assert abs(float(fop["ctr"]) - expected_ctr) < 0.1

def test_aggregate_meta_clicks_leq_impressions():
    df = _make_meta_df()
    result = aggregate_meta_ads(df, "13.07.2026")
    bad = result[result["clicks"].astype(int) > result["impressions"].astype(int)]
    assert len(bad) == 0

def test_aggregate_meta_required_columns():
    df = _make_meta_df()
    result = aggregate_meta_ads(df, "13.07.2026")
    required = ["week_start", "product", "campaign_name", "impressions",
                "clicks", "ctr", "spend", "campaign_type"]
    for col in required:
        assert col in result.columns

def test_aggregate_meta_campaign_type_classified():
    df = _make_meta_df()
    result = aggregate_meta_ads(df, "13.07.2026")
    valid = {"app_install", "lead_form", "traffic"}
    assert set(result["campaign_type"].unique()).issubset(valid)

def test_aggregate_meta_empty():
    result = aggregate_meta_ads(pd.DataFrame(), "13.07.2026")
    assert result.empty
