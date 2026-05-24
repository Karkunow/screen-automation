"""
Local OCR test on 111.jpg — runs the same HSV + crop logic as mia_handler.find_blue_row().
Auto-detects the blue row and the IPN column x bounds from the mask itself.
"""
import sys
import cv2
import numpy as np
from PIL import Image
import pytesseract

IMG_PATH = "123.png"
CONFIG_PATH = "config.json"
EXPECTED_IPN = "272222414994"
#3493810955
# ── Load config ──────────────────────────────────────────────────────────────
import json
with open(CONFIG_PATH) as f:
    cfg = json.load(f)
tl = cfg["mia_ipn_cell_tl"]
br = cfg["mia_ipn_cell_br"]
col_br = cfg.get("mia_ipn_col_br")
x1 = tl[0]
x2 = br[0]
cell_h = max(14, br[1] - tl[1])
print(f"[CFG] cell_tl={tl}  cell_br={br}  col_br={col_br}  → x={x1}..{x2} (ширина {x2-x1}px), cell_h={cell_h}px")

# ── Load image ───────────────────────────────────────────────────────────────
img_bgr = cv2.imread(IMG_PATH)
if img_bgr is None:
    sys.exit(f"Cannot read {IMG_PATH}")
h_img, w_img = img_bgr.shape[:2]
print(f"[IMG] розмір: {w_img}x{h_img}px")

# ── HSV blue mask (same as mia_handler) ─────────────────────────────────────
img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
mask = cv2.inRange(img_hsv,
                   np.array([95, 60, 40]),
                   np.array([125, 255, 255]))
total_blue = int(cv2.countNonZero(mask))
print(f"[BLUE] всього синіх пікселів: {total_blue}")

# ── Restrict mask to calibrated IPN column (x + y bounds) ──────────────────
col_mask = np.zeros_like(mask)
y1 = max(0, tl[1] - 2)
if col_br is not None:
    y2 = min(h_img, col_br[1] + 2)
else:
    y2 = int(h_img * 0.75)
col_mask[y1:y2, x1:x2] = mask[y1:y2, x1:x2]

# Find rows with enough blue pixels (15% of column width)
row_sums = col_mask.sum(axis=1)
threshold = max(10, int((x2 - x1) * 0.15 * 255))
blue_rows = np.where(row_sums >= threshold)[0]
print(f"[BLUE] поріг на рядок: {threshold}, рядків що проходять: {len(blue_rows)}")

if len(blue_rows) == 0:
    print("[BLUE] синіх рядків не знайдено — перевір HSV діапазон")
    dbg = img_bgr.copy()
    dbg[mask > 0] = (0, 255, 0)
    cv2.rectangle(dbg, (x1, 0), (x2, h_img), (0, 0, 255), 2)
    cv2.imwrite("debug_mask_overlay.png", dbg)
    print("[BLUE] збережено debug_mask_overlay.png (зелені=синя маска, червоний прямокутник=IPN колонка)")
    sys.exit(1)

# ── Group contiguous blue rows (gap ≤ 8px) ───────────────────────────────────
groups = []
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
print(f"[BLUE] знайдено {len(groups)} синіх груп: {groups}")

# ── Pick the tallest group (most likely the selected data row) ────────────────
tallest = max(groups, key=lambda g: g[1] - g[0])
g_start, g_end = tallest
raw_h = g_end - g_start + 1
crop_y1 = max(0, g_start - 2)
crop_y2 = min(h_img, crop_y1 + cell_h)
print(f"\n[BEST GROUP] y={g_start}..{g_end} raw_h={raw_h}px → crop y={crop_y1}..{crop_y2} (cell_h з config={cell_h}px)")

# ── Crop: IPN column only, full-row y band ────────────────────────────────────
crop = img_bgr[crop_y1:crop_y2, x1:x2]
print(f"[CROP] розмір: {crop.shape[1]}x{crop.shape[0]}px")
cv2.imwrite("debug_crop_orig.png", crop)

# Grayscale → threshold: white text on blue bg → black text on white bg
gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
_, thr = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
big = cv2.resize(thr, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)

# Keep last 2 OCR crops with rotation
import os
if os.path.exists("debug_ocr_orig_1.png"):
    os.replace("debug_ocr_orig_1.png", "debug_ocr_orig_2.png")
if os.path.exists("debug_ocr_thr_1.png"):
    os.replace("debug_ocr_thr_1.png", "debug_ocr_thr_2.png")
cv2.imwrite("debug_ocr_orig_1.png", crop)
cv2.imwrite("debug_ocr_thr_1.png", big)

# ── OCR ───────────────────────────────────────────────────────────────────────
pil = Image.fromarray(big)

raw_full = pytesseract.image_to_string(pil, config="--psm 7").strip()
print(f"[OCR psm7 full] {raw_full!r}")

raw_digits = pytesseract.image_to_string(
    pil, config="--psm 7 -c tessedit_char_whitelist=0123456789"
).strip()
digits = "".join(c for c in raw_digits if c.isdigit())
match = digits == EXPECTED_IPN
print(f"[OCR digits]    {digits!r}  (очікую {EXPECTED_IPN!r}  збіг={'✓ ТАК' if match else '✗ НІ'})")

print(f"\n[RESULT] debug_crop_orig.png — оригінал  |  debug_crop_ocr.png — те, що бачить Tesseract")
