import os
import subprocess
import sys
import time
import webbrowser
import urllib.request
import json
import tempfile
import version

URL = "http://localhost:9876"
CURRENT_VERSION = version.VERSION  # Récupéré dynamiquement depuis version.py
GITHUB_API_URL = "https://api.github.com/repos/Ludo-PersoDev/EasyFacture/releases/latest"

def verifier_et_telecharger_maj(force_notification=False):
    """Vérifie sur GitHub si une nouvelle version est disponible et l'installe."""
    try:
        req = urllib.request.Request(
            GITHUB_API_URL, 
            headers={'User-Agent': 'EasyFacture-Updater'}
        )
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode())
            latest_tag = data.get("tag_name", "").strip().lstrip('v')
            
            if not latest_tag:
                if force_notification:
                    from nicegui import ui
                    ui.notify("Impossible de récupérer la version en ligne.", type="warning")
                return

            if latest_tag > CURRENT_VERSION:
                exe_url = None
                for asset in data.get("assets", []):
                    if asset["name"].lower().endswith(".exe"):
                        exe_url = asset["browser_download_url"]
                        break
                
                if exe_url:
                    if force_notification:
                        from nicegui import ui
                        ui.notify(f"Mise à jour v{latest_tag} trouvée ! Téléchargement...", type="info")

                    temp_dir = tempfile.gettempdir()
                    installer_path = os.path.join(temp_dir, "Setup_EasyFacture_Update.exe")
                    
                    urllib.request.urlretrieve(exe_url, installer_path)
                    
                    if os.path.exists(installer_path):
                        subprocess.Popen([installer_path, '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART'])
                        sys.exit(0)
            else:
                if force_notification:
                    from nicegui import ui
                    ui.notify("Votre logiciel est déjà à jour !", type="positive")
    except Exception as e:
        if force_notification:
            from nicegui import ui
            ui.notify("Erreur lors de la vérification de la mise à jour.", type="negative")

def kill_existing_instances():
    """Tue proprement les anciennes instances de app.py."""
    current_pid = os.getpid()
    try:
        output = subprocess.check_output(
            'wmic process where "name=\'pythonw.exe\'" get ProcessId,CommandLine',
            shell=True,
        ).decode(errors="ignore")

        for line in output.splitlines():
            if "app.py" in line and "launcher.pyw" not in line:
                parts = line.strip().split()
                if parts:
                    try:
                        pid = int(parts[-1])
                        if pid != current_pid:
                            subprocess.run(f"taskkill /F /PID {pid}", shell=True, check=False)
                    except ValueError:
                        pass
    except Exception:
        pass

if __name__ == "__main__":
    # Si le launcher est appelé avec l'argument "--check-update", on force la vérification (utilisé depuis l'UI)
    if len(sys.argv) > 1 and sys.argv[1] == "--check-update":
        verifier_et_telecharger_maj(force_notification=True)
        sys.exit(0)

    # 0. Vérification silencieuse des mises à jour GitHub au démarrage
    verifier_et_telecharger_maj(force_notification=False)

    # 1. Nettoyage des anciennes instances
    kill_existing_instances()
    time.sleep(0.3)

    # 2. Lancement du serveur NiceGUI en arrière-plan
    script_dir = os.path.dirname(__file__)
    script_app = os.path.join(script_dir, "app.py")
    
    python_exe = sys.executable
    if "python.exe" in python_exe.lower():
        pythonw_candidate = python_exe.replace("python.exe", "pythonw.exe")
        if os.path.exists(pythonw_candidate):
            python_exe = pythonw_candidate

    subprocess.Popen([python_exe, script_app], cwd=script_dir)

    # 3. Ouverture immédiate de la page de chargement locale dans le navigateur
    loading_path = os.path.abspath(os.path.join(script_dir, "loading.html"))
    
    time.sleep(0.5)
    if os.path.exists(loading_path):
        webbrowser.open(f"file:///{loading_path.replace(os.sep, '/')}", new=0)
    else:
        webbrowser.open(URL, new=0)