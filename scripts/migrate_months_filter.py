"""
Міграція до архітектури з months filter.

Що робить:
  1. Копіює дані з видимих аркушів у приховані _data_*
  2. Очищає видимі аркуші і вставляє =FILTER(..., months!$A$1) формули
  3. Створює аркуш months з dropdown по місяцях
  4. Ховає _data_* аркуші

Відкат: scripts/rollback_months_filter.py (копіює _data_* назад у видимі)

Запуск: python3.11 scripts/migrate_months_filter.py
"""
import glob
import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os, re
from dotenv import load_dotenv

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

# Видимі аркуші і кількість колонок (для FILTER діапазону)
TABS = [
    {"name": "traffic_by_channel", "cols": 8},
    {"name": "gsc_keywords",       "cols": 12},
    {"name": "engagement",         "cols": 13},
    {"name": "ads_keywords",       "cols": 11},
    {"name": "meta_ads",           "cols": 9},
    {"name": "product_matrix",     "cols": 17},
]


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


def _col_letter(n: int) -> str:
    result = ""
    while n > 0:
        n, r = divmod(n - 1, 26)
        result = chr(65 + r) + result
    return result


def step1_copy_to_data_sheets(gc: gspread.Client, spreadsheet: gspread.Spreadsheet):
    """Копіює дані з видимих аркушів у _data_* (або створює їх)."""
    print("\n[1/3] Копіюю дані у _data_* аркуші...")
    existing_titles = {ws.title for ws in spreadsheet.worksheets()}

    for tab in TABS:
        src_name = tab["name"]
        dst_name = f"_data_{src_name}"

        src = spreadsheet.worksheet(src_name)
        all_vals = src.get_all_values()

        if dst_name not in existing_titles:
            spreadsheet.add_worksheet(title=dst_name, rows=2000, cols=tab["cols"] + 2)
            print(f"  Створено {dst_name}")

        dst = spreadsheet.worksheet(dst_name)
        dst.clear()
        if all_vals:
            dst.update(all_vals, "A1")
        print(f"  {src_name} → {dst_name}: {len(all_vals)} рядків")


def step2_collect_months(gc: gspread.Client, spreadsheet: gspread.Spreadsheet) -> list[str]:
    """Збирає унікальні місяці з _data_traffic_by_channel (формат MM.YYYY)."""
    ws = spreadsheet.worksheet("_data_traffic_by_channel")
    vals = ws.get_all_values()
    months = set()
    for row in vals[3:]:  # skip rows 1-3 (dropdown, empty, headers)
        if row and row[0] and re.match(r"\d{2}\.\d{2}\.\d{4}", row[0]):
            # week_start = DD.MM.YYYY → беремо MM.YYYY
            months.add(row[0][3:])  # "DD.MM.YYYY" → "MM.YYYY"
    # Сортуємо хронологічно
    sorted_months = sorted(months, key=lambda m: (m[3:], m[:2]))
    print(f"  Знайдено місяців: {sorted_months}")
    return sorted_months


def step3_create_months_sheet(
    gc: gspread.Client,
    spreadsheet: gspread.Spreadsheet,
    service,
    months: list[str],
):
    """Створює або оновлює аркуш months з dropdown."""
    print("\n[2/3] Створюю аркуш months...")
    existing_titles = {ws.title for ws in spreadsheet.worksheets()}
    spreadsheet_id = spreadsheet.id

    if "months" not in existing_titles:
        spreadsheet.add_worksheet(title="months", rows=10, cols=5)

    ws = spreadsheet.worksheet("months")
    ws.clear()
    ws.update([["← виберіть місяць"]], "A1")
    ws.update([["Показуються дані за весь цей місяць у всіх аркушах"]], "B1")

    # Отримуємо sheetId
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheet_id_map = {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta["sheets"]}
    months_sid = sheet_id_map["months"]

    last_month = months[-1] if months else "07.2026"

    requests = [
        # Dropdown з місяцями в A1
        {
            "setDataValidation": {
                "range": {"sheetId": months_sid, "startRowIndex": 0, "endRowIndex": 1,
                          "startColumnIndex": 0, "endColumnIndex": 1},
                "rule": {
                    "condition": {
                        "type": "ONE_OF_LIST",
                        "values": [{"userEnteredValue": m} for m in months],
                    },
                    "showCustomUi": True,
                    "strict": False,
                },
            }
        },
        # Форматування: жовтий фон, bold
        {
            "repeatCell": {
                "range": {"sheetId": months_sid, "startRowIndex": 0, "endRowIndex": 1,
                          "startColumnIndex": 0, "endColumnIndex": 2},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": {"red": 1.0, "green": 0.95, "blue": 0.6},
                        "textFormat": {"bold": True, "fontSize": 12},
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat)",
            }
        },
        # Ширина колонки A = 120px
        {
            "updateDimensionProperties": {
                "range": {"sheetId": months_sid, "dimension": "COLUMNS",
                          "startIndex": 0, "endIndex": 1},
                "properties": {"pixelSize": 120},
                "fields": "pixelSize",
            }
        },
        # Ширина колонки B = 400px
        {
            "updateDimensionProperties": {
                "range": {"sheetId": months_sid, "dimension": "COLUMNS",
                          "startIndex": 1, "endIndex": 2},
                "properties": {"pixelSize": 400},
                "fields": "pixelSize",
            }
        },
    ]
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"requests": requests}
    ).execute()

    # Вставляємо поточний (останній) місяць як дефолт
    # Апостроф на початку — щоб Sheets не конвертував "07.2026" в число 7.2026
    ws.update([[f"'{last_month}"]], "A1", value_input_option="RAW")
    print(f"  months створено, дефолт: {last_month}")


def step4_write_filter_formulas(
    gc: gspread.Client,
    spreadsheet: gspread.Spreadsheet,
    service,
):
    """Очищає видимі аркуші і вставляє FILTER формули."""
    print("\n[3/3] Вставляю FILTER формули у видимі аркуші...")
    spreadsheet_id = spreadsheet.id

    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheet_id_map = {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta["sheets"]}

    for tab in TABS:
        name = tab["name"]
        col_count = tab["cols"]
        col_last = _col_letter(col_count)
        sid = sheet_id_map.get(name)
        if sid is None:
            print(f"  ⚠ {name} не знайдено, пропускаємо")
            continue

        ws = spreadsheet.worksheet(name)

        # Отримуємо заголовки з _data_ аркушу (рядок 3)
        data_ws = spreadsheet.worksheet(f"_data_{name}")
        data_vals = data_ws.get_all_values()
        headers = data_vals[2] if len(data_vals) >= 3 else []

        # Очищаємо рядки 3+ (залишаємо 1-2: metrics dropdown)
        ws.batch_clear([f"A3:{col_last}2000"])

        updates = []

        # Рядок 3: заголовки (копіюємо з _data_)
        if headers:
            updates.append({"range": f"A3:{col_last}3", "values": [headers]})

        # RIGHT(...,7) бере останні 7 символів "DD–DD.MM.YYYY" → "MM.YYYY"
        data_range = f"'_data_{name}'!A4:{col_last}"
        date_col = f"'_data_{name}'!A4:A"
        filter_formula = (
            f'=IFERROR(FILTER({data_range},RIGHT({date_col},7)=months!$C$2),"")'
        )
        updates.append({"range": "A4", "values": [[filter_formula]]})

        ws.batch_update(updates, value_input_option="USER_ENTERED")

        # Freeze 3 рядки
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": [{
                "updateSheetProperties": {
                    "properties": {"sheetId": sid, "gridProperties": {"frozenRowCount": 3}},
                    "fields": "gridProperties.frozenRowCount",
                }
            }]}
        ).execute()

        print(f"  ✓ {name}: FILTER формула вставлена")


def step5_hide_data_sheets(service, spreadsheet_id: str, spreadsheet: gspread.Spreadsheet):
    """Ховає _data_* аркуші."""
    print("\n  Ховаю _data_* аркуші...")
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    requests = []
    for s in meta["sheets"]:
        if s["properties"]["title"].startswith("_data_"):
            requests.append({
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": s["properties"]["sheetId"],
                        "hidden": True,
                    },
                    "fields": "hidden",
                }
            })
    if requests:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body={"requests": requests}
        ).execute()
        print(f"  Сховано {len(requests)} аркушів")


if __name__ == "__main__":
    print("Авторизація...")
    creds = get_credentials()
    gc = gspread.authorize(creds)
    service = build("sheets", "v4", credentials=creds)

    sheet_id = os.getenv("GOOGLE_SHEETS_ID")
    if not sheet_id:
        raise ValueError("GOOGLE_SHEETS_ID не встановлено в .env")

    spreadsheet = gc.open_by_key(sheet_id)
    print(f"Spreadsheet: {spreadsheet.title}")

    step1_copy_to_data_sheets(gc, spreadsheet)
    months = step2_collect_months(gc, spreadsheet)
    step3_create_months_sheet(gc, spreadsheet, service, months)
    step4_write_filter_formulas(gc, spreadsheet, service)
    step5_hide_data_sheets(service, sheet_id, spreadsheet)

    print("\n✓ Міграція завершена!")
    print("  - Аркуш 'months': вибери місяць → всі аркуші оновляться автоматично")
    print("  - Дані зберігаються у прихованих _data_* аркушах")
    print("  - Відкат: python3.11 scripts/rollback_months_filter.py")
