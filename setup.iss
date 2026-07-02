#define MyAppName      "Screen Automation"
#define MyAppVersion   "1.0"
#define MyDistDir      "dist\screen_automation"

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
Name: "english";   MessagesFile: "compiler:Default.isl"

[Files]
; app.exe + automation.exe + calibrate.exe + спiльний _internal/
Source: "{#MyDistDir}\*"; DestDir: "{app}"; \
    Flags: recursesubdirs createallsubdirs ignoreversion

; Стартовий файл даних (не перезаписувати якщо вже є)
Source: "big_list.csv"; DestDir: "{app}"; Flags: onlyifdoesntexist

[Icons]
; Робочий стiл -- тiльки app.exe (головний GUI)
Name: "{userdesktop}\Screen Automation"; \
    Filename: "{app}\app.exe"; \
    WorkingDir: "{app}"; \
    Comment: "Запустити автоматизацiю"

; Меню Пуск
Name: "{group}\Screen Automation"; \
    Filename: "{app}\app.exe"; \
    WorkingDir: "{app}"
Name: "{group}\Видалити"; \
    Filename: "{uninstallexe}"

[Run]
; Запустити GUI пiсля встановлення
Filename: "{app}\app.exe"; \
    Description: "Запустити Screen Automation"; \
    WorkingDir: "{app}"; \
    Flags: postinstall nowait skipifsilent

[UninstallDelete]
Type: files; Name: "{app}\config.json"
Type: files; Name: "{app}\results_log.txt"
Type: files; Name: "{app}\debug_*.png"
