from nicegui import ui
import database

# CSS pour masquer proprement la colonne de sélection Quasar dans tous les tableaux
ui.add_head_html('''
<style>
    .no-checkbox-table .q-table tbody td:first-child .q-checkbox,
    .no-checkbox-table .q-table<thead> th:first-child .q-checkbox {
        display: none !important;
    }
</style>
''')

def render_clients():
    ui.label("Gestion des Clients").classes("text-2xl font-bold text-slate-800 mb-6")

    with ui.card().classes("w-full p-6 bg-white border border-slate-200 rounded-xl space-y-6"):

        table_container = ui.column().classes("w-full")

        def rafraichir_liste():
            table_container.clear()

            conn = database.get_conn()
            rows = conn.execute("SELECT * FROM clients ORDER BY nom_societe ASC").fetchall()
            conn.close()

            clients = []
            for r in rows:
                item = dict(r)
                item['type_client'] = "Particulier" if item['est_particulier'] else "Professionnel"
                item['multisite_txt'] = "Oui" if item['multi_etab'] else "Non"
                item['recap_txt'] = "Oui" if item['recap_interventions'] else "Non"
                
                # Formatage adresse
                item['adresse_txt'] = item['adresse'] or "-"
                if item['cp'] or item['ville']:
                    item['cp_ville_txt'] = f"{item['cp'] or ''} {item['ville'] or ''}".strip()
                else:
                    item['cp_ville_txt'] = "-"

                # Contact
                item['contact_nom'] = item['contact'] or "-"
                item['contact_email'] = item['email'] or ""
                item['contact_tel'] = item['telephone'] or ""

                clients.append(item)

            columns = [
                {'name': 'nom_societe', 'label': 'Nom / Société', 'field': 'nom_societe', 'align': 'left', 'sortable': True},
                {'name': 'type_client', 'label': 'Type', 'field': 'type_client', 'align': 'center', 'sortable': True},
                {'name': 'contact_nom', 'label': 'Contact / Email', 'field': 'contact_nom', 'align': 'left'},
                {'name': 'adresse_txt', 'label': 'Adresse', 'field': 'adresse_txt', 'align': 'left'},
                {'name': 'cp_ville_txt', 'label': 'CP / Ville', 'field': 'cp_ville_txt', 'align': 'left', 'sortable': True},
                {'name': 'multisite_txt', 'label': 'Multisite', 'field': 'multisite_txt', 'align': 'center'},
                {'name': 'recap_txt', 'label': 'Récap. Auto', 'field': 'recap_txt', 'align': 'center'},
            ]

            with table_container:
                with ui.row().classes("w-full justify-between items-center mb-4 gap-4"):
                    search_input = ui.input(placeholder="Rechercher un client...").props('dense outlined icon="search"').classes("w-72")
                    ui.button("Nouveau Client", icon="person_add", on_click=lambda: ouvrir_dialogue_client()).props("color=primary")

                if not clients:
                    ui.label("Aucun client enregistré pour le moment.").classes("text-slate-400 italic py-4")
                else:
                    # Ajout de la classe custom 'no-checkbox-table' pour masquer la checkbox en CSS
                    grid = ui.table(columns=columns, rows=clients, row_key='id', selection='single', pagination=10).classes("w-full cursor-pointer no-checkbox-table")
                    grid.props('flat borderless hide-selection-color')

                    search_input.on_value_change(lambda e: grid.set_filter(e.value))

                    # 1. Badge Type Client
                    grid.add_slot('body-cell-type_client', '''
                        <q-td :props="props">
                            <q-chip dense 
                                    :color="props.row.est_particulier ? 'purple-1' : 'blue-1'" 
                                    :text-color="props.row.est_particulier ? 'purple-9' : 'blue-9'"
                                    :icon="props.row.est_particulier ? 'person' : 'business'">
                                {{ props.value }}
                            </q-chip>
                        </q-td>
                    ''')

                    # 2. Nom & Email Contact
                    grid.add_slot('body-cell-contact_nom', '''
                        <q-td :props="props">
                            <div class="font-medium text-slate-800">{{ props.row.contact_nom }}</div>
                            <div v-if="props.row.contact_email" class="text-xs text-slate-500 flex items-center gap-1">
                                <q-icon name="mail" size="12px" /> {{ props.row.contact_email }}
                            </div>
                        </q-td>
                    ''')

                    # 3. Multisite Chip
                    grid.add_slot('body-cell-multisite_txt', '''
                        <q-td :props="props">
                            <q-chip dense
                                    :color="props.row.multi_etab ? 'teal-1' : 'grey-2'" 
                                    :text-color="props.row.multi_etab ? 'teal-9' : 'grey-7'" 
                                    :icon="props.row.multi_etab ? 'domain' : 'close'">
                                {{ props.value }}
                            </q-chip>
                        </q-td>
                    ''')

                    # 4. Récap Auto Chip
                    grid.add_slot('body-cell-recap_txt', '''
                        <q-td :props="props">
                            <q-chip dense 
                                    :color="props.row.recap_interventions ? 'emerald-1' : 'grey-2'" 
                                    :text-color="props.row.recap_interventions ? 'emerald-9' : 'grey-7'" 
                                    :icon="props.row.recap_interventions ? 'task_alt' : 'highlight_off'">
                                {{ props.value }}
                            </q-chip>
                        </q-td>
                    ''')

                    # --- BARRE D'ACTIONS SOUS LE TABLEAU ---
                    actions_bar = ui.row().classes("w-full justify-between items-center p-4 bg-slate-50 border border-slate-200 rounded-xl mt-4 transition-all")
                    actions_bar.set_visibility(False)

                    label_selection = ui.label().classes("font-semibold text-slate-700")
                    buttons_container = ui.row().classes("gap-2 items-center")

                    def update_actions_bar():
                        if grid.selected:
                            client_sel = grid.selected[0]
                            label_selection.set_text(f"Client sélectionné : {client_sel['nom_societe']}")
                            
                            buttons_container.clear()
                            with buttons_container:
                                # Bouton Sites (uniquement si multisite)
                                if client_sel.get('multi_etab'):
                                    ui.button("Établissements / Sites", icon="business", 
                                              on_click=lambda: ouvrir_dialogue_sites(client_sel)).props("outline color=amber-9 dense")

                                # Bouton Catalogue & Tarifs
                                ui.button("Tarifs & Prestations", icon="sell", 
                                          on_click=lambda: ouvrir_dialogue_tarifs(client_sel)).props("outline color=teal dense")

                                # Bouton Modifier
                                ui.button("Modifier", icon="edit", 
                                          on_click=lambda: ouvrir_dialogue_client(client_sel)).props("color=primary dense")

                                # Bouton Supprimer
                                ui.button("Supprimer", icon="delete", 
                                          on_click=lambda: confirmer_suppression(client_sel['id'], client_sel['nom_societe'])).props("color=negative dense")

                            actions_bar.set_visibility(True)
                        else:
                            actions_bar.set_visibility(False)

                    # Sélection directe au clic sur la ligne
                    def on_row_click(e):
                        client_row = e.args[1]
                        grid.selected.clear()
                        grid.selected.append(client_row)
                        update_actions_bar()

                    grid.on('row-click', on_row_click)

                    with actions_bar:
                        label_selection
                        buttons_container

        # --- MODALE CRÉATION / ÉDITION CLIENT ---
        def ouvrir_dialogue_client(client=None):
            is_edit = client is not None
            titre = "Modifier le client" if is_edit else "Nouveau client"

            with ui.dialog() as dialog, ui.card().classes("w-full max-w-2xl p-6 space-y-4"):
                ui.label(titre).classes("text-xl font-bold text-slate-800 border-b pb-2")

                is_particulier_check = ui.checkbox("Client Particulier (Masquer identifiants professionnels)", value=bool(client['est_particulier']) if is_edit else False)

                nom_in = ui.input("Nom de la Société / Nom Complet *", value=client['nom_societe'] if is_edit else "").classes("w-full")
                contact_in = ui.input("Nom du Contact Référent", value=client['contact'] if is_edit else "").classes("w-full")

                with ui.row().classes("w-full gap-4"):
                    email_in = ui.input("Email", value=client['email'] if is_edit else "").classes("w-1/2")
                    tel_in = ui.input("Téléphone", value=client['telephone'] if is_edit else "").classes("w-1/2")

                adresse_in = ui.input("Adresse", value=client['adresse'] if is_edit else "").classes("w-full")
                with ui.row().classes("w-full gap-4"):
                    cp_in = ui.input("Code Postal", value=client['cp'] if is_edit else "").classes("w-1/3")
                    ville_in = ui.input("Ville", value=client['ville'] if is_edit else "").classes("w-2/3")

                pro_container = ui.column().classes("w-full p-4 bg-slate-50 border rounded-xl gap-4")
                with pro_container:
                    ui.label("Informations Professionnelles").classes("text-xs font-bold text-slate-500 uppercase")
                    with ui.row().classes("w-full gap-4"):
                        siret_in = ui.input("SIRET", value=client['siret'] if is_edit else "").classes("flex-1")
                        tva_in = ui.input("N° TVA Intracommunautaire", value=client['tva_intra'] if is_edit else "").classes("flex-1")
                    with ui.row().classes("w-full gap-4"):
                        rcs_in = ui.input("RCS / RM", value=client['rcs'] if is_edit else "").classes("flex-1")
                        ape_in = ui.input("APE / NAF", value=client['ape'] if is_edit else "").classes("flex-1")

                options_container = ui.column().classes("w-full gap-2")
                with options_container:
                    ui.label("Options de facturation & Gestion").classes("text-sm font-bold text-slate-700 mt-2")
                    sans_tva_check = ui.checkbox("Exonérer ce client de TVA (Facturation HT)", value=bool(client['sans_tva']) if is_edit else False)
                    recap_check = ui.checkbox("Générer automatiquement le PDF Récapitulatif de prestation", value=bool(client['recap_interventions']) if is_edit else False)
                    multi_check = ui.checkbox("Client Multisite (Gestion de plusieurs établissements)", value=bool(client['multi_etab']) if is_edit else False)
                    
                    ui.label("Modèle de facture à utiliser :").classes("text-xs font-bold text-slate-500 mt-2")
                    valeur_modele_actuelle = client.get('modele_facture', 'condense') if is_edit else 'condense'
                    modele_facture_select = ui.select(
                        options={
                            'condense': 'Facture condensée (Regroupée par prestation)',
                            'detaille': 'Facture détaillée (Ligne par ligne / intervention)'
                        },
                        value=valeur_modele_actuelle
                    ).classes("w-full").props('dense outlined')

                def toggle_type_client():
                    if is_particulier_check.value:
                        adresse_in.set_label("Adresse")
                        pro_container.set_visibility(False)
                        options_container.set_visibility(False)
                    else:
                        adresse_in.set_label("Adresse Siège")
                        pro_container.set_visibility(True)
                        options_container.set_visibility(True)

                is_particulier_check.on_value_change(toggle_type_client)
                toggle_type_client()

                def toggle_tva_client():
                    if sans_tva_check.value:
                        tva_in.disable()
                    else:
                        if not is_particulier_check.value:
                            tva_in.enable()

                sans_tva_check.on_value_change(toggle_tva_client)
                toggle_tva_client()

                def sauvegarder():
                    if not nom_in.value.strip():
                        ui.notify("Le nom / raison sociale est obligatoire.", type="warning")
                        return

                    est_part = int(is_particulier_check.value)
                    sans_tva_val = 0 if est_part else int(sans_tva_check.value)
                    recap_val = 0 if est_part else int(recap_check.value)
                    multi_val = 0 if est_part else int(multi_check.value)
                    modele_val = 'condense' if est_part else (modele_facture_select.value or 'condense')

                    conn = database.get_conn()
                    cursor = conn.cursor()

                    if is_edit:
                        cursor.execute("""
                            UPDATE clients SET
                                nom_societe=?, contact=?, adresse=?, cp=?, ville=?, email=?, telephone=?,
                                est_particulier=?, siret=?, tva_intra=?, rcs=?, ape=?,
                                sans_tva=?, recap_interventions=?, multi_etab=?, modele_facture=?
                            WHERE id=?
                        """, (
                            nom_in.value.strip(), contact_in.value, adresse_in.value, cp_in.value, ville_in.value, email_in.value, tel_in.value,
                            est_part, 
                            "" if est_part else siret_in.value, 
                            "" if est_part else tva_in.value, 
                            "" if est_part else rcs_in.value, 
                            "" if est_part else ape_in.value,
                            sans_tva_val, recap_val, multi_val, modele_val, client['id']
                        ))
                        ui.notify("Fiche client mise à jour !", type="positive")
                    else:
                        cursor.execute("""
                            INSERT INTO clients (
                                nom_societe, contact, adresse, cp, ville, email, telephone,
                                est_particulier, siret, tva_intra, rcs, ape,
                                sans_tva, recap_interventions, multi_etab, modele_facture
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            nom_in.value.strip(), contact_in.value, adresse_in.value, cp_in.value, ville_in.value, email_in.value, tel_in.value,
                            est_part, 
                            "" if est_part else siret_in.value, 
                            "" if est_part else tva_in.value, 
                            "" if est_part else rcs_in.value, 
                            "" if est_part else ape_in.value,
                            sans_tva_val, recap_val, multi_val, modele_val
                        ))
                        ui.notify("Nouveau client créé !", type="positive")

                    conn.commit()
                    conn.close()
                    dialog.close()
                    rafraichir_liste()

                with ui.row().classes("w-full justify-end gap-2 mt-4"):
                    ui.button("Annuler", on_click=dialog.close).props("flat color=slate")
                    ui.button("Enregistrer", icon="check", on_click=sauvegarder).props("color=primary")

            dialog.open()

        # --- MODALE GESTION DES SITES (MULTISITE AVEC ÉDITION) ---
        def ouvrir_dialogue_sites(client):
            with ui.dialog() as dialog, ui.card().classes("w-full max-w-xl p-6 space-y-4"):
                ui.label(f"Sites / Établissements : {client['nom_societe']}").classes("text-xl font-bold text-slate-800 border-b pb-2")

                sites_container = ui.column().classes("w-full space-y-2")
                site_edite = {"id": None}

                site_nom = ui.input("Nom du site (ex: Agence Lyon, Entrepôt Nord)").classes("w-full")
                site_adr = ui.input("Adresse du site").classes("w-full")
                with ui.row().classes("w-full gap-4"):
                    site_cp = ui.input("Code Postal").classes("w-1/3")
                    site_ville = ui.input("Ville").classes("w-2/3")

                btn_ajouter = ui.button("Ajouter ce site", icon="add", on_click=lambda: sauvegarder_site()).props("color=positive").classes("w-full text-white")

                def rafraichir_sites():
                    sites_container.clear()
                    conn = database.get_conn()
                    sites = conn.execute("SELECT * FROM etablissements WHERE client_id=? ORDER BY nom_site ASC", (client['id'],)).fetchall()
                    conn.close()

                    with sites_container:
                        if not sites:
                            ui.label("Aucun site secondaire ajouté.").classes("text-slate-400 italic text-sm py-2")
                        for s in sites:
                            with ui.row().classes("w-full justify-between items-center p-3 bg-slate-50 border rounded-lg"):
                                with ui.column().classes("gap-0 flex-1"):
                                    ui.label(s['nom_site']).classes("font-bold text-slate-800")
                                    ui.label(f"{s['adresse']}, {s['cp']} {s['ville']}").classes("text-xs text-slate-500")
                                
                                with ui.row().classes("gap-1"):
                                    ui.button(icon="edit", color="primary", on_click=lambda site=s: charger_pour_edition(site)).props("flat round dense")
                                    ui.button(icon="delete", color="negative", on_click=lambda s_id=s['id']: supprimer_site(s_id)).props("flat round dense")

                def charger_pour_edition(site):
                    site_edite["id"] = site['id']
                    site_nom.value = site['nom_site']
                    site_adr.value = site['adresse']
                    site_cp.value = site['cp']
                    site_ville.value = site['ville']
                    btn_ajouter.set_text("Modifier ce site")
                    btn_ajouter.props("color=primary")

                def reinitialiser_form_site():
                    site_edite["id"] = None
                    site_nom.value = ""
                    site_adr.value = ""
                    site_cp.value = ""
                    site_ville.value = ""
                    btn_ajouter.set_text("Ajouter ce site")
                    btn_ajouter.props("color=positive")

                def sauvegarder_site():
                    if not site_nom.value.strip():
                        ui.notify("Veuillez donner un nom au site.", type="warning")
                        return

                    conn = database.get_conn()
                    if site_edite["id"]:
                        conn.execute("UPDATE etablissements SET nom_site=?, adresse=?, cp=?, ville=? WHERE id=?",
                                   (site_nom.value.strip(), site_adr.value, site_cp.value, site_ville.value, site_edite["id"]))
                        ui.notify("Site mis à jour !", type="positive")
                    else:
                        conn.execute("INSERT INTO etablissements (client_id, nom_site, adresse, cp, ville) VALUES (?, ?, ?, ?, ?)",
                                   (client['id'], site_nom.value.strip(), site_adr.value, site_cp.value, site_ville.value))
                        ui.notify("Nouveau site ajouté !", type="positive")

                    conn.commit()
                    conn.close()
                    reinitialiser_form_site()
                    rafraichir_sites()

                def supprimer_site(site_id):
                    conn = database.get_conn()
                    conn.execute("DELETE FROM etablissements WHERE id=?", (site_id,))
                    conn.commit()
                    conn.close()
                    reinitialiser_form_site()
                    rafraichir_sites()

                rafraichir_sites()

                with ui.row().classes("w-full justify-end mt-4"):
                    ui.button("Fermer", on_click=dialog.close).props("flat color=slate")

            dialog.open()

        # --- MODALE TARIFS SPÉCIFIQUES & ACTIVATION DES PRESTATIONS ---
        def ouvrir_dialogue_tarifs(client):
            with ui.dialog() as dialog, ui.card().classes("w-full max-w-2xl p-6 space-y-4"):
                ui.label(f"Catalogue & Tarifs client : {client['nom_societe']}").classes("text-lg font-bold text-slate-800 border-b pb-2")
                ui.label("Cochez les prestations réalisables chez ce client et ajustez leurs prix si nécessaire.").classes("text-xs text-slate-500")

                conn = database.get_conn()
                prestations = conn.execute("SELECT * FROM prestations ORDER BY designation ASC").fetchall()
                
                tarifs_rows = conn.execute("SELECT * FROM client_tarifs WHERE client_id=?", (client['id'],)).fetchall()
                tarifs_existants = {r['prestation_id']: dict(r) for r in tarifs_rows}
                conn.close()

                inputs_tarifs = {}

                with ui.column().classes("w-full max-h-96 overflow-y-auto space-y-3 p-2"):
                    if not prestations:
                        ui.label("Aucune prestation enregistrée dans le catalogue.").classes("text-slate-400 italic text-sm")
                    
                    for p in prestations:
                        p_id = p['id']
                        tarif_custom = tarifs_existants.get(p_id)
                        
                        est_actif = bool(tarif_custom['est_actif']) if (tarif_custom and 'est_actif' in tarif_custom and tarif_custom['est_actif'] is not None) else True
                        prix_val = tarif_custom['prix_specifique_ht'] if (tarif_custom and tarif_custom['prix_specifique_ht'] is not None) else p['prix_ht']

                        with ui.row().classes("w-full justify-between items-center p-3 bg-slate-50 border rounded-lg gap-4"):
                            actif_check = ui.checkbox(value=est_actif).props("dense")
                            
                            with ui.column().classes("flex-1 gap-0"):
                                ui.label(p['designation']).classes("font-bold text-slate-800 text-sm")
                                ui.label(f"Standard : {p['prix_ht']:.2f} € / {p['unite']}").classes("text-xs text-slate-500")

                            num_in = ui.number(label="Prix HT Client (€)", value=prix_val, format="%.2f").classes("w-36")
                            
                            def toggle_input(e, target_input=num_in):
                                if e.value:
                                    target_input.enable()
                                else:
                                    target_input.disable()

                            actif_check.on_value_change(toggle_input)
                            if not est_actif:
                                num_in.disable()

                            inputs_tarifs[p_id] = {"actif": actif_check, "prix": num_in}

                def enregistrer_tarifs():
                    conn = database.get_conn()
                    cursor = conn.cursor()
                    for p_id, items in inputs_tarifs.items():
                        nouveau_prix = float(items["prix"].value or 0.0)
                        is_active = 1 if items["actif"].value else 0
                        cursor.execute("""
                            INSERT INTO client_tarifs (client_id, prestation_id, prix_specifique_ht, est_actif)
                            VALUES (?, ?, ?, ?)
                            ON CONFLICT(client_id, prestation_id) DO UPDATE SET 
                                prix_specifique_ht=excluded.prix_specifique_ht,
                                est_actif=excluded.est_actif
                        """, (client['id'], p_id, nouveau_prix, is_active))
                    conn.commit()
                    conn.close()
                    ui.notify("Catalogue et tarifs du client enregistrés !", type="positive")
                    dialog.close()

                with ui.row().classes("w-full justify-end gap-2 mt-4"):
                    ui.button("Annuler", on_click=dialog.close).props("flat color=slate")
                    ui.button("Enregistrer", icon="save", on_click=enregistrer_tarifs).props("color=primary")

            dialog.open()

        # --- SUPPRESSION CLIENT ---
        def confirmer_suppression(client_id, nom_client):
            with ui.dialog() as dialog, ui.card().classes("p-6 space-y-4"):
                ui.label("Confirmer la suppression").classes("text-lg font-bold text-slate-800")
                ui.label(f"Voulez-vous supprimer le client « {nom_client} » et toutes ses données associées ?").classes("text-slate-600")

                def supprimer():
                    conn = database.get_conn()
                    conn.execute("DELETE FROM clients WHERE id=?", (client_id,))
                    conn.commit()
                    conn.close()
                    dialog.close()
                    ui.notify("Client supprimé.", type="info")
                    rafraichir_liste()

                with ui.row().classes("w-full justify-end gap-2"):
                    ui.button("Annuler", on_click=dialog.close).props("flat color=slate")
                    ui.button("Supprimer", color="negative", on_click=supprimer)

            dialog.open()

        rafraichir_liste()