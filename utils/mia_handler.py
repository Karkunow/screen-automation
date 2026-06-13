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
        wins = gw.getWindowsWithTitle("Заробітна плата")
        if wins:
            return wins[0]
        all_titles = [w.title for w in gw.getAllWindows() if w.title.strip()]
        print(f"  [WIN] УВАГА: вікно MIA не знайдено! Всі вікна: {all_titles[:10]}")
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
        except Exception as e:
            print(f"  [WIN] помилка скріншоту вікна: {e} — беремо весь екран")
    img = pyautogui.screenshot()
    img_bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    print(f"  [WIN] УВАГА: скріншот ВЕСЬ ЕКРАН (вікно не знайдено)")
    return img_bgr, 0, 0


# ── Public API ────────────────────────────────────────────────────────────────

def type_ipn(ipn: str, cell_tl: list, cell_br: list, delays: dict) -> None:
    """Click the IPN column cell in MIA and type the IPN character by character."""
    cx = (cell_tl[0] + cell_br[0]) // 2
    cy = (cell_tl[1] + cell_br[1]) // 2
    print(f"  [TYPE] клік на центр клітинки MIA ({cx},{cy}), вводимо ІПН: {ipn}")
    pyautogui.click(cx, cy)
    time.sleep(0.3)
    pyautogui.typewrite(ipn, interval=0.06)
    time.sleep(delays.get("after_type_ipn", 0.5))
    print(f"  [TYPE] введено, чекаємо {delays.get('after_type_ipn', 0.5)}с")


def _move_mouse_away(cell_tl: list, cell_br: list) -> None:
    """Move cursor to the right of the IPN column so it doesn't obscure the row."""
    cell_w = max(20, cell_br[0] - cell_tl[0])
    park_x = cell_br[0] + cell_w
    park_y = cell_tl[1]
    print(f"  [TIP] відсуваємо мишу вправо від колонки → ({park_x},{park_y})")
    pyautogui.moveTo(park_x, park_y, duration=0.15)


def wait_tooltip_gone(mia_title: str, timeout: float = 10.0,
                      cell_tl: list | None = None,
                      cell_br: list | None = None) -> None:
    """Wait until the yellow search tooltip disappears from the MIA window.

    Yellow tooltip HSV range (OpenCV 0-180 hue):
      H 20-40  (yellow),  S 30-150,  V 200-255
    """
    # Phase 1: wait up to 2 s for tooltip to appear
    print(f"  [TIP] фаза 1: чекаємо появи жовтого tooltip (до 2с)...")
    t0 = time.time()
    deadline_appear = t0 + 2.0
    appeared = False
    while time.time() < deadline_appear:
        if _yellow_present(mia_title):
            appeared = True
            break
        time.sleep(0.1)
    if appeared:
        print(f"  [TIP] tooltip з'явився за {time.time()-t0:.1f}с")
    else:
        print(f"  [TIP] tooltip не з'явився за 2с (пошук міг завершитись миттєво)")

    # Phase 2: wait for tooltip to disappear
    print(f"  [TIP] фаза 2: чекаємо зникнення tooltip (до {timeout}с)...")
    t1 = time.time()
    deadline_gone = t1 + timeout
    while time.time() < deadline_gone:
        if not _yellow_present(mia_title):
            print(f"  [TIP] tooltip зник за {time.time()-t1:.1f}с — пошук завершено")
            if cell_tl and cell_br:
                _move_mouse_away(cell_tl, cell_br)
            return
        time.sleep(0.2)
    print(f"  [TIP] ТАЙМАУТ {timeout}с — продовжуємо без підтвердження")
    if cell_tl and cell_br:
        _move_mouse_away(cell_tl, cell_br)


def find_blue_row(ipn: str, cell_tl: list, cell_br: list, mia_title: str,
                  col_br: list | None = None) -> int | None:
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

    # Dark navy-blue mask  (HSV: H 95-125, S 80-255, V 40-255)
    # V extended to 255 — Windows selection blue can be bright (V ~180-220)
    mask = cv2.inRange(img_hsv,
                       np.array([95, 60, 40]),
                       np.array([125, 255, 255]))

    # Restrict search to the calibrated IPN column rectangle:
    #   x: left/right edges of the column (cell_tl[0] .. cell_br[0])
    #   y: first data row (cell_tl[1]) .. last visible row (col_br[1])
    #      Falls back to top-75% of window if col_br was not calibrated.
    col_mask = np.zeros_like(mask)
    y1 = max(0, cell_tl[1] - win_top - 2)
    if col_br is not None:
        y2 = min(img_bgr.shape[0], col_br[1] - win_top + 2)
    else:
        y2 = int(img_bgr.shape[0] * 0.75)
    col_mask[y1:y2, x1:x2] = mask[y1:y2, x1:x2]

    # Find rows with enough blue pixels (at least 15% of column width)
    row_sums = col_mask.sum(axis=1)
    threshold = max(10, int((x2 - x1) * 0.15 * 255))
    blue_rows = np.where(row_sums >= threshold)[0]

    # Save debug screenshot with marked column (silent, overwrites each call)
    try:
        dbg = img_bgr.copy()
        cv2.rectangle(dbg, (x1, 0), (x2, dbg.shape[0]), (0, 255, 0), 2)
        cv2.imwrite("debug_blue_search.png", dbg)
    except Exception:
        pass

    if len(blue_rows) == 0:
        print(f"  [OCR] синіх рядків не знайдено (ІПН={ipn})")
        return None

    # Collect contiguous groups
    groups: list[tuple[int, int]] = []
    start = int(blue_rows[0])
    prev = int(blue_rows[0])
    for r in blue_rows[1:]:
        r = int(r)
        if r - prev <= 8:
            prev = r
        else:
            groups.append((start, prev))
            start = r
            prev = r
    groups.append((start, prev))

    min_row_h = max(5, cell_h // 2)
    for idx, (g_start, g_end) in enumerate(groups):
        if g_end - g_start + 1 < min_row_h:
            continue  # тонка синя межа/лінія таблиці — ігноруємо
        # Verify IPN with OCR if available
        if _OCR_AVAILABLE:
            crop_y1 = max(0, g_start - 2)
            crop_y2 = min(img_bgr.shape[0], crop_y1 + cell_h)
            crop = img_bgr[crop_y1:crop_y2, x1:x2]
            if crop.size == 0:
                continue
            # Grayscale + Otsu threshold: white text on blue bg → black text on white bg
            # Otsu finds optimal split between dark-blue bg and bright text automatically
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
            _, thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            # Auto-trim border lines: rows where >85% of pixels are black
            # are table borders, not digit strokes — paint them white.
            # Solid border lines hit ~100% fill; even dense digit rows rarely exceed 70%.
            row_fill = (thr == 0).sum(axis=1) / max(1, thr.shape[1])
            thr[row_fill > 0.85] = 255
            big = cv2.resize(thr, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
            # Add white padding so Tesseract doesn't cut off edge digits
            big = cv2.copyMakeBorder(big, 20, 20, 20, 20, cv2.BORDER_CONSTANT, value=255)
            # Keep last 2 OCR crops (orig + thresholded) with rotation
            try:
                import os
                if os.path.exists("debug_ocr_orig_1.png"):
                    os.replace("debug_ocr_orig_1.png", "debug_ocr_orig_2.png")
                if os.path.exists("debug_ocr_thr_1.png"):
                    os.replace("debug_ocr_thr_1.png", "debug_ocr_thr_2.png")
                cv2.imwrite("debug_ocr_orig_1.png", crop)
                cv2.imwrite("debug_ocr_thr_1.png", big)
            except Exception:
                pass
            pil_img = Image.fromarray(big)
            raw = pytesseract.image_to_string(
                pil_img,
                config="--psm 7 -c tessedit_char_whitelist=0123456789",
            ).strip()
            digits = "".join(c for c in raw if c.isdigit())
            if digits != ipn:
                print(f"  [OCR] очікував {ipn!r} — отримав {raw!r}")
                continue
        else:
            print(f"  [OCR] pytesseract недоступний — приймаємо першу групу без перевірки")

        abs_y = win_top + g_start
        print(f"  [OCR] ✓ знайдено {ipn!r}")
        return abs_y

    print(f"  [OCR] жодна група не підтверджена для ІПН={ipn}")
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
    print(f"  [CHK] кліком на галочку: ({check_x},{check_y})  cell_tl={cell_tl}  offset=({dx},{dy})  row_top_y={row_top_y}")
    pyautogui.click(check_x, check_y)
    time.sleep(0.2)
    print(f"  [CHK] клік виконано")


def confirm_batch(delays: dict) -> None:
    """Commit the current batch of 20 and reopen the search dialog.

    Sequence: Enter (OK) → wait → Insert (reopen) → wait for dialog.
    """
    w1 = delays.get("batch_confirm_wait", 3.0)
    w2 = delays.get("batch_reopen_wait", 12.0)
    print(f"  [BATCH] натискаємо Enter (підтвердити батч)")
    pyautogui.press("return")
    print(f"  [BATCH] чекаємо {w1}с після підтвердження...")
    time.sleep(w1)
    print(f"  [BATCH] натискаємо Insert (перевідкрити пошук)")
    pyautogui.press("insert")
    print(f"  [BATCH] чекаємо {w2}с поки діалог завантажиться...")
    time.sleep(w2)
    print(f"  [BATCH] готово")


# ── Private helpers ───────────────────────────────────────────────────────────

def _yellow_present(mia_title: str) -> bool:
    """Return True if a yellow tooltip region is visible in the MIA window."""
    img_bgr, _, _ = _screenshot_mia(mia_title)
    img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(img_hsv,
                       np.array([20, 30, 200]),
                       np.array([40, 150, 255]))
    count = int(cv2.countNonZero(mask))
    return count >= 50
