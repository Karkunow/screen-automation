"""
automation.py
Main automation loop: reads IPN values from Numbers/Excel via the clipboard,
searches each one in Google Sheets (Chrome) via Ctrl+F, and marks found
entries by toggling their checkbox.

Prerequisites
  1. Run generate_data.py to create the CSV files.
  2. Manually import big_list.csv into Google Sheets (col C → Checkbox format).
  3. Manually import small_list.csv into Numbers (Mac) or Excel (Windows).
  4. Run calibrate.py once to create config.json.
  5. Open both applications and make sure:
       • Numbers/Excel — small_list data visible, cursor anywhere is fine.
       • Chrome        — big_list Google Sheets tab is the active tab.
  6. Run this script:  python automation.py

Safety
  Move the mouse to the TOP-LEFT corner of the screen at any time to abort.
"""

import json
import sys
import time

import pyautogui

from utils.window_manager import focus_spreadsheet, focus_browser
from utils.excel_reader import click_and_read, write_result
from utils.sheets_handler import (
    set_checkbox_offset,
    open_find,
    is_found,
    mark_found,
    close_find,
)

pyautogui.FAILSAFE = True  # top-left corner raises FailSafeException → clean stop

CONFIG_FILE = "config.json"
LOG_FILE = "results_log.txt"


# ── Config ────────────────────────────────────────────────────────────────────

def _load_config() -> dict:
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"ПОМИЛКА: файл {CONFIG_FILE} не знайдено. Спочатку запусти calibrate.py.")
        sys.exit(1)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    cfg = _load_config()

    x: int = cfg["ipn_cell_x"]
    y: int = cfg["ipn_cell_y"]
    row_count: int = cfg.get("row_count", 50)
    chrome_title: str = cfg.get("chrome_title_part", "")
    delays: dict = cfg.get("delays", {})
    win_delay: float = delays.get("window_switch", 0.7)

    set_checkbox_offset(cfg.get("checkbox_offset", 1))

    _print_banner(row_count)
    input("Натисни Enter для запуску (відлік 3 секунди)…")

    for i in range(3, 0, -1):
        print(f"  Старт через {i}…", end="\r", flush=True)
        time.sleep(1)
    print()

    found_count = 0
    not_found_count = 0
    skipped_count = 0
    log_rows: list[tuple] = []

    try:
        for row in range(0, row_count):
            label = f"[{row + 1:02d}/{row_count}]"

            # ── 1. Read IPN from Numbers / Excel ─────────────────────
            focus_spreadsheet(delay=win_delay)

            ipn = click_and_read(row, x, y, copy_delay=delays.get("after_copy", 0.4))

            if not ipn or not ipn.isdigit():
                print(f"{label} ПОМИЛКА — неочікуване значення з буфера: {ipn!r}")
                print("Зупиняємо. Перевір що Numbers відкритий і вікно не перекрите.")
                break

            print(f"{label} ІПН: {ipn}", flush=True)

            # ── 2. Search in Google Sheets ────────────────────────────
            print(f"  → перемикаємо на Chrome…", flush=True)
            focus_browser(chrome_title, delay=win_delay)
            print(f"  → відкриваємо пошук Ctrl+F…", flush=True)
            open_find(ipn, delays)

            # ── 3. Act on result ──────────────────────────────────────
            print(f"  → перевіряємо результат…", flush=True)
            found = is_found()
            print(f"  → is_found повернув: {found}", flush=True)
            if found:
                mark_found(delays)
                found_count += 1
                print(f"  → ЗНАЙДЕНО ✓")
                log_rows.append((row + 1, ipn, "знайдено"))
            else:
                close_find()
                not_found_count += 1
                print(f"  → не знайдено")
                log_rows.append((row + 1, ipn, "не знайдено"))

            # ── 4. Write result back to Numbers column C ──────────────
            result_text = "Так" if found else "Ні"
            print(f"  → повертаємось до Numbers, пишемо '{result_text}'…", flush=True)
            focus_spreadsheet(delay=win_delay)
            write_result(result_text)

    except pyautogui.FailSafeException:
        print("\n\nЗупинено — мишу переміщено у верхній лівий кут (FailSafe).")

    # ── Summary ───────────────────────────────────────────────────────────────
    processed = found_count + not_found_count + skipped_count
    print()
    print("=" * 52)
    print(f"Оброблено  : {processed} / {row_count}")
    print(f"  Знайдено   : {found_count}")
    print(f"  Не знайдено: {not_found_count}")
    print(f"  Пропущено  : {skipped_count}")
    print("=" * 52)

    _save_log(log_rows, found_count, not_found_count, skipped_count)
    print(f"Лог збережено → {LOG_FILE}")


def _print_banner(row_count: int) -> None:
    platform_label = "macOS  (Numbers + Chrome)" if sys.platform == "darwin" else "Windows  (Excel + Chrome)"
    print("=" * 52)
    print("   Автоматизація екрану — Звірка ІПН")
    print("=" * 52)
    print(f"Платформа: {platform_label}")
    print(f"Рядків   : {row_count}")
    print()
    print("Перед запуском переконайся:")
    print("  • Numbers/Excel — відкрито з даними small_list")
    print("  • Chrome        — активна вкладка з Google Sheets (big_list)")
    print()
    print("Безпека: перемісти мишу у ВЕРХНІЙ ЛІВИЙ кут для аварійної зупинки.")
    print()


def _save_log(rows: list, found: int, not_found: int, skipped: int) -> None:
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"Результати звірки ІПН\n")
        f.write(f"Знайдено: {found}  |  Не знайдено: {not_found}  |  Пропущено: {skipped}\n")
        f.write("-" * 38 + "\n")
        f.write(f"{'Рядок':<7} {'ІПН':<13} Статус\n")
        f.write("-" * 38 + "\n")
        for row_num, ipn, status in rows:
            f.write(f"{row_num:<7} {ipn:<13} {status}\n")


if __name__ == "__main__":
    main()
