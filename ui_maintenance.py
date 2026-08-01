from datetime import datetime
import os
import shutil
import zipfile
import database
from nicegui import ui

# Nom exact de ta base de données SQLite
DB_FILENAME = "FactureX.db"


def render_maintenance():
  ui.label("Sauvegarde & Maintenance").classes(
      "text-2xl font-bold text-slate-800 mb-6"
  )

  # --- 1. SAUVEGARDE COMPLÈTE ---
  with ui.card().classes(
      "w-full p-6 bg-white border border-slate-200 rounded-xl space-y-4 mb-6"
      " shadow-sm"
  ):
    with ui.row().classes("items-center gap-3"):
      ui.icon("save_alt", size="32px", color="primary")
      with ui.column():
        ui.label("Sauvegarder les données de l'application").classes(
            "text-lg font-bold text-slate-800"
        )
        ui.label(
            "Générez une sauvegarde complète (base de données FactureX.db +"
            " factures PDF) pour changer de PC ou créer un backup."
        ).classes("text-xs text-slate-500")

    def exporter_sauvegarde_complete():
      try:
        os.makedirs("backups", exist_ok=True)
        horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"backups/FactureX_Backup_{horodatage}.zip"

        with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
          # Ingestion explicite de la base FactureX.db
          if os.path.exists(DB_FILENAME):
            zipf.write(DB_FILENAME, arcname=DB_FILENAME)
          else:
            ui.notify(
                f"Fichier {DB_FILENAME} introuvable à la racine.",
                type="warning",
            )

          # Ingestion du dossier exports (Factures et Devis PDF)
          if os.path.exists("exports"):
            for root, dirs, files in os.walk("exports"):
              for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, ".")
                zipf.write(full_path, arcname=rel_path)

        ui.notify("Sauvegarde créée avec succès !", type="positive")
        ui.download(zip_filename)
      except Exception as e:
        ui.notify(f"Erreur lors de la sauvegarde : {str(e)}", type="negative")

    ui.button(
        "Exporter la sauvegarde (.zip)",
        icon="download",
        on_click=exporter_sauvegarde_complete,
    ).props("color=primary font-bold")

  # --- 2. INFORMATIONS TECHNIQUES ---
  with ui.card().classes(
      "w-full p-6 bg-white border border-slate-200 rounded-xl space-y-4"
      " shadow-sm"
  ):
    ui.label("Informations Système").classes("text-lg font-bold text-slate-800")

    taille_bdd = "Introuvable"
    if os.path.exists(DB_FILENAME):
      taille = os.path.getsize(DB_FILENAME) / 1024
      taille_bdd = f"{taille:.2f} Ko"

    with ui.row().classes("gap-8"):
      with ui.column():
        ui.label("Version Logiciel").classes("text-xs text-slate-400 font-bold")
        ui.label("v1.0.0").classes("text-sm text-slate-700")
      with ui.column():
        ui.label("Base de données").classes("text-xs text-slate-400 font-bold")
        ui.label(f"{DB_FILENAME} ({taille_bdd})").classes(
            "text-sm text-slate-700"
        )
      with ui.column():
        ui.label("Moteur").classes("text-xs text-slate-400 font-bold")
        ui.label("Python & NiceGUI").classes("text-sm text-slate-700")