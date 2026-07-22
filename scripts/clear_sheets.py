"""Очищає всі 6 аркушів Google Sheets (залишає тільки заголовки)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import gspread
from google.oauth2.credentials import Credentials

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

creds = Credentials.from_authorized_user_file("token.json", SCOPES)
client = gspread.authorize(creds)
sheet = client.open_by_key(os.environ["GOOGLE_SHEETS_ID"])

for tab in TABS:
    ws = sheet.worksheet(tab)
    ws.clear()
    print(f"✓ {tab} — очищено")

print("Готово.")
