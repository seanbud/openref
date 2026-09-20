#ifndef MyAppVersion
  #define MyAppVersion "0.6.0"
#endif
#ifndef MyAppVersionInfo
  #define MyAppVersionInfo "0.6.0.0"
#endif

[Setup]
AppId={{A7CAFC1D-1B75-4E15-A1B3-93EB476208A7}
AppName=OpenRef
AppVersion={#MyAppVersion}
AppPublisher=OpenRef contributors
AppPublisherURL=https://github.com/seanbud/openref
AppSupportURL=https://github.com/seanbud/openref/issues
LicenseFile=..\..\LICENSE
DefaultDirName={autopf}\OpenRef
DefaultGroupName=OpenRef
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\..\dist\installer
OutputBaseFilename=OpenRef-Windows-Setup
SetupIconFile=..\..\beeref\assets\openref.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\OpenRef.exe
VersionInfoVersion={#MyAppVersionInfo}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "..\..\dist\OpenRef.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\LICENSE"; DestDir: "{app}"; DestName: "LICENSE.txt"; Flags: ignoreversion
Source: "..\..\NOTICE"; DestDir: "{app}"; DestName: "NOTICE.txt"; Flags: ignoreversion
Source: "..\..\SOURCE_CODE.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\CONTRIBUTORS.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\ASSET_PROVENANCE.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\build\legal\third-party\*"; DestDir: "{app}\THIRD_PARTY_LICENSES"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\..\build\legal\build-provenance.json"; DestDir: "{app}"; Flags: ignoreversion

[Registry]
; Register only the native board format. Legacy .bee files can still be
; imported/opened from OpenRef without taking over their existing association.
Root: HKCU; Subkey: "Software\Classes\.openref"; ValueType: string; ValueName: ""; ValueData: "OpenRef.Document"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\OpenRef.Document"; ValueType: string; ValueName: ""; ValueData: "OpenRef board"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\OpenRef.Document\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\OpenRef.exe,0"
Root: HKCU; Subkey: "Software\Classes\OpenRef.Document\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\OpenRef.exe"" ""%1"""

[Icons]
Name: "{autoprograms}\OpenRef"; Filename: "{app}\OpenRef.exe"
Name: "{autodesktop}\OpenRef"; Filename: "{app}\OpenRef.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\OpenRef.exe"; Description: "Launch OpenRef"; Flags: nowait postinstall skipifsilent
