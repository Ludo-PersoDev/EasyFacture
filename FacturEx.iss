; Script d'installation Inno Setup (Propre - Sans BDD personnelle)
; -------------------------------------------------------------------------------

; Lecture dynamique de la version depuis version.py (ex: VERSION = "1.3")
#define MyAppVersion GetFileVersion("version.py")
#define MyAppName "EasyFacture"
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
; Copie uniquement des fichiers source Python de l'application
Source: "*.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "*.pyw"; DestDir: "{app}"; Flags: ignoreversion

; Fichier HTML de chargement local pour le launcher
Source: "loading.html"; DestDir: "{app}"; Flags: ignoreversion

; Dossier des ressources (logos, images, etc.) - Sécurisé avec createallsubdirs
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

; Fichier de configuration optionnel (credentials Google API s'il existe)
Source: "credentials.json"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
; Raccourci dans le Menu Démarrer
Name: "{group}\{#MyAppName}"; Filename: "pythonw.exe"; Parameters: "{app}\{#MyAppMainScript}"; WorkingDir: "{app}"; IconFilename: "{app}\assets\logo.ico"
Name: "{group}\Désinstaller {#MyAppName}"; Filename: "{uninstallexe}"

; Raccourci sur le Bureau
Name: "{autodesktop}\{#MyAppName}"; Filename: "pythonw.exe"; Parameters: "{app}\{#MyAppMainScript}"; WorkingDir: "{app}"; IconFilename: "{app}\assets\logo.ico"; Tasks: desktopicon

[Run]
; 1. Installation automatique de toutes les dépendances requises pour l'utilisateur courant
Filename: "python"; Parameters: "-m pip install --user nicegui reportlab google-auth google-auth-oauthlib google-api-python-client"; Flags: runminimized waituntilterminated

; 2. Lancer l'application automatiquement à la fin de l'installation via pythonw
Filename: "pythonw.exe"; Parameters: "{app}\{#MyAppMainScript}"; WorkingDir: "{app}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent