; Inno Setup Script para AICommandBridge
; Compile this script with Inno Setup Compiler
; Download: https://jrsoftware.org/isinfo.php

#define MyAppName "AI Command Bridge"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "AI Command Auto Executor"
#define MyAppURL "https://github.com/alvesleiteevaldo-crypto/ai-command-auto-executor"
#define MyAppExeName "AICommandBridge.exe"
#define MyAppAssocName MyAppName + " Command File"
#define MyAppAssocExt ".aicmd"
#define MyAppAssocProgID "AICommandBridge.1"

[Setup]
; NOTE: The value of AppId uniquely identifies this application. Do not use the same AppId value in installers for other applications.
AppId={{7F5E9B5E-8C3D-4F7E-9B5E-8C3D4F7E9B5E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName="{pf}\{#MyAppName}"
DefaultGroupName={#MyAppName}
LicenseFile=LICENSE.txt
OutputDir=dist\installer
OutputBaseFilename=AICommandBridge-Setup-1.0.0
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UsedUserModeInstaller=no
PrivilegesRequired=admin
ShowLanguageDialog=auto
LanguageDetectionMethod=uilanguage
InfoBeforeFile=INSTALL_INFO.txt
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "portuguese"; MessagesFile: "compiler:Languages\Portuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIconTask}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "autostart"; Description: "Iniciar automaticamente na senha de boot (usuario local)"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "USAGE.txt"; DestDir: "{app}"; Flags: ignoreversion isreadme

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon
Name: "{commonstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Registry]
Root: "HKCU"; Subkey: "Software\{#MyAppName}"; Flags: uninsdeletekeyifempty
Root: "HKCU"; Subkey: "Software\{#MyAppName}\Path"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletevalue

[UninstallDelete]
Type: filesandordirs; Name: "{app}\*.log"
Type: filesandordirs; Name: "{app}\__pycache__"

[Code]
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    MsgBox('AI Command Bridge foi instalado com sucesso!' + #13#13 +
            'Abra a aplicacao e configure os comandos permitidos em config.json.' + #13#13 +
            'Por padrao, o servidor roda em http://127.0.0.1:8765',
            mbInformation, MB_OK);
  end;
end;
