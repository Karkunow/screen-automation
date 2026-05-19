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
    """Fetch the latest patch version of Python *series* (e.g. '3.12')."""
    url = "https://www.python.org/ftp/python/"
    with urllib.request.urlopen(url, timeout=15) as resp:
        html = resp.read().decode()
    prefix = series.replace(".", r"\.")
    versions = re.findall(rf'href="({prefix}\.\d+)/"', html)
    if not versions:
        raise RuntimeError(f"Не знайдено версій Python {series}")
    return sorted(versions, key=lambda v: [int(x) for x in v.split(".")])[-1]


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


def pip_download(extra_args: list[str]) -> bool:
    cmd = [sys.executable, "-m", "pip", "download",
           "-r", str(ROOT / "requirements.txt"),
           "-d", str(PACKAGES),
           *extra_args]
    return subprocess.run(cmd).returncode == 0


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
    ok = pip_download([
        "--platform", "win_amd64",
        "--python-version", PY_TARGET,
        "--only-binary", ":all:",
    ])
    if not ok:
        print("  Деякі пакети не мають готових wheels, завантажуємо source...")
        pip_download([
            "--platform", "win_amd64",
            "--python-version", PY_TARGET,
        ])

    print("\n" + "=" * 52)
    print("  Готово! Далі:")
    print("  1. Скопіюй всю папку на Windows-комп'ютер")
    print("  2. Запусти install.bat")
    print("=" * 52 + "\n")


if __name__ == "__main__":
    main()
