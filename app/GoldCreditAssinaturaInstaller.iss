#define MyAppName "Gold Credit - Assinatura Digital"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Gold Credit"
#define MyAppExeName "GoldCreditAssinatura.exe"
#define MyAppId "GoldCreditAssinatura"

[Setup]
AppId={{8B1C16BE-0E9F-4700-B11A-7C70A7BE6A92}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Gold Credit\Assinatura Digital
DefaultGroupName=Gold Credit
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=installer
OutputBaseFilename=GoldCreditAssinaturaSetup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na area de trabalho"; GroupDescription: "Atalhos:"
Name: "autostart"; Description: "Iniciar com o Windows"; GroupDescription: "Inicializacao:"

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "{#MyAppId}"; ValueData: """{app}\{#MyAppExeName}"""; \
    Flags: uninsdeletevalue; Tasks: autostart

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Executar o assinador agora"; \
    Flags: nowait postinstall skipifsilent unchecked

[UninstallDelete]
Type: files; Name: "{app}\log.txt"

[Code]
function InitializeSetup(): Boolean;
begin
  if not FileExists(ExpandConstant('{#SourcePath}\dist\{#MyAppExeName}')) then
  begin
    MsgBox(
      'Nao foi encontrado o executavel em "dist\{#MyAppExeName}".' + #13#10#13#10 +
      'Gere primeiro o executavel do assinador antes de criar o instalador.',
      mbCriticalError,
      MB_OK
    );
    Result := False;
    exit;
  end;

  Result := True;
end;
