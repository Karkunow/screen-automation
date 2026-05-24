"""
calibrate.py
One-time setup: records screen positions for Excel IPN cell and MIA window.

Saves result to config.json — required before running automation.py.

Usage:
    python calibrate.py
"""

import json
import subprocess
import sys
import time

import pyautogui

CONFIG_FILE = "config.json"


def _beep():
    """Short audible beep — afplay on macOS, winsound on Windows."""
    if sys.platform == "darwin":
        subprocess.run(
            ["afplay", "/System/Library/Sounds/Ping.aiff"],
            check=False,
        )
    elif sys.platform == "win32":
        import winsound
        winsound.Beep(800, 300)
    else:
        print("\a", end="", flush=True)


def _countdown(seconds: int):
    for i in range(seconds, 0, -1):
        print(f"  {i}...", end="\r", flush=True)
        time.sleep(1)
    print("  Записано!   ")


def _ask_skip(label: str, current) -> bool:
    """Show current value and return True if user chooses to skip."""
    if current is None:
        return False
    print(f"  Поточне значення: {current}")
    ans = input("  [Enter] перекалібрувати  /  [s] пропустити: ").strip().lower()
    return ans == "s"


def _capture_pos(prompt: str) -> tuple[int, int]:
    """Print prompt, countdown 7s, return cursor position."""
    input(f"\n  {prompt} Натисни Enter — у тебе є 7 секунд: ")
    _countdown(7)
    x, y = pyautogui.position()
    print(f"  ✓ Збережено ({x}, {y})")
    _beep()
    return x, y


def main():
    is_mac = sys.platform == "darwin"
    spreadsheet_app = "Numbers" if is_mac else "Excel"
    total_steps = 6 if is_mac else 7

    print("=" * 52)
    print("   Автоматизація екрану — Калібрування")
    print("=" * 52)
    print(f"Платформа  : {'macOS' if is_mac else 'Windows'}")
    print(f"Таблиця    : {spreadsheet_app}")
    print()

    config: dict = {
        "platform": "mac" if is_mac else "windows",
        "row_count": 50,
        "batch_size": 20,
        "delays": {
            "window_switch": 0.7,
            "after_copy": 0.4,
            "after_type_ipn": 0.5,
            "tooltip_timeout": 15.0,
            "batch_confirm_wait": 3.0,
            "batch_reopen_wait": 12.0,
        },
        "mia_title_part": "Обіймання посад",
    }

    # Load existing config so steps can be skipped
    existing: dict = {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            existing = json.load(f)
        for key in ("delays", "platform", "batch_size", "mia_title_part"):
            if key in existing:
                config[key] = existing[key]
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    # ── Step 1 : first IPN cell in Excel ────────────────────────────────────
    print(f"Крок 1 / {total_steps}  —  Перша клітинка ІПН у {spreadsheet_app}")
    cur_cell = (existing.get("ipn_cell_x"), existing.get("ipn_cell_y"))
    if cur_cell[0] is not None and _ask_skip("позиція", cur_cell):
        config["ipn_cell_x"], config["ipn_cell_y"] = cur_cell
        print(f"  → збережено попереднє ({cur_cell[0]}, {cur_cell[1]})")
    else:
        print(f"  1. Відкрий {spreadsheet_app} з даними.")
        print("  2. Дані мають починатись з рядка 2  (рядок 1 = заголовки).")
        print("  3. Наведи мишу на першу клітинку ІПН (перший рядок з даними).")
        x, y = _capture_pos("Наведи мишу на першу клітинку ІПН і натисни Enter.")
        config["ipn_cell_x"] = x
        config["ipn_cell_y"] = y
    print()

    # ── Step 2 : row count ───────────────────────────────────────────────────
    print(f"Крок 2 / {total_steps}  —  Кількість рядків")
    if existing.get("row_count") is not None and _ask_skip("кількість рядків", existing["row_count"]):
        config["row_count"] = existing["row_count"]
        print(f"  → збережено попереднє ({existing['row_count']})")
    else:
        raw = input("  Скільки рядків з даними? (за замовчуванням 50): ").strip()
        config["row_count"] = int(raw) if raw.isdigit() else 50
        print(f"  ✓ Кількість рядків: {config['row_count']}")
        _beep()
    print()

    # ── Step 3 : MIA — верхній лівий кут ПЕРШОГО рядка колонки ІПН ────────────
    print(f"Крок 3 / {total_steps}  —  MIA: верхній лівий кут стовпця ІПН (перший рядок)")
    cur_tl = existing.get("mia_ipn_cell_tl")
    if cur_tl and _ask_skip("mia_ipn_cell_tl", cur_tl):
        config["mia_ipn_cell_tl"] = cur_tl
        print(f"  → збережено попереднє {cur_tl}")
    else:
        print("  1. Переключись на вікно MIA ('Обіймання посад').")
        print("  2. Знайди ПЕРШИЙ рядок з даними у стовпці 'Ідентифікатор' (самий верхній).")
        print("  3. Наведи мишу на ВЕРХНІЙ ЛІВИЙ кут цього першого рядка.")
        x, y = _capture_pos("Наведи мишу на верхній лівий кут першого рядка ІПН.")
        config["mia_ipn_cell_tl"] = [x, y]
    print()

    # ── Step 4 : MIA — нижній правий кут клітинки ІПН ───────────────────────
    print(f"Крок 4 / {total_steps}  —  MIA: нижній правий кут клітинки ІПН (той самий перший рядок)")
    cur_br = existing.get("mia_ipn_cell_br")
    if cur_br and _ask_skip("mia_ipn_cell_br", cur_br):
        config["mia_ipn_cell_br"] = cur_br
        print(f"  → збережено попереднє {cur_br}")
    else:
        print("  1. Залишся у вікні MIA — той САМИЙ перший рядок 'Ідентифікатор'.")
        print("  2. Наведи мишу на НИЖНІЙ ПРАВИЙ кут тієї самої клітинки.")
        x, y = _capture_pos("Наведи мишу на нижній правий кут клітинки ІПН.")
        config["mia_ipn_cell_br"] = [x, y]
    print()

    # ── Step 5 : MIA — нижній правий кут стовпця ІПН ────────────────────────
    print(f"Крок 5 / {total_steps}  —  MIA: нижній правий кут стовпця ІПН (останній рядок)")
    cur_col_br = existing.get("mia_ipn_col_br")
    if cur_col_br and _ask_skip("mia_ipn_col_br", cur_col_br):
        config["mia_ipn_col_br"] = cur_col_br
        print(f"  → збережено попереднє {cur_col_br}")
    else:
        print("  1. Залишся у вікні MIA.")
        print("  2. Знайди ОСТАННІЙ видимий рядок з даними у стовпці 'Ідентифікатор'.")
        print("  3. Наведи мишу на НИЖНІЙ ПРАВИЙ кут цього останнього рядка.")
        x, y = _capture_pos("Наведи мишу на нижній правий кут останнього рядка ІПН.")
        config["mia_ipn_col_br"] = [x, y]
    print()

    # ── Step 6 : MIA — позиція галочки ──────────────────────────────────────
    print(f"Крок 6 / {total_steps}  —  MIA: галочка поруч з клітинкою ІПН")
    cur_cb = existing.get("mia_checkbox_offset")
    if cur_cb and _ask_skip("mia_checkbox_offset", cur_cb):
        config["mia_checkbox_offset"] = cur_cb
        print(f"  → збережено попереднє {cur_cb}")
    else:
        print("  1. Залишся у вікні MIA — перший рядок.")
        print("  2. Наведи мишу ТОЧНО на галочку зліва від цього рядка.")
        cx, cy = _capture_pos("Наведи мишу на галочку зліва від рядка.")
        tl = config["mia_ipn_cell_tl"]
        dx = cx - tl[0]
        dy = cy - tl[1]
        config["mia_checkbox_offset"] = [dx, dy]
        print(f"  ✓ Зміщення галочки: dx={dx}, dy={dy}")
    print()

    # ── Step 7 (Windows only) : назва вікна MIA ─────────────────────────────
    if not is_mac:
        print(f"Крок 7 / {total_steps}  —  Назва вікна MIA (Windows)")
        cur_title = existing.get("mia_title_part", "Обіймання посад")
        if cur_title and _ask_skip("mia_title_part", cur_title):
            config["mia_title_part"] = cur_title
            print(f"  → збережено попереднє ('{cur_title}')")
        else:
            print("  Відкрий MIA — вікно 'Обіймання посад' має бути відкрите.")
            print("  Назва вікна (з PowerShell): 'Обіймання посад' або 'Заробітна плата'.")
            part = input("  Введи фрагмент назви вікна MIA [Обіймання посад]: ").strip()
            config["mia_title_part"] = part if part else "Обіймання посад"
            print(f"  ✓ Назву вікна збережено: '{config['mia_title_part']}'")
            _beep()
        print()

    # ── Save ─────────────────────────────────────────────────────────────────
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print("=" * 52)
    print(f"✓  Конфіг збережено у {CONFIG_FILE}")
    print()
    print("Готово до запуску:")
    print(f"  1. Тримай {spreadsheet_app} відкритим з даними.")
    print("  2. Тримай MIA відкритим — вікно 'Обіймання посад'.")
    print("  3. Запускай:  python automation.py")
    print()
    print("Безпека: перемісти мишу у ВЕРХНІЙ ЛІВИЙ кут для аварійної зупинки.")
    print("=" * 52)


if __name__ == "__main__":
    main()
