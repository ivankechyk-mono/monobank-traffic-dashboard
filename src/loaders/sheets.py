import os
from datetime import datetime, timedelta
import gspread
from google.oauth2.credentials import Credentials
import pandas as pd

WEEKS_TO_KEEP = int(os.getenv("WEEKS_TO_KEEP", "40"))


def _get_worksheet(sheet_id: str, tab_name: str, credentials: Credentials) -> gspread.Worksheet:
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(sheet_id)
    return spreadsheet.worksheet(tab_name)


def upsert_weekly_snapshot(
    df: pd.DataFrame,
    tab_name: str,
    week_start_col: str = "week_start",
    credentials: Credentials = None,
    sheet_id: str = None,
) -> None:
    sheet_id = sheet_id or os.getenv("GOOGLE_SHEETS_ID")
    if not sheet_id:
        raise ValueError("GOOGLE_SHEETS_ID не встановлено")

    ws = _get_worksheet(sheet_id, tab_name, credentials)

    existing = ws.get_all_values()
    if not existing or len(existing) < 2:
        rows_to_keep = []
    else:
        headers = existing[0]
        week_col_idx = headers.index(week_start_col) if week_start_col in headers else 0
        cutoff = (datetime.today() - timedelta(weeks=WEEKS_TO_KEEP)).strftime("%Y-%m-%d")

        week_start = df[week_start_col].iloc[0]
        rows_to_keep = [
            row for row in existing[1:]
            if len(row) > week_col_idx
            and row[week_col_idx] >= cutoff
            and row[week_col_idx] != week_start
        ]

    new_rows = df.values.tolist()
    all_rows = rows_to_keep + new_rows

    ws.clear()
    headers = df.columns.tolist()
    ws.update([headers] + all_rows)
