@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo.
echo ============================================
echo   Screen Automation -- Збiрка EXE
echo ============================================
echo.

set "ROOT=%~dp0"
set "VENV=%ROOT%.venv"
set "VENV_SITE=%VENV%\Lib\site-packages"

rem Не використовуємо .venv\Scripts\python.exe -- вiн падає з "No Python at ?????"
rem коли iм'я користувача мiстить не-ASCII символи (кирилиця тощо).
rem Замiсть цього: знаходимо базовий Python i пiдключаємо пакети venv через PYTHONPATH.

:: ── Знайти базовий Python ─────────────────────────────────────────────────
set "PY="

rem py.exe launcher -- найнадiйнiший спосiб
py --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%v in ('py -c "import sys; print(sys.executable)" 2^>nul') do set "PY=%%v"
)

rem Вiдомi шляхи (per-user та system)
if not defined PY for %%p in (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "%ProgramFiles%\Python313\python.exe"
    "%ProgramFiles%\Python312\python.exe"
    "%ProgramFiles%\Python311\python.exe"
    "C:\Python313\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
) do if not defined PY if exist %%p set "PY=%%~p"

if not defined PY (
    echo ПОМИЛКА: Python не знайдено.
    echo Встанови Python або запусти install.bat спочатку.
    pause & exit /b 1
)
echo   Python: !PY!

:: ── Перевiрити наявнiсть пакетiв venv ────────────────────────────────────
if not exist "%VENV_SITE%\" (
    echo ПОМИЛКА: .venv\Lib\site-packages не знайдено.
    echo Запусти install.bat спочатку.
    pause & exit /b 1
)

rem Пакети venv доступнi через PYTHONPATH -- без запуску venv python.exe
set "PYTHONPATH=%VENV_SITE%"

:: ── PyInstaller -- перевiрити або встановити ─────────────────────────────
set "PYINST_CMD="

rem Варiант 1: вже є у venv (перевiряємо папку, не через pip)
if exist "%VENV_SITE%\PyInstaller\" (
    set "PYINST_CMD=!PY! -m PyInstaller"
    goto :build
)

rem Варiант 2: є глобально
where pyinstaller >nul 2>&1
if %errorlevel% equ 0 (
    set "PYINST_CMD=pyinstaller"
    goto :build
)

rem Варiант 3: встановити у venv (потрiбен iнтернет)
echo Встановлення PyInstaller...
"!PY!" -m pip install --target "%VENV_SITE%" pyinstaller
if %errorlevel% neq 0 (
    echo ПОМИЛКА: не вдалося встановити PyInstaller.
    echo Встанови вручну: pip install pyinstaller
    pause & exit /b 1
)
set "PYINST_CMD=!PY! -m PyInstaller"

:build
:: ── Збiрка (app + automation + calibrate в одну папку) ───────────────────
echo.
echo [1/2] Збiрка exe-файлiв (PyInstaller)...
!PYINST_CMD! app.spec --noconfirm --distpath "%ROOT%dist"
if %errorlevel% neq 0 (
    echo ПОМИЛКА при збiрцi.
    pause & exit /b 1
)
echo   OK: dist\screen_automation\  ^(app.exe, automation.exe, calibrate.exe^)

:: ── Inno Setup ───────────────────────────────────────────────────────────
echo.
echo [2/2] Компiляцiя iнсталятора (Inno Setup)...
set "ISCC="
for %%p in (
    "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
    "%ProgramFiles%\Inno Setup 6\ISCC.exe"
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    "C:\Program Files\Inno Setup 6\ISCC.exe"
) do (
    if not defined ISCC if exist %%p set "ISCC=%%~p"
)

if defined ISCC (
    "!ISCC!" "%ROOT%setup.iss"
    if !errorlevel! equ 0 (
        echo   OK: installer_output\ScreenAutomation_Setup.exe
    ) else (
        echo   ПОМИЛКА при компiляцiї iнсталятора.
        pause & exit /b 1
    )
) else (
    echo   Inno Setup не знайдено.
    echo   Завантажити: https://jrsoftware.org/isdl.php
    echo   Пiсля встановлення запусти build.bat знову.
)

echo.
echo ============================================
echo   Готово!
echo ============================================
echo.
pause
endlocal
