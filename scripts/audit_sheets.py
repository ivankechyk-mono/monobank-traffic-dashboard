"""
Аудит данных в Google Sheets.
Читает каждую таблицу, проверяет логику и записывает проблемы.
Запуск: python3.11 scripts/audit_sheets.py
"""
import os
import sys
from pathlib import Path

# Добавляем корень проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import gspread
import json
import pandas as pd
from google.oauth2.credentials import Credentials

SHEET_ID = os.getenv("GOOGLE_SHEETS_ID")
TOKEN_PATH = Path(__file__).parent.parent / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

TABS = [
    "traffic_by_channel",
    "gsc_keywords",
    "engagement",
    "ads_keywords",
    "meta_ads",
    "product_matrix",
]

issues = []  # список найденных проблем


def log(msg):
    print(msg)


def issue(tab, problem, detail="", rows=None):
    entry = {"tab": tab, "problem": problem, "detail": detail}
    if rows:
        entry["rows"] = rows
    issues.append(entry)
    marker = "  [ПРОБЛЕМА]"
    print(f"{marker} {tab}: {problem}")
    if detail:
        print(f"           {detail}")
    if rows:
        for r in rows[:5]:
            print(f"           -> {r}")
        if len(rows) > 5:
            print(f"           ... и ещё {len(rows)-5} строк")


def get_credentials():
    from src.connectors.ga4 import _get_credentials
    return _get_credentials()


def read_tab(spreadsheet, tab_name):
    """Читает лист, пропуская 3 строки заголовка (dropdown, пустая, headers)."""
    # Пробуем сначала _data_ версию (months filter архитектура)
    for name in [f"_data_{tab_name}", tab_name]:
        try:
            ws = spreadsheet.worksheet(name)
            all_vals = ws.get_all_values()
            log(f"\n{'='*60}")
            log(f"Лист: {name} | Всего строк в файле: {len(all_vals)}")
            if len(all_vals) < 3:
                issue(tab_name, "Лист пустой или нет заголовков", f"Строк: {len(all_vals)}")
                return None, name
            headers = all_vals[2]  # строка 3 — заголовки
            data_rows = all_vals[3:]  # строка 4+ — данные
            log(f"  Заголовки ({len(headers)}): {headers}")
            log(f"  Строк данных: {len(data_rows)}")
            if not data_rows:
                issue(tab_name, "Нет строк с данными", f"Заголовки есть, но данных нет")
                return None, name
            df = pd.DataFrame(data_rows, columns=headers)
            # Убираем полностью пустые строки
            df = df[df.apply(lambda r: any(v.strip() for v in r.astype(str)), axis=1)]
            log(f"  Строк после фильтра пустых: {len(df)}")
            return df, name
        except gspread.exceptions.WorksheetNotFound:
            continue
    issue(tab_name, "Лист не найден в spreadsheet")
    return None, tab_name


def check_numeric(df, tab, col, min_val=None, max_val=None):
    """Проверяет что колонка числовая и в разумных пределах."""
    if col not in df.columns:
        issue(tab, f"Отсутствует колонка", col)
        return
    vals = pd.to_numeric(df[col].replace("", pd.NA), errors="coerce")
    non_numeric = df[col][vals.isna() & df[col].notna() & (df[col] != "")].tolist()
    if non_numeric:
        issue(tab, f"Нечисловые значения в '{col}'", rows=[str(v) for v in non_numeric])
    if min_val is not None:
        bad = df[col][vals < min_val].tolist()
        if bad:
            issue(tab, f"'{col}' < {min_val}", rows=[str(v) for v in bad])
    if max_val is not None:
        bad = df[col][vals > max_val].tolist()
        if bad:
            issue(tab, f"'{col}' > {max_val}", rows=[str(v) for v in bad])


def check_required(df, tab, cols):
    for col in cols:
        if col not in df.columns:
            issue(tab, f"Отсутствует обязательная колонка '{col}'")
            continue
        empty = df[df[col].astype(str).str.strip() == ""]
        if not empty.empty:
            issue(tab, f"Пустые значения в '{col}'", f"{len(empty)} строк")


def check_dates(df, tab, date_col="week_start"):
    if date_col not in df.columns:
        issue(tab, f"Нет колонки дат '{date_col}'")
        return
    from datetime import datetime
    bad_dates = []
    future_dates = []
    today = datetime.today()
    for v in df[date_col]:
        v = str(v).strip()
        if not v:
            continue
        parsed = None
        for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
            try:
                parsed = datetime.strptime(v, fmt)
                break
            except ValueError:
                continue
        if parsed is None:
            bad_dates.append(v)
        elif parsed > today:
            future_dates.append(v)
    if bad_dates:
        issue(tab, f"Нечитаемые даты в '{date_col}'", rows=bad_dates)
    if future_dates:
        issue(tab, f"Даты в будущем в '{date_col}'", rows=future_dates)
    # Проверяем диапазон дат
    valid = []
    for v in df[date_col]:
        v = str(v).strip()
        for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
            try:
                valid.append(datetime.strptime(v, fmt))
                break
            except ValueError:
                continue
    if valid:
        min_d = min(valid)
        max_d = max(valid)
        weeks = len(set(v.strftime("%Y-%W") for v in valid))
        log(f"  Даты: с {min_d.strftime('%d.%m.%Y')} по {max_d.strftime('%d.%m.%Y')} | Уникальных недель: {weeks}")
        if weeks < 2:
            issue(tab, "Только одна неделя данных — динамику не видно", f"Недель: {weeks}")


def audit_traffic_by_channel(df, tab):
    log("\n  --- Проверки ---")
    check_required(df, tab, ["week_start", "product", "channel", "sessions", "users"])
    check_dates(df, tab)
    check_numeric(df, tab, "sessions", min_val=0)
    check_numeric(df, tab, "users", min_val=0)
    check_numeric(df, tab, "pct_of_total", min_val=0, max_val=100)

    # Логика: users > sessions — невозможно при нормальной агрегации
    s = pd.to_numeric(df["sessions"].replace("", pd.NA), errors="coerce")
    u = pd.to_numeric(df["users"].replace("", pd.NA), errors="coerce")
    bad = df[(u > s) & s.notna() & u.notna()][["week_start","product","channel","sessions","users"]]
    if not bad.empty:
        issue(tab, "users > sessions — логическая ошибка",
              "Уникальных пользователей не может быть больше сессий",
              rows=bad.to_dict("records"))

    # Проверяем известные каналы
    known_channels = {"Organic Search", "Paid Search", "Meta Ads", "Direct", "Referral"}
    unknown = df[~df["channel"].isin(known_channels)]["channel"].unique().tolist()
    if unknown:
        issue(tab, "Неизвестные каналы", rows=[str(c) for c in unknown])

    # Проверяем известные продукты
    known_products = {"ФОП", "ЮО", "Еквайринг", "ЗП-проект", "Аванс", "Частинами", "Пакети"}
    unknown_p = df[~df["product"].isin(known_products)]["product"].unique().tolist()
    if unknown_p:
        issue(tab, "Неизвестные продукты", rows=[str(p) for p in unknown_p])

    # pct_of_total сумма по неделе должна быть ~100
    if "pct_of_total" in df.columns:
        pct = pd.to_numeric(df["pct_of_total"].replace("", pd.NA), errors="coerce")
        df2 = df.copy()
        df2["_pct"] = pct
        totals = df2.groupby("week_start")["_pct"].sum()
        bad_weeks = totals[(totals < 80) | (totals > 120)].index.tolist()
        if bad_weeks:
            issue(tab, "Сумма pct_of_total за неделю далека от 100%",
                  f"Недели: {bad_weeks[:5]}")

    log(f"  Уникальных продуктов: {df['product'].nunique()} -> {df['product'].unique().tolist()}")
    log(f"  Уникальных каналов:   {df['channel'].nunique()} -> {df['channel'].unique().tolist()}")


def audit_gsc_keywords(df, tab):
    log("\n  --- Проверки ---")
    check_required(df, tab, ["week_start", "product", "keyword_type", "total_clicks", "total_impressions", "avg_ctr", "avg_position"])
    check_dates(df, tab)
    check_numeric(df, tab, "total_clicks", min_val=0)
    check_numeric(df, tab, "total_impressions", min_val=0)
    check_numeric(df, tab, "avg_ctr", min_val=0, max_val=100)
    check_numeric(df, tab, "avg_position", min_val=1)

    # clicks > impressions — невозможно
    c = pd.to_numeric(df["total_clicks"].replace("", pd.NA), errors="coerce")
    i = pd.to_numeric(df["total_impressions"].replace("", pd.NA), errors="coerce")
    bad = df[(c > i) & c.notna() & i.notna()][["week_start","product","keyword_type","total_clicks","total_impressions"]]
    if not bad.empty:
        issue(tab, "total_clicks > total_impressions — невозможно",
              rows=bad.to_dict("records"))

    # avg_ctr согласован с clicks/impressions?
    ctr_calc = (c / i * 100).round(2)
    ctr_reported = pd.to_numeric(df["avg_ctr"].replace("", pd.NA), errors="coerce")
    diff = (ctr_reported - ctr_calc).abs()
    bad_ctr = df[diff > 5][["week_start","product","avg_ctr"]].copy()
    bad_ctr["ctr_expected"] = ctr_calc[diff > 5].round(2)
    if not bad_ctr.empty:
        issue(tab, "avg_ctr сильно расходится с clicks/impressions (>5%)",
              rows=bad_ctr.to_dict("records"))

    # Нулевые клики при ненулевых показах — не ошибка, но стоит отметить
    zero_clicks = df[(c == 0) & (i > 0)]
    if not zero_clicks.empty:
        log(f"  Заметка: {len(zero_clicks)} строк с 0 кликами при показах > 0 (низкий CTR, не ошибка)")

    known_types = {"branded", "non-branded"}
    unknown_t = df[~df["keyword_type"].isin(known_types)]["keyword_type"].unique().tolist()
    if unknown_t:
        issue(tab, "Неизвестные keyword_type", rows=[str(t) for t in unknown_t])

    log(f"  Уникальных продуктов: {df['product'].nunique()}")
    log(f"  keyword_type: {df['keyword_type'].unique().tolist()}")
    if "funnel_stage" in df.columns:
        log(f"  funnel_stage: {df['funnel_stage'].unique().tolist()}")


def audit_engagement(df, tab):
    log("\n  --- Проверки ---")
    check_required(df, tab, ["week_start", "product", "channel", "sessions", "users", "bounce_rate"])
    check_dates(df, tab)
    check_numeric(df, tab, "sessions", min_val=0)
    check_numeric(df, tab, "users", min_val=0)
    check_numeric(df, tab, "bounce_rate", min_val=0, max_val=100)
    check_numeric(df, tab, "avg_session_duration", min_val=0)
    check_numeric(df, tab, "pages_per_session", min_val=0)

    s = pd.to_numeric(df["sessions"].replace("", pd.NA), errors="coerce")
    u = pd.to_numeric(df["users"].replace("", pd.NA), errors="coerce")
    bad = df[(u > s) & s.notna() & u.notna()][["week_start","product","channel","sessions","users"]]
    if not bad.empty:
        issue(tab, "users > sessions — логическая ошибка",
              rows=bad.to_dict("records"))

    # bounce_rate = 100% для всех строк — подозрительно
    br = pd.to_numeric(df["bounce_rate"].replace("", pd.NA), errors="coerce")
    if (br == 100).sum() > len(df) * 0.5:
        issue(tab, "Более 50% строк имеют bounce_rate=100% — возможно GA4 настроен неверно")

    # avg_session_duration = 0 — люди уходят мгновенно?
    dur = pd.to_numeric(df.get("avg_session_duration", pd.Series()).replace("", pd.NA), errors="coerce")
    zero_dur = df[dur == 0]
    if not zero_dur.empty:
        issue(tab, f"{len(zero_dur)} строк с avg_session_duration=0",
              "Возможно GA4 не фиксирует время на странице")

    log(f"  Уникальных продуктов: {df['product'].nunique()}")
    log(f"  Уникальных каналов:   {df['channel'].nunique()}")


def audit_ads_keywords(df, tab):
    log("\n  --- Проверки ---")
    check_required(df, tab, ["week_start", "product", "funnel_stage", "total_clicks", "total_impressions", "avg_ctr", "total_cost_uah"])
    check_dates(df, tab)
    check_numeric(df, tab, "total_clicks", min_val=0)
    check_numeric(df, tab, "total_impressions", min_val=0)
    check_numeric(df, tab, "avg_ctr", min_val=0, max_val=100)
    check_numeric(df, tab, "total_cost_uah", min_val=0)

    c = pd.to_numeric(df["total_clicks"].replace("", pd.NA), errors="coerce")
    i = pd.to_numeric(df["total_impressions"].replace("", pd.NA), errors="coerce")
    bad = df[(c > i) & c.notna() & i.notna()][["week_start","product","funnel_stage","total_clicks","total_impressions"]]
    if not bad.empty:
        issue(tab, "total_clicks > total_impressions — невозможно", rows=bad.to_dict("records"))

    # Клики есть но расходов нет — подозрительно
    cost = pd.to_numeric(df["total_cost_uah"].replace("", pd.NA), errors="coerce")
    bad_cost = df[(c > 0) & (cost == 0)][["week_start","product","total_clicks","total_cost_uah"]]
    if not bad_cost.empty:
        issue(tab, "Есть клики но total_cost_uah=0",
              "Возможно ошибка в получении стоимости из API",
              rows=bad_cost.to_dict("records"))

    known_stages = {"awareness", "consideration", "decision"}
    unknown_s = df[~df["funnel_stage"].isin(known_stages)]["funnel_stage"].unique().tolist()
    if unknown_s:
        issue(tab, "Неизвестные funnel_stage", rows=[str(s) for s in unknown_s])

    log(f"  Уникальных продуктов: {df['product'].nunique()}")
    log(f"  funnel_stage: {df['funnel_stage'].unique().tolist()}")
    if "landing_url" in df.columns:
        log(f"  landing_url примеры: {df['landing_url'].dropna().unique()[:5].tolist()}")


def audit_meta_ads(df, tab):
    log("\n  --- Проверки ---")
    check_required(df, tab, ["week_start", "product", "impressions", "clicks", "ctr", "spend"])
    check_dates(df, tab)
    check_numeric(df, tab, "impressions", min_val=0)
    check_numeric(df, tab, "clicks", min_val=0)
    check_numeric(df, tab, "ctr", min_val=0, max_val=100)
    check_numeric(df, tab, "spend", min_val=0)

    c = pd.to_numeric(df["clicks"].replace("", pd.NA), errors="coerce")
    i = pd.to_numeric(df["impressions"].replace("", pd.NA), errors="coerce")
    bad = df[(c > i) & c.notna() & i.notna()][["week_start","product","clicks","impressions"]]
    if not bad.empty:
        issue(tab, "clicks > impressions — невозможно", rows=bad.to_dict("records"))

    # CTR согласован?
    ctr_calc = (c / i * 100).round(2)
    ctr_rep = pd.to_numeric(df["ctr"].replace("", pd.NA), errors="coerce")
    diff = (ctr_rep - ctr_calc).abs()
    bad_ctr = df[diff > 5][["week_start","product","ctr"]].copy()
    bad_ctr["ctr_expected"] = ctr_calc[diff > 5].round(2)
    if not bad_ctr.empty:
        issue(tab, "ctr расходится с clicks/impressions (>5%)", rows=bad_ctr.to_dict("records"))

    log(f"  Уникальных продуктов: {df['product'].nunique()} -> {df['product'].unique().tolist()}")
    if "campaign_type" in df.columns:
        log(f"  campaign_type: {df['campaign_type'].unique().tolist()}")


def audit_product_matrix(df, tab):
    log("\n  --- Проверки ---")
    expected_cols = [
        "week_start","product","sessions","users","bounce_rate",
        "organic_clicks","organic_impressions","organic_ctr","top_keyword",
        "paid_clicks","paid_impressions","paid_cost_uah",
        "meta_clicks","meta_impressions","meta_spend","top_page"
    ]
    check_required(df, tab, expected_cols)
    check_dates(df, tab)
    check_numeric(df, tab, "sessions", min_val=0)
    check_numeric(df, tab, "users", min_val=0)
    check_numeric(df, tab, "bounce_rate", min_val=0, max_val=100)
    check_numeric(df, tab, "organic_clicks", min_val=0)
    check_numeric(df, tab, "organic_ctr", min_val=0, max_val=100)
    check_numeric(df, tab, "paid_clicks", min_val=0)
    check_numeric(df, tab, "paid_cost_uah", min_val=0)
    check_numeric(df, tab, "meta_clicks", min_val=0)
    check_numeric(df, tab, "meta_spend", min_val=0)

    s = pd.to_numeric(df["sessions"].replace("", pd.NA), errors="coerce")
    u = pd.to_numeric(df["users"].replace("", pd.NA), errors="coerce")
    bad = df[(u > s) & s.notna() & u.notna()][["week_start","product","sessions","users"]]
    if not bad.empty:
        issue(tab, "users > sessions — логическая ошибка", rows=bad.to_dict("records"))

    # Перекрёстная проверка: organic_clicks в матрице vs сумма из gsc_keywords
    # (выводим только статистику — точная проверка будет ниже)
    log(f"  Уникальных продуктов: {df['product'].nunique()} -> {df['product'].unique().tolist()}")
    expected_products = {"ФОП", "ЮО", "Еквайринг", "ЗП-проект", "Аванс", "Частинами", "Пакети"}
    missing_p = expected_products - set(df["product"].unique())
    if missing_p:
        issue(tab, "Отсутствуют продукты в матрице", f"Нет: {missing_p}")


AUDITORS = {
    "traffic_by_channel": audit_traffic_by_channel,
    "gsc_keywords": audit_gsc_keywords,
    "engagement": audit_engagement,
    "ads_keywords": audit_ads_keywords,
    "meta_ads": audit_meta_ads,
    "product_matrix": audit_product_matrix,
}


def main():
    log(f"Spreadsheet ID: {SHEET_ID}")
    creds = get_credentials()
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SHEET_ID)

    all_worksheets = [ws.title for ws in spreadsheet.worksheets()]
    log(f"Листы в spreadsheet: {all_worksheets}")

    dataframes = {}
    for tab in TABS:
        df, actual_name = read_tab(spreadsheet, tab)
        if df is not None:
            auditor = AUDITORS.get(tab)
            if auditor:
                auditor(df, tab)
            dataframes[tab] = df

    # Перекрёстная проверка: traffic_by_channel vs engagement (sessions должны совпадать)
    log(f"\n{'='*60}")
    log("Перекрёстная проверка: traffic_by_channel vs engagement")
    if "traffic_by_channel" in dataframes and "engagement" in dataframes:
        tc = dataframes["traffic_by_channel"].copy()
        eng = dataframes["engagement"].copy()
        tc["sessions"] = pd.to_numeric(tc["sessions"].replace("", pd.NA), errors="coerce")
        eng["sessions"] = pd.to_numeric(eng["sessions"].replace("", pd.NA), errors="coerce")
        tc_sum = tc.groupby(["week_start","product"])["sessions"].sum().reset_index(name="tc_sessions")
        eng_sum = eng.groupby(["week_start","product"])["sessions"].sum().reset_index(name="eng_sessions")
        merged = tc_sum.merge(eng_sum, on=["week_start","product"], how="outer")
        merged["diff"] = (merged["tc_sessions"] - merged["eng_sessions"]).abs()
        big_diff = merged[merged["diff"] > 10].dropna(subset=["diff"])
        if not big_diff.empty:
            issue("cross_check", "sessions в traffic_by_channel и engagement расходятся >10",
                  rows=big_diff.to_dict("records"))
        else:
            log("  OK — сессии совпадают между таблицами")

    # Перекрёстная проверка: gsc_keywords vs product_matrix (organic_clicks)
    log(f"\n{'='*60}")
    log("Перекрёстная проверка: gsc_keywords vs product_matrix (organic_clicks)")
    if "gsc_keywords" in dataframes and "product_matrix" in dataframes:
        gsc = dataframes["gsc_keywords"].copy()
        pm = dataframes["product_matrix"].copy()
        gsc["total_clicks"] = pd.to_numeric(gsc["total_clicks"].replace("", pd.NA), errors="coerce")
        pm["organic_clicks"] = pd.to_numeric(pm["organic_clicks"].replace("", pd.NA), errors="coerce")
        gsc_sum = gsc.groupby(["week_start","product"])["total_clicks"].sum().reset_index(name="gsc_clicks")
        pm_sel = pm[["week_start","product","organic_clicks"]]
        merged = gsc_sum.merge(pm_sel, on=["week_start","product"], how="outer")
        merged["diff"] = (merged["gsc_clicks"] - merged["organic_clicks"]).abs()
        big_diff = merged[merged["diff"] > 10].dropna(subset=["diff"])
        if not big_diff.empty:
            issue("cross_check", "organic_clicks в gsc_keywords и product_matrix расходятся >10",
                  rows=big_diff.to_dict("records"))
        else:
            log("  OK — organic_clicks совпадают")

    # Итог
    log(f"\n{'='*60}")
    log(f"ИТОГО ПРОБЛЕМ: {len(issues)}")

    if not issues:
        log("Проблем не найдено.")
        return

    # Записываем отчёт на Desktop
    from datetime import datetime
    report_path = Path("/Users/redbull1122/Desktop/sheets_audit_report.md")
    today = datetime.today().strftime("%d.%m.%Y %H:%M")

    lines = [
        f"# Аудит данных Google Sheets — {today}",
        f"",
        f"Spreadsheet: `{SHEET_ID}`",
        f"Всего проблем: **{len(issues)}**",
        f"",
        f"---",
        f"",
    ]

    by_tab = {}
    for entry in issues:
        by_tab.setdefault(entry["tab"], []).append(entry)

    for tab, tab_issues in by_tab.items():
        lines.append(f"## {tab}")
        lines.append("")
        for e in tab_issues:
            lines.append(f"### {e['problem']}")
            if e.get("detail"):
                lines.append(f"> {e['detail']}")
            if e.get("rows"):
                lines.append("")
                lines.append("Примеры:")
                for r in e["rows"][:10]:
                    lines.append(f"- `{r}`")
            lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    log(f"\nОтчёт записан: {report_path}")


if __name__ == "__main__":
    main()
