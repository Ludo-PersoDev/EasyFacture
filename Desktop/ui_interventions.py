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
        if diff < 0:  # Gère le cas où l'intervention se termine après minuit
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

        # ESTHÉTIQUE & FILTRES EN HAUT
        top_bar = ui.row().classes(
            "w-full justify-between items-center mb-2 gap-4 flex-wrap"
        )

        selection_holder = {"selected_row": None}

        # Définition statique des colonnes AG Grid
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

        # Tableau fixe (créé une seule fois pour éviter de tout détruire au rafraîchissement)
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

        # BARRE D'ACTIONS EN BAS
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

            conn = database.get_conn()
            try:
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(interventions)")
                cols = [column[1] for column in cursor.fetchall()]
                has_facture_id = "facture_id" in cols

                query = f"""
                    SELECT 
                        i.*, 
                        c.nom_societe AS client_nom,
                        p.designation AS prestation_nom,
                        e.nom_site AS etablissement_nom
                        {', f.statut AS statut_facture' if has_facture_id else ', NULL AS facture_id, NULL AS statut_facture'}
                    FROM interventions i
                    JOIN clients c ON i.client_id = c.id
                    LEFT JOIN prestations p ON i.prestation_id = p.id
                    LEFT JOIN etablissements e ON i.etablissement_id = e.id
                    {'LEFT JOIN factures f ON i.facture_id = f.id' if has_facture_id else ''}
                    ORDER BY i.date DESC, i.id DESC
                """
                rows = conn.execute(query).fetchall()
            finally:
                conn.close()

            prestations = []
            for r in rows:
                item = dict(r)
                statut_dyn = calculer_statut_prestation(
                    item["date"],
                    item.get("facture_id"),
                    item.get("statut_facture"),
                )
                item["statut_dynamique"] = statut_dyn
                item["date_fr"] = formater_date_fr(item["date"])
                item["nom_prestation_txt"] = (
                    item["prestation_nom"] or "Prestation libre"
                )
                item["site_txt"] = item["etablissement_nom"] or "-"
                item["heure_txt"] = (
                    f"{item['heure_debut'] or ''} - {item['heure_fin'] or ''}".strip(
                        " -"
                    )
                    or "-"
                )
                item["prix_txt"] = (
                    f"{(item['prix_final_ht'] or 0.0) * (item['quantite'] or 1.0):.2f} € HT"
                )
                item["commentaire_txt"] = item["commentaire"] or ""

                # Application des filtres Mois / Année basés sur la date (AAAA-MM-JJ)
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
                    and str(item["client_id"]) != str(filtre_client)
                ):
                    continue

                prestations.append(item)

            grid.options["rowData"] = prestations
            grid.update()

        # CONSTITUTION DE LA BARRE DU HAUT
        with top_bar:
            with ui.row().classes("items-center gap-3 flex-wrap flex-1"):
                ui.label("Prestations").classes("text-lg font-semibold text-slate-700")

                # Options des mois
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

                # Récupération dynamique des années depuis la base de données
                conn_db = database.get_conn()
                try:
                    annees_db = conn_db.execute(
                        "SELECT DISTINCT SUBSTR(date, 1, 4) FROM interventions WHERE date IS NOT NULL AND date != '' ORDER BY date DESC"
                    ).fetchall()
                finally:
                    conn_db.close()

                annees_options = {"Tous": "Toutes"}
                annees_disponibles = [row[0] for row in annees_db if row[0]]
                
                annee_actuelle = str(datetime.now().year)
                if not annees_disponibles:
                    annees_disponibles = [annee_actuelle]

                for a in annees_disponibles:
                    annees_options[a] = a

                val_annee_defaut = annee_actuelle if annee_actuelle in annees_disponibles else annees_disponibles[0]

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

        # LOGIQUE SÉCURITÉ ÉDITION / SUPPRESSION
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

        # DIALOGUE DE CRÉATION / ÉDITION
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
                    conn = database.get_conn()
                    try:
                        tarifs_spec = conn.execute(
                            """
                            SELECT p.id, p.designation, ct.prix_specifique_ht, p.prix_ht
                            FROM client_tarifs ct
                            JOIN prestations p ON ct.prestation_id = p.id
                            WHERE ct.client_id=? AND ct.est_actif=1
                        """,
                            (client_id,),
                        ).fetchall()

                        options = {}
                        if tarifs_spec:
                            for t in tarifs_spec:
                                px = (
                                    t["prix_specifique_ht"]
                                    if t["prix_specifique_ht"] is not None
                                    else t["prix_ht"]
                                )
                                options[t["id"]] = (
                                    f"{t['designation']} ({px:.2f} €/h - Tarif"
                                    " spécifique)"
                                )
                        else:
                            cat = conn.execute(
                                "SELECT * FROM prestations ORDER BY"
                                " designation ASC"
                            ).fetchall()
                            for p in cat:
                                options[p["id"]] = (
                                    f"{p['designation']} ({p['prix_ht']:.2f}"
                                    " €/h)"
                                )
                    finally:
                        conn.close()

                    prest_select.options = options
                    val_prest_init = (
                        interv_existante["prestation_id"]
                        if (is_edition and interv_existante["prestation_id"])
                        else (list(options.keys())[0] if options else None)
                    )
                    prest_select.value = val_prest_init

                def charger_etablissements(client_id):
                    conn = database.get_conn()
                    try:
                        etabs = conn.execute(
                            "SELECT * FROM etablissements WHERE client_id=?",
                            (client_id,),
                        ).fetchall()
                    finally:
                        conn.close()

                    if etabs:
                        options = {e["id"]: e["nom_site"] for e in etabs}
                        etab_select.options = options
                        etab_select.value = (
                            interv_existante["etablissement_id"]
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
                    interv_existante["date"]
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
                    interv_existante["heure_debut"]
                    if (is_edition and interv_existante["heure_debut"])
                    else "14:00"
                )
                val_h_fin = (
                    interv_existante["heure_fin"]
                    if (is_edition and interv_existante["heure_fin"])
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
                        interv_existante["commentaire"]
                        if (is_edition and interv_existante["commentaire"])
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

                    conn = database.get_conn()
                    try:
                        spec = conn.execute(
                            "SELECT prix_specifique_ht FROM client_tarifs WHERE"
                            " client_id=? AND prestation_id=?",
                            (client_id, prest_id),
                        ).fetchone()
                        prest_info = conn.execute(
                            "SELECT * FROM prestations WHERE id=?", (prest_id,)
                        ).fetchone()

                        prix_ht = (
                            spec["prix_specifique_ht"]
                            if (
                                spec
                                and spec["prix_specifique_ht"] is not None
                            )
                            else (
                                prest_info["prix_ht"] if prest_info else 0.0
                            )
                        )
                        taux_tva = prest_info["taux_tva"] if prest_info else 0.0

                        cur = conn.cursor()
                        if is_edition:
                            cur.execute(
                                """
                                UPDATE interventions SET
                                    client_id=?, etablissement_id=?, prestation_id=?, date=?, 
                                    heure_debut=?, heure_fin=?, quantite=?, prix_final_ht=?, taux_tva=?, commentaire=?
                                WHERE id=?
                            """,
                                (
                                    client_id,
                                    etab_id,
                                    prest_id,
                                    date_val,
                                    h_debut.value,
                                    h_fin.value,
                                    qte_calc,
                                    prix_ht,
                                    taux_tva,
                                    remarque_input.value,
                                    interv_existante["id"],
                                ),
                            )
                            ui.notify(
                                "Prestation mise à jour !", type="positive"
                            )
                        else:
                            num_interv = database.generer_numero_document(
                                "PREST"
                            )
                            cur.execute(
                                """
                                INSERT INTO interventions (
                                    numero_intervention, client_id, etablissement_id, prestation_id, date,
                                    heure_debut, heure_fin, quantite, prix_final_ht, taux_tva, statut, commentaire
                                )
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'En attente', ?)
                            """,
                                (
                                    num_interv,
                                    client_id,
                                    etab_id,
                                    prest_id,
                                    date_val,
                                    h_debut.value,
                                    h_fin.value,
                                    qte_calc,
                                    prix_ht,
                                    taux_tva,
                                    remarque_input.value,
                                ),
                            )
                            ui.notify(
                                f"Prestation {num_interv} créée !",
                                type="positive",
                            )

                        conn.commit()
                    finally:
                        conn.close()

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
                    conn = database.get_conn()
                    try:
                        conn.execute(
                            "DELETE FROM interventions WHERE id=?", (interv_id,)
                        )
                        conn.commit()
                    finally:
                        conn.close()

                    dialog.close()
                    ui.notify("Prestation supprimée.", type="info")
                    charger_donnees()

                with ui.row().classes("w-full justify-end gap-2"):
                    ui.button("Annuler", on_click=dialog.close).props(
                        "flat color=slate"
                    )
                    ui.button("Supprimer", on_click=supprimer).props(
                        "negative font-bold"
                    )

            dialog.open()

        # Premier chargement au rendu (par défaut sur l'année en cours pour ne pas surcharger)
        charger_donnees()