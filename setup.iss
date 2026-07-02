#define MyAppName      "Screen Automation"
#define MyAppVersion   "1.0"
#define MyDistDir      "dist"

[Setup]
AppId={{B7C4D2E1-93FA-4A18-BC50-D3F1A62E8074}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
; Встановлення без прав адмiнiстратора, в папку користувача
PrivilegesRequired=lowest
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
; Вихiдний iнсталятор
OutputDir=installer_output
OutputBaseFilename=ScreenAutomation_Setup
SetupIconFile=img\icon.ico
; Стиснення
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; Архiтектура -- 64-бiт
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "ukrainian"; MessagesFile: "compiler:Languages\Ukrainian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; automation.exe + всi залежностi (Python, OpenCV, Tesseract, ...)
Source: "{#MyDistDir}\automation\*"; DestDir: "{app}\automation"; \
    Flags: recursesubdirs createallsubdirs ignoreversion

; calibrate.exe + залежностi
Source: "{#MyDistDir}\calibrate\*"; DestDir: "{app}\calibrate"; \
    Flags: recursesubdirs createallsubdirs ignoreversion

; Стартовий файл даних (тiльки якщо ще немає -- не перезаписувати дані)
Source: "big_list.csv"; DestDir: "{app}"; Flags: onlyifdoesntexist

[Icons]
; Робочий стiл
Name: "{userdesktop}\Automation";  Filename: "{app}\automation\automation.exe"; \
    WorkingDir: "{app}"; IconFilename: "{app}\automation\automation.exe"; \
    Comment: "Запустити автоматизацiю"
Name: "{userdesktop}\Calibrate";   Filename: "{app}\calibrate\calibrate.exe"; \
    WorkingDir: "{app}"; IconFilename: "{app}\calibrate\calibrate.exe"; \
    Comment: "Калiбрування (запускати один раз)"

; Меню Пуск
Name: "{group}\Automation";        Filename: "{app}\automation\automation.exe"; \
    WorkingDir: "{app}"
Name: "{group}\Calibrate";         Filename: "{app}\calibrate\calibrate.exe"; \
    WorkingDir: "{app}"
Name: "{group}\Видалити";          Filename: "{uninstallexe}"

[Run]
; Запропонувати запустити калiбрування одразу пiсля встановлення
Filename: "{app}\calibrate\calibrate.exe"; \
    Description: "Запустити калiбрування зараз"; \
    WorkingDir: "{app}"; \
    Flags: postinstall nowait skipifsilent

[UninstallDelete]
; Видалити config.json та логи при деiнсталяцiї
Type: files; Name: "{app}\config.json"
Type: files; Name: "{app}\results_log.txt"
Type: files; Name: "{app}\debug_*.png"
