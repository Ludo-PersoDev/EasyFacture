import os
import subprocess
import sys
import time
import urllib.request
import json
import tempfile
import webview
import version

URL = "http://localhost:9876"
CURRENT_VERSION = version.VERSION
GITHUB_API_URL = "https://api.github.com/repos/Ludo-PersoDev/EasyFacture/releases/latest"

def is_app_running():
    try:
        req = urllib.request.urlopen(URL, timeout=0.5)
        return req.getcode() == 200
    except Exception:
        return False

def executer_mise_a_jour(script_dir):
    updating_html = """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <title>Mise à jour d'EasyFacture</title>
        <style>
            body {
                margin: 0;
                padding: 0;
                background-color: #0f172a;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                color: #f8fafc;
                overflow: hidden !important;
            }
            .card {
                background: #1e293b;
                padding: 40px;
                border-radius: 16px;
                box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
                text-align: center;
                width: 420px;
                border: 1px solid #334155;
            }
            h2 {
                margin-top: 0;
                color: #ffffff;
                font-size: 22px;
            }
            p {
                color: #94a3b8;
                font-size: 14px;
                margin-bottom: 25px;
                line-height: 1.5;
            }
            .spinner {
                width: 50px;
                height: 50px;
                border: 4px solid rgba(255, 255, 255, 0.1);
                border-top: 4px solid #3b82f6;
                border-radius: 50%;
                animation: spin 1s linear infinite;
                margin: 0 auto 20px auto;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
    </head>
    <body>
        <div class="card">
            <div class="spinner"></div>
            <h2>Mise à jour requise 🚀</h2>
            <p>Une nouvelle version d'EasyFacture est disponible. Téléchargement et installation en cours en arrière-plan...</p>
        </div>
    </body>
    </html>
    """
    
    temp_dir = tempfile.gettempdir()
    update_file_path = os.path.join(temp_dir, "easyfacture_updating.html")
    with open(update_file_path, "w", encoding="utf-8") as f:
        f.write(updating_html)

    def background_update_task():
        try:
            req = urllib.request.Request(
                GITHUB_API_URL, 
                headers={'User-Agent': 'EasyFacture-Updater'}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                exe_url = None
                for asset in data.get("assets", []):
                    if asset["name"].lower().endswith(".exe"):
                        exe_url = asset["browser_download_url"]
                        break
                
                if exe_url:
                    installer_path = os.path.join(temp_dir, "Setup_EasyFacture_Update.exe")
                    urllib.request.urlretrieve(exe_url, installer_path)
                    
                    if os.path.exists(installer_path):
                        subprocess.run([
                            installer_path, 
                            '/VERYSILENT', 
                            '/SUPPRESSMSGBOXES', 
                            '/NORESTART', 
                            '/CLOSEAPPLICATIONS'
                        ], check=False)
                        
                        python_exe = sys.executable
                        if "python.exe" in python_exe.lower():
                            pythonw_candidate = python_exe.replace("python.exe", "pythonw.exe")
                            if os.path.exists(pythonw_candidate):
                                python_exe = pythonw_candidate
                        
                        subprocess.Popen([python_exe, __file__], cwd=script_dir)
                        os._exit(0)
        except Exception:
            pass
        sys.exit(0)

    import threading
    t = threading.Thread(target=background_update_task)
    t.start()

    # Récupération de la résolution pour la fenêtre de maj avec marges
    import ctypes
    user32 = ctypes.windll.user32
    user32.SetProcessDPIAware()
    w = int(user32.GetSystemMetrics(0) * 0.90)
    h = int(user32.GetSystemMetrics(1) * 0.90)
    x = int((user32.GetSystemMetrics(0) - w) / 2)
    y = int((user32.GetSystemMetrics(1) - h) / 2)

    webview.create_window(
        "Mise à jour - EasyFacture", 
        update_file_path, 
        width=w, 
        height=h, 
        x=x, 
        y=y,
        resizable=True
    )
    webview.start()

def verifier_et_installer_maj_avec_ui(script_dir):
    try:
        req = urllib.request.Request(
            GITHUB_API_URL, 
            headers={'User-Agent': 'EasyFacture-Updater'}
        )
        with urllib.request.urlopen(req, timeout=3) as response:
            data = json.loads(response.read().decode())
            latest_tag = data.get("tag_name", "").strip().lstrip('v')
            
            if latest_tag and latest_tag > CURRENT_VERSION:
                executer_mise_a_jour(script_dir)
    except Exception:
        pass

if __name__ == "__main__":
    script_dir = os.path.dirname(__file__)

    if len(sys.argv) > 1 and sys.argv[1] == "--check-update":
        verifier_et_installer_maj_avec_ui(script_dir)
        sys.exit(0)

    verifier_et_installer_maj_avec_ui(script_dir)

    server_process = None

    if not is_app_running():
        script_app = os.path.join(script_dir, "app.py")
        python_exe = sys.executable
        if "python.exe" in python_exe.lower():
            pythonw_candidate = python_exe.replace("python.exe", "pythonw.exe")
            if os.path.exists(pythonw_candidate):
                python_exe = pythonw_candidate

        server_process = subprocess.Popen([python_exe, script_app], cwd=script_dir)

    loading_html = """
    <!DOCTYPE html>
    <html lang="fr">
    <head>
        <meta charset="UTF-8">
        <title>Chargement d'EasyFacture</title>
        <style>
            body, html {
                margin: 0;
                padding: 0;
                background-color: #0f172a;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                color: #f8fafc;
                overflow: hidden !important;
            }
            .container {
                text-align: center;
                transition: opacity 0.8s ease-in-out;
            }
            .logo {
                width: 90px;
                height: 90px;
                margin-bottom: 20px;
                animation: pulse 2s infinite ease-in-out;
            }
            h1 {
                font-size: 26px;
                font-weight: 700;
                margin: 0 0 10px 0;
                letter-spacing: 0.5px;
            }
            .message {
                font-size: 14px;
                color: #94a3b8;
                height: 20px;
                margin-bottom: 30px;
            }
            .spinner {
                width: 35px;
                height: 35px;
                border: 3px solid rgba(255, 255, 255, 0.1);
                border-top: 3px solid #3b82f6;
                border-radius: 50%;
                animation: spin 0.8s linear infinite;
                margin: 0 auto;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            @keyframes pulse {
                0%, 100% { transform: scale(1); opacity: 1; }
                50% { transform: scale(1.05); opacity: 0.85; }
            }
            .welcome-screen {
                opacity: 0;
                transform: scale(0.95);
                transition: all 0.6s cubic-bezier(0.16, 1, 0.3, 1);
            }
            .welcome-screen.show {
                opacity: 1;
                transform: scale(1);
            }
        </style>
    </head>
    <body>
        <div class="container" id="main-container">
            <img src="assets/logo.ico" alt="Logo EasyFacture" class="logo" onerror="this.style.display='none'">
            <h1>EasyFacture</h1>
            <div class="message" id="loading-msg">Préparation de votre espace de travail...</div>
            <div class="spinner" id="spinner"></div>
        </div>

        <script>
            const messages = [
                "Vérification des moteurs de calcul...",
                "Chargement de vos factures et clients...",
                "Optimisation de l'interface...",
                "Presque prêt..."
            ];

            let msgIndex = 0;
            const msgElement = document.getElementById("loading-msg");

            const msgInterval = setInterval(() => {
                msgIndex++;
                if (msgIndex < messages.length) {
                    msgElement.textContent = messages[msgIndex];
                } else {
                    clearInterval(msgInterval);
                }
            }, 800);

            function checkServer() {
                fetch("http://localhost:9876", { mode: 'no-cors' })
                    .then(() => {
                        clearInterval(msgInterval);
                        msgElement.textContent = "Bienvenue ! 🎉";
                        document.getElementById("spinner").style.display = "none";
                        
                        document.getElementById("main-container").classList.add("welcome-screen");
                        document.getElementById("main-container").classList.add("show");

                        setTimeout(() => {
                            window.location.replace("http://localhost:9876");
                        }, 500);
                    })
                    .catch(() => {
                        setTimeout(checkServer, 400);
                    });
            }

            setTimeout(checkServer, 1000);
        </script>
    </body>
    </html>
    """

    temp_dir = tempfile.gettempdir()
    loading_file_path = os.path.join(temp_dir, "easyfacture_loading.html")
    with open(loading_file_path, "w", encoding="utf-8") as f:
        f.write(loading_html)

    # Calcul dynamique de la taille (90% de l'écran) et centrage avec marges
    import ctypes
    user32 = ctypes.windll.user32
    user32.SetProcessDPIAware()
    screen_width = user32.GetSystemMetrics(0)
    screen_height = user32.GetSystemMetrics(1)

    win_width = int(screen_width * 0.90)
    win_height = int(screen_height * 0.90)
    win_x = int((screen_width - win_width) / 2)
    win_y = int((screen_height - win_height) / 2)

    try:
        webview.create_window(
            "EasyFacture", 
            loading_file_path, 
            width=win_width, 
            height=win_height, 
            x=win_x, 
            y=win_y,
            min_size=(900, 600)
        )
        webview.start()
    except Exception as e:
        # Solution de secours ultime : si le webview natif plante, on ouvre l'app dans le navigateur par défaut
        import webbrowser
        webbrowser.open("http://localhost:9876")
        # On garde le processus serveur actif
        if server_process:
            server_process.wait()

    if server_process:
        try:
            server_process.terminate()
        except Exception:
            pass