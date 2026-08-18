# ui_parametres.py
import asyncio
import os
from nicegui import ui
import database
# Assure-toi que ui_helpers ne contient pas d'autres imports vers app.py
from ui_helpers import afficher_note_importante

def render_parametres():
    params = database.recuperer_parametres()

    # --- ENTÊTE AVEC TITRE ET BOUTON D'INFO ---
    with ui.row().classes("w-full justify-between items-center mb-6"):
        ui.label("Paramètres de l'entreprise").classes("text-2xl font-bold text-slate-800")
        
        ui.button("Infos Importantes", icon="warning", on_click=lambda: afficher_note_importante(
            "Points d'attention - Paramètres",
            [
                "Le nom de l'entreprise et le SIRET sont obligatoires pour débloquer la facturation.",
                "Ces informations apparaîtront sur tous vos documents officiels (devis/factures).",
                "Les envois de mails internes au logiciels ne sont fonctionnels qu'avec une adresse GMail équipée d'un mot de passe d'application"
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

                    logo_path_holder = {"path": params.get("logo_path", "")}
                    with ui.column().classes("w-44 items-center p-3 border-2 border-dashed border-slate-300 rounded-lg bg-slate-50 gap-2"):
                        ui.label("Logo").classes("text-xs font-medium text-slate-600")
                        
                        logo_container = ui.column().classes("w-full items-center justify-center min-h-[50px]")

                        def rafraichir_apercu_logo():
                            logo_container.clear()
                            with logo_container:
                                if logo_path_holder["path"] and os.path.exists(logo_path_holder["path"]):
                                    ui.image(logo_path_holder["path"]).classes("max-h-14 object-contain rounded")
                                    ui.button("Supprimer", icon="delete", on_click=supprimer_logo).props("flat color=negative size=xs")
                                else:
                                    ui.label("Aucun logo").classes("text-[10px] text-slate-400 italic")

                        async def handle_upload(e):
                            os.makedirs("assets", exist_ok=True)
                            nom_fichier = getattr(e, 'name', None) or getattr(getattr(e, 'content', None), 'name', 'logo.png')
                            
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

                            file_path = os.path.join("assets", nom_fichier)
                            with open(file_path, "wb") as f:
                                f.write(binary_data)
                            
                            logo_path_holder["path"] = file_path
                            rafraichir_apercu_logo()
                            ui.notify("Logo importé !", type="positive", icon="cloud_done")

                        def supprimer_logo():
                            logo_path_holder["path"] = ""
                            rafraichir_apercu_logo()
                            ui.notify("Logo retiré.", type="info")

                        rafraichir_apercu_logo()
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
                    mention_exo_input.bind_enabled_from(tva_exo_checkbox, 'value')
                    num_tva_input.bind_enabled_from(tva_exo_checkbox, 'value', backward=lambda val: not val)

                ui.label("Configuration E-mail (SMTP)").classes("text-lg font-semibold text-slate-700 border-b pb-2 w-full mt-4")
                with ui.row().classes("w-full gap-4"):
                    smtp_server_input = ui.input("Serveur SMTP", value=params.get("smtp_server", "smtp.gmail.com")).classes("flex-2")
                    smtp_port_input = ui.input("Port SMTP", value=str(params.get("smtp_port", 587))).classes("flex-1")
                with ui.row().classes("w-full gap-4"):
                    smtp_user_input = ui.input("E-mail d'envoi", value=params.get("smtp_user", "")).classes("flex-1")
                    smtp_password_input = ui.input("Mot de passe d'application", value=params.get("smtp_password", ""), password=True, password_toggle_button=True).classes("flex-1")

                def enregistrer():
                    conn = database.get_conn()
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE parametres SET nom_entreprise=?, adresse=?, code_postal=?, ville=?, telephone=?, email=?, siret=?, rcs=?, ape=?, tva_exoneree=?, num_tva=?, mention_tva_exoneree=?, nom_banque=?, iban=?, bic=?, logo_path=?, smtp_server=?, smtp_port=?, smtp_user=?, smtp_password=?
                        WHERE id = 1
                    """, (nom_input.value, adresse_input.value, cp_input.value, ville_input.value, tel_input.value, email_input.value, siret_input.value, rcs_input.value, ape_input.value, int(tva_exo_checkbox.value), num_tva_input.value, mention_exo_input.value, banque_input.value, iban_input.value, bic_input.value, logo_path_holder["path"], smtp_server_input.value, int(smtp_port_input.value or 587), smtp_user_input.value, smtp_password_input.value))
                    conn.commit()
                    conn.close()
                    ui.notify("Paramètres sauvegardés !", type="positive")

                ui.button("Enregistrer les modifications", icon="save", on_click=enregistrer).props("color=primary size=lg").classes("w-full")