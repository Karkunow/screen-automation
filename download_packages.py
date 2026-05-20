"""
download_packages.py — запусти ОДИН РАЗ на будь-якій машині з інтернетом.

Завантажує в поточну папку:
  installers/
    python-3.12.x-amd64.exe       — Python інсталятор для Windows
    tesseract-ocr-w64-setup.exe   — Tesseract OCR
    tessdata/
      ukr.traineddata              — Мовний пакет: Українська
      eng.traineddata              — Мовний пакет: English
  packages/
    *.whl / *.tar.gz               — Python залежності

Після завершення скопіюй всю папку на офлайн-Windows-машину
та запусти install.bat
"""

import re
import subprocess
import sys
import urllib.request
from pathlib import Path

TESSERACT_URL = (
    "https://github.com/UB-Mannheim/tesseract/releases/download/"
    "v5.4.0.20240606/tesseract-ocr-w64-setup-5.4.0.20240606.exe"
)
TESSDATA_BASE = "https://github.com/tesseract-ocr/tessdata_fast/raw/main"
TESSDATA_FILES = ["ukr.traineddata", "eng.traineddata"]

ROOT = Path(__file__).parent
INSTALLERS = ROOT / "installers"
TESSDATA_DIR = INSTALLERS / "tessdata"
PACKAGES = ROOT / "packages"
PY_TARGET = "3.12"


# ── helpers ───────────────────────────────────────────────────────────────────

def get_latest_python(series: str) -> str:
    """Fetch the latest patch version of Python *series* that has a Windows installer."""
    url = "https://www.python.org/ftp/python/"
    with urllib.request.urlopen(url, timeout=15) as resp:
        html = resp.read().decode()
    prefix = series.replace(".", r"\.")
    versions = re.findall(rf'href="({prefix}\.\d+)/"', html)
    if not versions:
        raise RuntimeError(f"Не знайдено версій Python {series}")
    # Check versions from newest to oldest; return first that has an amd64 installer
    for ver in sorted(versions, key=lambda v: [int(x) for x in v.split(".")], reverse=True):
        exe_url = f"https://www.python.org/ftp/python/{ver}/python-{ver}-amd64.exe"
        try:
            req = urllib.request.Request(exe_url, method="HEAD")
            with urllib.request.urlopen(req, timeout=10):
                return ver
        except Exception:
            continue
    raise RuntimeError(f"Не знайдено робочого інсталятора Python {series}")


def download(url: str, dest: Path) -> None:
    if dest.exists():
        print(f"  вже є: {dest.name}")
        return
    print(f"  ↓ {dest.name} ...", end="", flush=True)
    tmp = dest.with_suffix(dest.suffix + ".tmp")
    try:
        urllib.request.urlretrieve(url, tmp)
        tmp.rename(dest)
    except Exception as exc:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"Помилка завантаження {url}: {exc}") from exc
    print(f" {dest.stat().st_size / 1_048_576:.1f} МБ")


def download_all_packages() -> None:
    """Download Python packages for Windows x64 / Python 3.12.

    Per-package strategy:
      1. Try binary wheel (win_amd64)  — for numpy, Pillow, opencv, etc.
      2. Fall back to platform-agnostic — for pure-Python packages
         like pyautogui (sdist only), pyperclip, pytesseract, pygetwindow.
    """
    req_file = ROOT / "requirements.txt"
    specs = [
        line.strip()
        for line in req_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    dest = str(PACKAGES)
    errors: list[str] = []

    for spec in specs:
        pkg_name = re.split(r"[><=!@]", spec)[0].strip()
        # Attempt 1: binary wheel for Windows
        r = subprocess.run(
            [sys.executable, "-m", "pip", "download", spec,
             "-d", dest,
             "--platform", "win_amd64",
             "--python-version", PY_TARGET,
             "--only-binary", ":all:",
             "--quiet"],
            capture_output=True,
        )
        if r.returncode == 0:
            print(f"  {pkg_name:30s} wheel (win_amd64)")
            continue

        # Attempt 2: pure-Python wheel/sdist targeting Windows
        r2 = subprocess.run(
            [sys.executable, "-m", "pip", "download", spec,
             "-d", dest,
             "--platform", "win_amd64",
             "--python-version", PY_TARGET,
             "--quiet"],
            capture_output=True,
        )
        if r2.returncode == 0:
            print(f"  {pkg_name:30s} sdist / pure-python")
        else:
            print(f"  {pkg_name:30s} ПОМИЛКА")
            errors.append(r2.stderr.decode(errors="replace").strip())

    if errors:
        print("\n  Не вдалось завантажити:")
        for e in errors:
            print(f"    {e}")
        sys.exit(1)


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    INSTALLERS.mkdir(exist_ok=True)
    TESSDATA_DIR.mkdir(exist_ok=True)
    PACKAGES.mkdir(exist_ok=True)

    # 1. Python installer
    print(f"\n=== [1/3] Python {PY_TARGET} інсталятор ===")
    py_version = get_latest_python(PY_TARGET)
    py_url = (f"https://www.python.org/ftp/python/{py_version}/"
              f"python-{py_version}-amd64.exe")
    download(py_url, INSTALLERS / f"python-{py_version}-amd64.exe")

    # 2. Tesseract + tessdata
    print("\n=== [2/3] Tesseract OCR + мовні пакети ===")
    download(TESSERACT_URL, INSTALLERS / "tesseract-ocr-w64-setup.exe")
    for lang in TESSDATA_FILES:
        download(f"{TESSDATA_BASE}/{lang}", TESSDATA_DIR / lang)

    # 3. Python wheels for Windows x64 / Python 3.12
    print(f"\n=== [3/3] Python пакети (win_amd64 / Python {PY_TARGET}) ===")
    # setuptools + wheel needed to build sdist packages offline
    for build_dep in ("setuptools", "wheel"):
        subprocess.run(
            [sys.executable, "-m", "pip", "download", build_dep,
             "-d", str(PACKAGES),
             "--platform", "win_amd64",
             "--python-version", PY_TARGET,
             "--only-binary", ":all:",
             "--quiet"],
            capture_output=True,
        )
    download_all_packages()

    print("\n" + "=" * 52)
    print("  Готово! Далі:")
    print("  1. Скопіюй всю папку на Windows-комп'ютер")
    print("  2. Запусти install.bat")
    print("=" * 52 + "\n")


if __name__ == "__main__":
    main()
