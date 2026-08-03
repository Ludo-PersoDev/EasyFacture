; Script d'installation Inno Setup (Mode Source / Python direct avec launcher)
; -------------------------------------------------------------------------------

#define MyAppName "EasyFacture"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "LuA"
#define MyAppMainScript "launcher.pyw"

[Setup]
AppId={{7B8D9F2C-4A1E-4E5B-9F12-8C3D2E1F0A9B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
; Répertoire technique d'installation en interne
DefaultDirName=C:\FacturEx
; Nom du dossier dans le Menu Démarrer pour l'utilisateur
DefaultGroupName=EasyFacture
DisableDirPage=yes
AllowNoIcons=yes
Compression=lzma
SolidCompression=yes
OutputDir=userdocs:InnoSetup Output
OutputBaseFilename=Setup_EasyFacture_v1.0.0
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Copie de tous les fichiers source Python de l'application (y compris launcher.pyw) dans C:\FacturEx
Source: "*.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "*.pyw"; DestDir: "{app}"; Flags: ignoreversion

; Dossier des ressources (logos, images, etc.)
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs

; Fichiers de configuration optionnels (credentials Google API, base de données si existante)
Source: "credentials.json"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "FactureX.db"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
; Raccourci dans le Menu Démarrer (Exécute pythonw.exe avec launcher.pyw pour masquer la console)
Name: "{group}\{#MyAppName}"; Filename: "pythonw.exe"; Parameters: "{app}\{#MyAppMainScript}"; WorkingDir: "{app}"; IconFilename: "{app}\assets\logo.ico"
Name: "{group}\Désinstaller {#MyAppName}"; Filename: "{uninstallexe}"

; Raccourci sur le Bureau
Name: "{autodesktop}\{#MyAppName}"; Filename: "pythonw.exe"; Parameters: "{app}\{#MyAppMainScript}"; WorkingDir: "{app}"; IconFilename: "{app}\assets\logo.ico"; Tasks: desktopicon

[Run]
; 1. Installation automatique des dépendances requises via pip
Filename: "pip"; Parameters: "install nicegui reportlab google-auth google-auth-oauthlib google-api-python-client"; Flags: runminimized waituntilterminated

; 2. Lancer l'application automatiquement à la fin de l'installation via pythonw
Filename: "pythonw.exe"; Parameters: "{app}\{#MyAppMainScript}"; WorkingDir: "{app}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent