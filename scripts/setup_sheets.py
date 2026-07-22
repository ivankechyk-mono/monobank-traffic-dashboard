"""
Створює Google Spreadsheet для monobank-traffic-dashboard.
Запуск: python3.11 scripts/setup_sheets.py
"""
import glob
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

SHEETS = [
    {
        "title": "traffic_by_channel",
        "headers": [
            "week_start", "product", "channel",
            "sessions", "users", "pct_of_total", "top_page", "source_note",
        ],
        "metrics": ["sessions", "users", "pct_of_total"],
    },
    {
        "title": "gsc_keywords",
        "headers": [
            "week_start", "product", "keyword_type", "dominant_intent",
            "top_keywords", "top_keyword", "total_clicks", "total_impressions",
            "avg_ctr", "avg_position", "top_page", "source_note",
        ],
        "metrics": ["total_clicks", "total_impressions", "avg_ctr", "avg_position"],
    },
    {
        "title": "engagement",
        "headers": [
            "week_start", "product", "channel", "source", "medium", "campaign",
            "sessions", "users", "bounce_rate", "avg_session_duration",
            "pages_per_session", "top_page", "source_note",
        ],
        "metrics": ["sessions", "bounce_rate", "avg_session_duration", "pages_per_session"],
    },
    {
        "title": "ads_keywords",
        "headers": [
            "week_start", "product", "funnel_stage",
            "top_keywords", "top_keyword", "total_clicks", "total_impressions",
            "avg_ctr", "total_cost_uah", "landing_url", "source_note",
        ],
        "metrics": ["total_clicks", "avg_ctr", "total_cost_uah"],
    },
    {
        "title": "meta_ads",
        "headers": [
            "week_start", "product", "campaign_name",
            "impressions", "clicks", "ctr", "spend", "campaign_type", "source_note",
        ],
        "metrics": ["clicks", "impressions", "ctr", "spend"],
    },
    {
        "title": "product_matrix",
        "headers": [
            "week_start", "product",
            "sessions", "users", "bounce_rate",
            "organic_clicks", "organic_impressions", "organic_ctr", "top_keyword",
            "paid_clicks", "paid_impressions", "paid_cost_uah",
            "meta_clicks", "meta_impressions", "meta_spend",
            "top_page", "source_note",
        ],
        "metrics": ["sessions", "organic_clicks", "paid_clicks", "meta_clicks", "paid_cost_uah", "meta_spend"],
    },
]

# Довідник метрик: metric_name → [назва_ua, що_це, де_дивитись]
METRICS_DICT = {
    "sessions":              ["Сесії",                   "Кількість відвідувань за тиждень. 1 людина може дати 2+ сесії",                            "traffic_by_channel, engagement, product_matrix"],
    "users":                 ["Унікальні користувачі",   "Унікальні відвідувачі. Зазвичай менше ніж sessions на 10–30%",                             "traffic_by_channel, engagement, product_matrix"],
    "pct_of_total":          ["% від трафіку",           "Частка сесій цього каналу/продукту від усього тижневого трафіку (%)",                      "traffic_by_channel"],
    "total_clicks":          ["Кліки (загально)",        "Суммарні кліки по кластеру. Для GSC — органічні, для Ads — платні",                        "gsc_keywords, ads_keywords"],
    "total_impressions":     ["Покази (загально)",       "Суммарні покази по кластеру в Google Search або Google Ads",                               "gsc_keywords, ads_keywords"],
    "avg_ctr":               ["CTR середній (%)",        "Середній click-through rate. clicks / impressions × 100",                                  "gsc_keywords, ads_keywords"],
    "avg_position":          ["Позиція в Google",        "Середня позиція в органічному пошуку Google. 1 = перший результат",                        "gsc_keywords"],
    "bounce_rate":           ["Відсоток відмов (%)",     "% сесій без взаємодії. Висока цифра = люди пішли не знайшовши потрібного",                 "engagement, product_matrix"],
    "avg_session_duration":  ["Час сесії (сек)",         "Середня тривалість сесії в секундах. >60 сек = люди читають, залучені",                    "engagement"],
    "pages_per_session":     ["Сторінок за сесію",       "Скільки сторінок переглянули за одну сесію. >1.5 = досліджують продукт",                   "engagement"],
    "total_cost_uah":        ["Витрати Google Ads (грн)","Сумарні витрати на ключові слова кластеру в Google Ads за тиждень",                        "ads_keywords"],
    "landing_url":           ["Landing URL (Ads)",       "URL сторінки куди веде ключове слово в Google Ads. Перевір чи це правильна сторінка",      "ads_keywords"],
    "clicks":                ["Кліки Meta",              "Кліки по Meta-рекламі (Facebook/Instagram). Включає всі кліки по оголошенню",              "meta_ads"],
    "impressions":           ["Покази Meta",             "Кількість разів показано рекламу в Meta. Зазвичай вище ніж Google Ads",                    "meta_ads"],
    "ctr":                   ["CTR Meta (%)",            "Click-through rate для Meta. Норма 0.5–2% (нижче ніж Google Search)",                      "meta_ads, ads_keywords"],
    "spend":                 ["Витрати Meta (грн)",      "Сумарні витрати на кампанії Meta за тиждень у гривнях",                                    "meta_ads"],
    "organic_clicks":        ["Органічні кліки (GSC)",   "Кліки з Google Search без реклами — трафік який ми заробили через SEO",                    "product_matrix"],
    "organic_impressions":   ["Органічні покази (GSC)",  "Покази в органічному пошуку Google",                                                       "product_matrix"],
    "organic_ctr":           ["Органічний CTR (%)",      "CTR органічного пошуку для продукту",                                                      "product_matrix"],
    "paid_clicks":           ["Кліки Google Ads",        "Кліки з платного пошуку Google",                                                           "product_matrix"],
    "paid_impressions":      ["Покази Google Ads",       "Покази платної реклами Google",                                                            "product_matrix"],
    "paid_cost_uah":         ["Витрати Google Ads (грн)","Витрати на Google Ads за тиждень у гривнях",                                              "product_matrix"],
    "meta_clicks":           ["Кліки Meta",              "Кліки з Meta-реклами для продукту",                                                        "product_matrix"],
    "meta_impressions":      ["Покази Meta",             "Покази Meta-реклами для продукту",                                                         "product_matrix"],
    "meta_spend":            ["Витрати Meta (грн)",      "Витрати Meta за тиждень у гривнях",                                                        "product_matrix"],
    "top_page":              ["Топ URL сторінки",        "URL сторінки куди найчастіше потрапляє трафік. Перевір чи це правильна сторінка продукту", "всі аркуші"],
    "campaign_type":         ["Тип кампанії Meta",       "app_install = веде на Google Play; lead_form = форма у Facebook; traffic = зовнішній сайт", "meta_ads"],
}


def get_credentials():
    token_path = "token.json"
    creds = None

    if glob.glob(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        secret_files = glob.glob("client_secret*.json")
        if not secret_files:
            raise FileNotFoundError("client_secret*.json не знайдено")
        flow = InstalledAppFlow.from_client_secrets_file(secret_files[0], SCOPES)
        creds = flow.run_local_server(port=0)
        with open(token_path, "w") as f:
            f.write(creds.to_json())

    return creds


def create_spreadsheet(service):
    body = {
        "properties": {"title": "monobank-traffic-dashboard"},
        "sheets": [{"properties": {"title": s["title"]}} for s in SHEETS],
    }
    spreadsheet = service.spreadsheets().create(body=body).execute()
    return spreadsheet["spreadsheetId"]


def add_headers(service, spreadsheet_id):
    """Записує заголовки в рядок 3 кожного аркушу (рядки 1-2 — для metrics dropdown)."""
    data = []
    for sheet in SHEETS:
        data.append({
            "range": f"'{sheet['title']}'!A3",
            "values": [sheet["headers"]],
        })
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"valueInputOption": "RAW", "data": data},
    ).execute()


def add_metrics_dropdown_to_all_sheets(service, spreadsheet_id):
    """
    На кожному аркуші:
      Рядок 1: [▼ dropdown метрик] | Назва метрики | Що це | Де є
      Рядок 2: (порожній — роздільник)
      Рядок 3: заголовки таблиці
      Рядок 4+: дані
    Довідник метрик зберігається у прихованих рядках після даних (offset 200+).
    """
    sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheet_id_map = {
        s["properties"]["title"]: s["properties"]["sheetId"]
        for s in sheet_metadata["sheets"]
    }

    all_requests = []
    all_value_updates = []

    for sheet_def in SHEETS:
        title = sheet_def["title"]
        sid = sheet_id_map.get(title)
        if sid is None:
            continue

        sheet_metrics = sheet_def.get("metrics", [])
        if not sheet_metrics:
            continue

        # Довідник для цього аркушу — тільки релевантні метрики + top_page якщо є
        relevant = list(sheet_metrics)
        if "top_page" in sheet_def["headers"] and "top_page" not in relevant:
            relevant.append("top_page")
        if "landing_url" in sheet_def["headers"] and "landing_url" not in relevant:
            relevant.append("landing_url")
        if "campaign_type" in sheet_def["headers"] and "campaign_type" not in relevant:
            relevant.append("campaign_type")

        # Рядок 1: мітка і VLOOKUP формули
        # Довідник метрик розміщуємо в рядках 200–230 (прихована зона)
        ref_start = 200
        ref_end = ref_start + len(relevant) - 1
        ref_range = f"A{ref_start}:C{ref_end}"

        vlookup_name = f'=IFERROR(VLOOKUP(A1,{ref_range},2,0),"")'
        vlookup_desc = f'=IFERROR(VLOOKUP(A1,{ref_range},3,0),"")'

        all_value_updates.append({
            "range": f"'{title}'!A1:D1",
            "values": [["← виберіть метрику", vlookup_name, vlookup_desc, ""]],
        })

        # Довідник у рядках 200+
        dict_rows = [[m, METRICS_DICT[m][0], METRICS_DICT[m][1]] for m in relevant if m in METRICS_DICT]
        if dict_rows:
            all_value_updates.append({
                "range": f"'{title}'!A{ref_start}:C{ref_start + len(dict_rows) - 1}",
                "values": dict_rows,
            })

        # Data Validation dropdown для A1
        all_requests.append({
            "setDataValidation": {
                "range": {
                    "sheetId": sid,
                    "startRowIndex": 0, "endRowIndex": 1,
                    "startColumnIndex": 0, "endColumnIndex": 1,
                },
                "rule": {
                    "condition": {
                        "type": "ONE_OF_LIST",
                        "values": [{"userEnteredValue": m} for m in relevant],
                    },
                    "showCustomUi": True,
                    "strict": False,
                },
            }
        })

        # Форматування рядка 1: жовтий фон, bold
        all_requests.append({
            "repeatCell": {
                "range": {
                    "sheetId": sid,
                    "startRowIndex": 0, "endRowIndex": 1,
                    "startColumnIndex": 0, "endColumnIndex": 4,
                },
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 1.0, "green": 0.95, "blue": 0.6},
                        "textFormat": {"bold": True},
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)",
            }
        })

        # Ховаємо рядки довідника (200+)
        all_requests.append({
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sid,
                    "dimension": "ROWS",
                    "startIndex": ref_start - 1,
                    "endIndex": ref_start + len(relevant),
                },
                "properties": {"hiddenByUser": True},
                "fields": "hiddenByUser",
            }
        })

        # Freeze рядок 1 (dropdown) і рядок 3 (заголовки)
        all_requests.append({
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sid,
                    "gridProperties": {"frozenRowCount": 3},
                },
                "fields": "gridProperties.frozenRowCount",
            }
        })

        # Bold заголовки в рядку 3
        all_requests.append({
            "repeatCell": {
                "range": {
                    "sheetId": sid,
                    "startRowIndex": 2, "endRowIndex": 3,
                    "startColumnIndex": 0,
                    "endColumnIndex": len(sheet_def["headers"]),
                },
                "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                "fields": "userEnteredFormat.textFormat.bold",
            }
        })

    # Записуємо всі значення
    service.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"valueInputOption": "USER_ENTERED", "data": all_value_updates},
    ).execute()

    # Застосовуємо всі форматування
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": all_requests},
    ).execute()


def freeze_and_bold_headers(service, spreadsheet_id):
    """Freeze рядок 3 (заголовки), bold headers — для існуючих таблиць без рядка 1."""
    sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    requests = []

    for sheet in sheet_metadata["sheets"]:
        title = sheet["properties"]["title"]
        sheet_id = sheet["properties"]["sheetId"]
        sheet_def = next((s for s in SHEETS if s["title"] == title), None)
        if not sheet_def:
            continue
        col_count = len(sheet_def["headers"])
        requests += [
            {
                "updateSheetProperties": {
                    "properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": 1}},
                    "fields": "gridProperties.frozenRowCount",
                }
            },
            {
                "repeatCell": {
                    "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1,
                               "startColumnIndex": 0, "endColumnIndex": col_count},
                    "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                    "fields": "userEnteredFormat.textFormat.bold",
                }
            },
        ]

    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": requests},
    ).execute()


if __name__ == "__main__":
    print("Авторизація Google (відкриється браузер)...")
    creds = get_credentials()
    service = build("sheets", "v4", credentials=creds)

    print("Створюю Google Spreadsheet...")
    spreadsheet_id = create_spreadsheet(service)

    print("Додаю заголовки (рядок 3)...")
    add_headers(service, spreadsheet_id)

    print("Додаю Metrics dropdown на кожен аркуш (рядок 1)...")
    add_metrics_dropdown_to_all_sheets(service, spreadsheet_id)

    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
    print(f"\nГотово! Spreadsheet ID: {spreadsheet_id}")
    print(f"Посилання: {url}")
    print("\nДодай у .env:")
    print(f"GOOGLE_SHEETS_ID={spreadsheet_id}")
