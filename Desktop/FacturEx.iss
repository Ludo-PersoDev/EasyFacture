; Script d'installation Inno Setup (EasyFacture)
; -------------------------------------------------------------------------------

#define MyAppName "EasyFacture"
#define MyAppVersion "2.0.5"
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
PrivilegesRequired=admin
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

; Installateur Python embarqué (copié temporairement puis supprimé)
Source: "installer\python-3.14.7-amd64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "pythonw.exe"; Parameters: "{app}\{#MyAppMainScript}"; WorkingDir: "{app}"; IconFilename: "{app}\assets\logo.ico"
Name: "{group}\Désinstaller {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "pythonw.exe"; Parameters: "{app}\{#MyAppMainScript}"; WorkingDir: "{app}"; IconFilename: "{app}\assets\logo.ico"; Tasks: desktopicon

[Run]
; 1. Installation silencieuse de Python (pour tous les utilisateurs, ajout au PATH, avec PIP)
Filename: "{tmp}\python-3.14.7-amd64.exe"; Parameters: "/quiet InstallAllUsers=1 PrependPath=1 Include_pip=1"; StatusMsg: "Installation de l'environnement Python en cours..."; Flags: waituntilterminated

; 2. Mise à jour de pip et installation des dépendances requises
Filename: "python"; Parameters: "-m pip install --upgrade pip"; Flags: runminimized waituntilterminated
Filename: "python"; Parameters: "-m pip install --user nicegui reportlab google-auth google-auth-oauthlib google-api-python-client pywebview orjson requests supabase"; Flags: runminimized waituntilterminated

; 3. Lancement de l'application à la fin de l'installation
Filename: "pythonw.exe"; Parameters: "{app}\{#MyAppMainScript}"; WorkingDir: "{app}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent