[Setup]
AppId={{163C1D39-E804-433C-B0DB-5E43F8366D09}
AppName=TikoPlay
AppVersion=2.0.0
DefaultDirName={localappdata}\Programs\TikoPlay
DefaultGroupName=TikoPlay
PrivilegesRequired=lowest
OutputDir=..\dist\installer
OutputBaseFilename=TikoPlay-2.0.0-test-setup
SetupIconFile=..\tiko_play.ico
UninstallDisplayIcon={app}\TikoPlay.exe
Compression=lzma2
SolidCompression=yes
CloseApplications=yes
[Files]
Source: "..\dist\TikoPlay\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{autodesktop}\TikoPlay"; Filename: "{app}\TikoPlay.exe"; WorkingDir: "{app}"
Name: "{group}\TikoPlay"; Filename: "{app}\TikoPlay.exe"; WorkingDir: "{app}"
[Run]
Filename: "{app}\TikoPlay.exe"; Description: "Uruchom TikoPlay"; Flags: nowait postinstall skipifsilent
