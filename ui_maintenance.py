from datetime import datetime
import os
import shutil
import tkinter as tk
from tkinter import filedialog
import zipfile
import database
from database import get_backup_path, save_backup_path, recuperer_parametres
from nicegui import ui
import version
import subprocess
import sys
import io

# Import du module Google Drive
try:
    import gdrive_backup
except ImportError:
    gdrive_backup = None

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

    # --- 2. SAUVEGARDE & RESTAURATION (LOCAL VS DISTANT) ---
    with ui.card().classes(
        "w-full p-6 bg-white border border-slate-200 rounded-xl space-y-4 mb-6"
        " shadow-sm"
    ):
        with ui.row().classes("items-center gap-3"):
            ui.icon("cloud_sync", size="32px", color="primary")
            with ui.column():
                ui.label("Sauvegarder ou Restaurer (Local & Cloud)").classes(
                    "text-lg font-bold text-slate-800"
                )
                ui.label(
                    "Gérez vos sauvegardes en local ou connectez-vous au Google Drive sécurisé par SIRET."
                ).classes("text-xs text-slate-500")

        # --- ONGLETS ---
        with ui.tabs().classes("w-full text-primary") as tabs:
            tab_sauvegarde = ui.tab("Sauvegarde", icon="cloud_upload")
            tab_restau_locale = ui.tab("Restauration Locale", icon="settings_backup_restore")
            tab_restau_distante = ui.tab("Restauration Cloud (Drive)", icon="history_edu")
            tab_audit = ui.tab("Journal d'Audit", icon="verified_user")

        with ui.tab_panels(tabs, value=tab_sauvegarde).classes("w-full pt-4"):
            
            # --- PANNEAU SAUVEGARDE (DOUBLE : LOCAL + CLOUD) ---
            with ui.tab_panel(tab_sauvegarde):
                with ui.column().classes("gap-4 w-full"):
                    ui.label("Créer une sauvegarde complète (Base de données + Documents PDF)").classes("text-sm text-slate-600")
                    
                    def executer_sauvegarde_complete():
                        try:
                            params = recuperer_parametres()
                            siret_brut = params.get("siret", "")
                            siret_propre = gdrive_backup.nettoyer_siret(siret_brut) if gdrive_backup else ""

                            if len(siret_propre) != 14:
                                ui.notify("Erreur : Veuillez renseigner un SIRET valide à 14 chiffres dans vos paramètres entreprise avant de sauvegarder sur le Cloud.", type="negative", timeout=6000)
                                return

                            dossier_backup = get_backup_path()
                            os.makedirs(dossier_backup, exist_ok=True)
                            
                            date_jour = datetime.now().strftime("%Y-%m-%d")
                            zip_filename = os.path.join(dossier_backup, f"EasyFacture_{date_jour}.zip")

                            # Écrasement direct si le fichier du jour existe déjà
                            if os.path.exists(zip_filename):
                                os.remove(zip_filename)

                            with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
                                if os.path.exists(DB_FILENAME):
                                    zipf.write(DB_FILENAME, arcname=DB_FILENAME)

                                if os.path.exists("exports"):
                                    for root, dirs, files in os.walk("exports"):
                                        for file in files:
                                            full_path = os.path.join(root, file)
                                            rel_path = os.path.relpath(full_path, ".")
                                            zipf.write(full_path, arcname=rel_path)

                            ui.notify("Sauvegarde locale créée avec succès !", type="positive")
                            
                            if gdrive_backup:
                                try:
                                    gdrive_backup.pousser_sauvegarde_vers_drive(zip_filename, siret_propre)
                                    ui.notify(f"Sauvegarde envoyée sur Google Drive (Dossier SIRET : {siret_propre}) !", type="positive", icon="cloud_done")
                                except Exception as g_err:
                                    ui.notify(f"Sauvegarde locale OK, mais échec Google Drive : {g_err}", type="warning")

                            ui.download(zip_filename)
                        except Exception as e:
                            ui.notify(f"Erreur lors de la sauvegarde : {str(e)}", type="negative")

                    ui.button(
                        "Lancer la sauvegarde (Local & Drive)",
                        icon="save_alt",
                        on_click=executer_sauvegarde_complete,
                    ).props("color=primary font-bold")

            # --- PANNEAU RESTAURATION LOCALE (AVEC GARDE-FOU) ---
            with ui.tab_panel(tab_restau_locale):
                with ui.column().classes("gap-4 w-full"):
                    ui.label("Remplacer vos données actuelles à partir d'un fichier .zip stocké sur votre machine.").classes("text-sm text-slate-600")
                    
                    def ouvrir_modal_gardefou_local(e):
                        filename = getattr(e.file, 'name', 'Fichier local .zip')
                        
                        with ui.dialog() as dialog, ui.card().classes("w-[450px] p-6 space-y-4"):
                            ui.label("⚠️ Sécurité & Traçabilité - Restauration Locale").classes("text-lg font-bold text-amber-600")
                            ui.label(f"Vous vous apprêtez à restaurer le fichier : {filename}.\nCette action va écraser les données actuelles.").classes("text-xs text-slate-600")
                            
                            input_nom = ui.input("Nom de l'intervenant").classes("w-full").props("outlined dense required")
                            input_prenom = ui.input("Prénom de l'intervenant").classes("w-full").props("outlined dense required")
                            input_motif = ui.textarea("Motif de la restauration (ex: Maintenance, bascule de poste...)").classes("w-full").props("outlined dense required")

                            async def valider_et_restaurer_local():
                                if not input_nom.value or not input_prenom.value or not input_motif.value:
                                    ui.notify("Veuillez remplir tous les champs (Nom, Prénom, Motif).", type="warning")
                                    return

                                dialog.close()
                                try:
                                    donnees_binaires = await e.file.read()
                                    contenu_flux = io.BytesIO(donnees_binaires)
                                    
                                    with zipfile.ZipFile(contenu_flux, "r") as zip_ref:
                                        zip_ref.extractall(".")

                                    # Traçabilité et indexation des compteurs post-restauration
                                    conn = database.get_conn()
                                    cursor = conn.cursor()
                                    
                                    dernier_devis = "N/A"
                                    dernier_facture = "N/A"
                                    derniere_intervention = "N/A"
                                    try:
                                        dernier_devis = cursor.execute("SELECT numero_devis FROM devis ORDER BY id DESC LIMIT 1").fetchone()[0] or "Aucun"
                                    except Exception:
                                        pass
                                    try:
                                        dernier_facture = cursor.execute("SELECT numero_facture FROM factures ORDER BY id DESC LIMIT 1").fetchone()[0] or "Aucune"
                                    except Exception:
                                        pass
                                    try:
                                        derniere_intervention = cursor.execute("SELECT numero_intervention FROM interventions ORDER BY id DESC LIMIT 1").fetchone()[0] or "Aucune"
                                    except Exception:
                                        pass

                                    motif_complet = f"{input_motif.value} [Dernier Devis: {dernier_devis} | Dernière Facture: {dernier_facture} | Dernière Interv: {derniere_intervention}]"

                                    conn.execute("""
                                        INSERT INTO restaurations_log (nom, prenom, motif, nom_fichier_restore)
                                        VALUES (?, ?, ?, ?)
                                    """, (input_nom.value, input_prenom.value, motif_complet, f"[LOCAL] {filename}"))
                                    conn.commit()

                                    # Backup immédiat post-restauration unifié
                                    dossier_backup = get_backup_path()
                                    os.makedirs(dossier_backup, exist_ok=True)
                                    date_jour = datetime.now().strftime('%Y-%m-%d')
                                    secours_zip_path = os.path.join(dossier_backup, f"EasyFacture_{date_jour}.zip")
                                    
                                    if os.path.exists(secours_zip_path):
                                        os.remove(secours_zip_path)
                                    
                                    with zipfile.ZipFile(secours_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                                        if os.path.exists(DB_FILENAME):
                                            zipf.write(DB_FILENAME, arcname=DB_FILENAME)
                                        if os.path.exists("exports"):
                                            for root, dirs, files in os.walk("exports"):
                                                for file in files:
                                                    full_path = os.path.join(root, file)
                                                    rel_path = os.path.relpath(full_path, ".")
                                                    zipf.write(full_path, arcname=rel_path)

                                    if gdrive_backup:
                                        try:
                                            params = recuperer_parametres()
                                            siret_propre = gdrive_backup.nettoyer_siret(params.get("siret", ""))
                                            if len(siret_propre) == 14:
                                                gdrive_backup.pousser_sauvegarde_vers_drive(secours_zip_path, siret_propre)
                                        except Exception as g_err:
                                            print(f"Alerte push secours post-restore Drive : {g_err}")

                                    conn.close()

                                    ui.notify(
                                        "Restauration locale réussie, tracée et sécurisée ! Rechargement...",
                                        type="positive",
                                        close_button="Recharger",
                                        on_dismiss=lambda: ui.navigate.reload(),
                                    )
                                except Exception as err:
                                    ui.notify(
                                        f"Erreur lors de la restauration : {str(err)}", type="negative"
                                    )

                            with ui.row().classes("w-full justify-end gap-2 mt-4"):
                                ui.button("Annuler", on_click=dialog.close).props("flat color=slate")
                                ui.button("Confirmer la restauration", on_click=valider_et_restaurer_local).props("color=amber-800 font-bold")

                        dialog.open()

                    ui.upload(
                        label="Sélectionner un fichier .zip local",
                        auto_upload=True,
                        on_upload=ouvrir_modal_gardefou_local,
                    ).props("accept=.zip flat color=warning").classes("max-w-md")

            # --- PANNEAU RESTAURATION DISTANTE (GOOGLE DRIVE) ---
            with ui.tab_panel(tab_restau_distante):
                with ui.column().classes("gap-4 w-full"):
                    ui.label("Récupérez vos sauvegardes de secours (en cas de crash PC par exemple) filtrées par votre numéro SIRET.").classes("text-sm text-slate-600")

                    container_liste_drive = ui.column().classes("w-full gap-2")

                    def charger_liste_drive():
                        container_liste_drive.clear()
                        if not gdrive_backup:
                            with container_liste_drive:
                                ui.label("Module Google Drive indisponible.").classes("text-red-500")
                            return

                        params = recuperer_parametres()
                        siret_brut = params.get("siret", "")
                        siret_propre = gdrive_backup.nettoyer_siret(siret_brut)

                        if len(siret_propre) != 14:
                            with container_liste_drive:
                                ui.card().classes("w-full p-4 bg-red-50 border border-red-200 rounded-lg")
                                ui.label("⚠️ Renseigner un SIRET valide (14 chiffres) dans vos paramètres avant de récupérer vos données.").classes("text-sm text-red-600 font-bold")
                            return

                        try:
                            ui.notify(f"Interrogation du Google Drive pour le SIRET {siret_propre}...", type="info")
                            fichiers = gdrive_backup.lister_sauvegardes_drive_par_siret(siret_propre)
                            
                            if not fichiers:
                                with container_liste_drive:
                                    ui.label(f"Aucune sauvegarde trouvée sur le Google Drive pour le SIRET {siret_propre}.").classes("italic text-slate-500")
                                return

                            with container_liste_drive:
                                ui.label(f"{len(fichiers)} sauvegarde(s) disponible(s) pour le SIRET {siret_propre} :").classes("font-semibold text-xs text-slate-500 mb-2")
                                
                                for f in fichiers:
                                    nom_f = f.get('name')
                                    file_id = f.get('id')
                                    taille_Mo = int(f.get('size', 0)) / (1024 * 1024) if 'size' in f else 0
                                    date_c = f.get('createdTime', 'Date inconnue')

                                    with ui.row().classes("w-full justify-between items-center p-3 bg-slate-50 border rounded-lg"):
                                        with ui.column():
                                            ui.label(nom_f).classes("font-bold text-sm text-slate-800")
                                            ui.label(f"Taille : {taille_Mo:.2f} Mo | Créé le : {date_c}").classes("text-xs text-slate-500")
                                        
                                        ui.button("Restaurer", icon="restore", on_click=lambda fid=file_id, fn=nom_f: ouvrir_modal_gardefou_drive(fid, fn)).props("color=warning dense")

                        except Exception as e:
                            with container_liste_drive:
                                ui.label(f"Erreur de connexion au Drive : {str(e)}").classes("text-red-500 text-xs")

                    def ouvrir_modal_gardefou_drive(file_id, filename):
                        with ui.dialog() as dialog, ui.card().classes("w-[450px] p-6 space-y-4"):
                            ui.label("⚠️ Sécurité & Traçabilité - Restauration Cloud").classes("text-lg font-bold text-red-600")
                            ui.label(f"Vous vous apprêtez à restaurer le fichier : {filename}.\nCette action va écraser les données actuelles.").classes("text-xs text-slate-600")
                            
                            input_nom = ui.input("Nom de l'intervenant").classes("w-full").props("outlined dense required")
                            input_prenom = ui.input("Prénom de l'intervenant").classes("w-full").props("outlined dense required")
                            input_motif = ui.textarea("Motif de la restauration (ex: PC planté, BDD corrompue...)").classes("w-full").props("outlined dense required")

                            def valider_et_restaurer_drive():
                                if not input_nom.value or not input_prenom.value or not input_motif.value:
                                    ui.notify("Veuillez remplir tous les champs (Nom, Prénom, Motif).", type="warning")
                                    return

                                dialog.close()
                                ui.notify("Téléchargement de la sauvegarde depuis le Drive...", type="info")
                                
                                chemin_temp = "temp_restore.zip"
                                succes = gdrive_backup.telecharger_sauvegarde_drive(file_id, chemin_temp)
                                
                                if not succes:
                                    ui.notify("Échec du téléchargement depuis le Google Drive.", type="negative")
                                    return

                                try:
                                    with zipfile.ZipFile(chemin_temp, "r") as zip_ref:
                                        zip_ref.extractall(".")
                                    
                                    if os.path.exists(chemin_temp):
                                        os.remove(chemin_temp)

                                    # Traçabilité et indexation des compteurs post-restauration
                                    conn = database.get_conn()
                                    cursor = conn.cursor()
                                    
                                    dernier_devis = "N/A"
                                    dernier_facture = "N/A"
                                    derniere_intervention = "N/A"
                                    try:
                                        dernier_devis = cursor.execute("SELECT numero_devis FROM devis ORDER BY id DESC LIMIT 1").fetchone()[0] or "Aucun"
                                    except Exception:
                                        pass
                                    try:
                                        dernier_facture = cursor.execute("SELECT numero_facture FROM factures ORDER BY id DESC LIMIT 1").fetchone()[0] or "Aucune"
                                    except Exception:
                                        pass
                                    try:
                                        derniere_intervention = cursor.execute("SELECT numero_intervention FROM interventions ORDER BY id DESC LIMIT 1").fetchone()[0] or "Aucune"
                                    except Exception:
                                        pass

                                    motif_complet = f"{input_motif.value} [Dernier Devis: {dernier_devis} | Dernière Facture: {dernier_facture} | Dernière Interv: {derniere_intervention}]"

                                    conn.execute("""
                                        INSERT INTO restaurations_log (nom, prenom, motif, nom_fichier_restore)
                                        VALUES (?, ?, ?, ?)
                                    """, (input_nom.value, input_prenom.value, motif_complet, filename))
                                    conn.commit()

                                    # Backup immédiat post-restauration unifié
                                    dossier_backup = get_backup_path()
                                    os.makedirs(dossier_backup, exist_ok=True)
                                    date_jour = datetime.now().strftime('%Y-%m-%d')
                                    secours_zip_path = os.path.join(dossier_backup, f"EasyFacture_{date_jour}.zip")
                                    
                                    if os.path.exists(secours_zip_path):
                                        os.remove(secours_zip_path)
                                        
                                    with zipfile.ZipFile(secours_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                                        if os.path.exists(DB_FILENAME):
                                            zipf.write(DB_FILENAME, arcname=DB_FILENAME)
                                        if os.path.exists("exports"):
                                            for root, dirs, files in os.walk("exports"):
                                                for file in files:
                                                    full_path = os.path.join(root, file)
                                                    rel_path = os.path.relpath(full_path, ".")
                                                    zipf.write(full_path, arcname=rel_path)

                                    if gdrive_backup:
                                        try:
                                            params = recuperer_parametres()
                                            siret_propre = gdrive_backup.nettoyer_siret(params.get("siret", ""))
                                            if len(siret_propre) == 14:
                                                gdrive_backup.pousser_sauvegarde_vers_drive(secours_zip_path, siret_propre)
                                        except Exception as g_err:
                                            print(f"Alerte push secours post-restore Drive : {g_err}")

                                    conn.close()

                                    ui.notify(
                                        "Restauration Cloud réussie, tracée et sécurisée ! Rechargement...",
                                        type="positive",
                                        close_button="Recharger",
                                        on_dismiss=lambda: ui.navigate.reload(),
                                    )
                                except Exception as err:
                                    ui.notify(f"Erreur critique lors de l'application de la sauvegarde : {err}", type="negative")

                            with ui.row().classes("w-full justify-end gap-2 mt-4"):
                                ui.button("Annuler", on_click=dialog.close).props("flat color=slate")
                                ui.button("Confirmer la restauration", on_click=valider_et_restaurer_drive).props("color=negative font-bold")

                        dialog.open()

                    ui.button("Lister les sauvegardes du Drive (par SIRET)", icon="refresh", on_click=charger_liste_drive).props("color=primary outline")

            # --- PANNEAU JOURNAL D'AUDIT (LECTURE SEULE & EXPORT) ---
            with ui.tab_panel(tab_audit):
                with ui.column().classes("gap-4 w-full"):
                    ui.label("Historique immuable de toutes les restaurations effectuées (Locale & Cloud)").classes("text-sm text-slate-600")

                    container_table_audit = ui.column().classes("w-full")

                    def charger_journal_audit():
                        container_table_audit.clear()
                        try:
                            conn = database.get_conn()
                            cursor = conn.cursor()
                            cursor.execute("SELECT date_restauration, nom, prenom, motif, nom_fichier_restore FROM restaurations_log ORDER BY id DESC")
                            lignes = cursor.fetchall()
                            conn.close()

                            if not lignes:
                                with container_table_audit:
                                    ui.label("Aucune restauration enregistrée pour le moment.").classes("italic text-slate-400")
                                return

                            with container_table_audit:
                                columns = [
                                    {"name": "date", "label": "Date & Heure", "field": "date", "sortable": True},
                                    {"name": "intervenant", "label": "Intervenant", "field": "intervenant", "sortable": True},
                                    {"name": "motif", "label": "Motif & Index Pièces", "field": "motif"},
                                    {"name": "fichier", "label": "Fichier restauré", "field": "fichier"},
                                ]
                                rows = []
                                for l in lignes:
                                    rows.append({
                                        "date": l["date_restauration"],
                                        "intervenant": f"{l['prenom']} {l['nom']}",
                                        "motif": l["motif"],
                                        "fichier": l["nom_fichier_restore"]
                                    })

                                ui.table(columns=columns, rows=rows, row_key="date").classes("w-full")

                                def exporter_csv_audit():
                                    try:
                                        import csv
                                        os.makedirs("exports", exist_ok=True)
                                        csv_path = "exports/journal_audit_restaurations.csv"
                                        with open(csv_path, mode="w", newline="", encoding="utf-8-sig") as f:
                                            writer = csv.writer(f)
                                            writer.writerow(["Date", "Nom", "Prenom", "Motif", "Fichier"])
                                            for l in lignes:
                                                writer.writerow([l["date_restauration"], l["nom"], l["prenom"], l["motif"], l["nom_fichier_restore"]])
                                        ui.download(csv_path)
                                        ui.notify("Journal exporté avec succès !", type="positive")
                                    except Exception as ex:
                                        ui.notify(f"Erreur export CSV : {ex}", type="negative")

                                ui.button("Exporter le journal (CSV)", icon="download", on_click=exporter_csv_audit).props("color=slate outline dense mt-2")

                        except Exception as e:
                            with container_table_audit:
                                ui.label(f"Erreur de lecture du journal : {e}").classes("text-red-500 text-xs")

                    tab_audit.on('click', charger_journal_audit)
                    ui.button("Actualiser le journal", icon="refresh", on_click=charger_journal_audit).props("color=primary outline dense")

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

        def verifier_maj_manuelle():
            ui.notify("Vérification des mises à jour en cours...", type="info")
            try:
                subprocess.Popen([sys.executable, "launcher.pyw", "--check-update"])
            except Exception:
                ui.notify("Impossible de lancer la vérification.", type="negative")

        with ui.row().classes("gap-8 items-center justify-between w-full"):
            with ui.row().classes("gap-8 items-center"):
                with ui.column():
                    ui.label("Version Logiciel").classes(
                        "text-xs text-slate-400 font-bold"
                    )
                    ui.label(f"v{version.VERSION}").classes("text-sm text-slate-700")
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
                
                with ui.column():
                    ui.button("Vérifier les mises à jour", icon="system_update", on_click=verifier_maj_manuelle).props("outline color=primary dense")

            with ui.column().classes("items-end"):
                ui.label("Powered by").classes("text-[10px] text-slate-400 uppercase tracking-wider font-semibold")
                ui.label("FacturEx by LuA").classes("text-sm font-extrabold text-primary")