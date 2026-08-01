from nicegui import app, ui
import os
import database
import sys
from ui_parametres import render_parametres
from ui_prestations import render_prestations
from ui_clients import render_clients
from ui_devis import render_devis
from ui_interventions import render_interventions
from ui_factures import render_factures
from ui_analytics import render_analytics
from ui_passerelle import render_passerelle_export

database.initialiser_bdd()

os.makedirs("assets", exist_ok=True)
app.add_static_files('/assets', 'assets')

current_page = "Accueil"

def set_page(page_name: str):
    global current_page
    current_page = page_name
    content_area.refresh()

# --- VUE ACCUEIL (Style Odoo / Launcher) ---
def render_odoo_home():
    with ui.column().classes("w-full items-center justify-center py-6 gap-8"):
        with ui.column().classes("items-center gap-2 text-center"):
            ui.label("Bienvenue sur EasyFacture").classes("text-3xl font-extrabold text-slate-800")
            ui.label("Sélectionnez un module pour commencer").classes("text-slate-500 text-sm")

        # Dans render_odoo_home() dans app.py :

        modules = [
            # Ligne 1 : Configuration & Référentiels
            ("build", "Infos de mon entreprise", "slate", "Configuration/modification de mon entreprise"),
            ("groups", "Clients", "teal", "Fichier clients & grille tarifaire"),
            ("list_alt", "Catalogue", "orange", "Liste des prestations & formations"),
            
            # Ligne 2 : Moteur de Facturation & Activité
            ("description", "Devis", "blue", "Gestion et conversion des devis"),
            ("event_available", "Suivi des prestations réalisées", "emerald", "Saisie et suivi des prestations"),
            ("receipt", "Factures", "violet", "Facturation & avoirs"),
            
            # Ligne 3 : Pilotage, Dématérialisation & Technique
            ("bar_chart", "CRM & Analytics", "indigo", "Suivi du CA et statistiques"),
            ("cloud_upload", "Passerelle Factur-X", "sky", "Export et envoi des PDF vers la plateforme"),
            ("settings_backup_restore", "Sauvegarde & Maintenance", "zinc", "Export/Import de la BDD et transfert PC"),
        ]

        with ui.grid(columns=3).classes("gap-6 max-w-5xl w-full px-4"):
            for icon, title, color, desc in modules:
                with ui.card().classes(
                    "p-6 cursor-pointer hover:shadow-lg transition-all duration-200 border border-slate-200 flex flex-col items-center text-center gap-3 bg-white hover:-translate-y-1"
                ).on("click", lambda t=title: set_page(t)):
                    ui.icon(icon, size="2.5rem").classes(f"text-{color}-600")
                    ui.label(title).classes("font-bold text-lg text-slate-800")
                    ui.label(desc).classes("text-xs text-slate-500")

# --- ZONE DE CONTENU DYNAMIQUE ---
@ui.refreshable
def content_area():
    if current_page == "Accueil":
        render_odoo_home()
    elif current_page == "CRM & Analytics":
        render_analytics()
    elif current_page == "Passerelle Factur-X":
        render_passerelle_export()  # Fonction du nouveau module !
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
    else:
        render_fallback()

def render_fallback():
    with ui.column().classes("gap-4"):
        ui.button("← Retour à l'accueil", icon="arrow_back", on_click=lambda: set_page("Accueil")).props("flat color=primary")
        ui.label(f"Module : {current_page}").classes("text-2xl font-bold text-slate-800")
        ui.label("Contenu en cours de développement...").classes("text-slate-500")

# En-tête fixe style Odoo
with ui.header().classes("bg-white border-b border-slate-200 px-6 py-3 flex justify-between items-center text-slate-800"):
    with ui.row().classes("items-center gap-4"):
        ui.button(icon="grid_view", on_click=lambda: set_page("Accueil")).props("flat round color=primary").tooltip("Menu Principal (Accueil)")
        ui.label("EasyFacture").classes("font-bold text-lg text-slate-800")
    ui.badge("v1.0").props("color=slate outline")

with ui.column().classes("w-full p-6 bg-slate-50 min-h-screen"):
    content_area()

if __name__ in {"__main__", "__mp_main__"}:
    # Si on tourne sous forme d'exécutable PyInstaller
    is_frozen = getattr(sys, 'frozen', False)
    
    ui.run(
        title="EasyFacture",
        port=8080,
        reload=not is_frozen,  # Désactive le reload automatique en mode .exe
        show=True,             # Ouvre automatiquement le navigateur / la fenêtre
    )