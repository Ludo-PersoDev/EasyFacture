from datetime import datetime
import multiprocessing
import os
import sys
import threading
from pathlib import Path
from nicegui import app, ui
from nicegui import run
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

# --- DOSSIER DE DONNÉES LOCALES (Asset & Sync) ---
LOCAL_ASSETS_DIR = Path("assets")
LOCAL_ASSETS_DIR.mkdir(parents=True, exist_ok=True)
LOCAL_LOGO_PATH = LOCAL_ASSETS_DIR / "logo.png"

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

# --- GESTION DE LA SYNCHRONISATION LOCALE (LOGO & FACTURES VIA SUPABASE) ---

def sync_local_logo(supabase_client: Client, user_id: str, bucket_name: str = "settings") -> Path:
    """
    Vérifie et télécharge le logo distant (isolé par utilisateur) dans le stockage local si nécessaire.
    """
    if not supabase_client or not user_id:
        return LOCAL_LOGO_PATH if LOCAL_LOGO_PATH.exists() else None
        
    remote_logo_path = f"{user_id}/company_logo/logo.png"
    try:
        response = supabase_client.storage.from_(bucket_name).download(remote_logo_path)
        if response:
            with open(LOCAL_LOGO_PATH, "wb") as f:
                f.write(response)
    except Exception as e:
        print(f"[Logo Sync] Impossible de synchroniser le logo distant : {e}")
    
    if LOCAL_LOGO_PATH.exists():
        return LOCAL_LOGO_PATH
    
    return None

def sync_pending_factures(supabase_client: Client, user_id: str, bucket_name: str = "documents"):
    if not supabase_client or not user_id:
        print("[Sync Factures] Annulé : client ou user_id manquant.", flush=True)
        return

    try:
        response = supabase_client.table("factures").select("id, numero_facture, pdf_path, pdf_url").execute()
        invoices = response.data
        
        if not invoices:
            print("[Sync Factures] Aucune facture trouvée dans la table distante.", flush=True)
            return

        for inv in invoices:
            if inv.get("pdf_url"):
                continue

            inv_id = inv.get("id")
            inv_number = inv.get("numero_facture")
            pdf_path = inv.get("pdf_path")
            
            try:
                if not pdf_path or not os.path.exists(pdf_path):
                    continue
                    
                file_name = f"{inv_number}.pdf"
                # Arborescence demandée : documents/{user_id}/factures/{nomdoc}
                storage_path = f"{user_id}/factures/{file_name}"
                
                with open(pdf_path, "rb") as f:
                    file_bytes = f.read()
                    
                supabase_client.storage.from_(bucket_name).upload(
                    path=storage_path,
                    file=file_bytes,
                    file_options={"content-type": "application/pdf", "upsert": "true"}
                )
                
                public_url = supabase_client.storage.from_(bucket_name).get_public_url(storage_path)
                
                if public_url:
                    supabase_client.table("factures").update({
                        "pdf_url": public_url
                    }).eq("id", inv_id).execute()
                    
                    print(f"✅ [Sync Factures] Facture {inv_number} synchronisée ! URL : {public_url}", flush=True)
                
            except Exception as e:
                print(f"❌ [Sync Error] Facture {inv_number} : {e}", flush=True)
                continue
                
    except Exception as e:
        print(f"❌ [Sync Error general factures] {e}", flush=True)
        
def sync_pending_devis(supabase_client: Client, user_id: str, bucket_name: str = "documents"):
    if not supabase_client or not user_id:
        print("[Sync Devis] Annulé : client ou user_id manquant.", flush=True)
        return

    try:
        response = supabase_client.table("devis").select("id, numero_devis, pdf_path, pdf_url").execute()
        devis_list = response.data
        
        if not devis_list:
            print("[Sync Devis] Aucun devis trouvé dans la table distante.", flush=True)
            return

        for dev in devis_list:
            if dev.get("pdf_url"):
                continue

            dev_id = dev.get("id")
            dev_number = dev.get("numero-devis")
            pdf_path = dev.get("pdf_path")
            
            try:
                if not pdf_path or not os.path.exists(pdf_path):
                    continue
                    
                file_name = f"{dev_number}.pdf"
                # Arborescence demandée : documents/{user_id}/devis/{nomdoc}
                storage_path = f"{user_id}/devis/{file_name}"
                
                with open(pdf_path, "rb") as f:
                    file_bytes = f.read()
                    
                supabase_client.storage.from_(bucket_name).upload(
                    path=storage_path,
                    file=file_bytes,
                    file_options={"content-type": "application/pdf", "upsert": "true"}
                )
                
                public_url = supabase_client.storage.from_(bucket_name).get_public_url(storage_path)
                
                if public_url:
                    supabase_client.table("devis").update({
                        "pdf_url": public_url
                    }).eq("id", dev_id).execute()
                    
                    print(f"✅ [Sync Devis] Devis {dev_number} synchronisé ! URL : {public_url}", flush=True)
                
            except Exception as e:
                print(f"❌ [Sync Error] Devis {dev_number} : {e}", flush=True)
                continue
                
    except Exception as e:
        print(f"❌ [Sync Error general devis] {e}", flush=True)


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
                    res = supabase.auth.set_session(access_token, refresh_token)
                    if res.user:
                        current_user = res.user
                        database.init_database_supabase(supabase, current_user.id)
                        
                        # Lancement de la synchro avec le user_id de l'utilisateur connecté
                        threading.Thread(target=lambda: sync_local_logo(supabase, current_user.id), daemon=True).start()
                        threading.Thread(target=lambda: sync_pending_factures(supabase, current_user.id), daemon=True).start()
                        threading.Thread(target=lambda: sync_pending_devis(supabase, current_user.id), daemon=True).start()
                        
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
                    def make_handler(t):
                        return lambda: set_page(t)
                    card.on("click", make_handler(title))

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
def main_page(access_token: str = None, refresh_token: str = None, type: str = None):
    global current_user
    
    if access_token and refresh_token:
        try:
            res = supabase.auth.set_session(access_token, refresh_token)
            if res.user:
                current_user = res.user
                if type == "recovery":
                    render_update_password_screen()
                    return
                else:
                    sauvegarder_session(res.session)
        except Exception as e:
            print(f"[Auth Error Token] {e}")

    if not charger_session_enregistree():
        render_login_screen()
        return

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

def render_update_password_screen():
    with ui.column().classes("w-full h-screen items-center justify-center bg-slate-900"):
        with ui.card().classes("w-96 p-8 bg-slate-800 border border-slate-700 text-white shadow-2xl rounded-2xl gap-4"):
            with ui.column().classes("items-center w-full gap-2 mb-2"):
                ui.icon("lock_reset", size="3rem").classes("text-amber-500")
                ui.label("Nouveau mot de passe").classes("text-xl font-bold")
                ui.label("Veuillez définir votre nouveau mot de passe").classes("text-xs text-slate-400")

            new_password_input = ui.input("Nouveau mot de passe", password=True, password_toggle_button=True).classes("w-full").props("dark outlined")
            confirm_password_input = ui.input("Confirmer le mot de passe", password=True, password_toggle_button=True).classes("w-full").props("dark outlined")

            def valider_nouveau_mot_de_passe():
                if not new_password_input.value or not confirm_password_input.value:
                    ui.notify("Veuillez remplir tous les champs", type="warning")
                    return
                if new_password_input.value != confirm_password_input.value:
                    ui.notify("Les mots de passe ne correspondent pas", type="negative")
                    return
                try:
                    supabase.auth.update_user({"password": new_password_input.value})
                    ui.notify("Mot de passe mis à jour avec succès !", type="positive")
                    session = supabase.auth.get_session()
                    if session:
                        sauvegarder_session(session)
                    ui.navigate.to("/")
                except Exception as e:
                    ui.notify(f"Erreur lors de la mise à jour : {e}", type="negative")

            ui.button("Mettre à jour", on_click=valider_nouveau_mot_de_passe).classes("w-full bg-amber-600 text-white font-bold py-3 mt-2").props("unelevated")

def render_login_screen():
    auth_mode = "login"

    with ui.column().classes("w-full h-screen items-center justify-center bg-slate-900"):
        container = ui.card().classes("w-96 p-8 bg-slate-800 border border-slate-700 text-white shadow-2xl rounded-2xl gap-4")

        def update_auth_card():
            container.clear()
            with container:
                nonlocal auth_mode
                if auth_mode == "login":
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
                                global current_user
                                current_user = res.user
                                database.init_database_supabase(supabase, current_user.id)
                                
                                # Lancement asynchrone des synchronisations avec l'ID utilisateur
                                threading.Thread(target=lambda: sync_local_logo(supabase, current_user.id), daemon=True).start()
                                threading.Thread(target=lambda: sync_pending_invoices(supabase, current_user.id), daemon=True).start()
                                
                                ui.navigate.to("/")
                            else:
                                ui.notify("Échec de la connexion", type="negative")
                        except Exception as e:
                            ui.notify("Identifiants incorrects ou erreur de connexion.", type="negative")

                    ui.button("Se connecter", on_click=tenter_connexion).classes("w-full bg-blue-600 text-white font-bold py-3 mt-2").props("unelevated")
                    
                    with ui.row().classes("w-full justify-between mt-3 text-xs"):
                        ui.button("Mot de passe oublié ?", on_click=lambda: set_mode("forgot")).props("flat dense color=blue-400")
                        ui.button("Créer un compte", on_click=lambda: set_mode("signup")).props("flat dense color=green-400")

                elif auth_mode == "signup":
                    with ui.column().classes("items-center w-full gap-2 mb-2"):
                        ui.icon("person_add", size="3rem").classes("text-green-500")
                        ui.label("Inscription EasyFacture").classes("text-xl font-bold")
                        ui.label("Créer un nouveau compte").classes("text-xs text-slate-400")

                    email_input = ui.input("Email").classes("w-full").props("dark outlined")
                    password_input = ui.input("Mot de passe", password=True, password_toggle_button=True).classes("w-full").props("dark outlined")
                    confirm_password_input = ui.input("Confirmer le mot de passe", password=True, password_toggle_button=True).classes("w-full").props("dark outlined")

                    def tenter_inscription():
                        if not supabase:
                            ui.notify("Client Supabase non initialisé", type="negative")
                            return
                        if not email_input.value or not password_input.value:
                            ui.notify("Veuillez remplir tous les champs", type="warning")
                            return
                        if password_input.value != confirm_password_input.value:
                            ui.notify("Les mots de passe ne correspondent pas", type="negative")
                            return
                        
                        try:
                            res = supabase.auth.sign_up({
                                "email": email_input.value,
                                "password": password_input.value
                            })
                            
                            user_obj = getattr(res, "user", None)
                            identities = getattr(user_obj, "identities", None) if user_obj else None
                            
                            if user_obj and identities is not None and len(identities) == 0:
                                ui.notify("Cet e-mail est déjà utilisé par un autre compte.", type="warning")
                            else:
                                ui.notify("Compte créé avec succès ! Vous pouvez vous connecter.", type="positive")
                                set_mode("login")
                        except Exception as e:
                            err_msg = str(e)
                            if "already registered" in err_msg.lower() or "already exists" in err_msg.lower() or "user already registered" in err_msg.lower():
                                ui.notify("Cet e-mail est déjà utilisé par un autre compte.", type="warning")
                            else:
                                ui.notify("Cet e-mail est déjà utilisé ou invalide.", type="warning")

                    ui.button("S'inscrire", on_click=tenter_inscription).classes("w-full bg-green-600 text-white font-bold py-3 mt-2").props("unelevated")
                    
                    with ui.row().classes("w-full justify-center mt-3"):
                        ui.button("← Retour à la connexion", on_click=lambda: set_mode("login")).props("flat dense color=slate-400")

                elif auth_mode == "forgot":
                    with ui.column().classes("items-center w-full gap-2 mb-2"):
                        ui.icon("lock_reset", size="3rem").classes("text-amber-500")
                        ui.label("Mot de passe oublié").classes("text-xl font-bold")
                        ui.label("Recevoir un lien de réinitialisation").classes("text-xs text-slate-400")

                    email_input = ui.input("Email").classes("w-full").props("dark outlined")

                    def tenter_reinitialisation():
                        if not supabase:
                            ui.notify("Client Supabase non initialisé", type="negative")
                            return
                        if not email_input.value:
                            ui.notify("Veuillez entrer votre adresse e-mail", type="warning")
                            return
                        try:
                            supabase.auth.reset_password_for_email(
                                email_input.value,
                                {"redirect_to": "http://localhost:9876/"}
                            )
                            ui.notify("Si cet e-mail existe, un lien de réinitialisation a été envoyé.", type="positive")
                            set_mode("login")
                        except Exception as e:
                            ui.notify(f"Erreur : {e}", type="negative")

                    ui.button("Envoyer le lien", on_click=tenter_reinitialisation).classes("w-full bg-amber-600 text-white font-bold py-3 mt-2").props("unelevated")
                    
                    with ui.row().classes("w-full justify-center mt-3"):
                        ui.button("← Retour à la connexion", on_click=lambda: set_mode("login")).props("flat dense color=slate-400")

        def set_mode(mode):
            nonlocal auth_mode
            auth_mode = mode
            update_auth_card()

        update_auth_card()

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="EasyFacture", port=9876, reload=False, show=False)