from datetime import datetime
import multiprocessing
import os
import sys
import threading
from nicegui import run
from nicegui import app, ui
import asyncio
import time
import subprocess

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

application_path = os.path.dirname(sys.executable) if getattr(sys, "frozen", False) else os.path.dirname(os.path.abspath(__file__))
os.chdir(application_path)
sys.path.insert(0, application_path)

from auto_backup import lancer_sauvegarde_automatique
import database
from nicegui import app, ui
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

# --- GESTION PROPRE DE LA FERMETURE ---
def sauvegarder_et_quitter():
    """Sauvegarde et fermeture totale via purge des processus Python / App"""
    
    ui.notify(
        "Sauvegarde des données et fermeture en cours...", 
        type="ongoing", 
        spinner=True, 
        position="bottom-right",
        timeout=None
    )
    
    def tache_arriere_plan():
        try:
            # 1. Exécution de la sauvegarde Google Drive
            lancer_sauvegarde_automatique()
        except Exception as e:
            print(f"[Erreur Backup Quitter] {e}")
        
        import time
        time.sleep(0.5)
        
        # 2. Nettoyage radical par nom de processus et par PID
        try:
            # Si on tourne sous forme d'exécutable ou de script python, on cible large pour nettoyer la fenêtre et le serveur
            if getattr(sys, "frozen", False):
                nom_executable = os.path.basename(sys.executable)
                subprocess.Popen(f"taskkill /f /im {nom_executable}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                # En mode dev (python.exe / pythonw.exe), on tue les instances python et le PID courant
                subprocess.Popen(f"taskkill /f /pid {os.getpid()}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                # Optionnel : si le launcher lance pythonw, on peut aussi nettoyer un coup si besoin
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
database.initialiser_bdd()

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
                
                with ui.column().classes("w-full bg-blue-50 p-3 rounded-lg border border-blue-200 gap-1 mt-3 text-center"):
                    ui.label("💡 Restauration de données").classes("text-xs font-bold text-blue-800")
                    ui.label("IMPORTANT : Dans le cas d'une restauration de données, vous pourrez récupérer vos sauvegardes dès que votre SIRET et votre Raison Sociale seront renseignés.").classes("text-xs text-blue-700")

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
                    if niveau == 1:
                        msg = "Veuillez d'abord configurer votre entreprise dans les paramètres."
                    elif niveau == 2:
                        msg = "Veuillez d'abord ajouter des prestations dans le Catalogue."
                    else:
                        msg = "Veuillez d'abord enregistrer au moins un client."
                    card.on("click", lambda m=msg: ui.notify(m, type="warning"))
                else:
                    card.on("click", lambda t=title: set_page(t))
                with card:
                    ui.icon(icon, size="2.5rem").classes(f"text-{color}-600")
                    ui.label(title).classes("font-bold text-lg text-slate-800")
                    ui.label(desc).classes("text-xs text-slate-500")

@ui.refreshable
def content_area():
    niveau = database.verifier_progression_onboarding()
    
    message_blocage = ""
    redirection_cible = "Infos de mon entreprise"
    
    if niveau == 1 and current_page not in ["Infos de mon entreprise", "Paramètres"]:
        message_blocage = "Veuillez terminer la configuration de votre entreprise."
        redirection_cible = "Infos de mon entreprise"
    elif niveau == 2 and current_page in ["Clients", "Devis", "Factures", "Interventions", "Suivi des prestations réalisées", "CRM & Analytics", "Passerelle Factur-X"]:
        message_blocage = "Veuillez d'abord renseigner votre catalogue de prestations."
        redirection_cible = "Catalogue"
    elif niveau == 3 and current_page in ["Devis", "Factures", "Interventions", "Suivi des prestations réalisées", "CRM & Analytics", "Passerelle Factur-X"]:
        message_blocage = "Veuillez d'abord enregistrer au moins un client."
        redirection_cible = "Clients"
        
    if message_blocage and current_page != "Accueil":
        with ui.column().classes("w-full items-center justify-center p-10 gap-2"):
            ui.icon("lock", size="4rem", color="slate-400")
            ui.label("Accès restreint").classes("text-xl font-bold")
            ui.label(message_blocage).classes("text-slate-500")
            
            if niveau == 1:
                with ui.column().classes("w-full max-w-lg bg-blue-50 p-4 rounded-lg border border-blue-200 gap-1 mt-3 text-center"):
                    ui.label("💡 Restauration de données").classes("text-xs font-bold text-blue-800")
                    ui.label("IMPORTANT : Dans le cas d'une restauration de données, vous pourrez récupérer vos sauvegardes dès que votre SIRET et votre Raison Sociale seront renseignés.").classes("text-xs text-blue-700")

            ui.button("Continuer le parcours", on_click=lambda target=redirection_cible: set_page(target)).classes("mt-4")
        return

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
        ui.label("Contenu en cours de développement...").classes("text-slate-500")

with ui.header().classes("bg-white border-b border-slate-200 px-6 py-3 flex justify-between items-center text-slate-800"):
    with ui.row().classes("items-center gap-4"):
        ui.button(icon="grid_view", on_click=lambda: set_page("Accueil")).props("flat round color=primary").tooltip("Menu Principal")
        ui.label("EasyFacture").classes("font-bold text-lg text-slate-800")
    
    with ui.row().classes("items-center gap-2"):
        b = ui.button(on_click=lancer_assistance_technique).props("flat color=primary")
        with b:
            ui.image('assets/support_icon.png').classes('w-10 h-10 mr-2')
            ui.label('Assistance')
        ui.badge("v1.9").props("color=slate outline")
        ui.button("Quitter", icon="exit_to_app", on_click=sauvegarder_et_quitter).props("flat color=red").classes("ml-4")

with ui.column().classes("w-full p-6 bg-slate-50 min-h-screen"):
    content_area()

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="EasyFacture", port=9876, reload=False, show=False)