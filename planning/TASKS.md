# Tasks: monobank-traffic-dashboard
**Проєкт:** monobank-traffic-dashboard
**Дата:** 2026-07-13
**Spec:** planning/SPEC.md | **Plan:** planning/TECH_STACK.md

---

## Фаза 0: Setup (~2д)

**Мета:** Повністю працюючий локальний розвиток, структура репозиторію, секрети в env, CI на місці.

- [x] T001 [S0.1] Ініціалізувати структуру проєкту: `src/connectors/`, `src/transforms/`, `src/loaders/`, `tests/`, `scripts/`, `migrations/`, `config/`  `src/`
- [x] T002 [S0.2] ~~`docker-compose.yml` з postgres~~ — не потрібно, використовуємо Google Sheets; `.env` вже є
- [x] T003 [S0.3] ~~`get_google_token.py`~~ — OAuth flow вбудований у `scripts/check_access.py` і `scripts/setup_sheets.py`; секрети читаються з env
- [x] T004 [S0.4] `requirements.txt` з точними версіями (`==`); `Makefile` з таргетами `install`, `test`, `lint`
- [x] T005 [S0.5] GitHub Actions CI: workflow `.github/workflows/ci.yml`
- [x] T006 [S0.6] `.gitignore` з усіма credentials-патернами
- [x] T007 [S0.7] `config/page_filters.py` — URL-фільтри і маппінг URL → продукти

**Definition of Done:**
- `docker compose up -d` підіймає Postgres; `psql $DATABASE_URL` підключається
- `make install && make test` виконуються без помилок на чистому клоні
- CI проходить на GitHub; `git status` не показує жодного credentials-файлу
- `scripts/get_google_token.py` не містить жодних hardcoded секретів

---

## Фаза 1 — Story 1: Базовий трафік по каналах (P1) (~4д)

**Мета:** Щоденний знімок трафіку по каналах у Postgres + базовий Looker Studio дашборд з фільтром `/business/*`.

**Незалежний тест:** Відкрити Looker Studio дашборд → побачити графік сесій по каналах за останні 30 днів з фільтром на `/business/*`.

- [x] T010 [P1][S1.1] `connectors/ga4.py` — клас `GA4Connector` з методами `get_channel_traffic`, `get_engagement_metrics`, `get_page_paths`
- [x] T011 [P1][S1.2] `transforms/traffic.py` — нормалізація назв каналів, розрахунок `pct_of_total`, дедублікація
- [x] T012 [P1][S1.3] `loaders/sheets.py` — `upsert_weekly_snapshot(df, tab_name)` з автоочисткою старших за 40 тижнів
- [x] T013 [P1][S1.4] ~~Міграція БД~~ — не потрібно, використовуємо Google Sheets
- [x] T014 [P1][S1.5] `scripts/run_pipeline.py` — оркестратор; запускається щотижня через GitHub Actions
- [ ] T015 [P1][S1.6] Unit-тести для `connectors/ga4.py` і `transforms/traffic.py` з mock GA4 відповідями; покриття ≥ 80%  `tests/unit/test_ga4.py`, `tests/unit/test_traffic.py`
- [ ] T016 [P1][S1.7] Looker Studio: підключити GA4 як data source; базовий звіт "Сесії за каналом на /business/*" з таблицею (Канал, Сесії, Користувачі, %) і date range picker  *(Looker Studio — зовнішній ресурс, URL у README)*
- [ ] T017 [P1][S1.8] `crontab.example` з записом `0 6 * * * python scripts/run_pipeline.py --date yesterday`; документація запуску вручну  `crontab.example`

**Definition of Done:**
- `python scripts/run_pipeline.py --date yesterday` завершується без помилок
- Таблиця `traffic_by_channel_daily` містить ≥1 рядок з датою вчора і `sessions > 0` для Organic Search
- Повторний запуск за ту саму дату не дублює рядки (перевірити `SELECT COUNT(*) GROUP BY date, channel`)
- Looker Studio дашборд відкривається і дані відповідають GA4 інтерфейсу
- `make test` проходить; coverage ≥ 80% для модулів фази 1

---

## Фаза 2 — Story 2: Матриця Продукт×Канал + ключові слова (P2) (~4д)

**Мета:** Дані з GSC і Google Ads у Postgres; матриця для аналізу ефективності каналів по продуктах (ЮО, ФОП, Еквайринг, ЗП-проект).

**Незалежний тест:** Відкрити звіт "Матриця" в Looker Studio → побачити рядки ЮО/ФОП/Еквайринг/ЗП-проект і колонки по каналах з метриками сесій і кліків.

- [ ] T020 [P2][S2.1] `connectors/gsc.py` — `GSCConnector`; метод `get_keywords(site_url, date_range, page_filter="/business/")` → DataFrame(query, page, clicks, impressions, ctr, position)  `src/connectors/gsc.py`
- [ ] T021 [P2][S2.2] `connectors/google_ads.py` — `GoogleAdsConnector`; метод `get_keywords_performance(customer_id, date_range)` → DataFrame(keyword, campaign, clicks, cost, impressions)  `src/connectors/google_ads.py`
- [ ] T022 [P2][S2.3] `transforms/product_matrix.py` — маппінг URL-паттернів (`/business/card`, `/business/credit`, `/business/fop`, `/business/acquiring`, `/business/salary`) → продукти; join GSC + Ads + GA4; fallback "Unknown product" для нерозпізнаних URL  `src/transforms/product_matrix.py`
- [ ] T023 [P2][S2.4] Міграції БД: `migrations/002_create_gsc_ads_tables.sql` — таблиці `gsc_keywords_daily(date, query, page, clicks, impressions, ctr, position)`, `ads_keywords_daily(date, keyword, campaign, clicks, cost, impressions)`, `product_channel_matrix_weekly(week_start, product, channel, sessions, clicks)`; FK і індекси на `(date, product)`  `migrations/002_create_gsc_ads_tables.sql`
- [ ] T024 [P2][S2.5] `loaders/gsc_loader.py` і `loaders/ads_loader.py` — upsert для нових таблиць; оновити `scripts/run_pipeline.py` щоб включав фазу 2 (`--phase p2` або `--phase all`)  `src/loaders/gsc_loader.py`, `src/loaders/ads_loader.py`, `scripts/run_pipeline.py`
- [ ] T025 [P2][S2.6] Postgres view `v_top_keywords`: `CREATE OR REPLACE VIEW v_top_keywords AS ...` — топ-20 GSC + топ-20 Ads, поле `source` = 'GSC' | 'Ads'  `migrations/003_create_views.sql`
- [ ] T026 [P2][S2.7] Unit-тести для `connectors/gsc.py`, `connectors/google_ads.py`, `transforms/product_matrix.py` з mock відповідями; покриття ≥ 80%  `tests/unit/test_gsc.py`, `tests/unit/test_google_ads.py`, `tests/unit/test_product_matrix.py`
- [ ] T027 [P2][S2.8] Looker Studio: матриця Продукт×Канал (рядки = продукти, колонки = канали, значення = сесії/кліки); фільтр по тижню; окремий звіт "Топ-20 ключових слів" з джерела `v_top_keywords`  *(Looker Studio — зовнішній ресурс, URL у README)*

**Definition of Done:**
- `python scripts/run_pipeline.py --date 3days_ago --phase p2` завершується без помилок (GSC із затримкою 3 доби)
- `gsc_keywords_daily` містить рядки з `page` виключно для `/business/*` URL
- `product_channel_matrix_weekly` містить рядки для всіх 4 продуктів
- Нерозпізнаний URL повертає "Unknown product" (не падає з помилкою)
- Looker Studio матриця відображає всі 4 продукти; є фільтр по тижню

---

## Фаза 3 — Story 3: Поведінкові метрики (P3) (~3д)

**Мета:** Bounce rate, середній час на сторінці, топ сторінок для `/business/*` у Postgres і Looker Studio.

**Незалежний тест:** Відкрити дашборд "Поведінка" → побачити bounce rate по каналах і топ-10 сторінок за кількістю сесій.

- [ ] T030 [P3][S3.1] Розширити `connectors/ga4.py`: метод `get_engagement_metrics(property_id, date_range, page_filter)` → DataFrame(date, channel, bounce_rate, avg_session_duration, pages_per_session)  `src/connectors/ga4.py`
- [ ] T031 [P3][S3.2] Розширити `connectors/ga4.py`: метод `get_page_paths(property_id, date_range, page_filter="/business/")` → DataFrame(page_path, entrances, exits, pageviews)  `src/connectors/ga4.py`
- [ ] T032 [P3][S3.3] `transforms/engagement.py` — нормалізація, розрахунок cohort-рівнів bounce (low <30%, mid 30-60%, high >60%), агрегація по каналу і сторінці  `src/transforms/engagement.py`
- [ ] T033 [P3][S3.4] Міграція БД: `migrations/004_create_engagement_daily.sql` — таблиця `engagement_daily(date, channel, page_path, bounce_rate, avg_duration_sec, pages_per_session, entrances, exits, pageviews)`  `migrations/004_create_engagement_daily.sql`
- [ ] T034 [P3][S3.5] Оновити `scripts/run_pipeline.py`: додати фазу 3 (`get_engagement_metrics` + `get_page_paths` → `engagement_daily`); loader з `ON CONFLICT DO UPDATE`  `scripts/run_pipeline.py`
- [ ] T035 [P3][S3.6] Unit-тести для нових методів `ga4.py` і `transforms/engagement.py`; покриття ≥ 80%  `tests/unit/test_engagement.py`
- [ ] T036 [P3][S3.7] Looker Studio: дашборд "Поведінка" — scorecard (Bounce Rate, Avg. Duration, Pages/Session з порівнянням до попереднього тижня); таблиця топ-10 `/business/*` сторінок; фільтр по каналу  *(Looker Studio — зовнішній ресурс, URL у README)*

**Definition of Done:**
- `python scripts/run_pipeline.py --date yesterday --phase p3` завершується без помилок
- `engagement_daily` містить дані за 30 днів (завантажити backfill при першому запуску)
- Scorecard показує bounce rate з порівнянням до попереднього тижня (+/- %)
- Фільтр "Paid Search" у дашборді показує bounce rate лише для Ads-трафіку
- `make test` проходить; coverage ≥ 80% для модулів фази 3

---

## Фаза 4: Polish (~1д)

**Мета:** Продакшн-готовність: smoke-тест, алерт, документація, code review.

- [ ] T040 [S4.1] `tests/integration/test_pipeline_smoke.py` — перевіряє що в `traffic_by_channel_daily`, `gsc_keywords_daily`, `ads_keywords_daily`, `engagement_daily` є рядки за вчора; перевіряє відхил між GA4 API і Postgres ≤ 2%  `tests/integration/test_pipeline_smoke.py`
- [ ] T041 [S4.2] Алерт: `scripts/check_pipeline_health.py` — якщо таблиця порожня за поточний день або pipeline завершився з помилкою → надіслати email або Slack webhook; інтегрувати у `run_pipeline.py`  `scripts/check_pipeline_health.py`
- [ ] T042 [S4.3] `README.md`: розділи "Як запустити локально", "Як отримати Google токени", "Як додати нове джерело даних", "Looker Studio: посилання і структура"  `README.md`
- [ ] T043 [S4.4] Перевірити покриття: `pytest --cov=src --cov-fail-under=80`; виправити gap-тести якщо coverage < 80%  `tests/`
- [ ] T044 [S4.5] Фінальний code review: перевірка відсутності hardcoded секретів (`grep -r "client_secret\|password\|token" src/`), SQL-параметризація (не f-string у запитах), структура шарів (connectors не імпортують loaders)  *(code review — ревізія коду, не файл)*

**Definition of Done:**
- `tests/integration/test_pipeline_smoke.py` проходить після кожного запуску pipeline
- Помилковий запуск pipeline генерує Slack/email повідомлення
- Новий розробник може запустити проєкт локально за <30 хвилин, слідуючи README
- `pytest --cov=src --cov-fail-under=80` проходить у CI
- `grep -r "client_secret\|password" src/` — пустий результат

---

## Dependency Graph

```
T001 → T002 → T003 → T004 → T005 → T006 → T007
                                              ↓
T007 → T010 → T011 → T012 → T013 → T014 → T015 → T016 → T017
                                              ↓
T017 → T020 → T021 → T022 → T023 → T024 → T025 → T026 → T027
                                              ↓
T027 → T030 → T031 → T032 → T033 → T034 → T035 → T036
                                              ↓
T036 → T040 → T041 → T042 → T043 → T044
```

Ключові залежності:
- T013 (міграція БД) → T012 (loader) — loader потребує існуючої таблиці
- T014 (run_pipeline.py) → T010, T011, T012, T013 — оркестратор потребує всіх компонентів фази 1
- T024 (loaders P2) → T023 (міграції P2) — аналогічно
- T025 (view v_top_keywords) → T023 (таблиці GSC і Ads) — view будується поверх таблиць
- T040 (smoke-test) → T034 (pipeline фази 3) — тест перевіряє повний pipeline

---

## Паралельне виконання

**Можна паралельно:**
- T001–T006 (Setup) — більшість незалежні між собою, окрім T003 (потребує T001)
- T010 (GA4 connector) і T011 (transforms) — розробка паралельно, інтеграція потім
- T020 (GSC connector) і T021 (Ads connector) — повністю незалежні один від одного
- T030 і T031 (два нові методи GA4) — можна розробляти паралельно
- T042 (README) і T043 (coverage) — незалежні задачі polish-фази

**Строго послідовно:**
- Фази 0 → 1 → 2 → 3 → 4 (кожна фаза залежить від попередньої)
- T013 (міграція) → T012 (loader) → T014 (pipeline)
- T023 (міграції P2) → T024 (loaders P2) → T025 (view)
- T033 (міграція P3) → T034 (pipeline P3) → T040 (smoke-test)
- T040 → T041 → T044 (фінальна перевірка лише після повного pipeline)
