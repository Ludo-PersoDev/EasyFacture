import os
import subprocess
import sys
import webbrowser
import urllib.request
import time

URL = "http://localhost:9876"

def kill_existing_instances():
    """Tue les instances précédentes pour forcer le rechargement du code mis à jour."""
    current_pid = os.getpid()
    try:
        output = subprocess.check_output(
            'wmic process where "name=\'pythonw.exe\'" get ProcessId,CommandLine',
            shell=True,
        ).decode(errors='ignore')
        for line in output.splitlines():
            if "app.py" in line or "launcher.pyw" in line:
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
    # 1. On tue les éventuels vieux serveurs zombies/lancés avant la mise à jour
    kill_existing_instances()
    
    # Petite pause pour laisser Windows libérer le port proprement
    time.sleep(0.5)

    # 2. On importe et lance l'application fraîchement mise à jour
    import app

    # Ouvre le navigateur un petit instant après le lancement
    webbrowser.open(URL)

    # 3. Point d'entrée de l'application (exécute NiceGUI et bloque le thread proprement)
    # Assure-toi que ton app.py appelle ui.run(port=9876, reload=False) dedans
    if hasattr(app, "main"):
        app.main()