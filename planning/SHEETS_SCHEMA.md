# Google Sheets — схема таблиць

> Перед будь-якими змінами в pipeline або коннекторах — звір фактичні колонки з цим документом.
> Після кожного запуску pipeline перевір: `ws.get_all_values()[2]` == очікувані колонки нижче (рядок 3!).

## Структура кожного аркушу

```
Рядок 1: [dropdown ← виберіть метрику] | назва метрики (VLOOKUP) | опис метрики (VLOOKUP)
Рядок 2: (порожній — роздільник)
Рядок 3: заголовки таблиці (bold, frozen)
Рядок 4+: дані (pipeline пише сюди)
Рядки 200+: прихований довідник метрик для VLOOKUP (hidden rows)
```

**Dropdown:** клік на A1 → випадає список метрик → B1 і C1 автоматично показують назву і опис.
**Міграція/налаштування:** `python3.11 scripts/migrate_sheets_dropdown.py`

---

## traffic_by_channel

**Джерело:** GA4 → `get_channel_traffic()` + `get_engagement_full()` → `build_traffic_by_channel()`
**Гранулярність:** 1 рядок = 1 продукт × 1 канал за 1 тиждень (≤28 рядків: 7 продуктів × 4 канали)
**Ключ upsert:** `week_start` + `product` + `channel`

| Колонка | Тип | Звідки | Що означає |
|---|---|---|---|
| `week_start` | DD.MM.YYYY | pipeline | Дата понеділка тижня |
| `product` | string | `get_product_by_url()` | Кластер: ФОП / ЮО / Еквайринг / ЗП-проект / Аванс / Частинами / Пакети |
| `channel` | string | GA4 → нормалізація | Канал: Organic Search, Paid Search, Meta Ads, Direct, Referral |
| `sessions` | int | GA4 `sessions` | Сесії з цього каналу на сторінках продукту за тиждень |
| `users` | int | GA4 `totalUsers` | Унікальні користувачі |
| `pct_of_total` | float | розраховується | Частка від усіх сесій тижня (%) |
| `top_page` | string | GA4 `pagePath` (топ по sessions) | **URL топ-сторінки входу** — куди реально попадають люди |
| `source_note` | string | автогенерується | Текстовий опис рядка |

---

## gsc_keywords

**Джерело:** Google Search Console → `GSCConnector.get_keywords()` → `aggregate_gsc_keywords()`
**Гранулярність:** 1 рядок = 1 продукт × 1 keyword_type (≤14 рядків: 7 продуктів × branded/non-branded)
**Ключ upsert:** `week_start` + `product` + `keyword_type`
**Затримка даних:** ~3 дні від поточної дати

**Принцип кластеризації:** ключові слова — характеристики кластеру. Топ-5 запитів зібрані в `top_keywords` через кому. Окремого рядка на кожен запит немає.

| Колонка | Тип | Звідки | Що означає |
|---|---|---|---|
| `week_start` | DD.MM.YYYY | pipeline | Дата початку тижня |
| `product` | string | `get_product_by_url()` | Кластер |
| `keyword_type` | string | `classify_keyword()` | `branded` / `non-branded` |
| `funnel_stage` | string | `classify_funnel_stage()` | Домінуюча стадія: `awareness` / `consideration` / `decision` |
| `top_keywords` | string | топ-5 запитів через кому | Характеристика кластеру — як клієнти шукають цей продукт |
| `top_keyword` | string | GSC — топ запит по кліках | Запит №1 за кількістю кліків |
| `total_clicks` | int | GSC `clicks` (сума) | Суммарні кліки по всіх запитах кластеру |
| `total_impressions` | int | GSC `impressions` (сума) | Суммарні покази |
| `avg_ctr` | float | GSC `ctr` (середнє) | Середній CTR (%) |
| `avg_position` | float | GSC `position` (середнє) | Середня позиція в пошуку |
| `top_page` | string | GSC `page` (топ по кліках) | **URL сторінки** куди прийшов органічний клік |
| `source_note` | string | автогенерується | Текстовий опис рядка |

---

## engagement

**Джерело:** GA4 → `get_engagement_full()` → `aggregate_engagement()`
**Гранулярність:** 1 рядок = 1 продукт × 1 канал за 1 тиждень (≤28 рядків)
**Ключ upsert:** `week_start` + `product` + `channel`

| Колонка | Тип | Звідки | Що означає |
|---|---|---|---|
| `week_start` | DD.MM.YYYY | pipeline | Дата початку тижня |
| `product` | string | `get_product_by_url()` | Кластер |
| `channel` | string | GA4 `sessionDefaultChannelGroup` | Нормалізований канал |
| `source` | string | GA4 `sessionSource` | Джерело (google, direct тощо) |
| `medium` | string | GA4 `sessionMedium` | Medium (organic, cpc тощо) |
| `campaign` | string | GA4 `sessionCampaignName` | Назва кампанії |
| `sessions` | int | GA4 `sessions` | Сесії |
| `users` | int | GA4 `totalUsers` | Унікальні користувачі |
| `bounce_rate` | float | GA4 `bounceRate` × 100 | Відсоток відмов (%) |
| `avg_session_duration` | float | GA4 `averageSessionDuration` | Середня тривалість сесії (сек) |
| `pages_per_session` | float | GA4 `screenPageViewsPerSession` | Сторінок за сесію |
| `top_page` | string | GA4 `pagePath` (топ по sessions) | **URL найпопулярнішої сторінки** продукту |
| `source_note` | string | автогенерується | Текстовий опис рядка |

---

## ads_keywords

**Джерело:** Google Ads → `GoogleAdsConnector.get_keywords_performance()` → `aggregate_ads_keywords()`
**Гранулярність:** 1 рядок = 1 продукт × 1 funnel_stage (≤21 рядків: 7 продуктів × 3 стадії)
**Ключ upsert:** `week_start` + `product` + `funnel_stage`

**Принцип кластеризації:** ключові слова — характеристики кластеру. Топ-5 слів у `top_keywords` через кому. Product визначається за `landing_url`.

| Колонка | Тип | Звідки | Що означає |
|---|---|---|---|
| `week_start` | DD.MM.YYYY | pipeline | Дата початку тижня |
| `product` | string | `get_product_by_url(landing_url)` | Кластер — визначається за landing URL |
| `funnel_stage` | string | `classify_funnel_stage()` | `awareness` / `consideration` / `decision` |
| `top_keywords` | string | топ-5 ключів через кому | Характеристика кластеру |
| `top_keyword` | string | топ ключ по кліках | Ключ №1 за кількістю кліків |
| `total_clicks` | int | `metrics.clicks` (сума) | Суммарні кліки кластеру |
| `total_impressions` | int | `metrics.impressions` (сума) | Суммарні покази |
| `avg_ctr` | float | розраховується | CTR (%) |
| `total_cost_uah` | float | `metrics.cost_micros` / 1_000_000 (сума) | Витрати в гривнях |
| `landing_url` | string | `ad_group_ad.ad.final_urls[0]` (топ по кліках) | **URL лендингу** — куди веде реклама кластеру |
| `source_note` | string | автогенерується | Текстовий опис рядка |

---

## meta_ads

**Джерело:** Meta Graph API → `MetaAdsConnector.get_campaigns()` → `aggregate_meta_ads()`
**Гранулярність:** 1 рядок = 1 продукт (топ кампанія) (≤7 рядків)
**Ключ upsert:** `week_start` + `product`
**Акаунт:** `act_455699156062655`

| Колонка | Тип | Звідки | Що означає |
|---|---|---|---|
| `week_start` | DD.MM.YYYY | pipeline | Дата початку тижня |
| `product` | string | `_meta_product_from_campaign(campaign_name)` | Кластер — визначається за назвою кампанії |
| `campaign_name` | string | Meta `campaign_name` (топ по spend) | Назва топ-кампанії кластеру |
| `impressions` | int | Meta `impressions` (сума) | Покази |
| `clicks` | int | Meta `clicks` (сума) | Кліки |
| `ctr` | float | розраховується | CTR (%) |
| `spend` | float | Meta `spend` (сума) | Витрати (UAH) |
| `campaign_type` | string | аналіз назви кампанії | `app_install` / `lead_form` / `traffic` — куди веде кампанія |
| `source_note` | string | автогенерується | Текстовий опис рядка |

**Примітка:** Meta не повертає `landing_url` для бізнес-сторінок. Кампанії ведуть на Google Play (app_install) або Lead Form. `product` визначається за патернами в `_META_CAMPAIGN_PRODUCT_MAP` у `traffic.py`.

---

## product_matrix

**Джерело:** GA4 + GSC + Google Ads + Meta Ads → `transforms/product_matrix.py`
**Гранулярність:** 1 рядок = 1 продукт за 1 тиждень (7 рядків — фіксований список кластерів)
**Ключ upsert:** `week_start` + `product`

**Принцип:** Повний маркетинговий портрет продукту в одному рядку. Всі канали в колонках.

| Колонка | Тип | Звідки | Що означає |
|---|---|---|---|
| `week_start` | DD.MM.YYYY | pipeline | Дата початку тижня |
| `product` | string | фіксований список | Кластер (7 продуктів) |
| `sessions` | int | GA4 engagement | Всього сесій |
| `users` | int | GA4 engagement | Унікальні користувачі |
| `bounce_rate` | float | GA4 engagement | Середній відсоток відмов (%) |
| `organic_clicks` | int | GSC | Органічні кліки з Google Search |
| `organic_impressions` | int | GSC | Органічні покази |
| `organic_ctr` | float | GSC | Органічний CTR (%) |
| `top_keyword` | string | GSC | Топ органічний запит за кліками |
| `paid_clicks` | int | Google Ads | Кліки з платного пошуку |
| `paid_impressions` | int | Google Ads | Покази платної реклами |
| `paid_cost_uah` | float | Google Ads | Витрати (UAH) |
| `meta_clicks` | int | Meta Ads | Кліки з Meta |
| `meta_impressions` | int | Meta Ads | Покази Meta |
| `meta_spend` | float | Meta Ads | Витрати Meta (UAH) |
| `top_page` | string | GA4 | **URL топ-сторінки** продукту |
| `source_note` | string | автогенерується | Текстовий опис рядка |
