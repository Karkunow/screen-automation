"""
calibrate.py
One-time setup: records the screen position of the first IPN cell in
Numbers/Excel and (on Windows) the Chrome window title.

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
    """Short audible beep \u2014 afplay on macOS, winsound on Windows."""
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

def main():
    is_mac = sys.platform == "darwin"
    spreadsheet_app = "Numbers" if is_mac else "Excel"

    print("=" * 52)
    print("   Автоматизація екрану — Калібрування")
    print("=" * 52)
    print(f"Платформа  : {'macOS' if is_mac else 'Windows'}")
    print(f"Таблиця    : {spreadsheet_app}")
    print()

    config: dict = {
        "platform": "mac" if is_mac else "windows",
        "row_count": 50,
        # How many columns to the RIGHT of the IPN cell is the checkbox.
        # Default: 1  (IPN = col B, checkbox = col C)
        "checkbox_offset": 1,
        "delays": {
            "window_switch": 0.7,   # seconds to wait after focusing a window
            "after_copy": 0.4,      # seconds to wait after Cmd/Ctrl+C
            "after_search_open": 0.7,  # seconds after opening Ctrl+F
            "after_search_type": 1.1,  # seconds after pasting the IPN
            "after_mark": 0.35,     # seconds after toggling the checkbox
        },
    }

    # Load existing config so steps can be skipped
    existing: dict = {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            existing = json.load(f)
        # Carry over values that calibrate.py doesn't touch
        for key in ("delays", "checkbox_offset", "platform"):
            if key in existing:
                config[key] = existing[key]
    except (FileNotFoundError, json.JSONDecodeError):
        pass

    # ── Step 1 : first IPN cell ───────────────────────────────────────
    print(f"Крок 1 / {'2' if is_mac else '3'}  —  Перша клітинка ІПН у {spreadsheet_app}")
    cur_cell = (existing.get("ipn_cell_x"), existing.get("ipn_cell_y"))
    if cur_cell[0] is not None and _ask_skip("позиція", cur_cell):
        config["ipn_cell_x"], config["ipn_cell_y"] = cur_cell
        print(f"  → збережено попереднє ({cur_cell[0]}, {cur_cell[1]})")
    else:
        print(f"  1. Відкрий {spreadsheet_app} з імпортованим small_list.csv.")
        print("  2. Дані мають починатись з рядка 2  (рядок 1 = заголовки: ПІБ | ІПН).")
        print("  3. Наведи мишу на першу клітинку ІПН  (колонка B, рядок 2).")
        print("  4. Натисни Enter — у тебе є 7 секунд на позиціонування.")
        input("\n  Натисни Enter коли готовий: ")
        _countdown(7)
        x, y = pyautogui.position()
        config["ipn_cell_x"] = x
        config["ipn_cell_y"] = y
        print(f"  ✓ Позицію збережено ({x}, {y})")
        _beep()
    print()

    # ── Step 2 : row count ─────────────────────────────────────────
    print("Крок 2  —  Кількість рядків")
    if existing.get("row_count") is not None and _ask_skip("кількість рядків", existing["row_count"]):
        config["row_count"] = existing["row_count"]
        print(f"  → збережено попереднє ({existing['row_count']})")
    else:
        raw = input("  Скільки рядків з даними в таблиці? (за замовчуванням 50): ").strip()
        config["row_count"] = int(raw) if raw.isdigit() else 50
        print(f"  ✓ Кількість рядків: {config['row_count']}")
        _beep()
    print()

    # ── Step 3 : Google Sheets find bar region ───────────────────
    print("Крок 3  —  Регіон рядка пошуку Google Sheets")
    cur_fb = existing.get("find_bar_region")
    if cur_fb is not None and _ask_skip("регіон", cur_fb):
        config["find_bar_region"] = cur_fb
        print(f"  → збережено попереднє {cur_fb}")
    else:
        print("  1. Переключись на Chrome з відкритим Google Sheets (big_list).")
        print("  2. Відкрий рядок пошуку (Cmd+F).")
        print("  3. Наведи мишу на ВЕРХНІЙ ЛІВИЙ кут рядка пошуку.")
        print("  4. Натисни Enter — у тебе є 7 секунд.")
        input("\n  Натисни Enter коли готовий: ")
        _countdown(7)
        fx1, fy1 = pyautogui.position()
        print(f"  ✓ Верхній лівий кут збережено: ({fx1}, {fy1})")
        _beep()

        print("  5. Тепер наведи мишу на ПРАВИЙ НИЖНІЙ кут рядка пошуку.")
        print("  6. Натисни Enter — у тебе є 7 секунд.")
        input("\n  Натисни Enter коли готовий: ")
        _countdown(7)
        fx2, fy2 = pyautogui.position()
        print(f"  ✓ Правий нижній кут збережено: ({fx2}, {fy2})")
        _beep()

        config["find_bar_region"] = [fx1, fy1, fx2, fy2]
        print(f"  ✓ Регіон рядка пошуку збережено: ({fx1}, {fy1}) → ({fx2}, {fy2})")
        _beep()
    print()

    # ── Step 4 (Windows only): Chrome window title ────────────────────
    if not is_mac:
        print("Крок 4  —  Заголовок вікна Chrome  (тільки Windows)")
        if existing.get("chrome_title_part") and _ask_skip("заголовок", existing["chrome_title_part"]):
            config["chrome_title_part"] = existing["chrome_title_part"]
            print(f"  → збережено попереднє ('{existing['chrome_title_part']}')")
        else:
            print("  Відкрий Chrome з активною вкладкою Google Sheets (big_list).")
            print("  Подивись на заголовок вікна Windows — там показана назва документа.")
            part = input("  Введи частину цієї назви (напр. 'big_list'): ").strip()
            config["chrome_title_part"] = part
            print(f"  ✓ Частину заголовку збережено: '{part}'")
            _beep()

    # ── Save ──────────────────────────────────────────────────────────
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print("=" * 52)
    print(f"✓  Конфіг збережено у {CONFIG_FILE}")
    print()
    print("Готово до запуску:")
    print(f"  1. Тримай {spreadsheet_app} відкритим з даними small_list.")
    print("  2. Тримай Chrome відкритим з Google Sheets (big_list) як активна вкладка.")
    print("  3. Запускай:  python automation.py")
    print()
    print("Безпека: перемісти мишу у ВЕРХНІЙ ЛІВИЙ кут для аварійної зупинки.")
    print("=" * 52)


if __name__ == "__main__":
    main()
