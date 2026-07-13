# CLAUDE.md — monobank-traffic-dashboard

## Про проєкт
Python ETL pipeline що щодня вичитує метрики трафіку monobank.ua/business з GA4, Google Search Console і Google Ads, зберігає агреговані дані у Postgres і відображає у Looker Studio дашборді.

**Тип:** Internal analytics tool / ETL pipeline
**Сайт:** monobank.ua/business
**Створено:** 2026-07-13

## При старті кожної сесії
ЗАВЖДИ читай ці файли перед будь-якою дією:
1. `planning/STATE.md` — де зупинились і що відкрито
2. `planning/TASKS.md` — поточна фаза і наступна задача
3. `planning/SPEC.md` — acceptance criteria для поточної story

Тільки після цього виконуй команди або пиши код.

## Tech Stack
- **Python 3.11+** — весь backend
- **Архітектура:** `src/connectors/` → `src/transforms/` → `src/loaders/` → Postgres
- **Google APIs:** google-analytics-data, google-api-python-client, google-ads
- **БД:** PostgreSQL 16 (docker-compose локально)
- **Дашборд:** Looker Studio (підключається до GA4 + Ads напряму + Postgres для матриці)
- **Тести:** pytest + pytest-cov, покриття transforms/ ≥ 80%
- **CI:** GitHub Actions

## Структура проєкту
```
src/
  connectors/    — виклики Google API (GA4, GSC, Ads)
  transforms/    — бізнес-логіка, агрегації (без I/O)
  loaders/       — запис у Postgres
scripts/
  get_google_token.py  — OAuth flow
  run_pipeline.py      — оркестратор
migrations/            — SQL схеми таблиць
tests/
  unit/transforms/
  integration/connectors/
  fixtures/
planning/
  SPEC.md, CONSTITUTION.md, TECH_STACK.md, ROADMAP.md, TASKS.md, STATE.md
```

## Ключові правила (з CONSTITUTION.md)
- Secrets — тільки через env, ніколи в коді
- Google API scopes — тільки readonly
- БД — тільки Postgres, не SQLite
- Один шар — одна відповідальність (connectors/transforms/loaders не змішуються)
- transforms/ покриті тестами ≥ 80%

## Команди
- `/next-task` — взяти наступну задачу з TASKS.md
- `/review` — перевірити щойно написаний код
- `/status` — показати поточний стан проєкту
