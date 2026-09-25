from nicegui import ui
import database
from ui_helpers import afficher_note_importante

# CSS pour masquer proprement la colonne de sélection Quasar dans tous les tableaux
ui.add_head_html('''
<style>
    .no-checkbox-table .q-table tbody td:first-child .q-checkbox,
    .no-checkbox-table .q-table<thead> th:first-child .q-checkbox {
        display: none !important;
    }
</style>
''', shared=True)

def render_annuaire():
    # Onglets pour basculer entre la gestion des clients et l'ajout de prestations
    with ui.tabs().classes("w-full text-slate-700") as tabs:
        client_tab = ui.tab("Clients", icon="people")
        presta_tab = ui.tab("Catalogue (Création)", icon="post_add")

    with ui.tab_panels(tabs, value=client_tab).classes("w-full bg-transparent"):
        
        # --- PANNEAU CLIENTS (Ajout, Modif, Tarifs) ---
        with ui.tab_panel(client_tab):
            with ui.row().classes("w-full justify-between items-center mb-6"):
                ui.label("Gestion des Clients & Tarifs").classes("text-2xl font-bold text-slate-800")
                ui.button("Infos Importantes", icon="warning", on_click=lambda: afficher_note_importante(
                    "Points d'attention - Fichier Clients",
                    [
                        "• Pour un professionnel, indiquez le nom de l'entreprise ; pour un particulier, le nom et le prénom.",
                        "• L'adresse de facturation est obligatoire car elle figurera sur tous vos documents officiels.",
                        "• L'e-mail de contact est indispensable pour l'envoi automatisé de vos devis et factures."
                    ],
                    tuto_titre="Tuto : Tarifs & Multi-sites",
                    tuto_etapes=[
                        "• Gestion des prix par client : Associez des grilles tarifaires spécifiques dans la fiche client.",
                        "• Gestion multi-sites : Rattachez plusieurs adresses de chantiers à une même entreprise."
                    ]
                )).props("flat color=amber")

            with ui.card().classes("w-full p-6 bg-white border border-slate-200 rounded-xl space-y-6"):
                table_container = ui.column().classes("w-full")

                def rafraichir_liste_clients():
                    table_container.clear()
                    supabase = database.get_db()
                    response = supabase.table("clients").select("*").order("nom_societe", desc=False).execute()
                    rows = response.data if response and hasattr(response, 'data') else []

                    clients = []
                    for r in rows:
                        item = dict(r)
                        item['type_client'] = "Particulier" if item.get('est_particulier') else "Professionnel"
                        item['multisite_txt'] = "Oui" if item.get('multi_etab') else "Non"
                        item['adresse_txt'] = item.get('adresse') or "-"
                        item['cp_ville_txt'] = f"{item.get('cp') or ''} {item.get('ville') or ''}".strip() or "-"
                        item['contact_nom'] = item.get('contact') or "-"
                        clients.append(item)

                    columns = [
                        {'name': 'nom_societe', 'label': 'Nom / Société', 'field': 'nom_societe', 'align': 'left', 'sortable': True},
                        {'name': 'type_client', 'label': 'Type', 'field': 'type_client', 'align': 'center', 'sortable': True},
                        {'name': 'contact_nom', 'label': 'Contact / Email', 'field': 'contact_nom', 'align': 'left'},
                        {'name': 'adresse_txt', 'label': 'Adresse', 'field': 'adresse_txt', 'align': 'left'},
                        {'name': 'cp_ville_txt', 'label': 'CP / Ville', 'field': 'cp_ville_txt', 'align': 'left', 'sortable': True},
                        {'name': 'multisite_txt', 'label': 'Multisite', 'field': 'multisite_txt', 'align': 'center'},
                    ]

                    with table_container:
                        with ui.row().classes("w-full justify-between items-center mb-4 gap-4"):
                            search_input = ui.input(placeholder="Rechercher un client...").props('dense outlined icon="search"').classes("w-72")
                            ui.button("Nouveau Client", icon="person_add", on_click=lambda: ouvrir_dialogue_client()).props("color=primary")

                        if not clients:
                            ui.label("Aucun client enregistré pour le moment.").classes("text-slate-400 italic py-4")
                        else:
                            grid = ui.table(columns=columns, rows=clients, row_key='id', selection='single', pagination=10).classes("w-full cursor-pointer no-checkbox-table")
                            grid.props('flat borderless hide-selection-color')
                            search_input.on_value_change(lambda e: grid.set_filter(e.value))

                            actions_bar = ui.row().classes("w-full justify-between items-center p-4 bg-slate-50 border border-slate-200 rounded-xl mt-4")
                            actions_bar.set_visibility(False)
                            label_selection = ui.label().classes("font-semibold text-slate-700")
                            buttons_container = ui.row().classes("gap-2 items-center")

                            def update_actions_bar():
                                if grid.selected:
                                    client_sel = grid.selected[0]
                                    label_selection.set_text(f"Client sélectionné : {client_sel['nom_societe']}")
                                    buttons_container.clear()
                                    with buttons_container:
                                        if client_sel.get('multi_etab'):
                                            ui.button("Établissements", icon="business", on_click=lambda: ouvrir_dialogue_sites(client_sel)).props("outline color=amber-9 dense")
                                        ui.button("Tarifs", icon="sell", on_click=lambda: ouvrir_dialogue_tarifs(client_sel)).props("outline color=teal dense")
                                        ui.button("Modifier", icon="edit", on_click=lambda: ouvrir_dialogue_client(client_sel)).props("color=primary dense")
                                        ui.button("Supprimer", icon="delete", on_click=lambda: confirmer_suppression_client(client_sel['id'])).props("color=negative dense")
                                    actions_bar.set_visibility(True)
                                else:
                                    actions_bar.set_visibility(False)

                            grid.on('row-click', lambda e: (grid.selected.clear(), grid.selected.append(e.args[1]), update_actions_bar()))

                            with actions_bar:
                                label_selection
                                buttons_container

                # Modale de création / édition client (reprise de ui_clients.py)[cite: 4]
                def ouvrir_dialogue_client(client=None):
                    is_edit = client is not None
                    with ui.dialog() as dialog, ui.card().classes("w-full max-w-2xl p-6 space-y-4"):
                        ui.label("Modifier le client" if is_edit else "Nouveau client").classes("text-xl font-bold text-slate-800 border-b pb-2")
                        
                        nom_in = ui.input("Nom de la Société / Nom Complet *", value=client.get('nom_societe') if is_edit else "").classes("w-full")
                        contact_in = ui.input("Nom du Contact", value=client.get('contact') if is_edit else "").classes("w-full")
                        
                        with ui.row().classes("w-full gap-2"):
                            email_in = ui.input("Email", value=client.get('email') if is_edit else "").classes("flex-1")
                            tel_in = ui.input("Téléphone", value=client.get('telephone') if is_edit else "").classes("flex-1")
                        
                        adresse_in = ui.input("Adresse", value=client.get('adresse') if is_edit else "").classes("w-full")
                        
                        with ui.row().classes("w-full gap-2"):
                            cp_in = ui.input("Code Postal", value=client.get('cp') if is_edit else "").classes("w-1/3")
                            ville_in = ui.input("Ville", value=client.get('ville') if is_edit else "").classes("w-2/3")

                        multi_check = ui.checkbox("Client Multisite (Gestion d'établissements)", value=bool(client.get('multi_etab')) if is_edit else False)

                        def sauvegarder():
                            if not nom_in.value.strip():
                                ui.notify("Le nom est obligatoire.", type="warning")
                                return
                            data = {
                                "nom_societe": nom_in.value.strip(),
                                "contact": contact_in.value,
                                "email": email_in.value,
                                "telephone": tel_in.value,
                                "adresse": adresse_in.value,
                                "cp": cp_in.value,
                                "ville": ville_in.value,
                                "multi_etab": multi_check.value
                            }
                            supabase = database.get_db()
                            if is_edit:
                                supabase.table("clients").update(data).eq("id", client['id']).execute()
                                ui.notify("Client mis à jour !", type="positive")
                            else:
                                supabase.table("clients").insert(data).execute()
                                ui.notify("Client créé !", type="positive")
                            dialog.close()
                            rafraichir_liste_clients()

                        with ui.row().classes("w-full justify-end gap-2 mt-4"):
                            ui.button("Annuler", on_click=dialog.close).props("flat")
                            ui.button("Enregistrer", icon="check", on_click=sauvegarder).props("color=primary")
                    dialog.open()

                # Modale gestion des tarifs spécifiques par client (reprise de ui_clients.py)[cite: 4]
                def ouvrir_dialogue_tarifs(client):
                    with ui.dialog() as dialog, ui.card().classes("w-full max-w-xl p-6 space-y-4"):
                        ui.label(f"Tarifs spécifiques : {client['nom_societe']}").classes("text-lg font-bold text-slate-800 border-b pb-2")
                        
                        supabase = database.get_db()
                        prestations = supabase.table("prestations").select("*").execute().data or []
                        tarifs_existants = {r['prestation_id']: r for r in supabase.table("client_tarifs").select("*").eq("client_id", client['id']).execute().data or []}
                        
                        inputs = {}
                        with ui.column().classes("w-full max-h-80 overflow-y-auto space-y-2"):
                            for p in prestations:
                                t = tarifs_existants.get(p['id'], {})
                                prix_val = t.get('prix_specifique_ht', p['prix_ht'])
                                with ui.row().classes("w-full justify-between items-center bg-slate-50 p-2 rounded border"):
                                    ui.label(p['designation']).classes("text-sm font-medium")
                                    inputs[p['id']] = ui.number(value=prix_val, format="%.2f").classes("w-32").props("dense outlined")

                        def enregistrer_tarifs():
                            for p_id, num in inputs.items():
                                supabase.table("client_tarifs").upsert({
                                    "client_id": client['id'],
                                    "prestation_id": p_id,
                                    "prix_specifique_ht": float(num.value or 0.0),
                                    "est_actif": True
                                }, on_conflict="client_id,prestation_id").execute()
                            ui.notify("Tarifs enregistrés !", type="positive")
                            dialog.close()

                        with ui.row().classes("w-full justify-end gap-2 mt-4"):
                            ui.button("Fermer", on_click=dialog.close).props("flat")
                            ui.button("Enregistrer", icon="save", on_click=enregistrer_tarifs).props("color=primary")
                    dialog.open()

                def ouvrir_dialogue_sites(client):
                    # Logique simplifiée ou existante pour les sites secondaires
                    pass

                def confirmer_suppression_client(client_id):
                    supabase = database.get_db()
                    supabase.table("clients").delete().eq("id", client_id).execute()
                    ui.notify("Client supprimé.", type="info")
                    rafraichir_liste_clients()

                rafraichir_liste_clients()

        # --- PANNEAU PRESTATIONS (Création simple uniquement) ---
        with ui.tab_panel(presta_tab):
            with ui.row().classes("w-full justify-between items-center mb-6"):
                ui.label("Création de Prestations (Catalogue)").classes("text-2xl font-bold text-slate-800")

            with ui.card().classes("w-full max-w-xl mx-auto p-6 bg-white border border-slate-200 rounded-xl space-y-4"):
                ui.label("Ajouter une nouvelle prestation au catalogue").classes("text-base font-semibold text-slate-700 border-b pb-2")

                desig_in = ui.input("Désignation *").classes("w-full")
                
                with ui.row().classes("w-full gap-4"):
                    unite_in = ui.select(
                        options=["Heure", "Jour", "Forfait", "Km", "Unité"], 
                        value="Heure",
                        label="Unité"
                    ).classes("w-1/2").props("dense outlined")
                    
                    prix_in = ui.number("Prix HT (€) *", value=0.0, format="%.2f", precision=2).classes("w-1/2").props("dense outlined")

                tva_in = ui.select(
                    options={0.0: "0 % (Exonéré)", 5.5: "5.5 %", 10.0: "10 %", 20.0: "20 %"},
                    value=20.0,
                    label="Taux de TVA par défaut"
                ).classes("w-full").props("dense outlined")

                def creer_prestation():
                    if not desig_in.value.strip():
                        ui.notify("Veuillez saisir une désignation.", type="warning")
                        return

                    supabase = database.get_db()
                    supabase.table("prestations").insert({
                        "designation": desig_in.value.strip(),
                        "unite": unite_in.value,
                        "prix_ht": float(prix_in.value or 0.0),
                        "taux_tva": float(tva_in.value or 0.0)
                    }).execute()

                    ui.notify("Nouvelle prestation ajoutée avec succès !", type="positive")
                    desig_in.value = ""
                    prix_in.value = 0.0

                with ui.row().classes("w-full justify-end mt-4"):
                    ui.button("Créer la prestation", icon="add", on_click=creer_prestation).props("color=primary")