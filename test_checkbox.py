"""
test_checkbox.py  —  verify checkbox detection on a real row screenshot.

Simulates _is_checkbox_checked logic directly on a saved row image.

Usage:
    python test_checkbox.py <image_path>

Example:
    python test_checkbox.py debug_crop_orig.png
"""

import sys
import cv2
import numpy as np


def detect(img_bgr: np.ndarray) -> None:
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    h = gray.shape[0]
    border = ((gray >= 140) & (gray <= 190)).astype(np.uint8)

    # Drop full-height vertical separators
    col_sums = border.sum(axis=0)
    cb_cols = np.where((col_sums >= 4) & (col_sums < int(h * 0.9)))[0]
    print(f"col_sums: {list(enumerate(col_sums.tolist()))}")
    print(f"checkbox candidate cols: {cb_cols.tolist()}")

    if len(cb_cols) < 2:
        print("ERROR: checkbox border cols not found")
        return

    left_x  = int(cb_cols[0])
    right_x = int(cb_cols[-1])

    region   = border[:, left_x:right_x + 1]
    row_sums = region.sum(axis=1)
    border_rows = np.where(row_sums >= (right_x - left_x))[0]
    print(f"row_sums in [{left_x}..{right_x}]: {list(enumerate(row_sums.tolist()))}")
    print(f"border rows: {border_rows.tolist()}")

    if len(border_rows) < 2:
        print("ERROR: horizontal borders not found")
        return

    top_y    = int(border_rows[0])
    bottom_y = int(border_rows[-1])

    ix1, iy1 = left_x + 2, top_y + 2
    ix2, iy2 = right_x - 1, bottom_y - 1

    interior = gray[iy1:iy2, ix1:ix2]
    total    = interior.size
    white    = int((interior > 200).sum())
    ratio    = white / total if total else 0

    print(f"\ncheckbox border: ({left_x},{top_y}) → ({right_x},{bottom_y})")
    print(f"interior crop:   ({ix1},{iy1}) → ({ix2},{iy2})  shape={interior.shape}")
    print(f"білих пікселів:  {white}/{total} = {100*ratio:.0f}%")
    print(f"→ {'unchecked' if ratio >= 0.90 else 'CHECKED'}")

    # Save annotated image at 8×
    out = cv2.resize(img_bgr, (img_bgr.shape[1]*8, img_bgr.shape[0]*8),
                     interpolation=cv2.INTER_NEAREST)
    cv2.rectangle(out, (left_x*8, top_y*8), (right_x*8, bottom_y*8), (0, 0, 255), 2)
    cv2.imwrite("debug_cb_result.png", out)
    print("→ debug_cb_result.png saved (8× + red rect on detected checkbox)")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    img = cv2.imread(sys.argv[1])
    if img is None:
        print(f"ERROR: cannot load {sys.argv[1]}")
        sys.exit(1)

    print(f"Image: {sys.argv[1]}  {img.shape[1]}×{img.shape[0]}\n")
    detect(img)


if __name__ == "__main__":
    main()
