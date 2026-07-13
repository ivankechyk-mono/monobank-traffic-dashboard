# TECH STACK
**Проєкт:** monobank-traffic-dashboard
**Дата:** 2026-07-13

---

## Обраний підхід

**ETL pipeline на чистому Python + Postgres + Looker Studio**

Мінімальний стек без фреймворків оркестрації: Python-скрипти у трьох шарах (`connectors/` → `transforms/` → `loaders/`) вичитують дані з GA4, GSC і Google Ads API, трансформують і зберігають агреговані метрики у Postgres. Looker Studio підключається напряму до GA4 і Google Ads для real-time дашбордів; Postgres слугує для кастомних звітів (матриця Продукт×Канал, поведінкові агрегати), де прямих конекторів недостатньо. Cron або Cloud Scheduler запускають pipeline щодня. Підхід обраний тому що: команда вже має OAuth-токени, нові залежності мінімальні, кожен шар тестується ізольовано.

---

## Технології

| Шар | Технологія | Версія | Причина вибору |
|-----|-----------|--------|----------------|
| **Runtime** | Python | 3.11+ | Зафіксовано конституцією; підтримка `match`, `tomllib`, сучасний `asyncio` |
| **GA4 connector** | `google-analytics-data` | 0.18.x | Офіційна бібліотека Google для GA4 Data API v1 |
| **GSC connector** | `google-api-python-client` | 2.x | Єдиний офіційний клієнт для Search Console API v1 |
| **Google Ads connector** | `google-ads` | 24.x | Офіційний Python-клієнт; підтримує GAQL-запити для звітів по кампаніях і ключових словах |
| **Auth** | `google-auth`, `google-auth-oauthlib` | 2.x | Автоматична ротація refresh-токенів; вже використовується в `get_google_token.py` |
| **Трансформації** | `pandas` | 2.x | Зручна робота з DataFrame при агрегації метрик; замінюється на `polars` якщо обсяг перевищить 10M рядків |
| **База даних** | PostgreSQL | 16 | Зафіксовано конституцією; JSONB для зберігання raw-знімків; window-функції для розрахунку трендів |
| **DB-драйвер** | `psycopg2-binary` | 2.9.x | Синхронний драйвер достатній для щоденного batch-завантаження |
| **ORM / query builder** | без ORM, чистий SQL | — | Pipeline простий; ORM додає складність без користі |
| **Конфігурація** | `python-dotenv` | 1.x | Читання `.env` локально; у продакшні — env-змінні напряму |
| **Контейнеризація** | Docker + `docker-compose` | 24.x / 2.x | Обов'язково за конституцією; `postgres:16` сервіс для локального розробу |
| **Тести** | `pytest` + `pytest-cov` + `unittest.mock` | 8.x / 5.x | Зафіксовано конституцією; покриття ≥ 80% через `pytest-cov` |
| **Планувальник** | `cron` (локально) / Cloud Scheduler (прод) | — | Простий cron достатній для щоденного запуску; без Celery/RQ для MVP |
| **Візуалізація** | Looker Studio | — | Вбудований конектор до GA4 і Google Ads; кастомні звіти через BigQuery або PostgreSQL-конектор |
| **Secrets** | env-змінні + `.env` (тільки локально) | — | Зафіксовано конституцією; `git-secrets` pre-commit hook |
| **CI** | GitHub Actions | — | Запуск `pytest --cov` та перевірка coverage на кожен PR |
| **Логування** | `logging` (stdlib) | — | Достатньо для batch-job; структуровані логи у JSON для продакшну через `python-json-logger` |

---

## Альтернативи що розглядались

### Apache Airflow як оркестратор

**Плюси:**
- Граф залежностей між tasks (DAG) — зручно якщо pipeline розростеться
- Вбудований retry, alerting, web UI для моніторингу запусків
- Великий ecosystem операторів для Google API

**Мінуси:**
- Важкий для MVP: потребує окремого сервера, Redis або Celery, складний setup
- Overhead на навчання команди; конституція забороняє Celery/RQ для MVP
- Надмірно для щоденного pipeline з 3 джерелами і ~10 задачами
- Локально потребує окремого `docker-compose` сервісу

**Рішення:** відхилено. Повернутись до Airflow при переході в продакшн якщо pipeline перевищить 10 джерел або з'явиться потреба в retry-логіці.

---

## Залежності від третіх сторін

| Сервіс | Тип доступу | Credentials | Ризик відмови |
|--------|------------|-------------|--------------|
| GA4 Data API v1 | OAuth 2.0 read-only | `GOOGLE_CREDENTIALS_PATH` + `GOOGLE_REFRESH_TOKEN` | Зміна квот Google (10K requests/day free tier) |
| Google Search Console API | OAuth 2.0 read-only | Той самий OAuth токен | Затримка даних 2–3 доби для impressions/clicks |
| Google Ads API | OAuth 2.0 + Developer Token | `GOOGLE_ADS_DEVELOPER_TOKEN`, `GOOGLE_ADS_CUSTOMER_ID` | Developer token потребує верифікації Google (до 5 робочих днів) |
| PostgreSQL (Cloud SQL / Supabase) | TCP + SSL | `DATABASE_URL` | SLA залежить від провайдера; локально — Docker |
| Looker Studio | Вбудований конектор | Сервісний акаунт або OAuth | Безкоштовний tier; немає SLA для кастомних конекторів |
