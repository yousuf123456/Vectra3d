; Inno Setup script for Vectra3D's installer (G6.1b).
;
; Build the app first (see vectra3d.spec), then:
;   "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" packaging\vectra3d.iss
; Output: dist\Vectra3D-0.1.0-setup.exe
;
; Deliberate choices:
; - Per-user install, no administrator rights: students on lab or university
;   laptops usually cannot approve an admin prompt. The default folder,
;   {autopf}, is then the user's own %LOCALAPPDATA%\Programs.
; - The folder can still be changed on the "Select Destination" page.
; - AppId must never change: Windows uses it to recognise an upgrade and to
;   find the uninstaller.
; - The version must match pyproject.toml; tests/test_readme_note.py checks.

#define AppName "Vectra3D"
#define AppVersion "0.1.0"
#define AppExe "Vectra3D.exe"
#define ReadMe "Read me first.txt"

[Setup]
AppId={{C1A97CC0-F4A8-4D8D-9013-5436A3728469}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppName}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename={#AppName}-{#AppVersion}-setup
SetupIconFile=..\assets\icons\vectra3d.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
; The whole one-folder build: the .exe needs its _internal folder beside it.
Source: "..\dist\{#AppName}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autoprograms}\{#AppName} - read me first"; Filename: "{app}\{#ReadMe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#ReadMe}"; Description: "Open ""Read me first"""; Flags: postinstall shellexec skipifsilent unchecked
Filename: "{app}\{#AppExe}"; Description: "Launch {#AppName}"; Flags: postinstall nowait skipifsilent
