; Script d'installation Inno Setup (Propre - Sans BDD personnelle)
; -------------------------------------------------------------------------------

#define MyAppName "EasyFacture"
#define MyAppVersion "1.5"
#define MyAppPublisher "LuA"
#define MyAppMainScript "launcher.pyw"

[Setup]
AppId={{7B8D9F2C-4A1E-4E5B-9F12-8C3D2E1F0A9B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName=C:\FacturEx
DefaultGroupName=EasyFacture
DisableDirPage=no
AllowNoIcons=yes
Compression=lzma
SolidCompression=yes
OutputDir=userdocs:InnoSetup Output
OutputBaseFilename=Setup_EasyFacture_v{#MyAppVersion}
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Fichiers sources Python & version
Source: "*.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "*.pyw"; DestDir: "{app}"; Flags: ignoreversion

; Fichiers HTML de chargement et de mise à jour
Source: "loading.html"; DestDir: "{app}"; Flags: ignoreversion
Source: "updating.html"; DestDir: "{app}"; Flags: ignoreversion

; Dossier des ressources (logos, icônes)
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

; Fichier credentials optionnel
Source: "credentials.json"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "pythonw.exe"; Parameters: "{app}\{#MyAppMainScript}"; WorkingDir: "{app}"; IconFilename: "{app}\assets\logo.ico"
Name: "{group}\Désinstaller {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "pythonw.exe"; Parameters: "{app}\{#MyAppMainScript}"; WorkingDir: "{app}"; IconFilename: "{app}\assets\logo.ico"; Tasks: desktopicon

[Run]
Filename: "python"; Parameters: "-m pip install --user nicegui reportlab google-auth google-auth-oauthlib google-api-python-client"; Flags: runminimized waituntilterminated
Filename: "pythonw.exe"; Parameters: "{app}\{#MyAppMainScript}"; WorkingDir: "{app}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent