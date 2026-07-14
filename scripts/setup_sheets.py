"""
Створює Google Spreadsheet для monobank-traffic-dashboard.
Запуск: python3.11 scripts/setup_sheets.py
"""
import glob
import json
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
        "headers": ["week_start", "channel", "sessions", "users", "pageviews", "pct_of_total"],
    },
    {
        "title": "gsc_keywords",
        "headers": ["week_start", "query", "page", "clicks", "impressions", "ctr", "position"],
    },
    {
        "title": "ads_keywords",
        "headers": ["week_start", "keyword", "campaign", "clicks", "cost", "impressions"],
    },
    {
        "title": "product_matrix",
        "headers": ["week_start", "product", "channel", "sessions", "clicks"],
    },
    {
        "title": "engagement",
        "headers": ["week_start", "channel", "page_path", "bounce_rate", "avg_duration_sec", "pages_per_session"],
    },
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


def create_spreadsheet(service):
    body = {
        "properties": {"title": "monobank-traffic-dashboard"},
        "sheets": [{"properties": {"title": s["title"]}} for s in SHEETS],
    }
    spreadsheet = service.spreadsheets().create(body=body).execute()
    return spreadsheet["spreadsheetId"]


def add_headers(service, spreadsheet_id):
    data = []
    for sheet in SHEETS:
        data.append({
            "range": f"{sheet['title']}!A1",
            "values": [sheet["headers"]],
        })

    service.spreadsheets().values().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"valueInputOption": "RAW", "data": data},
    ).execute()


def freeze_and_bold_headers(service, spreadsheet_id):
    sheet_metadata = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    requests = []

    for sheet in sheet_metadata["sheets"]:
        sheet_id = sheet["properties"]["sheetId"]
        col_count = next(
            len(s["headers"]) for s in SHEETS
            if s["title"] == sheet["properties"]["title"]
        )
        requests += [
            # freeze row 1
            {
                "updateSheetProperties": {
                    "properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": 1}},
                    "fields": "gridProperties.frozenRowCount",
                }
            },
            # bold headers
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

    print("Додаю заголовки...")
    add_headers(service, spreadsheet_id)

    print("Форматую заголовки...")
    freeze_and_bold_headers(service, spreadsheet_id)

    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
    print(f"\nГотово! Spreadsheet ID: {spreadsheet_id}")
    print(f"Посилання: {url}")
    print("\nДодай у .env:")
    print(f"GOOGLE_SHEETS_ID={spreadsheet_id}")
