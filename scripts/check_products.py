"""
Перевіряє кожну таблицю: які продукти є, яких немає і чому.
Запуск: python3 scripts/check_products.py
"""
import os, sys
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.connectors.ga4 import _get_credentials
import gspread, pandas as pd
from datetime import datetime

EXPECTED_PRODUCTS = ["ФОП", "ЮО", "Еквайринг", "ЗП-проект", "Аванс", "Частинами", "Пакети"]

# Пояснення чому продукт може бути відсутнім
ABSENCE_REASONS = {
    "traffic_by_channel": {
        "ЮО":        "GA4 events — business_legal_entity_page_view (SPA, нема pagePath)",
        "ЗП-проект": "GA4 events — business_salary_shown (SPA, нема pagePath)",
        "Аванс":     "GA4 events — business_mca_banner_shown (SPA, нема pagePath)",
        "Частинами": "Немає окремої сторінки і немає GA4 event — відсутній в property",
        "Пакети":    "Немає окремої сторінки і немає GA4 event — відсутній в property",
    },
    "engagement": {
        "ЮО":        "GA4 events (без bounce_rate/duration — SPA не генерує ці метрики)",
        "ЗП-проект": "GA4 events (без bounce_rate/duration)",
        "Аванс":     "GA4 events (без bounce_rate/duration)",
        "Частинами": "Немає GA4 event — відсутній",
        "Пакети":    "Немає GA4 event — відсутній",
    },
    "gsc_keywords": {
        "Еквайринг": "Є — маркетинговий сайт у GSC",
        "ФОП":       "Є — маркетинговий сайт у GSC",
        "ЮО":        "Є — маркетинговий сайт у GSC",
        "Частинами": "Є — маркетинговий сайт у GSC",
        "ЗП-проект": "Є — маркетинговий сайт у GSC",
        "Пакети":    "Є — але низький трафік (14 показів/тиждень)",
        "Аванс":     "Є якщо є branded запити 'аванс монобанк'",
    },
    "ads_keywords": {
        "Частинами": "Немає Ads кампаній або не вдалось атрибутувати за landing_url",
        "Пакети":    "Немає Ads кампаній",
        "Аванс":     "Немає Ads кампаній (МСА = Аванс — перевір landing_url)",
    },
    "meta_ads": {
        "Частинами": "Є як 'Оплата Частями' — назва відрізняється",
        "Пакети":    "Немає Meta кампаній",
        "ЗП-проект": "Немає Meta кампаній або не вдалось атрибутувати",
        "Аванс":     "Немає Meta кампаній (МСА кампанії не мають явного патерну)",
    },
    "product_matrix": {
        "Аванс":     "Є в GSC якщо є branded запити; GA4 не дає sessions — тільки events",
    },
}

creds = _get_credentials()
gc = gspread.authorize(creds)
sheet = gc.open_by_key(os.environ["GOOGLE_SHEETS_ID"])

def get_df(tab):
    for name in [f"_data_{tab}", tab]:
        try:
            ws = sheet.worksheet(name)
            vals = ws.get_all_values()
            if len(vals) < 4:
                return pd.DataFrame(), name
            headers = vals[2]
            data = [r for r in vals[3:] if any(v.strip() for v in r)]
            return pd.DataFrame(data, columns=headers), name
        except:
            continue
    return pd.DataFrame(), tab

print("=" * 65)
print("ПЕРЕВІРКА ПРОДУКТІВ ПО ТАБЛИЦЯХ")
print(f"Очікувані продукти: {', '.join(EXPECTED_PRODUCTS)}")
print("=" * 65)

TABS = ["traffic_by_channel", "gsc_keywords", "engagement", "ads_keywords", "meta_ads", "product_matrix"]

for tab in TABS:
    df, ws_name = get_df(tab)
    print(f"\n{'─'*65}")
    print(f"Таблиця: {tab}  [{ws_name}]")

    if df.empty:
        print("  ⚠️  ПОРОЖНЯ або не знайдена")
        continue

    product_col = "product" if "product" in df.columns else None
    if not product_col:
        print("  ⚠️  Колонка 'product' відсутня")
        continue

    # Тижні
    date_col = "week_start" if "week_start" in df.columns else df.columns[0]
    dates = sorted(df[date_col].dropna().unique())
    try:
        dates_sorted = sorted(dates, key=lambda x: datetime.strptime(x.strip(), "%d.%m.%Y"))
        oldest, newest = dates_sorted[0], dates_sorted[-1]
    except:
        oldest, newest = dates[0] if dates else "?", dates[-1] if dates else "?"

    print(f"  Рядків: {len(df)} | Тижнів: {len(dates)} | Діапазон: {oldest} → {newest}")

    present = sorted(df[product_col].dropna().unique().tolist())
    missing = [p for p in EXPECTED_PRODUCTS if p not in present]
    extra   = [p for p in present if p not in EXPECTED_PRODUCTS]

    print(f"  ✅ Є ({len(present)}): {', '.join(present)}")

    if missing:
        print(f"  ❌ Відсутні ({len(missing)}):")
        reasons = ABSENCE_REASONS.get(tab, {})
        for p in missing:
            reason = reasons.get(p, "причина невідома — потрібна перевірка")
            print(f"     • {p}: {reason}")
    else:
        print("  ✅ Всі 7 продуктів присутні")

    if extra:
        print(f"  ℹ️  Додаткові (не в схемі): {', '.join(extra)}")

    # Додаткова статистика для числових колонок
    for col in ["sessions", "total_clicks", "clicks", "spend", "users"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
            per_product = df.groupby(product_col)[col].sum().sort_values(ascending=False)
            print(f"  {col} по продуктах:")
            for p, v in per_product.items():
                flag = "  " if v > 0 else "⚠️"
                print(f"    {flag} {p}: {int(v)}")
            break

print(f"\n{'='*65}")
print("ПОЯСНЕННЯ: що таке Unassigned")
print("─"*65)
print("""
Unassigned = трафік який GA4 не зміг класифікувати в жодну групу.

Чому так буває:
1. Людина перейшла за посиланням БЕЗ UTM-параметрів (не direct, не organic)
   Приклад: хтось надіслав посилання в Telegram/Viber/WhatsApp — GA4 не знає звідки.

2. Реклама запущена без UTM-розмітки — GA4 не розуміє що це Paid трафік.

3. Посилання з мобільних додатків (наприклад сама monobank app веде на web.monobank.ua).

4. Редіректи без збереження UTM (наприклад landing page → onboarding).

Що з цим робити:
• Перевірити чи всі рекламні кампанії (Google Ads, Meta) мають UTM
• Перевірити чи посилання з листів/push-нотифікацій мають utm_source
• В GA4 Unassigned зазвичай 1-5% — якщо більше, це сигнал що є нерозмічені джерела
""")
