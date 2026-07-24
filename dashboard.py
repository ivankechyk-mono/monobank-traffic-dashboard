"""
monobank business — Marketing Dashboard
Запуск: streamlit run dashboard.py
"""
import os
import sys
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Сторінка ──────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="monobank business · Marketing",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Dark theme CSS ─────────────────────────────────────────────────────────────
BG       = "#0f1117"
BG2      = "#1a1d27"
BG3      = "#232634"
BORDER   = "#2d3148"
TEXT     = "#e5e7eb"
TEXT_DIM = "#6b7280"
TEXT_MUT = "#4b5563"
BLUE     = "#3b82f6"
GREEN    = "#10b981"
RED      = "#ef4444"
ORANGE   = "#f97316"
PURPLE   = "#7c3aed"

st.markdown(f"""
<style>
html, body, [data-testid="stAppViewContainer"],
[data-testid="stApp"], [data-testid="stHeader"] {{
    background: {BG} !important;
    color: {TEXT} !important;
}}
section[data-testid="stSidebar"] {{ background: {BG2} !important; }}
.block-container {{ padding-top: 1.2rem; padding-bottom: 1rem; max-width: 1440px; }}

/* Tabs */
button[data-baseweb="tab"] {{
    background: transparent !important;
    color: {TEXT_DIM} !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    border-bottom: 2px solid transparent !important;
    padding-left: 20px !important;
    padding-right: 20px !important;
    margin-right: 4px !important;
}}
button[data-baseweb="tab"][aria-selected="true"] {{
    color: {TEXT} !important;
    border-bottom: 2px solid {BLUE} !important;
}}
div[data-testid="stTabs"] > div > div {{
    border-bottom: 1px solid {BORDER} !important;
    gap: 4px !important;
}}

/* Inputs */
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
div[data-testid="stDateInput"] > div > div > div {{
    background: {BG2} !important;
    border-color: {BORDER} !important;
    color: {TEXT} !important;
}}
div[data-baseweb="menu"] {{
    background: {BG3} !important;
    border: 1px solid {BORDER} !important;
}}
div[data-baseweb="menu"] li {{ color: {TEXT} !important; }}
div[data-baseweb="menu"] li:hover {{ background: {BG2} !important; }}

/* Toggle */
label[data-testid="stToggle"] span {{ color: {TEXT_DIM} !important; font-size: 0.83rem !important; }}

/* Dataframe */
[data-testid="stDataFrame"] {{ background: {BG2} !important; }}

/* KPI картка */
.kpi-card {{
    background: {BG2};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 16px 20px;
    min-height: 95px;
}}
.kpi-label {{
    font-size: 0.72rem;
    color: {TEXT_DIM};
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 6px;
}}
.kpi-value {{
    font-size: 1.9rem;
    font-weight: 700;
    color: {TEXT};
    line-height: 1.1;
}}
.kpi-delta-pos {{ font-size: 0.8rem; color: {GREEN}; font-weight: 600; margin-top: 4px; }}
.kpi-delta-neg {{ font-size: 0.8rem; color: {RED};   font-weight: 600; margin-top: 4px; }}
.kpi-delta-neu {{ font-size: 0.8rem; color: {TEXT_DIM}; font-weight: 500; margin-top: 4px; }}

/* Section headers */
.sec-head {{
    font-size: 0.95rem;
    font-weight: 600;
    color: {TEXT};
    margin-bottom: 2px;
    margin-top: 4px;
}}
.sec-sub {{
    font-size: 0.75rem;
    color: {TEXT_DIM};
    margin-bottom: 10px;
}}

/* Note/info box */
.note {{
    background: {BG3};
    border-left: 3px solid {BORDER};
    padding: 8px 14px;
    border-radius: 5px;
    font-size: 0.78rem;
    color: {TEXT_DIM};
    margin: 8px 0;
}}
.note-warn {{ border-left-color: #d97706; }}
.note-info {{ border-left-color: {BLUE}; }}

/* Filter label */
.filter-label {{
    font-size: 0.72rem;
    color: {TEXT_DIM};
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 4px;
    font-weight: 500;
}}

/* Hr divider */
.divider {{ border: none; border-top: 1px solid {BORDER}; margin: 16px 0; }}

/* Quick-range buttons */
div[data-testid="stButton"] > button {{
    font-size: 0.82rem !important;
    padding: 4px 10px !important;
    border-radius: 6px !important;
    font-weight: 500 !important;
}}
div[data-testid="stButton"] > button[kind="secondary"] {{
    background: {BG2} !important;
    border: 1px solid {BORDER} !important;
    color: {TEXT_DIM} !important;
}}
div[data-testid="stButton"] > button[kind="primary"] {{
    background: {BLUE} !important;
    border: 1px solid {BLUE} !important;
    color: #fff !important;
}}

/* Date range input */
div[data-testid="stDateInput"] input {{
    font-size: 0.83rem !important;
    color: {TEXT} !important;
}}
</style>
""", unsafe_allow_html=True)

# ── Кольори ───────────────────────────────────────────────────────────────────
PRODUCT_COLORS = {
    "ФОП":       "#3b82f6",
    "ЮО":        "#f97316",
    "Еквайринг": "#06b6d4",
    "ЗП-проект": "#8b5cf6",
    "Аванс":     "#f59e0b",
    "Частинами": "#10b981",
    "Пакети":    "#6b7280",
}
CHANNEL_COLORS = {
    "Organic Search": "#10b981",
    "Direct":         "#3b82f6",
    "Paid Search":    "#f59e0b",
    "Meta Ads":       "#f97316",
    "Referral":       "#8b5cf6",
    "Social":         "#ec4899",
    "Email":          "#06b6d4",
    "Unassigned":     "#4b5563",
    "Other":          "#374151",
}
SPA_PRODUCTS = {"ЮО", "ЗП-проект", "Аванс"}

PLOTLY_LAYOUT = dict(
    plot_bgcolor="#1a1d27",
    paper_bgcolor="#0f1117",
    font=dict(color="#9ca3af", size=11),
    xaxis=dict(showgrid=False, linecolor="#2d3148", tickfont=dict(size=10, color="#6b7280")),
    yaxis=dict(showgrid=True, gridcolor="#232634", zeroline=False, tickfont=dict(size=10, color="#6b7280")),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                font=dict(size=10, color="#9ca3af"), bgcolor="rgba(0,0,0,0)"),
    margin=dict(l=0, r=0, t=10, b=0),
    hovermode="x unified",
)

# ── Завантаження даних ────────────────────────────────────────────────────────
def _get_gspread_client():
    import gspread
    import json
    from google.oauth2 import service_account

    SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
              "https://www.googleapis.com/auth/drive.readonly"]

    # Streamlit Cloud: секція [gcp_service_account] в Secrets
    if "gcp_service_account" in st.secrets:
        info = dict(st.secrets["gcp_service_account"])
        creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        return gspread.authorize(creds)

    # env змінна (GitHub Actions / локально)
    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if sa_json:
        info = json.loads(sa_json)
        creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        return gspread.authorize(creds)

    # локальний OAuth token (розробка)
    token_path = "token.json"
    if os.path.exists(token_path):
        from src.connectors.ga4 import _get_credentials
        creds = _get_credentials()
        return gspread.authorize(creds)

    raise RuntimeError(
        "Не знайдено credentials. "
        "Додай [gcp_service_account] в Streamlit Secrets або GOOGLE_SERVICE_ACCOUNT_JSON в env."
    )

@st.cache_data(ttl=900, show_spinner=False)
def load_data():
    gc = _get_gspread_client()
    spr = gc.open_by_key(os.environ["GOOGLE_SHEETS_ID"])

    def sheet(tab):
        for name in [f"_data_{tab}", tab]:
            try:
                ws = spr.worksheet(name)
                vals = ws.get_all_values()
                if len(vals) < 4:
                    return pd.DataFrame()
                df = pd.DataFrame(vals[3:], columns=vals[2])
                return df[df.apply(lambda r: any(v.strip() for v in r), axis=1)]
            except Exception:
                continue
        return pd.DataFrame()

    def prep(df, *num_cols):
        if "week_start" in df.columns:
            df["week_start"] = pd.to_datetime(df["week_start"], format="%d.%m.%Y", errors="coerce")
        for c in num_cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
        return df

    traffic = prep(sheet("traffic_by_channel"), "sessions", "users", "pct_of_total")
    gsc     = prep(sheet("gsc_keywords"),       "total_clicks", "total_impressions", "avg_ctr", "avg_position")
    eng     = prep(sheet("engagement"),         "sessions", "users", "bounce_rate", "avg_session_duration")
    ads     = prep(sheet("ads_keywords"),       "total_clicks", "total_impressions", "avg_ctr", "total_cost_uah")
    meta    = prep(sheet("meta_ads"),           "impressions", "clicks", "ctr", "spend")
    matrix  = prep(sheet("product_matrix"),
                   "sessions", "users", "bounce_rate",
                   "organic_clicks", "organic_impressions", "organic_ctr",
                   "paid_clicks", "paid_cost_uah", "meta_clicks", "meta_spend")
    conv    = prep(sheet("conversions"),        "starts", "successes", "cr_pct")
    return traffic, gsc, eng, ads, meta, matrix, conv


# ── Хелпери ───────────────────────────────────────────────────────────────────
def fmt(n, suffix=""):
    n = float(n)
    if n >= 1_000_000: return f"{n/1_000_000:.1f}M{suffix}"
    if n >= 1_000:     return f"{n/1_000:.1f}K{suffix}"
    return f"{int(n)}{suffix}"

def fmt_uah(n):
    n = float(n)
    if n >= 1_000_000: return f"₴{n/1_000_000:.2f}M"
    if n >= 1_000:     return f"₴{n/1_000:.0f}K"
    return f"₴{int(n)}"

def delta_html(curr, prev):
    if prev == 0: return f'<span class="kpi-delta-neu">— немає даних попереднього</span>'
    pct = (curr - prev) / prev * 100
    cls = "kpi-delta-pos" if pct >= 0 else "kpi-delta-neg"
    arrow = "↑" if pct >= 0 else "↓"
    return f'<span class="{cls}">{arrow} {abs(pct):.1f}% vs попередній</span>'

def kpi_card(label, value, delta_html_str="", hint=""):
    parts = [
        f'<div class="kpi-card">',
        f'<div class="kpi-label">{label}</div>',
        f'<div class="kpi-value">{value}</div>',
    ]
    if delta_html_str:
        parts.append(f'<div>{delta_html_str}</div>')
    if hint:
        parts.append(f'<div style="font-size:0.72rem;color:{TEXT_MUT};margin-top:2px;">{hint}</div>')
    parts.append('</div>')
    st.markdown("\n".join(parts), unsafe_allow_html=True)

def filt(df, products, d_start, d_end):
    if df.empty: return df
    m = pd.Series(True, index=df.index)
    if "week_start" in df.columns:
        m &= (df["week_start"] >= pd.Timestamp(d_start)) & (df["week_start"] <= pd.Timestamp(d_end))
    if products and "Всі" not in products and "product" in df.columns:
        m &= df["product"].isin(products)
    return df[m].copy()

def progress_bar_cell(value, max_value, color=BLUE):
    if max_value == 0:
        return f'<span style="color:{TEXT_MUT}">0</span>'
    pct = min(value / max_value * 100, 100)
    return (
        f'<div style="display:flex;align-items:center;gap:8px;white-space:nowrap;">'
        f'<span style="min-width:44px;text-align:right;font-weight:600;color:{TEXT};">{fmt(value)}</span>'
        f'<div style="flex:1;min-width:60px;background:{BG3};border-radius:3px;height:5px;">'
        f'<div style="width:{pct:.1f}%;background:{color};border-radius:3px;height:5px;"></div>'
        f'</div>'
        f'<span style="min-width:36px;font-size:0.72rem;color:{TEXT_DIM};">{pct:.1f}%</span>'
        f'</div>'
    )

def num_pct_cell(value, total, color=TEXT):
    if total == 0:
        return f'<span style="color:{TEXT_MUT}">—</span>'
    pct = value / total * 100
    return (
        f'<span style="font-weight:600;color:{color};">{fmt(value)}</span>'
        f'<span style="color:{TEXT_MUT};font-size:0.75rem;margin-left:5px;">· {pct:.1f}%</span>'
    )

def sparkline(values, color=BLUE):
    vals = list(values)
    if len(vals) < 2 or max(vals) == 0:
        return ""
    mn, mx = min(vals), max(vals)
    rng = mx - mn if mx != mn else 1
    w, h = 80, 22
    pts = []
    for i, v in enumerate(vals):
        x = i / (len(vals) - 1) * w
        y = h - ((v - mn) / rng * (h - 4) + 2)
        pts.append(f"{x:.1f},{y:.1f}")
    path = " ".join(pts)
    return (f'<svg width="{w}" height="{h}" style="overflow:visible">'
            f'<polyline points="{path}" fill="none" stroke="{color}" stroke-width="1.5"/></svg>')

def html_table(rows_html, headers, widths=None):
    """Повертає HTML темної таблиці."""
    th_style = f"text-align:left;padding:8px 12px;color:{TEXT_DIM};font-size:0.71rem;text-transform:uppercase;font-weight:500;white-space:nowrap;"
    ths = "".join(
        f'<th style="{th_style}{"width:" + w + ";" if widths and w else ""}">{h}</th>'
        for h, w in zip(headers, widths or [""] * len(headers))
    )
    return (
        f'<html><body style="margin:0;background:{BG};font-family:-apple-system,BlinkMacSystemFont,sans-serif;">'
        f'<table style="width:100%;border-collapse:collapse;font-size:0.84rem;">'
        f'<thead><tr style="border-bottom:1px solid {BORDER};">{ths}</tr></thead>'
        f'<tbody>{rows_html}</tbody>'
        f'</table></body></html>'
    )

def tr(cells_html, i):
    bg = BG2 if i % 2 == 0 else BG
    return f'<tr style="background:{bg};border-bottom:1px solid {BORDER};">{cells_html}</tr>'

def td(content, align="left", mono=False, dim=False, bold=False):
    color = TEXT_DIM if dim else TEXT
    fw = "600" if bold else "400"
    ff = "font-family:monospace;" if mono else ""
    return f'<td style="padding:10px 12px;text-align:{align};color:{color};font-weight:{fw};{ff}">{content}</td>'

def td_num(content):
    return td(content, align="right")


# ── Завантаження ──────────────────────────────────────────────────────────────
with st.spinner("Завантаження даних…"):
    try:
        traffic, gsc, eng, ads, meta, matrix, conv = load_data()
    except Exception as e:
        st.error(f"Помилка завантаження: {e}")
        st.stop()

# Межі дат з даних
all_dates = pd.concat([
    df["week_start"] for df in [traffic, gsc] if not df.empty and "week_start" in df.columns
]).dropna()
data_min = all_dates.min().date()
data_max = all_dates.max().date()

all_products = sorted({
    p for df in [traffic, matrix] if not df.empty and "product" in df.columns
    for p in df["product"].dropna().unique()
})

# Всі тижні (понеділки)
all_weeks = sorted(all_dates.dt.normalize().unique())
all_week_labels = [w.strftime("%d.%m.%Y") for w in pd.to_datetime(all_weeks)]

# Всі місяці
all_months = sorted({w.to_period("M") for w in pd.to_datetime(all_weeks)})
all_month_labels = [m.strftime("%b %Y") for m in all_months]


# ══════════════════════════════════════════════════════════════════════════════
# ШАПКА
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(
    f'<div style="font-size:1.1rem;font-weight:700;color:{TEXT};margin-bottom:16px;">'
    f'monobank business · <span style="color:{BLUE};">Marketing Dashboard</span></div>',
    unsafe_allow_html=True,
)

# ── Фільтри ───────────────────────────────────────────────────────────────────
QUICK_RANGES = {
    "7д":    7,
    "28д":   28,
    "3міс":  90,
    "12міс": 365,
}

# Стан швидкого діапазону
if "quick_range" not in st.session_state:
    st.session_state.quick_range = "28д"

fr_cols = st.columns([3.5, 0.8, 1.5])

with fr_cols[0]:
    st.markdown(f'<div class="filter-label">Діапазон</div>', unsafe_allow_html=True)
    btn_cols = st.columns(len(QUICK_RANGES) + 1)
    for i, (label, days) in enumerate(QUICK_RANGES.items()):
        is_active = st.session_state.quick_range == label
        if btn_cols[i].button(
            label,
            key=f"qr_{label}",
            type="primary" if is_active else "secondary",
            use_container_width=True,
        ):
            st.session_state.quick_range = label
            st.rerun()
    if btn_cols[len(QUICK_RANGES)].button(
        "Свій",
        key="qr_custom",
        type="primary" if st.session_state.quick_range == "custom" else "secondary",
        use_container_width=True,
    ):
        st.session_state.quick_range = "custom"
        st.rerun()

with fr_cols[2]:
    st.markdown(f'<div class="filter-label">Продукти</div>', unsafe_allow_html=True)
    sel_products = st.multiselect("", ["Всі"] + all_products, default=["Всі"],
                                  label_visibility="collapsed", placeholder="Всі продукти")

# Обчислення дат
if st.session_state.quick_range == "custom":
    custom_range = st.date_input(
        "Оберіть діапазон",
        value=(data_max - timedelta(days=27), data_max),
        min_value=data_min,
        max_value=data_max,
        format="DD.MM.YYYY",
        label_visibility="collapsed",
    )
    if isinstance(custom_range, (list, tuple)) and len(custom_range) == 2:
        d_start, d_end = custom_range[0], custom_range[1]
    else:
        d_start = d_end = data_max
    period_label = f"{d_start.strftime('%d.%m.%Y')} – {d_end.strftime('%d.%m.%Y')}"
else:
    days = QUICK_RANGES[st.session_state.quick_range]
    d_end   = data_max
    d_start = (pd.Timestamp(data_max) - pd.Timedelta(days=days - 1)).date()
    period_label = st.session_state.quick_range

# Гранулярність для графіків — авто залежно від діапазону
period_days_total = (pd.Timestamp(d_end) - pd.Timestamp(d_start)).days + 1
granularity = "Місяць" if period_days_total > 60 else "Тиждень"

# Порівняння — окремий рядок з поясненням
cmp_col, info_col = st.columns([1, 4])
with cmp_col:
    compare = st.toggle("vs попередній період", value=False)
with info_col:
    if compare:
        period_days = (pd.Timestamp(d_end) - pd.Timestamp(d_start)).days + 1
        prev_end_dt   = pd.Timestamp(d_start) - pd.Timedelta(days=1)
        prev_start_dt = prev_end_dt - pd.Timedelta(days=period_days - 1)
        prev_start = prev_start_dt.date()
        prev_end   = prev_end_dt.date()
        st.markdown(
            f'<div style="font-size:0.78rem;color:{TEXT_DIM};padding-top:10px;">'
            f'▲ vs <b style="color:{TEXT_DIM};">{prev_start.strftime("%d.%m")} – {prev_end.strftime("%d.%m.%Y")}</b>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        prev_start = prev_end = d_start

st.markdown(f'<div class="divider"></div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# ВКЛАДКИ
# ══════════════════════════════════════════════════════════════════════════════
tabs = st.tabs(["Огляд", "Трафік", "Органіка", "Реклама", "Воронка", "Поведінка", "Матриця"])
tab_overview, tab_traffic, tab_organic, tab_paid, tab_funnel, tab_eng, tab_matrix = tabs


# ══════════════════════════════════════════════════════════════════════════════
# ОГЛЯД
# ══════════════════════════════════════════════════════════════════════════════
with tab_overview:
    tf = filt(traffic, sel_products, d_start, d_end)
    gf = filt(gsc,     sel_products, d_start, d_end)
    af = filt(ads,     sel_products, d_start, d_end)
    mf = filt(meta,    sel_products, d_start, d_end)
    ef = filt(eng,     sel_products, d_start, d_end)
    cf = filt(conv,    sel_products, d_start, d_end)

    sessions_cur    = int(tf["sessions"].sum())
    organic_cur     = int(gf["total_clicks"].sum())
    impressions_cur = int(gf["total_impressions"].sum())
    ad_spend_cur    = float(af["total_cost_uah"].sum()) + float(mf["spend"].sum())

    if compare:
        tf_p = filt(traffic, sel_products, prev_start, prev_end)
        gf_p = filt(gsc,     sel_products, prev_start, prev_end)
        af_p = filt(ads,     sel_products, prev_start, prev_end)
        mf_p = filt(meta,    sel_products, prev_start, prev_end)
        d1 = delta_html(sessions_cur,    int(tf_p["sessions"].sum()))
        d2 = delta_html(organic_cur,     int(gf_p["total_clicks"].sum()))
        d3 = delta_html(impressions_cur, int(gf_p["total_impressions"].sum()))
        d4 = delta_html(ad_spend_cur,    float(af_p["total_cost_uah"].sum()) + float(mf_p["spend"].sum()))
    else:
        d1 = d2 = d3 = d4 = ""

    ads_clicks_cur = int(af["total_clicks"].sum()) if not af.empty else 0
    cpc_cur = round(float(af["total_cost_uah"].sum()) / ads_clicks_cur, 1) if ads_clicks_cur > 0 else 0

    k1, k2, k3, k4 = st.columns(4)
    with k1: kpi_card("Сесії (GA4)",      fmt(sessions_cur),     d1, "відвідувань сайту · джерело GA4")
    with k2: kpi_card("Кліки з Google",   fmt(organic_cur),      d2, "переходів з пошуку Google · джерело GSC")
    with k3: kpi_card("Рекламний бюджет", fmt_uah(ad_spend_cur), d4, "витрачено · Google Ads + Meta Ads")
    with k4: kpi_card("CPC (Google Ads)", f"₴{cpc_cur}", "", "середня ціна за рекламний клік")

    # Рядок конверсій
    if not cf.empty:
        total_starts    = int(cf["starts"].sum())
        total_successes = int(cf["successes"].sum())
        cpl = round(float(af["total_cost_uah"].sum()) / total_successes, 0) if total_successes > 0 else 0
        avg_cr = round(total_successes / total_starts * 100, 1) if total_starts > 0 else 0

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1: kpi_card("Старти онбордингу", fmt(total_starts),    "", "людей почали відкриття рахунку · GA4")
        with c2: kpi_card("Успішних відкриттів", fmt(total_successes), "", "рахунок відкрито · ФОП + ЮО + Аванс")
        with c3: kpi_card("CR онбордингу",  f"{avg_cr}%",            "", "% що дійшли до кінця")
        with c4: kpi_card("CPL (Google Ads)", fmt_uah(cpl),           "", "витрат на одне відкриття рахунку")

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # Головний тренд
    st.markdown(f'<div class="sec-head">Трафік по тижнях</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sec-sub">{d_start.strftime("%d.%m.%Y")} — {d_end.strftime("%d.%m.%Y")} · GA4 сесії</div>', unsafe_allow_html=True)

    if not tf.empty:
        if granularity == "Місяць":
            tf["period"] = tf["week_start"].dt.to_period("M").dt.to_timestamp()
        else:
            tf["period"] = tf["week_start"]

        trend = tf.groupby(["period", "product"], as_index=False)["sessions"].sum()
        trend = trend[trend["sessions"] > 0]

        # попередній період для графіку
        trend_prev = pd.DataFrame()
        if compare:
            tf_p = filt(traffic, sel_products, prev_start, prev_end)
            if not tf_p.empty:
                if granularity == "Місяць":
                    tf_p["period"] = tf_p["week_start"].dt.to_period("M").dt.to_timestamp()
                else:
                    tf_p["period"] = tf_p["week_start"]
                # зсуваємо дати попереднього до поточного для накладання на той же графік
                offset = pd.Timestamp(d_start) - pd.Timestamp(prev_start)
                tf_p["period"] = tf_p["period"] + offset
                trend_prev = tf_p.groupby(["period", "product"], as_index=False)["sessions"].sum()
                trend_prev = trend_prev[trend_prev["sessions"] > 0]

        fig = go.Figure()
        products_ordered = trend.groupby("product")["sessions"].sum().sort_values(ascending=False).index
        for product in products_ordered:
            color = PRODUCT_COLORS.get(product, "#6b7280")
            d = trend[trend["product"] == product].sort_values("period")
            fig.add_trace(go.Scatter(
                x=d["period"], y=d["sessions"], name=product,
                mode="lines+markers",
                line=dict(color=color, width=2),
                marker=dict(size=5),
                hovertemplate=f"<b>{product}</b><br>%{{x|%d.%m.%Y}}<br>Сесії: %{{y:,}}<extra></extra>",
            ))
            if not trend_prev.empty and product in trend_prev["product"].values:
                dp = trend_prev[trend_prev["product"] == product].sort_values("period")
                fig.add_trace(go.Scatter(
                    x=dp["period"], y=dp["sessions"],
                    name=f"{product} (пред.)",
                    mode="lines",
                    line=dict(color=color, width=1.5, dash="dot"),
                    opacity=0.45,
                    showlegend=False,
                    hovertemplate=f"<b>{product} (пред.)</b><br>%{{x|%d.%m.%Y}}<br>Сесії: %{{y:,}}<extra></extra>",
                ))

        fig.update_layout(height=220, **PLOTLY_LAYOUT)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown(f'<div class="divider"></div>', unsafe_allow_html=True)

    # Таблиця по продуктах
    st.markdown(f'<div class="sec-head">По продуктах</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sec-sub">Сесії · Organic · CTR · Позиція · Реклама · Відмови · Тренд</div>', unsafe_allow_html=True)

    if not tf.empty:
        rows_data = []
        cp = filt(conv, sel_products, d_start, d_end) if not conv.empty else pd.DataFrame()
        for p in all_products:
            pf  = tf[tf["product"] == p] if "product" in tf.columns else pd.DataFrame()
            gp  = gf[gf["product"] == p] if not gf.empty and "product" in gf.columns else pd.DataFrame()
            ap  = af[af["product"] == p] if not af.empty and "product" in af.columns else pd.DataFrame()
            mp  = mf[mf["product"] == p] if not mf.empty and "product" in mf.columns else pd.DataFrame()
            ep  = ef[ef["product"] == p] if not ef.empty and "product" in ef.columns else pd.DataFrame()
            cvp = cp[cp["product"] == p] if not cp.empty and "product" in cp.columns else pd.DataFrame()
            sessions = int(pf["sessions"].sum()) if not pf.empty else 0
            if sessions == 0 and gp.empty and ap.empty and mp.empty:
                continue
            organic  = int(gp["total_clicks"].sum()) if not gp.empty else 0
            ctr      = float(gp["avg_ctr"].mean()) if not gp.empty and "avg_ctr" in gp.columns else None
            position = float(gp["avg_position"].mean()) if not gp.empty and "avg_position" in gp.columns else None
            ad_spend = (float(ap["total_cost_uah"].sum()) if not ap.empty else 0) + \
                       (float(mp["spend"].sum()) if not mp.empty else 0)
            bounce   = float(ep["bounce_rate"].mean()) if not ep.empty and "bounce_rate" in ep.columns and p not in SPA_PRODUCTS else None
            top_kw   = gp.sort_values("total_clicks", ascending=False)["top_keyword"].iloc[0] if not gp.empty and "top_keyword" in gp.columns else ""
            spark_vals = pf.groupby("week_start")["sessions"].sum().sort_index().values if not pf.empty else []
            p_successes = int(cvp["successes"].sum()) if not cvp.empty and "successes" in cvp.columns else 0
            p_starts    = int(cvp["starts"].sum())    if not cvp.empty and "starts"    in cvp.columns else 0
            p_cr   = round(p_successes / p_starts * 100, 1) if p_starts > 0 else None
            p_ads  = float(ap["total_cost_uah"].sum()) if not ap.empty else 0
            p_cpl  = round(p_ads / p_successes, 0) if p_successes > 0 and p_ads > 0 else None
            rows_data.append({"product": p, "sessions": sessions, "organic": organic,
                               "ctr": ctr, "position": position, "top_kw": top_kw,
                               "ad_spend": ad_spend, "bounce": bounce, "spark": spark_vals,
                               "cr": p_cr, "cpl": p_cpl})

        rows_data.sort(key=lambda r: r["sessions"], reverse=True)
        max_sess  = max((r["sessions"] for r in rows_data), default=1)
        max_org   = max((r["organic"]  for r in rows_data), default=1)

        def fmt_ctr(v):
            if v is None: return f'<span style="color:{TEXT_MUT}">—</span>'
            return f'<span style="color:{TEXT}">{v:.1f}%</span>'

        def fmt_pos(v):
            if v is None: return f'<span style="color:{TEXT_MUT}">—</span>'
            color = GREEN if v <= 3 else (TEXT if v <= 10 else TEXT_DIM)
            return f'<span style="color:{color};font-weight:600">{v:.1f}</span>'

        def fmt_bounce(v):
            if v is None: return f'<span style="color:{TEXT_MUT}">SPA</span>'
            color = GREEN if v < 25 else (ORANGE if v < 45 else RED)
            return f'<span style="color:{color};font-weight:600">{v:.0f}%</span>'

        def fmt_cr(v):
            if v is None: return f'<span style="color:{TEXT_MUT}">—</span>'
            color = GREEN if v >= 20 else (ORANGE if v >= 10 else RED)
            return f'<span style="color:{color};font-weight:600">{v:.1f}%</span>'

        def fmt_cpl(v):
            if v is None: return f'<span style="color:{TEXT_MUT}">—</span>'
            color = GREEN if v < 600 else (ORANGE if v < 1200 else RED)
            return f'<span style="color:{color};font-weight:600">₴{v:,.0f}</span>'

        rows_html = ""
        for i, r in enumerate(rows_data):
            color = PRODUCT_COLORS.get(r["product"], TEXT_DIM)
            spa   = f' <span style="font-size:0.62rem;color:{TEXT_MUT};">SPA</span>' if r["product"] in SPA_PRODUCTS else ""
            top_kw_cell = f'<span style="color:{TEXT_DIM};font-size:0.75rem;">{r["top_kw"]}</span>' if r["top_kw"] else f'<span style="color:{TEXT_MUT}">—</span>'
            rows_html += tr(
                f'<td style="padding:10px 12px;font-weight:700;color:{color};">{r["product"]}{spa}</td>'
                f'<td style="padding:10px 12px;">{progress_bar_cell(r["sessions"], max_sess, color)}</td>'
                f'<td style="padding:10px 12px;">{progress_bar_cell(r["organic"], max_org, GREEN)}</td>'
                f'<td style="padding:10px 12px;max-width:160px;">{top_kw_cell}</td>'
                f'<td style="padding:10px 12px;text-align:center;">{fmt_ctr(r["ctr"])}</td>'
                f'<td style="padding:10px 12px;text-align:center;">{fmt_pos(r["position"])}</td>'
                f'<td style="padding:10px 12px;text-align:right;color:{TEXT};white-space:nowrap;">{fmt_uah(r["ad_spend"])}</td>'
                f'<td style="padding:10px 12px;text-align:center;">{fmt_cr(r["cr"])}</td>'
                f'<td style="padding:10px 12px;text-align:center;">{fmt_cpl(r["cpl"])}</td>'
                f'<td style="padding:10px 12px;text-align:center;">{fmt_bounce(r["bounce"])}</td>'
                f'<td style="padding:10px 12px;text-align:center;">{sparkline(r["spark"], color)}</td>',
                i,
            )
        body = html_table(rows_html,
                          ["Продукт", "Сесії", "Organic", "Топ запит", "CTR", "Позиція", "Реклама ₴", "CR", "CPL", "Відмови", "Тренд"],
                          ["120px", "160px", "130px", "150px", "60px", "70px", "95px", "60px", "90px", "70px", "85px"])
        components.html(body, height=max(200, len(rows_data) * 54 + 60), scrolling=False)


# ══════════════════════════════════════════════════════════════════════════════
# ТРАФІК
# ══════════════════════════════════════════════════════════════════════════════
with tab_traffic:
    tf = filt(traffic, sel_products, d_start, d_end)

    if tf.empty:
        st.info("Немає даних за обраний період")
    else:
        total_s = int(tf["sessions"].sum())
        total_u = int(tf["users"].sum())
        top_ch  = tf.groupby("channel")["sessions"].sum().idxmax()
        top_pct = tf.groupby("channel")["sessions"].sum().max() / total_s * 100 if total_s > 0 else 0
        unass   = tf[tf["channel"] == "Unassigned"]["sessions"].sum() / total_s * 100 if total_s > 0 else 0

        k1, k2, k3, k4 = st.columns(4)
        with k1:
            d = delta_html(total_s, int(filt(traffic, sel_products, prev_start, prev_end)["sessions"].sum())) if compare else ""
            kpi_card("Сесії", fmt(total_s), d, "відвідувань сайту · GA4")
        with k2: kpi_card("Користувачі", fmt(total_u), "", "унікальних людей · GA4")
        with k3: kpi_card("Топ канал", top_ch, f'<span class="kpi-delta-neu">{top_pct:.0f}% трафіку</span>')
        with k4: kpi_card("Unassigned", f"{unass:.1f}%", f'<span class="kpi-delta-neu">трафік без UTM</span>', "переходи без розмітки — не знаємо звідки")

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        sub_t = st.tabs(["Канали", "Топ сторінок"])

        with sub_t[0]:
            col_l, col_r = st.columns([3, 2])
            if granularity == "Місяць":
                tf["period"] = tf["week_start"].dt.to_period("M").dt.to_timestamp()
            else:
                tf["period"] = tf["week_start"]

            with col_l:
                st.markdown(f'<div class="sec-head">Динаміка по каналах</div>', unsafe_allow_html=True)
                ch_week = tf.groupby(["period", "channel"], as_index=False)["sessions"].sum()
                fig = go.Figure()
                for ch in ch_week.groupby("channel")["sessions"].sum().sort_values(ascending=False).index:
                    d = ch_week[ch_week["channel"] == ch].sort_values("period")
                    fig.add_trace(go.Scatter(
                        x=d["period"], y=d["sessions"], name=ch, mode="lines",
                        stackgroup="one",
                        line=dict(color=CHANNEL_COLORS.get(ch, "#374151"), width=0),
                        fillcolor=CHANNEL_COLORS.get(ch, "#374151"),
                        hovertemplate=f"<b>{ch}</b>: %{{y:,}}<extra></extra>",
                    ))
                fig.update_layout(height=300, **PLOTLY_LAYOUT)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            with col_r:
                st.markdown(f'<div class="sec-head">Розподіл</div>', unsafe_allow_html=True)
                ch_tot = tf.groupby("channel", as_index=False)["sessions"].sum()
                ch_tot = ch_tot[ch_tot["sessions"] > 0].sort_values("sessions", ascending=False)
                fig2 = go.Figure(go.Bar(
                    x=ch_tot["sessions"], y=ch_tot["channel"], orientation="h",
                    marker_color=[CHANNEL_COLORS.get(c, "#374151") for c in ch_tot["channel"]],
                    text=[f"{v/total_s*100:.0f}%" for v in ch_tot["sessions"]],
                    textposition="outside",
                    textfont=dict(color="#9ca3af", size=10),
                    hovertemplate="<b>%{y}</b>: %{x:,}<extra></extra>",
                ))
                layout2 = {**PLOTLY_LAYOUT}
                layout2["xaxis"] = dict(showgrid=False, showticklabels=False)
                layout2["yaxis"] = dict(showgrid=False, tickfont=dict(size=11, color="#e5e7eb"))
                fig2.update_layout(height=300, **layout2)
                st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

            tbl_mode = st.radio(
                "Таблиця", ["Зведено", "По тижнях"],
                horizontal=True, label_visibility="collapsed",
                key="traffic_table_mode",
            )
            if tbl_mode == "Зведено":
                st.markdown(f'<div class="sec-head">Продукт × канал</div>', unsafe_allow_html=True)
                pivot = tf.groupby(["product", "channel"])["sessions"].sum().unstack(fill_value=0)
                pivot["Всього"] = pivot.sum(axis=1)
                pivot = pivot.sort_values("Всього", ascending=False)
                st.dataframe(pivot.style.format("{:,.0f}"), use_container_width=True)
            else:
                st.markdown(f'<div class="sec-head">Сесії по тижнях</div>', unsafe_allow_html=True)
                wt = tf.groupby(["week_start", "product"], as_index=False)["sessions"].sum()
                wt_pivot = wt.pivot(index="week_start", columns="product", values="sessions").fillna(0).astype(int)
                wt_pivot.index = wt_pivot.index.strftime("%d.%m.%Y")
                wt_pivot.index.name = "Тиждень"
                wt_pivot["Всього"] = wt_pivot.sum(axis=1)
                wt_pivot = wt_pivot.sort_index(ascending=False)
                st.dataframe(wt_pivot.style.format("{:,.0f}"), use_container_width=True)

            if unass > 3:
                st.markdown(f'<div class="note note-warn">⚠️ Unassigned {unass:.1f}% — посилання з Telegram/Viber, мобільний додаток, редіректи без UTM. Норма &lt;5%.</div>', unsafe_allow_html=True)

        with sub_t[1]:
            st.markdown(f'<div class="sec-head">Топ лендингів</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="sec-sub">Які сторінки отримують трафік і з яких каналів</div>', unsafe_allow_html=True)

            if "top_page" in tf.columns:
                pages = tf[tf["top_page"].notna() & (tf["top_page"] != "")].groupby(
                    ["top_page", "channel"], as_index=False)["sessions"].sum()
                pg_tot = pages.groupby("top_page")["sessions"].sum().reset_index()
                pg_tot = pg_tot.sort_values("sessions", ascending=False).head(30)
                max_pg  = int(pg_tot["sessions"].max()) if not pg_tot.empty else 1

                rows_html = ""
                for i, (_, pr) in enumerate(pg_tot.iterrows()):
                    pg_ch = pages[pages["top_page"] == pr["top_page"]].sort_values("sessions", ascending=False).head(3)
                    badges = "".join(
                        f'<span style="background:{CHANNEL_COLORS.get(r["channel"], BORDER)};color:#fff;'
                        f'font-size:0.62rem;padding:2px 7px;border-radius:10px;margin-right:3px;">'
                        f'{r["channel"].replace(" Search","").replace(" Ads","")}</span>'
                        for _, r in pg_ch.iterrows()
                    )
                    page_path = pr["top_page"]
                    page_url  = f"https://monobank.ua{page_path}" if page_path.startswith("/") else page_path
                    page_link = (
                        f'<a href="{page_url}" target="_blank" '
                        f'style="color:{BLUE};text-decoration:none;font-family:monospace;font-size:0.81rem;">'
                        f'{page_path}</a>'
                        f'<a href="{page_url}" target="_blank" '
                        f'style="color:{TEXT_MUT};margin-left:6px;font-size:0.78rem;">↗</a>'
                    )
                    rows_html += tr(
                        td(f'<span style="color:{TEXT_DIM};">{i+1}</span>', bold=False) +
                        f'<td style="padding:10px 12px;">{page_link}</td>' +
                        f'<td style="padding:10px 12px;">{progress_bar_cell(pr["sessions"], max_pg)}</td>' +
                        f'<td style="padding:10px 12px;">{badges}</td>',
                        i,
                    )
                components.html(
                    html_table(rows_html, ["#", "Сторінка", "Сесії", "Топ канали"], ["40px","","200px",""]),
                    height=max(200, len(pg_tot) * 54 + 60), scrolling=False,
                )
            else:
                st.info("Дані top_page недоступні")


# ══════════════════════════════════════════════════════════════════════════════
# ВОРОНКА
# ══════════════════════════════════════════════════════════════════════════════
with tab_funnel:
    cf_f = filt(conv, sel_products, d_start, d_end)
    tf_f = filt(traffic, sel_products, d_start, d_end)

    total_sessions_f = int(tf_f["sessions"].sum()) if not tf_f.empty else 0
    total_starts_f   = int(cf_f["starts"].sum())    if not cf_f.empty else 0
    total_success_f  = int(cf_f["successes"].sum()) if not cf_f.empty else 0
    cr_s2a = round(total_starts_f   / total_sessions_f * 100, 2) if total_sessions_f > 0 else 0
    cr_a2s = round(total_success_f  / total_starts_f   * 100, 1) if total_starts_f   > 0 else 0
    cr_total = round(total_success_f / total_sessions_f * 100, 2) if total_sessions_f > 0 else 0

    st.markdown(f'<div class="sec-head">Воронка онбордингу</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sec-sub">{d_start.strftime("%d.%m.%Y")} — {d_end.strftime("%d.%m.%Y")}</div>', unsafe_allow_html=True)

    # Funnel chart
    if total_sessions_f > 0:
        funnel_labels = ["Сесії сайту", "Старти онбордингу", "Відкриті рахунки"]
        funnel_values = [total_sessions_f, total_starts_f, total_success_f]
        funnel_colors = [BLUE, ORANGE, GREEN]

        fig_f = go.Figure(go.Funnel(
            y=funnel_labels,
            x=funnel_values,
            textposition="inside",
            textinfo="value+percent initial",
            opacity=0.9,
            marker=dict(color=funnel_colors),
            connector=dict(line=dict(color=BORDER, width=2)),
            textfont=dict(color="#fff", size=14),
        ))
        fig_f.update_layout(
            height=320,
            margin=dict(l=0, r=0, t=10, b=10),
            paper_bgcolor=BG2, plot_bgcolor=BG2,
            font=dict(color=TEXT, size=12),
        )
        st.plotly_chart(fig_f, use_container_width=True, config={"displayModeBar": False})

        # CR карточки під воронкою
        fa1, fa2, fa3, fa4 = st.columns(4)
        with fa1: kpi_card("Сесій",            fmt(total_sessions_f), "", "всього відвідувань")
        with fa2: kpi_card("Старти онбордингу", fmt(total_starts_f),  "", f"CR з сесій: {cr_s2a}%")
        with fa3: kpi_card("Відкрили рахунок",  fmt(total_success_f), "", f"CR зі старту: {cr_a2s}%")
        with fa4: kpi_card("Загальний CR",       f"{cr_total}%",       "", "сесія → відкритий рахунок")
    else:
        st.info("Немає даних за обраний період")

    # Воронка по продуктах
    if not cf_f.empty:
        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        st.markdown(f'<div class="sec-head">По продуктах</div>', unsafe_allow_html=True)

        prod_rows = []
        for p in cf_f["product"].unique():
            pp = cf_f[cf_f["product"] == p]
            starts = int(pp["starts"].sum())
            success = int(pp["successes"].sum())
            cr = round(success / starts * 100, 1) if starts > 0 else 0
            ap_p = filt(ads, [p], d_start, d_end)
            spend = float(ap_p["total_cost_uah"].sum()) if not ap_p.empty else 0
            cpl = round(spend / success, 0) if success > 0 and spend > 0 else None
            prod_rows.append({"product": p, "starts": starts, "success": success, "cr": cr, "spend": spend, "cpl": cpl})

        prod_rows.sort(key=lambda r: r["success"], reverse=True)
        max_st = max((r["starts"]  for r in prod_rows), default=1)
        max_su = max((r["success"] for r in prod_rows), default=1)

        rows_html = ""
        for i, r in enumerate(prod_rows):
            color = PRODUCT_COLORS.get(r["product"], TEXT_DIM)
            cr_color = GREEN if r["cr"] >= 20 else (ORANGE if r["cr"] >= 10 else RED)
            cpl_str = f'<span style="color:{GREEN if r["cpl"] and r["cpl"]<600 else (ORANGE if r["cpl"] and r["cpl"]<1200 else RED)};font-weight:600">₴{r["cpl"]:,.0f}</span>' if r["cpl"] else f'<span style="color:{TEXT_MUT}">—</span>'
            rows_html += tr(
                f'<td style="padding:10px 12px;font-weight:700;color:{color};">{r["product"]}</td>'
                f'<td style="padding:10px 12px;">{progress_bar_cell(r["starts"], max_st, ORANGE)}</td>'
                f'<td style="padding:10px 12px;">{progress_bar_cell(r["success"], max_su, GREEN)}</td>'
                f'<td style="padding:10px 12px;text-align:center;"><span style="color:{cr_color};font-weight:600">{r["cr"]:.1f}%</span></td>'
                f'<td style="padding:10px 12px;text-align:right;color:{TEXT};">{fmt_uah(r["spend"])}</td>'
                f'<td style="padding:10px 12px;text-align:center;">{cpl_str}</td>',
                i,
            )
        body_f = html_table(rows_html,
                            ["Продукт", "Старти онбордингу", "Відкрили рахунок", "CR", "Витрати Google Ads", "CPL"],
                            ["130px", "200px", "200px", "70px", "160px", "100px"])
        components.html(body_f, height=max(200, len(prod_rows) * 54 + 60), scrolling=False)

        # Тижнева динаміка воронки
        if not cf_f.empty and "week_start" in cf_f.columns:
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            st.markdown(f'<div class="sec-head">Динаміка по тижнях</div>', unsafe_allow_html=True)
            wf = cf_f.groupby("week_start", as_index=False)[["starts","successes"]].sum()
            wf = wf.sort_values("week_start")
            fig_fw = go.Figure()
            fig_fw.add_trace(go.Bar(
                x=wf["week_start"], y=wf["starts"], name="Старти",
                marker_color=ORANGE, opacity=0.7,
                hovertemplate="<b>Старти</b>: %{y:,}<extra></extra>",
            ))
            fig_fw.add_trace(go.Bar(
                x=wf["week_start"], y=wf["successes"], name="Відкриття",
                marker_color=GREEN,
                hovertemplate="<b>Відкриття</b>: %{y:,}<extra></extra>",
            ))
            fig_fw.update_layout(height=220, barmode="group", **PLOTLY_LAYOUT)
            st.plotly_chart(fig_fw, use_container_width=True, config={"displayModeBar": False})


# ══════════════════════════════════════════════════════════════════════════════
# ОРГАНІКА
# ══════════════════════════════════════════════════════════════════════════════
with tab_organic:
    gf = filt(gsc, sel_products, d_start, d_end)

    if gf.empty:
        st.info("Немає даних GSC за обраний період")
    else:
        total_clicks = int(gf["total_clicks"].sum())
        total_impr   = int(gf["total_impressions"].sum())
        avg_pos      = round(float(gf["avg_position"].mean()), 1)
        wctr         = round(total_clicks / total_impr * 100, 2) if total_impr > 0 else 0

        k1, k2, k3, k4 = st.columns(4)
        if compare:
            gp = filt(gsc, sel_products, prev_start, prev_end)
            with k1: kpi_card("Кліки з Google",  fmt(total_clicks), delta_html(total_clicks, int(gp["total_clicks"].sum())), "переходів з пошуку · GSC")
            with k2: kpi_card("Покази в Google", fmt(total_impr),   delta_html(total_impr,   int(gp["total_impressions"].sum())), "разів сайт з'явився в пошуку · GSC")
        else:
            with k1: kpi_card("Кліки з Google",  fmt(total_clicks), "", "переходів з пошуку · GSC")
            with k2: kpi_card("Покази в Google", fmt(total_impr),   "", "разів сайт з'явився в пошуку · GSC")
        with k3: kpi_card("CTR",      f"{wctr}%",   f'<span class="kpi-delta-neu">кліки / покази</span>', "% людей що клікнули побачивши сайт")
        with k4: kpi_card("Позиція",  f"{avg_pos}",  f'<span class="kpi-delta-neu">1 = перше місце</span>', "середня позиція в результатах пошуку")

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        sub_o = st.tabs(["По продуктах", "Всі запити"])

        # ── По продуктах ───────────────────────────────────────────────────────
        with sub_o[0]:
            col_l, col_r = st.columns([3, 2])

            with col_l:
                st.markdown(f'<div class="sec-head">Organic кліки по тижнях</div>', unsafe_allow_html=True)
                if granularity == "Місяць":
                    gf["period"] = gf["week_start"].dt.to_period("M").dt.to_timestamp()
                else:
                    gf["period"] = gf["week_start"]

                gw = gf.groupby(["period", "product"], as_index=False)["total_clicks"].sum()
                gw = gw[gw["total_clicks"] > 0]
                fig = go.Figure()
                for p in gw.groupby("product")["total_clicks"].sum().sort_values(ascending=False).index:
                    d = gw[gw["product"] == p].sort_values("period")
                    fig.add_trace(go.Scatter(
                        x=d["period"], y=d["total_clicks"], name=p, mode="lines+markers",
                        line=dict(color=PRODUCT_COLORS.get(p, "#6b7280"), width=2),
                        marker=dict(size=4),
                        hovertemplate=f"<b>{p}</b>: %{{y:,}}<extra></extra>",
                    ))
                fig.update_layout(height=300, **PLOTLY_LAYOUT)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            with col_r:
                st.markdown(f'<div class="sec-head">Позиція vs CTR</div>', unsafe_allow_html=True)
                st.caption("Ліворуч і вгору = краще")
                pa = gf.groupby("product", as_index=False).agg(
                    pos=("avg_position", "mean"), clicks=("total_clicks", "sum"), impr=("total_impressions", "sum"))
                pa["ctr"] = (pa["clicks"] / pa["impr"] * 100).round(1)
                pa = pa[pa["clicks"] > 0]
                fig2 = go.Figure()
                for _, row in pa.iterrows():
                    fig2.add_trace(go.Scatter(
                        x=[row["pos"]], y=[row["ctr"]], mode="markers+text",
                        name=row["product"], text=[row["product"]], textposition="top center",
                        textfont=dict(size=10, color="#9ca3af"),
                        marker=dict(size=max(10, row["clicks"] / pa["clicks"].max() * 32),
                                    color=PRODUCT_COLORS.get(row["product"], "#6b7280"), opacity=0.85),
                        hovertemplate=f"<b>{row['product']}</b><br>Позиція: {row['pos']:.1f}<br>CTR: {row['ctr']}%<extra></extra>",
                    ))
                layout_sc = {**PLOTLY_LAYOUT, "showlegend": False}
                layout_sc["xaxis"] = dict(autorange="reversed", title="Позиція ↑ краще",
                                          showgrid=True, gridcolor=BG3, tickfont=dict(size=10, color=TEXT_DIM))
                layout_sc["yaxis"] = dict(title="CTR %", showgrid=True, gridcolor=BG3,
                                          tickfont=dict(size=10, color=TEXT_DIM))
                fig2.update_layout(height=300, **layout_sc)
                st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

            st.markdown(f'<div class="sec-head">Пошукові запити по продукту</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="sec-sub">Топ запит · топ-5 запитів · кліки · CTR · позиція</div>', unsafe_allow_html=True)

            kw = gf.groupby(["product", "top_keyword", "top_keywords"], as_index=False).agg(
                clicks=("total_clicks", "sum"), impr=("total_impressions", "sum"), pos=("avg_position", "mean"))
            kw["ctr"] = (kw["clicks"] / kw["impr"] * 100).round(1)
            kw["pos"] = kw["pos"].round(1)
            kw = kw[kw["top_keyword"] != ""].sort_values("clicks", ascending=False)
            max_kw = int(kw["clicks"].max()) if not kw.empty else 1

            def keyword_tags(keywords_str, top_keyword):
                if not keywords_str:
                    return f'<span style="color:{TEXT_DIM};font-size:0.8rem;">{top_keyword}</span>'
                tags = [k.strip() for k in str(keywords_str).split(",") if k.strip()]
                html = ""
                for tag in tags[:5]:
                    is_top = tag == top_keyword
                    bg = BG3 if not is_top else "#1e3a5f"
                    border = BORDER if not is_top else "#3b82f6"
                    color = TEXT if not is_top else BLUE
                    html += (
                        f'<span style="display:inline-block;margin:2px 3px 2px 0;padding:2px 8px;'
                        f'background:{bg};border:1px solid {border};border-radius:10px;'
                        f'font-size:0.72rem;color:{color};white-space:nowrap;">{tag}</span>'
                    )
                return html

            rows_html = ""
            for i, (_, row) in enumerate(kw.iterrows()):
                color = PRODUCT_COLORS.get(row["product"], TEXT_DIM)
                top_kw = row.get("top_keyword", "")
                top_kws = row.get("top_keywords", "")
                rows_html += tr(
                    f'<td style="padding:10px 12px;font-weight:700;color:{color};white-space:nowrap;">{row["product"]}</td>' +
                    f'<td style="padding:10px 14px;max-width:340px;">{keyword_tags(top_kws, top_kw)}</td>' +
                    f'<td style="padding:10px 12px;">{progress_bar_cell(row["clicks"], max_kw, color)}</td>' +
                    td_num(f'{row["ctr"]}%') + td_num(str(row["pos"])),
                    i,
                )
            components.html(
                html_table(rows_html, ["Продукт", "Запити (топ-5)", "Кліки", "CTR %", "Позиція"],
                           ["120px", "", "200px", "80px", "80px"]),
                height=max(200, len(kw) * 60 + 60), scrolling=False,
            )

        # ── Всі запити ─────────────────────────────────────────────────────────
        with sub_o[1]:
            st.markdown(f'<div class="sec-head">Всі пошукові запити</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="sec-sub">Кожен рядок = product × тип запиту · з трендом кліків за обраний період</div>', unsafe_allow_html=True)

            # top_page береться як перше унікальне значення для групи
            page_map = {}
            if "top_page" in gf.columns:
                for (prod, ktype), grp in gf.groupby(["product", "keyword_type"]):
                    pages_vals = grp["top_page"].dropna().unique()
                    page_map[(prod, ktype)] = pages_vals[0] if len(pages_vals) > 0 else ""

            all_q = gf.groupby(["product", "keyword_type", "top_keyword"], as_index=False).agg(
                clicks=("total_clicks", "sum"), impr=("total_impressions", "sum"), pos=("avg_position", "mean"))
            all_q["ctr"] = (all_q["clicks"] / all_q["impr"] * 100).round(1)
            all_q["pos"] = all_q["pos"].round(1)
            all_q = all_q[all_q["top_keyword"] != ""].sort_values("clicks", ascending=False)

            trend_map = {}
            if "week_start" in gf.columns:
                for (prod, ktype), grp in gf.groupby(["product", "keyword_type"]):
                    trend_map[(prod, ktype)] = grp.groupby("week_start")["total_clicks"].sum().sort_index().values

            max_q = int(all_q["clicks"].max()) if not all_q.empty else 1

            rows_html = ""
            for i, (_, row) in enumerate(all_q.iterrows()):
                color = PRODUCT_COLORS.get(row["product"], TEXT_DIM)
                ktype = row["keyword_type"]
                badge_bg = BLUE if ktype == "branded" else GREEN
                badge    = (f'<span style="background:{badge_bg};color:#fff;font-size:0.62rem;'
                            f'padding:2px 7px;border-radius:10px;">{"branded" if ktype=="branded" else "non-brand"}</span>')
                spark    = sparkline(trend_map.get((row["product"], ktype), []), color)
                page_path = page_map.get((row["product"], ktype), "")
                if page_path:
                    page_url  = f"https://monobank.ua{page_path}" if page_path.startswith("/") else page_path
                    page_cell = (f'<a href="{page_url}" target="_blank" '
                                 f'style="color:{BLUE};text-decoration:none;font-family:monospace;font-size:0.79rem;">'
                                 f'{page_path}</a>'
                                 f'<a href="{page_url}" target="_blank" '
                                 f'style="color:{TEXT_MUT};margin-left:4px;font-size:0.75rem;">↗</a>')
                else:
                    page_cell = f'<span style="color:{TEXT_MUT};">—</span>'
                rows_html += tr(
                    td(f'<span style="color:{TEXT_MUT};">{i+1}</span>') +
                    f'<td style="padding:10px 12px;font-weight:700;color:{color};">{row["product"]}</td>' +
                    f'<td style="padding:10px 12px;">{badge}</td>' +
                    td(row["top_keyword"]) +
                    f'<td style="padding:10px 12px;">{page_cell}</td>' +
                    f'<td style="padding:10px 12px;">{progress_bar_cell(row["clicks"], max_q, color)}</td>' +
                    td_num(fmt(row["impr"])) +
                    td_num(f'{row["ctr"]}%') +
                    td_num(str(row["pos"])) +
                    f'<td style="padding:10px 12px;text-align:center;">{spark}</td>',
                    i,
                )
            components.html(
                html_table(rows_html,
                           ["#","Продукт","Тип","Топ запит","Лендинг","Кліки","Покази","CTR %","Позиція","Тренд"],
                           ["40px","120px","100px","","","180px","70px","65px","65px","90px"]),
                height=max(200, len(all_q) * 54 + 60), scrolling=False,
            )


# ══════════════════════════════════════════════════════════════════════════════
# РЕКЛАМА
# ══════════════════════════════════════════════════════════════════════════════
with tab_paid:
    af = filt(ads,  sel_products, d_start, d_end)
    mf = filt(meta, sel_products, d_start, d_end)

    ads_spend   = float(af["total_cost_uah"].sum()) if not af.empty else 0
    meta_spend  = float(mf["spend"].sum())          if not mf.empty else 0
    ads_clicks  = int(af["total_clicks"].sum())     if not af.empty else 0
    meta_clicks = int(mf["clicks"].sum())           if not mf.empty else 0

    k1, k2, k3, k4 = st.columns(4)
    with k1: kpi_card("Google Ads бюджет",  fmt_uah(ads_spend),  "", "витрачено на пошукову рекламу")
    with k2: kpi_card("Meta Ads бюджет",    fmt_uah(meta_spend), "", "витрачено на рекламу в соцмережах")
    with k3: kpi_card("Google Ads кліки",   fmt(ads_clicks),     f'<span class="kpi-delta-neu">рекламні кліки</span>', "кліки по платних оголошеннях")
    with k4: kpi_card("Meta кліки",         fmt(meta_clicks),    f'<span class="kpi-delta-neu">App Opens + Link Clicks</span>', "≠ GA4 сесії, різна методологія")

    st.markdown(f'<div class="note note-info">ℹ️ Meta "кліки" = App Opens + Link Clicks — не порівнюй напряму з GA4 сесіями.</div>', unsafe_allow_html=True)

    col_l, col_r = st.columns(2)

    with col_l:
        st.markdown(f'<div class="sec-head">Google Ads · витрати по продуктах</div>', unsafe_allow_html=True)
        if not af.empty:
            ap = af.groupby("product", as_index=False).agg(cost=("total_cost_uah","sum"), clicks=("total_clicks","sum"))
            # landing_url — беремо перший для продукту
            if "landing_url" in af.columns:
                landing = af[af["landing_url"].notna() & (af["landing_url"] != "")].groupby("product")["landing_url"].first().reset_index()
                ap = ap.merge(landing, on="product", how="left")
            else:
                ap["landing_url"] = ""
            ap = ap[ap["cost"] > 0].sort_values("cost", ascending=True)
            ap["cpc"] = (ap["cost"] / ap["clicks"].replace(0, 1)).round(0)

            fig = go.Figure(go.Bar(
                x=ap["cost"], y=ap["product"], orientation="h",
                marker_color=[PRODUCT_COLORS.get(p, "#6b7280") for p in ap["product"]],
                text=[f"₴{v:,.0f}" for v in ap["cost"]],
                textposition="outside", textfont=dict(color="#9ca3af", size=10),
                hovertemplate="<b>%{y}</b>: ₴%{x:,.0f}<extra></extra>",
            ))
            layout_bar = {**PLOTLY_LAYOUT}
            layout_bar["xaxis"] = dict(showgrid=False, showticklabels=False)
            layout_bar["yaxis"] = dict(showgrid=False, tickfont=dict(size=11, color=TEXT))
            fig.update_layout(height=260, **layout_bar)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            cpc_rows = ""
            for i, (_, r) in enumerate(ap.sort_values("cost", ascending=False).iterrows()):
                color = PRODUCT_COLORS.get(r["product"], TEXT_DIM)
                url   = r.get("landing_url", "")
                if url and isinstance(url, str) and url.startswith("http"):
                    url_cell = (f'<a href="{url}" target="_blank" '
                                f'style="color:{BLUE};text-decoration:none;font-size:0.79rem;">'
                                f'{url.replace("https://","").rstrip("/")}</a>'
                                f'<a href="{url}" target="_blank" '
                                f'style="color:{TEXT_MUT};margin-left:4px;font-size:0.75rem;">↗</a>')
                else:
                    url_cell = f'<span style="color:{TEXT_MUT};">—</span>'
                cpc_rows += tr(
                    f'<td style="padding:9px 12px;font-weight:700;color:{color};">{r["product"]}</td>' +
                    td_num(f'{int(r["clicks"]):,}') +
                    td_num(f'₴{int(r["cost"]):,}') +
                    td_num(f'₴{int(r["cpc"])}') +
                    f'<td style="padding:9px 12px;">{url_cell}</td>',
                    i,
                )
            components.html(
                html_table(cpc_rows, ["Продукт","Кліки","Витрати","CPC","Лендинг"],
                           ["120px","80px","90px","70px",""]),
                height=max(120, len(ap) * 50 + 56), scrolling=False,
            )

    with col_r:
        st.markdown(f'<div class="sec-head">Meta Ads · витрати по продуктах</div>', unsafe_allow_html=True)
        if not mf.empty:
            mp = mf.groupby("product", as_index=False).agg(spend=("spend","sum"), clicks=("clicks","sum"))
            mp = mp[mp["spend"] > 0].sort_values("spend", ascending=True)

            fig2 = go.Figure(go.Bar(
                x=mp["spend"], y=mp["product"], orientation="h",
                marker_color=[PRODUCT_COLORS.get(p, "#6b7280") for p in mp["product"]],
                text=[f"₴{v:,.0f}" for v in mp["spend"]],
                textposition="outside", textfont=dict(color="#9ca3af", size=10),
                hovertemplate="<b>%{y}</b>: ₴%{x:,.0f}<extra></extra>",
            ))
            fig2.update_layout(height=260, **layout_bar)
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

            ct = mf.groupby(["product","campaign_type"], as_index=False)["spend"].sum()
            ct = ct[ct["spend"] > 0]
            fig3 = px.bar(ct, x="product", y="spend", color="campaign_type", barmode="stack",
                          color_discrete_map={"app_install": BLUE, "lead_form": ORANGE, "traffic": GREEN},
                          labels={"spend":"₴","product":"","campaign_type":"Тип"})
            fig3.update_layout(height=180, plot_bgcolor=BG2, paper_bgcolor=BG,
                               margin=dict(l=0,r=0,t=4,b=0),
                               font=dict(color="#9ca3af",size=10),
                               legend=dict(orientation="h",y=1.01,x=0,font=dict(size=10),bgcolor="rgba(0,0,0,0)"),
                               xaxis=dict(showgrid=False,tickfont=dict(color=TEXT)),
                               yaxis=dict(showgrid=True,gridcolor=BG3))
            st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})

    # Тренд витрат
    st.markdown(f'<div class="sec-head">Динаміка витрат по тижнях</div>', unsafe_allow_html=True)
    spend_rows = []
    if not af.empty:
        for (w, p), g in af.groupby(["week_start","product"]):
            spend_rows.append({"week": w, "product": p, "source": "Google Ads", "spend": g["total_cost_uah"].sum()})
    if not mf.empty:
        for (w, p), g in mf.groupby(["week_start","product"]):
            spend_rows.append({"week": w, "product": p, "source": "Meta Ads", "spend": g["spend"].sum()})

    if spend_rows:
        sdf = pd.DataFrame(spend_rows)
        sdf = sdf[sdf["spend"] > 0]
        fig4 = px.line(sdf, x="week", y="spend", color="product", line_dash="source",
                       color_discrete_map=PRODUCT_COLORS, markers=True,
                       labels={"week":"","spend":"₴","product":"Продукт","source":"Канал"})
        fig4.update_layout(height=280, plot_bgcolor=BG2, paper_bgcolor=BG,
                           margin=dict(l=0,r=0,t=4,b=0), hovermode="x unified",
                           font=dict(color="#9ca3af",size=10),
                           legend=dict(orientation="h",y=1.02,x=0,font=dict(size=10),bgcolor="rgba(0,0,0,0)"),
                           xaxis=dict(showgrid=False,linecolor=BORDER,tickfont=dict(size=10,color=TEXT_DIM)),
                           yaxis=dict(showgrid=True,gridcolor=BG3,tickfont=dict(size=10,color=TEXT_DIM)))
        st.plotly_chart(fig4, use_container_width=True, config={"displayModeBar": False})


# ══════════════════════════════════════════════════════════════════════════════
# ПОВЕДІНКА
# ══════════════════════════════════════════════════════════════════════════════
with tab_eng:
    ef = filt(eng, sel_products, d_start, d_end)
    non_spa = ef[~ef["product"].isin(SPA_PRODUCTS)] if not ef.empty else pd.DataFrame()

    st.markdown(
        f'<div class="note note-info">ℹ️ Дані лише для <b>Еквайринг і ФОП</b> (лендинги). '
        f'<b>ЮО, ЗП-проект, Аванс, Пакети, Частинами</b> — це SPA всередині web.monobank.ua: '
        f'GA4 не бачить окремих сторінок, тому bounce rate і тривалість технічно неможливо виміряти.</div>',
        unsafe_allow_html=True,
    )

    if not non_spa.empty:
        avg_br  = round(float(non_spa["bounce_rate"].mean()), 1)
        avg_dur = round(float(non_spa["avg_session_duration"].mean()) / 60, 1)
        k1, k2 = st.columns(2)
        with k1: kpi_card("Середній bounce rate", f"{avg_br}%", f'<span class="kpi-delta-neu">Еквайринг + ФОП</span>')
        with k2: kpi_card("Середня тривалість сесії", f"{avg_dur} хв")

        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
        col_l, col_r = st.columns(2)

        layout_br = {**PLOTLY_LAYOUT}
        layout_br["xaxis"] = dict(showgrid=False, showticklabels=False)
        layout_br["yaxis"] = dict(showgrid=False, tickfont=dict(size=11, color=TEXT))

        br = non_spa.groupby("product", as_index=False)["bounce_rate"].mean().round(1)
        br = br[br["bounce_rate"] > 0].sort_values("bounce_rate")
        dur = non_spa.groupby("product", as_index=False)["avg_session_duration"].mean()
        dur["minutes"] = (dur["avg_session_duration"] / 60).round(1)
        dur = dur[dur["minutes"] > 0].sort_values("minutes")

        _multi_product = len(br) >= 2

        with col_l:
            st.markdown(f'<div class="sec-head">Відсоток відмов</div>', unsafe_allow_html=True)
            st.caption("Людина зайшла і одразу пішла. Менше = краще.")
            if _multi_product:
                fig = go.Figure(go.Bar(
                    x=br["bounce_rate"], y=br["product"], orientation="h",
                    marker_color=[PRODUCT_COLORS.get(p, "#6b7280") for p in br["product"]],
                    text=[f"{v:.1f}%" for v in br["bounce_rate"]],
                    textposition="outside", textfont=dict(color="#9ca3af", size=10),
                ))
                fig.add_vline(x=40, line_dash="dot", line_color=RED,
                              annotation_text="⚠️ 40%", annotation_font_color=RED)
                fig.update_layout(height=240, **layout_br)
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("Оберіть кілька продуктів у фільтрі щоб порівняти")

        with col_r:
            st.markdown(f'<div class="sec-head">Тривалість сесії (хв)</div>', unsafe_allow_html=True)
            st.caption("Скільки часу проводить користувач. Більше = краще.")
            if _multi_product:
                fig2 = go.Figure(go.Bar(
                    x=dur["minutes"], y=dur["product"], orientation="h",
                    marker_color=[PRODUCT_COLORS.get(p, "#6b7280") for p in dur["product"]],
                    text=[f"{v:.1f} хв" for v in dur["minutes"]],
                    textposition="outside", textfont=dict(color="#9ca3af", size=10),
                ))
                fig2.update_layout(height=240, **layout_br)
                st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
            else:
                st.info("Оберіть кілька продуктів у фільтрі щоб порівняти")

        st.markdown(f'<div class="sec-head">Динаміка відмов по тижнях</div>', unsafe_allow_html=True)
        br_w = non_spa.groupby(["week_start","product"], as_index=False)["bounce_rate"].mean().round(1)
        br_w = br_w[br_w["bounce_rate"] > 0]
        fig3 = go.Figure()
        for p in br_w["product"].unique():
            d = br_w[br_w["product"] == p].sort_values("week_start")
            fig3.add_trace(go.Scatter(
                x=d["week_start"], y=d["bounce_rate"], name=p, mode="lines+markers",
                line=dict(color=PRODUCT_COLORS.get(p, "#6b7280"), width=2), marker=dict(size=4),
            ))
        fig3.add_hline(y=40, line_dash="dot", line_color=RED,
                       annotation_text="⚠️ 40%", annotation_font_color=RED)
        fig3.update_layout(height=260, **PLOTLY_LAYOUT)
        st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})


# ══════════════════════════════════════════════════════════════════════════════
# МАТРИЦЯ
# ══════════════════════════════════════════════════════════════════════════════
with tab_matrix:
    mxf = filt(matrix, sel_products, d_start, d_end)

    if mxf.empty:
        st.info("Немає даних за обраний період")
    else:
        prod_s = mxf.groupby("product", as_index=False).agg(
            sessions=("sessions","sum"), users=("users","sum"),
            organic_clicks=("organic_clicks","sum"),
            paid_clicks=("paid_clicks","sum"), paid_cost=("paid_cost_uah","sum"),
            meta_clicks=("meta_clicks","sum"), meta_spend=("meta_spend","sum"),
            bounce_rate=("bounce_rate","mean"),
        ).round({"bounce_rate":1,"paid_cost":0,"meta_spend":0})
        prod_s["total_spend"] = prod_s["paid_cost"] + prod_s["meta_spend"]

        st.markdown(f'<div class="sec-head">Повний маркетинговий портрет по продуктах</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="sec-sub">{d_start.strftime("%d.%m.%Y")} — {d_end.strftime("%d.%m.%Y")}</div>', unsafe_allow_html=True)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        cols = st.columns(min(len(prod_s), 4))
        for i, (_, r) in enumerate(prod_s.sort_values("sessions", ascending=False).iterrows()):
            c = PRODUCT_COLORS.get(r["product"], TEXT_DIM)
            spa = f' <span style="font-size:0.68rem;color:{TEXT_MUT};"> · SPA</span>' if r["product"] in SPA_PRODUCTS else ""
            with cols[i % 4]:
                st.markdown(f"""
                <div style="background:{BG2};border:1px solid {BORDER};border-top:3px solid {c};
                            border-radius:8px;padding:14px 16px;margin-bottom:12px;">
                    <div style="font-weight:700;font-size:0.88rem;color:{TEXT};">{r['product']}{spa}</div>
                    <div style="font-size:1.5rem;font-weight:700;color:{c};margin:6px 0;">{"SPA — немає" if r["product"] in SPA_PRODUCTS and r["sessions"] == 0 else fmt(r["sessions"])}</div>
                    <div style="font-size:0.75rem;color:{TEXT_DIM};line-height:1.8;">
                        🔍 {fmt(r['organic_clicks'])} organic<br>
                        💰 {fmt_uah(r['total_spend'])} реклама
                    </div>
                    {"" if r["product"] not in SPA_PRODUCTS else f'<div style="font-size:0.68rem;color:{TEXT_MUT};margin-top:4px;">GA4-сесії SPA-продуктів не вимірюються</div>'}
                </div>""", unsafe_allow_html=True)

        st.markdown(f'<div class="divider"></div>', unsafe_allow_html=True)

        # Bubble chart
        st.markdown(f'<div class="sec-head">Organic кліки vs Рекламний бюджет</div>', unsafe_allow_html=True)
        st.caption("Розмір кола = сесії GA4 · ідеал: правий нижній кут (багато organic, мало платить)")
        bdf = prod_s[(prod_s["organic_clicks"] > 0) | (prod_s["total_spend"] > 0)].copy()
        if not bdf.empty:
            fig = go.Figure()
            for _, row in bdf.iterrows():
                fig.add_trace(go.Scatter(
                    x=[row["organic_clicks"]], y=[row["total_spend"]],
                    mode="markers+text", name=row["product"],
                    text=[row["product"]], textposition="top center",
                    textfont=dict(size=10, color="#9ca3af"),
                    marker=dict(size=max(14, row["sessions"] / max(bdf["sessions"].max(),1) * 52),
                                color=PRODUCT_COLORS.get(row["product"],"#6b7280"),
                                opacity=0.8, line=dict(width=1, color=BG)),
                    hovertemplate=(f"<b>{row['product']}</b><br>Organic: {row['organic_clicks']:,.0f}<br>"
                                   f"Реклама: ₴{row['total_spend']:,.0f}<br>Сесії: {row['sessions']:,.0f}<extra></extra>"),
                ))
            layout_bub = {**PLOTLY_LAYOUT, "showlegend": False}
            layout_bub["xaxis"] = dict(title="Organic кліки (GSC)", showgrid=True, gridcolor=BG3, tickfont=dict(size=10,color=TEXT_DIM))
            layout_bub["yaxis"] = dict(title="Рекламний бюджет ₴",  showgrid=True, gridcolor=BG3, tickfont=dict(size=10,color=TEXT_DIM))
            fig.update_layout(height=360, **layout_bub)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # Детальна таблиця
        st.markdown(f'<div class="sec-head">Детальна таблиця</div>', unsafe_allow_html=True)
        tbl = prod_s.sort_values("sessions", ascending=False)
        max_sess_mx    = int(tbl["sessions"].max()) if len(tbl) > 0 else 1
        total_org_mx   = int(tbl["organic_clicks"].sum())
        total_paid_mx  = float(tbl["paid_cost"].sum())
        total_meta_mx  = float(tbl["meta_spend"].sum())
        total_pc_mx    = float(tbl["paid_clicks"].sum())

        rows_html = ""
        for i, (_, r) in enumerate(tbl.iterrows()):
            color = PRODUCT_COLORS.get(r["product"], TEXT_DIM)
            spa_note = f' <span style="font-size:0.62rem;color:{TEXT_MUT};">SPA</span>' if r["product"] in SPA_PRODUCTS else ""
            br_cell  = f'{r["bounce_rate"]:.1f}%' if r["bounce_rate"] > 0 else f'<span style="color:{TEXT_MUT};">SPA</span>'
            rows_html += tr(
                f'<td style="padding:10px 12px;font-weight:700;color:{color};">{r["product"]}{spa_note}</td>' +
                f'<td style="padding:10px 12px;">{progress_bar_cell(r["sessions"], max_sess_mx, color)}</td>' +
                f'<td style="padding:10px 12px;text-align:right;">{num_pct_cell(r["organic_clicks"], total_org_mx, GREEN)}</td>' +
                f'<td style="padding:10px 12px;text-align:right;">{num_pct_cell(r["paid_clicks"], total_pc_mx, "#f59e0b")}</td>' +
                f'<td style="padding:10px 12px;text-align:right;">{num_pct_cell(r["paid_cost"], total_paid_mx, "#f59e0b")}</td>' +
                f'<td style="padding:10px 12px;text-align:right;">{num_pct_cell(r["meta_spend"], total_meta_mx, ORANGE)}</td>' +
                f'<td style="padding:10px 12px;text-align:right;color:{TEXT};">{br_cell}</td>',
                i,
            )
        components.html(
            html_table(rows_html,
                       ["Продукт","Сесії","Organic · %","Ads кліки · %","Google Ads ₴ · %","Meta ₴ · %","Відмови"],
                       ["140px","200px","","","","",""]),
            height=max(200, len(tbl) * 54 + 60), scrolling=False,
        )


# ── Футер ─────────────────────────────────────────────────────────────────────
st.markdown(
    f"<hr style='border-color:{BORDER};margin-top:32px;'>"
    f"<p style='text-align:center;font-size:0.72rem;color:{TEXT_MUT};padding:8px 0;'>"
    f"monobank business · internal · GA4 + GSC + Google Ads + Meta Ads"
    f"</p>",
    unsafe_allow_html=True,
)
