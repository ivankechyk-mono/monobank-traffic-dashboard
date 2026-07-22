"""
Налаштовує metrics dropdown на існуючій таблиці:
1. Створює прихований аркуш '_metrics_dict' з усіма метриками
2. На кожному аркуші: рядок 1 = dropdown A1 + VLOOKUP B1:C1 (з '_metrics_dict')
3. strict=False → без помилки "Input must be an item"
4. Видаляє старий аркуш "Metrics" якщо є

Запуск: python3.11 scripts/migrate_sheets_dropdown.py
"""
import glob
import os
import sys

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.setup_sheets import SHEETS, METRICS_DICT

SCOPES = [
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

DICT_SHEET = "_metrics_dict"


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


def _get_sheet_map(service, spreadsheet_id):
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    return {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta["sheets"]}


def step1_cleanup(service, spreadsheet_id):
    """Видаляємо старі/непотрібні аркуші."""
    sheet_map = _get_sheet_map(service, spreadsheet_id)
    to_delete = [t for t in ("Metrics", "linkedin_ads") if t in sheet_map]
    if not to_delete:
        return
    requests = [{"deleteSheet": {"sheetId": sheet_map[t]}} for t in to_delete]
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"requests": requests}
    ).execute()
    print(f"  Видалено аркуші: {to_delete}")


def step2_create_dict_sheet(service, spreadsheet_id):
    """Створює/перезаписує прихований аркуш _metrics_dict з усіма метриками."""
    sheet_map = _get_sheet_map(service, spreadsheet_id)

    if DICT_SHEET not in sheet_map:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": DICT_SHEET, "hidden": True}}}]},
        ).execute()
        print(f"  Створено аркуш '{DICT_SHEET}'")
        sheet_map = _get_sheet_map(service, spreadsheet_id)
    else:
        print(f"  Аркуш '{DICT_SHEET}' вже існує — перезаписую")

    # Записуємо всі метрики: col A = ключ, B = назва_ua, C = опис
    all_rows = [["metric_key", "name_ua", "description"]]
    for key, (name, desc, _) in METRICS_DICT.items():
        all_rows.append([key, name, desc])

    service.spreadsheets().values().update(
        spreadsheetId=spreadsheet_id,
        range=f"'{DICT_SHEET}'!A1",
        valueInputOption="RAW",
        body={"values": all_rows},
    ).execute()
    print(f"  Записано {len(all_rows)-1} метрик у '{DICT_SHEET}'")
    return sheet_map[DICT_SHEET]


def step3_add_dropdowns(service, spreadsheet_id, dict_sheet_id):
    """На кожному аркуші: оновлює A1 dropdown + VLOOKUP → _metrics_dict."""
    sheet_map = _get_sheet_map(service, spreadsheet_id)

    requests = []
    value_updates = []

    # Скільки рядків метрик є в довіднику (без заголовка)
    dict_last_row = 1 + len(METRICS_DICT)
    dict_range = f"'{DICT_SHEET}'!A2:C{dict_last_row}"

    for sheet_def in SHEETS:
        title = sheet_def["title"]
        sid = sheet_map.get(title)
        if sid is None:
            print(f"  '{title}' не знайдено — пропускаю")
            continue

        sheet_metrics = list(sheet_def.get("metrics", []))
        if "top_page" in sheet_def["headers"] and "top_page" not in sheet_metrics:
            sheet_metrics.append("top_page")
        if "landing_url" in sheet_def["headers"] and "landing_url" not in sheet_metrics:
            sheet_metrics.append("landing_url")
        if "campaign_type" in sheet_def["headers"] and "campaign_type" not in sheet_metrics:
            sheet_metrics.append("campaign_type")

        # VLOOKUP шукає в _metrics_dict, col A=key, B=name, C=desc
        vlookup_name = f"=IFERROR(VLOOKUP(A1,{dict_range},2,0),\"\")"
        vlookup_desc = f"=IFERROR(VLOOKUP(A1,{dict_range},3,0),\"\")"

        # Перевіряємо чи рядки 1-2 вже є (якщо міграція вже виконувалась)
        import gspread
        from google.oauth2.credentials import Credentials as GCreds
        # Записуємо значення в A1:D1 — не чіпаємо дані нижче
        value_updates.append({
            "range": f"'{title}'!A1:D1",
            "values": [["← виберіть метрику", vlookup_name, vlookup_desc, ""]],
        })

        # Data Validation — strict=False щоб не було помилки
        requests.append({
            "setDataValidation": {
                "range": {
                    "sheetId": sid,
                    "startRowIndex": 0, "endRowIndex": 1,
                    "startColumnIndex": 0, "endColumnIndex": 1,
                },
                "rule": {
                    "condition": {
                        "type": "ONE_OF_LIST",
                        "values": [{"userEnteredValue": m} for m in sheet_metrics],
                    },
                    "showCustomUi": True,
                    "strict": False,
                },
            }
        })

        # Жовтий фон + bold рядок 1
        requests.append({
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

        # Freeze перших 3 рядків
        requests.append({
            "updateSheetProperties": {
                "properties": {
                    "sheetId": sid,
                    "gridProperties": {"frozenRowCount": 3},
                },
                "fields": "gridProperties.frozenRowCount",
            }
        })

        # Bold заголовки рядок 3
        requests.append({
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

        print(f"  '{title}': dropdown з {len(sheet_metrics)} метрик")

    service.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"valueInputOption": "USER_ENTERED", "data": value_updates},
    ).execute()

    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": requests},
    ).execute()


if __name__ == "__main__":
    spreadsheet_id = os.getenv("GOOGLE_SHEETS_ID")
    if not spreadsheet_id:
        raise ValueError("GOOGLE_SHEETS_ID не встановлено у .env")

    print(f"Spreadsheet: {spreadsheet_id}")
    creds = get_credentials()
    service = build("sheets", "v4", credentials=creds)

    print("\n[1/3] Прибираємо старі аркуші...")
    step1_cleanup(service, spreadsheet_id)

    print("\n[2/3] Створюємо довідник '_metrics_dict'...")
    dict_sheet_id = step2_create_dict_sheet(service, spreadsheet_id)

    print("\n[3/3] Додаємо dropdown на кожен аркуш...")
    step3_add_dropdowns(service, spreadsheet_id, dict_sheet_id)

    print(f"\nГотово! https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
