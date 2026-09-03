from datetime import datetime, timedelta
from nicegui import ui
import database


def calculer_statut_prestation(
    date_interv_str, facture_id=None, statut_facture=None
):
    """Calcule automatiquement le statut selon la date et la facturation."""
    if facture_id:
        if statut_facture == "Payée":
            return "Payée"
        return "Facturée"

    if not date_interv_str:
        return "Planifiée"

    try:
        date_obj = datetime.strptime(
            str(date_interv_str).strip(), "%Y-%m-%d"
        ).date()
        aujourdhui = datetime.now().date()
        return "Planifiée" if date_obj > aujourdhui else "Réalisée"
    except ValueError:
        return "Planifiée"


def calculer_duree_heures(h_debut_str, h_fin_str):
    """Calcule la durée en heures décimales entre deux chaînes HH:MM."""
    try:
        fmt = "%H:%M"
        t1 = datetime.strptime(h_debut_str.strip(), fmt)
        t2 = datetime.strptime(h_fin_str.strip(), fmt)
        diff = (t2 - t1).total_seconds() / 3600.0
        if diff < 0:
            diff += 24.0
        return round(diff, 2) if diff > 0 else 1.0
    except Exception:
        return 1.0


def formater_date_fr(date_str):
    """Convertit AAAA-MM-JJ en JJ/MM/AAAA pour l'affichage."""
    if not date_str:
        return ""
    try:
        d = datetime.strptime(str(date_str).strip(), "%Y-%m-%d")
        return d.strftime("%d/%m/%Y")
    except Exception:
        return str(date_str)


def render_interventions():
    ui.label("Suivi des Prestations Réalisées").classes(
        "text-2xl font-bold text-slate-800 mb-6"
    )

    with ui.card().classes(
        "w-full p-6 bg-white border border-slate-200 rounded-xl space-y-4"
    ):
        top_bar = ui.row().classes(
            "w-full justify-between items-center mb-2 gap-4 flex-wrap"
        )
        selection_holder = {"selected_row": None}

        columns = [
            {
                "headerName": "N° Intervention",
                "field": "numero_intervention",
                "align": "left",
                "sortable": True,
                "filter": "agTextColumnFilter",
            },
            {
                "headerName": "Date",
                "field": "date_fr",
                "align": "center",
                "sortable": True,
                "filter": "agDateColumnFilter",
            },
            {
                "headerName": "Client",
                "field": "client_nom",
                "align": "left",
                "sortable": True,
                "filter": "agTextColumnFilter",
            },
            {
                "headerName": "Site",
                "field": "site_txt",
                "align": "left",
                "sortable": True,
                "filter": "agTextColumnFilter",
            },
            {
                "headerName": "Prestation",
                "field": "nom_prestation_txt",
                "align": "left",
                "sortable": True,
                "filter": "agTextColumnFilter",
            },
            {
                "headerName": "Durée (h)",
                "field": "quantite",
                "align": "center",
                "sortable": True,
            },
            {
                "headerName": "Horaires",
                "field": "heure_txt",
                "align": "center",
                "sortable": True,
            },
            {
                "headerName": "Montant HT",
                "field": "prix_txt",
                "align": "right",
                "sortable": True,
            },
            {
                "headerName": "Commentaire",
                "field": "commentaire_txt",
                "align": "left",
                "sortable": True,
                "filter": "agTextColumnFilter",
            },
            {
                "headerName": "Statut",
                "field": "statut_dynamique",
                "align": "center",
                "sortable": True,
                "filter": "agTextColumnFilter",
                "cellClassRules": {
                    "bg-blue-100 text-blue-800 font-bold border-blue-300": (
                        'x === "Planifiée"'
                    ),
                    "bg-amber-100 text-amber-800 font-bold border-amber-300": (
                        'x === "Réalisée"'
                    ),
                    (
                        "bg-orange-100 text-orange-800 font-bold"
                        " border-orange-300"
                    ): 'x === "Facturée"',
                    (
                        "bg-emerald-100 text-emerald-800 font-bold"
                        " border-emerald-300"
                    ): 'x === "Payée"',
                },
            },
        ]

        grid = ui.aggrid(
            {
                "columnDefs": columns,
                "rowData": [],
                "rowSelection": "single",
                "pagination": True,
                "paginationPageSize": 12,
                "defaultColDef": {
                    "resizable": True,
                    "sortable": True,
                    "filter": True,
                },
            }
        ).classes("h-96 w-full cursor-pointer")

        with ui.row().classes(
            "w-full justify-between items-center pt-3 border-t border-slate-200 min-h-[48px]"
        ):
            action_label = ui.label(
                "💡 Cliquez sur une ligne du tableau pour l'éditer ou la supprimer."
            ).classes("text-xs text-slate-400 font-medium italic py-1")

            with ui.row().classes("items-center gap-3") as action_buttons:
                btn_editer = ui.button(
                    "Éditer",
                    icon="edit",
                    on_click=lambda: tenter_edition(),
                ).props("dense outline color=primary font-bold")
                btn_supprimer = ui.button(
                    "Supprimer",
                    icon="delete",
                    on_click=lambda: tenter_suppression(),
                ).props("dense flat color=negative font-bold")
                btn_editer.set_visibility(False)
                btn_supprimer.set_visibility(False)

        def update_action_bar():
            selected = selection_holder["selected_row"]
            if selected:
                num = selected.get("numero_intervention", "")
                action_label.set_text(f"Sélection : {num}")
                action_label.classes(
                    replace=(
                        "text-sm font-bold text-slate-700 bg-slate-100 px-3"
                        " py-1.5 rounded-lg border border-slate-200"
                    )
                )
                btn_editer.set_visibility(True)
                btn_supprimer.set_visibility(True)
            else:
                action_label.set_text(
                    "💡 Cliquez sur une ligne du tableau pour l'éditer ou la supprimer."
                )
                action_label.classes(
                    replace=(
                        "text-xs text-slate-400 font-medium italic py-1"
                    )
                )
                btn_editer.set_visibility(False)
                btn_supprimer.set_visibility(False)

        def on_cell_clicked(e):
            data = e.args.get("data")
            if data:
                selection_holder["selected_row"] = data
                update_action_bar()

        grid.on("cellClicked", on_cell_clicked)

        def charger_donnees():
            selection_holder["selected_row"] = None
            update_action_bar()

            filtre_statut = select_statut.value
            filtre_client = select_client.value
            filtre_mois = select_mois.value
            filtre_annee = select_annee.value
            masquer_payees = checkbox_payees.value

            client_db = database.get_client()
            try:
                # Requête Supabase avec jointures (clients, prestations, etablissements, factures)
                response = (
                    client_db.table("interventions")
                    .select(
                        "*, clients(nom_societe), prestations(designation), etablissements(nom_site), factures(statut)"
                    )
                    .order("date", desc=True)
                    .order("id", desc=True)
                    .execute()
                )
                rows = response.data or []
            except Exception as e:
                ui.notify(f"Erreur de chargement des interventions : {e}", type="negative")
                rows = []

            prestations = []
            for r in rows:
                item = dict(r)
                
                # Récupération sécurisée des données de jointure Supabase (dicts ou listes)
                client_rel = item.get("clients")
                item["client_nom"] = client_rel.get("nom_societe") if isinstance(client_rel, dict) else (client_rel[0].get("nom_societe") if client_rel and isinstance(client_rel, list) else "-")

                prest_rel = item.get("prestations")
                item["prestation_nom"] = prest_rel.get("designation") if isinstance(prest_rel, dict) else (prest_rel[0].get("designation") if prest_rel and isinstance(prest_rel, list) else None)

                etab_rel = item.get("etablissements")
                item["etablissement_nom"] = etab_rel.get("nom_site") if isinstance(etab_rel, dict) else (etab_rel[0].get("nom_site") if etab_rel and isinstance(etab_rel, list) else None)

                fact_rel = item.get("factures")
                statut_facture = fact_rel.get("statut") if isinstance(fact_rel, dict) else (fact_rel[0].get("statut") if fact_rel and isinstance(fact_rel, list) else None)
                
                statut_dyn = calculer_statut_prestation(
                    item.get("date"),
                    item.get("facture_id"),
                    statut_facture,
                )
                item["statut_dynamique"] = statut_dyn
                item["date_fr"] = formater_date_fr(item.get("date"))
                item["nom_prestation_txt"] = (
                    item["prestation_nom"] or "Prestation libre"
                )
                item["site_txt"] = item["etablissement_nom"] or "-"
                item["heure_txt"] = (
                    f"{item.get('heure_debut') or ''} - {item.get('heure_fin') or ''}".strip(
                        " -"
                    )
                    or "-"
                )
                item["prix_txt"] = (
                    f"{(item.get('prix_final_ht') or 0.0) * (item.get('quantite') or 1.0):.2f} € HT"
                )
                item["commentaire_txt"] = item.get("commentaire") or ""

                date_val = str(item.get("date", "")).strip()
                if date_val and len(date_val) >= 10:
                    annee_str = date_val[0:4]
                    mois_str = date_val[5:7]
                else:
                    annee_str = ""
                    mois_str = ""

                if filtre_annee != "Tous" and annee_str != filtre_annee:
                    continue
                if filtre_mois != "Tous" and mois_str != filtre_mois:
                    continue
                if masquer_payees and statut_dyn == "Payée":
                    continue
                if filtre_statut != "Tous" and statut_dyn != filtre_statut:
                    continue
                if (
                    filtre_client != "Tous"
                    and str(item.get("client_id")) != str(filtre_client)
                ):
                    continue

                prestations.append(item)

            grid.options["rowData"] = prestations
            grid.update()

        # CONSTITUTION DE LA BARRE DU HAUT
        with top_bar:
            with ui.row().classes("items-center gap-3 flex-wrap flex-1"):
                ui.label("Prestations").classes("text-lg font-semibold text-slate-700")

                mois_options = {
                    "Tous": "Tous les mois",
                    "01": "Janvier",
                    "02": "Février",
                    "03": "Mars",
                    "04": "Avril",
                    "05": "Mai",
                    "06": "Juin",
                    "07": "Juillet",
                    "08": "Août",
                    "09": "Septembre",
                    "10": "Octobre",
                    "11": "Novembre",
                    "12": "Décembre",
                }
                select_mois = ui.select(
                    mois_options, value="Tous", label="Mois"
                ).classes("w-36")

                # Récupération dynamique des années depuis Supabase
                client_db = database.get_client()
                try:
                    res_annees = client_db.table("interventions").select("date").execute()
                    annees_disponibles = sorted(
                        list(set(row["date"][:4] for row in (res_annees.data or []) if row.get("date"))),
                        reverse=True
                    )
                except Exception:
                    annees_disponibles = []

                annees_options = {"Tous": "Toutes"}
                annee_actuelle = str(datetime.now().year)
                if not annees_disponibles:
                    annees_disponibles = [annee_actuelle]

                for a in annees_disponibles:
                    annees_options[a] = a

                val_annee_defaut = (
                    annee_actuelle if annee_actuelle in annees_disponibles else annees_disponibles[0]
                )

                select_annee = ui.select(
                    annees_options,
                    value=val_annee_defaut,
                    label="Année",
                ).classes("w-28")

                select_statut = ui.select(
                    ["Tous", "Planifiée", "Réalisée", "Facturée", "Payée"],
                    value="Tous",
                    label="Filtrer par Statut",
                ).classes("w-36")

                clients_list = database.recuperer_tous_les_clients()
                client_filter_opts = {"Tous": "Tous les clients"}
                client_filter_opts.update(
                    {str(c["id"]): c["nom_societe"] for c in clients_list}
                )

                select_client = ui.select(
                    client_filter_opts, value="Tous", label="Filtrer par Client"
                ).classes("w-44")

                checkbox_payees = ui.checkbox(
                    "Masquer payées", value=False
                ).classes("text-slate-700 font-medium text-xs")

                select_mois.on_value_change(lambda _: charger_donnees())
                select_annee.on_value_change(lambda _: charger_donnees())
                select_statut.on_value_change(lambda _: charger_donnees())
                select_client.on_value_change(lambda _: charger_donnees())
                checkbox_payees.on_value_change(lambda _: charger_donnees())

            ui.button(
                "Nouvelle Prestation",
                icon="add",
                on_click=lambda: ouvrir_dialog_intervention(),
            ).props("color=primary font-bold")

        def tenter_edition():
            interv = selection_holder["selected_row"]
            if not interv:
                return
            statut = interv.get("statut_dynamique", "")
            if statut in ["Facturée", "Payée"]:
                ui.notify(
                    f"Impossible de modifier la prestation « {interv['numero_intervention']} » : elle est déjà {statut.lower()} !",
                    type="warning",
                    icon="lock",
                )
                return

            if statut == "Réalisée":
                ui.notify(
                    f"Attention : la prestation « {interv['numero_intervention']} » est déjà indiquée comme RÉALISÉE.",
                    type="warning",
                    icon="warning",
                )

            ouvrir_dialog_intervention(interv_existante=interv)

        def tenter_suppression():
            interv = selection_holder["selected_row"]
            if not interv:
                return
            statut = interv.get("statut_dynamique", "")
            if statut in ["Facturée", "Payée"]:
                ui.notify(
                    f"Impossible de supprimer la prestation « {interv['numero_intervention']} » : elle est déjà {statut.lower()} !",
                    type="warning",
                    icon="lock",
                )
                return

            confirmer_suppression(
                interv["id"],
                interv["numero_intervention"],
                statut_realisee=(statut == "Réalisée"),
            )

        def ouvrir_dialog_intervention(interv_existante=None):
            is_edition = interv_existante is not None
            titre = (
                f"Éditer Prestation « {interv_existante['numero_intervention']} »"
                if is_edition
                else "Nouvelle Prestation Directe"
            )

            clients = database.recuperer_tous_les_clients()
            if not clients:
                ui.notify("Veuillez d'abord créer un client.", type="warning")
                return

            dialog = ui.dialog()
            with dialog, ui.card().classes(
                "p-6 space-y-4 w-full max-w-lg bg-white rounded-2xl shadow-xl"
            ):
                ui.label(titre).classes(
                    "text-xl font-bold text-slate-800 border-b pb-2 w-full"
                )

                if (
                    is_edition
                    and interv_existante.get("statut_dynamique") == "Réalisée"
                ):
                    ui.label(
                        "⚠️ Cette prestation est marquée comme RÉALISÉE. Toute modification impactera la facture à venir."
                    ).classes(
                        "p-2 bg-amber-50 text-amber-800 border border-amber-200"
                        " rounded text-xs w-full"
                    )

                client_options = {c["id"]: c["nom_societe"] for c in clients}
                val_client_init = (
                    interv_existante["client_id"]
                    if is_edition
                    else clients[0]["id"]
                )
                client_select = ui.select(
                    client_options, label="Client", value=val_client_init
                ).classes("w-full").props("dense outlined")

                etab_select = ui.select(
                    {}, label="Site / Établissement"
                ).classes("w-full").props("dense outlined")
                prest_select = ui.select(
                    {}, label="Cours / Prestation"
                ).classes("w-full").props("dense outlined")

                def charger_prestations_client(client_id):
                    client_db = database.get_client()
                    try:
                        # Récupération des tarifs spécifiques
                        res_tarifs = (
                            client_db.table("client_tarifs")
                            .select("prestation_id, prix_specifique_ht, prestations(id, designation, prix_ht)")
                            .eq("client_id", client_id)
                            .eq("est_actif", True)
                            .execute()
                        )
                        tarifs_spec = res_tarifs.data or []

                        options = {}
                        if tarifs_spec:
                            for t in tarifs_spec:
                                p_info = t.get("prestations") or {}
                                px = (
                                    t["prix_specifique_ht"]
                                    if t.get("prix_specifique_ht") is not None
                                    else p_info.get("prix_ht", 0.0)
                                )
                                p_id = t.get("prestation_id")
                                designation = p_info.get("designation", "Prestation")
                                options[p_id] = (
                                    f"{designation} ({px:.2f} €/h - Tarif spécifique)"
                                )
                        else:
                            res_cat = client_db.table("prestations").select("*").order("designation").execute()
                            cat = res_cat.data or []
                            for p in cat:
                                options[p["id"]] = (
                                    f"{p['designation']} ({p['prix_ht']:.2f} €/h)"
                                )
                    except Exception:
                        options = {}

                    prest_select.options = options
                    val_prest_init = (
                        interv_existante.get("prestation_id")
                        if (is_edition and interv_existante.get("prestation_id"))
                        else (list(options.keys())[0] if options else None)
                    )
                    prest_select.value = val_prest_init

                def charger_etablissements(client_id):
                    client_db = database.get_client()
                    try:
                        res_etabs = client_db.table("etablissements").select("*").eq("client_id", client_id).execute()
                        etabs = res_etabs.data or []
                    except Exception:
                        etabs = []

                    if etabs:
                        options = {e["id"]: e["nom_site"] for e in etabs}
                        etab_select.options = options
                        etab_select.value = (
                            interv_existante.get("etablissement_id")
                            if is_edition
                            else etabs[0]["id"]
                        )
                        etab_select.set_visibility(True)
                    else:
                        etab_select.options = {}
                        etab_select.value = None
                        etab_select.set_visibility(False)

                charger_etablissements(val_client_init)
                charger_prestations_client(val_client_init)

                client_select.on_value_change(
                    lambda e: (
                        charger_etablissements(e.value),
                        charger_prestations_client(e.value),
                    )
                )

                val_date_init = (
                    interv_existante.get("date")
                    if is_edition
                    else datetime.now().strftime("%Y-%m-%d")
                )
                date_input = ui.input(
                    "Date d'exécution", value=val_date_init
                ).props("dense outlined").classes("w-full")
                with date_input:
                    with ui.menu() as menu_date:
                        ui.date().bind_value(date_input)
                    with date_input.add_slot("append"):
                        ui.icon("event").classes("cursor-pointer").on(
                            "click", menu_date.open
                        )

                val_h_deb = (
                    interv_existante.get("heure_debut")
                    if (is_edition and interv_existante.get("heure_debut"))
                    else "14:00"
                )
                val_h_fin = (
                    interv_existante.get("heure_fin")
                    if (is_edition and interv_existante.get("heure_fin"))
                    else "16:00"
                )

                with ui.row().classes("w-full gap-4 items-center"):
                    h_debut = ui.input("Début", value=val_h_deb).props(
                        "dense outlined"
                    ).classes("w-1/3")
                    with h_debut:
                        with ui.menu() as menu_h1:
                            ui.time().props(
                                "format24h minute-step=5"
                            ).bind_value(h_debut)
                        with h_debut.add_slot("append"):
                            ui.icon("schedule").classes("cursor-pointer").on(
                                "click", menu_h1.open
                            )

                    h_fin = ui.input("Fin", value=val_h_fin).props(
                        "dense outlined"
                    ).classes("w-1/3")
                    with h_fin:
                        with ui.menu() as menu_h2:
                            ui.time().props(
                                "format24h minute-step=5"
                            ).bind_value(h_fin)
                        with h_fin.add_slot("append"):
                            ui.icon("schedule").classes("cursor-pointer").on(
                                "click", menu_h2.open
                            )

                    duree_label = ui.label("Durée : 2.0 h").classes(
                        "w-1/4 text-sm font-semibold text-slate-700 text-center"
                        " bg-slate-100 py-2 rounded"
                    )

                def maj_duree():
                    duree = calculer_duree_heures(h_debut.value, h_fin.value)
                    duree_label.set_text(f"Durée : {duree} h")

                h_debut.on_value_change(lambda _: maj_duree())
                h_fin.on_value_change(lambda _: maj_duree())
                maj_duree()

                remarque_input = ui.input(
                    "Remarques / Commentaire",
                    value=(
                        interv_existante.get("commentaire")
                        if (is_edition and interv_existante.get("commentaire"))
                        else ""
                    ),
                ).classes("w-full").props("dense outlined")

                def sauvegarder():
                    client_id = client_select.value
                    etab_id = etab_select.value
                    prest_id = prest_select.value
                    date_val = date_input.value or datetime.now().strftime(
                        "%Y-%m-%d"
                    )
                    qte_calc = calculer_duree_heures(
                        h_debut.value, h_fin.value
                    )

                    if not prest_id:
                        ui.notify(
                            "Veuillez sélectionner une prestation.",
                            type="warning",
                        )
                        return

                    client_db = database.get_client()
                    try:
                        # Récupération tarif spécifique ou standard
                        res_spec = (
                            client_db.table("client_tarifs")
                            .select("prix_specifique_ht")
                            .eq("client_id", client_id)
                            .eq("prestation_id", prest_id)
                            .execute()
                        )
                        spec_data = res_spec.data[0] if res_spec.data else None

                        res_prest = client_db.table("prestations").select("*").eq("id", prest_id).execute()
                        prest_info = res_prest.data[0] if res_prest.data else {}

                        prix_ht = (
                            spec_data["prix_specifique_ht"]
                            if (
                                spec_data
                                and spec_data.get("prix_specifique_ht") is not None
                            )
                            else (
                                prest_info.get("prix_ht", 0.0)
                            )
                        )
                        taux_tva = prest_info.get("taux_tva", 0.0)

                        payload = {
                            "client_id": client_id,
                            "etablissement_id": etab_id,
                            "prestation_id": prest_id,
                            "date": date_val,
                            "heure_debut": h_debut.value,
                            "heure_fin": h_fin.value,
                            "quantite": qte_calc,
                            "prix_final_ht": prix_ht,
                            "taux_tva": taux_tva,
                            "commentaire": remarque_input.value,
                        }

                        if is_edition:
                            client_db.table("interventions").update(payload).eq("id", interv_existante["id"]).execute()
                            ui.notify("Prestation mise à jour !", type="positive")
                        else:
                            num_interv = database.generer_numero_document("PREST")
                            payload["numero_intervention"] = num_interv
                            payload["statut"] = "En attente"
                            client_db.table("interventions").insert(payload).execute()
                            ui.notify(f"Prestation {num_interv} créée !", type="positive")

                    except Exception as e:
                        ui.notify(f"Erreur lors de la sauvegarde : {e}", type="negative")
                        return

                    dialog.close()
                    charger_donnees()

                with ui.row().classes("w-full justify-end gap-2 mt-4"):
                    ui.button("Annuler", on_click=dialog.close).props(
                        "flat color=slate"
                    )
                    ui.button(
                        "Enregistrer", icon="check", on_click=sauvegarder
                    ).props("color=positive font-bold")

            dialog.open()

        def confirmer_suppression(
            interv_id, num_interv, statut_realisee=False
        ):
            dialog = ui.dialog()
            with dialog, ui.card().classes(
                "p-6 space-y-4 max-w-md bg-white rounded-2xl shadow-xl"
            ):
                ui.label("Confirmer la suppression").classes(
                    "text-lg font-bold text-slate-800"
                )

                if statut_realisee:
                    ui.label(
                        f"⚠️ La prestation « {num_interv} » est déjà marquée comme RÉALISÉE. Êtes-vous sûr de vouloir la supprimer ?"
                    ).classes(
                        "text-amber-700 bg-amber-50 p-3 border border-amber-200"
                        " rounded text-sm font-medium"
                    )
                else:
                    ui.label(
                        f"Voulez-vous supprimer la prestation « {num_interv} » ?"
                    ).classes("text-slate-600")

                def supprimer():
                    client_db = database.get_client()
                    try:
                        client_db.table("interventions").delete().eq("id", interv_id).execute()
                        dialog.close()
                        ui.notify("Prestation supprimée.", type="info")
                        charger_donnees()
                    except Exception as e:
                        ui.notify(f"Erreur lors de la suppression : {e}", type="negative")

                with ui.row().classes("w-full justify-end gap-2"):
                    ui.button("Annuler", on_click=dialog.close).props(
                        "flat color=slate"
                    )
                    ui.button("Supprimer", on_click=supprimer).props(
                        "negative font-bold"
                    )

            dialog.open()

        charger_donnees()