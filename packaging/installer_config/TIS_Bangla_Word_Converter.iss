; Inno Setup 6 script — TIS (Bangla Word Converter)
; Build after PyInstaller has produced dist\TIS_Bangla_Word_Converter\ :
;   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" packaging\installer_config\TIS_Bangla_Word_Converter.iss
; Output: release\TIS_Bangla_Word_Converter_Setup.exe

#define AppName      "TIS (Bangla Word Converter)"
#define AppShortName "TIS Bangla Word Converter"
#define AppVersion   "1.5.0"
#define AppPublisher "Tariqul Islam (Sumon) - TIS Academy"
#define AppExe       "TIS_Bangla_Word_Converter.exe"
#define SrcDir       "..\..\dist\TIS_Bangla_Word_Converter"

[Setup]
AppId={{6F1C2B7A-4E0D-4C1B-9A55-7B3E2D9C1A01}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppComments=Smart Bengali Text & Document Conversion — Unicode to Bijoy
VersionInfoVersion={#AppVersion}.0
VersionInfoProductName={#AppName}
VersionInfoDescription={#AppName} Setup
DefaultDirName={autopf}\{#AppShortName}
DefaultGroupName={#AppShortName}
DisableProgramGroupPage=yes
LicenseFile=..\..\LICENSE
OutputDir=..\..\release
OutputBaseFilename=TIS_Bangla_Word_Converter_Setup
SetupIconFile=..\..\assets\icons\tis.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
WizardStyle=modern
WizardImageFile=wizard_large.bmp,wizard_large@2x.bmp
WizardSmallImageFile=wizard_small.bmp,wizard_small@2x.bmp
Compression=lzma2/max
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
CloseApplications=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SrcDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\LICENSE"; DestDir: "{app}"; DestName: "LICENSE.txt"; Flags: ignoreversion
Source: "..\..\README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme

[Icons]
Name: "{group}\{#AppShortName}"; Filename: "{app}\{#AppExe}"; IconFilename: "{app}\{#AppExe}"; Comment: "Unicode to Bijoy converter"
Name: "{group}\Uninstall {#AppShortName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppShortName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppShortName}}"; Flags: nowait postinstall skipifsilent

; User settings and history live in %APPDATA%\TIS Bangla Word Converter and are
; intentionally kept on uninstall (so a reinstall keeps the user's history).
