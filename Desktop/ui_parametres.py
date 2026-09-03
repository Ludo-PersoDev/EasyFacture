import asyncio
import os
from nicegui import ui
import database
# Assure-toi que ui_helpers ne contient pas d'autres imports vers app.py
from ui_helpers import afficher_note_importante
import subprocess
import platform
import glob

def render_parametres():
    params = database.recuperer_parametres()

    # --- ENTÊTE AVEC TITRE ET BOUTON D'INFO ---
    with ui.row().classes("w-full justify-between items-center mb-6"):
        ui.label("Paramètres de l'entreprise").classes("text-2xl font-bold text-slate-800")
        
        ui.button("Infos Importantes", icon="warning", on_click=lambda: afficher_note_importante(
            "Points d'attention - Paramètres",
            [
                "• Le nom de l'entreprise et le SIRET sont obligatoires pour débloquer la facturation.",
                "• Ces informations apparaîtront sur tous vos documents officiels (devis/factures).",
                "• Les envois de mails internes au logiciels ne sont fonctionnels qu'avec une adresse GMail équipée d'un mot de passe d'application"
            ],
            tuto_titre="Tuto : Mot de passe d'application Gmail",
            tuto_etapes=[
                "1. Activez la validation en 2 étapes sur votre compte Google.",
                "2. Allez dans Sécurité > Mots de passe d'application.",
                "3. Créez un mot de passe dédié à l'application.",
                "4. Copiez-le sans aucun espace dans le champ ci-dessous."
            ]
        )).props("flat color=amber")

    with ui.card().classes("w-full p-6 bg-white border border-slate-200 rounded-xl space-y-6"):
        
        # --- MISE EN PAGE GLOBALE EN 2 COLONNES ---
        with ui.row().classes("w-full gap-8 items-start"):
            
            # ================= COLONNE GAUCHE (Identité + Logo + Banque) =================
            with ui.column().classes("flex-1 gap-6"):
                
                ui.label("Identité & Image de Marque").classes("text-lg font-semibold text-slate-700 border-b pb-2 w-full")
                
                with ui.row().classes("w-full gap-4 items-start"):
                    with ui.column().classes("flex-1 gap-4"):
                        nom_input = ui.input("Nom / Raison Sociale", value=params.get("nom_entreprise", "")).classes("w-full")
                        adresse_input = ui.input("Adresse", value=params.get("adresse", "")).classes("w-full")
                        
                        with ui.row().classes("w-full gap-2"):
                            cp_input = ui.input("Code Postal", value=params.get("code_postal", "")).classes("w-1/3")
                            ville_input = ui.input("Ville", value=params.get("ville", "")).classes("w-2/3")

                    # S'assure que le dossier local assets existe
                    os.makedirs("assets", exist_ok=True)
                    logo_fixe = os.path.join("assets", "logo.png")
                    logo_path_holder = {"path": logo_fixe}

                    with ui.column().classes("w-44 items-center p-3 border-2 border-dashed border-slate-300 rounded-lg bg-slate-50 gap-2"):
                        ui.label("Logo").classes("text-xs font-medium text-slate-600")
                        
                        def ouvrir_logo():
                            chemin = logo_path_holder["path"]
                            if chemin and os.path.exists(chemin):
                                if platform.system() == "Darwin":       # macOS
                                    subprocess.run(["open", chemin])
                                elif platform.system() == "Windows":    # Windows
                                    os.startfile(chemin)
                                else:                                   # Linux
                                    subprocess.run(["xdg-open", chemin])
                            else:
                                ui.notify("Aucun fichier logo.png trouvé dans assets.", type="warning")

                        ui.button("Voir mon logo", icon="visibility", on_click=ouvrir_logo).props("flat size=xs color=primary").classes("w-full")

                        async def handle_upload(e):
                            if hasattr(e, 'content'):
                                if callable(getattr(e.content, 'read', None)):
                                    res = e.content.read()
                                    binary_data = await res if asyncio.iscoroutine(res) else res
                                else:
                                    binary_data = e.content
                            elif hasattr(e, 'file'):
                                res = e.file.read()
                                binary_data = await res if asyncio.iscoroutine(res) else res
                            else:
                                binary_data = getattr(e, 'buffer', b'')

                            try:
                                os.makedirs("assets", exist_ok=True)
                                # On force l'enregistrement sous le nom unique "logo.png"
                                local_path = os.path.join("assets", "logo.png")
                                with open(local_path, "wb") as f:
                                    f.write(binary_data)

                                logo_path_holder["path"] = local_path

                                # Synchronisation cloud en arrière-plan (optionnelle)
                                try:
                                    supabase = database.get_db()
                                    user_response = supabase.auth.get_user()
                                    user_id = user_response.user.id if user_response and user_response.user else "shared"
                                    storage_path = f"{user_id}/company_logo/logo.png"
                                    supabase.storage.from_("settings").upload(
                                        path=storage_path,
                                        file=binary_data,
                                        file_options={"upsert": "true", "content-type": "image/png"}
                                    )
                                except Exception:
                                    pass

                                ui.notify("logo.png mis à jour avec succès !", type="positive", icon="check")
                            except Exception as ex:
                                ui.notify(f"Erreur lors de l'enregistrement : {ex}", type="negative")

                        ui.upload(on_upload=handle_upload, auto_upload=True, max_files=1).props('accept=".png, .jpg, .jpeg" flat label="Changer"').classes("w-full text-xs")

                with ui.row().classes("w-full gap-4"):
                    tel_input = ui.input("Téléphone", value=params.get("telephone", "")).classes("flex-1")
                    email_input = ui.input("E-mail de contact", value=params.get("email", "")).classes("flex-1")

                ui.label("Coordonnées Bancaires").classes("text-lg font-semibold text-slate-700 border-b pb-2 w-full mt-4")
                with ui.row().classes("w-full gap-4"):
                    banque_input = ui.input("Banque", value=params.get("nom_banque", "")).classes("flex-1")
                    iban_input = ui.input("IBAN", value=params.get("iban", "")).classes("flex-2")
                    bic_input = ui.input("BIC / SWIFT", value=params.get("bic", "")).classes("flex-1")

            # ================= COLONNE DROITE (Immatriculation + SMTP) =================
            with ui.column().classes("flex-1 gap-6"):
                
                ui.label("Immatriculation & Fiscalité").classes("text-lg font-semibold text-slate-700 border-b pb-2 w-full")

                with ui.row().classes("w-full gap-4"):
                    siret_input = ui.input("SIRET", value=params.get("siret", "")).classes("flex-2")
                    rcs_input = ui.input("RCS", value=params.get("rcs", "")).classes("flex-2")
                    ape_input = ui.input("Code APE", value=params.get("ape", "")).classes("flex-1")

                with ui.column().classes("w-full gap-3 bg-slate-50 p-4 rounded-lg border border-slate-200"):
                    tva_exo_checkbox = ui.checkbox("Entreprise exonérée de TVA", value=bool(params.get("tva_exoneree", 1)))
                    mention_exo_input = ui.input("Mention légale d'exonération", value=params.get("mention_tva_exoneree", "TVA non applicable, art. 293 B du CGI")).classes("w-full")
                    num_tva_input = ui.input("N° TVA Intracommunautaire", value=params.get("num_tva", "")).classes("w-full")
                    
                    mention_exo_input.bind_visibility_from(tva_exo_checkbox, 'value')
                    num_tva_input.bind_visibility_from(tva_exo_checkbox, 'value', backward=lambda val: not val)

                ui.label("Configuration E-mail (SMTP)").classes("text-lg font-semibold text-slate-700 border-b pb-2 w-full mt-4")
                with ui.row().classes("w-full gap-4"):
                    smtp_server_input = ui.input("Serveur SMTP", value=params.get("smtp_server", "smtp.gmail.com")).classes("flex-2")
                    smtp_port_input = ui.input("Port SMTP", value=str(params.get("smtp_port", 587))).classes("flex-1")
                with ui.row().classes("w-full gap-4"):
                    smtp_user_input = ui.input("E-mail d'envoi", value=params.get("smtp_user", "")).classes("flex-1")
                    smtp_password_input = ui.input("Mot de passe d'application", value=params.get("smtp_password", ""), password=True, password_toggle_button=True).classes("flex-1")

                def enregistrer():
                    # --- SUPABASE : Préparation des données ---
                    data_payload = {
                        "nom_entreprise": nom_input.value,
                        "adresse": adresse_input.value,
                        "code_postal": cp_input.value,
                        "ville": ville_input.value,
                        "telephone": tel_input.value,
                        "email": email_input.value,
                        "siret": siret_input.value,
                        "rcs": rcs_input.value,
                        "ape": ape_input.value,
                        "tva_exoneree": int(tva_exo_checkbox.value),
                        "num_tva": num_tva_input.value,
                        "mention_tva_exoneree": mention_exo_input.value,
                        "nom_banque": banque_input.value,
                        "iban": iban_input.value,
                        "bic": bic_input.value,
                        "logo_path": logo_path_holder["path"],
                        "smtp_server": smtp_server_input.value,
                        "smtp_port": int(smtp_port_input.value or 587),
                        "smtp_user": smtp_user_input.value,
                        "smtp_password": smtp_password_input.value
                    }

                    supabase = database.get_client()
                    supabase.table("parametres").insert(data_payload).execute()
                    ui.notify("Paramètres sauvegardés !", type="positive")

                ui.button("Enregistrer les modifications", icon="save", on_click=enregistrer).props("color=primary size=lg").classes("w-full")