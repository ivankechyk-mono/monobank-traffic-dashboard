"""
Проверяем: pipeline использует week_start_display как значение колонки
в таблицах. Смотрим что сейчас записано vs что нужно для Looker Studio.
"""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv()

from datetime import datetime, timedelta

today = datetime.today()
last_monday = today - timedelta(days=today.weekday() + 7)
last_sunday = last_monday + timedelta(days=6)

display_current = f"{last_monday.strftime('%d')}–{last_sunday.strftime('%d.%m.%Y')}"
display_fixed = last_monday.strftime("%d.%m.%Y")

print(f"Текущий формат (ПРОБЛЕМА): '{display_current}'")
print(f"Правильный формат (дата понедельника): '{display_fixed}'")
print()
print("Почему понедельник?")
print("  - week_start = начало недели = понедельник")
print("  - Looker Studio читает дату и строит временную шкалу")
print("  - Диапазон DD–DD.MM.YYYY не парсится как дата")
print()

# Проверяем что _parse_display_date в sheets.py умеет парсить новый формат
from src.loaders.sheets import _parse_display_date
test_dates = [display_fixed, "07.07.2026", "2026-07-07"]
for d in test_dates:
    try:
        parsed = _parse_display_date(d)
        print(f"  '{d}' -> {parsed.strftime('%d.%m.%Y')} OK")
    except ValueError as e:
        print(f"  '{d}' -> ОШИБКА: {e}")
