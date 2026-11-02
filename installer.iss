#define MyVer "1.0.0"
[Setup]
AppId={{9A67CFBB-5E39-408C-A13F-677448FA2798}
AppName=EX STORAGE LAB
AppVersion={#MyVer}
AppVerName=EX STORAGE LAB {#MyVer}
AppPublisher=EX Inc.
AppPublisherURL=https://github.com/Teobokki/ex-storage-lab
AppCopyright=©2026 EX Inc./HYPERION DIGITAL ©2026
VersionInfoVersion={#MyVer}.0
VersionInfoCompany=EX Inc.
VersionInfoCopyright=©2026 EX Inc./HYPERION DIGITAL ©2026
VersionInfoProductName=EX STORAGE LAB
VersionInfoDescription=EX STORAGE LAB Setup
DefaultDirName={localappdata}\Programs\EX STORAGE LAB
DefaultGroupName=EX STORAGE LAB
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=dist
OutputBaseFilename=EX.STORAGE.LAB.Setup.{#MyVer}
SetupIconFile=assets\logo.ico
UninstallDisplayIcon={app}\EX STORAGE LAB.exe
UninstallDisplayName=EX STORAGE LAB
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[InstallDelete]
Type: filesandordirs; Name: "{app}\_internal"

[Files]
Source: "dist\EX STORAGE LAB\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\EX STORAGE LAB"; Filename: "{app}\EX STORAGE LAB.exe"; IconFilename: "{app}\EX STORAGE LAB.exe"
Name: "{group}\Uninstall EX STORAGE LAB"; Filename: "{uninstallexe}"
Name: "{userdesktop}\EX STORAGE LAB"; Filename: "{app}\EX STORAGE LAB.exe"; IconFilename: "{app}\EX STORAGE LAB.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\EX STORAGE LAB.exe"; Description: "Launch EX STORAGE LAB now"; Flags: nowait postinstall skipifsilent
