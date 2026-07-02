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
set "PY=%VENV%\Scripts\python.exe"

rem pip.exe / pyinstaller.exe мiстять захардкодженi шляхи i не працюють
rem якщо venv перенесено з iншого комп'ютера -- використовуємо python -m

if not exist "%PY%" (
    echo ПОМИЛКА: .venv не знайдено. Спочатку запусти install.bat
    pause & exit /b 1
)

:: ── PyInstaller -- знайти або встановити ────────────────────────────────
rem Варiант 1: вже є у venv
set "PYINST_CMD=%PY% -m PyInstaller"
"%PY%" -m pip show pyinstaller >nul 2>&1
if %errorlevel% equ 0 goto :build

rem Варiант 2: є глобально
where pyinstaller >nul 2>&1
if %errorlevel% equ 0 (
    set "PYINST_CMD=pyinstaller"
    goto :build
)

rem Варiант 3: встановити у venv (потрiбен iнтернет)
echo Встановлення PyInstaller у .venv...
"%PY%" -m pip install pyinstaller
if %errorlevel% neq 0 (
    echo ПОМИЛКА: PyInstaller не знайдено i не вдалося встановити.
    echo Встанови вручну: pip install pyinstaller
    pause & exit /b 1
)

:build
:: ── Збiрка (app + automation + calibrate в одну папку) ───────────────────
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
