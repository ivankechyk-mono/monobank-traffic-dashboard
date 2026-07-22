import os
from datetime import datetime, timedelta
import gspread
from google.oauth2.credentials import Credentials
import pandas as pd

WEEKS_TO_KEEP = int(os.getenv("WEEKS_TO_KEEP", "40"))


def _parse_display_date(value: str) -> datetime:
    """Парсить дату у форматі DD.MM.YYYY, YYYY-MM-DD або DD–DD.MM.YYYY (тиждень)."""
    # Формат тижня "DD–DD.MM.YYYY" — беремо кінець (дата неділі)
    if "–" in value:
        value = value.split("–")[1]
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Невідомий формат дати: {value}")


def _get_worksheet(sheet_id: str, tab_name: str, credentials: Credentials) -> gspread.Worksheet:
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(sheet_id)
    return spreadsheet.worksheet(tab_name)


def upsert_weekly_snapshot(
    df: pd.DataFrame,
    tab_name: str,
    date_col: str = "date",
    week_start: str = None,
    week_end: str = None,
    credentials: Credentials = None,
    sheet_id: str = None,
) -> None:
    """
    Замінює рядки за поточний тиждень і видаляє старші за WEEKS_TO_KEEP.
    Якщо є аркуш _data_<tab_name> — пише туди (архітектура months filter).
    Рядки 1-2: metrics dropdown (setup_sheets.py), рядок 3: заголовки, рядок 4+: дані.
    week_start / week_end — у форматі DD.MM.YYYY.
    """
    sheet_id = sheet_id or os.getenv("GOOGLE_SHEETS_ID")
    if not sheet_id:
        raise ValueError("GOOGLE_SHEETS_ID не встановлено")

    if df.empty:
        return

    # Якщо є _data_* аркуш — пишемо туди; видимий аркуш містить FILTER формулу
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(sheet_id)
    data_tab = f"_data_{tab_name}"
    try:
        ws = spreadsheet.worksheet(data_tab)
    except Exception:
        ws = spreadsheet.worksheet(tab_name)
    # get_all_values() повертає всі рядки; рядки 1-2 — dropdown/роздільник, рядок 3 — заголовки
    existing = ws.get_all_values()

    # Дані починаються з рядка 4 (індекс 3 у списку)
    HEADER_ROWS = 3  # рядки 1 (dropdown), 2 (порожній), 3 (заголовки)

    if len(existing) < HEADER_ROWS + 1:
        rows_to_keep = []
    else:
        # заголовки в рядку 3 (індекс 2)
        headers = existing[HEADER_ROWS - 1]
        date_col_idx = headers.index(date_col) if date_col in headers else 0
        cutoff = datetime.today() - timedelta(weeks=WEEKS_TO_KEEP)

        week_start_dt = _parse_display_date(week_start) if week_start else None
        week_end_dt = _parse_display_date(week_end) if week_end else None

        rows_to_keep = []
        for row in existing[HEADER_ROWS:]:
            if len(row) <= date_col_idx or not row[date_col_idx]:
                continue
            try:
                row_date = _parse_display_date(row[date_col_idx])
            except ValueError:
                continue
            if row_date < cutoff:
                continue
            if week_start_dt and week_end_dt:
                if week_start_dt <= row_date <= week_end_dt:
                    continue
            rows_to_keep.append(row)

    # Замінюємо NaN/inf на "" щоб не ламати JSON-серіалізацію
    df = df.fillna("").replace([float("inf"), float("-inf")], "")

    new_rows = df.values.tolist()
    # Конвертуємо float без дробової частини в int для чистішого вигляду
    new_rows = [
        [int(v) if isinstance(v, float) and v == int(v) else v for v in row]
        for row in new_rows
    ]
    all_data_rows = rows_to_keep + new_rows

    # Оновлюємо лише рядок заголовків (3) і дані (4+), не чіпаємо рядки 1-2 (dropdown)
    col_count = len(df.columns)
    col_letter = _col_index_to_letter(col_count)
    header_range = f"A3:{col_letter}3"
    data_range = f"A4:{col_letter}{3 + len(all_data_rows)}"

    # Очищаємо зону даних включно зі старими колонками (якщо схема змінилась)
    old_col_count = len(existing[HEADER_ROWS - 1]) if len(existing) >= HEADER_ROWS else col_count
    clear_col_letter = _col_index_to_letter(max(col_count, old_col_count))
    last_data_row = max(len(existing), 3 + len(all_data_rows)) + 10
    ws.batch_clear([f"A3:{clear_col_letter}{last_data_row}"])

    updates = [{"range": header_range, "values": [df.columns.tolist()]}]
    if all_data_rows:
        updates.append({"range": data_range, "values": all_data_rows})

    ws.batch_update(updates)


def _col_index_to_letter(n: int) -> str:
    """Конвертує номер колонки (1-based) в літеру(и): 1→A, 26→Z, 27→AA."""
    result = ""
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        result = chr(65 + remainder) + result
    return result
