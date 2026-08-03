import os
import subprocess
import sys
import urllib.request

URL = "http://localhost:9876"


def est_deja_lance():
  try:
    urllib.request.urlopen(URL, timeout=1)
    return True
  except Exception:
    return False


if __name__ == "__main__":
  # Si l'application ne tourne pas encore, on la lance en arrière-plan
  if not est_deja_lance():
    pythonw = sys.executable.replace("python.exe", "pythonw.exe")
    script_app = os.path.join(os.path.dirname(__file__), "app.py")
    subprocess.Popen([pythonw, script_app], cwd=os.path.dirname(__file__))

  # Dans tous les cas, on ouvre le navigateur sur l'application
  import webbrowser

  webbrowser.open(URL)