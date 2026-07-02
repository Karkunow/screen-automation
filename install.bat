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
set "IS_ADMIN=0"
set "PY="
set "TESS_PATH="

:: ── Перевірка прав адміністратора ─────────────────────────────────────────
net session >nul 2>&1
if %errorlevel% equ 0 set "IS_ADMIN=1"
if "!IS_ADMIN!"=="0" (
    echo  [!] Скрипт запущено БЕЗ прав адміністратора.
    echo      Tesseract встановлюється у %ProgramFiles% i потребує admin.
    echo      Рекомендується: правий клiк на install.bat -^> "Запуск вiд iменi адмiнiстратора"
    echo.
    rem choice може вiдсутнiй на деяких мiнiмальних Windows - перевiряємо
    where choice >nul 2>&1
    if !errorlevel! equ 0 (
        choice /c YN /t 30 /d Y /m "Продовжити все одно? (Y=Так, N=Нi, авто-Y через 30 сек)"
        if !errorlevel! equ 2 exit /b 0
    ) else (
        echo      Натиснiть Enter щоб продовжити, або закрийте вiкно для скасування.
        pause >nul
    )
    echo.
)

:: ═══════════════════════════════════════════════════════════════════════════
:: [1/4] Python
:: ═══════════════════════════════════════════════════════════════════════════
echo [1/4] Перевiрка Python...
call :find_python
if not defined PY (
    echo   Python не знайдено. Шукаємо iнсталятор...
    call :install_python
    if not defined PY (
        echo   ПОМИЛКА: Python не вдалося встановити або знайти.
        echo   Закрий CMD, вiдкрий знову i запусти install.bat ще раз.
        pause & exit /b 1
    )
)
for /f "tokens=*" %%v in ('"!PY!" --version 2>&1') do echo   %%v  [!PY!]

:: ═══════════════════════════════════════════════════════════════════════════
:: [2/4] Tesseract OCR
:: ═══════════════════════════════════════════════════════════════════════════
echo.
echo [2/4] Перевiрка Tesseract...
call :find_tesseract
if not defined TESS_PATH (
    echo   Tesseract не знайдено. Шукаємо iнсталятор...
    call :install_tesseract
    call :find_tesseract
)
if defined TESS_PATH (
    echo   Tesseract знайдено: !TESS_PATH!
    rem Додати до PATH поточної сесiї якщо ще немає
    echo !PATH! | findstr /i "Tesseract-OCR" >nul 2>&1
    if !errorlevel! neq 0 set "PATH=!PATH!;!TESS_PATH!"
) else (
    echo   [!] Tesseract не знайдено -- OCR може не працювати. Продовжуємо...
)

:: ═══════════════════════════════════════════════════════════════════════════
:: [3/4] Мовнi пакети Tesseract
:: ═══════════════════════════════════════════════════════════════════════════
echo.
echo [3/4] Мовнi пакети Tesseract...
if defined TESS_PATH (
    if exist "%INSTALLERS%\tessdata\" (
        set "TESS_DATA=!TESS_PATH!\tessdata"
        if exist "!TESS_DATA!\" (
            copy /y "%INSTALLERS%\tessdata\*.traineddata" "!TESS_DATA!\" >nul 2>&1
            if !errorlevel! equ 0 (
                echo   Скопiйовано мовнi пакети до: !TESS_DATA!
            ) else (
                echo   [!] Не вдалося скопiювати мовнi пакети -- можливо потрiбнi права admin.
            )
        ) else (
            echo   [!] Папку tessdata Tesseract не знайдено: !TESS_DATA!
        )
    ) else (
        echo   installers\tessdata не знайдено -- пропускаємо.
    )
) else (
    echo   Tesseract не встановлено -- пропускаємо.
)

:: ═══════════════════════════════════════════════════════════════════════════
:: [4/4] Python venv + пакети
:: ═══════════════════════════════════════════════════════════════════════════
echo.
echo [4/4] Python venv та залежностi...

if not exist "%PACKAGES%\" (
    echo   ПОМИЛКА: папку packages\ не знайдено.
    echo   Запусти download_packages.py на машинi з iнтернетом спочатку.
    pause & exit /b 1
)

:: Перевiрити чи venv робочий; якщо нi -- видалити i створити знову
if exist "%VENV%\Scripts\python.exe" (
    "%VENV%\Scripts\python.exe" --version >nul 2>&1
    if !errorlevel! neq 0 (
        echo   Виявлено пошкоджений venv -- вiдновлення...
        rmdir /s /q "%VENV%" >nul 2>&1
    ) else (
        echo   Iснуючий .venv знайдено i перевiрено.
    )
)

if not exist "%VENV%\Scripts\python.exe" (
    echo   Створення .venv...
    "!PY!" -m venv "%VENV%"
    if !errorlevel! neq 0 (
        echo   ПОМИЛКА при створеннi venv.
        pause & exit /b 1
    )
    echo   .venv створено.
)

echo   Встановлення пакетiв...
"%VENV%\Scripts\python.exe" -m pip install --no-index --find-links="%PACKAGES%" -r "%ROOT%requirements.txt"
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
goto :eof


:: ═══════════════════════════════════════════════════════════════════════════
:: :find_python  -- шукає Python i встановлює змiнну PY
:: Порядок: py launcher -> python (не Store stub) -> python3 -> вiдомi шляхи
:: ═══════════════════════════════════════════════════════════════════════════
:find_python
set "PY="

:: 1. py.exe launcher -- найнадiйнiший спосiб на Windows 10/11
py --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%v in ('py -c "import sys; print(sys.executable)" 2^>nul') do set "PY=%%v"
    if defined PY goto :eof
    set "PY=py"
    goto :eof
)

:: 2. python -- але не Windows Store stub (шлях мiстить "WindowsApps")
python --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%v in ('python -c "import sys; print(sys.executable)" 2^>nul') do (
        set "_exe=%%v"
        echo !_exe! | findstr /i "WindowsApps" >nul 2>&1
        if !errorlevel! neq 0 (
            set "PY=!_exe!"
            goto :eof
        )
    )
)

:: 3. python3
python3 --version >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%v in ('python3 -c "import sys; print(sys.executable)" 2^>nul') do set "PY=%%v"
    if defined PY goto :eof
)

:: 4. Вiдомi шляхи встановлення (per-user i system)
for %%p in (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python39\python.exe"
    "%ProgramFiles%\Python313\python.exe"
    "%ProgramFiles%\Python312\python.exe"
    "%ProgramFiles%\Python311\python.exe"
    "%ProgramFiles%\Python310\python.exe"
    "C:\Python313\python.exe"
    "C:\Python312\python.exe"
    "C:\Python311\python.exe"
    "C:\Python310\python.exe"
) do (
    if not defined PY if exist %%p set "PY=%%~p"
)
goto :eof


:: ═══════════════════════════════════════════════════════════════════════════
:: :install_python  -- запускає iнсталятор з папки installers\
:: ═══════════════════════════════════════════════════════════════════════════
:install_python
set "PY_EXE="
for %%f in ("%INSTALLERS%\python-*.exe") do set "PY_EXE=%%f"
if not defined PY_EXE (
    echo   ПОМИЛКА: не знайдено python-*.exe у папцi installers\
    echo   Запусти download_packages.py на машинi з iнтернетом спочатку.
    goto :eof
)
echo   Встановлення: %PY_EXE%
"%PY_EXE%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
if %errorlevel% neq 0 (
    echo   ПОМИЛКА пiд час встановлення Python (код: %errorlevel%).
    goto :eof
)
echo   Python встановлено.
:: Оновити PATH поточної сесiї з реєстру користувача через PowerShell
for /f "usebackq tokens=*" %%v in (`powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('PATH','User')" 2^>nul`) do (
    set "_upath=%%v"
)
if defined _upath set "PATH=!_upath!;%PATH%"
:: Спробувати знайти Python ще раз
call :find_python
goto :eof


:: ═══════════════════════════════════════════════════════════════════════════
:: :find_tesseract  -- шукає Tesseract i встановлює змiнну TESS_PATH
:: Порядок: PATH -> реєстр (HKLM) -> вiдомi шляхи
:: ═══════════════════════════════════════════════════════════════════════════
:find_tesseract
set "TESS_PATH="

:: 1. Перевiрити PATH
where tesseract >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%p in ('where tesseract 2^>nul') do (
        if not defined TESS_PATH for %%d in ("%%~dpp.") do set "TESS_PATH=%%~fd"
    )
    if defined TESS_PATH goto :eof
)

:: 2. Реєстр -- 64-бiтний i 32-бiтний Tesseract
for /f "usebackq tokens=*" %%v in (`powershell -NoProfile -Command "(Get-ItemProperty 'HKLM:\SOFTWARE\Tesseract-OCR' -ErrorAction SilentlyContinue).InstallDir" 2^>nul`) do set "_tp=%%v"
if defined _tp if exist "!_tp!\tesseract.exe" ( set "TESS_PATH=!_tp!" & goto :eof )

for /f "usebackq tokens=*" %%v in (`powershell -NoProfile -Command "(Get-ItemProperty 'HKLM:\SOFTWARE\WOW6432Node\Tesseract-OCR' -ErrorAction SilentlyContinue).InstallDir" 2^>nul`) do set "_tp=%%v"
if defined _tp if exist "!_tp!\tesseract.exe" ( set "TESS_PATH=!_tp!" & goto :eof )

:: 3. Вiдомi шляхи
for %%p in (
    "%ProgramFiles%\Tesseract-OCR"
    "%ProgramFiles(x86)%\Tesseract-OCR"
    "C:\Tesseract-OCR"
    "C:\Program Files\Tesseract-OCR"
    "C:\Program Files (x86)\Tesseract-OCR"
) do (
    if not defined TESS_PATH if exist "%%~p\tesseract.exe" set "TESS_PATH=%%~p"
)
goto :eof


:: ═══════════════════════════════════════════════════════════════════════════
:: :install_tesseract  -- запускає iнсталятор з папки installers\
:: ═══════════════════════════════════════════════════════════════════════════
:install_tesseract
set "TESS_EXE="
for %%f in ("%INSTALLERS%\tesseract-*.exe") do set "TESS_EXE=%%f"
if not defined TESS_EXE (
    echo   ПОМИЛКА: не знайдено tesseract-*.exe у папцi installers\
    goto :eof
)
echo   Встановлення: %TESS_EXE%
"%TESS_EXE%" /S
if %errorlevel% neq 0 (
    echo   ПОМИЛКА пiд час встановлення Tesseract (код: %errorlevel%).
    goto :eof
)
echo   Tesseract встановлено.
:: Додати до Machine PATH якщо є права admin
if "!IS_ADMIN!"=="1" (
    powershell -NoProfile -Command "$p='%ProgramFiles%\Tesseract-OCR'; $cur=[Environment]::GetEnvironmentVariable('PATH','Machine'); if ($cur -notlike '*Tesseract-OCR*') { [Environment]::SetEnvironmentVariable('PATH', $cur+';'+$p, 'Machine') }" >nul 2>&1
    echo   Tesseract додано до системного PATH.
) else (
    rem Без admin -- додати до PATH користувача
    powershell -NoProfile -Command "$p='%ProgramFiles%\Tesseract-OCR'; $cur=[Environment]::GetEnvironmentVariable('PATH','User'); if ($cur -notlike '*Tesseract-OCR*') { [Environment]::SetEnvironmentVariable('PATH', $cur+';'+$p, 'User') }" >nul 2>&1
    echo   Tesseract додано до PATH користувача.
)
goto :eof
