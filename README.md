# Screen Automation — ІПН пошук

Скрипт порівнює ІПН із таблиці Excel з Google Sheets у Chrome:
читає ІПН → шукає через Ctrl+F → відмічає галочку в Google Sheets → пише "Так"/"Ні" у Excel.

---

## Встановлення на Windows

### 1. Встановити Python

1. Завантаж з **https://www.python.org/downloads/**
2. Запусти інсталятор
3. ⚠️ Постав галочку **"Add Python to PATH"** перед натисканням Install

Перевір у CMD:
```
python --version
```

---

### 2. Встановити Tesseract OCR

1. Завантаж інсталятор з **https://github.com/UB-Mannheim/tesseract/wiki**
   (файл виглядає як `tesseract-ocr-w64-setup-5.x.x.exe`)
2. Під час встановлення додатково вибери мовні пакети: **Ukrainian** та **English**
3. Запам'ятай шлях встановлення (зазвичай `C:\Program Files\Tesseract-OCR`)
4. Додай Tesseract до PATH — виконай у CMD від імені адміністратора:
   ```
   setx PATH "%PATH%;%ProgramFiles%\Tesseract-OCR" /M
   ```
   Після цього **закрий і відкрий CMD заново**.

Перевір у CMD:
```
tesseract --version
```

---

### 3. Клонувати репозиторій

```
git clone https://github.com/Karkunow/screen-automation.git
cd screen-automation
```

Або завантаж ZIP: **Code → Download ZIP**, розпакуй.

---

### 4. Створити віртуальне середовище та встановити залежності

Виконуй **у CMD** (не PowerShell):

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install pygetwindow
```

> **Якщо використовуєш PowerShell і бачиш помилку "running scripts is disabled"** — виконай один раз:
> ```
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```
> Після цього `.venv\Scripts\activate` запрацює.

---

### 5. Підготовка

- Відкрий **Excel** з файлом `small_list.csv` (колонки: A=ПІБ, B=ІПН, C=Результат)
- Відкрий **Chrome** з Google Sheets (big_list) як активна вкладка
- Переконайся що в Google Sheets колонки: A=ПІБ, B=ІПН, C=Знайдено (чекбокси)

---

### 6. Калібрування (один раз)

```
python calibrate.py
```

Скрипт запитає:
1. Навести мишу на першу клітинку ІПН у Excel (колонка B, рядок 2)
2. Кількість рядків з даними
3. Верхній лівий та правий нижній кут рядка пошуку Chrome (Ctrl+F)
4. Частину заголовку вікна Chrome (напр. `big_list`)

---

### 7. Запуск

```
python automation.py
```

⚠️ **Аварійна зупинка**: перемісти мишу у верхній лівий кут екрану.

---

---

## Офлайн-встановлення на Windows (без інтернету)

Якщо на цільовій машині немає інтернету — скористайся `install.bat`.

**Крок 1 — на машині з інтернетом:**

```
python download_packages.py
```

Скрипт завантажить Python-інсталятор, Tesseract, tessdata та всі pip-пакети
у папки `installers\` та `packages\`.

**Крок 2 — скопіювати весь проект** на цільову машину (флешка / мережа).

**Крок 3 — на цільовій машині:**

Правий клік на `install.bat` → **"Запуск від імені адміністратора"** → далі за інструкціями.

Скрипт сам встановить Python, Tesseract, мовні пакети та створить `.venv` з залежностями.

---

## Збірка Windows EXE-інсталятора

Дозволяє зробити єдиний `ScreenAutomation_Setup.exe` — без Python, без pip, без нічого.
Користувач просто запускає інсталятор і отримує ярлики на робочому столі.

**Потрібно встановити один раз (на машині розробника):**

- [PyInstaller](https://pyinstaller.org/) — встановлюється автоматично через `build.bat`
- [Inno Setup 6](https://jrsoftware.org/isdl.php) — безкоштовний, встановити вручну

**Зібрати:**

```
build.bat
```

Скрипт:
1. Встановить PyInstaller у `.venv` якщо відсутній
2. Зберe `automation.exe` (з вбудованим Tesseract)
3. Зберe `calibrate.exe`
4. Скомпілює `installer_output\ScreenAutomation_Setup.exe` через Inno Setup

**Що отримає користувач після встановлення:**

```
%LocalAppData%\Screen Automation\
  automation\automation.exe    ← ярлик на робочому столі
  calibrate\calibrate.exe      ← ярлик на робочому столі
  big_list.csv
  config.json                  ← створюється calibrate.exe при першому запуску
```

Розмір інсталятора: ~100–150 МБ.
Для деінсталяції — стандартно через "Програми та компоненти" Windows.

---

## Структура проекту

```
automation.py          — головний скрипт
calibrate.py           — одноразове калібрування координат
config.json            — збережені координати та налаштування
requirements.txt       — залежності Python
install.bat            — офлайн-встановлення (Python + Tesseract + venv)
build.bat              — збірка EXE-інсталятора через PyInstaller + Inno Setup
automation.spec        — PyInstaller конфіг для automation.exe
calibrate.spec         — PyInstaller конфіг для calibrate.exe
setup.iss              — Inno Setup скрипт для фінального інсталятора
utils/
  excel_reader.py      — читання/запис у Excel/Numbers
  sheets_handler.py    — взаємодія з Google Sheets
  window_manager.py    — перемикання вікон
  tesseract_path.py    — налаштування шляху до Tesseract у frozen exe
installers/            — офлайн-інсталятори (заповнюється download_packages.py)
packages/              — pip-пакети для офлайн-встановлення
```
