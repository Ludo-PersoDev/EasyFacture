import asyncio
import os
from nicegui import ui
import database

def render_parametres():
    # Chargement des données actuelles depuis SQLite
    params = database.recuperer_parametres()

    ui.label("Paramètres de l'entreprise").classes("text-2xl font-bold text-slate-800 mb-6")

    # Conteneur principal
    with ui.card().classes("w-full p-6 bg-white border border-slate-200 rounded-xl space-y-6"):
        
        # --- SECTION 1 : IDENTITÉ & LOGO ---
        ui.label("Identité & Image de Marque").classes("text-lg font-semibold text-slate-700 border-b pb-2 w-full")
        
        with ui.row().classes("w-full gap-8 items-start"):
            # Formulaire Identité
            with ui.column().classes("flex-1 gap-4"):
                nom_input = ui.input("Nom / Raison Sociale", value=params.get("nom_entreprise", "")).classes("w-full")
                adresse_input = ui.input("Adresse", value=params.get("adresse", "")).classes("w-full")
                
                with ui.row().classes("w-full gap-4"):
                    cp_input = ui.input("Code Postal", value=params.get("code_postal", "")).classes("w-1/3")
                    ville_input = ui.input("Ville", value=params.get("ville", "")).classes("w-2/3")

                with ui.row().classes("w-full gap-4"):
                    tel_input = ui.input("Téléphone", value=params.get("telephone", "")).classes("w-1/2")
                    email_input = ui.input("E-mail de contact", value=params.get("email", "")).classes("w-1/2")

            # Encadrement & Gestion du Logo
            logo_path_holder = {"path": params.get("logo_path", "")}

            with ui.column().classes("w-64 items-center p-4 border-2 border-dashed border-slate-300 rounded-lg bg-slate-50 gap-3"):
                ui.label("Logo de l'entreprise").classes("text-sm font-medium text-slate-600")
                
                # Zone d'affichage du logo
                logo_container = ui.column().classes("w-full items-center justify-center min-h-[100px]")

                def rafraichir_apercu_logo():
                    logo_container.clear()
                    with logo_container:
                        if logo_path_holder["path"] and os.path.exists(logo_path_holder["path"]):
                            ui.image(logo_path_holder["path"]).classes("max-h-24 object-contain rounded")
                            ui.button("Supprimer le logo", icon="delete", on_click=supprimer_logo).props("flat color=negative size=sm")
                        else:
                            ui.label("Aucun logo sélectionné").classes("text-xs text-slate-400 italic")

                async def handle_upload(e):
                    os.makedirs("assets", exist_ok=True)
                    
                    # 1. Récupération du nom de fichier
                    nom_fichier = getattr(e, 'name', None) or getattr(getattr(e, 'content', None), 'name', 'logo.png')
                    
                    # 2. Lecture asynchrone du contenu binaire
                    if hasattr(e, 'content'):
                        if callable(getattr(e.content, 'read', None)):
                            res = e.content.read()
                            # Si c'est une coroutine (NiceGUI récent), on l'attend avec await
                            if asyncio.iscoroutine(res):
                                binary_data = await res
                            else:
                                binary_data = res
                        else:
                            binary_data = e.content
                    elif hasattr(e, 'file'):
                        res = e.file.read()
                        binary_data = await res if asyncio.iscoroutine(res) else res
                    else:
                        binary_data = getattr(e, 'buffer', b'')

                    # 3. Sauvegarde du fichier sur le disque
                    file_path = os.path.join("assets", nom_fichier)
                    with open(file_path, "wb") as f:
                        f.write(binary_data)
                    
                    # 4. Mise à jour de l'affichage
                    logo_path_holder["path"] = file_path
                    rafraichir_apercu_logo()
                    ui.notify("Logo importé avec succès !", type="positive", icon="cloud_done")

                def supprimer_logo():
                    logo_path_holder["path"] = ""
                    rafraichir_apercu_logo()
                    ui.notify("Logo retiré.", type="info")

                rafraichir_apercu_logo()

                # Bouton d'upload NiceGUI
                ui.upload(
                    on_upload=handle_upload, 
                    auto_upload=True, 
                    max_files=1
                ).props('accept=".png, .jpg, .jpeg" flat label="Changer le logo"').classes("w-full")

        # --- SECTION 2 : IMMATRICULATION & FISCALITÉ ---
        ui.label("Immatriculation & Fiscalité").classes("text-lg font-semibold text-slate-700 border-b pb-2 w-full mt-4")

        with ui.row().classes("w-full gap-4"):
            siret_input = ui.input("SIRET", value=params.get("siret", "")).classes("w-1/3")
            rcs_input = ui.input("RCS", value=params.get("rcs", "")).classes("w-1/3")
            ape_input = ui.input("Code APE / NAF", value=params.get("ape", "")).classes("w-1/3")

        with ui.column().classes("w-full gap-4 bg-slate-50 p-4 rounded-lg border border-slate-200 mt-2"):
            # Checkbox Exonération
            tva_exo_checkbox = ui.checkbox(
                "Entreprise exonérée de TVA (ex: Micro-entreprise)", 
                value=bool(params.get("tva_exoneree", 1))
            )

            with ui.row().classes("w-full gap-4 items-center"):
                mention_exo_input = ui.input(
                    "Mention légale d'exonération de TVA", 
                    value=params.get("mention_tva_exoneree", "TVA non applicable, art. 293 B du CGI")
                ).classes("w-2/3")
                
                num_tva_input = ui.input(
                    "N° TVA Intracommunautaire", 
                    value=params.get("num_tva", "")
                ).classes("w-1/3")

            # --- LIAISON DYNAMIQUE (BINDING / CONDITIONNEL) ---
            # Mention d'exonération : Active seulement si la case 'Exonérée' est cochée
            mention_exo_input.bind_enabled_from(tva_exo_checkbox, 'value')

            # Numéro de TVA : Actif seulement si la case 'Exonérée' est décochée (sens inverse)
            num_tva_input.bind_enabled_from(tva_exo_checkbox, 'value', backward=lambda val: not val)

        # --- SECTION 3 : COORDONNÉES BANCAIRES ---
        ui.label("Coordonnées Bancaires (Règlement)").classes("text-lg font-semibold text-slate-700 border-b pb-2 w-full mt-4")

        with ui.row().classes("w-full gap-4"):
            banque_input = ui.input("Nom de la Banque", value=params.get("nom_banque", "")).classes("w-1/3")
            iban_input = ui.input("IBAN", value=params.get("iban", "")).classes("w-1/3")
            bic_input = ui.input("BIC / SWIFT", value=params.get("bic", "")).classes("w-1/3")

        # --- SECTION 4 : CONFIGURATION E-MAIL (SMTP) ---
        ui.label("Configuration E-mail (Envoi des documents)").classes("text-lg font-semibold text-slate-700 border-b pb-2 w-full mt-4")

        with ui.row().classes("w-full gap-4"):
            smtp_server_input = ui.input("Serveur SMTP", value=params.get("smtp_server", "smtp.gmail.com")).classes("w-1/3")
            smtp_port_input = ui.input("Port SMTP", value=str(params.get("smtp_port", 587))).classes("w-1/6")
            smtp_user_input = ui.input("E-mail d'envoi (Gmail)", value=params.get("smtp_user", "")).classes("w-1/4")
            smtp_password_input = ui.input(
                "Mot de passe d'application", 
                value=params.get("smtp_password", ""), 
                password=True, 
                password_toggle_button=True
            ).classes("w-1/4")

        # --- BOUTON DE SAUVEGARDE GÉNÉRALE ---
        def enregistrer():
            conn = database.get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE parametres SET
                    nom_entreprise=?, adresse=?, code_postal=?, ville=?, telephone=?, email=?,
                    siret=?, rcs=?, ape=?, tva_exoneree=?, num_tva=?, mention_tva_exoneree=?,
                    nom_banque=?, iban=?, bic=?, logo_path=?,
                    smtp_server=?, smtp_port=?, smtp_user=?, smtp_password=?
                WHERE id = 1
            """, (
                nom_input.value, adresse_input.value, cp_input.value, ville_input.value, tel_input.value, email_input.value,
                siret_input.value, rcs_input.value, ape_input.value, int(tva_exo_checkbox.value), num_tva_input.value, mention_exo_input.value,
                banque_input.value, iban_input.value, bic_input.value, logo_path_holder["path"],
                smtp_server_input.value, int(smtp_port_input.value or 587), smtp_user_input.value, smtp_password_input.value
            ))
            conn.commit()
            conn.close()
            ui.notify("Paramètres sauvegardés avec succès !", type="positive", icon="save")

        with ui.row().classes("w-full justify-end mt-6"):
            ui.button("Enregistrer les modifications", icon="save", on_click=enregistrer).props("color=primary size=lg")
