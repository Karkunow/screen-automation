"""
utils/sheets_handler.py
Interact with Google Sheets (open in Chrome) via keyboard + screen detection.

Search flow
  1. open_find()   — Ctrl+F, paste IPN, wait for results
  2. is_found()    — primary: pytesseract OCR of the find-bar area
                     fallback: OpenCV orange-highlight detection
  3. mark_found()  — Esc (cursor lands on found IPN cell)
                     → Right-arrow N times → Space (toggle checkbox) → Enter
     close_find()  — Esc only (no match)
"""

import re
import sys
import time

import cv2
import numpy as np
import pyautogui
import pyperclip

_MOD = "command" if sys.platform == "darwin" else "ctrl"

# Columns to move right from the IPN cell to reach the checkbox column.
# IPN = col B, Знайдено = col C  →  offset = 1
_checkbox_offset: int = 1


def set_checkbox_offset(offset: int) -> None:
    global _checkbox_offset
    _checkbox_offset = offset


# ── Public API ────────────────────────────────────────────────────────────────

def open_find(ipn: str, delays: dict) -> None:
    """Open the Ctrl+F find bar in Google Sheets and search for *ipn*."""
    pyautogui.hotkey(_MOD, "f")
    time.sleep(delays.get("after_search_open", 0.7))

    # Clear any leftover search text, then paste the IPN
    pyautogui.hotkey(_MOD, "a")
    time.sleep(0.1)
    pyperclip.copy(ipn)
    pyautogui.hotkey(_MOD, "v")
    time.sleep(delays.get("after_search_type", 1.1))


def is_found() -> bool:
    """Return True if Google Sheets found at least one match for the current
    Ctrl+F query.

    Strategy 1 (preferred): OCR the top portion of the screen.
      • Found    → counter text looks like "1 of 3" / "1 з 3"
      • Not found → "No results" / "Збігів немає" / "0 of 0"

    Strategy 2 (fallback): detect the orange cell-highlight that Google Sheets
    renders around matched cells.
    """
    result = _ocr_detect()
    if result is not None:
        return result
    return _orange_detect()


def mark_found(delays: dict) -> None:
    """After a successful find, close the find bar and check the checkbox.

    When the find bar is closed with Escape, the active cell in Google Sheets
    is the found cell (IPN column B).  We move right to the checkbox column,
    read the formula bar via OCR to check the current state, and only press
    Space if the checkbox is not yet TRUE.
    """
    pyautogui.press("escape")
    time.sleep(delays.get("after_mark", 0.35))

    for _ in range(_checkbox_offset):
        pyautogui.press("right")
        pyautogui.keyUp("fn")
        time.sleep(0.1)

    if _is_checked():
        print("  → галочка вже стоїть, пропускаємо")
        return

    pyautogui.press("space")
    time.sleep(delays.get("after_mark", 0.35))


def close_find() -> None:
    """Close the find bar without marking anything."""
    pyautogui.press("escape")
    time.sleep(0.3)


# ── Detection helpers ─────────────────────────────────────────────────────────

def _is_checked() -> bool:
    """Return True if the currently selected Google Sheets checkbox is checked.

    Copies the cell value via clipboard — reliable regardless of what else
    is visible on screen (avoids false positives from locateOnScreen).
    """
    pyperclip.copy("")
    pyautogui.hotkey(_MOD, "c")
    time.sleep(0.3)
    val = pyperclip.paste().strip().upper()
    print(f"  → значення чекбоксу: {val!r}")
    return val in ("TRUE", "ИСТИНА", "ПРАВДА")


def _ocr_detect() -> bool | None:
    """Try OCR on the find bar region recorded during calibration.
    Returns True/False when confident, or None to signal fallback.
    """
    try:
        import json
        import pytesseract
        from PIL import ImageGrab

        # Load find bar region from config
        with open("config.json", "r", encoding="utf-8") as f:
            cfg = json.load(f)
        region = cfg.get("find_bar_region")
        if not region or len(region) != 4:
            print("  [OCR] find_bar_region не знайдено в config — запусти calibrate.py")
            return None

        x1, y1, x2, y2 = region
        # On macOS Retina displays ImageGrab returns physical pixels (2×),
        # while pyautogui coordinates are logical pixels — scale accordingly.
        if sys.platform == "darwin":
            x1, y1, x2, y2 = x1 * 2, y1 * 2, x2 * 2, y2 * 2
        screenshot = ImageGrab.grab()
        #screenshot.save("debug_full_screenshot.png")
        crop = screenshot.crop((x1, y1, x2, y2))
        #crop.save("debug_ocr_crop.png")
        crop = crop.resize((crop.width * 3, crop.height * 3))

        text = pytesseract.image_to_string(
            crop, lang="eng+ukr", config="--psm 7 --oem 3"
        ).lower()
        print(f"  [OCR] прочитано: {text!r}")

        # Match "count sep total" pattern.
        # Handles standard: "1 of 5", "1 з 5", "1 із 5", "1 из 5"
        # Handles OCR misreads of "із": "i", "iз", "i3" (з→3)
        #   e.g. "0 із 30" → OCR → "0i30"  (sep="i", total="30")
        #        "0 із 30" → OCR → "0i330" (sep="i3", total="0" — count still 0)
        # In both cases count==0 → NOT FOUND; count>0 → FOUND.
        m = re.search(
            r"(\d+)\s*(?:of|із|iз|i3|з\b|из|i(?=\d))\s*(\d+)",
            text, re.IGNORECASE
        )
        if m:
            count = int(m.group(1))
            if count > 0:
                print("  [OCR] патерн: ЗНАЙДЕНО")
                return True
            else:
                print("  [OCR] патерн: НЕ ЗНАЙДЕНО")
                return False

        # Fallback text patterns (no counter visible at all)
        no_match = [
            "no result", "no match",
            "збігів немає", "не знайдено", "нет результ",
        ]
        if any(p in text for p in no_match):
            print("  [OCR] патерн: НЕ ЗНАЙДЕНО")
            return False
        print("  [OCR] неоднозначно, переходимо до fallback")

    except Exception:
        pass

    return None  # inconclusive — caller will use fallback


def _orange_detect() -> bool:
    """Fallback: detect the orange/amber highlight Google Sheets draws around
    matched cells.  Works regardless of UI language.

    Ignores the top 12 % of the screen (browser chrome / find bar area) to
    avoid false positives from the browser UI itself.
    """
    screenshot = pyautogui.screenshot()
    img_hsv = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2HSV)

    h = img_hsv.shape[0]
    # Mask out the browser-chrome area at the top
    img_hsv[: int(h * 0.12), :] = 0

    # Google Sheets match highlight: orange/amber
    # HSV H ≈ 8–28, S ≈ 120–255, V ≈ 120–255
    mask = cv2.inRange(
        img_hsv,
        np.array([8, 120, 120], dtype=np.uint8),
        np.array([28, 255, 255], dtype=np.uint8),
    )
    orange_pixels = int(np.sum(mask > 0))
    print(f"  [Orange] помаранчевих пікселів: {orange_pixels}")
    return orange_pixels > 600
