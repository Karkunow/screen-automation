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

:: ── PyInstaller -- перевiрити наявнiсть ───────────────────────────────────
set "PIP=%VENV%\Scripts\pip"
set "PYINST=%VENV%\Scripts\pyinstaller"

if not exist "%VENV%\Scripts\python.exe" (
    echo ПОМИЛКА: .venv не знайдено. Спочатку запусти install.bat
    pause & exit /b 1
)

"%PIP%" show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo Встановлення PyInstaller...
    "%PIP%" install pyinstaller
    if %errorlevel% neq 0 (
        echo ПОМИЛКА при встановленнi PyInstaller.
        pause & exit /b 1
    )
)

:: ── Збiрка automation.exe ─────────────────────────────────────────────────
echo [1/2] Збiрка automation.exe...
"%PYINST%" automation.spec --noconfirm --distpath "%ROOT%dist"
if %errorlevel% neq 0 (
    echo ПОМИЛКА при збiрцi automation.exe
    pause & exit /b 1
)
echo   OK: dist\automation\automation.exe

:: ── Збiрка calibrate.exe ──────────────────────────────────────────────────
echo.
echo [2/2] Збiрка calibrate.exe...
"%PYINST%" calibrate.spec --noconfirm --distpath "%ROOT%dist"
if %errorlevel% neq 0 (
    echo ПОМИЛКА при збiрцi calibrate.exe
    pause & exit /b 1
)
echo   OK: dist\calibrate\calibrate.exe

:: ── Inno Setup (опцiонально) ──────────────────────────────────────────────
echo.
echo Шукаємо Inno Setup...
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
    echo Компiляцiя iнсталятора...
    "!ISCC!" "%ROOT%setup.iss"
    if !errorlevel! equ 0 (
        echo   OK: installer_output\ScreenAutomation_Setup.exe
    ) else (
        echo   ПОМИЛКА при компiляцiї iнсталятора.
    )
) else (
    echo   Inno Setup не знайдено -- iнсталятор не зiбрано.
    echo   Завантажити: https://jrsoftware.org/isdl.php
    echo   Пiсля встановлення запусти build.bat знову.
)

echo.
echo ============================================
echo   Готово!
echo   Файли знаходяться у папцi dist\
echo ============================================
echo.
pause
endlocal
