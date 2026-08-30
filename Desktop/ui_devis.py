from datetime import datetime, timedelta
import os
import subprocess
import sys
import database
import pdf_generator
from nicegui import ui
utils = __import__('utils')
import codecs

if sys.stdout.encoding != 'utf-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

def formater_date_fr(date_str):
    """Convertit AAAA-MM-JJ en JJ/MM/AAAA pour l'affichage."""
    if not date_str:
        return ""
    try:
        d = datetime.strptime(str(date_str).strip(), "%Y-%m-%d")
        return d.strftime("%d/%m/%Y")
    except Exception:
        return str(date_str)

def ouvrir_fichier_pdf(chemin_pdf):
    """Ouvre directement le fichier PDF avec l'application par défaut."""
    if not os.path.exists(chemin_pdf):
        ui.notify("Fichier PDF introuvable.", type="negative")
        return
    
    try:
        if sys.platform == "win32":
            os.startfile(chemin_pdf)
        elif sys.platform == "darwin":
            subprocess.run(["open", chemin_pdf], check=True)
        else:
            subprocess.run(["xdg-open", chemin_pdf], check=True)
    except Exception as e:
        ui.notify(f"Erreur lors de l'ouverture du PDF : {e}", type="negative")

# --- FONCTION GLOBALE DE CONVERSION ---
def convertir_devis_en_prestation(devis_id, num_devis, callback_rechargement):
    client_db = database.get_client()
    try:
        res_devis = client_db.table("devis").select("*").eq("id", devis_id).execute()
        devis = res_devis.data[0] if res_devis.data else None
        
        res_items = client_db.table("devis_items").select("*").eq("devis_id", devis_id).execute()
        items = res_items.data or []
        
        client_id = devis['client_id'] if devis else None
        sites_sec = []
        if client_id:
            try:
                res_sites = client_db.table("etablissements").select("id, nom_site, adresse").eq("client_id", client_id).execute()
                sites_sec = res_sites.data or []
            except Exception:
                sites_sec = []
    except Exception as e:
        ui.notify(f"Erreur lors de la récupération du devis : {e}", type="negative")
        return

    date_defaut = devis['date_prevue_execution'] if (devis and devis['date_prevue_execution']) else datetime.now().strftime("%Y-%m-%d")

    dialog = ui.dialog()
    with dialog, ui.card().classes("p-6 space-y-4 w-full max-w-lg"):
        ui.label(f"Convertir Devis {num_devis} en Prestation").classes("text-xl font-bold text-slate-800 border-b pb-2 w-full")
        ui.label("Planifier l'intervention issue du devis :").classes("text-sm text-slate-600 font-medium")

        site_select = None
        if sites_sec:
            sites_options = {None: "Adresse principale du client"}
            for s in sites_sec:
                sites_options[s['id']] = f"{s['nom_site']} - {s['adresse']}"
            site_select = ui.select(options=sites_options, value=None, label="Établissement / Site d'intervention").props("dense outlined").classes("w-full")

        date_exec_input = ui.input("Date d'exécution", value=date_defaut).props("dense outlined").classes("w-full")
        with date_exec_input:
            with ui.menu() as menu_date:
                ui.date().bind_value(date_exec_input)
            with date_exec_input.add_slot('append'):
                ui.icon('event').classes('cursor-pointer').on('click', menu_date.open)

        with ui.row().classes("w-full gap-4 items-center"):
            h_debut_input = ui.input("Début", value="14:00").props("dense outlined").classes("w-1/2")
            with h_debut_input:
                with ui.menu() as menu_h1:
                    ui.time().props("format24h minute-step=5").bind_value(h_debut_input)
                with h_debut_input.add_slot('append'):
                    ui.icon('schedule').classes('cursor-pointer').on('click', menu_h1.open)

            h_fin_input = ui.input("Fin", value="16:00").props("dense outlined").classes("w-1/2")
            with h_fin_input:
                with ui.menu() as menu_h2:
                    ui.time().props("format24h minute-step=5").bind_value(h_fin_input)
                with h_fin_input.add_slot('append'):
                    ui.icon('schedule').classes('cursor-pointer').on('click', menu_h2.open)

        duree_label = ui.label("Durée calculée : 2.0 h").classes("w-full text-center text-sm font-semibold text-slate-700 bg-slate-100 py-2 rounded")

        def maj_duree_val():
            try:
                t1 = datetime.strptime(h_debut_input.value, "%H:%M")
                t2 = datetime.strptime(h_fin_input.value, "%H:%M")
                diff = (t2 - t1).total_seconds() / 3600.0
                if diff < 0:
                    diff += 24.0
                duree_label.set_text(f"Durée calculée : {round(diff, 2)} h")
            except Exception:
                duree_label.set_text("Durée calculée : 1.0 h")

        h_debut_input.on_value_change(lambda _: maj_duree_val())
        h_fin_input.on_value_change(lambda _: maj_duree_val())

        def valider_acceptation():
            val_date = date_exec_input.value or date_defaut
            val_h_debut = h_debut_input.value or ""
            val_h_fin = h_fin_input.value or ""
            val_site_id = site_select.value if site_select else None

            qte_calculee = 1.0
            try:
                t1 = datetime.strptime(val_h_debut, "%H:%M")
                t2 = datetime.strptime(val_h_fin, "%H:%M")
                diff = (t2 - t1).total_seconds() / 3600.0
                if diff < 0:
                    diff += 24.0
                qte_calculee = round(diff, 2)
            except Exception:
                pass

            try:
                client_db.table("devis").update({
                    "statut": "Accepté",
                    "date_prevue_execution": val_date
                }).eq("id", devis_id).execute()

                num_interv = database.generer_numero_document("PREST")

                if items:
                    for item in items:
                        quantite_finale = qte_calculee if qte_calculee else item['quantite']
                        payload = {
                            "numero_intervention": num_interv,
                            "client_id": devis['client_id'],
                            "etablissement_id": val_site_id,
                            "prestation_id": item['prestation_id'],
                            "devis_id": devis_id,
                            "date": val_date,
                            "heure_debut": val_h_debut,
                            "heure_fin": val_h_fin,
                            "quantite": quantite_finale,
                            "prix_final_ht": item['prix_unitaire_ht'],
                            "taux_tva": item['taux_tva'],
                            "statut": "En attente",
                            "commentaire": f"Générée depuis devis {num_devis}"
                        }
                        try:
                            client_db.table("interventions").insert(payload).execute()
                        except Exception:
                            # Fallback sans etablissement_id si la colonne n'existe pas
                            payload.pop("etablissement_id", None)
                            client_db.table("interventions").insert(payload).execute()
                else:
                    payload = {
                        "numero_intervention": num_interv,
                        "client_id": devis['client_id'],
                        "etablissement_id": val_site_id,
                        "devis_id": devis_id,
                        "date": val_date,
                        "heure_debut": val_h_debut,
                        "heure_fin": val_h_fin,
                        "quantite": qte_calculee,
                        "prix_final_ht": devis['total_ht'],
                        "statut": "En attente",
                        "commentaire": f"Générée depuis devis {num_devis}"
                    }
                    try:
                        client_db.table("interventions").insert(payload).execute()
                    except Exception:
                        payload.pop("etablissement_id", None)
                        client_db.table("interventions").insert(payload).execute()

            except Exception as e:
                ui.notify(f"Erreur lors de la conversion : {e}", type="negative")
                return

            ui.notify(f"Devis {num_devis} ACCEPTÉ ! Prestation {num_interv} planifiée.", type="positive", icon="event_available")
            dialog.close()
            if callback_rechargement:
                callback_rechargement()

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
            ui.button("Annuler", on_click=dialog.close).props("flat color=slate")
            ui.button("Planifier la Prestation", icon="check", on_click=valider_acceptation).props("color=positive font-bold")

    dialog.open()


def render_devis():
    ui.label("Gestion des Devis").classes("text-2xl font-bold text-slate-800 mb-6")

    with ui.card().classes("w-full p-6 bg-white border border-slate-200 rounded-xl space-y-4"):

        top_bar = ui.row().classes("w-full justify-between items-center mb-2 gap-4 flex-wrap")
        
        selection_holder = {'selected_row': None}

        columns = [
            {'headerName': 'N° Devis', 'field': 'numero_devis', 'align': 'left', 'sortable': True, 'filter': 'agTextColumnFilter'},
            {'headerName': 'Client', 'field': 'nom_societe', 'align': 'left', 'sortable': True, 'filter': 'agTextColumnFilter'},
            {'headerName': 'Émission', 'field': 'date_creation_fr', 'align': 'center', 'sortable': True, 'filter': 'agDateColumnFilter'},
            {'headerName': 'Échéance', 'field': 'date_validite_fr', 'align': 'center', 'sortable': True},
            {'headerName': 'Total HT', 'field': 'total_ht_txt', 'align': 'right', 'sortable': True},
            {'headerName': 'Total TTC', 'field': 'total_ttc_txt', 'align': 'right', 'sortable': True},
            {
                'headerName': 'Statut', 
                'field': 'statut', 
                'align': 'center', 
                'sortable': True, 
                'filter': 'agTextColumnFilter',
                'cellClassRules': {
                    'bg-slate-100 text-slate-700 font-bold border-slate-300': 'x === "Brouillon"',
                    'bg-blue-100 text-blue-800 font-bold border-blue-300': 'x === "Envoyé"',
                    'bg-emerald-100 text-emerald-800 font-bold border-emerald-300': 'x === "Accepté"',
                    'bg-red-100 text-red-800 font-bold border-red-300': 'x === "Refusé"',
                }
            }
        ]

        grid = ui.aggrid({
            'columnDefs': columns,
            'rowData': [],
            'rowSelection': 'single',
            'pagination': True,
            'paginationPageSize': 12,
            'defaultColDef': {'resizable': True, 'sortable': True, 'filter': True}
        }).classes('h-96 w-full cursor-pointer')

        with ui.row().classes("w-full justify-between items-center pt-3 border-t border-slate-200 min-h-[48px]"):
            action_label = ui.label("💡 Cliquez sur une ligne du tableau pour interagir.").classes("text-xs text-slate-400 font-medium italic py-1")
            
            with ui.row().classes("items-center gap-2 flex-wrap") as action_buttons:
                btn_print = ui.button("Voir PDF", icon="picture_as_pdf", on_click=lambda: tenter_impression()).props("dense color=primary font-bold")
                btn_email = ui.button("Envoyer", icon="send", on_click=lambda: tenter_envoi_email()).props("dense outline color=info font-bold")
                btn_convertir = ui.button("Convertir en Prestation", icon="event_available", on_click=lambda: tenter_conversion()).props("dense color=positive font-bold")
                btn_editer = ui.button("Éditer", icon="edit", on_click=lambda: tenter_edition()).props("dense outline color=primary font-bold")
                btn_refuser = ui.button("Refuser", icon="cancel", on_click=lambda: tenter_refus()).props("dense flat color=warning font-bold")
                btn_supprimer = ui.button("Supprimer", icon="delete", on_click=lambda: tenter_suppression()).props("dense flat color=negative font-bold")
                
                for btn in [btn_print, btn_email, btn_convertir, btn_editer, btn_refuser, btn_supprimer]:
                    btn.set_visibility(False)

        def update_action_bar():
            selected = selection_holder['selected_row']
            if selected:
                num = selected.get('numero_devis', '')
                statut = selected.get('statut', '')
                
                action_label.set_text(f"Devis sélectionné : {num} ({statut})")
                action_label.classes(replace="text-sm font-bold text-slate-700 bg-slate-100 px-3 py-1.5 rounded-lg border border-slate-200")
                
                btn_print.set_visibility(True)
                btn_supprimer.set_visibility(True)

                btn_email.set_visibility(statut == "Brouillon")
                btn_convertir.set_visibility(statut not in ["Accepté", "Refusé"])
                btn_editer.set_visibility(statut not in ["Accepté", "Refusé"])
                btn_refuser.set_visibility(statut not in ["Accepté", "Refusé"])
            else:
                action_label.set_text("💡 Cliquez sur une ligne du tableau pour interagir.")
                action_label.classes(replace="text-xs text-slate-400 font-medium italic py-1")
                for btn in [btn_print, btn_email, btn_convertir, btn_editer, btn_refuser, btn_supprimer]:
                    btn.set_visibility(False)

        def on_cell_clicked(e):
            data = e.args.get('data')
            if data:
                selection_holder['selected_row'] = data
                update_action_bar()

        grid.on('cellClicked', on_cell_clicked)

        def charger_donnees():
            selection_holder['selected_row'] = None
            update_action_bar()

            filtre_statut = select_statut.value
            filtre_client = select_client.value

            client_db = database.get_client()
            try:
                res = client_db.table("devis").select("*, clients(nom_societe, email)").order("id", desc=True).execute()
                rows = res.data or []
            except Exception as e:
                ui.notify(f"Erreur de chargement des devis : {e}", type="negative")
                rows = []

            devis_list = []
            for r in rows:
                item = dict(r)
                client_info = item.get('clients') or {}
                item['nom_societe'] = client_info.get('nom_societe', 'Inconnu')
                item['client_email'] = client_info.get('email', '')

                item['date_creation_fr'] = formater_date_fr(item['date_creation'])
                item['date_validite_fr'] = formater_date_fr(item['date_validite'])
                item['total_ht_txt'] = f"{(item['total_ht'] or 0.0):.2f} €"
                item['total_ttc_txt'] = f"{(item['total_ttc'] or 0.0):.2f} €"

                if filtre_statut != "Tous" and item['statut'] != filtre_statut:
                    continue
                if filtre_client != "Tous" and str(item['client_id']) != str(filtre_client):
                    continue

                devis_list.append(item)

            grid.options['rowData'] = devis_list
            grid.update()

        with top_bar:
            with ui.row().classes("items-center gap-4 flex-wrap flex-1"):
                ui.label("Devis").classes("text-lg font-semibold text-slate-700")

                select_statut = ui.select(
                    ["Tous", "Brouillon", "Envoyé", "Accepté", "Refusé"], 
                    value="Tous", 
                    label="Filtrer par Statut"
                ).classes("w-44")
                
                clients_list = database.recuperer_tous_les_clients()
                client_filter_opts = {"Tous": "Tous les clients"}
                client_filter_opts.update({str(c['id']): c['nom_societe'] for c in clients_list})
                
                select_client = ui.select(
                    client_filter_opts, 
                    value="Tous", 
                    label="Filtrer par Client"
                ).classes("w-52")

                select_statut.on_value_change(lambda _: charger_donnees())
                select_client.on_value_change(lambda _: charger_donnees())

            ui.button("Créer un Devis", icon="add", on_click=lambda: ouvrir_dialogue_devis()).props("color=primary font-bold")

        def tenter_impression():
            d = selection_holder['selected_row']
            if not d:
                return
            dossier_export = pdf_generator.obtenir_chemin_export(d['nom_societe'], type_doc="Devis")
            filename = f"Devis_{d['numero_devis']}.pdf"
            pdf_path = os.path.join(dossier_export, filename)

            pdf_generator.generer_pdf_devis(d['id'], pdf_path)
            ui.notify(f"Ouverture du devis {d['numero_devis']}...", type="positive", icon="picture_as_pdf")
            ouvrir_fichier_pdf(pdf_path)

        def tenter_envoi_email():
            d = selection_holder['selected_row']
            if not d:
                return
            ouvrir_dialogue_envoi_email(d)

        def tenter_conversion():
            d = selection_holder['selected_row']
            if not d:
                ui.notify("Veuillez sélectionner un devis.", type="warning")
                return
            
            devis_id = d.get('id')
            num_dev = d.get('numero_devis')
            
            if devis_id:
                convertir_devis_en_prestation(devis_id, num_dev, charger_donnees)
            else:
                ui.notify("Erreur : Impossible de lire l'identifiant du devis.", type="negative")

        def tenter_edition():
            d = selection_holder['selected_row']
            if not d:
                return
            ouvrir_dialogue_devis(devis_id=d['id'])

        def tenter_refus():
            d = selection_holder['selected_row']
            if not d:
                return
            client_db = database.get_client()
            try:
                client_db.table("devis").update({"statut": "Refusé"}).eq("id", d['id']).execute()
            except Exception as e:
                ui.notify(f"Erreur : {e}", type="negative")
                return

            ui.notify(f"Devis {d['numero_devis']} marqué comme Refusé.", type="warning")
            charger_donnees()

        def tenter_suppression():
            d = selection_holder['selected_row']
            if not d:
                return
            confirmer_suppression(d['id'], d['numero_devis'])

        # --- DIALOGUE CRÉATION / ÉDITION DEVIS ---
        def ouvrir_dialogue_devis(devis_id=None):
            is_edit = devis_id is not None
            client_db = database.get_client()
            try:
                res_clients = client_db.table("clients").select("id, nom_societe, sans_tva").order("nom_societe").execute()
                clients_rows = res_clients.data or []
                clients_dict = {c['id']: c['nom_societe'] for c in clients_rows}
                clients_tva_map = {c['id']: bool(c['sans_tva']) for c in clients_rows}

                params = database.recuperer_parametres()
                entreprise_exoneree = bool(params.get("tva_exoneree", 1))

                if not clients_dict:
                    ui.notify("Veuillez d'abord enregistrer au moins un client.", type="warning")
                    return

                devis_data = None
                items_data = []
                if is_edit:
                    res_d = client_db.table("devis").select("*").eq("id", devis_id).execute()
                    devis_data = res_d.data[0] if res_d.data else None
                    res_items = client_db.table("devis_items").select("*").eq("devis_id", devis_id).execute()
                    items_data = res_items.data or []
            except Exception as e:
                ui.notify(f"Erreur d'initialisation du dialogue : {e}", type="negative")
                return

            statut_actuel = devis_data['statut'] if is_edit else "Brouillon"

            dialog = ui.dialog()
            with dialog, ui.card().classes("w-full max-w-6xl p-6 space-y-4"):
                titre = f"Modifier Devis {devis_data['numero_devis']}" if is_edit else "Créer un Devis"

                with ui.row().classes("w-full justify-between items-center border-b pb-2"):
                    ui.label(titre).classes("text-xl font-bold text-slate-800")
                    ui.badge(statut_actuel).props("color=blue outline font-bold").classes("text-sm p-2")

                # GRANDE LIGNE EN 2 COLONNES
                with ui.row().classes("w-full gap-6 items-start"):

                    # COLONNE DE GAUCHE : Paramètres & Client
                    with ui.column().classes("w-96 gap-4"):
                        ui.label("Paramètres & Client").classes("text-xs font-bold text-slate-500 uppercase")

                        client_select = ui.select(
                            options=clients_dict,
                            value=devis_data['client_id'] if is_edit else list(clients_dict.keys())[0],
                            label="Client *"
                        ).classes("w-full")

                        with ui.row().classes("w-full gap-2"):
                            date_crea_val = devis_data['date_creation'] if is_edit else datetime.now().strftime("%Y-%m-%d")
                            date_crea = ui.input("Date d'émission", value=date_crea_val).props("readonly dense outlined").classes("flex-1 bg-slate-50")

                            duree_options = {15: "15 jours", 30: "1 mois", 60: "2 mois", 90: "3 mois"}
                            duree_select = ui.select(options=duree_options, value=30, label="Validité").props("dense outlined").classes("w-28")

                        with ui.row().classes("w-full gap-2"):
                            date_val_defaut = devis_data['date_validite'] if is_edit else (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
                            date_val = ui.input("Date d'échéance", value=date_val_defaut).props("readonly dense outlined").classes("flex-1 bg-slate-50")

                            date_exec_val = devis_data['date_prevue_execution'] if is_edit else ""
                            date_exec = ui.input("Exécution prévue", value=date_exec_val).props("dense outlined").classes("flex-1")
                            with date_exec:
                                with ui.menu() as menu_cal:
                                    ui.date().bind_value(date_exec)
                                with date_exec.add_slot('append'):
                                    ui.icon('event').classes('cursor-pointer').on('click', menu_cal.open)

                        def recalculer_echeance(e):
                            try:
                                dt_crea = datetime.strptime(date_crea.value, "%Y-%m-%d")
                                dt_val = dt_crea + timedelta(days=int(e.value))
                                date_val.value = dt_val.strftime("%Y-%m-%d")
                            except Exception:
                                pass

                        duree_select.on_value_change(recalculer_echeance)
                        remarque_in = ui.textarea("Remarques / Conditions particulières", value=devis_data['remarque'] if is_edit else "").classes("w-full mt-2")

                    # COLONNE DE DROITE : Lignes & Totaux
                    with ui.column().classes("flex-1 gap-4"):
                        ui.label("Lignes du Devis & Totaux").classes("text-xs font-bold text-slate-500 uppercase")

                        lignes_container = ui.column().classes("w-full space-y-2 max-h-72 overflow-y-auto pr-1")
                        lignes_state = []

                        with ui.row().classes("w-full justify-between items-center p-4 bg-slate-50 border border-slate-200 rounded-xl mt-2"):
                            with ui.column().classes("gap-0"):
                                ui.label("Total HT :").classes("text-xs text-slate-500 uppercase font-bold")
                                lbl_total_ht = ui.label("0.00 €").classes("font-bold text-base text-slate-800")

                            with ui.column().classes("gap-0"):
                                ui.label("Total TVA :").classes("text-xs text-slate-500 uppercase font-bold")
                                lbl_total_tva = ui.label("0.00 €").classes("text-sm text-slate-600")

                            with ui.column().classes("gap-0 items-end"):
                                ui.label("Total TTC :").classes("text-xs text-slate-500 uppercase font-bold")
                                lbl_total_ttc = ui.label("0.00 €").classes("font-extrabold text-xl text-primary")

                def calculer_totaux():
                    tot_ht = 0.0
                    tot_tva = 0.0
                    client_id = client_select.value
                    client_exonere = clients_tva_map.get(client_id, False)
                    is_exo = entreprise_exoneree or client_exonere

                    for line in lignes_state:
                        qte = float(line['qte'].value or 0.0)
                        pu = float(line['pu'].value or 0.0)
                        taux_tva = float(line['tva'].value or 0.0) if not is_exo else 0.0

                        line_ht = qte * pu
                        line_tva = 0.0 if is_exo else line_ht * (taux_tva / 100.0)

                        tot_ht += line_ht
                        tot_tva += line_tva

                    tot_ttc = tot_ht + tot_tva
                    lbl_total_ht.set_text(f"{tot_ht:.2f} €")
                    lbl_total_tva.set_text(f"{tot_tva:.2f} €")
                    lbl_total_ttc.set_text(f"{tot_ttc:.2f} €")

                def ajouter_ligne(item_initial=None):
                    client_id = client_select.value
                    client_exonere = clients_tva_map.get(client_id, False)
                    is_exo = entreprise_exoneree or client_exonere

                    client_db = database.get_client()
                    try:
                        res_p = client_db.table("prestations").select("*").order("designation").execute()
                        prestations_base = res_p.data or []
                        
                        res_t = client_db.table("client_tarifs").select("*").eq("client_id", client_id).execute()
                        tarifs_specifiques = {t['prestation_id']: t for t in (res_t.data or [])}

                        prestations = []
                        for p in prestations_base:
                            t_spec = tarifs_specifiques.get(p['id'])
                            if t_spec and not t_spec.get('est_actif', True):
                                continue
                            prix_eff = t_spec['prix_specifique_ht'] if t_spec and t_spec.get('prix_specifique_ht') is not None else p['prix_ht']
                            prestations.append({
                                'id': p['id'],
                                'designation': p['designation'],
                                'unite': p.get('unite'),
                                'taux_tva': p['taux_tva'],
                                'prix_effectif': prix_eff
                            })
                    except Exception as e:
                        ui.notify(f"Erreur chargement prestations : {e}", type="negative")
                        return

                    if not prestations:
                        ui.notify("Aucune prestation disponible pour ce client.", type="warning")
                        return

                    p_options = {p['id']: f"{p['designation']} ({p['prix_effectif']:.2f} €)" for p in prestations}
                    p_details = {p['id']: p for p in prestations}

                    with lignes_container:
                        with ui.row().classes("w-full items-center gap-2 p-2 bg-slate-50 border rounded-lg") as row_element:
                            p_sel = ui.select(
                                options=p_options,
                                value=item_initial['prestation_id'] if item_initial else prestations[0]['id'],
                                label="Prestation"
                            ).classes("flex-1").props("dense outlined")

                            qte_in = ui.number(
                                label="Qté",
                                value=item_initial['quantite'] if item_initial else 1.0,
                                format="%.2f"
                            ).classes("w-20").props("dense outlined")

                            pu_in = ui.number(
                                label="Prix HT (€)",
                                value=item_initial['prix_unitaire_ht'] if item_initial else prestations[0]['prix_effectif'],
                                format="%.2f"
                            ).classes("w-28").props("dense outlined")

                            valeur_tva_init = 0.0 if is_exo else (item_initial['taux_tva'] if item_initial else prestations[0]['taux_tva'])
                            tva_in = ui.select(
                                options={0.0: "0%", 5.5: "5.5%", 10.0: "10%", 20.0: "20%"},
                                value=valeur_tva_init,
                                label="TVA"
                            ).classes("w-24").props("dense outlined")

                            if is_exo:
                                tva_in.props("disable")

                            btn_del = ui.button(icon="delete", color="negative").props("flat round dense")

                            line_obj = {"row": row_element, "prest": p_sel, "qte": qte_in, "pu": pu_in, "tva": tva_in}
                            lignes_state.append(line_obj)

                            def on_prestation_change(e, pu_field=pu_in, tva_field=tva_in):
                                selected_p = p_details.get(e.value)
                                if selected_p:
                                    pu_field.value = selected_p['prix_effectif']
                                    tva_field.value = 0.0 if is_exo else selected_p['taux_tva']
                                calculer_totaux()

                            def supprimer_ligne(obj=line_obj):
                                lignes_container.remove(obj['row'])
                                lignes_state.remove(obj)
                                calculer_totaux()

                            p_sel.on_value_change(on_prestation_change)
                            qte_in.on_value_change(lambda _: calculer_totaux())
                            pu_in.on_value_change(lambda _: calculer_totaux())
                            tva_in.on_value_change(lambda _: calculer_totaux())
                            btn_del.on_click(supprimer_ligne)

                    calculer_totaux()

                def on_client_change(e):
                    lignes_container.clear()
                    lignes_state.clear()
                    ajouter_ligne()

                client_select.on_value_change(on_client_change)

                ui.button("Ajouter une prestation", icon="add", on_click=lambda: ajouter_ligne()).props("color=emerald outline dense").classes("mt-1")

                if is_edit and items_data:
                    for item in items_data:
                        ajouter_ligne(item)
                else:
                    ajouter_ligne()

                def sauvegarder():
                    if not lignes_state:
                        ui.notify("Veuillez ajouter au moins une ligne au devis.", type="warning")
                        return

                    tot_ht = 0.0
                    tot_tva = 0.0
                    client_exonere = clients_tva_map.get(client_select.value, False)
                    is_exo = entreprise_exoneree or client_exonere

                    for line in lignes_state:
                        qte = float(line['qte'].value or 0.0)
                        pu = float(line['pu'].value or 0.0)
                        taux_tva = 0.0 if is_exo else float(line['tva'].value or 0.0)

                        line_ht = qte * pu
                        line_tva = 0.0 if is_exo else line_ht * (taux_tva / 100.0)

                        tot_ht += line_ht
                        tot_tva += line_tva

                    tot_ttc = tot_ht + tot_tva

                    client_db = database.get_client()
                    try:
                        if is_edit:
                            num_devis = devis_data['numero_devis']
                            client_db.table("devis").update({
                                "client_id": client_select.value,
                                "date_creation": date_crea.value,
                                "date_validite": date_val.value,
                                "date_prevue_execution": date_exec.value,
                                "statut": statut_actuel,
                                "total_ht": tot_ht,
                                "total_tva": tot_tva,
                                "total_ttc": tot_ttc,
                                "remarque": remarque_in.value
                            }).eq("id", devis_id).execute()

                            client_db.table("devis_items").delete().eq("devis_id", devis_id).execute()
                            target_devis_id = devis_id
                        else:
                            num_devis = database.generer_numero_document("DEV")
                            res_ins = client_db.table("devis").insert({
                                "numero_devis": num_devis,
                                "client_id": client_select.value,
                                "date_creation": date_crea.value,
                                "date_validite": date_val.value,
                                "date_prevue_execution": date_exec.value,
                                "statut": "Brouillon",
                                "total_ht": tot_ht,
                                "total_tva": tot_tva,
                                "total_ttc": tot_ttc,
                                "remarque": remarque_in.value
                            }).execute()
                            target_devis_id = res_ins.data[0]['id']

                        items_payload = []
                        for line in lignes_state:
                            taux_tva_sauvegarder = 0.0 if is_exo else float(line['tva'].value or 0.0)
                            items_payload.append({
                                "devis_id": target_devis_id,
                                "prestation_id": line['prest'].value,
                                "quantite": float(line['qte'].value or 0.0),
                                "prix_unitaire_ht": float(line['pu'].value or 0.0),
                                "taux_tva": taux_tva_sauvegarder
                            })
                        
                        if items_payload:
                            client_db.table("devis_items").insert(items_payload).execute()

                    except Exception as e:
                        ui.notify(f"Erreur lors de la sauvegarde : {e}", type="negative")
                        return

                    ui.notify(f"Devis {num_devis} enregistré !", type="positive")
                    dialog.close()
                    charger_donnees()

                with ui.row().classes("w-full justify-end gap-2 mt-4 pt-2 border-t"):
                    ui.button("Annuler", on_click=dialog.close).props("flat color=slate")
                    ui.button("Enregistrer le devis", icon="check", on_click=sauvegarder).props("color=primary font-bold")

            dialog.open()

        def ouvrir_dialogue_envoi_email(devis):
            client_db = database.get_client()
            try:
                res_c = client_db.table("clients").select("nom_societe, email").eq("id", devis['client_id']).execute()
                client = res_c.data[0] if res_c.data else None
            except Exception as e:
                ui.notify(f"Erreur : {e}", type="negative")
                return

            email_client = client['email'] if client else ""
            if not email_client:
                ui.notify("Attention : Ce client n'a pas d'adresse e-mail renseignée !", type="warning", icon="warning")
                return

            dialog = ui.dialog()
            with dialog, ui.card().classes("w-full max-w-md p-6 space-y-4"):
                ui.label(f"Envoyer le Devis {devis['numero_devis']}").classes("text-xl font-bold text-slate-800")
                ui.label(f"Le devis sera envoyé à : {client['nom_societe']} ({email_client})").classes("text-sm text-slate-600")

                def confirmer_envoi():
                    dossier_export = pdf_generator.obtenir_chemin_export(client['nom_societe'], type_doc="Devis")
                    filename = f"Devis_{devis['numero_devis']}.pdf"
                    pdf_path = os.path.join(dossier_export, filename)
                    pdf_generator.generer_pdf_devis(devis['id'], pdf_path)

                    succes, message = utils.envoyer_email_devis(
                        email_destinataire=email_client,
                        nom_client=client['nom_societe'],
                        num_devis=devis['numero_devis'],
                        montant_ttc=devis['total_ttc'],
                        pdf_path=pdf_path
                    )

                    if succes:
                        client_db = database.get_client()
                        try:
                            client_db.table("devis").update({"statut": "Envoyé"}).eq("id", devis['id']).execute()
                        except Exception as e:
                            ui.notify(f"Erreur mise à jour statut : {e}", type="negative")
                            return

                        ui.notify(f"Devis {devis['numero_devis']} envoyé !", type="positive", icon="send")
                        dialog.close()
                        charger_donnees()
                    else:
                        ui.notify(message, type="negative")

                with ui.row().classes("w-full justify-end gap-2 mt-4"):
                    ui.button("Annuler", on_click=dialog.close).props("flat color=slate")
                    ui.button("Envoyer par E-mail", icon="send", on_click=confirmer_envoi).props("color=primary font-bold")

            dialog.open()

        def confirmer_suppression(devis_id, num_devis):
            dialog = ui.dialog()
            with dialog, ui.card().classes("p-6 space-y-4 max-w-md"):
                ui.label("Confirmer la suppression").classes("text-lg font-bold text-slate-800")
                ui.label(f"Voulez-vous supprimer définitivement le devis « {num_devis} » ?").classes("text-slate-600")

                def supprimer():
                    client_db = database.get_client()
                    try:
                        client_db.table("devis").delete().eq("id", devis_id).execute()
                    except Exception as e:
                        ui.notify(f"Erreur lors de la suppression : {e}", type="negative")
                        return

                    dialog.close()
                    ui.notify("Devis supprimé.", type="info")
                    charger_donnees()

                with ui.row().classes("w-full justify-end gap-2"):
                    ui.button("Annuler", on_click=dialog.close).props("flat color=slate")
                    ui.button("Supprimer", on_click=supprimer).props("color=negative font-bold")

            dialog.open()

        charger_donnees()