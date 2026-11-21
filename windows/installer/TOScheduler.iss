; Technical Officials Scheduler - Windows installer (Inno Setup 6).
; Built by .github/workflows/windows.yml:
;   iscc /DAppVersion=1.0.3 /DArch=x64 /DPublishDir=..\publish\x64 installer\TOScheduler.iss
; Installs for the current user without administrator rights, or for all users (the installer asks).
; Installs the Microsoft Edge WebView2 Runtime when the PC does not have it (it is part of Windows 11).

#ifndef AppVersion
  #define AppVersion "1.0.3"
#endif
#ifndef Arch
  #define Arch "x64"
#endif
#ifndef PublishDir
  #define PublishDir "..\publish\" + Arch
#endif
#define AppName "Technical Officials Scheduler"
#define AppExe "TOScheduler.exe"
#define WebView2Key "{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"

[Setup]
AppId={{6F83C922-52EB-47D1-93B8-04B07B329294}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=TriSport.me
AppPublisherURL=https://www.trisport.me/
AppSupportURL=https://www.trisport.me/support.html
AppUpdatesURL=https://github.com/bojansurbatovic-web/technical-officials-scheduler/releases
AppCopyright=MIT licence. Not affiliated with World Triathlon.
VersionInfoVersion={#AppVersion}
VersionInfoProductName={#AppName}
VersionInfoDescription={#AppName} installer
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
#if Arch == "arm64"
ArchitecturesAllowed=arm64
ArchitecturesInstallIn64BitMode=arm64
#else
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
#endif
MinVersion=10.0.17763
OutputDir=..\dist
OutputBaseFilename=TechnicalOfficialsScheduler-Setup-{#AppVersion}-{#Arch}
SetupIconFile=..\app.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
LicenseFile=..\..\LICENSE
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
ChangesAssociations=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#PublishDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "MicrosoftEdgeWebview2Setup.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall; Check: NeedsWebView2

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; Comment: "Plan the Technical Officials of triathlon events"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
; "Open with -> Technical Officials Scheduler" for plan files (.json); does not change the default app for .json
Root: HKA; Subkey: "Software\Classes\TOScheduler.Plan"; ValueType: string; ValueName: ""; ValueData: "Technical Officials plan"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\TOScheduler.Plan\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#AppExe},0"
Root: HKA; Subkey: "Software\Classes\TOScheduler.Plan\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""
Root: HKA; Subkey: "Software\Classes\.json\OpenWithProgids"; ValueType: string; ValueName: "TOScheduler.Plan"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}"; ValueType: string; ValueName: "FriendlyAppName"; ValueData: "{#AppName}"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\Applications\{#AppExe}\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#AppExe}"" ""%1"""

[Run]
Filename: "{tmp}\MicrosoftEdgeWebview2Setup.exe"; Parameters: "/silent /install"; StatusMsg: "Installing Microsoft Edge WebView2 Runtime..."; Check: NeedsWebView2; Flags: waituntilterminated
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[Code]
function HasVersion(Root: Integer; Key: String): Boolean;
var
  V: String;
begin
  Result := RegQueryStringValue(Root, Key, 'pv', V) and (V <> '') and (V <> '0.0.0.0');
end;

function NeedsWebView2(): Boolean;
begin
  Result := not (HasVersion(HKLM, 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{#WebView2Key}') or
                 HasVersion(HKLM, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{#WebView2Key}') or
                 HasVersion(HKCU, 'Software\Microsoft\EdgeUpdate\Clients\{#WebView2Key}'));
end;
