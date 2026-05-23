"""
automation.py
Main automation loop: reads IPN values from Excel, searches each in MIA
('Обіймання посад'), ticks the checkbox if found, writes the result back
to Excel. Processes rows in batches of 20 — after each batch confirms in
MIA (Enter) and reopens the search dialog (Insert).

Prerequisites
  1. Run calibrate.py once to create config.json.
  2. Open Excel with your data (first IPN cell calibrated).
  3. Open MIA — 'Обіймання посад' dialog must be visible.
  4. Run:  python automation.py

Safety
  Move the mouse to the TOP-LEFT corner of the screen at any time to abort.
"""

import json
import sys
import time

import pyautogui

from utils.window_manager import focus_spreadsheet, focus_mia
from utils.excel_reader import click_and_read, write_result
from utils.mia_handler import (
    type_ipn,
    wait_tooltip_gone,
    find_blue_row,
    click_checkbox,
    confirm_batch,
)

pyautogui.FAILSAFE = True

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

    ipn_x: int = cfg["ipn_cell_x"]
    ipn_y: int = cfg["ipn_cell_y"]
    row_count: int = cfg.get("row_count", 50)
    batch_size: int = cfg.get("batch_size", 20)
    mia_title: str = cfg.get("mia_title_part", "Обіймання посад")
    cell_tl: list = cfg["mia_ipn_cell_tl"]
    cell_br: list = cfg["mia_ipn_cell_br"]
    cb_offset: list = cfg["mia_checkbox_offset"]
    delays: dict = cfg.get("delays", {})
    win_delay: float = delays.get("window_switch", 0.7)
    tooltip_timeout: float = delays.get("tooltip_timeout", 15.0)

    _print_banner(row_count, batch_size)
    input("Натисни Enter для запуску (відлік 3 секунди)…")
    for i in range(3, 0, -1):
        print(f"  Старт через {i}…", end="\r", flush=True)
        time.sleep(1)
    print()

    found_count = 0
    not_found_count = 0
    log_rows: list[tuple] = []

    try:
        for row in range(row_count):
            label = f"[{row + 1:02d}/{row_count}]"

            # ── 1. Read IPN from Excel ────────────────────────────────
            focus_spreadsheet(delay=win_delay)
            ipn = click_and_read(row, ipn_x, ipn_y,
                                 copy_delay=delays.get("after_copy", 0.4))

            if not ipn or not ipn.isdigit():
                print(f"{label} Порожній рядок або неочікуване значення: {ipn!r} → не знайдено")
                result = "не знайдено"
                not_found_count += 1
                log_rows.append((row + 1, ipn or "", "не знайдено"))
            else:
                print(f"{label} ІПН: {ipn}", flush=True)

                # ── 2. Search in MIA ──────────────────────────────────
                focus_mia(mia_title, delay=win_delay)
                print(f"  → вводимо ІПН у MIA…", flush=True)
                type_ipn(ipn, cell_tl, delays)

                print(f"  → чекаємо завершення пошуку…", flush=True)
                wait_tooltip_gone(mia_title, timeout=tooltip_timeout)

                print(f"  → шукаємо синій рядок…", flush=True)
                row_top_y = find_blue_row(ipn, cell_tl, cell_br, mia_title)

                if row_top_y is not None:
                    print(f"  → ЗНАЙДЕНО ✓ — ставимо галочку…", flush=True)
                    click_checkbox(row_top_y, cell_tl, cb_offset)
                    result = "знайдено"
                    found_count += 1
                    log_rows.append((row + 1, ipn, "знайдено"))
                else:
                    print(f"  → не знайдено")
                    result = "не знайдено"
                    not_found_count += 1
                    log_rows.append((row + 1, ipn, "не знайдено"))

            # ── 3. Write result back to Excel ─────────────────────────
            focus_spreadsheet(delay=win_delay)
            write_result(result)

            # ── 4. Batch confirm (every batch_size rows or at the end) ─
            batch_pos = row + 1
            is_last = (row == row_count - 1)
            if batch_pos % batch_size == 0 or is_last:
                print(f"\n  ── Кінець батчу ({batch_pos}) — підтверджуємо в MIA… ──")
                focus_mia(mia_title, delay=win_delay)
                confirm_batch(delays)
                if not is_last:
                    print(f"  ── Діалог перевідкрито — продовжуємо… ──\n")

    except pyautogui.FailSafeException:
        print("\n\nЗупинено — мишу переміщено у верхній лівий кут (FailSafe).")

    # ── Summary ───────────────────────────────────────────────────────────────
    processed = found_count + not_found_count
    print()
    print("=" * 52)
    print(f"Оброблено  : {processed} / {row_count}")
    print(f"  Знайдено   : {found_count}")
    print(f"  Не знайдено: {not_found_count}")
    print("=" * 52)

    _save_log(log_rows, found_count, not_found_count)
    print(f"Лог збережено → {LOG_FILE}")


def _print_banner(row_count: int, batch_size: int) -> None:
    print("=" * 52)
    print("   Автоматизація екрану — Звірка ІПН у MIA")
    print("=" * 52)
    print(f"Рядків   : {row_count}")
    print(f"Батч     : {batch_size} рядків")
    print()
    print("Перед запуском переконайся:")
    print("  • Excel відкрито з даними")
    print("  • MIA — вікно 'Обіймання посад' відкрите")
    print()
    print("Безпека: перемісти мишу у ВЕРХНІЙ ЛІВИЙ кут для аварійної зупинки.")
    print()


def _save_log(rows: list, found: int, not_found: int) -> None:
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("Результати звірки ІПН\n")
        f.write(f"Знайдено: {found}  |  Не знайдено: {not_found}\n")
        f.write("-" * 38 + "\n")
        f.write(f"{'Рядок':<7} {'ІПН':<13} Статус\n")
        f.write("-" * 38 + "\n")
        for row_num, ipn, status in rows:
            f.write(f"{row_num:<7} {ipn:<13} {status}\n")


if __name__ == "__main__":
    main()

