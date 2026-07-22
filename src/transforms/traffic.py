import pandas as pd
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from config.page_filters import BRANDED_KEYWORDS, BUSINESS_PAGES, CABINET_PAGES

BASE_URL = "https://monobank.ua"


def _is_public_page(path: str) -> bool:
    """Тільки публічні маркетингові сторінки. Кабінетні шляхи явно виключаємо."""
    if any(path.startswith(p) for p in CABINET_PAGES):
        return False
    return any(path.startswith(p) for p in BUSINESS_PAGES)


def _full_url(path: str) -> str:
    if not path:
        return ""
    if path.startswith("http"):
        return path
    return BASE_URL + ("" if path.startswith("/") else "/") + path


CHANNEL_NAME_MAP = {
    "Organic Search": "Organic Search",
    "Paid Search": "Paid Search",
    "Direct": "Direct",
    "Referral": "Referral",
    "Organic Social": "Social",
    "Paid Social": "Meta Ads",
    "Cross-network": "Paid Search",
    "AI Assistant": "AI Assistant",
    "Organic Video": "Organic Video",
    "Email": "Email",
    "Unassigned": "Unassigned",
}


def classify_keyword(query: str) -> str:
    q = query.lower()
    for kw in BRANDED_KEYWORDS:
        if kw in q:
            return "branded"
    return "non-branded"


_DECISION_SIGNALS = [
    "підключити", "відкрити", "зареєструвати", "оформити", "замовити",
    "підключення", "реєстрація", "connect", "open", "register", "sign up",
    "купити", "тариф", "ціна", "price", "pricing", "cost",
]
_CONSIDERATION_SIGNALS = [
    "порівняння", "порівняти", "кращий", "топ", "рейтинг", "vs", "versus",
    "або", "чи варто", "відгуки", "огляд", "comparison", "best", "review",
    "альтернатива", "alternative",
]


def classify_funnel_stage(query: str) -> str:
    """Визначає стадію воронки: awareness / consideration / decision."""
    q = query.lower()
    if any(sig in q for sig in _DECISION_SIGNALS):
        return "decision"
    if any(sig in q for sig in _CONSIDERATION_SIGNALS):
        return "consideration"
    return "awareness"


def normalize_channels(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    df = df.copy()
    df["channel"] = df["channel"].map(CHANNEL_NAME_MAP).fillna("Other")
    df = (
        df.groupby("channel", as_index=False)
        .agg({"sessions": "sum", "users": "sum", "pageviews": "sum"})
    )

    total_sessions = df["sessions"].sum()
    df["pct_of_total"] = (
        (df["sessions"] / total_sessions * 100).round(2) if total_sessions > 0 else 0.0
    )

    return df.sort_values("sessions", ascending=False).reset_index(drop=True)


def build_traffic_by_channel(
    df_channel: pd.DataFrame,
    df_engagement: pd.DataFrame,
    week_start: str,
    df_events: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Агрегує трафік по каналах з розбивкою по продуктах.

    Джерела:
    - df_engagement: GA4 сторінки (Еквайринг, ФОП — onboarding paths)
    - df_events: GA4 custom events (ЮО, ЗП-проект, Аванс — SPA events всередині /mono-business)
    - df_channel: GA4 канали без розбивки (fallback якщо обидва порожні)

    Повертає: week_start, product, channel, sessions, users, pct_of_total, top_page, source_note
    """
    cols = ["week_start", "product", "channel", "sessions", "users",
            "pct_of_total", "top_page", "source_note"]

    if df_engagement.empty and (df_events is None or df_events.empty):
        df = normalize_channels(df_channel)
        if df.empty:
            return pd.DataFrame(columns=cols)
        df.insert(0, "week_start", week_start)
        df.insert(2, "product", "Всі продукти")
        df["top_page"] = ""
        df["source_note"] = df["channel"].apply(
            lambda c: f"GA4 — сесії з каналу {c} (розбивка по продуктах відсутня)"
        )
        return df

    parts = []

    # --- Частина 1: onboarding сторінки (Еквайринг, ФОП) ---
    if not df_engagement.empty:
        df = df_engagement.copy()
        df["channel"] = df["channel"].map(CHANNEL_NAME_MAP).fillna("Other")
        users_col = "users" if "users" in df.columns else "sessions"
        df_filtered = df[~df["product"].isin(["Unknown", "Кабінет", "Інформаційні"])]
        page_agg = (
            df_filtered
            .groupby(["product", "channel"], as_index=False)
            .agg(sessions=("sessions", "sum"), users=(users_col, "sum"))
        )
        # top_page — сторінка з найбільшою кількістю сесій для product×channel
        if "page_path" in df_filtered.columns:
            top_pages = (
                df_filtered.groupby(["product", "channel", "page_path"], as_index=False)["sessions"]
                .sum()
                .sort_values("sessions", ascending=False)
                .groupby(["product", "channel"], as_index=False)["page_path"]
                .first()
                .rename(columns={"page_path": "top_page"})
            )
            page_agg = page_agg.merge(top_pages, on=["product", "channel"], how="left")
            page_agg["top_page"] = page_agg["top_page"].fillna("")
        else:
            page_agg["top_page"] = ""
        page_agg["source_note"] = page_agg.apply(
            lambda r: f"GA4 сторінки — '{r['product']}', канал {r['channel']}, сесій: {r['sessions']}",
            axis=1,
        )
        parts.append(page_agg)

    # --- Частина 2: SPA events (ЮО, ЗП-проект, Аванс) ---
    if df_events is not None and not df_events.empty:
        df_ev = df_events.copy()
        df_ev["channel"] = df_ev["channel"].map(CHANNEL_NAME_MAP).fillna("Other")
        ev_agg = (
            df_ev.groupby(["product", "channel"], as_index=False)
            .agg(sessions=("users", "sum"), users=("users", "sum"))
        )
        ev_agg["top_page"] = ""
        ev_agg["source_note"] = ev_agg.apply(
            lambda r: f"GA4 events — '{r['product']}', канал {r['channel']}, users: {r['users']}",
            axis=1,
        )
        # тільки нові продукти — щоб не сумувати з onboarding сторінками
        existing = set(parts[0]["product"].unique()) if parts else set()
        ev_new = ev_agg[~ev_agg["product"].isin(existing)]
        if not ev_new.empty:
            parts.append(ev_new)

    agg = pd.concat(parts, ignore_index=True)
    # якщо той самий продукт×канал є в обох — сумуємо
    agg = agg.groupby(["product", "channel"], as_index=False).agg(
        sessions=("sessions", "sum"),
        users=("users", "sum"),
        top_page=("top_page", "first"),
        source_note=("source_note", "first"),
    )

    total = agg["sessions"].sum()
    agg["pct_of_total"] = (agg["sessions"] / total * 100).round(2) if total > 0 else 0.0
    agg.insert(0, "week_start", week_start)

    return agg[cols].sort_values(["product", "sessions"], ascending=[True, False]).reset_index(drop=True)


def aggregate_gsc_keywords(df: pd.DataFrame, week_start: str, top_n: int = 5) -> pd.DataFrame:
    """
    Агрегує GSC ключові слова кластерами: 1 рядок = product × keyword_type.
    Ключові слова — характеристики кластеру (топ-N через кому в одній клітинці).
    Повертає: week_start, product, keyword_type, dominant_intent, top_keywords, top_keyword,
              total_clicks, total_impressions, avg_ctr, avg_position, top_page, source_note
    """
    if df.empty:
        return pd.DataFrame(columns=[
            "week_start", "product", "keyword_type", "dominant_intent",
            "top_keywords", "top_keyword", "total_clicks", "total_impressions",
            "avg_ctr", "avg_position", "top_page", "source_note",
        ])

    df = df[df["query"] != ""].copy()
    # тільки відомі кластери
    known_products = ["ФОП", "ЮО", "Еквайринг", "ЗП-проект", "Аванс", "Частинами", "Пакети"]
    df = df[df["product"].isin(known_products)]
    if df.empty:
        return pd.DataFrame(columns=[
            "week_start", "product", "keyword_type", "dominant_intent",
            "top_keywords", "top_keyword", "total_clicks", "total_impressions",
            "avg_ctr", "avg_position", "top_page", "source_note",
        ])

    # агрегуємо по query щоб мати clicks/impressions на рівні query
    query_agg = (
        df.groupby(["product", "keyword_type", "query"], as_index=False)
        .agg(clicks=("clicks", "sum"), impressions=("impressions", "sum"),
             avg_position=("position", "mean"), avg_ctr=("ctr", "mean"))
    )
    query_agg["intent"] = query_agg["query"].apply(classify_funnel_stage)

    # топ сторінка для кластеру (product × keyword_type)
    top_page_df = (
        df.sort_values("clicks", ascending=False)
        .groupby(["product", "keyword_type"])["page"]
        .first()
        .reset_index()
        .rename(columns={"page": "top_page"})
    )
    top_page_df["top_page"] = top_page_df["top_page"].apply(_full_url)

    # кластерна агрегація
    result_rows = []
    for (product, kw_type), grp in query_agg.groupby(["product", "keyword_type"]):
        grp_sorted = grp.sort_values("clicks", ascending=False)
        top_queries = grp_sorted["query"].head(top_n).tolist()
        top_kw = top_queries[0] if top_queries else ""
        top_keywords_str = ", ".join(top_queries)

        # dominant_intent — домінуючий намір серед топ-N запитів
        dominant = grp_sorted["intent"].head(top_n).mode()
        dominant_intent = dominant.iloc[0] if not dominant.empty else "awareness"

        total_clicks = int(grp["clicks"].sum())
        total_impressions = int(grp["impressions"].sum())
        avg_ctr = round(total_clicks / total_impressions * 100, 2) if total_impressions > 0 else 0.0
        avg_position = round(grp["avg_position"].mean(), 1)

        result_rows.append({
            "product": product,
            "keyword_type": kw_type,
            "dominant_intent": dominant_intent,
            "top_keywords": top_keywords_str,
            "top_keyword": top_kw,
            "total_clicks": total_clicks,
            "total_impressions": total_impressions,
            "avg_ctr": avg_ctr,
            "avg_position": avg_position,
        })

    result = pd.DataFrame(result_rows)
    result = result.merge(top_page_df, on=["product", "keyword_type"], how="left")
    result["top_page"] = result["top_page"].fillna("")
    result.insert(0, "week_start", week_start)

    result["source_note"] = result.apply(
        lambda r: (
            f"GSC — продукт '{r['product']}', "
            f"{'брендовані' if r['keyword_type'] == 'branded' else 'небрендовані'} запити, "
            f"намір: {r['dominant_intent']}, топ: '{r['top_keyword']}', "
            f"кліків: {r['total_clicks']}, CTR {r['avg_ctr']}%, позиція {r['avg_position']}, "
            f"сторінка: {r['top_page']}"
        ),
        axis=1,
    )

    cols = [
        "week_start", "product", "keyword_type", "dominant_intent",
        "top_keywords", "top_keyword", "total_clicks", "total_impressions",
        "avg_ctr", "avg_position", "top_page", "source_note",
    ]
    return result[cols].sort_values(["product", "keyword_type"]).reset_index(drop=True)


def aggregate_ads_keywords(df: pd.DataFrame, week_start: str, top_n: int = 5) -> pd.DataFrame:
    """
    Агрегує Google Ads ключові слова кластерами: 1 рядок = product × funnel_stage.
    Ключові слова — характеристики кластеру (топ-N через кому).
    Повертає: week_start, product, funnel_stage, top_keywords, top_keyword,
              total_clicks, total_impressions, avg_ctr, total_cost_uah, landing_url, source_note
    """
    if df.empty:
        return pd.DataFrame(columns=[
            "week_start", "product", "funnel_stage", "top_keywords", "top_keyword",
            "total_clicks", "total_impressions", "avg_ctr", "total_cost_uah",
            "landing_url", "source_note",
        ])

    df = df.copy()
    df["funnel_stage"] = df["keyword"].apply(classify_funnel_stage)

    # визначаємо product за landing_url якщо є
    if "landing_url" in df.columns and "product" not in df.columns:
        from config.page_filters import get_product_by_url
        df["product"] = df["landing_url"].fillna("").apply(
            lambda u: get_product_by_url(u)[0] if u else "Загальне"
        )
    elif "product" not in df.columns:
        df["product"] = "Загальне"

    # тільки відомі кластери
    known_products = ["ФОП", "ЮО", "Еквайринг", "ЗП-проект", "Аванс", "Частинами", "Пакети"]
    df = df[df["product"].isin(known_products)]
    if df.empty:
        return pd.DataFrame(columns=[
            "week_start", "product", "funnel_stage", "top_keywords", "top_keyword",
            "total_clicks", "total_impressions", "avg_ctr", "total_cost_uah",
            "landing_url", "source_note",
        ])

    # кластерна агрегація
    result_rows = []
    for (product, stage), grp in df.groupby(["product", "funnel_stage"]):
        kw_agg = (
            grp.groupby("keyword", as_index=False)
            .agg(clicks=("clicks", "sum"), impressions=("impressions", "sum"),
                 cost_uah=("cost_uah", "sum"))
        )
        kw_sorted = kw_agg.sort_values("clicks", ascending=False)
        top_kws = kw_sorted["keyword"].head(top_n).tolist()
        top_kw = top_kws[0] if top_kws else ""

        total_clicks = int(grp["clicks"].sum())
        total_impressions = int(grp["impressions"].sum())
        avg_ctr = round(total_clicks / total_impressions * 100, 2) if total_impressions > 0 else 0.0
        total_cost = round(float(grp["cost_uah"].sum()), 2)

        # топ landing_url для кластеру
        landing_url = ""
        if "landing_url" in grp.columns:
            urls = grp[grp["landing_url"].notna() & (grp["landing_url"] != "")]
            if not urls.empty:
                landing_url = _full_url(urls.sort_values("clicks", ascending=False).iloc[0]["landing_url"])

        result_rows.append({
            "product": product,
            "funnel_stage": stage,
            "top_keywords": ", ".join(top_kws),
            "top_keyword": top_kw,
            "total_clicks": total_clicks,
            "total_impressions": total_impressions,
            "avg_ctr": avg_ctr,
            "total_cost_uah": total_cost,
            "landing_url": landing_url,
        })

    result = pd.DataFrame(result_rows)
    result.insert(0, "week_start", week_start)

    result["source_note"] = result.apply(
        lambda r: (
            f"Google Ads — продукт '{r['product']}', стадія: {r['funnel_stage']}, "
            f"топ: '{r['top_keyword']}', кліків: {r['total_clicks']}, "
            f"CTR {r['avg_ctr']}%, витрати {r['total_cost_uah']} грн"
            + (f", лендинг: {r['landing_url']}" if r["landing_url"] else "")
        ),
        axis=1,
    )

    cols = [
        "week_start", "product", "funnel_stage", "top_keywords", "top_keyword",
        "total_clicks", "total_impressions", "avg_ctr", "total_cost_uah",
        "landing_url", "source_note",
    ]
    return result[cols].sort_values(["product", "funnel_stage"]).reset_index(drop=True)


def aggregate_engagement(
    df: pd.DataFrame,
    week_start: str,
    df_events: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Агрегує поведінкові метрики по product × channel за тиждень.
    df       — GA4 сторінки (Еквайринг, ФОП)
    df_events — GA4 custom events (ЮО, ЗП-проект, Аванс)
    """
    if df.empty:
        return pd.DataFrame(columns=[
            "week_start", "product", "channel", "source", "medium", "campaign",
            "sessions", "users", "bounce_rate", "avg_session_duration",
            "top_page", "source_note"
        ])

    df = df.copy()
    df["channel"] = df["channel"].map(CHANNEL_NAME_MAP).fillna("Other")

    # source/medium/campaign — нормалізуємо (not set) → ""
    for col in ["source", "medium", "campaign"]:
        if col in df.columns:
            df[col] = df[col].replace({"(not set)": "", "(none)": "", "(organic)": "organic",
                                        "(direct)": "direct", "(referral)": "referral",
                                        "(ai-assistant)": "ai-assistant"})
        else:
            df[col] = ""

    top_pages = (
        df[df["page_path"].apply(_is_public_page)]
        .sort_values("sessions", ascending=False)
        .groupby(["product", "channel"])["page_path"]
        .first()
        .reset_index()
        .rename(columns={"page_path": "top_page"})
    )
    top_pages["top_page"] = top_pages["top_page"].apply(_full_url)

    # топ source/medium/campaign по сесіях для кожного product × channel
    top_sources = (
        df.sort_values("sessions", ascending=False)
        .groupby(["product", "channel"])[["source", "medium", "campaign"]]
        .first()
        .reset_index()
    )

    users_col = "users" if "users" in df.columns else "sessions"

    agg = (
        df[~df["product"].isin(["Unknown", "Кабінет", "Інформаційні"])]
        .groupby(["product", "channel"], as_index=False)
        .agg(
            sessions=("sessions", "sum"),
            users=(users_col, "sum"),
            bounce_rate=("bounce_rate", "mean"),
            avg_session_duration=("avg_session_duration", "mean"),
        )
    )
    agg["bounce_rate"] = agg["bounce_rate"].round(1)
    agg["avg_session_duration"] = agg["avg_session_duration"].round(1)

    agg = agg.merge(top_pages, on=["product", "channel"], how="left")
    agg = agg.merge(top_sources, on=["product", "channel"], how="left")
    agg.insert(0, "week_start", week_start)

    def _eng_note(r):
        src = r.get("source", "")
        med = r.get("medium", "")
        camp = r.get("campaign", "")
        src_str = ""
        if r["channel"] == "Paid Search":
            src_str = f", джерело: {src}/{med}"
            if camp and camp not in ("", "(not set)"):
                src_str += f", кампанія: '{camp}'"
        elif src and src not in ("", "direct"):
            src_str = f", джерело: {src}"
        return (
            f"GA4 — продукт '{r['product']}', канал {r['channel']}{src_str}, "
            f"сесій: {r['sessions']}, users: {r['users']}, "
            f"топ сторінка: {r['top_page']}, відмови {r['bounce_rate']}%, "
            f"avg duration: {r['avg_session_duration']}с"
        )

    agg["source_note"] = agg.apply(_eng_note, axis=1)

    cols = ["week_start", "product", "channel", "source", "medium", "campaign",
            "sessions", "users", "bounce_rate", "avg_session_duration",
            "top_page", "source_note"]

    # --- Додаємо SPA events (ЮО, ЗП-проект, Аванс) ---
    if df_events is not None and not df_events.empty:
        df_ev = df_events.copy()
        df_ev["channel"] = df_ev["channel"].map(CHANNEL_NAME_MAP).fillna("Other")
        ev_agg = (
            df_ev.groupby(["product", "channel"], as_index=False)
            .agg(sessions=("users", "sum"), users=("users", "sum"))
        )
        ev_agg["bounce_rate"] = 0.0
        ev_agg["avg_session_duration"] = 0.0
        ev_agg["top_page"] = ""
        ev_agg["source"] = ""
        ev_agg["medium"] = ""
        ev_agg["campaign"] = ""
        ev_agg["source_note"] = ev_agg.apply(
            lambda r: f"GA4 events — '{r['product']}', канал {r['channel']}, users: {r['users']}",
            axis=1,
        )
        ev_agg.insert(0, "week_start", week_start)
        # Додаємо тільки продукти яких ще немає від сторінок — щоб не дублювати ФОП
        existing_products = set(agg["product"].unique())
        ev_new = ev_agg[~ev_agg["product"].isin(existing_products)]
        if not ev_new.empty:
            agg = pd.concat([agg, ev_new[cols]], ignore_index=True)

    return agg[cols].sort_values(["product", "sessions"], ascending=[True, False]).reset_index(drop=True)


_META_CAMPAIGN_PRODUCT_MAP = [
    # патерни в назвах кампаній → product
    ("FOP", "ФОП"),
    ("Fop", "ФОП"),
    ("fop", "ФОП"),
    ("ФОП", "ФОП"),
    ("Acquiring", "Еквайринг"),
    ("acquiring", "Еквайринг"),
    ("Еквайрінг", "Еквайринг"),
    ("YO_", "ЮО"),
    ("_YO", "ЮО"),
    ("ЮО", "ЮО"),
    ("ЗП", "ЗП-проект"),
    ("salary", "ЗП-проект"),
    ("КЕП", "ЮО"),           # КЕП = кваліфікований електронний підпис — бізнес-продукт
    ("ПЧ", "Оплата Частями"),
    ("Частями", "Оплата Частями"),
    ("advance", "Аванс"),
    ("Advance", "Аванс"),
    ("beauty", "Пакети"),
    ("Beauty", "Пакети"),
]


def _meta_product_from_campaign(campaign_name: str) -> str:
    for pattern, product in _META_CAMPAIGN_PRODUCT_MAP:
        if pattern in campaign_name:
            return product
    return "Загальне"


def aggregate_meta_ads(df: pd.DataFrame, week_start: str) -> pd.DataFrame:
    """
    Агрегує Meta Ads кластерами: 1 рядок = product (топ кампанія кластеру).
    Product визначається за назвою кампанії (Meta не повертає landing_url для бізнес-сторінок —
    кампанії ведуть на Google Play або Lead Form).
    Повертає: week_start, product, campaign_name, impressions, clicks, ctr, spend, campaign_type, source_note
    """
    if df.empty:
        return pd.DataFrame(columns=[
            "week_start", "product", "campaign_name", "impressions",
            "clicks", "ctr", "spend", "campaign_type", "source_note",
        ])

    df = df.copy()

    if "product" not in df.columns:
        df["product"] = df["campaign_name"].apply(_meta_product_from_campaign)

    # тип кампанії: app_install або lead_form або traffic
    def _campaign_type(name: str) -> str:
        n = name.lower()
        if "pr_app_reg" in n or "cpa" in n or "android" in n:
            return "app_install"
        if "lead" in n or "leads" in n:
            return "lead_form"
        return "traffic"

    df["campaign_type"] = df["campaign_name"].apply(_campaign_type)

    if "landing_url" not in df.columns:
        df["landing_url"] = ""

    # кластерна агрегація: 1 рядок на product
    result_rows = []
    for product, grp in df.groupby("product"):
        grp_sorted = grp.sort_values("spend", ascending=False)
        top_row = grp_sorted.iloc[0]

        total_impressions = int(grp["impressions"].sum())
        total_clicks = int(grp["clicks"].sum())
        total_spend = round(float(grp["spend"].sum()), 2)
        ctr = round(total_clicks / total_impressions * 100, 2) if total_impressions > 0 else 0.0
        camp_type = top_row.get("campaign_type", "traffic")

        result_rows.append({
            "product": product,
            "campaign_name": str(top_row["campaign_name"]),
            "impressions": total_impressions,
            "clicks": total_clicks,
            "ctr": ctr,
            "spend": total_spend,
            "campaign_type": camp_type,
        })

    result = pd.DataFrame(result_rows)
    result.insert(0, "week_start", week_start)

    result["source_note"] = result.apply(
        lambda r: (
            f"Meta Ads — продукт '{r['product']}', тип: {r['campaign_type']}, "
            f"кампанія '{r['campaign_name']}', "
            f"{r['impressions']} показів, {r['clicks']} кліків, CTR {r['ctr']}%, {r['spend']} грн"
        ),
        axis=1,
    )

    cols = [
        "week_start", "product", "campaign_name", "impressions",
        "clicks", "ctr", "spend", "campaign_type", "source_note",
    ]
    return result[cols].sort_values("spend", ascending=False).reset_index(drop=True)


def add_week_start(df: pd.DataFrame, week_start: str) -> pd.DataFrame:
    df = df.copy()
    df.insert(0, "week_start", week_start)
    return df


def drop_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    return df.drop_duplicates(subset=["week_start", "channel"]).reset_index(drop=True)
