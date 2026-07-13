# ROADMAP
**Проєкт:** monobank-traffic-dashboard
**Загальна оцінка:** ~14 робочих днів (3 тижні)

---

## Фази

### Фаза 0: Setup (~2д)

**Мета:** Повністю працюючий локальний розвиток і структура репозиторію.

| # | Задача | Критерій завершення |
|---|--------|-------------------|
| 0.1 | Ініціалізувати структуру проєкту: `src/connectors/`, `src/transforms/`, `src/loaders/`, `tests/` | Папки і `__init__.py` присутні |
| 0.2 | `docker-compose.yml` з `postgres:16`; `.env.example` з усіма потрібними змінними | `docker compose up -d` підіймає Postgres; `psql` підключається |
| 0.3 | Перенести `get_google_token.py` → `scripts/get_google_token.py`; CLIENT_SECRET з env | Секрети не в коді; `git-secrets` pre-commit hook встановлено |
| 0.4 | `requirements.txt` з точними версіями (`==`); `Makefile` з таргетами `install`, `test`, `lint` | `make install` встановлює залежності; `make test` запускає `pytest` |
| 0.5 | GitHub Actions CI: `pytest --cov` на кожен push | CI проходить на чистому репо |
| 0.6 | `.gitignore` з усіма credentials-патернами (конституція §Безпека) | `git status` не показує `*.json`, `.env`, `token.*` |

---

### Фаза 1: P1 — Базовий трафік на /business/* (~4д)

**Мета:** Щоденний знімок трафіку по каналах у Postgres + базовий Looker Studio дашборд.

| # | Задача | Критерій завершення |
|---|--------|-------------------|
| 1.1 | `connectors/ga4.py` — клас `GA4Connector`; метод `get_channel_traffic(property_id, date_range, page_filter="/business/")` | Повертає `pd.DataFrame`; smoke-тест з mock проходить |
| 1.2 | `transforms/traffic.py` — функції нормалізації каналів, розрахунок відсотків, дедублікація | Unit-тести ≥ 80% покриття |
| 1.3 | `loaders/postgres.py` — `upsert_daily_snapshot(df, table)` через `psycopg2`; idempotent (ON CONFLICT DO UPDATE) | Повторний запуск не дублює рядки |
| 1.4 | Міграції БД: таблиця `traffic_by_channel_daily` (date, channel, sessions, users, pageviews) | `\d traffic_by_channel_daily` показує коректну схему |
| 1.5 | `scripts/run_pipeline.py` — оркестратор фази 1; викликає connector → transform → loader | `python run_pipeline.py --date yesterday` завершується без помилок; дані в Postgres |
| 1.6 | Looker Studio: підключити GA4 як data source; базовий звіт "Сесії за каналом на /business/*" | Дашборд відкривається; дані відповідають GA4 інтерфейсу |
| 1.7 | Cron: `0 6 * * * python run_pipeline.py --date yesterday` у `crontab.example` | Документовано; запускається вручну успішно |

---

### Фаза 2: P2 — Матриця Продукт×Канал + ключові слова (~4д)

**Мета:** Дані з GSC і Google Ads у Postgres; матриця для аналізу ефективності каналів по продуктах.

| # | Задача | Критерій завершення |
|---|--------|-------------------|
| 2.1 | `connectors/gsc.py` — `GSCConnector`; метод `get_keywords(site_url, date_range, page_filter="/business/")` | Повертає DataFrame з query, page, clicks, impressions, position; smoke-тест проходить |
| 2.2 | `connectors/google_ads.py` — `GoogleAdsConnector`; метод `get_keywords_performance(customer_id, date_range)` | Повертає DataFrame з keyword, campaign, clicks, cost, impressions; smoke-тест проходить |
| 2.3 | `transforms/product_matrix.py` — маппінг URL-паттернів `/business/card`, `/business/credit` тощо → продукти; join GSC + Ads + GA4 | Unit-тести для маппінгу і join-логіки; ≥ 80% покриття |
| 2.4 | Міграції БД: таблиці `gsc_keywords_daily`, `ads_keywords_daily`, `product_channel_matrix_weekly` | Схеми створені; FK і індекси на (date, product) |
| 2.5 | Loaders для GSC і Ads; оновити `run_pipeline.py` щоб включав фазу 2 | Pipeline запускається end-to-end; всі три таблиці наповнені |
| 2.6 | Looker Studio: матриця Продукт×Канал (рядки = продукти, колонки = канали, значення = сесії/кліки) | Матриця відображається; є фільтр по тижню |
| 2.7 | Звіт "Топ-20 ключових слів по продуктах" (GSC + Ads combined view) | Звіт у Looker Studio; джерело — Postgres view `v_top_keywords` |

---

### Фаза 3: P3 — Поведінкові метрики (~3д)

**Мета:** Bounce rate, час на сайті, шляхи користувачів для /business/* у Postgres і Looker Studio.

| # | Задача | Критерій завершення |
|---|--------|-------------------|
| 3.1 | Розширити `connectors/ga4.py`: метод `get_engagement_metrics(property_id, date_range, page_filter)` — bounce_rate, avg_session_duration, pages_per_session | Повертає DataFrame; smoke-тест з mock |
| 3.2 | `connectors/ga4.py`: метод `get_page_paths(property_id, date_range)` — топ вхідних/вихідних сторінок для /business/* | DataFrame з page_path, entrances, exits, pageviews |
| 3.3 | `transforms/engagement.py` — нормалізація, розрахунок cohort-рівнів bounce (low/mid/high), агрегація по каналу | Unit-тести ≥ 80% покриття |
| 3.4 | Міграції БД: таблиці `engagement_daily` (date, channel, page, bounce_rate, avg_duration, pages_per_session) | Схема створена; дані за 30 днів завантажені |
| 3.5 | Looker Studio: дашборд "Поведінка" — scorecard bounce rate по каналах, heatmap сторінок, funnel вхід→конверсія | Дашборд відкривається; значення відповідають GA4 |

---

### Фаза 4: Polish (~1д)

**Мета:** Продакшн-готовність, документація, моніторинг.

| # | Задача | Критерій завершення |
|---|--------|-------------------|
| 4.1 | Smoke-test pipeline: `tests/integration/test_pipeline_smoke.py` — перевіряє що дані за вчора є у всіх таблицях | Тест проходить після кожного запуску pipeline |
| 4.2 | Алерт: якщо pipeline завершився з помилкою або таблиця порожня за поточний день — надіслати email/Slack повідомлення | Помилковий запуск генерує повідомлення |
| 4.3 | `README.md` у проєкті: як запустити локально, як отримати токени, як додати нове джерело | Новий розробник може запустити проєкт за <30 хвилин |
| 4.4 | Перевірити покриття тестами: `pytest --cov=src --cov-fail-under=80` | CI проходить; coverage report показує ≥ 80% |
| 4.5 | Фінальний code review: перевірка секретів, структури шарів, SQL-ін'єкцій | Жодних CONSTITUTION-порушень у git diff |

---

## Ризики

| Ризик | Вірогідність | Вплив | Мітигація |
|-------|-------------|-------|-----------|
| Google Ads Developer Token не верифіковано (затримка до 5 днів) | Висока | Середній — блокує тільки P2 Ads-частину, GSC і GA4 незалежні | Подати заявку на токен у Фазі 0; паралельно розробляти GSC-конектор |
| Зміна структури GA4 events або page_path через редизайн сайту | Середня | Середній — зламає фільтр `/business/*` | Хардкодити path-фільтри окремим конфігом `config/page_filters.py`; unit-тест на парсинг |
| Квоти GA4 API (200K tokens/day, 10 concurrent requests) | Низька | Низький — щоденний batch не наближається до ліміту | Логувати кількість API-запитів; додати `time.sleep(0.1)` між сторінками пагінації |
| GSC затримка даних 2–3 доби | Висока | Низький — відомо заздалегідь | Pipeline для GSC запускає з `--date 3days_ago`; документовано в README |
| Looker Studio PostgreSQL-конектор потребує публічного IP | Середня | Середній — блокує кастомні звіти з Postgres | Альтернатива: BigQuery як проміжний шар або Cloud SQL Auth Proxy |
| Drift між Looker Studio GA4-звітом і Postgres-агрегатами | Середня | Середній — підриває довіру до дашборду | Smoke-тест щодня порівнює сесії з GA4 API і Postgres; допустимий відхил ±2% |
