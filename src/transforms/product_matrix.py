import pandas as pd

from src.transforms.traffic import CHANNEL_NAME_MAP, _is_public_page, _full_url

# 7 маркетингових кластерів — фіксований порядок
PRODUCT_CLUSTERS = ["ФОП", "ЮО", "Еквайринг", "ЗП-проект", "Аванс", "Частинами", "Пакети"]


def build_product_matrix(
    df_engagement: pd.DataFrame,
    df_gsc: pd.DataFrame,
    df_ads: pd.DataFrame,
    df_meta: pd.DataFrame,
    week_start: str,
) -> pd.DataFrame:
    """
    Зведена матриця: 1 рядок = 1 продукт (7 рядків max).
    Всі канали в колонках — повний маркетинговий портрет продукту за тиждень.
    Джерела: GA4 (sessions, bounce_rate), GSC (organic_clicks, top_keyword),
             Google Ads (paid_clicks, paid_cost_uah), Meta Ads (meta_clicks, meta_spend).
    """
    rows = {p: _empty_row(p, week_start) for p in PRODUCT_CLUSTERS}

    # --- GA4: total sessions + bounce_rate + top_page ---
    if not df_engagement.empty:
        eng = df_engagement.copy()
        eng["channel"] = eng["channel"].map(CHANNEL_NAME_MAP).fillna("Other")
        eng = eng[eng["product"].isin(PRODUCT_CLUSTERS)]

        users_col = "users" if "users" in eng.columns else "sessions"
        ga4_agg = (
            eng.groupby("product", as_index=False)
            .agg(
                sessions=("sessions", "sum"),
                users=(users_col, "sum"),
                bounce_rate=("bounce_rate", "mean"),
            )
        )
        ga4_agg["bounce_rate"] = ga4_agg["bounce_rate"].round(1)

        # top_page — тільки публічні маркетингові сторінки
        if "page_path" in eng.columns:
            top_pages = (
                eng[eng["page_path"].apply(_is_public_page)]
                .sort_values("sessions", ascending=False)
                .groupby("product")["page_path"]
                .first()
                .apply(_full_url)
                .to_dict()
            )
        else:
            top_pages = {}

        for _, r in ga4_agg.iterrows():
            p = r["product"]
            if p in rows:
                rows[p]["sessions"] = int(r["sessions"])
                rows[p]["users"] = int(r["users"])
                rows[p]["bounce_rate"] = r["bounce_rate"]
                rows[p]["top_page"] = top_pages.get(p, "")

    # --- GSC: organic clicks + impressions + ctr + top_keyword ---
    if not df_gsc.empty:
        gsc = df_gsc[df_gsc.get("query", df_gsc.get("top_keyword", pd.Series(dtype=str))) != ""].copy() if "query" in df_gsc.columns else df_gsc.copy()

        # підтримуємо обидва формати: старий (query) і новий (top_keyword кластерний)
        if "top_keyword" in gsc.columns:
            # новий кластерний формат
            gsc_totals = (
                gsc.groupby("product", as_index=False)
                .agg(organic_clicks=("total_clicks", "sum"),
                     organic_impressions=("total_impressions", "sum"))
            )
            gsc_top_kw = (
                gsc.sort_values("total_clicks", ascending=False)
                .groupby("product")["top_keyword"]
                .first()
                .to_dict()
            )
        else:
            # старий формат (query рядки)
            gsc_totals = (
                gsc.groupby("product", as_index=False)
                .agg(organic_clicks=("clicks", "sum"),
                     organic_impressions=("impressions", "sum"))
            )
            gsc_top_kw = (
                gsc.sort_values("clicks", ascending=False)
                .groupby("product")["query"]
                .first()
                .to_dict()
            )

        # top_page з GSC (для fallback коли GA4 sessions=0)
        gsc_top_page = {}
        page_col = "top_page" if "top_page" in gsc.columns else ("page" if "page" in gsc.columns else None)
        if page_col:
            clicks_col = "total_clicks" if "total_clicks" in gsc.columns else "clicks"
            gsc_top_page = (
                gsc.sort_values(clicks_col, ascending=False)
                .groupby("product")[page_col]
                .first()
                .apply(lambda p: ("https://monobank.ua" + p) if p and not p.startswith("http") else p)
                .to_dict()
            )

        for _, r in gsc_totals.iterrows():
            p = r["product"]
            if p in rows:
                rows[p]["organic_clicks"] = int(r["organic_clicks"])
                rows[p]["organic_impressions"] = int(r["organic_impressions"])
                imp = int(r["organic_impressions"])
                rows[p]["organic_ctr"] = round(int(r["organic_clicks"]) / imp * 100, 2) if imp > 0 else 0.0
                rows[p]["top_keyword"] = gsc_top_kw.get(p, "")
                # fallback: якщо GA4 не дав top_page — беремо з GSC
                if not rows[p]["top_page"] and p in gsc_top_page:
                    rows[p]["top_page"] = gsc_top_page[p]

    # --- Google Ads: paid clicks + cost ---
    if not df_ads.empty:
        # підтримуємо кластерний формат (product + total_clicks) і сирий (keyword + clicks)
        if "product" in df_ads.columns and "total_clicks" in df_ads.columns:
            ads_agg = (
                df_ads.groupby("product", as_index=False)
                .agg(paid_clicks=("total_clicks", "sum"),
                     paid_impressions=("total_impressions", "sum"),
                     paid_cost_uah=("total_cost_uah", "sum"))
            )
            for _, r in ads_agg.iterrows():
                p = r["product"]
                if p in rows:
                    rows[p]["paid_clicks"] = int(r["paid_clicks"])
                    rows[p]["paid_impressions"] = int(r.get("paid_impressions", 0))
                    rows[p]["paid_cost_uah"] = round(float(r["paid_cost_uah"]), 2)
        else:
            # сирий формат — агрегуємо всього, розподіляємо рівномірно між Paid Search рядками
            clicks_col = "clicks" if "clicks" in df_ads.columns else "total_clicks"
            imp_col = "impressions" if "impressions" in df_ads.columns else "total_impressions"
            cost_col = "cost_uah" if "cost_uah" in df_ads.columns else "total_cost_uah"
            total_paid_clicks = int(df_ads[clicks_col].sum())
            total_paid_impressions = int(df_ads[imp_col].sum()) if imp_col in df_ads.columns else 0
            total_paid_cost = round(float(df_ads[cost_col].sum()), 2) if cost_col in df_ads.columns else 0.0
            paid_products = [p for p in PRODUCT_CLUSTERS if rows[p]["sessions"] > 0]
            if paid_products:
                share = 1 / len(paid_products)
                for p in paid_products:
                    rows[p]["paid_clicks"] = round(total_paid_clicks * share)
                    rows[p]["paid_impressions"] = round(total_paid_impressions * share)
                    rows[p]["paid_cost_uah"] = round(total_paid_cost * share, 2)

    # --- Meta Ads: meta clicks + spend ---
    if not df_meta.empty:
        if "product" in df_meta.columns:
            meta_agg = (
                df_meta.groupby("product", as_index=False)
                .agg(meta_clicks=("clicks", "sum"),
                     meta_impressions=("impressions", "sum"),
                     meta_spend=("spend", "sum"))
            )
            for _, r in meta_agg.iterrows():
                p = r["product"]
                if p in rows:
                    rows[p]["meta_clicks"] = int(r["meta_clicks"])
                    rows[p]["meta_impressions"] = int(r["meta_impressions"])
                    rows[p]["meta_spend"] = round(float(r["meta_spend"]), 2)
        else:
            total_meta_clicks = int(df_meta["clicks"].sum())
            total_meta_impressions = int(df_meta["impressions"].sum())
            total_meta_spend = round(float(df_meta["spend"].sum()), 2)
            # без product-розбивки — пишемо загально (не знаємо куди)

    df = pd.DataFrame(
        [rows[p] for p in PRODUCT_CLUSTERS if rows[p]["sessions"] > 0 or rows[p]["organic_clicks"] > 0 or rows[p]["paid_clicks"] > 0 or rows[p]["meta_clicks"] > 0]
        or list(rows.values())[:1]
    )
    df["source_note"] = df.apply(_build_source_note, axis=1)

    cols = [
        "week_start", "product",
        "sessions", "users", "bounce_rate",
        "organic_clicks", "organic_impressions", "organic_ctr", "top_keyword",
        "paid_clicks", "paid_impressions", "paid_cost_uah",
        "meta_clicks", "meta_impressions", "meta_spend",
        "top_page", "source_note",
    ]
    return df[cols].reset_index(drop=True)


def _empty_row(product: str, week_start: str) -> dict:
    return {
        "week_start": week_start,
        "product": product,
        "sessions": 0,
        "users": 0,
        "bounce_rate": 0.0,
        "organic_clicks": 0,
        "organic_impressions": 0,
        "organic_ctr": 0.0,
        "top_keyword": "",
        "paid_clicks": 0,
        "paid_impressions": 0,
        "paid_cost_uah": 0.0,
        "meta_clicks": 0,
        "meta_impressions": 0,
        "meta_spend": 0.0,
        "top_page": "",
    }


def _build_source_note(r) -> str:
    parts = []
    signals = []

    if r["sessions"] > 0:
        note = f"GA4: {r['sessions']} сесій, {r.get('users', 0)} users"
        if r["top_page"]:
            note += f", топ сторінка: {r['top_page']}"
        if r["bounce_rate"] > 0:
            note += f", відмови {r['bounce_rate']}%"
        parts.append(note)
        if r["bounce_rate"] >= 70:
            signals.append("⚠️ bounce >70% — перевір лендинг і оголошення")

    if r["organic_clicks"] > 0:
        note = f"GSC: {r['organic_clicks']} кліків, {r['organic_impressions']} показів, CTR {r['organic_ctr']}%"
        if r["top_keyword"]:
            note += f" → топ запит: '{r['top_keyword']}'"
        parts.append(note)

    if r["paid_clicks"] > 0:
        note = f"Google Ads: {r['paid_clicks']} кліків, {r['paid_cost_uah']} грн"
        parts.append(note)
    elif r["paid_cost_uah"] > 0:
        signals.append("⚠️ Google Ads: є витрати, але кліків немає")

    if r["meta_clicks"] > 0:
        note = f"Meta Ads: {r['meta_clicks']} кліків, {r['meta_spend']} грн"
        parts.append(note)

    if r["sessions"] == 0 and r["organic_clicks"] == 0 and r["paid_clicks"] == 0 and r["meta_clicks"] == 0:
        return "немає даних за тиждень"

    if signals:
        parts.append("РІШЕННЯ: " + " | ".join(signals))

    return " | ".join(parts)
