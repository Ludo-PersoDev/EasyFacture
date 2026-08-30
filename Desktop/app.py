from datetime import datetime
import multiprocessing
import os
import sys
import threading
import nicegui
import asyncio
import time
import subprocess
import json
from supabase import create_client, Client

# --- GESTION DES CHEMINS (Défini en premier pour config.json) ---
if getattr(sys, "frozen", False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

os.chdir(application_path)
sys.path.insert(0, application_path)

# --- CHARGEMENT DE LA CONFIGURATION SUPABASE ---
CONFIG_FILE = os.path.join(application_path, "config.json")

SUPABASE_URL = ""
SUPABASE_KEY = ""

if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            SUPABASE_URL = config.get("SUPABASE_URL", "")
            SUPABASE_KEY = config.get("SUPABASE_KEY", "")
    except Exception as e:
        print(f"[Config Error] Impossible de lire le fichier de config : {e}")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("⚠️ Attention : Configuration Supabase manquante dans config.json")

# Initialisation du client Supabase global
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

# Fichier local pour stocker la session et éviter de se reconnecter à chaque fois
SESSION_FILE = os.path.join(os.path.expanduser("~"), ".easyfacture_session.json")

log_file = open("app.log", "a", encoding="utf-8")
sys.stdout = log_file
sys.stderr = log_file

if getattr(sys, "frozen", False):
    log_path = os.path.join(os.path.dirname(sys.executable), "erreur_fatale.txt")
    sys.stdout = open(log_path, "w", encoding="utf-8")
    sys.stderr = open(log_path, "w", encoding="utf-8")
else:
    if sys.stdout is None: sys.stdout = open(os.devnull, "w")
    if sys.stderr is None: sys.stderr = open(os.devnull, "w")

if __name__ == "__main__":
    multiprocessing.freeze_support()

from auto_backup import lancer_sauvegarde_automatique
import database
from fastapi.responses import FileResponse
from ui_analytics import render_analytics
from ui_clients import render_clients
from ui_devis import render_devis
from ui_factures import render_factures
from ui_interventions import render_interventions
from ui_maintenance import render_maintenance
from ui_parametres import render_parametres
from ui_passerelle import render_passerelle_export
from ui_prestations import render_prestations
from ui_helpers import lancer_assistance_technique

# --- GESTION DE LA SESSION UTILISATEUR ---
current_user = None

def charger_session_enregistree():
    global current_user
    if not supabase:
        return False
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                access_token = data.get("access_token")
                refresh_token = data.get("refresh_token")
                if access_token and refresh_token:
                    # Restauration de la session dans Supabase
                    res = supabase.auth.set_session(access_token, refresh_token)
                    if res.user:
                        current_user = res.user
                        # Initialisation de la BDD Supabase avec l'utilisateur connecté
                        database.init_database_supabase(supabase, current_user.id)
                        return True
        except Exception as e:
            print(f"[Auth Error] Impossible de restaurer la session : {e}")
    return False

def sauvegarder_session(session):
    try:
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "access_token": session.access_token,
                "refresh_token": session.refresh_token
            }, f)
    except Exception as e:
        print(f"[Auth Error] Impossible de sauvegarder la session : {e}")

def effacer_session():
    global current_user
    current_user = None
    if os.path.exists(SESSION_FILE):
        try:
            os.remove(SESSION_FILE)
        except:
            pass
    if supabase:
        try:
            supabase.auth.sign_out()
        except:
            pass
    ui.navigate.to("/")

# --- GESTION PROPRE DE LA FERMETURE ---
def sauvegarder_et_quitter():
    ui.notify(
        "Sauvegarde des données et fermeture en cours...", 
        type="ongoing", 
        spinner=True, 
        position="bottom-right",
        timeout=None
    )
    
    def tache_arriere_plan():
        try:
            lancer_sauvegarde_automatique()
        except Exception as e:
            print(f"[Erreur Backup Quitter] {e}")
        
        import time
        time.sleep(0.5)
        
        try:
            if getattr(sys, "frozen", False):
                nom_executable = os.path.basename(sys.executable)
                subprocess.Popen(f"taskkill /f /im {nom_executable}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                subprocess.Popen(f"taskkill /f /pid {os.getpid()}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.Popen(f"taskkill /f /im pythonw.exe", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            print(f"[Erreur Taskkill global] {e}")
            os._exit(0)

    threading.Thread(target=tache_arriere_plan, daemon=True).start()

@app.get('/pdf/{filepath:path}')
def serve_pdf(filepath: str):
    full_path = os.path.join(os.getcwd(), "Export", filepath)
    if os.path.exists(full_path):
        return FileResponse(full_path, media_type='application/pdf')
    return 'Fichier introuvable', 404

@app.on_startup
def startup_backup():
    try:
        lancer_sauvegarde_automatique()
        print("[Backup] Sauvegarde initiale effectuée.")
    except Exception as e:
        print(f"[Backup Error] {e}")

os.makedirs("assets", exist_ok=True)
app.add_static_files("/assets", "assets")

current_page = "Accueil"

def set_page(page_name: str):
    global current_page
    current_page = page_name
    content_area.refresh()

def render_odoo_home():
    niveau = database.verifier_progression_onboarding()
    
    with ui.column().classes("w-full items-center justify-center py-6 gap-8"):
        with ui.column().classes("items-center gap-2 text-center max-w-xl"):
            ui.label("Bienvenue sur EasyFacture").classes("text-3xl font-extrabold text-slate-800")
            
            if niveau == 1:
                ui.label("⚠️ Étape 1 : Configuration de l'entreprise requise").classes("text-amber-600 font-bold")
                ui.label("Veuillez renseigner les informations de votre entreprise dans les paramètres pour commencer.").classes("text-slate-500 text-sm")
            elif niveau == 2:
                ui.label("⚠️ Étape 2 : Votre catalogue de prestations est vide").classes("text-orange-600 font-bold")
                ui.label("Veuillez ajouter vos prestations ou formations dans le Catalogue avant de pouvoir créer des clients.").classes("text-slate-500 text-sm")
            elif niveau == 3:
                ui.label("⚠️ Étape 3 : Aucun client enregistré").classes("text-teal-600 font-bold")
                ui.label("Veuillez ajouter au moins un client pour pouvoir commencer à réaliser des devis et factures.").classes("text-slate-500 text-sm")
            else:
                ui.label("Sélectionnez un module pour commencer").classes("text-slate-500 text-sm")

        modules = [
            ("build", "Infos de mon entreprise", "slate", "Configuration/modification de mon entreprise", 1),
            ("groups", "Clients", "teal", "Fichier clients & grille tarifaire", 3),
            ("list_alt", "Catalogue", "orange", "Liste des prestations & formations", 2),
            ("description", "Devis", "blue", "Gestion et conversion des devis", 4),
            ("event_available", "Suivi des prestations réalisées", "emerald", "Saisie et suivi des prestations", 4),
            ("receipt", "Factures", "violet", "Facturation & avoirs", 4),
            ("bar_chart", "CRM & Analytics", "indigo", "Suivi du CA et statistiques", 4),
            ("cloud_upload", "Passerelle Factur-X", "sky", "Export et envoi des PDF vers la plateforme", 4),
            ("settings_backup_restore", "Sauvegarde & Maintenance", "zinc", "Export/Import de la BDD et transfert PC", 2),
        ]

        with ui.grid(columns=3).classes("gap-6 max-w-5xl w-full px-4"):
            for icon, title, color, desc, niveau_requis in modules:
                is_module_blocked = niveau < niveau_requis
                
                card = ui.card().classes("p-6 cursor-pointer hover:shadow-lg transition-all duration-200 border border-slate-200 flex flex-col items-center text-center gap-3 bg-white hover:-translate-y-1")
                if is_module_blocked:
                    card.classes("opacity-50 cursor-not-allowed")
                    card.on("click", lambda m="Module verrouillé": ui.notify(m, type="warning"))
                else:
                    card.on("click", lambda t=title: set_page(t))
                with card:
                    ui.icon(icon, size="2.5rem").classes(f"text-{color}-600")
                    ui.label(title).classes("font-bold text-lg text-slate-800")
                    ui.label(desc).classes("text-xs text-slate-500")

@ui.refreshable
def content_area():
    if current_page == "Accueil":
        render_odoo_home()
    elif current_page == "CRM & Analytics":
        render_analytics()
    elif current_page == "Passerelle Factur-X":
        render_passerelle_export()
    elif current_page in ["Infos de mon entreprise", "Paramètres"]:
        render_parametres()
    elif current_page == "Catalogue":
        render_prestations()
    elif current_page == "Clients":
        render_clients()
    elif current_page == "Devis":
        render_devis()
    elif current_page in ["Interventions", "Suivi des prestations réalisées"]:
        render_interventions()
    elif current_page == "Factures":
        render_factures()
    elif current_page in ["Maintenance", "Sauvegarde & Maintenance"]:
        render_maintenance()
    else:
        render_fallback()

def render_fallback():
    with ui.column().classes("gap-4"):
        ui.button("← Retour à l'accueil", icon="arrow_back", on_click=lambda: set_page("Accueil")).props("flat color=primary")
        ui.label(f"Module : {current_page}").classes("text-2xl font-bold text-slate-800")

@ui.page("/")
def main_page():
    # Vérification de la session au chargement de la page principale
    if not charger_session_enregistree():
        render_login_screen()
        return

    # Interface principale si authentifié
    with ui.header().classes("bg-white border-b border-slate-200 px-6 py-3 flex justify-between items-center text-slate-800"):
        with ui.row().classes("items-center gap-4"):
            ui.button(icon="grid_view", on_click=lambda: set_page("Accueil")).props("flat round color=primary").tooltip("Menu Principal")
            ui.label("EasyFacture").classes("font-bold text-lg text-slate-800")
        
        with ui.row().classes("items-center gap-2"):
            ui.label(f"Connecté ({current_user.email if current_user else ''})").classes("text-xs text-slate-500 mr-2")
            b = ui.button(on_click=lancer_assistance_technique).props("flat color=primary")
            with b:
                ui.image('assets/support_icon.png').classes('w-10 h-10 mr-2')
                ui.label('Assistance')
            ui.badge("v1.9").props("color=slate outline")
            ui.button("Déconnexion", icon="logout", on_click=effacer_session).props("flat color=orange").classes("ml-2")
            ui.button("Quitter", icon="exit_to_app", on_click=sauvegarder_et_quitter).props("flat color=red").classes("ml-2")

    with ui.column().classes("w-full p-6 bg-slate-50 min-h-screen"):
        content_area()

def render_login_screen():
    with ui.column().classes("w-full h-screen items-center justify-center bg-slate-900"):
        with ui.card().classes("w-96 p-8 bg-slate-800 border border-slate-700 text-white shadow-2xl rounded-2xl gap-4"):
            with ui.column().classes("items-center w-full gap-2 mb-2"):
                ui.icon("lock_person", size="3rem").classes("text-blue-500")
                ui.label("Connexion EasyFacture").classes("text-xl font-bold")
                ui.label("Entrez vos identifiants Supabase").classes("text-xs text-slate-400")

            email_input = ui.input("Email").classes("w-full").props("dark outlined")
            password_input = ui.input("Mot de passe", password=True, password_toggle_button=True).classes("w-full").props("dark outlined")

            def tenter_connexion():
                if not supabase:
                    ui.notify("Client Supabase non initialisé (vérifiez config.json)", type="negative")
                    return
                try:
                    res = supabase.auth.sign_in_with_password({
                        "email": email_input.value,
                        "password": password_input.value
                    })
                    if res.session:
                        sauvegarder_session(res.session)
                        ui.navigate.to("/")
                    else:
                        ui.notify("Échec de la connexion", type="negative")
                except Exception as e:
                    ui.notify(f"Erreur : {e}", type="negative")

            ui.button("Se connecter", on_click=tenter_connexion).classes("w-full bg-blue-600 text-white font-bold py-3 mt-2").props("unelevated")

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="EasyFacture", port=9876, reload=False, show=False)