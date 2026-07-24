; FileSwift - Instalador Windows (Inno Setup)
;
; Instalação por usuário (sem exigir admin/UAC), em %LOCALAPPDATA%\Programs\FileSwift.
; Espera encontrar a pasta dist\FileSwift\ já gerada pelo PyInstaller
; (pyinstaller fileswift.spec) antes de compilar este script.

#define MyAppName "FileSwift"
#define MyAppVersion GetEnv("FILESWIFT_VERSION")
#if MyAppVersion == ""
  #define MyAppVersion "0.0.0"
#endif
#define MyAppPublisher "Bruno Fragoso"
#define MyAppExeName "FileSwift.exe"

[Setup]
AppId={{8F3E2C1A-9B4D-4E7F-8A2C-FILESWIFT001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=Output
OutputBaseFilename=FileSwiftSetup-{#MyAppVersion}
SetupIconFile=fileswift.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\FileSwift\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Não apaga dados do usuário (%LOCALAPPDATA%\FileSwift: banco, uploads, anexos) —
; só o que foi instalado pelo próprio instalador, em {app}.
Type: filesandordirs; Name: "{app}"
