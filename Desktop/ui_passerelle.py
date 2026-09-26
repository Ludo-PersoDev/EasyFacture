from datetime import datetime
import email.mime.application
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import smtplib
import zipfile
import database
from nicegui import ui
from ui_helpers import afficher_note_importante


def parse_date(date_str):
    if not date_str:
        return None
    date_str = str(date_str).strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d', '%d-%m-%Y'):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            pass
    return None


def trouver_chemin_pdf(nom_client, num_facture):
    if not nom_client or not num_facture:
        return None

    dossier_client_factures = os.path.join(
        'export', str(nom_client).strip(), 'factures'
    )

    chemin_1 = os.path.join(dossier_client_factures, f'facture_{num_facture}.pdf')
    if os.path.exists(chemin_1):
        return chemin_1

    chemin_2 = os.path.join(dossier_client_factures, f'{num_facture}.pdf')
    if os.path.exists(chemin_2):
        return chemin_2

    if os.path.exists(dossier_client_factures):
        for fichier in os.listdir(dossier_client_factures):
            if fichier.endswith('.pdf') and str(num_facture) in fichier:
                return os.path.join(dossier_client_factures, fichier)

    return None


def envoyer_email_depot_smtp(dest_email, liste_factures, config_smtp):
    """Envoie un e-mail avec la liste des PDF de factures joints vers la plateforme."""
    smtp_host = config_smtp.get('smtp_host') or config_smtp.get('smtp_serveur')
    smtp_port = int(
        config_smtp.get('smtp_port') or config_smtp.get('port_smtp') or 587
    )
    smtp_user = config_smtp.get('smtp_user') or config_smtp.get('email_expediteur')
    smtp_pass = config_smtp.get('smtp_password') or config_smtp.get('mot_de_passe')
    nom_entreprise = (
        config_smtp.get('nom_entreprise')
        or config_smtp.get('raison_sociale')
        or 'EasyFacture'
    )

    if not smtp_host or not smtp_user or not smtp_pass:
        raise Exception(
            'La configuration SMTP est incomplète dans la table paramètres.'
        )

    msg = MIMEMultipart()
    msg['From'] = f'{nom_entreprise} <{smtp_user}>'
    msg['To'] = dest_email
    msg['Subject'] = (
        f"Dépôt de factures - {nom_entreprise} - {datetime.now().strftime('%d/%m/%Y')}"
    )

    corps_html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #334155;">
        <h2>Dépôt automatique de factures - {nom_entreprise}</h2>
        <p>Veuillez trouver ci-joint les factures générées à transmettre :</p>
        <ul>
    """
    fichiers_joints_count = 0
    for row in liste_factures:
        pdf_path = row.get('pdf_path_reel')
        num_fac = row.get('numero_facture')
        client = row.get('nom_societe')
        corps_html += f'<li>Facture <b>{num_fac}</b> - Client : {client}</li>'

        if pdf_path and os.path.exists(pdf_path):
            with open(pdf_path, 'rb') as f:
                part = email.mime.application.MIMEApplication(
                    f.read(), _subtype='pdf'
                )
                part.add_header(
                    'Content-Disposition',
                    'attachment',
                    filename=os.path.basename(pdf_path),
                )
                msg.attach(part)
                fichiers_joints_count += 1

    corps_html += """
        </ul>
        <p><i>E-mail envoyé automatiquement depuis EasyFacture.</i></p>
      </body>
    </html>
    """

    msg.attach(MIMEText(corps_html, 'html'))

    if fichiers_joints_count == 0:
        raise Exception("Aucun fichier PDF valide à joindre à l'e-mail.")

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)

    return fichiers_joints_count


def render_passerelle_export():
    with ui.row().classes("w-full justify-between items-center mb-6"):  
        ui.label('Passerelle Factur-X & Dématérialisation').classes(
            'text-2xl font-bold text-slate-800'
        )
        ui.button("Infos Importantes", icon="warning", on_click=lambda: afficher_note_importante(
            "Points d'attention - Passerelle de transmission",
            [
                "• Calendrier légal : L'obligation d'émission électronique pour les entreprises individuelles s'applique à compter du 1er septembre 2027.",
                "• Les factures émises avant cette date sont automatiquement classées en 'Non concerné'."
            ],
            tuto_titre="Tuto : Gestion des statuts & Envois",
            tuto_etapes=[
                "• Filtrage : Utilisez la case à cocher pour masquer les factures non concernées.",
                "• Envoi groupé : Sélectionnez vos factures et transmettez-les via le serveur SMTP configuré."
            ]
        )).props("flat color=amber")

    # Récupération de la configuration Supabase (table 'parametres')
    supabase_client = database.get_conn()
    config_dict = {}
    try:
        res_cfg = supabase_client.table('parametres').select('*').limit(1).execute()
        if res_cfg.data:
            config_dict = res_cfg.data[0]
    except Exception as e:
        print(f"Erreur chargement paramètres : {e}")

    email_depot_initial = config_dict.get('email_depot_plateforme') or ''

    # --- 1. CONFIGURATION ADRESSE D'INGESTION ---
    with ui.card().classes(
        'w-full p-6 bg-white border border-slate-200 rounded-xl space-y-4 mb-6 shadow-sm'
    ):
        with ui.row().classes('items-center justify-between w-full'):
            with ui.row().classes('items-center gap-3'):
                ui.icon('cloud_upload', size='32px', color='primary')
                with ui.column():
                    ui.label(
                        'Paramètres de la Plateforme Récipiendaire (ex: Tiime, PPF)'
                    ).classes('text-lg font-bold text-slate-800')
                    ui.label(
                        "Adresse e-mail d'ingestion automatique de votre plateforme."
                    ).classes('text-xs text-slate-500')

        with ui.row().classes('w-full items-center gap-4 mt-2'):
            input_email_depot = (
                ui.input(
                    label="Adresse e-mail de dépôt plateforme",
                    placeholder='ex: factures-ludovic@tiime.fr',
                    value=email_depot_initial,
                )
                .classes('flex-1')
                .props('outlined dense')
            )

            def enregistrer_email_depot():
                try:
                    supabase_client.table('parametres').update({
                        'email_depot_plateforme': input_email_depot.value.strip()
                    }).eq('id', 1).execute()
                    ui.notify(
                        'Adresse e-mail de la plateforme sauvegardée !', type='positive'
                    )
                except Exception as ex:
                    ui.notify(f'Erreur lors de la sauvegarde : {str(ex)}', type='negative')

            ui.button(
                'Enregistrer', icon='save', on_click=enregistrer_email_depot
            ).props('color=primary dense')

    # --- 2. BARRE DE SELECTION ET FILTRES ---
    annee_actuelle = str(datetime.now().year)

    with ui.card().classes(
        'w-full p-6 bg-white border border-slate-200 rounded-xl space-y-4 mb-6 shadow-sm'
    ):
        with ui.row().classes(
            'w-full items-center justify-between gap-4 border-b pb-3'
        ):
            ui.label('Sélection des factures à exporter').classes(
                'text-lg font-bold text-slate-800'
            )
            
            with ui.row().classes('items-center gap-3'):
                select_annee = (
                    ui.select(
                        options={annee_actuelle: annee_actuelle, 'Toutes': 'Toutes'},
                        value=annee_actuelle,
                        label='Année',
                    )
                    .classes('w-28')
                    .props('dense outlined')
                )

                select_statut_facture = (
                    ui.select(
                        options={
                            'Toutes': 'Tous statuts factures',
                            'Émise': 'Émise',
                            'Payée': 'Payée',
                        },
                        value='Toutes',
                        label='Statut Facture',
                    )
                    .classes('w-44')
                    .props('dense outlined')
                )

                select_statut_export = (
                    ui.select(
                        options={
                            'Toutes': 'Tous les états d\'export',
                            'Non concerné': 'Non concerné',
                            'À transmettre': 'À transmettre',
                            'Transmise': 'Transmise',
                            'Erreur': 'Erreur',
                        },
                        value='Toutes',
                        label='État Téléversement',
                    )
                    .classes('w-52')
                    .props('dense outlined')
                )

        # Ligne de filtrage additionnelle (Case pour masquer les non concernés) et actions globales
        with ui.row().classes('w-full items-center justify-between py-2 border-b border-slate-100'):
            checkbox_masquer_non_concernes = ui.checkbox(
                'Masquer les factures non concernées par la réforme (< 01/09/2027)', 
                value=True
            ).on_value_change(lambda: charger_factures())
            
            lbl_compteur = ui.label('0 facture(s) sélectionnée(s)').classes(
                'text-sm font-semibold text-slate-600'
            )

        with ui.row().classes('w-full items-center justify-end py-1 gap-2'):
            ui.button("Tout cocher", icon="done_all", on_click=lambda: grid_export.selected.extend([r for r in grid_export.rows if r not in grid_export.selected]) or on_selection_change()).props("flat dense color=primary size=sm")
            ui.button("Tout décocher", icon="remove_done", on_click=lambda: grid_export.selected.clear() or on_selection_change()).props("flat dense color=slate size=sm")

        columns = [
            {
                'name': 'numero_facture',
                'label': 'N° Facture',
                'field': 'numero_facture',
                'align': 'left',
                'sortable': True,
            },
            {
                'name': 'date_creation',
                'label': 'Date',
                'field': 'date_creation',
                'align': 'center',
                'sortable': True,
            },
            {
                'name': 'nom_societe',
                'label': 'Client',
                'field': 'nom_societe',
                'align': 'left',
                'sortable': True,
            },
            {
                'name': 'total_ttc_txt',
                'label': 'Montant TTC',
                'field': 'total_ttc_txt',
                'align': 'right',
                'sortable': True,
            },
            {
                'name': 'statut',
                'label': 'Statut Interne',
                'field': 'statut',
                'align': 'center',
                'sortable': True,
            },
            {
                'name': 'statut_export_txt',
                'label': 'État Envoi Plateforme',
                'field': 'statut_export_txt',
                'align': 'center',
                'sortable': True,
            },
            {
                'name': 'pdf_existant',
                'label': 'Fichier PDF',
                'field': 'pdf_existant',
                'align': 'center',
                'sortable': True,
            },
        ]

        grid_export = ui.table(
            columns=columns, rows=[], row_key='id', selection='multiple', pagination=10
        ).classes('w-full')

        # Slot pour colorer les puces de statut d'export
        grid_export.add_slot(
            'body-cell-statut_export_txt',
            """
            <q-td :props="props">
                <q-chip dense :color="props.row.statut_export_plateforme === 'Transmise' ? 'emerald-2' : (props.row.statut_export_plateforme === 'Erreur' ? 'red-2' : (props.row.statut_export_plateforme === 'À transmettre' ? 'amber-2' : 'grey-3'))" 
                        :text-color="props.row.statut_export_plateforme === 'Transmise' ? 'emerald-9' : (props.row.statut_export_plateforme === 'Erreur' ? 'red-9' : (props.row.statut_export_plateforme === 'À transmettre' ? 'amber-9' : 'grey-8'))" 
                        :icon="props.row.statut_export_plateforme === 'Transmise' ? 'check_circle' : (props.row.statut_export_plateforme === 'Erreur' ? 'error' : (props.row.statut_export_plateforme === 'À transmettre' ? 'pending' : 'remove_circle_outline'))">
                    {{ props.value }}
                </q-chip>
            </q-td>
        """,
        )

        # --- 3. ACTIONS DE MASSE (ZIP & TRANSMISSION EMAIL SMTP) ---
        with ui.row().classes('w-full justify-end items-center pt-4 gap-3'):

            def generer_pack_zip():
                selection = grid_export.selected
                if not selection:
                    ui.notify(
                        'Veuillez sélectionner au moins une facture.', type='warning'
                    )
                    return

                os.makedirs('exports', exist_ok=True)
                zip_filename = (
                    'exports/pack_factures_'
                    f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                )

                fichiers_ajoutes = 0
                with zipfile.ZipFile(zip_filename, 'w') as zipf:
                    for row in selection:
                        pdf_path = row.get('pdf_path_reel')
                        if pdf_path and os.path.exists(pdf_path):
                            zipf.write(pdf_path, arcname=os.path.basename(pdf_path))
                            fichiers_ajoutes += 1

                if fichiers_ajoutes > 0:
                    ui.notify(
                        f'Pack ZIP créé avec succès ({fichiers_ajoutes} PDF) !',
                        type='positive',
                    )
                    ui.download(zip_filename)
                else:
                    ui.notify(
                        'Aucun fichier PDF trouvé sur le disque pour ces factures.',
                        type='negative',
                    )

            def envoyer_lot_plateforme():
                selection = grid_export.selected
                dest_email = input_email_depot.value.strip()

                if not selection:
                    ui.notify(
                        'Veuillez sélectionner au moins une facture.', type='warning'
                    )
                    return
                if not dest_email:
                    ui.notify(
                        "Veuillez renseigner l'adresse email de la plateforme ci-dessus.",
                        type='warning',
                    )
                    return

                try:
                    res_cfg = supabase_client.table('parametres').select('*').limit(1).execute()
                    config_smtp = res_cfg.data[0] if res_cfg.data else {}
                except Exception:
                    config_smtp = {}

                if not config_smtp:
                    ui.notify(
                        'Configuration introuvable dans les paramètres.', type='negative'
                    )
                    return

                ui.notify(
                    f'Envoi de {len(selection)} facture(s) vers {dest_email} en cours...',
                    type='info',
                )

                try:
                    nb_envoyes = envoyer_email_depot_smtp(
                        dest_email, selection, config_smtp
                    )

                    date_actuelle = datetime.now().strftime('%Y-%m-%d %H:%M')
                    ids = [row['id'] for row in selection]
                    
                    supabase_client.table('factures').update({
                        'statut_export_plateforme': 'Transmise',
                        'date_export_plateforme': date_actuelle
                    }).in_('id', ids).execute()

                    ui.notify(
                        f'Succès : {nb_envoyes} PDF transmis par e-mail à {dest_email} !',
                        type='positive',
                    )
                    charger_factures()

                except Exception as ex:
                    ids = [row['id'] for row in selection]
                    try:
                        supabase_client.table('factures').update({
                            'statut_export_plateforme': 'Erreur'
                        }).in_('id', ids).execute()
                    except Exception:
                        pass
                    
                    ui.notify(f'Erreur d\'envoi e-mail : {str(ex)}', type='negative')
                    charger_factures()

            ui.button(
                'Télécharger le Pack ZIP', icon='archive', on_click=generer_pack_zip
            ).props('outline color=primary')
            ui.button(
                'Transmettre à la Plateforme',
                icon='send',
                on_click=envoyer_lot_plateforme,
            ).props('color=positive font-bold')

    # --- 4. LOGIQUE DE CHARGEMENT SUPABASE ---
    # --- 4. LOGIQUE DE CHARGEMENT SUPABASE ---
    date_limite_reforme = datetime(2027, 9, 1).date()

    def charger_factures():
        try:
            res = (
                supabase_client.table('factures')
                .select('*, clients(nom_societe)')
                .neq('statut', 'Brouillon')
                .neq('statut', 'Annulée')
                .order('id', desc=True)
                .execute()
            )
            rows = res.data if hasattr(res, 'data') else []
        except Exception as e:
            print(f"DEBUG ERREUR SUPABASE FACTURES : {e}")
            rows = []

        sel_annee = select_annee.value
        sel_statut_fac = select_statut_facture.value
        sel_statut_exp = select_statut_export.value
        masquer_non_concernes = checkbox_masquer_non_concernes.value

        rows_formatted = []
        for r in rows:
            item = dict(r)
            if 'clients' in item and isinstance(item['clients'], dict):
                item['nom_societe'] = item['clients'].get('nom_societe', '')

            d = parse_date(item.get('date_creation'))

            # Détermination automatique du statut selon le calendrier légal (<= 01/09/2027)
            statut_exp = item.get('statut_export_plateforme')
            if not statut_exp or statut_exp.strip() == '':
                if d and d <= date_limite_reforme:
                    statut_exp = 'Non concerné'
                else:
                    statut_exp = 'À transmettre'

            item['statut_export_plateforme'] = statut_exp

            # Application robuste du filtre de masquage (Date <= 01/09/2027 ou statut Non concerné)
            if masquer_non_concernes:
                if (d and d <= date_limite_reforme) or statut_exp == 'Non concerné':
                    continue

            # Application des autres filtres
            if sel_annee != 'Toutes' and d and str(d.year) != sel_annee:
                continue
            if sel_statut_fac != 'Toutes' and item.get('statut') != sel_statut_fac:
                continue
            if sel_statut_exp != 'Toutes' and statut_exp != sel_statut_exp:
                continue

            num = item.get('numero_facture')
            client_nom = item.get('nom_societe')
            pdf_path = trouver_chemin_pdf(client_nom, num)

            item['pdf_path_reel'] = pdf_path
            item['total_ttc_txt'] = f"{(item.get('total_ttc') or 0.0):.2f} €"
            item['pdf_existant'] = '✅ Prêt' if pdf_path else '❌ Absent'

            if statut_exp == 'Transmise':
                date_exp = item.get('date_export_plateforme') or ''
                item['statut_export_txt'] = (
                    f"Transmise ({date_exp.split(' ')[0]})" if date_exp else 'Transmise'
                )
            else:
                item['statut_export_txt'] = statut_exp

            rows_formatted.append(item)

        grid_export.selected.clear()
        grid_export.rows = rows_formatted
        grid_export.update()
        on_selection_change()

    def on_selection_change():
        lbl_compteur.set_text(
            f'{len(grid_export.selected)} facture(s) sélectionnée(s)'
        )

    grid_export.on('selection', on_selection_change)
    select_annee.on_value_change(lambda: charger_factures())
    select_statut_facture.on_value_change(lambda: charger_factures())
    select_statut_export.on_value_change(lambda: charger_factures())

    charger_factures()