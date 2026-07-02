import glob
import os

# ── Locate Tesseract at build time ────────────────────────────────────────
TESS_DIR = os.environ.get('TESSERACT_DIR', '')
if not TESS_DIR:
    for _p in [
        os.path.join(os.environ.get('ProgramFiles', ''), 'Tesseract-OCR'),
        os.path.join(os.environ.get('ProgramFiles(x86)', ''), 'Tesseract-OCR'),
        r'C:\Tesseract-OCR',
        r'C:\Program Files\Tesseract-OCR',
        r'C:\Program Files (x86)\Tesseract-OCR',
    ]:
        if _p and os.path.exists(os.path.join(_p, 'tesseract.exe')):
            TESS_DIR = _p
            break

if TESS_DIR:
    print(f'[spec] Tesseract знайдено: {TESS_DIR}')
else:
    print('[spec] УВАГА: Tesseract не знайдено — OCR не буде працювати у зібраному exe')

# Collect tesseract.exe + DLLs as binaries (placed into tesseract/ subfolder)
tess_binaries = []
if TESS_DIR:
    tess_binaries.append((os.path.join(TESS_DIR, 'tesseract.exe'), 'tesseract'))
    for _dll in glob.glob(os.path.join(TESS_DIR, '*.dll')):
        tess_binaries.append((_dll, 'tesseract'))

# Collect tessdata: prefer installers\tessdata (curated), fall back to Tesseract install
tess_datas = []
_tessdata_src = os.path.join('installers', 'tessdata')
if not os.path.isdir(_tessdata_src) and TESS_DIR:
    _tessdata_src = os.path.join(TESS_DIR, 'tessdata')
if os.path.isdir(_tessdata_src):
    for _td in glob.glob(os.path.join(_tessdata_src, '*.traineddata')):
        tess_datas.append((_td, 'tesseract/tessdata'))

# ─────────────────────────────────────────────────────────────────────────
a = Analysis(
    ['automation.py'],
    pathex=[],
    binaries=tess_binaries,
    datas=tess_datas,
    hiddenimports=[
        'pygetwindow',
        'pyscreeze',
        'pymsgbox',
        'mouseinfo',
        'pytesseract',
        'cv2',
        'numpy',
        'PIL',
        'PIL.Image',
        'PIL.ImageGrab',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='automation',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    icon='img/icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='automation',
)
