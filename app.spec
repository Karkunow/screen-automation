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
    print('[spec] УВАГА: Tesseract не знайдено — OCR не буде працювати у зiбраному exe')

tess_binaries = []
tess_datas = []
if TESS_DIR:
    tess_binaries.append((os.path.join(TESS_DIR, 'tesseract.exe'), 'tesseract'))
    for _dll in glob.glob(os.path.join(TESS_DIR, '*.dll')):
        tess_binaries.append((_dll, 'tesseract'))
    _tessdata_src = os.path.join('installers', 'tessdata')
    if not os.path.isdir(_tessdata_src):
        _tessdata_src = os.path.join(TESS_DIR, 'tessdata')
    if os.path.isdir(_tessdata_src):
        for _td in glob.glob(os.path.join(_tessdata_src, '*.traineddata')):
            tess_datas.append((_td, 'tesseract/tessdata'))

# ── Shared hidden imports ─────────────────────────────────────────────────
_hidden = [
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
]

# ── Three Analysis passes ─────────────────────────────────────────────────

a_app = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=_hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

a_auto = Analysis(
    ['automation.py'],
    pathex=[],
    binaries=tess_binaries,
    datas=tess_datas,
    hiddenimports=_hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

a_calib = Analysis(
    ['calibrate.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['pygetwindow', 'pyscreeze', 'pymsgbox', 'mouseinfo'],
    hookspath=[],
    runtime_hooks=[],
    excludes=['pytesseract', 'cv2'],
    noarchive=False,
)

# ── EXE objects ───────────────────────────────────────────────────────────

pyz_app = PYZ(a_app.pure)
exe_app = EXE(
    pyz_app, a_app.scripts, [],
    exclude_binaries=True,
    name='app',
    console=False,  # без чорного вiкна CMD
    icon='img/icon.ico',
)

pyz_auto = PYZ(a_auto.pure)
exe_auto = EXE(
    pyz_auto, a_auto.scripts, [],
    exclude_binaries=True,
    name='automation',
    console=True,
    icon='img/icon.ico',
)

pyz_calib = PYZ(a_calib.pure)
exe_calib = EXE(
    pyz_calib, a_calib.scripts, [],
    exclude_binaries=True,
    name='calibrate',
    console=True,
    icon='img/icon.ico',
)

# ── Single COLLECT — всi три exe + один спiльний _internal/ ──────────────
# PyInstaller дедуплiкує спiльнi бiблiотеки автоматично.
coll = COLLECT(
    exe_app,  a_app.binaries,  a_app.zipfiles,  a_app.datas,
    exe_auto, a_auto.binaries, a_auto.zipfiles, a_auto.datas,
    exe_calib, a_calib.binaries, a_calib.zipfiles, a_calib.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='screen_automation',
)
