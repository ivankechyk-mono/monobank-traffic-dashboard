"""
Проверяем данные в Sheets перед подключением к Looker Studio:
- формат дат (должен быть DD.MM.YYYY)
- наличие всех продуктов
- диапазон недель
"""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv; load_dotenv()

from src.connectors.ga4 import _get_credentials
import gspread, pandas as pd

creds = _get_credentials()
client = gspread.authorize(creds)
spreadsheet = client.open_by_key(os.getenv("GOOGLE_SHEETS_ID"))

TABS = ["traffic_by_channel", "gsc_keywords", "engagement", "ads_keywords", "meta_ads", "product_matrix"]

for tab in TABS:
    for name in [f"_data_{tab}", tab]:
        try:
            ws = spreadsheet.worksheet(name)
            vals = ws.get_all_values()
            if len(vals) < 4:
                print(f"{tab}: пусто")
                break
            headers = vals[2]
            data = vals[3:]
            df = pd.DataFrame(data, columns=headers)
            df = df[df.apply(lambda r: any(v.strip() for v in r.astype(str)), axis=1)]

            date_col = "week_start" if "week_start" in df.columns else headers[0]
            dates = df[date_col].dropna().unique().tolist()
            # фильтруем только DD.MM.YYYY формат
            from datetime import datetime
            good, bad = [], []
            for d in dates:
                try:
                    datetime.strptime(str(d).strip(), "%d.%m.%Y")
                    good.append(d)
                except:
                    bad.append(d)

            products = sorted(df["product"].unique().tolist()) if "product" in df.columns else []
            print(f"\n{tab} ({len(df)} строк):")
            print(f"  Недель с правильным форматом: {len(good)}")
            print(f"  Недель со старым форматом:    {len(bad)}")
            if good:
                print(f"  Диапазон: {min(good)} → {max(good)}")
            print(f"  Продукты: {products}")
            break
        except:
            continue
