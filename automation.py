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

import datetime
import io
import json
import sys
import time

# Frozen exe on Windows defaults to cp1251 — force UTF-8 so Ukrainian text prints correctly.
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

import pyautogui

from utils.tesseract_path import setup as _setup_tesseract
_setup_tesseract()  # must run before any pytesseract call; no-op outside frozen exe

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
    col_br: list | None = cfg.get("mia_ipn_col_br")
    cb_offset: list = cfg["mia_checkbox_offset"]
    delays: dict = cfg.get("delays", {})
    win_delay: float = delays.get("window_switch", 0.7)
    tooltip_timeout: float = delays.get("tooltip_timeout", 15.0)

    _print_banner(row_count, batch_size)
    print(f"[CFG] Excel IPN клітинка : ({ipn_x},{ipn_y})")
    print(f"[CFG] MIA cell_tl        : {cell_tl}")
    print(f"[CFG] MIA cell_br        : {cell_br}")
    print(f"[CFG] MIA col_br         : {col_br if col_br else '(не скалібрований — fallback 75%)'}")
    print(f"[CFG] checkbox_offset    : {cb_offset}")
    print(f"[CFG] mia_title          : {mia_title!r}")
    print(f"[CFG] batch_size         : {batch_size}")
    print(f"[CFG] tooltip_timeout    : {tooltip_timeout}s")
    print(f"[CFG] затримки           : {delays}")
    print()
    for i in range(3, 0, -1):
        print(f"  Старт через {i}…", end="\r", flush=True)
        time.sleep(1)
    print()

    start_time = datetime.datetime.now()
    print(f"[ЧАС] Початок: {start_time.strftime('%H:%M:%S')}")
    print()

    found_count = 0
    not_found_count = 0
    consecutive_not_found = 0
    MAX_CONSECUTIVE_NOT_FOUND = 10
    log_rows: list[tuple] = []

    try:
        for row in range(row_count):
            label = f"[{row + 1:02d}/{row_count}]"

            # ── 1. Read IPN from Excel ────────────────────────────────
            print(f"{label} ─────────────────────────────")
            print(f"{label} [XLS] читаємо ІПН з Excel рядок {row+1}...")
            focus_spreadsheet(delay=win_delay)
            ipn = click_and_read(row, ipn_x, ipn_y,
                                 copy_delay=delays.get("after_copy", 0.4))
            print(f"{label} [XLS] отримано з буфера: {ipn!r}")

            if not ipn or not ipn.isdigit():
                result = "не знайдено"
                not_found_count += 1
                consecutive_not_found += 1
                log_rows.append((row + 1, ipn or "", "не знайдено"))
            else:
                print(f"{label} ІПН: {ipn}", flush=True)

                # ── 2. Search in MIA (до 2 спроб) ────────────────────
                focus_mia(mia_title, delay=win_delay)
                row_top_y = None
                for attempt in range(1, 3):
                    print(f"  → вводимо ІПН у MIA… (спроба {attempt})", flush=True)
                    type_ipn(ipn, cell_tl, cell_br, delays)

                    print(f"  → чекаємо завершення пошуку…", flush=True)
                    wait_tooltip_gone(mia_title, timeout=tooltip_timeout,
                                      cell_tl=cell_tl, cell_br=cell_br)

                    print(f"  → шукаємо синій рядок…", flush=True)
                    row_top_y = find_blue_row(ipn, cell_tl, cell_br, mia_title, col_br=col_br)

                    if row_top_y is not None:
                        break
                    if attempt < 2:
                        print(f"  → не знайдено з першої спроби — повторюємо…", flush=True)

                if row_top_y is not None:
                    print(f"  → ЗНАЙДЕНО ✓ — ставимо галочку…", flush=True)
                    click_checkbox(row_top_y, cell_tl, cb_offset, mia_title)
                    result = "знайдено"
                    found_count += 1
                    consecutive_not_found = 0
                    log_rows.append((row + 1, ipn, "знайдено"))
                else:
                    print(f"  → не знайдено")
                    result = "не знайдено"
                    not_found_count += 1
                    consecutive_not_found += 1
                    log_rows.append((row + 1, ipn, "не знайдено"))

            # ── 3. Write result back to Excel ─────────────────────────
            focus_spreadsheet(delay=win_delay)
            write_result(result)

            # ── Check consecutive not-found limit ─────────────────────
            if consecutive_not_found >= MAX_CONSECUTIVE_NOT_FOUND:
                print(f"\n  СТОП: {MAX_CONSECUTIVE_NOT_FOUND} підряд не знайдено — зупиняємо скрипт.")
                break

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

    end_time = datetime.datetime.now()
    elapsed = end_time - start_time
    elapsed_str = str(elapsed).split(".")[0]  # HH:MM:SS без мікросекунд

    # ── Summary ───────────────────────────────────────────────────────────────
    processed = found_count + not_found_count
    print()
    print("=" * 52)
    print(f"Оброблено  : {processed} / {row_count}")
    print(f"  Знайдено   : {found_count}")
    print(f"  Не знайдено: {not_found_count}")
    print(f"[ЧАС] Початок : {start_time.strftime('%H:%M:%S')}")
    print(f"[ЧАС] Кінець  : {end_time.strftime('%H:%M:%S')}")
    print(f"[ЧАС] Тривалість: {elapsed_str}")
    print("=" * 52)

    _save_log(log_rows, found_count, not_found_count, start_time, end_time, elapsed_str)
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


def _save_log(rows: list, found: int, not_found: int,
              start_time: datetime.datetime, end_time: datetime.datetime,
              elapsed_str: str) -> None:
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("Результати звірки ІПН\n")
        f.write(f"Початок  : {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Кінець   : {end_time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Тривалість: {elapsed_str}\n")
        f.write(f"Знайдено: {found}  |  Не знайдено: {not_found}\n")
        f.write("-" * 38 + "\n")
        f.write(f"{'Рядок':<7} {'ІПН':<13} Статус\n")
        f.write("-" * 38 + "\n")
        for row_num, ipn, status in rows:
            f.write(f"{row_num:<7} {ipn:<13} {status}\n")


if __name__ == "__main__":
    main()

