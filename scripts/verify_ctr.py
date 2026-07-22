"""
Прямой запрос GSC: сравниваем avg_ctr (среднее по запросам)
vs weighted_ctr (clicks/impressions). Проверяем что разница закономерна.
"""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()

from src.connectors.ga4 import _get_credentials
from src.connectors.gsc import GSCConnector

creds = _get_credentials()
gsc = GSCConnector(site_url=os.getenv("GSC_SITE_URL", "https://monobank.ua/"), credentials=creds)

df = gsc.get_keywords(date_range=("2026-07-07", "2026-07-13"))
print(f"Строк из GSC: {len(df)}")
print(f"Колонки: {df.columns.tolist()}\n")

from src.transforms.traffic import classify_keyword
import pandas as pd

df["keyword_type"] = df["query"].apply(classify_keyword)
from config.page_filters import get_product_by_url
df["product"] = df["page"].apply(lambda p: get_product_by_url(p)[0])

known = ["ФОП", "ЮО", "Еквайринг", "ЗП-проект", "Аванс", "Частинами", "Пакети"]
df = df[df["product"].isin(known)]

df["clicks"] = pd.to_numeric(df["clicks"], errors="coerce").fillna(0)
df["impressions"] = pd.to_numeric(df["impressions"], errors="coerce").fillna(0)
df["ctr"] = pd.to_numeric(df["ctr"], errors="coerce").fillna(0)

print(f"{'Продукт':<15} {'Тип':<14} {'clicks':>8} {'impr':>8} {'avg_ctr(наш)':>13} {'weighted_ctr':>13} {'разница':>8}")
print("-" * 83)

for (product, kw_type), grp in df.groupby(["product", "keyword_type"]):
    total_clicks = int(grp["clicks"].sum())
    total_impr = int(grp["impressions"].sum())
    avg_ctr = round(grp["ctr"].mean() * 100, 2)          # текущая логика: среднее по запросам
    weighted_ctr = round(total_clicks / total_impr * 100, 2) if total_impr > 0 else 0.0
    diff = round(avg_ctr - weighted_ctr, 2)
    flag = " !!!" if abs(diff) > 5 else ""
    print(f"{product:<15} {kw_type:<14} {total_clicks:>8} {total_impr:>8} {avg_ctr:>13} {weighted_ctr:>13}{flag}")
