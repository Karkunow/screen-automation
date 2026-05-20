@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo.
echo ============================================
echo   Screen Automation -- Vstanovlennya
echo ============================================
echo.

set "ROOT=%~dp0"
set "INSTALLERS=%ROOT%installers"
set "PACKAGES=%ROOT%packages"
set "VENV=%ROOT%.venv"

:: ── Перевірка прав адміністратора ────────────────────────────────────────────
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo  [!] Скрипт запущено БЕЗ прав адміністратора.
    echo      Tesseract встановлюється у %ProgramFiles% і потребує admin.
    echo      Рекомендується: правий клік на install.bat -^> "Запуск від імені адміністратора"
    echo.
    choice /c YN /m "Продовжити все одно?"
    if errorlevel 2 exit /b 0
    echo.
)

:: ═══════════════════════════════════════════════════════════════════════════
:: [1/4] Python
:: ═══════════════════════════════════════════════════════════════════════════
echo [1/4] Перевірка Python...
python --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo   %%v -- вже встановлено, пропускаємо.
    goto :install_tesseract
)

echo   Python не знайдено. Шукаємо iнсталятор...
set "PY_EXE="
for %%f in ("%INSTALLERS%\python-*.exe") do set "PY_EXE=%%f"
if not defined PY_EXE (
    echo   ПОМИЛКА: не знайдено python-*.exe у папцi installers\
    echo   Запусти download_packages.py на машинi з iнтернетом спочатку.
    pause & exit /b 1
)
echo   Встановлення: %PY_EXE%
"%PY_EXE%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
if %errorlevel% neq 0 (
    echo   ПОМИЛКА пiд час встановлення Python.
    pause & exit /b 1
)
echo   Python встановлено.
:: Оновити PATH для поточної сесiї з реєстру
for /f "tokens=2*" %%a in ('reg query "HKCU\Environment" /v PATH 2^>nul') do (
    set "PATH=%%b;%PATH%"
)

:install_tesseract
:: ═══════════════════════════════════════════════════════════════════════════
:: [2/4] Tesseract OCR
:: ═══════════════════════════════════════════════════════════════════════════
echo.
echo [2/4] Перевiрка Tesseract...
where tesseract >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%v in ('tesseract --version 2^>^&1 ^| findstr /i "tesseract"') do echo   %%v -- вже встановлено, пропускаємо.
    goto :copy_tessdata
)

echo   Tesseract не знайдено. Шукаємо iнсталятор...
set "TESS_EXE="
for %%f in ("%INSTALLERS%\tesseract-*.exe") do set "TESS_EXE=%%f"
if not defined TESS_EXE (
    echo   ПОМИЛКА: не знайдено tesseract-*.exe у папцi installers\
    pause & exit /b 1
)
echo   Встановлення: %TESS_EXE%
"%TESS_EXE%" /S
if %errorlevel% neq 0 (
    echo   ПОМИЛКА пiд час встановлення Tesseract.
    pause & exit /b 1
)
echo   Tesseract встановлено.

:: Додати Tesseract до PATH користувача (без /M, без admin)
set "TESS_BIN=%ProgramFiles%\Tesseract-OCR"
powershell -NoProfile -Command ^
  "$cur = [Environment]::GetEnvironmentVariable('PATH','Machine'); ^
   if ($cur -notlike '*Tesseract-OCR*') { ^
     [Environment]::SetEnvironmentVariable('PATH', $cur + ';%TESS_BIN%', 'Machine') ^
   }" >nul 2>&1
set "PATH=%PATH%;%TESS_BIN%"
echo   Tesseract додано до PATH.

:copy_tessdata
:: ═══════════════════════════════════════════════════════════════════════════
:: [3/4] Мовнi пакети Tesseract
:: ═══════════════════════════════════════════════════════════════════════════
echo.
echo [3/4] Мовнi пакети Tesseract...
if exist "%INSTALLERS%\tessdata\" (
    set "TESS_DATA=%ProgramFiles%\Tesseract-OCR\tessdata"
    if exist "!TESS_DATA!\" (
        copy /y "%INSTALLERS%\tessdata\*.traineddata" "!TESS_DATA!\" >nul
        echo   Скопiйовано: ukr.traineddata, eng.traineddata
    ) else (
        echo   Папку tessdata Tesseract не знайдено -- пропускаємо.
    )
) else (
    echo   installers\tessdata не знайдено -- пропускаємо.
)

:: ═══════════════════════════════════════════════════════════════════════════
:: [4/4] Python venv + пакети
:: ═══════════════════════════════════════════════════════════════════════════
echo.
echo [4/4] Python venv та залежностi...

:: Знайти python.exe (PATH мiг не оновитись пiсля тихого встановлення)
set "PY=python"
python --version >nul 2>&1
if %errorlevel% neq 0 (
    set "PY="
    for %%p in (
        "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
        "C:\Python312\python.exe"
        "C:\Python313\python.exe"
    ) do (
        if not defined PY if exist %%p set "PY=%%~p"
    )
    if not defined PY (
        echo   ПОМИЛКА: python.exe не знайдено.
        echo   Закрий CMD, вiдкрий знову i запусти install.bat ще раз.
        pause & exit /b 1
    )
)
echo   Використовуємо: %PY%

:: Створити venv
if not exist "%VENV%\Scripts\python.exe" (
    echo   Створення .venv...
    "%PY%" -m venv "%VENV%"
    if %errorlevel% neq 0 (
        echo   ПОМИЛКА при створеннi venv.
        pause & exit /b 1
    )
)

:: Встановити пакети з локальної папки packages\
if not exist "%PACKAGES%\" (
    echo   ПОМИЛКА: папку packages\ не знайдено.
    echo   Запусти download_packages.py на машинi з iнтернетом спочатку.
    pause & exit /b 1
)
echo   Встановлення пакетiв...
"%VENV%\Scripts\pip" install --no-index --find-links="%PACKAGES%" -r "%ROOT%requirements.txt"
if %errorlevel% neq 0 (
    echo   ПОМИЛКА при встановленнi пакетiв.
    echo   Можливо пакети у packages\ не вiдповiдають версiї Python.
    echo   Запусти download_packages.py на машинi з такою ж версiєю Python.
    pause & exit /b 1
)

:: ═══════════════════════════════════════════════════════════════════════════
echo.
echo ============================================
echo   Встановлення завершено!
echo.
echo   Наступнi кроки:
echo     1. python calibrate.py   -- калiбрування
echo     2. python automation.py  -- запуск
echo ============================================
echo.
pause
endlocal
