# STATE

**Статус:** in_progress
**Поточна фаза:** 1 — Базовий трафік
**Остання дія:** T015 виконано — unit-тести traffic.py 35/35, покриття 84% (2026-07-22)

## Що зроблено
- [x] Фаза 0 — структура проєкту, CI, requirements, .gitignore
- [x] Google Sheets створено (5 аркушів + product_matrix)
- [x] GA4 connector — трафік по каналах, engagement, топ сторінок
- [x] transforms/traffic.py — нормалізація каналів, pct_of_total
- [x] loaders/sheets.py — upsert з автоочисткою 40 тижнів
- [x] scripts/run_pipeline.py — оркестратор
- [x] GitHub Actions — автозапуск щопонеділка 06:00 UTC
- [x] GSC connector — ключові слова по всіх бізнес-сторінках
- [x] Google Ads connector — ключові слова, кампанії (customer_id: 8339173472)
- [x] Meta Ads connector — кампанії (act_455699156062655)
- [x] planning/SHEETS_SCHEMA.md — точна схема всіх аркушів з колонками і джерелами
- [x] Аудит даних — знайдено і виправлено 4 критичні баги:
  - формат дат DD–DD.MM.YYYY → DD.MM.YYYY (run_pipeline.py, backfill.py)
  - users = count(рядків) → sum(users з GA4) (traffic.py:120)
  - avg_ctr невзважений → clicks/impressions (traffic.py:231)
  - Кабінет виключено з маркетингового трафіку (traffic.py:118, 411)
- [x] Backfill 40 тижнів запущено з виправленими даними (in progress)
- [x] T015 — unit-тести tests/unit/test_traffic.py: 35 тестів, покриття 84%

## Що зараз в Sheets
| Аркуш | Статус | Рядків | Колонки |
|---|---|---|---|
| traffic_by_channel | ✅ backfill in progress | — | week_start, product, channel, sessions, users, pct_of_total, top_page, source_note |
| gsc_keywords | ✅ backfill in progress | — | week_start, product, keyword_type, dominant_intent, top_keywords, top_keyword, total_clicks, total_impressions, avg_ctr, avg_position, top_page, source_note |
| engagement | ✅ backfill in progress | — | week_start, product, channel, source, medium, campaign, sessions, users, bounce_rate, avg_session_duration, pages_per_session, top_page, source_note |
| ads_keywords | ✅ backfill in progress | — | week_start, product, funnel_stage, top_keywords, top_keyword, total_clicks, total_impressions, avg_ctr, total_cost_uah, landing_url, source_note |
| meta_ads | ✅ backfill in progress | — | week_start, product, campaign_name, impressions, clicks, ctr, spend, campaign_type, source_note |
| product_matrix | ✅ backfill in progress | — | week_start, product, sessions, users, bounce_rate, organic_clicks, organic_impressions, organic_ctr, top_keyword, paid_clicks, paid_impressions, paid_cost_uah, meta_clicks, meta_impressions, meta_spend, top_page, source_note |

## Заблоковані задачі
- Google Ads Developer Token — є, але статус верифікації невідомий

## Наступний крок
- T016 — підключити Looker Studio до Google Sheets, побудувати єдиний звіт
