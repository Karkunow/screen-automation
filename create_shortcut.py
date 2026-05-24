"""
create_shortcut.py
Run once to create a desktop shortcut for МІА Автоматизація.

Usage:
    python create_shortcut.py
or double-click create_shortcut.bat
"""

import os
import pathlib
import subprocess
import sys


def main():
    app_dir = pathlib.Path(__file__).parent.resolve()

    # Find pythonw.exe (no console window when launching GUI)
    pythonw = pathlib.Path(sys.executable).parent / "pythonw.exe"
    if not pythonw.exists():
        print(f"[ERROR] pythonw.exe not found at {pythonw}")
        print("Make sure Python is installed correctly.")
        input("Press Enter to exit...")
        sys.exit(1)

    app_script = app_dir / "app.py"
    icon_path = app_dir / "img" / "icon.ico"
    desktop = pathlib.Path(os.environ["USERPROFILE"]) / "Desktop"
    shortcut_path = str(desktop / "МІА Автоматизація.lnk")

    # Build PowerShell command to create the .lnk shortcut
    icon_str = str(icon_path) if icon_path.exists() else ""
    ps_cmd = (
        f"$ws = New-Object -ComObject WScript.Shell; "
        f"$s = $ws.CreateShortcut('{shortcut_path}'); "
        f"$s.TargetPath = '{pythonw}'; "
        f"$s.Arguments = '\"{app_script}\"'; "
        f"$s.WorkingDirectory = '{app_dir}'; "
        f"$s.Description = 'МІА Автоматизація'; "
    )
    if icon_str:
        ps_cmd += f"$s.IconLocation = '{icon_str}'; "
    ps_cmd += "$s.Save()"

    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        print(f"✓ Ярлик створено: {shortcut_path}")
        if not icon_str:
            print("  (Іконку не знайдено — поклади img/icon.ico і запусти знову.)")
    else:
        print(f"[ERROR] Не вдалося створити ярлик.")
        print(result.stderr)
        input("Press Enter to exit...")
        sys.exit(1)

    input("Натисни Enter для виходу...")


if __name__ == "__main__":
    main()
