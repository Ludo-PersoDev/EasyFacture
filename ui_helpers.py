from nicegui import ui
import subprocess
import os
import urllib.request
import threading

def afficher_note_importante(titre, contenu_liste, tuto_titre=None, tuto_etapes=None):
    """Affiche une modale avec des points d'attention stylisés et un encadré bleu optionnel."""
    with ui.dialog() as dialog, ui.card().classes("w-[90vw] max-w-lg p-6 space-y-4"):
        ui.label(titre).classes("text-xl font-bold text-slate-800")
        ui.separator()
        
        # Points d'attention généraux avec un style plus punchy (couleur ambre/jaune)
        with ui.column().classes("gap-2"):
            for point in contenu_liste:
                with ui.row().classes("items-start gap-2"):
                    # Petit point ou icône colorée pour donner du punch
                    ui.icon("warning", color="amber", size="xs").classes("mt-1")
                    ui.label(point).classes("text-sm font-semibold text-amber-900")
                
        # Bloc tuto encadré sur fond bleu (s'il y en a un)
        if tuto_etapes:
            with ui.column().classes("w-full bg-blue-50 p-4 rounded-lg border border-blue-200 gap-2 mt-2"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("info", color="blue", size="sm")
                    ui.label(tuto_titre or "Tutoriel").classes("text-sm font-bold text-blue-900")
                
                with ui.column().classes("gap-1 pl-2"):
                    for etape in tuto_etapes:
                        ui.label(etape).classes("text-xs text-blue-800")
        
        ui.button("J'ai compris", on_click=dialog.close).props("color=primary w-full")
    dialog.open()

def lancer_assistance_technique():
    """Vérifie la présence de HopToDesk, le télécharge et l'installe si besoin avec un loader."""
    chemins_possibles = [
        r"C:\Program Files\HopToDesk\HopToDesk.exe",
        r"C:\Program Files (x86)\HopToDesk\HopToDesk.exe",
        os.path.join(os.environ.get("USERPROFILE", ""), r"Downloads\HopToDesk.exe")
    ]
    
    # 1. On vérifie s'il est déjà présent sur le poste
    for chemin in chemins_possibles:
        if os.path.exists(chemin):
            try:
                subprocess.Popen(chemin)
                ui.notify("Lancement de HopToDesk en cours...", type="positive")
                return
            except Exception as e:
                ui.notify(f"Erreur de lancement : {e}", type="negative")
                return

    # 2. Si absent, on affiche une modale de téléchargement/patientement
    with ui.dialog() as dialog, ui.card().classes("w-80 p-6 items-center text-center gap-4"):
        ui.spinner("audio", size="3rem", color="primary")
        ui.label("Module d'assistance introuvable").classes("font-bold text-lg text-slate-800")
        ui.label("Téléchargement et configuration de HopToDesk en cours, veuillez patienter...").classes("text-xs text-slate-500")
    
    dialog.open()

    def tache_telechargement():
        try:
            # Lien officiel direct du client HopToDesk Windows (ou remplace par ton lien direct si besoin)
            url_hoptodesk = "https://hoptodesk.com/download/hoptodesk.exe"
            
            # On le télécharge dans le dossier Téléchargements ou un dossier temporaire
            dossier_telechargement = os.path.join(os.environ.get("USERPROFILE", "C:"), "Downloads")
            os.makedirs(dossier_telechargement, exist_ok=True)
            chemin_cible = os.path.join(dossier_telechargement, "HopToDesk.exe")
            
            # Téléchargement du fichier
            urllib.request.urlretrieve(url_hoptodesk, chemin_cible)
            
            # Fermeture de la modale
            dialog.close()
            
            # Lancement de l'outil fraîchement téléchargé
            if os.path.exists(chemin_cible):
                subprocess.Popen(chemin_cible)
                ui.notify("HopToDesk prêt et lancé avec succès !", type="positive")
            else:
                ui.notify("Erreur lors de la récupération du fichier.", type="negative")
                
        except Exception as e:
            dialog.close()
            ui.notify(f"Échec du téléchargement automatique : {e}", type="negative")

    # Exécution dans un thread séparé pour ne pas figer l'interface NiceGUI pendant le téléchargement
    threading.Thread(target=tache_telechargement, daemon=True).start()