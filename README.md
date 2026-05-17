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
4. Додай Tesseract до PATH — відкрий **PowerShell від імені адміністратора** та виконай:
   ```powershell
   [Environment]::SetEnvironmentVariable("Path", [Environment]::GetEnvironmentVariable("Path","Machine") + ";$env:ProgramFiles\Tesseract-OCR", "Machine")
   ```
   Після цього **закрий і відкрий PowerShell/CMD заново**.

   > **Якщо без прав адміністратора** — виконай у звичайному PowerShell (додасть у PATH поточного користувача):
   > ```powershell
   > [Environment]::SetEnvironmentVariable("Path", [Environment]::GetEnvironmentVariable("Path","User") + ";$env:ProgramFiles\Tesseract-OCR", "User")
   > ```

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

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install pygetwindow
```

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

## Структура проекту

```
automation.py        — головний скрипт
calibrate.py         — одноразове калібрування координат
config.json          — збережені координати та налаштування
requirements.txt     — залежності Python
utils/
  excel_reader.py    — читання/запис у Excel/Numbers
  sheets_handler.py  — взаємодія з Google Sheets
  window_manager.py  — перемикання вікон
```
