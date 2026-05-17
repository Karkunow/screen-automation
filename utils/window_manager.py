"""
utils/window_manager.py
Cross-platform window focusing.

  Mac     — uses osascript (AppleScript) to activate apps by name.
  Windows — uses pygetwindow to find and activate a window by title.
"""

import subprocess
import sys
import time


def focus_spreadsheet(delay: float = 0.7) -> None:
    """Bring Numbers (Mac) or Excel (Windows) to the foreground."""
    if sys.platform == "darwin":
        _mac_activate("Numbers")
    else:
        _win_activate("Excel")
    time.sleep(delay)


def focus_browser(chrome_title_part: str = "", delay: float = 0.7) -> None:
    """Bring the Chrome window with Google Sheets to the foreground.

    On Mac the app is activated by name — no title needed.
    On Windows we search by window title; falls back to 'Google Chrome'.
    """
    if sys.platform == "darwin":
        _mac_activate("Google Chrome")
    else:
        activated = False
        if chrome_title_part:
            activated = _win_activate(chrome_title_part)
        if not activated:
            _win_activate("Google Chrome")
    time.sleep(delay)


# ── macOS helper ───────────────────────────────────────────────────────────────────

def _mac_activate(app_name: str) -> None:
    """Activate a macOS application by name using AppleScript.

    Two-step approach:
      1. `tell application X to activate` — brings the app to front.
      2. `System Events set frontmost of process X` — ensures the window
         is truly in front even if step 1 is throttled by the OS.
    """
    # Step 1: activate via the app itself
    subprocess.run(["osascript", "-e", f'tell application "{app_name}" to activate'])
    # Step 2: force frontmost via System Events (works around -10006 errors)
    subprocess.run([
        "osascript", "-e",
        f'tell application "System Events" to set frontmost of process "{app_name}" to true',
    ])


# ── Windows helper ────────────────────────────────────────────────────────────

def _win_activate(title_fragment: str) -> bool:
    """Find the first window whose title contains *title_fragment* and activate it.
    Returns True on success, False if no matching window was found.
    """
    try:
        import pygetwindow as gw  # noqa: PLC0415 — Windows-only import
        matches = gw.getWindowsWithTitle(title_fragment)
        if matches:
            try:
                matches[0].activate()
                return True
            except Exception:
                pass
    except ImportError:
        pass
    return False
