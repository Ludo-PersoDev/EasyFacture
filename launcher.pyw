import os
import subprocess
import sys
import time
import webbrowser

URL = "http://localhost:9876"

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

    # 3. Ouverture immédiate de la page de chargement locale dans le navigateur (en réutilisant l'onglet si possible)
    loading_path = os.path.abspath(os.path.join(script_dir, "loading.html"))
    
    time.sleep(0.5)
    if os.path.exists(loading_path):
        webbrowser.open(f"file:///{loading_path.replace(os.sep, '/')}", new=0)
    else:
        webbrowser.open(URL, new=0)