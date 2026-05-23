"""
utils/mia_handler.py
Handles all interaction with the MIA 'Обіймання посад' search window.

Key operations:
  type_ipn        — click IPN column cell and type the IPN digit by digit
  wait_tooltip_gone — wait for yellow search tooltip to disappear
  find_blue_row   — find the dark-blue highlighted row and confirm IPN via OCR
  click_checkbox  — click the checkbox to the left of the found row
  confirm_batch   — press Enter (OK) then Insert (reopen) to commit a batch
"""

import sys
import time

import cv2
import numpy as np
import pyautogui
import pyperclip

try:
    import pytesseract
    from PIL import Image
    _OCR_AVAILABLE = True
except ImportError:
    _OCR_AVAILABLE = False

_MOD = "command" if sys.platform == "darwin" else "ctrl"


# ── Window screenshot helpers ─────────────────────────────────────────────────

def _get_mia_win(mia_title: str):
    """Return the first pygetwindow window matching mia_title, or None."""
    try:
        import pygetwindow as gw
        wins = gw.getWindowsWithTitle(mia_title)
        if wins:
            return wins[0]
        # Fallback to main MIA app window
        wins = gw.getWindowsWithTitle("Заробітна плата")
        if wins:
            return wins[0]
    except ImportError:
        pass
    return None


def _screenshot_mia(mia_title: str):
    """Screenshot the MIA window only.

    Returns (img_bgr, win_left, win_top).
    Falls back to full screen if window cannot be located.
    """
    win = _get_mia_win(mia_title)
    if win is not None:
        try:
            region = (win.left, win.top, win.width, win.height)
            img = pyautogui.screenshot(region=region)
            img_bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            return img_bgr, win.left, win.top
        except Exception:
            pass
    img = pyautogui.screenshot()
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR), 0, 0


# ── Public API ────────────────────────────────────────────────────────────────

def type_ipn(ipn: str, cell_tl: list, delays: dict) -> None:
    """Click the IPN column cell in MIA and type the IPN character by character."""
    x, y = cell_tl
    pyautogui.click(x, y)
    time.sleep(0.3)
    pyautogui.typewrite(ipn, interval=0.06)
    time.sleep(delays.get("after_type_ipn", 0.5))


def wait_tooltip_gone(mia_title: str, timeout: float = 15.0) -> None:
    """Wait until the yellow search tooltip disappears from the MIA window.

    Yellow tooltip HSV range (OpenCV 0-180 hue):
      H 20-40  (yellow),  S 30-150,  V 200-255
    """
    # Phase 1: wait up to 2 s for tooltip to appear
    deadline_appear = time.time() + 2.0
    while time.time() < deadline_appear:
        if _yellow_present(mia_title):
            break
        time.sleep(0.1)

    # Phase 2: wait for tooltip to disappear
    deadline_gone = time.time() + timeout
    while time.time() < deadline_gone:
        if not _yellow_present(mia_title):
            return
        time.sleep(0.2)
    # Timeout — proceed anyway


def find_blue_row(ipn: str, cell_tl: list, cell_br: list, mia_title: str) -> int | None:
    """Scan the MIA window for the dark-blue highlighted row and confirm the IPN.

    Returns the absolute screen Y coordinate of the TOP of the found row,
    or None if no matching row is found.

    Dark navy-blue row HSV range (OpenCV 0-180 hue):
      H 95-125,  S 80-255,  V 40-180
    """
    img_bgr, win_left, win_top = _screenshot_mia(mia_title)
    img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

    # Window-relative IPN column x bounds
    x1 = max(0, cell_tl[0] - win_left)
    x2 = min(img_bgr.shape[1], cell_br[0] - win_left)
    cell_h = max(1, cell_br[1] - cell_tl[1])

    # Dark navy-blue mask
    mask = cv2.inRange(img_hsv,
                       np.array([95, 80, 40]),
                       np.array([125, 255, 180]))

    # Restrict to IPN column width
    col_mask = np.zeros_like(mask)
    col_mask[:, x1:x2] = mask[:, x1:x2]

    # Find rows with enough blue pixels (at least 30% of column width)
    row_sums = col_mask.sum(axis=1)
    threshold = max(10, int((x2 - x1) * 0.3 * 255))
    blue_rows = np.where(row_sums >= threshold)[0]

    if len(blue_rows) == 0:
        return None

    # Collect contiguous groups
    groups: list[tuple[int, int]] = []
    start = int(blue_rows[0])
    prev = int(blue_rows[0])
    for r in blue_rows[1:]:
        r = int(r)
        if r - prev <= 4:
            prev = r
        else:
            groups.append((start, prev))
            start = r
            prev = r
    groups.append((start, prev))

    for g_start, g_end in groups:
        # Verify IPN with OCR if available
        if _OCR_AVAILABLE:
            crop = img_bgr[g_start:g_end + 1, x1:x2]
            if crop.size == 0:
                continue
            # Invert: white text on dark background → black text on white
            inv = cv2.bitwise_not(crop)
            big = cv2.resize(inv, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
            pil_img = Image.fromarray(cv2.cvtColor(big, cv2.COLOR_BGR2RGB))
            raw = pytesseract.image_to_string(
                pil_img,
                config="--psm 7 -c tessedit_char_whitelist=0123456789",
            ).strip()
            digits = "".join(c for c in raw if c.isdigit())
            if digits != ipn:
                continue  # wrong row, keep looking

        # Return absolute screen Y of the top of this row
        return win_top + g_start

    return None


def click_checkbox(row_top_y: int, cell_tl: list, checkbox_offset: list) -> None:
    """Click the checkbox to the left of the found row.

    checkbox_offset = [dx, dy] recorded during calibration as:
        dx = checkbox_x - cell_tl_x
        dy = checkbox_y - cell_tl_y
    """
    dx, dy = checkbox_offset
    check_x = cell_tl[0] + dx
    check_y = row_top_y + dy
    pyautogui.click(check_x, check_y)
    time.sleep(0.2)


def confirm_batch(delays: dict) -> None:
    """Commit the current batch of 20 and reopen the search dialog.

    Sequence: Enter (OK) → wait → Insert (reopen) → wait for dialog.
    """
    pyautogui.press("return")
    time.sleep(delays.get("batch_confirm_wait", 3.0))
    pyautogui.press("insert")
    time.sleep(delays.get("batch_reopen_wait", 12.0))


# ── Private helpers ───────────────────────────────────────────────────────────

def _yellow_present(mia_title: str) -> bool:
    """Return True if a yellow tooltip region is visible in the MIA window."""
    img_bgr, _, _ = _screenshot_mia(mia_title)
    img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(img_hsv,
                       np.array([20, 30, 200]),
                       np.array([40, 150, 255]))
    return int(cv2.countNonZero(mask)) >= 50
