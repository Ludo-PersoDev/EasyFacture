from datetime import datetime
import os
import shutil
import tkinter as tk
from tkinter import filedialog
import zipfile
import database
from database import get_backup_path, save_backup_path
from nicegui import ui

# Nom exact de la base de données SQLite
DB_FILENAME = "FactureX.db"


def render_maintenance():
  ui.label("Sauvegarde & Maintenance").classes(
      "text-2xl font-bold text-slate-800 mb-6"
  )

  # --- 1. EMPLACEMENT DES SAUVEGARDES AUTOMATIQUES ---
  with ui.card().classes(
      "w-full p-6 bg-white border border-slate-200 rounded-xl space-y-4 mb-6"
      " shadow-sm"
  ):
    with ui.row().classes("items-center gap-3"):
      ui.icon("folder_special", size="32px", color="primary")
      with ui.column():
        ui.label("Emplacement des sauvegardes automatiques locales").classes(
            "text-lg font-bold text-slate-800"
        )
        ui.label(
            "Choisissez le dossier où EasyFacture enregistre les 8 derniers"
            " backups quotidiens."
        ).classes("text-xs text-slate-500")

    chemin_actuel = get_backup_path()
    input_dossier = (
        ui.input(
            label="Dossier de sauvegarde",
            value=chemin_actuel,
        )
        .classes("w-full")
        .props("outlined dense readonly")
    )

    def choisir_dossier():
      root = tk.Tk()
      root.withdraw()
      root.attributes("-topmost", True)
      dossier_selectionne = filedialog.askdirectory(
          title="Sélectionner le dossier de sauvegarde"
      )
      root.destroy()

      if dossier_selectionne:
        input_dossier.value = dossier_selectionne
        save_backup_path(dossier_selectionne)
        ui.notify("Nouvel emplacement enregistré !", type="positive")

    ui.button(
        "Parcourir...", icon="folder_open", on_click=choisir_dossier
    ).props("color=slate outline")

  # --- 2. EXPORT & RESTAURATION MANUELLE ---
  with ui.card().classes(
      "w-full p-6 bg-white border border-slate-200 rounded-xl space-y-4 mb-6"
      " shadow-sm"
  ):
    with ui.row().classes("items-center gap-3"):
      ui.icon("save_alt", size="32px", color="primary")
      with ui.column():
        ui.label("Sauvegarder ou Restaurer").classes(
            "text-lg font-bold text-slate-800"
        )
        ui.label(
            "Exportez manuellement vos données ou restaurez une version"
            " précédente à partir d'un fichier .zip."
        ).classes("text-xs text-slate-500")

    # A. EXPORTER
    def exporter_sauvegarde_complete():
      try:
        os.makedirs("backups", exist_ok=True)
        horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"backups/EasyFacture_Backup_{horodatage}.zip"

        with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
          if os.path.exists(DB_FILENAME):
            zipf.write(DB_FILENAME, arcname=DB_FILENAME)

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

    # B. RESTAURER DIRECTEMENT
    def restaurer_sauvegarde(e):
      try:
        # e.content donne accès au fichier téléversé par l'utilisateur
        with zipfile.ZipFile(e.content, "r") as zip_ref:
          # 1. Extraction directe et écrasement propre des données actuelles
          zip_ref.extractall(".")

        ui.notify(
            "Restauration réussie ! Rechargez la page.",
            type="positive",
            close_button="Recharger",
            on_dismiss=lambda: ui.navigate.reload(),
        )
      except Exception as err:
        ui.notify(
            f"Erreur lors de la restauration : {str(err)}", type="negative"
        )

    with ui.row().classes("gap-4 items-center"):
      ui.button(
          "Exporter (.zip)",
          icon="download",
          on_click=exporter_sauvegarde_complete,
      ).props("color=primary font-bold")

      ui.upload(
          label="Restaurer un fichier .zip",
          auto_upload=True,
          on_upload=restaurer_sauvegarde,
      ).props("accept=.zip flat color=warning").classes("max-w-xs")

  # --- 3. INFORMATIONS TECHNIQUES ---
  with ui.card().classes(
      "w-full p-6 bg-white border border-slate-200 rounded-xl space-y-4"
      " shadow-sm"
  ):
    ui.label("Informations Système").classes("text-lg font-bold text-slate-800")

    taille_bdd = "Introuvable"
    if os.path.exists(DB_FILENAME):
      taille = os.path.getsize(DB_FILENAME) / 1024
      taille_bdd = f"{taille:.2f} Ko"

    with ui.row().classes("gap-8 items-center justify-between w-full"):
      with ui.row().classes("gap-8"):
        with ui.column():
          ui.label("Version Logiciel").classes(
              "text-xs text-slate-400 font-bold"
          )
          ui.label("v1.0.0").classes("text-sm text-slate-700")
        with ui.column():
          ui.label("Base de données").classes(
              "text-xs text-slate-400 font-bold"
          )
          ui.label(f"{DB_FILENAME} ({taille_bdd})").classes(
              "text-sm text-slate-700"
          )
        with ui.column():
          ui.label("Moteur").classes("text-xs text-slate-400 font-bold")
          ui.label("Python & NiceGUI").classes("text-sm text-slate-700")

      # La petite touche "se jeter des fleurs" alignée à droite
      with ui.column().classes("items-end"):
        ui.label("Powered by").classes("text-[10px] text-slate-400 uppercase tracking-wider font-semibold")
        ui.label("FacturEx by LuA").classes("text-sm font-extrabold text-primary")