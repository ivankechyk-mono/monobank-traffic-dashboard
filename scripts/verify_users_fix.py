"""
Верифицируем исправление: сравниваем users через count(строк) vs sum(users из GA4).
Запрашиваем engagement за последнюю неделю, смотрим разницу.
"""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()

from src.connectors.ga4 import GA4Connector, _get_credentials
from config.page_filters import get_product_by_url, is_business_page

creds = _get_credentials()
ga4 = GA4Connector(property_id=os.getenv("GA4_PROPERTY_ID"), credentials=creds)

df = ga4.get_engagement_full(date_range=("2026-07-07", "2026-07-13"))

print(f"Строк из GA4: {len(df)}")
print(f"Колонки: {df.columns.tolist()}\n")

# Текущая логика (ОШИБКА): users = count строк
current = (
    df[df["product"] != "Unknown"]
    .groupby(["product", "channel"])
    .agg(sessions=("sessions", "sum"), users_wrong=("sessions", "count"))
    .reset_index()
)

# Правильная логика: users = sum(users из GA4)
correct = (
    df[df["product"] != "Unknown"]
    .groupby(["product", "channel"])
    .agg(sessions=("sessions", "sum"), users_correct=("users", "sum"))
    .reset_index()
)

merged = current.merge(correct, on=["product", "channel"])

print(f"{'Продукт':<15} {'Канал':<20} {'sessions_x':>10} {'users(ОШИБКА)':>14} {'users(верно)':>13}")
print("-" * 78)
for _, r in merged.iterrows():
    flag = " !!!" if r["users_wrong"] > r["sessions_x"] or r["users_wrong"] != r["users_correct"] else ""
    print(f"{r['product']:<15} {r['channel']:<20} {int(r['sessions_x']):>10} {int(r['users_wrong']):>14} {int(r['users_correct']):>13}{flag}")
