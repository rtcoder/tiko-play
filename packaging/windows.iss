#ifndef AppVersion
  #error AppVersion must be supplied from VERSION by the build script
#endif
[Setup]
AppId={{163C1D39-E804-433C-B0DB-5E43F8366D09}
AppName=TikoPlay
AppVersion={#AppVersion}
WizardStyle=modern
ArchitecturesAllowed=x64compatible
DefaultDirName={localappdata}\Programs\TikoPlay
DefaultGroupName=TikoPlay
PrivilegesRequired=lowest
UsePreviousAppDir=yes
UsePreviousTasks=yes
DisableProgramGroupPage=yes
OutputDir=..\dist\installer
OutputBaseFilename=TikoPlay-{#AppVersion}-windows-x64-setup
SetupIconFile=..\tiko_play.ico
UninstallDisplayIcon={app}\TikoPlay.exe
Compression=lzma2
SolidCompression=yes
CloseApplications=yes
CloseApplicationsFilter=*.exe,*.dll,*.pyd
RestartApplications=no
[Languages]
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"; InfoBeforeFile: "installer-pl.txt"
Name: "english"; MessagesFile: "compiler:Default.isl"; InfoBeforeFile: "installer-en.txt"
[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
[Files]
Source: "..\dist\TikoPlay\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Icons]
Name: "{autodesktop}\TikoPlay"; Filename: "{app}\TikoPlay.exe"; WorkingDir: "{app}"; Tasks: desktopicon
Name: "{group}\TikoPlay"; Filename: "{app}\TikoPlay.exe"; WorkingDir: "{app}"
[Run]
Filename: "{app}\TikoPlay.exe"; Description: "{cm:LaunchProgram,TikoPlay}"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent unchecked
