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
            print(f"  [WIN] знайдено вікно '{mia_title}': {wins[0].left},{wins[0].top} {wins[0].width}x{wins[0].height}")
            return wins[0]
        wins = gw.getWindowsWithTitle("Заробітна плата")
        if wins:
            print(f"  [WIN] fallback вікно 'Заробітна плата': {wins[0].left},{wins[0].top} {wins[0].width}x{wins[0].height}")
            return wins[0]
        all_titles = [w.title for w in gw.getAllWindows() if w.title.strip()]
        print(f"  [WIN] УВАГА: вікно MIA не знайдено! Всі вікна: {all_titles[:10]}")
    except ImportError:
        print("  [WIN] pygetwindow не встановлено — скріншот всього екрана")
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
            print(f"  [SCR] скріншот вікна MIA: {img_bgr.shape[1]}x{img_bgr.shape[0]} px, offset=({win.left},{win.top})")
            return img_bgr, win.left, win.top
        except Exception as e:
            print(f"  [SCR] помилка скріншоту вікна: {e} — беремо весь екран")
    img = pyautogui.screenshot()
    img_bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
    print(f"  [SCR] скріншот ВЕСЬ ЕКРАН: {img_bgr.shape[1]}x{img_bgr.shape[0]} px")
    return img_bgr, 0, 0


# ── Public API ────────────────────────────────────────────────────────────────

def type_ipn(ipn: str, cell_tl: list, delays: dict) -> None:
    """Click the IPN column cell in MIA and type the IPN character by character."""
    x, y = cell_tl
    print(f"  [TYPE] клік на клітинку MIA ({x},{y}), вводимо ІПН: {ipn}")
    pyautogui.click(x, y)
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


def wait_tooltip_gone(mia_title: str, timeout: float = 15.0,
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


def find_blue_row(ipn: str, cell_tl: list, cell_br: list, mia_title: str) -> int | None:
    """Scan the MIA window for the dark-blue highlighted row and confirm the IPN.

    Returns the absolute screen Y coordinate of the TOP of the found row,
    or None if no matching row is found.

    Dark navy-blue row HSV range (OpenCV 0-180 hue):
      H 95-125,  S 80-255,  V 40-180
    """
    print(f"  [BLUE] шукаємо синій рядок для ІПН={ipn}")
    print(f"  [BLUE] cell_tl={cell_tl} cell_br={cell_br}")
    img_bgr, win_left, win_top = _screenshot_mia(mia_title)
    img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)

    # Window-relative IPN column x bounds
    x1 = max(0, cell_tl[0] - win_left)
    x2 = min(img_bgr.shape[1], cell_br[0] - win_left)
    cell_h = max(1, cell_br[1] - cell_tl[1])
    print(f"  [BLUE] колонка в координатах вікна: x={x1}..{x2} (ширина {x2-x1}px), win_offset=({win_left},{win_top})")

    # Dark navy-blue mask
    mask = cv2.inRange(img_hsv,
                       np.array([95, 80, 40]),
                       np.array([125, 255, 180]))
    total_blue_px = int(cv2.countNonZero(mask))
    print(f"  [BLUE] всього синіх пікселів на всьому скріншоті: {total_blue_px}")

    # Restrict to IPN column width
    col_mask = np.zeros_like(mask)
    col_mask[:, x1:x2] = mask[:, x1:x2]
    col_blue_px = int(cv2.countNonZero(col_mask))

    # Find rows with enough blue pixels (at least 30% of column width)
    row_sums = col_mask.sum(axis=1)
    threshold = max(10, int((x2 - x1) * 0.3 * 255))
    blue_rows = np.where(row_sums >= threshold)[0]
    print(f"  [BLUE] синіх пікселів у колонці: {col_blue_px}, поріг на рядок: {threshold}, рядків що проходять: {len(blue_rows)}")

    # Save debug screenshot with marked column
    try:
        dbg = img_bgr.copy()
        cv2.rectangle(dbg, (x1, 0), (x2, dbg.shape[0]), (0, 255, 0), 2)
        cv2.imwrite("debug_blue_search.png", dbg)
        print(f"  [BLUE] debug скріншот збережено → debug_blue_search.png")
    except Exception as _e:
        print(f"  [BLUE] не вдалось зберегти debug скріншот: {_e}")

    if len(blue_rows) == 0:
        print(f"  [BLUE] синіх рядків не знайдено")
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
    print(f"  [BLUE] знайдено {len(groups)} синіх груп (y-діапазони у вікні): {groups}")

    for idx, (g_start, g_end) in enumerate(groups):
        print(f"  [OCR]  група {idx+1}/{len(groups)}: y={g_start}..{g_end} ({g_end-g_start+1}px висота)")
        # Verify IPN with OCR if available
        if _OCR_AVAILABLE:
            crop = img_bgr[g_start:g_end + 1, x1:x2]
            if crop.size == 0:
                print(f"  [OCR]  crop порожній — пропускаємо")
                continue
            print(f"  [OCR]  crop розмір: {crop.shape[1]}x{crop.shape[0]}px")
            # Invert: white text on dark background → black text on white
            inv = cv2.bitwise_not(crop)
            big = cv2.resize(inv, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
            # Save debug crop
            try:
                crop_path = f"debug_ocr_crop_{idx}.png"
                cv2.imwrite(crop_path, big)
                print(f"  [OCR]  crop збережено → {crop_path}")
            except Exception as _e:
                print(f"  [OCR]  не вдалось зберегти crop: {_e}")
            pil_img = Image.fromarray(cv2.cvtColor(big, cv2.COLOR_BGR2RGB))
            raw = pytesseract.image_to_string(
                pil_img,
                config="--psm 7 -c tessedit_char_whitelist=0123456789",
            ).strip()
            digits = "".join(c for c in raw if c.isdigit())
            match = digits == ipn
            print(f"  [OCR]  очікую={ipn!r}  raw={raw!r}  digits={digits!r}  збіг={'✓ ТАК' if match else '✗ НІ'}")
            if not match:
                continue
        else:
            print(f"  [OCR]  pytesseract недоступний — приймаємо першу групу без перевірки")

        abs_y = win_top + g_start
        print(f"  [BLUE] ✓ підтверджено! абсолютний y={abs_y} (win_top={win_top} + g_start={g_start})")
        return abs_y

    print(f"  [OCR] жодна група не підтверджена — повертаємо None")
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
