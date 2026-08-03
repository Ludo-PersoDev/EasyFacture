from datetime import datetime, timedelta
import os
import sqlite3
import zipfile
from database import get_backup_path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

DB_FILENAME = 'FactureX.db'
MAX_BACKUPS = 8

# ID de ton dossier Google Drive principal
GOOGLE_DRIVE_FOLDER_ID = '1Aeo7n-u4zbbTjzrZG1-s7f9dM8N37eeI'
SCOPES = ['https://www.googleapis.com/auth/drive']


def get_drive_service():
  """Authentifie et retourne le service Google Drive via le token OAuth personnel."""
  creds = None
  # Le token.json stocke tes identifiants de connexion persistants
  if os.path.exists('token.json'):
    creds = Credentials.from_authorized_user_file('token.json', SCOPES)

  # Si le token est expiré ou inexistant, on rafraîchit ou on se connecte
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      if not os.path.exists('credentials.json'):
        raise FileNotFoundError(
            'Le fichier credentials.json est introuvable.'
        )
      flow = InstalledAppFlow.from_client_secrets_file(
          'credentials.json', SCOPES
      )
      creds = flow.run_local_server(port=0)

    # Sauvegarde du token pour les prochaines utilisations
    with open('token.json', 'w') as token:
      token.write(creds.to_json())

  return build('drive', 'v3', credentials=creds)


def get_company_name():
  """Récupère le nom de l'entreprise depuis la base de données locale."""
  try:
    if not os.path.exists(DB_FILENAME):
      return 'EasyFacture_Default'
    conn = sqlite3.connect(DB_FILENAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    row = cursor.execute('SELECT nom_entreprise FROM parametres WHERE id = 1').fetchone()
    conn.close()
    if row and row['nom_entreprise']:
      nom = ''.join(
          c for c in row['nom_entreprise'] if c.isalnum() or c in (' ', '_', '-')
      ).strip()
      return nom.replace(' ', '_')
  except Exception:
    pass
  return 'MonEntreprise'


def get_or_create_drive_subfolder(service, parent_id, folder_name):
  """Vérifie si le sous-dossier de la société existe sur ton Drive, sinon le crée."""
  query = (
      f"'{parent_id}' in parents and name = '{folder_name}' and mimeType ="
      " 'application/vnd.google-apps.folder' and trashed = false"
  )
  results = (
      service.files().list(q=query, spaces='drive', fields='files(id)').execute()
  )
  folders = results.get('files', [])

  if folders:
    return folders[0]['id']
  else:
    folder_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id],
    }
    folder = service.files().create(body=folder_metadata, fields='id').execute()
    print(f'[Backup Auto] Sous-dossier Drive créé pour : {folder_name}')
    return folder['id']


def cleanup_old_drive_files(service, folder_id):
  """Supprime les fichiers de sauvegarde de plus de 8 jours sur le Google Drive."""
  try:
    query = f"'{folder_id}' in parents and trashed = false"
    results = (
        service.files()
        .list(q=query, spaces='drive', fields='files(id, name, createdTime)')
        .execute()
    )
    files = results.get('files', [])

    limite_date = datetime.utcnow() - timedelta(days=8)

    for file in files:
      name = file.get('name', '')
      if name.startswith('EasyFacture_Auto_') and name.endswith('.zip'):
        try:
          date_str = name.replace('EasyFacture_Auto_', '').replace('.zip', '')
          file_date = datetime.strptime(date_str, '%Y-%m-%d')
          if file_date < limite_date:
            print(
                f"[Backup Auto] Suppression sur le Drive de l'ancienne"
                f' sauvegarde : {name}'
            )
            service.files().delete(fileId=file['id']).execute()
        except ValueError:
          pass
  except Exception as e:
    print(f'[Backup Auto Error] Erreur lors du nettoyage Google Drive : {e}')


def upload_to_google_drive(file_path):
  """Envoie le ZIP dans le sous-dossier de l'entreprise sur ton Google Drive."""
  print(f"[Backup Auto] Envoi de {file_path} sur ton Google Drive...")

  try:
    service = get_drive_service()
    company_name = get_company_name()

    subfolder_id = get_or_create_drive_subfolder(
        service, GOOGLE_DRIVE_FOLDER_ID, company_name
    )

    file_name = os.path.basename(file_path)

    # 1. Supprimer un éventuel ancien fichier du même jour
    query = (
        f"'{subfolder_id}' in parents and name = '{file_name}' and"
        ' trashed = false'
    )
    results = (
        service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    )
    files = results.get('files', [])

    if files:
      for existing_file in files:
        service.files().delete(fileId=existing_file['id']).execute()

    # 2. Upload du nouveau fichier
    file_metadata = {'name': file_name, 'parents': [subfolder_id]}
    media = MediaFileUpload(file_path, resumable=True)

    service.files().create(
        body=file_metadata, media_body=media, fields='id'
    ).execute()
    print(
        f"[Backup Auto] Fichier {file_name} envoyé avec succès dans ton dossier"
        f' Drive ({company_name}).'
    )

    # 3. Nettoyage des fichiers de + de 8 jours
    cleanup_old_drive_files(service, subfolder_id)

  except Exception as e:
    print(f'[Backup Auto Error] Échec de l\'upload Google Drive : {e}')


def lancer_sauvegarde_automatique():
  """Effectue la sauvegarde locale et déclenche l'envoi sur ton Drive."""
  try:
    backup_dir = get_backup_path()

    if not os.path.exists(backup_dir):
      os.makedirs(backup_dir, exist_ok=True)

    aujourdhui = datetime.now().strftime('%Y-%m-%d')
    nom_zip = f'EasyFacture_Auto_{aujourdhui}.zip'
    chemin_zip = os.path.join(backup_dir, nom_zip)

    # Création du ZIP local
    with zipfile.ZipFile(chemin_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
      if os.path.exists(DB_FILENAME):
        zipf.write(DB_FILENAME, arcname=DB_FILENAME)

      if os.path.exists('exports'):
        for root, _, files in os.walk('exports'):
          for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, '.')
            zipf.write(full_path, arcname=rel_path)

    # Envoi sur ton Google Drive
    upload_to_google_drive(chemin_zip)

    # Rotation locale (garde les 8 plus récents)
    fichiers = [
        os.path.join(backup_dir, f)
        for f in os.listdir(backup_dir)
        if f.startswith('EasyFacture_Auto_') and f.endswith('.zip')
    ]

    fichiers.sort(key=lambda x: os.path.getmtime(x))

    while len(fichiers) > MAX_BACKUPS:
      ancien_fichier = fichiers.pop(0)
      os.remove(ancien_fichier)

  except Exception as e:
    print(f'[Backup Auto Error] Impossible de sauvegarder : {e}')