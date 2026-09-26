#define MyAppName "AI Command Bridge"
#define MyAppVersion "2.0.0"
#define MyAppPublisher "AI Command Auto Executor"
#define MyAppURL "https://github.com/alvesleiteevaldo-crypto/ai-command-auto-executor"
#define MyAppExeName "AICommandBridge.exe"

[Setup]
AppId={{91B92767-30F8-43E6-949E-9AB68B111E30}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={localappdata}\Programs\AICommandBridge
DefaultGroupName={#MyAppName}
OutputDir=dist\installer
OutputBaseFilename=AICommandBridge-Setup-2.0.0
Compression=lzma2
SolidCompression=yes
ArchitecturesAllowed=x64compatible
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "portuguese"; MessagesFile: "compiler:Languages\Portuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; Flags: unchecked
Name: "autostart"; Description: "Iniciar automaticamente ao entrar no Windows"; Flags: unchecked

[Files]
Source: "dist\AICommandBridge.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "USAGE_V2.txt"; DestDir: "{app}"; Flags: ignoreversion isreadme

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir {#MyAppName}"; Flags: nowait postinstall skipifsilent
