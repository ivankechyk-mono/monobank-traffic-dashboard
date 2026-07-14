# STATE

**Статус:** in_progress
**Поточна фаза:** 1 — Базовий трафік
**Остання дія:** GSC connector розширено на всі бізнес-сторінки (2026-07-14)

## Що зроблено
- [x] Фаза 0 — структура проєкту, CI, requirements, .gitignore
- [x] Google Sheets створено (5 аркушів)
- [x] GA4 connector — трафік по каналах, engagement, топ сторінок
- [x] transforms/traffic.py — нормалізація каналів, pct_of_total
- [x] loaders/sheets.py — upsert з автоочисткою 40 тижнів
- [x] scripts/run_pipeline.py — оркестратор
- [x] GitHub Actions — автозапуск щопонеділка 06:00 UTC
- [x] GSC connector — ключові слова по всіх бізнес-сторінках (876 ключів/тиждень)
- [x] Перший реальний запис даних у Google Sheets

## Що зараз в Sheets
| Аркуш | Статус | Рядків |
|---|---|---|
| traffic_by_channel | ✅ є дані | 9 каналів |
| gsc_keywords | ✅ є дані | 876 ключових слів |
| engagement | ✅ є дані | 10 каналів + 50 сторінок |
| ads_keywords | ⏳ чекаємо Ads | порожній |
| product_matrix | ⏳ чекаємо Ads | порожній |

## Заблоковані задачі (чекаємо доступів)
- Google Ads — Developer Token від ментора (T021, T021b, T021c)
- Meta Ads — System User Token від ментора (T050, T051)
- LinkedIn Ads — верифікація LinkedIn App (T060, T061)
- GA4 конверсії — перевірка events налаштування (T070, T071)

## Наступний крок (не заблокований)
- T015 — unit-тести для ga4.py і transforms/traffic.py
- T016 — підключити Looker Studio до Google Sheets
- Уточнити у ментора GA4 property для monobank.ua (публічний сайт)
