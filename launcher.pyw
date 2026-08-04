import os
import subprocess
import sys
import time
import webbrowser
import urllib.request

URL = "http://localhost:9876"

def est_deja_lance():
    try:
        urllib.request.urlopen(URL, timeout=1)
        return True
    except Exception:
        return False

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
    # 1. On tue l'ancienne version si elle tourne (permet d'appliquer les mises à jour)
    kill_existing_instances()
    time.sleep(0.5)

    # 2. On lance app.py en arrière-plan via pythonw de manière totalement indépendante
    pythonw = sys.executable.replace("python.exe", "pythonw.exe")
    script_app = os.path.join(os.path.dirname(__file__), "app.py")
    
    subprocess.Popen([pythonw, script_app], cwd=os.path.dirname(__file__))

    # 3. On attend quelques secondes que le serveur se lance, puis on ouvre le navigateur
    time.sleep(1.0)
    webbrowser.open(URL)