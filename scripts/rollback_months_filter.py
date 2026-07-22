"""
Відкат months filter. Копіює дані з _data_* назад у видимі аркуші.
Запуск: python3.11 scripts/rollback_months_filter.py
"""
import glob, os
import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

TABS = [
    "traffic_by_channel", "gsc_keywords", "engagement",
    "ads_keywords", "meta_ads", "product_matrix",
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


if __name__ == "__main__":
    print("Авторизація...")
    creds = get_credentials()
    gc = gspread.authorize(creds)
    service = build("sheets", "v4", credentials=creds)

    sheet_id = os.getenv("GOOGLE_SHEETS_ID")
    spreadsheet = gc.open_by_key(sheet_id)

    for tab in TABS:
        data_name = f"_data_{tab}"
        try:
            src = spreadsheet.worksheet(data_name)
        except gspread.WorksheetNotFound:
            print(f"  ⚠ {data_name} не знайдено, пропускаємо")
            continue

        all_vals = src.get_all_values()
        dst = spreadsheet.worksheet(tab)
        # Очищаємо тільки рядки 3+ (зберігаємо metrics dropdown у 1-2)
        dst.batch_clear(["A3:Z2000"])
        if all_vals:
            dst.update("A3", all_vals[2:])  # рядок 3+ з _data_ (там теж рядок 3 = заголовки)
        print(f"  ✓ {data_name} → {tab}: {len(all_vals)} рядків")

    # Показуємо _data_* назад (не обов'язково але корисно)
    meta = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
    requests = []
    for s in meta["sheets"]:
        if s["properties"]["title"].startswith("_data_") or s["properties"]["title"] == "months":
            requests.append({
                "updateSheetProperties": {
                    "properties": {"sheetId": s["properties"]["sheetId"], "hidden": False},
                    "fields": "hidden",
                }
            })
    if requests:
        service.spreadsheets().batchUpdate(spreadsheetId=sheet_id, body={"requests": requests}).execute()

    print("\n✓ Відкат завершено. Видимі аркуші відновлені.")
    print("  _data_* і months аркуші тепер видимі — можеш видалити вручну якщо не потрібні.")
