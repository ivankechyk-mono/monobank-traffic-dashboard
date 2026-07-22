"""
Финальная проверка: запускаем build_traffic_by_channel с исправленным кодом
и сверяем с прямыми данными GA4.
"""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()

from src.connectors.ga4 import GA4Connector
from src.transforms.traffic import build_traffic_by_channel

ga4 = GA4Connector(property_id=os.getenv("GA4_PROPERTY_ID"))
df_ch = ga4.get_channel_traffic(("2026-07-07", "2026-07-13"))
df_eng = ga4.get_engagement_full(("2026-07-07", "2026-07-13"))

result = build_traffic_by_channel(df_ch, df_eng, week_start="07.07.2026")

print(f"{'Продукт':<15} {'Канал':<20} {'sessions':>10} {'users':>8} {'users>sessions?':>15}")
print("-" * 72)
for _, r in result.iterrows():
    s, u = int(r["sessions"]), int(r["users"])
    flag = " ОШИБКА" if u > s else ""
    print(f"{r['product']:<15} {r['channel']:<20} {s:>10} {u:>8}{flag}")

print(f"\nСтрок итого: {len(result)}")
bad = result[result["users"].astype(int) > result["sessions"].astype(int)]
print(f"Строк где users > sessions: {len(bad)}")
