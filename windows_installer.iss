[Setup]
AppName=MrFold Music
AppVersion=1.0
DefaultDirName={autopf}\MrFold Music
DefaultGroupName=MrFold Music
OutputDir=dist
OutputBaseFilename=MrFold_Music_Windows_Installer
Compression=lzma2
SolidCompression=yes
SetupIconFile=icon.ico

[Files]
Source: "dist\MrFold Music\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\MrFold Music"; Filename: "{app}\MrFold Music.exe"
Name: "{commondesktop}\MrFold Music"; Filename: "{app}\MrFold Music.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Run]
Filename: "{app}\MrFold Music.exe"; Description: "Launch MrFold Music"; Flags: nowait postinstall skipifsilent
