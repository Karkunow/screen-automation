import os
import sys


def setup() -> None:
    """When running as a PyInstaller frozen exe, point pytesseract to the
    bundled tesseract.exe that lives next to _internal/ (PyInstaller onedir)."""
    if not getattr(sys, 'frozen', False):
        return
    try:
        import pytesseract
        base = sys._MEIPASS  # points to _internal/ in onedir builds
        cmd = os.path.join(base, 'tesseract', 'tesseract.exe')
        if os.path.exists(cmd):
            pytesseract.pytesseract.tesseract_cmd = cmd
            # Tesseract appends lang+".traineddata" directly to TESSDATA_PREFIX,
            # so point it at the tessdata/ subfolder where the files actually live.
            os.environ.setdefault(
                'TESSDATA_PREFIX',
                os.path.join(base, 'tesseract', 'tessdata'),
            )
    except Exception:
        pass
