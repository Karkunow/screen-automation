"""
test_checkbox.py
Перевіряє чи pyautogui може знайти шаблон відміченого чекбокса на екрані.

Використання:
  1. Переключись на Chrome з відкритим Google Sheets (відмічений чекбокс має бути видний).
  2. Запусти: python3 test_checkbox.py
  3. У тебе є 5 секунд щоб переключитись.
"""

import time
import sys

print("Перемикайся на Chrome... 5 секунд")
for i in range(5, 0, -1):
    print(f"  {i}…", end="\r", flush=True)
    time.sleep(1)
print()

import pyautogui

screenshot = pyautogui.screenshot()
screenshot.save("debug_screen.png")
print("Скріншот збережено → debug_screen.png\n")
from PIL import Image

path = "img/checkbox_checked.png"

try:
    img = Image.open(path)
    print(f"Шаблон: {path}  |  розмір: {img.size}  |  режим: {img.mode}")
except FileNotFoundError:
    print(f"ПОМИЛКА: файл {path} не знайдено")
    sys.exit(1)

print("Шукаємо на екрані...\n")

found = False
for conf in [0.95, 0.90, 0.85, 0.80, 0.75, 0.70, 0.60]:
    try:
        loc = pyautogui.locateOnScreen(path, confidence=conf)
        if loc:
            print(f"  ✓ ЗНАЙДЕНО  confidence={conf}  →  {loc}")
            found = True
            break
    except Exception:
        print(f"  ✗ не знайдено  confidence={conf}")

if not found:
    print("\nНЕ ЗНАЙДЕНО жодного збігу.")
    print("Можливі причини:")
    print("  • Chrome не активний або чекбокс не видно на екрані")
    print("  • Масштаб сторінки відрізняється від того, коли робили скріншот")
    print("  • Шаблон занадто великий (201x44) — спробуй зробити менший скріншот")
    print()
    print("  → перевір debug_screen.png щоб побачити що бачив скрипт")
