"""
Детальная проверка сырых данных в каждом листе.
Показываем первые и последние строки, реальные значения дат и сессий.
"""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv; load_dotenv()

from src.connectors.ga4 import _get_credentials
import gspread, pandas as pd
from datetime import datetime

creds = _get_credentials()
client = gspread.authorize(creds)
spreadsheet = client.open_by_key(os.getenv("GOOGLE_SHEETS_ID"))

def inspect_tab(tab):
    for name in [f"_data_{tab}", tab]:
        try:
            ws = spreadsheet.worksheet(name)
            vals = ws.get_all_values()
            break
        except:
            continue
    else:
        print(f"\n{tab}: НЕ НАЙДЕН")
        return

    if len(vals) < 4:
        print(f"\n{tab}: меньше 4 строк в листе")
        return

    headers = vals[2]
    data_rows = [r for r in vals[3:] if any(v.strip() for v in r)]
    df = pd.DataFrame(data_rows, columns=headers)

    print(f"\n{'='*60}")
    print(f"Лист: {name}  |  Всего строк данных: {len(df)}")
    print(f"Колонки: {headers}")

    # Анализ дат
    if "week_start" in df.columns:
        dates_raw = df["week_start"].dropna().unique().tolist()
        good, bad = [], []
        for d in dates_raw:
            d = str(d).strip()
            if not d:
                continue
            try:
                datetime.strptime(d, "%d.%m.%Y")
                good.append(d)
            except:
                bad.append(d)

        print(f"\n  Дат с правильным форматом (DD.MM.YYYY): {len(good)}")
        if good:
            # сортируем по дате
            good_sorted = sorted(good, key=lambda x: datetime.strptime(x, "%d.%m.%Y"))
            print(f"  Самая старая: {good_sorted[0]}")
            print(f"  Самая новая:  {good_sorted[-1]}")

        print(f"  Дат со старым форматом (DD–DD.MM.YYYY): {len(bad)}")
        if bad:
            bad_sample = bad[:3]
            print(f"  Примеры: {bad_sample}")

    # Анализ сессий / кликов
    for col in ["sessions", "total_clicks", "clicks", "organic_clicks"]:
        if col in df.columns:
            vals_num = pd.to_numeric(df[col].replace("", "0"), errors="coerce").fillna(0)
            total = int(vals_num.sum())
            mx = int(vals_num.max())
            print(f"\n  {col}: сумма={total}, макс={mx}")
            # топ-5 строк по этой колонке
            df[col] = pd.to_numeric(df[col].replace("", "0"), errors="coerce").fillna(0)
            top = df.nlargest(5, col) if col in df.columns else pd.DataFrame()
            if not top.empty:
                show_cols = [c for c in ["week_start","product","channel","sessions","users",
                                          "total_clicks","clicks","organic_clicks"] if c in top.columns]
                print(f"  Топ-5 строк по {col}:")
                print(top[show_cols].to_string(index=False))
            break  # только первую найденную

    # Последние 3 строки
    print(f"\n  Последние 3 строки:")
    show_cols = [c for c in ["week_start","product","channel","sessions","users","total_clicks","clicks"] if c in df.columns][:6]
    print(df.tail(3)[show_cols].to_string(index=False))

for tab in ["traffic_by_channel", "gsc_keywords", "engagement", "product_matrix"]:
    inspect_tab(tab)
