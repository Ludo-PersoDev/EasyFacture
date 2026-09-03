; Script d'installation Inno Setup (EasyFacture)
; -------------------------------------------------------------------------------

#define MyAppName "EasyFacture"
#define MyAppVersion "2.0.4"
#define MyAppPublisher "LuA"
#define MyAppMainScript "launcher.pyw"

[Setup]
AppId={{7B8D9F2C-4A1E-4E5B-9F12-8C3D2E1F0A9B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName=C:\FacturEx\Desktop
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

; Dossier des ressources (logos, icônes)
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

; Fichier credentials optionnel pour Google Drive
Source: "credentials.json"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

; Fichier credentials optionnel pour Supabase
Source: "config.json"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "pythonw.exe"; Parameters: "{app}\{#MyAppMainScript}"; WorkingDir: "{app}"; IconFilename: "{app}\assets\logo.ico"
Name: "{group}\Désinstaller {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "pythonw.exe"; Parameters: "{app}\{#MyAppMainScript}"; WorkingDir: "{app}"; IconFilename: "{app}\assets\logo.ico"; Tasks: desktopicon

[Run]
; Installation automatique de toutes les dépendances Python requises (v1.9.2)
Filename: "python"; Parameters: "-m pip install --upgrade pip"; Flags: runminimized waituntilterminated
Filename: "python"; Parameters: "-m pip install --user nicegui reportlab google-auth google-auth-oauthlib google-api-python-client pywebview orjson requests supabase"; Flags: runminimized waituntilterminated
Filename: "pythonw.exe"; Parameters: "{app}\{#MyAppMainScript}"; WorkingDir: "{app}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent