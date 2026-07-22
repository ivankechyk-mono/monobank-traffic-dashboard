"""Очищає дані з усіх _data_* аркушів (рядки 4+), залишає dropdown і заголовки."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv; load_dotenv()
from src.connectors.ga4 import _get_credentials
import gspread

TABS = ["traffic_by_channel", "gsc_keywords", "engagement", "ads_keywords", "meta_ads", "product_matrix"]

creds = _get_credentials()
client = gspread.authorize(creds)
sheet = client.open_by_key(os.environ["GOOGLE_SHEETS_ID"])

for tab in TABS:
    for name in [f"_data_{tab}", tab]:
        try:
            ws = sheet.worksheet(name)
            # Очищаем только данные (строка 4+), не трогаем строки 1-3 (dropdown, пустая, заголовки)
            all_vals = ws.get_all_values()
            if len(all_vals) > 3:
                last_col = chr(64 + len(all_vals[2])) if all_vals[2] else "R"
                last_row = len(all_vals) + 5
                ws.batch_clear([f"A4:{last_col}{last_row}"])
            print(f"  {name} — очищено")
            break
        except gspread.exceptions.WorksheetNotFound:
            continue

print("Готово.")
