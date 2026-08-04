from datetime import datetime, timedelta
import os
from utils import envoyer_email_facture
import utils
from nicegui import ui
import database
import pdf_factures


def formater_date_fr(date_str):
    """Convertit AAAA-MM-JJ en JJ/MM/AAAA."""
    if not date_str:
        return ""
    try:
        d = datetime.strptime(str(date_str).strip(), "%Y-%m-%d")
        return d.strftime("%d/%m/%Y")
    except Exception:
        return str(date_str)


def render_factures():
    ui.label("Gestion & Suivi des Factures").classes(
        "text-2xl font-bold text-slate-800 mb-6"
    )

    with ui.card().classes(
        "w-full p-6 bg-white border border-slate-200 rounded-xl space-y-4"
    ):

        top_bar = ui.row().classes(
            "w-full justify-between items-center mb-2 gap-4 flex-wrap"
        )

        table_container = ui.column().classes("w-full")
        actions_bar_container = ui.row().classes(
            "w-full justify-between items-center pt-3 border-t border-slate-200 min-h-[48px]"
        )

        filtres_holder = {}
        selection_holder = {"selected_row": None}

        def rafraichir_liste():
            table_container.clear()
            actions_bar_container.clear()
            selection_holder["selected_row"] = None

            filtre_statut = (
                filtres_holder["select_statut"].value
                if "select_statut" in filtres_holder
                else "Tous"
            )
            filtre_client = (
                filtres_holder["select_client"].value
                if "select_client" in filtres_holder
                else "Tous"
            )

            conn = database.get_conn()
            query = """
                SELECT 
                    f.*, 
                    c.nom_societe AS client_nom,
                    c.email AS client_email,
                    c.recap_interventions AS client_recap
                FROM factures f
                JOIN clients c ON f.client_id = c.id
                ORDER BY f.id DESC
            """
            rows = conn.execute(query).fetchall()
            conn.close()

            aujourdhui = datetime.now().date()
            factures_list = []

            for r in rows:
                item = dict(r)
                item["date_creation_fr"] = formater_date_fr(
                    item["date_creation"]
                )
                item["date_echeance_fr"] = formater_date_fr(
                    item["date_echeance"]
                )
                item["total_ht_txt"] = f"{item['total_ht'] or 0.0:.2f} € HT"
                item["total_ttc_txt"] = f"{item['total_ttc'] or 0.0:.2f} € TTC"

                etat_echeance = "vert"
                if item["statut"] not in ["Payée", "Annulée"] and item.get("date_echeance"):
                    try:
                        date_ech = datetime.strptime(str(item["date_echeance"]).strip(), "%Y-%m-%d").date()
                        diff_jours = (date_ech - aujourdhui).days

                        if diff_jours < 0:
                            etat_echeance = "rouge"
                        elif diff_jours <= 10:
                            etat_echeance = "jaune"
                        else:
                            etat_echeance = "vert"
                    except ValueError:
                        pass
                item["etat_echeance"] = etat_echeance

                if item.get("date_envoi_mail"):
                    date_env = formater_date_fr(item["date_envoi_mail"])
                    item["mail_status_txt"] = f"✅ Envoyé le {date_env}"
                else:
                    item["mail_status_txt"] = "❌ Non envoyé"

                date_paiement_fr = formater_date_fr(item.get("date_paiement"))
                mode_regl = item.get("mode_reglement")

                if item.get("statut") == "Payée" and date_paiement_fr:
                    if mode_regl:
                        item["statut_affichage"] = f"Payée le {date_paiement_fr} par {mode_regl}"
                    else:
                        item["statut_affichage"] = f"Payée le {date_paiement_fr}"
                else:
                    item["statut_affichage"] = item.get("statut", "")

                if filtre_statut != "Tous" and item["statut"] != filtre_statut:
                    continue
                if (
                    filtre_client != "Tous"
                    and str(item["client_id"]) != str(filtre_client)
                ):
                    continue

                factures_list.append(item)

            columns = [
                {
                    "headerName": "N° Facture",
                    "field": "numero_facture",
                    "align": "left",
                    "sortable": True,
                    "width": 200,
                    "filter": "agTextColumnFilter",
                },
                {
                    "headerName": "Émission",
                    "field": "date_creation_fr",
                    "align": "center",
                    "sortable": True,
                    "width": 200,
                },
                {
                    "headerName": "Échéance",
                    "field": "date_echeance_fr",
                    "align": "center",
                    "sortable": True,
                    "width": 200,
                    "cellClassRules": {
                        "bg-emerald-100 text-emerald-800 font-bold border-emerald-300": (
                            "data.etat_echeance === 'vert'"
                        ),
                        "bg-amber-100 text-amber-800 font-bold border-amber-300": (
                            "data.etat_echeance === 'jaune'"
                        ),
                        "bg-rose-100 text-rose-800 font-bold border-rose-300": (
                            "data.etat_echeance === 'rouge'"
                        ),
                    },
                },
                {
                    "headerName": "Client",
                    "field": "client_nom",
                    "align": "left",
                    "sortable": True,
                    "width": 200,
                    "filter": "agTextColumnFilter",
                },
                {
                    "headerName": "Montant HT",
                    "field": "total_ht_txt",
                    "align": "right",
                    "sortable": True,
                    "width": 200,
                },
                {
                    "headerName": "Montant TTC",
                    "field": "total_ttc_txt",
                    "align": "right",
                    "sortable": True,
                    "width": 200,
                },
                {
                    "headerName": "Envoi Mail",
                    "field": "mail_status_txt",
                    "align": "center",
                    "sortable": True,
                    "width": 200,
                    "cellClassRules": {
                        "text-emerald-700 font-medium text-xs": (
                            'x && x.startsWith("✅")'
                        ),
                        "text-rose-600 font-medium text-xs": 'x && x.startsWith("❌")',
                    },
                },
                {
                    "headerName": "Statut & Règlement",
                    "field": "statut_affichage",
                    "align": "center",
                    "sortable": True,
                    "minWidth": 200,
                    "flex": 1,
                    "cellClassRules": {
                        "bg-slate-100 text-slate-800 font-semibold text-xs border-slate-300": (
                            'x && x.startsWith("Brouillon")'
                        ),
                        "bg-blue-100 text-blue-800 font-semibold text-xs border-blue-300": (
                            'x && x.startsWith("Émise")'
                        ),
                        (
                            "bg-emerald-100 text-emerald-800 font-semibold text-xs"
                            " border-emerald-300"
                        ): 'x && x.startsWith("Payée")',
                        "bg-rose-100 text-rose-800 font-semibold text-xs border-rose-300": (
                            'x && x.startsWith("Annulée")'
                        ),
                    },
                },
            ]

            with table_container:
                grid = ui.aggrid(
                    {
                        "columnDefs": columns,
                        "rowData": factures_list,
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

                def on_cell_clicked(e):
                    data = e.args.get("data")
                    if data:
                        selection_holder["selected_row"] = data
                        update_action_bar()

                grid.on("cellClicked", on_cell_clicked)

            with actions_bar_container:
                btn_group = ui.row().classes("items-center gap-3 flex-wrap")

                def update_action_bar():
                    btn_group.clear()
                    selected = selection_holder["selected_row"]

                    with btn_group:
                        if selected:
                            num = selected.get("numero_facture", "")
                            statut = selected.get("statut", "")
                            has_recap_opt = (
                                selected.get("client_recap", 0) == 1
                            )

                            ui.label(f"Sélection : {num}").classes(
                                "text-sm font-bold text-slate-700 bg-slate-100"
                                " px-3 py-1.5 rounded-lg border border-slate-200"
                            )

                            ui.button(
                                "Voir / Imprimer PDF",
                                icon="print",
                                on_click=lambda: imprimer_facture_pdf(selected),
                            ).props("dense outline color=primary font-bold")

                            if has_recap_opt:
                                ui.button(
                                    "Récapitulatif Prestations",
                                    icon="table_chart",
                                    on_click=lambda: ouvrir_dialog_recap(selected),
                                ).props(
                                    "dense outline color=info font-bold text-sky-700"
                                )

                            ui.button(
                                "Envoyer Mail",
                                icon="email",
                                on_click=lambda: ouvrir_dialog_email(selected),
                            ).props("dense outline color=secondary font-bold")

                            if statut != "Payée" and statut != "Annulée":
                                ui.button(
                                    "Marquer Payée",
                                    icon="check_circle",
                                    on_click=lambda: ouvrir_dialog_paiement(
                                        selected
                                    ),
                                ).props("dense flat color=positive font-bold")

                            if statut != "Annulée":
                                ui.button(
                                    "Créer un Avoir",
                                    icon="assignment_return",
                                    on_click=lambda: confirmer_avoir_facture(
                                        selected
                                    ),
                                ).props(
                                    "dense flat color=warning font-bold"
                                ).tooltip(
                                    "Annule la facture en émettant un avoir légal"
                                )
                        else:
                            ui.label(
                                "💡 Cliquez sur une facture pour l'imprimer, voir son récapitulatif, l'envoyer ou enregistrer son paiement."
                            ).classes(
                                "text-xs text-slate-400 font-medium italic py-1"
                            )

                update_action_bar()

        with top_bar:
            with ui.row().classes("items-center gap-4 flex-wrap flex-1"):
                ui.label("Factures").classes(
                    "text-lg font-semibold text-slate-700"
                )

                filtres_holder["select_statut"] = ui.select(
                    ["Tous", "Brouillon", "Émise", "Payée", "Annulée"],
                    value="Tous",
                    label="Filtrer par Statut",
                ).classes("w-44")

                clients_list = database.recuperer_tous_les_clients()
                client_filter_opts = {"Tous": "Tous les clients"}
                client_filter_opts.update(
                    {str(c["id"]): c["nom_societe"] for c in clients_list}
                )

                filtres_holder["select_client"] = ui.select(
                    client_filter_opts,
                    value="Tous",
                    label="Filtrer par Client",
                ).classes("w-52")

                filtres_holder["select_statut"].on_value_change(
                    lambda _: rafraichir_liste()
                )
                filtres_holder["select_client"].on_value_change(
                    lambda _: rafraichir_liste()
                )

            ui.button(
                "Générer une Facture",
                icon="add",
                on_click=lambda: ouvrir_dialog_creation_facture(),
            ).props("color=primary font-bold")

        def ouvrir_dialog_recap(facture):
            with ui.dialog() as dialog, ui.card().classes(
                "w-full max-w-5xl p-6 space-y-4 bg-white"
            ):
                ui.label(
                    f"Récapitulatif des Prestations - Facture {facture['numero_facture']}"
                ).classes(
                    "text-xl font-bold text-slate-800 border-b pb-2 w-full"
                )
                
                with ui.row().classes("w-full items-center gap-4"):
                    ui.label(
                        f"Client : {facture.get('client_nom', '')} | Période de référence du mois"
                    ).classes("text-sm text-slate-600 font-medium flex-1")
                    
                    intitule_select = ui.select(
                        ["Intervention(s)", "Séance(s)", "Prestation(s)", "Heure(s)", "Cours(s)"],
                        value="Intervention(s)",
                        label="Intitulé du compteur"
                    ).classes("w-48").props("dense outlined")

                conn = database.get_conn()
                query_items = """
                    SELECT 
                        i.*, 
                        p.designation AS prest_nom,
                        e.nom_site AS etablissement_nom
                    FROM interventions i
                    LEFT JOIN prestations p ON i.prestation_id = p.id
                    LEFT JOIN etablissements e ON i.etablissement_id = e.id
                    WHERE i.facture_id = ?
                    ORDER BY i.date ASC
                """
                interventions = conn.execute(
                    query_items, (facture["id"],)
                ).fetchall()
                conn.close()

                if not interventions:
                    ui.label(
                        "Aucune prestation détaillée liée à cette facture."
                    ).classes("text-sm text-slate-500 italic py-4")
                else:
                    etabs_set = set()
                    for it in interventions:
                        etab = it["etablissement_nom"] or "Autre"
                        etabs_set.add(etab)
                    etabs_list = sorted(list(etabs_set))

                    semaines_dict = {}
                    for it in interventions:
                        dt = datetime.strptime(
                            str(it["date"]).strip(), "%Y-%m-%d"
                        )
                        debut_sem = dt - timedelta(days=dt.weekday())
                        fin_sem = debut_sem + timedelta(days=6)
                        sem_key = (
                            f"Semaine du {debut_sem.strftime('%d %B').lower()} au {fin_sem.strftime('%d %B').lower()}"
                        )

                        if sem_key not in semaines_dict:
                            semaines_dict[sem_key] = []
                        semaines_dict[sem_key].append(dict(it))

                    table_holder = ui.column().classes("w-full")

                    def rafraichir_tableau_recap():
                        table_holder.clear()
                        intitule_choisi = intitule_select.value or "Intervention(s)"

                        table_html = [
                            "<table class='w-full border-collapse border border-slate-300 text-sm text-left'>"
                        ]
                        table_html.append(
                            "<tr class='bg-slate-100 text-slate-700 font-bold'>"
                        )
                        table_html.append(
                            "<th class='border border-slate-300 p-2.5'>Semaines</th>"
                        )
                        for etab in etabs_list:
                            table_html.append(
                                f"<th class='border border-slate-300 p-2.5 text-center'>{etab}</th>"
                            )
                        table_html.append(
                            "<th class='border border-slate-300 p-2.5 text-center bg-slate-200'>Total semaine</th>"
                        )
                        table_html.append("</tr>")

                        total_general_mois = 0.0
                        total_general_nombre = 0

                        for sem_lib, items_sem in semaines_dict.items():
                            table_html.append("<tr>")
                            table_html.append(
                                f"<td class='border border-slate-300 p-2.5 font-semibold bg-slate-50'>{sem_lib}</td>"
                            )

                            total_semaine = 0.0
                            nombre_semaine = 0

                            for etab in etabs_list:
                                matches = [
                                    x
                                    for x in items_sem
                                    if (x["etablissement_nom"] or "Autre")
                                    == etab
                                ]
                                cell_texts = []
                                for m in matches:
                                    d_fr = formater_date_fr(m["date"])
                                    montant_ligne = (
                                        m["prix_final_ht"] or 0.0
                                    ) * (m["quantite"] or 1.0)
                                    total_semaine += montant_ligne
                                    nombre_semaine += 1
                                    
                                    desc_courte = (
                                        m["prest_nom"]
                                        or f"Intervention N°{m['id']}"
                                    )
                                    if m.get('commentaire'):
                                        desc_courte += f" ({m['commentaire']})"
                                    cell_texts.append(
                                        f"{d_fr} - {desc_courte} : {montant_ligne:.0f}€"
                                    )

                                contenu_cellule = (
                                    "<br>".join(cell_texts)
                                    if cell_texts
                                    else "-"
                                )
                                table_html.append(
                                    f"<td class='border border-slate-300 p-2.5 text-center text-xs'>{contenu_cellule}</td>"
                                )

                            total_general_mois += total_semaine
                            total_general_nombre += nombre_semaine

                            table_html.append(
                                f"<td class='border border-slate-300 p-2.5 text-center font-bold bg-slate-50'>{total_semaine:.0f}€<br/><span class='text-xs font-normal text-slate-500'>({nombre_semaine} {intitule_choisi})</span></td>"
                            )
                            table_html.append("</tr>")

                        table_html.append(
                            "<tr class='bg-primary text-white font-bold'>"
                        )
                        table_html.append(
                            "<td class='border border-slate-300 p-3'>TOTAL MOIS</td>"
                        )
                        for etab in etabs_list:
                            table_html.append(
                                "<td class='border border-slate-300 p-3 text-center'>-</td>"
                            )
                        table_html.append(
                            f"<td class='border border-slate-300 p-3 text-center'>{total_general_mois:.0f}€<br/><span class='text-xs font-normal text-sky-200'>({total_general_nombre} {intitule_choisi})</span></td>"
                        )
                        table_html.append("</tr>")
                        table_html.append("</table>")

                        with table_holder:
                            ui.html("".join(table_html)).classes("w-full")

                    intitule_select.on_value_change(lambda _: rafraichir_tableau_recap())
                    rafraichir_tableau_recap()

                with ui.row().classes("w-full justify-end gap-2 mt-4"):
                    ui.button("Fermer", on_click=dialog.close).props(
                        "flat color=slate"
                    )
                    ui.button(
                        "Imprimer le récapitulatif",
                        icon="print",
                        on_click=lambda: imprimer_recap_pdf(facture, intitule_select.value),
                    ).props("color=primary font-bold")

            dialog.open()

        def ouvrir_dialog_creation_facture():
            clients = database.recuperer_tous_les_clients()
            if not clients:
                ui.notify("Aucun client trouvé.", type="warning")
                return

            # Modale élargie (max-w-6xl) pour accueillir proprement les 2 colonnes
            with ui.dialog() as dialog, ui.card().classes(
                "p-8 space-y-6 w-full max-w-6xl bg-white rounded-2xl shadow-2xl"
            ):
                ui.label("Générer une nouvelle Facture").classes(
                    "text-2xl font-bold text-slate-800 border-b pb-3 w-full"
                )

                # Conteneur principal en 2 colonnes égales
                with ui.row().classes("w-full gap-8 items-start"):
                    
                    # ----------------------------------------------------
                    # COLONNE DE GAUCHE : Client, Options, Échéances
                    # ----------------------------------------------------
                    with ui.column().classes("w-1/2 space-y-5"):
                        ui.label("1. Paramètres de la facture").classes("text-sm font-bold text-slate-700 uppercase tracking-wide")

                        client_options = {c["id"]: c["nom_societe"] for c in clients}
                        client_select = ui.select(
                            client_options,
                            label="Sélectionnez le Client",
                            value=clients[0]["id"],
                        ).classes("w-full").props("outlined dense")

                        # Conteneur dynamique pour l'option de l'intitulé si le client a le récap actif
                        recap_options_container = ui.column().classes("w-full")
                        intitule_select_modal_holder = {"select": None}

                        date_aujourdhui_obj = datetime.now().date()
                        date_emiss_fr = date_aujourdhui_obj.strftime("%d/%m/%Y")
                        date_emiss_iso = date_aujourdhui_obj.strftime("%Y-%m-%d")

                        options_echeance = {
                            'Comptant': 'Paiement comptant',
                            '8 jours': 'Paiement à 8 jours',
                            '15 jours': 'Paiement à 15 jours',
                            '30 jours': 'Paiement à 30 jours',
                            '45 jours': 'Paiement à 45 jours',
                            '60 jours': 'Paiement à 60 jours',
                        }

                        delais_jours = {
                            'Comptant': 0,
                            '8 jours': 8,
                            '15 jours': 15,
                            '30 jours': 30,
                            '45 jours': 45,
                            '60 jours': 60,
                        }

                        with ui.row().classes("w-full gap-4 items-center"):
                            ui.input("Date d'émission", value=date_emiss_fr).props(
                                "dense outlined readonly bg-slate-100 cursor-not-allowed"
                            ).classes("w-1/2")

                            select_delai = ui.select(
                                options_echeance,
                                value="30 jours",
                                label="Conditions de règlement",
                            ).classes("w-1/2").props("dense outlined")

                        echeance_label = ui.label("").classes(
                            "text-xs font-semibold text-slate-500 italic w-full text-right"
                        )

                        def calculer_date_echeance():
                            choix = select_delai.value or '30 jours'
                            jours = delais_jours.get(choix, 30)
                            dt_echeance_obj = date_aujourdhui_obj + timedelta(
                                days=jours
                            )
                            echeance_label.set_text(
                                f"Échéance calculée au : {dt_echeance_obj.strftime('%d/%m/%Y')}"
                            )
                            return dt_echeance_obj.strftime("%Y-%m-%d")

                        select_delai.on_value_change(lambda _: calculer_date_echeance())
                        calculer_date_echeance()

                    # ----------------------------------------------------
                    # COLONNE DE DROITE : Prestations, Sélection, Totaux
                    # ----------------------------------------------------
                    with ui.column().classes("w-1/2 space-y-4 flex-1"):
                        ui.label("2. Sélection des prestations à facturer").classes("text-sm font-bold text-slate-700 uppercase tracking-wide")

                        with ui.row().classes("w-full gap-2 items-center flex-wrap"):
                            btn_m_prec = ui.button(
                                "Mois précédent", icon="event_repeat"
                            ).props("dense outline color=slate text-xs")
                            btn_m_cours = ui.button(
                                "Mois en cours", icon="today"
                            ).props("dense outline color=primary text-xs")
                            btn_deselect = ui.button(
                                "Tout décocher", icon="clear_all"
                            ).props("dense flat color=negative text-xs")
                            btn_select_all = ui.button(
                                "Tout cocher", icon="select_all"
                            ).props("dense flat color=slate text-xs")

                        # Conteneur des prestations bien large et confortable (hauteur augmentée)
                        prestations_container = ui.column().classes(
                            "w-full h-80 overflow-y-auto border border-slate-200 p-4 rounded-xl bg-slate-50/50 space-y-2.5"
                        )
                        
                        totaux_container = ui.row().classes(
                            "w-full justify-between items-center bg-slate-100 p-4 rounded-xl font-semibold text-slate-800"
                        )

                cochables_holder = {}

                def verifier_et_afficher_options_recap(client_id):
                    conn = database.get_conn()
                    client_res = conn.execute(
                        "SELECT recap_interventions FROM clients WHERE id = ?",
                        (client_id,)
                    ).fetchone()
                    conn.close()

                    recap_active = client_res and client_res["recap_interventions"] == 1
                    recap_options_container.clear()
                    intitule_select_modal_holder["select"] = None
                    
                    if recap_active:
                        with recap_options_container:
                            with ui.card().classes("w-full p-4 bg-sky-50/60 border border-sky-200 rounded-xl space-y-2 shadow-sm"):
                                ui.label("📊 Options du récapitulatif des prestations").classes("text-xs font-bold text-sky-800 uppercase tracking-wide")
                                intitule_select_modal_holder["select"] = ui.select(
                                    ["Intervention(s)", "Séance(s)", "Prestation(s)", "Heure(s)", "Cours(s)"],
                                    value="Intervention(s)",
                                    label="Intitulé du compteur pour le récapitulatif"
                                ).classes("w-full bg-white").props("dense outlined")

                def charger_prestations_realisees(client_id):
                    verifier_et_afficher_options_recap(client_id)
                    prestations_container.clear()
                    cochables_holder.clear()

                    conn = database.get_conn()
                    query = """
                        SELECT i.*, p.designation AS prest_nom
                        FROM interventions i
                        LEFT JOIN prestations p ON i.prestation_id = p.id
                        WHERE i.client_id = ? AND (i.facture_id IS NULL OR i.facture_id = '')
                        ORDER BY i.date ASC
                    """
                    items = conn.execute(query, (client_id,)).fetchall()
                    conn.close()

                    if not items:
                        with prestations_container:
                            ui.label(
                                "Aucune prestation en attente de facturation pour ce client."
                            ).classes("text-sm text-slate-500 italic py-2")
                        maj_totaux()
                        return

                    aujourdhui_str = datetime.now().strftime("%Y-%m-%d")

                    with prestations_container:
                        for item in items:
                            i_dict = dict(item)
                            d_fr = formater_date_fr(i_dict["date"])
                            px_tot = (i_dict["prix_final_ht"] or 0.0) * (
                                i_dict["quantite"] or 1.0
                            )
                            txt_label = f"{d_fr} | {i_dict['numero_intervention']} - {i_dict['prest_nom'] or 'Prestation'} ({i_dict['quantite']}h) : {px_tot:.2f} € HT"

                            cocher_defaut = i_dict["date"] <= aujourdhui_str

                            chk = ui.checkbox(
                                txt_label,
                                value=cocher_defaut,
                                on_change=lambda _: maj_totaux(),
                            ).classes("py-0.5")
                            cochables_holder[i_dict["id"]] = {
                                "checkbox": chk,
                                "data": i_dict,
                            }

                    cocher_par_periode("mois_precedent")

                def cocher_par_periode(periode_mode):
                    today = datetime.now().date()

                    if periode_mode == "mois_precedent":
                        premier_jour_ce_mois = today.replace(day=1)
                        dernier_jour_m_prec = premier_jour_ce_mois - timedelta(
                            days=1
                        )
                        premier_jour_m_prec = dernier_jour_m_prec.replace(day=1)
                        date_deb = premier_jour_m_prec.strftime("%Y-%m-%d")
                        date_fin = dernier_jour_m_prec.strftime("%Y-%m-%d")

                    elif periode_mode == "mois_encours":
                        premier_jour_ce_mois = today.replace(day=1)
                        date_deb = premier_jour_ce_mois.strftime("%Y-%m-%d")
                        date_fin = today.strftime("%Y-%m-%d")

                    for item_id, item_info in cochables_holder.items():
                        if periode_mode == "tout":
                            item_info["checkbox"].set_value(True)
                        elif periode_mode == "aucun":
                            item_info["checkbox"].set_value(False)
                        else:
                            dt_item = str(item_info["data"]["date"]).strip()
                            est_dans_intervalle = date_deb <= dt_item <= date_fin
                            item_info["checkbox"].set_value(est_dans_intervalle)

                    maj_totaux()

                btn_m_prec.on_click(
                    lambda: cocher_par_periode("mois_precedent")
                )
                btn_m_cours.on_click(lambda: cocher_par_periode("mois_encours"))
                btn_deselect.on_click(lambda: cocher_par_periode("aucun"))
                btn_select_all.on_click(lambda: cocher_par_periode("tout"))

                def maj_totaux():
                    totaux_container.clear()
                    total_ht = 0.0
                    total_tva = 0.0

                    for item_id, item_info in cochables_holder.items():
                        if item_info["checkbox"].value:
                            d = item_info["data"]
                            ht = (d["prix_final_ht"] or 0.0) * (
                                d["quantite"] or 1.0
                            )
                            tva = ht * ((d["taux_tva"] or 0.0) / 100.0)
                            total_ht += ht
                            total_tva += tva

                    total_ttc = total_ht + total_tva

                    with totaux_container:
                        ui.label(f"Total HT : {total_ht:.2f} €")
                        ui.label(f"TVA : {total_tva:.2f} €")
                        ui.label(f"Total TTC : {total_ttc:.2f} €").classes(
                            "text-lg text-primary font-bold"
                        )

                client_select.on_value_change(
                    lambda e: charger_prestations_realisees(e.value)
                )
                charger_prestations_realisees(client_select.value)

                def generer_facture():
                    client_id = client_select.value
                    interv_ids_soisis = [
                        id_item
                        for id_item, info in cochables_holder.items()
                        if info["checkbox"].value
                    ]

                    if not interv_ids_soisis:
                        ui.notify(
                            "Veuillez cocher au moins une prestation à facturer.",
                            type="warning",
                        )
                        return

                    num_facture = database.generer_numero_document("FAC")
                    date_ech_iso = calculer_date_echeance()

                    tot_ht = 0.0
                    tot_tva = 0.0
                    for item_id in interv_ids_soisis:
                        d = cochables_holder[item_id]["data"]
                        ht = (d["prix_final_ht"] or 0.0) * (
                            d["quantite"] or 1.0
                        )
                        tva = ht * ((d["taux_tva"] or 0.0) / 100.0)
                        tot_ht += ht
                        tot_tva += tva

                    tot_ttc = tot_ht + tot_tva

                    conn = database.get_conn()
                    cur = conn.cursor()

                    cur.execute(
                        """
                        INSERT INTO factures (
                            numero_facture, client_id, date_creation, date_echeance, 
                            statut, total_ht, total_tva, total_ttc, conditions_reglement
                        )
                        VALUES (?, ?, ?, ?, 'Émise', ?, ?, ?, ?)
                    """,
                        (
                            num_facture,
                            client_id,
                            date_emiss_iso,
                            date_ech_iso,
                            tot_ht,
                            tot_tva,
                            tot_ttc,
                            options_echeance.get(select_delai.value, select_delai.value),
                        ),
                    )

                    facture_id = cur.lastrowid

                    for item_id in interv_ids_soisis:
                        cur.execute(
                            "UPDATE interventions SET facture_id = ?, statut = 'Facturé' WHERE id = ?",
                            (facture_id, item_id),
                        )
                        cur.execute(
                            "INSERT INTO facture_items (facture_id, intervention_id) VALUES (?, ?)",
                            (facture_id, item_id),
                        )

                    client_info = conn.execute(
                        "SELECT recap_interventions FROM clients WHERE id = ?",
                        (client_id,),
                    ).fetchone()
                    if client_info and client_info["recap_interventions"] == 1:
                        conn.execute(
                            "UPDATE factures SET recap_genere = 1 WHERE id = ?",
                            (facture_id,),
                        )

                    conn.commit()
                    conn.close()

                    intitule_choisi = "Intervention(s)"
                    sel_widget = intitule_select_modal_holder["select"]
                    if client_info and client_info["recap_interventions"] == 1 and sel_widget and sel_widget.value:
                        intitule_choisi = sel_widget.value

                    try:
                        pdf_factures.generer_pdf_facture(facture_id)
                        if client_info and client_info["recap_interventions"] == 1:
                            if hasattr(
                                pdf_factures, "generer_pdf_recap_facture"
                            ):
                                pdf_factures.generer_pdf_recap_facture(
                                    facture_id, intitule=intitule_choisi
                                )
                    except Exception as e:
                        print(f"Erreur génération PDF auto : {e}")

                    ui.notify(
                        f"Facture {num_facture} générée avec succès !",
                        type="positive",
                        icon="check",
                    )
                    dialog.close()
                    rafraichir_liste()

                # Boutons de validation en bas de la modale
                with ui.row().classes("w-full justify-end gap-3 pt-4 border-t border-slate-100"):
                    ui.button("Annuler", on_click=dialog.close).props(
                        "flat color=slate"
                    )
                    ui.button(
                        "Valider et Générer",
                        icon="receipt",
                        on_click=generer_facture,
                    ).props("color=primary font-bold px-4 py-2")

            dialog.open()

        def ouvrir_dialog_paiement(facture):
            with ui.dialog() as dialog, ui.card().classes("w-full max-w-md p-6 space-y-4"):
                ui.label(f"Enregistrer le paiement - Facture {facture['numero_facture']}").classes("text-xl font-bold text-slate-800")
                
                options_modes = {
                    'Virement': 'Virement bancaire',
                    'Chèque': 'Chèque',
                    'Carte bancaire': 'Carte bancaire',
                    'Espèces': 'Espèces',
                    'Prélèvement': 'Prélèvement / Autre'
                }

                mode_select = ui.select(
                    options=options_modes, 
                    value='Virement', 
                    label="Mode de règlement"
                ).classes("w-full").props("dense outlined")

                ui.label("Date du règlement :").classes("text-sm text-slate-600 font-medium")
                date_selectionnee = ui.date(value=str(datetime.now().date())).classes("w-full")

                def confirmer_paiement():
                    date_paiement = date_selectionnee.value
                    mode_paiement = mode_select.value

                    conn = database.get_conn()
                    conn.execute(
                        "UPDATE factures SET statut = 'Payée', date_paiement = ?, mode_reglement = ? WHERE id = ?",
                        (date_paiement, mode_paiement, facture["id"]),
                    )
                    conn.commit()
                    conn.close()

                    ui.notify(
                        f"Facture {facture['numero_facture']} payée le {formater_date_fr(date_paiement)} par {mode_paiement} !",
                        type="positive",
                        icon="check_circle",
                    )
                    dialog.close()
                    rafraichir_liste()

                with ui.row().classes("w-full justify-end gap-2 mt-4"):
                    ui.button("Annuler", on_click=dialog.close).props("flat color=slate")
                    ui.button("Confirmer le paiement", icon="check", on_click=confirmer_paiement).props("color=positive font-bold")

            dialog.open()

        def confirmer_avoir_facture(facture):
            with ui.dialog() as dialog, ui.card().classes(
                "p-6 space-y-4 max-w-md"
            ):
                ui.label("Créer un Avoir (Annuler la facture)").classes(
                    "text-lg font-bold text-slate-800 border-b pb-2 w-full"
                )
                ui.label(
                    f"Voulez-vous annuler la facture « {facture['numero_facture']} » ?"
                ).classes("text-slate-700 font-semibold text-sm")
                ui.label(
                    "Les prestations liées redeviendront disponibles pour une facturation ultérieure et la facture sera classée 'Annulée'."
                ).classes("text-slate-500 text-xs italic")

                def annuler_et_creer_avoir():
                    conn = database.get_conn()
                    conn.execute(
                        "UPDATE interventions SET facture_id = NULL, statut = 'Réalisée' WHERE facture_id = ?",
                        (facture["id"],),
                    )
                    conn.execute(
                        "UPDATE factures SET statut = 'Annulée' WHERE id = ?",
                        (facture["id"],),
                    )
                    conn.commit()
                    conn.close()

                    dialog.close()
                    ui.notify(
                        f"Facture {facture['numero_facture']} annulée. Les prestations ont été réouvertes.",
                        type="info",
                        icon="assignment_return",
                    )
                    rafraichir_liste()

                with ui.row().classes("w-full justify-end gap-2"):
                    ui.button("Annuler", on_click=dialog.close).props(
                        "flat color=slate"
                    )
                    ui.button(
                        "Confirmer l'avoir",
                        icon="check",
                        on_click=annuler_et_creer_avoir,
                    ).props("color=warning font-bold")

            dialog.open()

        def imprimer_facture_pdf(facture):
            try:
                pdf_factures.generer_et_ouvrir_pdf_facture(
                    facture["id"]
                )
                ui.notify(
                    f"PDF de la facture {facture['numero_facture']} ouvert avec succès !",
                    type="positive",
                    icon="print",
                )
            except Exception as e:
                ui.notify(
                    f"Erreur lors de la génération PDF : {str(e)}",
                    type="negative",
                )
             
        def imprimer_recap_pdf(facture, intitule="Intervention(s)"):
            try:
                pdf_factures.generer_et_ouvrir_pdf_recap(
                    facture["id"], intitule=intitule
                )
                ui.notify(
                    f"PDF du récapitulatif ouvert avec succès !",
                    type="positive",
                    icon="print",
                )
            except Exception as e:
                ui.notify(
                    f"Erreur lors de la génération du récap : {str(e)}",
                    type="negative",
                )

        def ouvrir_dialog_email(facture):
            conn = database.get_conn()
            client = conn.execute(
                "SELECT nom_societe, email, recap_interventions FROM clients WHERE id=?",
                (facture["client_id"],),
            ).fetchone()
            conn.close()

            email_client = facture.get("client_email", "") or (
                client["email"] if client else ""
            )

            if not email_client:
                ui.notify(
                    "Attention : Ce client n'a pas d'adresse e-mail renseignée !",
                    type="warning",
                    icon="warning",
                )
                return

            with ui.dialog() as dialog, ui.card().classes(
                "w-full max-w-lg p-6 space-y-4"
            ):
                ui.label(
                    f"Envoyer la Facture {facture['numero_facture']}"
                ).classes(
                    "text-lg font-bold text-slate-800 border-b pb-2 w-full"
                )
                ui.label(
                    f"Le document sera envoyé à : {client['nom_societe'] if client else 'Client'} ({email_client})"
                ).classes("text-sm text-slate-600")

                if client and client["recap_interventions"] == 1:
                    ui.label(
                        "📎 Le récapitulatif détaillé des prestations sera joint automatiquement à l'e-mail."
                    ).classes("text-xs font-semibold text-info italic")

                email_input = ui.input(
                    "Destinataire (Email)", value=email_client
                ).classes("w-full")
                objet_input = ui.input(
                    "Objet du message",
                    value=f"Facture {facture['numero_facture']}",
                ).classes("w-full")
                msg_input = ui.textarea(
                    "Message",
                    value=(
                        "Bonjour,\n\nVeuillez trouver ci-joint votre facture "
                        f"{facture['numero_facture']}"
                        + (
                            " ainsi que le récapitulatif détaillé de vos prestations."
                            if client and client["recap_interventions"] == 1
                            else "."
                        )
                        + "\n\nCordialement."
                    ),
                ).classes("w-full h-32")

                def confirmer_envoi():
                    pdf_path = pdf_factures.generer_pdf_facture(facture["id"])

                    recap_path = None
                    recap_actif = False
                    if client and "recap_interventions" in client.keys():
                        recap_actif = (client["recap_interventions"] == 1)

                    if recap_actif:
                        try:
                            recap_path = pdf_factures.generer_pdf_recap_facture(facture["id"])
                        except Exception as e:
                            print(f"Erreur lors de la génération du récapitulatif : {e}")

                    dest = email_input.value.strip()
                    sujet = objet_input.value.strip()
                    corps = msg_input.value

                    succes, message = utils.envoyer_email_facture(
                        destinataire=dest,
                        sujet=sujet,
                        corps=corps,
                        pdf_path=pdf_path,
                        pdf_recap_path=recap_path
                    )

                    if succes:
                        date_jour_iso = datetime.now().strftime("%Y-%m-%d")
                        conn_e = database.get_conn()
                        conn_e.execute(
                            "UPDATE factures SET statut='Envoyée', date_envoi_mail=? WHERE id=?",
                            (date_jour_iso, facture["id"]),
                        )
                        conn_e.commit()
                        conn_e.close()

                        ui.notify(
                            f"Facture {facture['numero_facture']} envoyée à {dest} avec succès !",
                            type="positive",
                            icon="send",
                        )
                        dialog.close()
                        rafraichir_liste()
                    else:
                        ui.notify(message, type="negative", icon="error")

                with ui.row().classes("w-full justify-end gap-2 mt-4"):
                    ui.button("Annuler", on_click=dialog.close).props(
                        "flat color=slate"
                    )
                    ui.button(
                        "Envoyer par E-mail",
                        icon="send",
                        on_click=confirmer_envoi,
                    ).props("color=primary font-bold")

            dialog.open()

        rafraichir_liste()