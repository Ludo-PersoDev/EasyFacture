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
  smtp_host = config_smtp.get('smtp_host') or config_smtp.get('serveur_smtp')
  smtp_port = int(
      config_smtp.get('smtp_port') or config_smtp.get('port_smtp') or 587
  )
  smtp_user = config_smtp.get('smtp_user') or config_smtp.get('email_expediteur')
  smtp_pass = config_smtp.get('smtp_pass') or config_smtp.get('mot_de_passe')
  nom_entreprise = (
      config_smtp.get('nom_entreprise')
      or config_smtp.get('raison_sociale')
      or 'FactureX Pro'
  )

  if not smtp_host or not smtp_user or not smtp_pass:
    raise Exception(
        'La configuration SMTP est incomplète dans les paramètres de'
        " l'entreprise."
    )

  # Création du message MIME
  msg = MIMEMultipart()
  msg['From'] = f'{nom_entreprise} <{smtp_user}>'
  msg['To'] = dest_email
  msg['Subject'] = (
      f"Dépôt de factures - {nom_entreprise} -"
      f" {datetime.now().strftime('%d/%m/%Y')}"
  )

  corps_html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #334155;">
        <h2>Dépôt automatique de factures - {nom_entreprise}</h2>
        <p>Veuillez trouver ci-joint les factures générées à traiter et convertir pour la dématérialisation :</p>
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
        <p><i>E-mail envoyé automatiquement depuis FactureX Pro.</i></p>
      </body>
    </html>
    """

  msg.attach(MIMEText(corps_html, 'html'))

  if fichiers_joints_count == 0:
    raise Exception('Aucun fichier PDF valide à joindre à l\'e-mail.')

  # Connexion et envoi SMTP
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
                "• EasyFacture ne génère pas directement le format Factur-X lui-même : l'application transmet vos PDF standardisés à la passerelle.",
                "• PRÉREQUIS INDISPENSABLE : Pour que l'envoi fonctionne, la section d'envoi de mail SMTP doit être correctement remplie et paramétrée dans les paramètres de l'entreprise."
            ],
            tuto_titre="Tuto : Fonctionnement des envois & Suivi",
            tuto_etapes=[
                "• Adresse de dépôt : Renseignez l'adresse e-mail de dépôt fournie par votre plateforme (Tiime, PPF, etc.) dans la zone dédiée.",
                "• Suivi des transmissions : Le tableau de bord indique précisément l'état de chaque facture (transmise ou à transmettre) et vérifie la présence du PDF.",
                "• Envoi et Pack ZIP : Vous pouvez expédier les fichiers directement par e-mail vers la plateforme ou télécharger un pack ZIP global pour vos archives."
            ]
        )).props("flat color=amber")

      conn_init = database.get_conn()
      try:
        conn_init.execute(
            'ALTER TABLE factures ADD COLUMN statut_export_plateforme TEXT DEFAULT'
            " 'À transmettre'"
        )
        conn_init.execute(
            'ALTER TABLE factures ADD COLUMN date_export_plateforme TEXT'
        )
        conn_init.commit()
      except Exception:
        pass

      row_config = None
      conn_cfg = database.get_conn()
      try:
        row_config = conn_cfg.execute(
            'SELECT * FROM configuration WHERE id=1'
        ).fetchone()
      except Exception:
        pass

      config_dict = dict(row_config) if row_config else {}
      email_depot_initial = config_dict.get('email_depot_plateforme') or ''

      # --- 1. CONFIGURATION ADRESSE D'INGESTION ---
      with ui.card().classes(
          'w-full p-6 bg-white border border-slate-200 rounded-xl space-y-4 mb-6'
          ' shadow-sm'
      ):
        with ui.row().classes('items-center justify-between w-full'):
          with ui.row().classes('items-center gap-3'):
            ui.icon('cloud_upload', size='32px', color='primary')
            with ui.column():
              ui.label(
                  'Paramètres de la Plateforme Récipiendaire (ex: Tiime, PPF)'
              ).classes('text-lg font-bold text-slate-800')
              ui.label(
                  "Définissez l'adresse email d'ingestion automatique de votre"
                  ' plateforme.'
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
            c = database.get_conn()
            try:
              c.execute(
                  'ALTER TABLE configuration ADD COLUMN email_depot_plateforme TEXT'
              )
            except Exception:
              pass
            c.execute(
                'UPDATE configuration SET email_depot_plateforme = ? WHERE id = 1',
                (input_email_depot.value.strip(),),
            )
            c.commit()
            ui.notify(
                'Adresse e-mail de la plateforme sauvegardée !', type='positive'
            )

          ui.button(
              'Enregistrer', icon='save', on_click=enregistrer_email_depot
          ).props('color=primary dense')

      # --- 2. BARRE DE SELECTION ET FILTRES ---
      annee_actuelle = str(datetime.now().year)

      with ui.card().classes(
          'w-full p-6 bg-white border border-slate-200 rounded-xl space-y-4 mb-6'
          ' shadow-sm'
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
                        'À transmettre': 'À transmettre uniquement',
                        'Transmise': 'Transmises uniquement',
                        'Toutes': 'Tous les états d\'export',
                    },
                    value='À transmettre',
                    label='État Téléversement',
                )
                .classes('w-56')
                .props('dense outlined')
            )

        # Table des factures
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

        grid_export.add_slot(
            'body-cell-statut_export_txt',
            """
            <q-td :props="props">
                <q-chip dense :color="props.row.statut_export_plateforme === 'Transmise' ? 'emerald-2' : 'amber-2'" 
                        :text-color="props.row.statut_export_plateforme === 'Transmise' ? 'emerald-9' : 'amber-9'" 
                        :icon="props.row.statut_export_plateforme === 'Transmise' ? 'check_circle' : 'pending'">
                    {{ props.value }}
                </q-chip>
            </q-td>
        """,
        )

        # --- 3. ACTIONS DE MASSE (ZIP & TRANSMISSION EMAIL SMTP) ---
        with ui.row().classes('w-full justify-between items-center pt-4'):
          lbl_compteur = ui.label('0 facture(s) sélectionnée(s)').classes(
              'text-sm font-semibold text-slate-600'
          )

          with ui.row().classes('gap-3'):

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

              # Récupération de la configuration SMTP
              c_smtp = database.get_conn()
              row_s = c_smtp.execute(
                  'SELECT * FROM configuration WHERE id=1'
              ).fetchone()

              if not row_s:
                ui.notify(
                    'Configuration d\'entreprise introuvable.', type='negative'
                )
                return

              config_smtp = dict(row_s)

              ui.notify(
                  f'Envoi de {len(selection)} facture(s) vers {dest_email} en'
                  ' cours...',
                  type='info',
              )

              try:
                nb_envoyes = envoyer_email_depot_smtp(
                    dest_email, selection, config_smtp
                )

                # Mise à jour du statut en BDD après succès de l'envoi
                date_actuelle = datetime.now().strftime('%Y-%m-%d %H:%M')
                conn_upd = database.get_conn()
                for row in selection:
                  conn_upd.execute(
                      "UPDATE factures SET statut_export_plateforme = 'Transmise',"
                      ' date_export_plateforme = ? WHERE id = ?',
                      (date_actuelle, row['id']),
                  )
                conn_upd.commit()

                ui.notify(
                    f'Succès : {nb_envoyes} PDF transmis par e-mail à {dest_email} !',
                    type='positive',
                )
                charger_factures()

              except Exception as ex:
                ui.notify(f'Erreur d\'envoi e-mail : {str(ex)}', type='negative')

            ui.button(
                'Télécharger le Pack ZIP', icon='archive', on_click=generer_pack_zip
            ).props('outline color=primary')
            ui.button(
                'Transmettre à la Plateforme',
                icon='send',
                on_click=envoyer_lot_plateforme,
            ).props('color=positive font-bold')

      # --- 4. LOGIQUE DE CHARGEMENT SÉCURISÉE ---
      def charger_factures():
        conn = database.get_conn()
        try:
          # On teste l'appel brut pour voir l'erreur exacte si elle survient
          res = conn.table('factures').select('*, clients(nom_societe)').neq('statut', 'Brouillon').neq('statut', 'Annulée').order('id', desc=True).execute()
          rows = res.data if hasattr(res, 'data') else []
        except Exception as e:
          print(f"DEBUG ERREUR SUPABASE FACTURES : {e}")
          rows = []

        sel_annee = select_annee.value
        sel_statut_fac = select_statut_facture.value
        sel_statut_exp = select_statut_export.value

        rows_formatted = []
        for r in rows:
          item = dict(r)
          # Si le JOIN Supabase renvoie un objet imbriqué 'clients'
          if 'clients' in item and isinstance(item['clients'], dict):
            item['nom_societe'] = item['clients'].get('nom_societe', '')

          d = parse_date(item.get('date_creation'))

          statut_exp = item.get('statut_export_plateforme') or 'À transmettre'
          item['statut_export_plateforme'] = statut_exp

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
            item['stat_export_txt'] = (
                f"Transmise ({date_exp.split(' ')[0]})" if date_exp else 'Transmise'
            )
          else:
            item['statut_export_txt'] = 'À transmettre'

          rows_formatted.append(item)

        grid_export.selected.clear()
        grid_export.rows = rows_formatted
        grid_export.update()

      def on_selection_change():
        lbl_compteur.set_text(
            f'{len(grid_export.selected)} facture(s) sélectionnée(s)'
        )

      grid_export.on('selection', on_selection_change)
      select_annee.on_value_change(lambda: charger_factures())
      select_statut_facture.on_value_change(lambda: charger_factures())
      select_statut_export.on_value_change(lambda: charger_factures())

      charger_factures()