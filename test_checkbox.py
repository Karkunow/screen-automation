"""
test_checkbox.py  —  calibrate checkbox detection thresholds.

Loads img/checkbox_unchecked.png, img/checkbox_checked.png, and an optional
extra image (argv[1], default: debug_crop_orig.png) and prints pixel stats
for the inner region of each, then simulates the detection logic.

Usage:
    python test_checkbox.py [image_path]
"""

import sys
import os
import cv2
import numpy as np


def analyze(label: str, img_bgr: np.ndarray, pad: int = 5) -> None:
    """Crop centre ±pad px, print grayscale stats, report checked/unchecked."""
    h, w = img_bgr.shape[:2]
    cx, cy = w // 2, h // 2
    x1, y1 = max(0, cx - pad), max(0, cy - pad)
    x2, y2 = min(w, cx + pad), min(h, cy + pad)
    crop = img_bgr[y1:y2, x1:x2]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    total = gray.size

    very_light   = int((gray > 200).sum())   # white (unchecked interior)
    medium_gray  = int(((gray > 80) & (gray < 200)).sum())  # gray (checked bg)
    very_dark    = int((gray < 80).sum())    # dark border / shadow

    mean_val = float(gray.mean())
    std_val  = float(gray.std())

    # Detection logic variants
    # A: original (dark+light) — WRONG: checked box is gray, not dark+white
    det_a = very_dark > 10 and very_light > int(total * 0.25)
    # B: gray-based  (checked = lots of medium-gray pixels)
    det_b = medium_gray > int(total * 0.30)
    # C: mean-based  (unchecked = very bright interior, mean > 220)
    det_c = mean_val < 220

    print(f"\n{'─'*48}")
    print(f"  {label}")
    print(f"  crop {gray.shape}  total={total}")
    print(f"  very_light (>200)  : {very_light:3d}  ({100*very_light/total:.0f}%)")
    print(f"  medium_gray(80-200): {medium_gray:3d}  ({100*medium_gray/total:.0f}%)")
    print(f"  very_dark  (<80)   : {very_dark:3d}  ({100*very_dark/total:.0f}%)")
    print(f"  mean={mean_val:.1f}  std={std_val:.1f}")
    print(f"  → A (dark+light)  : {'CHECKED' if det_a else 'unchecked'}")
    print(f"  → B (medium>30%)  : {'CHECKED' if det_b else 'unchecked'}")
    print(f"  → C (mean<220)    : {'CHECKED' if det_c else 'unchecked'}")

    # Save annotated crop at 8× zoom
    out = cv2.resize(crop, (crop.shape[1]*8, crop.shape[0]*8), interpolation=cv2.INTER_NEAREST)
    safe = label.replace(" ", "_").replace("/", "_").replace(":", "").replace("(", "").replace(")", "")
    cv2.imwrite(f"debug_cb_{safe}.png", out)
    print(f"  → saved debug_cb_{safe}.png  (8× zoom)")


def load(path: str):
    img = cv2.imread(path)
    if img is None:
        print(f"  [!] не вдалося завантажити: {path}")
    return img


def main():
    root = os.path.dirname(os.path.abspath(__file__))

    items = [
        ("unchecked img", os.path.join(root, "img", "checkbox_unchecked.png")),
        ("checked   img", os.path.join(root, "img", "checkbox_checked.png")),
    ]

    extra = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, "debug_crop_orig.png")
    items.append((f"extra_{os.path.basename(extra)}", extra))

    print("Checkbox detection threshold test")
    print("=" * 48)
    for label, path in items:
        img = load(path)
        if img is not None:
            analyze(label, img)
    print(f"\n{'─'*48}")
    print("Recommendation:")
    print("  Use logic B (medium_gray > 30%) if checked box has gray background.")
    print("  Use logic C (mean < 220)        as a simpler alternative.")


if __name__ == "__main__":
    main()
