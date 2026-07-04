"""
utils/excel_reader.py
Read cell values from Numbers (Mac) / Excel (Windows) via the clipboard.

Flow per row
  • Row 0   : click the calibrated starting cell → copy → read clipboard
  • Row N>0 : press Down arrow (already on the right cell) → copy → read clipboard
"""

import sys
import time

import pyautogui
import pyperclip

_MOD = "command" if sys.platform == "darwin" else "ctrl"


def _copy() -> None:
    """Send Ctrl+C (Mac: Cmd+C) using virtual key codes on Windows.

    pyautogui.hotkey('ctrl', 'c') sends the character currently mapped to 'c'
    which changes with non-English keyboard layouts. keybd_event with
    VK_C (0x43) always targets the physical C key regardless of layout.
    """
    if sys.platform != "darwin":
        import ctypes
        VK_CONTROL, VK_C, KEYUP = 0x11, 0x43, 0x0002
        ke = ctypes.windll.user32.keybd_event  # type: ignore[attr-defined]
        ke(VK_CONTROL, 0, 0, 0)
        ke(VK_C, 0, 0, 0)
        ke(VK_C, 0, KEYUP, 0)
        ke(VK_CONTROL, 0, KEYUP, 0)
    else:
        pyautogui.hotkey("command", "c")


def click_and_read(row: int, x: int, y: int, copy_delay: float = 0.4) -> str:
    """Click cell at (x, y), select all text inside, copy, return the plain-text value."""
    pyperclip.copy("")  # очистити буфер перед копіюванням
    if row == 0:
        pyautogui.moveTo(x, y, duration=0.1)
        pyautogui.click(button="left")
    else:
        print(f"  → рухаємося вниз до рядка {row + 1}…", flush=True)
        move_down()
        print(f"  → редагуємо рядок {row + 1}…", flush=True)
        if sys.platform == "darwin":
            pyautogui.hotkey("option", "enter")
    print(f"  → виділяємо текст {_MOD} + А {row + 1}…", flush=True)
    if sys.platform == "darwin":
        pyautogui.hotkey("ctrl", "a")
    time.sleep(0.1)
    return read_current_cell(copy_delay=copy_delay)


def read_current_cell(copy_delay: float = 0.4) -> str:
    """Copy the currently selected cell and return its plain-text value."""
    time.sleep(0.1)
    _copy()
    time.sleep(copy_delay)
    if sys.platform == "darwin":
        pyautogui.press("escape")      # прибрати фокус з попередньої клітинки
    return _normalize(pyperclip.paste().strip())


def _normalize(raw: str) -> str:
    """Convert Numbers scientific notation (e.g. '4,115590309E+9') to plain digits."""
    cleaned = raw.replace(",", ".")
    try:
        return str(int(float(cleaned)))
    except (ValueError, OverflowError):
        return raw


def write_result(text: str) -> None:
    """Write *text* into column C (one column right of IPN column B) for the given row.

    Uses clipboard paste so Ukrainian text works regardless of keyboard layout.
    """
    print(f"  [XLS] записуємо результат: {text!r}", flush=True)
    # On Windows: press Escape first to clear any pending copy-mode (marching ants)
    # or autocomplete state left over from the previous read. Safe no-op otherwise.
    if sys.platform != "darwin":
        pyautogui.press("escape")
        time.sleep(0.1)
    # Cursor is on col B — move one column right → col C
    pyautogui.press("right")
    time.sleep(0.2)
    # Paste via clipboard (safe for non-ASCII / Ukrainian)
    pyperclip.copy(text)
    pyautogui.hotkey(_MOD, "v")
    time.sleep(0.3)
    # Return to col B
    pyautogui.press("left")
    time.sleep(0.15)
    print(f"  [XLS] результат записано", flush=True)


def move_down() -> None:
    """Move the selection one row down with the Down arrow key."""
    pyautogui.press("down")
    time.sleep(0.3)
