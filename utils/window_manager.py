"""
utils/window_manager.py
Cross-platform window focusing.

  Mac     — uses osascript (AppleScript) to activate apps by name.
  Windows — uses pygetwindow + ctypes to find and activate a window by title.
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


def focus_mia(mia_title_part: str = "Обіймання посад", delay: float = 0.7) -> None:
    """Bring the MIA window to the foreground.

    On Windows tries mia_title_part first, falls back to 'Заробітна плата'.
    On Mac does nothing (MIA is a Windows-only app).
    """
    if sys.platform == "darwin":
        return
    activated = _win_activate(mia_title_part)
    if not activated:
        _win_activate("Заробітна плата")
    time.sleep(delay)


# ── macOS helper ──────────────────────────────────────────────────────────────

def _mac_activate(app_name: str) -> None:
    """Activate a macOS application by name using AppleScript.

    Two-step approach:
      1. `tell application X to activate` — brings the app to front.
      2. `System Events set frontmost of process X` — ensures the window
         is truly in front even if step 1 is throttled by the OS.
    """
    subprocess.run(["osascript", "-e", f'tell application "{app_name}" to activate'])
    subprocess.run([
        "osascript", "-e",
        f'tell application "System Events" to set frontmost of process "{app_name}" to true',
    ])


# ── Windows helper ────────────────────────────────────────────────────────────

def _win_activate(title_fragment: str) -> bool:
    """Find the first window whose title contains *title_fragment* and activate it.

    Uses ctypes (SetForegroundWindow) for reliable focus on Windows, which
    avoids the silent failures of pygetwindow.activate() caused by Windows
    focus-stealing protection.

    Returns True on success, False if no matching window was found.
    """
    try:
        import ctypes
        import pygetwindow as gw  # noqa: PLC0415 — Windows-only import

        matches = gw.getWindowsWithTitle(title_fragment)  # type: ignore[attr-defined]
        if not matches:
            all_titles = [w.title for w in gw.getAllWindows() if w.title.strip()]  # type: ignore[attr-defined]
            print(f"  [WIN] вікно {title_fragment!r} не знайдено. Всі вікна: {all_titles[:15]}")
            return False

        # Prefer the window whose title most closely matches the fragment:
        # sort by length ascending so "Обіймання посад" beats
        # "Відомості — Обіймання посад" when both contain the fragment.
        matches = sorted(matches, key=lambda w: len(w.title))
        print(f"  [WIN] знайдено {len(matches)} вікно(а) для {title_fragment!r}: "
              f"{[w.title for w in matches]}")
        hwnd = matches[0]._hWnd
        user32 = ctypes.windll.user32  # type: ignore[attr-defined]

        # SW_RESTORE (9) un-minimises the window if needed
        user32.ShowWindow(hwnd, 9)

        # SetForegroundWindow alone fails when targeting a child/owned window
        # (Windows activates the owner instead). AttachThreadInput forces the
        # OS to treat our thread as part of the target window's input queue,
        # making BringWindowToTop + SetForegroundWindow work reliably.
        fg_hwnd = user32.GetForegroundWindow()
        fg_tid = user32.GetWindowThreadProcessId(fg_hwnd, None)
        tgt_tid = user32.GetWindowThreadProcessId(hwnd, None)
        if fg_tid != tgt_tid:
            user32.AttachThreadInput(fg_tid, tgt_tid, True)
        user32.BringWindowToTop(hwnd)
        result = user32.SetForegroundWindow(hwnd)
        if fg_tid != tgt_tid:
            user32.AttachThreadInput(fg_tid, tgt_tid, False)

        print(f"  [WIN] SetForegroundWindow({title_fragment!r}) → {result}")
        return True
    except Exception as e:
        print(f"  [WIN] ПОМИЛКА _win_activate({title_fragment!r}): {e}")
    return False
