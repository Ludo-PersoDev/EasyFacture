from datetime import datetime
from nicegui import ui
import database

def parse_date(date_str):
    """Convertit n'importe quelle chaîne de date (ISO YYYY-MM-DD ou FR DD/MM/YYYY) en objet date Python."""
    if not date_str:
        return None
    date_str = str(date_str).strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d', '%d-%m-%Y'):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            pass
    return None

def render_analytics():
    ui.label("Tableau de Bord & Analytics Financier").classes("text-2xl font-bold text-slate-800 mb-6")

    # --- 1. RÉCUPÉRATION DES ANNÉES DISPONIBLES ---
    supabase = database.get_db()
    rows_res = supabase.table("factures").select("date_creation").not_.is_("date_creation", "null").execute()
    rows_factures = rows_res.data

    annees_trouvees = set()
    for r in rows_factures:
        d = parse_date(r.get('date_creation'))
        if d:
            annees_trouvees.add(str(d.year))

    annee_courante = str(datetime.now().year)
    annees_disponibles = sorted(list(annees_trouvees), reverse=True)
    if annee_courante not in annees_disponibles:
        annees_disponibles.insert(0, annee_courante)

    options_annees = {'Toutes': 'Toutes les années'}
    options_annees.update({a: a for a in annees_disponibles})

    options_mois = {
        'Tous': 'Tous les mois',
        '01': 'Janvier', '02': 'Février', '03': 'Mars', '04': 'Avril',
        '05': 'Mai', '06': 'Juin', '07': 'Juillet', '08': 'Août',
        '09': 'Septembre', '10': 'Octobre', '11': 'Novembre', '12': 'Décembre'
    }

    # --- 2. BARRE DE FILTRES ---
    with ui.card().classes("w-full p-4 bg-white border border-slate-200 rounded-xl mb-6 shadow-sm"):
        with ui.row().classes("w-full items-center justify-between gap-4"):
            with ui.row().classes("items-center gap-2 text-slate-700 font-semibold"):
                ui.icon("filter_alt", size="20px")
                ui.label("Période d'analyse")

            with ui.row().classes("items-center gap-4"):
                filtre_annee = ui.select(options=options_annees, value=annee_courante, label="Année").classes("w-40").props("dense outlined")
                filtre_mois = ui.select(options=options_mois, value="Tous", label="Mois").classes("w-44").props("dense outlined")
                
                def reinitialiser_filtres():
                    filtre_annee.value = annee_courante
                    filtre_mois.value = "Tous"
                
                ui.button(icon="refresh", on_click=reinitialiser_filtres).props("flat round dense color=slate")

    # --- 3. STRUCTURE FIXE DES BLOCS DE L'INTERFACE ---
    
    # BLOC 1 : KPIs
    with ui.row().classes("w-full grid grid-cols-1 md:grid-cols-4 gap-4 mb-6"):
        with ui.card().classes("p-4 bg-white border border-slate-200 rounded-xl space-y-1 shadow-sm"):
            ui.label("CA Facturé Total HT").classes("text-xs font-bold text-slate-500 uppercase tracking-wider")
            lbl_kpi_ca = ui.label("0.00 €").classes("text-2xl font-black text-slate-800")
            ui.label("Période sélectionnée").classes("text-xs text-slate-400")

        with ui.card().classes("p-4 bg-emerald-50 border border-emerald-200 rounded-xl space-y-1 shadow-sm"):
            ui.label("Montant Encaissé TTC").classes("text-xs font-bold text-emerald-700 uppercase tracking-wider")
            lbl_kpi_encaisse = ui.label("0.00 €").classes("text-2xl font-black text-emerald-900")
            ui.label("Paiements confirmés").classes("text-xs text-emerald-600")

        card_retard_kpi = ui.card().classes("p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-1 shadow-sm")
        with card_retard_kpi:
            lbl_kpi_retard_title = ui.label("Paiements en Retard TTC").classes("text-xs font-bold text-slate-500 uppercase tracking-wider")
            lbl_kpi_retard_val = ui.label("0.00 €").classes("text-2xl font-black text-slate-800")
            lbl_kpi_retard_sub = ui.label("0 facture(s) dépassée(s)").classes("text-xs text-slate-400")

        with ui.card().classes("p-4 bg-blue-50 border border-blue-200 rounded-xl space-y-1 shadow-sm"):
            ui.label("En Attente de Règlement").classes("text-xs font-bold text-blue-700 uppercase tracking-wider")
            lbl_kpi_attente = ui.label("0.00 €").classes("text-2xl font-black text-blue-900")
            ui.label("Non échues sur la période").classes("text-xs text-blue-600")

    # BLOC 2 : GRAPHIQUES (LIGNE CA + CAMEMBERT MODES DE RÈGLEMENT)
    with ui.row().classes("w-full grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6"):
        # Graphique d'Évolution (2/3 de la largeur)
        with ui.card().classes("lg:col-span-2 p-6 bg-white border border-slate-200 rounded-xl space-y-4 shadow-sm"):
            with ui.row().classes("w-full justify-between items-center border-b pb-3"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("show_chart", color="primary", size="24px")
                    ui.label("Évolution du Chiffre d'Affaires HT").classes("text-lg font-bold text-slate-800")
                chip_comp = ui.chip("", color="blue-1", text_color="blue-9").props("dense")
                chip_comp.set_visibility(False)
                
            chart_ca = ui.echart({}).classes("w-full h-80")

        # Graphique Répartition Règlements (1/3 de la largeur)
        with ui.card().classes("p-6 bg-white border border-slate-200 rounded-xl space-y-4 shadow-sm"):
            with ui.row().classes("items-center gap-2 border-b pb-3"):
                ui.icon("pie_chart", color="secondary", size="24px")
                ui.label("Modes de Règlement").classes("text-lg font-bold text-slate-800")
            
            chart_modes = ui.echart({}).classes("w-full h-80")

    # BLOC 3 : ALERTES RETARD DE PAIEMENT
    with ui.card().classes("w-full p-6 bg-white border border-slate-200 rounded-xl space-y-4 mb-6 shadow-sm"):
        with ui.row().classes("w-full justify-between items-center border-b pb-3"):
            with ui.row().classes("items-center gap-2"):
                icon_retard = ui.icon("warning", color="grey", size="24px")
                ui.label("Alertes & Factures en Retard de Paiement").classes("text-lg font-bold text-slate-800")
            chip_retard_count = ui.chip("", color="rose-1", text_color="rose-9").props("dense")
            chip_retard_count.set_visibility(False)

        columns_retard = [
            {'name': 'numero_facture', 'label': 'N° Facture', 'field': 'numero_facture', 'align': 'left', 'sortable': True},
            {'name': 'nom_societe', 'label': 'Client', 'field': 'nom_societe', 'align': 'left', 'sortable': True},
            {'name': 'date_echeance', 'label': 'Échéance', 'field': 'date_echeance', 'align': 'center', 'sortable': True},
            {'name': 'jours_retard', 'label': 'Retard', 'field': 'jours_retard', 'align': 'center', 'sortable': True},
            {'name': 'total_ttc_txt', 'label': 'Montant TTC', 'field': 'total_ttc_txt', 'align': 'right', 'sortable': True},
        ]
        grid_retard = ui.table(columns=columns_retard, rows=[], row_key='id', selection='single', pagination=5).classes("w-full cursor-pointer no-checkbox-table")
        grid_retard.props('flat borderless hide-selection-color')
        grid_retard.add_slot('body-cell-jours_retard', '''
            <q-td :props="props">
                <q-chip dense color="rose-2" text-color="rose-9" icon="schedule">
                    {{ props.row.jours_retard_txt }}
                </q-chip>
            </q-td>
        ''')

        actions_bar_retard = ui.row().classes("w-full justify-between items-center p-4 bg-rose-50 border border-rose-200 rounded-xl mt-2")
        actions_bar_retard.set_visibility(False)
        label_sel_retard = ui.label().classes("font-semibold text-rose-900")
        buttons_retard = ui.row().classes("gap-2 items-center")
        
        with actions_bar_retard:
            label_sel_retard
            buttons_retard

    # BLOC 4 : STATISTIQUES ET RÈGLEMENTS PAR CLIENT
    with ui.card().classes("w-full p-6 bg-white border border-slate-200 rounded-xl space-y-4 shadow-sm"):
        ui.label("Répartition du CA et Modes de Règlement par Client").classes("text-lg font-bold text-slate-800 border-b pb-3")
        
        columns_clients = [
            {'name': 'nom', 'label': 'Client / Société', 'field': 'nom', 'align': 'left', 'sortable': True},
            {'name': 'nb_factures', 'label': 'Factures', 'field': 'nb_factures', 'align': 'center', 'sortable': True},
            {'name': 'ca_ht_txt', 'label': 'CA Total HT', 'field': 'ca_ht_txt', 'align': 'right', 'sortable': True},
            {'name': 'paye_ttc_txt', 'label': 'Encaissé TTC', 'field': 'paye_ttc_txt', 'align': 'right', 'sortable': True},
            {'name': 'modes_detail_txt', 'label': 'Modes de règlement utilisés', 'field': 'modes_detail_txt', 'align': 'left', 'sortable': True},
            {'name': 'retard_ttc_txt', 'label': 'En Retard TTC', 'field': 'retard_ttc_txt', 'align': 'right', 'sortable': True},
        ]
        grid_clients = ui.table(columns=columns_clients, rows=[], row_key='nom', pagination=5).classes("w-full")
        grid_clients.props('flat borderless')
        grid_clients.add_slot('body-cell-retard_ttc_txt', '''
            <q-td :props="props">
                <span :class="props.row.has_retard ? 'text-rose-600 font-bold' : 'text-slate-400'">
                    {{ props.value }}
                </span>
            </q-td>
        ''')

    # --- 4. LOGIQUE DE CALCUL ET REFRESH ---
    def rafraichir_dashboard():
        selected_annee = filtre_annee.value
        selected_mois = filtre_mois.value

        sup = database.get_supabase()
        res = sup.table("factures").select(
            "*, clients(nom_societe, contact, telephone, email)"
        ).neq("statut", "Annulée").execute()

        all_factures = []
        for row in res.data:
            c = row.get("clients") or {}
            f_dict = {**row}
            f_dict['nom_societe'] = c.get('nom_societe')
            f_dict['contact'] = c.get('contact')
            f_dict['telephone'] = c.get('telephone')
            f_dict['email'] = c.get('email')
            all_factures.append(f_dict)

        aujourdhui = datetime.now().date()
        total_ca_ht, total_encaisse_ttc, total_retard_ttc, total_attente_ttc = 0.0, 0.0, 0.0, 0.0
        nb_retards = 0
        factures_en_retard = []
        clients_stats = {}
        modes_stats = {}  # Pour le camembert

        for f in all_factures:
            d_creation = parse_date(f.get('date_creation'))
            if not d_creation:
                continue

            if selected_annee != 'Toutes' and str(d_creation.year) != str(selected_annee):
                continue
            if selected_mois != 'Tous' and f"{d_creation.month:02d}" != str(selected_mois):
                continue

            statut = f.get('statut')
            ttc = f.get('total_ttc') or 0.0
            ht = f.get('total_ht') or 0.0
            client_nom = f.get('nom_societe') or 'Client Inconnu'
            
            mode_regl = f.get('mode_reglement') or 'Non spécifié'

            if client_nom not in clients_stats:
                clients_stats[client_nom] = {
                    'ca_ht': 0.0, 
                    'paye_ttc': 0.0, 
                    'retard_ttc': 0.0, 
                    'nb_factures': 0,
                    'modes': {}
                }
            clients_stats[client_nom]['nb_factures'] += 1

            if statut in ['Émise', 'Payée']:
                total_ca_ht += ht
                clients_stats[client_nom]['ca_ht'] += ht

            if statut == 'Payée':
                total_encaisse_ttc += ttc
                clients_stats[client_nom]['paye_ttc'] += ttc

                modes_stats[mode_regl] = modes_stats.get(mode_regl, 0.0) + ttc
                clients_stats[client_nom]['modes'][mode_regl] = clients_stats[client_nom]['modes'].get(mode_regl, 0.0) + ttc

            elif statut == 'Émise':
                date_ech = parse_date(f.get('date_echeance'))
                if date_ech and date_ech < aujourdhui:
                    jours_retard = (aujourdhui - date_ech).days
                    f['jours_retard'] = jours_retard
                    total_retard_ttc += ttc
                    nb_retards += 1
                    factures_en_retard.append(f)
                    clients_stats[client_nom]['retard_ttc'] += ttc
                else:
                    total_attente_ttc += ttc

        # Mise à jour des KPIs
        lbl_kpi_ca.set_text(f"{total_ca_ht:.2f} €")
        lbl_kpi_encaisse.set_text(f"{total_encaisse_ttc:.2f} €")
        lbl_kpi_retard_val.set_text(f"{total_retard_ttc:.2f} €")
        lbl_kpi_attente.set_text(f"{total_attente_ttc:.2f} €")

        if nb_retards > 0:
            card_retard_kpi.classes(remove="bg-slate-50 border-slate-200", add="bg-rose-50 border-rose-200")
            lbl_kpi_retard_title.classes(remove="text-slate-500", add="text-rose-700")
            lbl_kpi_retard_val.classes(remove="text-slate-800", add="text-rose-900")
            lbl_kpi_retard_sub.classes(remove="text-slate-400", add="text-rose-600 font-bold")
            lbl_kpi_retard_sub.set_text(f"{nb_retards} facture(s) dépassée(s)")
        else:
            card_retard_kpi.classes(remove="bg-rose-50 border-rose-200", add="bg-slate-50 border-slate-200")
            lbl_kpi_retard_title.classes(remove="text-rose-700", add="text-slate-500")
            lbl_kpi_retard_val.classes(remove="text-rose-900", add="text-slate-800")
            lbl_kpi_retard_sub.classes(remove="text-rose-600 font-bold", add="text-slate-400")
            lbl_kpi_retard_sub.set_text("0 facture en retard")

        # --- A. Graphique Courbe CA ---
        labels_graph, ca_annee_sel, ca_annee_n1 = [], [], []
        comparaison_active = (selected_annee != 'Toutes')

        if comparaison_active:
            annee_num = int(selected_annee)
            labels_graph = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin', 'Juil', 'Aoû', 'Sep', 'Oct', 'Nov', 'Déc']
            ca_annee_sel = [0.0] * 12
            ca_annee_n1 = [0.0] * 12

            for f in all_factures:
                d = parse_date(f.get('date_creation'))
                if d and f.get('statut') != 'Annulée':
                    ht = f.get('total_ht') or 0.0
                    m_idx = d.month - 1
                    if d.year == annee_num:
                        ca_annee_sel[m_idx] += ht
                    elif d.year == (annee_num - 1):
                        ca_annee_n1[m_idx] += ht
        else:
            monthly_sums = {}
            for f in all_factures:
                d = parse_date(f.get('date_creation'))
                if d and f.get('statut') != 'Annulée':
                    key = f"{d.year}-{d.month:02d}"
                    monthly_sums[key] = monthly_sums.get(key, 0.0) + (f.get('total_ht') or 0.0)
            
            for k in sorted(monthly_sums.keys()):
                labels_graph.append(k)
                ca_annee_sel.append(round(monthly_sums[k], 2))

        if comparaison_active:
            chip_comp.set_text(f"Comparaison : {selected_annee} vs {int(selected_annee)-1}")
            chip_comp.set_visibility(True)
        else:
            chip_comp.set_visibility(False)

        series_ca = [{
            'name': f'Année {selected_annee}' if comparaison_active else 'CA Mensuel HT',
            'type': 'line', 'smooth': True, 'symbol': 'circle', 'symbolSize': 8,
            'itemStyle': {'color': '#2563eb', 'borderWidth': 2, 'borderColor': '#ffffff'},
            'lineStyle': {'color': '#2563eb', 'width': 3},
            'areaStyle': {'color': {'type': 'linear', 'x': 0, 'y': 0, 'x2': 0, 'y2': 1, 'colorStops': [{'offset': 0, 'color': 'rgba(37, 99, 235, 0.20)'}, {'offset': 1, 'color': 'rgba(37, 99, 235, 0.0)'}]}},
            'data': [round(v, 2) for v in ca_annee_sel]
        }]
        if comparaison_active:
            series_ca.append({
                'name': f'Année {int(selected_annee)-1} (N-1)',
                'type': 'line', 'smooth': True, 'symbol': 'circle', 'symbolSize': 6,
                'itemStyle': {'color': '#94a3b8', 'borderWidth': 1, 'borderColor': '#ffffff'},
                'lineStyle': {'color': '#94a3b8', 'width': 2, 'type': 'dashed'},
                'data': [round(v, 2) for v in ca_annee_n1]
            })

        chart_ca.options['xAxis'] = {'type': 'category', 'boundaryGap': False, 'data': labels_graph, 'axisLabel': {'color': '#64748b'}}
        chart_ca.options['yAxis'] = {'type': 'value', 'axisLabel': {'formatter': '{value} €', 'color': '#64748b'}, 'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#e2e8f0'}}}
        chart_ca.options['tooltip'] = {'trigger': 'axis', 'formatter': '{b} <br/>{a0} : {c0} € HT' + ('<br/>{a1} : {c1} € HT' if comparaison_active else '')}
        chart_ca.options['legend'] = {'data': [s['name'] for s in series_ca], 'bottom': 0}
        chart_ca.options['grid'] = {'left': '3%', 'right': '4%', 'bottom': '12%', 'top': '5%', 'containLabel': True}
        chart_ca.options['series'] = series_ca
        chart_ca.update()

        # --- B. Graphique Camembert Modes de Règlement ---
        data_pie = [{'value': round(v, 2), 'name': k} for k, v in modes_stats.items() if v > 0]
        
        chart_modes.options['tooltip'] = {'trigger': 'item', 'formatter': '{b} : {c} € TTC ({d}%)'}
        chart_modes.options['legend'] = {'bottom': '0', 'left': 'center'}
        chart_modes.options['series'] = [{
            'name': 'Modes de règlement',
            'type': 'pie',
            'radius': ['40%', '70%'],
            'avoidLabelOverlap': True,
            'itemStyle': {
                'borderRadius': 8,
                'borderColor': '#fff',
                'borderWidth': 2
            },
            'label': {'show': False},
            'data': data_pie if data_pie else [{'value': 0, 'name': 'Aucun encaissement'}]
        }]
        chart_modes.update()

        # --- C. Update Tableau Retards ---
        if nb_retards > 0:
            icon_retard.props("color=negative")
            chip_retard_count.set_text(f"{nb_retards} en retard")
            chip_retard_count.set_visibility(True)
        else:
            icon_retard.props("color=grey")
            chip_retard_count.set_visibility(False)
            actions_bar_retard.set_visibility(False)

        rows_retard = []
        for fr in factures_en_retard:
            item = dict(fr)
            item['total_ttc_txt'] = f"{item.get('total_ttc', 0.0):.2f} €"
            item['jours_retard_txt'] = f"+{item['jours_retard']} jrs"
            rows_retard.append(item)

        grid_retard.rows = rows_retard
        grid_retard.update()

        # --- D. Update Tableau Clients avec Détail des Règlements ---
        rows_clients = []
        for client_nom, data in clients_stats.items():
            modes_str_list = [f"{m} ({val:.0f}€)" for m, val in data['modes'].items() if val > 0]
            modes_detail_txt = ", ".join(modes_str_list) if modes_str_list else "Aucun paiement"

            rows_clients.append({
                'nom': client_nom,
                'nb_factures': data['nb_factures'],
                'ca_ht_txt': f"{data['ca_ht']:.2f} €",
                'paye_ttc_txt': f"{data['paye_ttc']:.2f} €",
                'modes_detail_txt': modes_detail_txt,
                'retard_ttc_txt': f"{data['retard_ttc']:.2f} €" if data['retard_ttc'] > 0 else "-",
                'has_retard': data['retard_ttc'] > 0
            })
        
        grid_clients.rows = rows_clients
        grid_clients.update()

    # --- 5. ÉVÉNEMENTS ET MODALES ---
    def update_retard_actions():
        if grid_retard.selected:
            f_sel = grid_retard.selected[0]
            label_sel_retard.set_text(f"Facture {f_sel.get('numero_facture')} ({f_sel.get('nom_societe')}) - Total : {f_sel.get('total_ttc_txt')}")
            buttons_retard.clear()
            with buttons_retard:
                ui.button("Marquer comme Payée", icon="check_circle", on_click=lambda: marquer_comme_payee(f_sel.get('id'))).props("color=positive dense")
                ui.button("Coordonnées Client", icon="contact_phone", on_click=lambda: afficher_contact_client(f_sel)).props("outline color=slate dense")
            actions_bar_retard.set_visibility(True)
        else:
            actions_bar_retard.set_visibility(False)

    grid_retard.on('row-click', lambda e: grid_retard.selected.clear() or grid_retard.selected.append(e.args[1]) or update_retard_actions())
    filtre_annee.on_value_change(lambda: rafraichir_dashboard())
    filtre_mois.on_value_change(lambda: rafraichir_dashboard())

    def marquer_comme_payee(facture_id):
        date_jour = datetime.now().strftime("%Y-%m-%d")
        sup = database.get_supabase()
        sup.table("factures").update({"statut": "Payée", "date_paiement": date_jour}).eq("id", facture_id).execute()
        ui.notify("Paiement enregistré avec succès !", type="positive")
        rafraichir_dashboard()

    def afficher_contact_client(facture_info):
        with ui.dialog() as dialog, ui.card().classes("p-6 space-y-4 max-w-md w-full"):
            ui.label("Coordonnées de Relance").classes("text-lg font-bold text-slate-800 border-b pb-2")
            ui.label(f"Client : {facture_info.get('nom_societe')}").classes("font-semibold text-slate-700")
            if facture_info.get('contact'):
                ui.label(f"Contact référent : {facture_info.get('contact')}").classes("text-sm text-slate-600")
            with ui.column().classes("w-full p-4 bg-slate-50 border rounded-lg space-y-2 mt-2"):
                with ui.row().classes("items-center gap-2 text-slate-700"):
                    ui.icon("email", size="18px")
                    ui.label(facture_info.get('email') or "Non renseigné").classes("text-sm font-medium")
                with ui.row().classes("items-center gap-2 text-slate-700"):
                    ui.icon("phone", size="18px")
                    ui.label(facture_info.get('telephone') or "Non renseigné").classes("text-sm font-medium")
            with ui.row().classes("w-full justify-end mt-4"):
                ui.button("Fermer", on_click=dialog.close).props("flat color=slate")
        dialog.open()

    # Lancement du premier chargement
    rafraichir_dashboard()