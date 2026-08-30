import os
import re
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
io_import = __import__('io')

SCOPES = ['https://www.googleapis.com/auth/drive']

# ID de ton dossier Google Drive principal dédié aux backups
GOOGLE_DRIVE_FOLDER_ID = '1mI8BWRK6A4e1lDwwLmcXTUYrCBeJ3NOh'

def get_drive_service():
    """Authentifie et retourne le service Google Drive."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        else:
            raise Exception("Impossible d'authentifier Google Drive : token.json invalide ou manquant.")
            
    return build('drive', 'v3', credentials=creds)

def nettoyer_siret(siret_brut: str) -> str:
    """Nettoie le SIRET pour ne garder que les 14 chiffres stricts."""
    if not siret_brut:
        return ""
    return re.sub(r'\D', '', str(siret_brut))

def obtenir_ou_creer_dossier_siret(service, siret):
    """Recherche ou crée un dossier sur le Drive basé sur le SIRET strict à 14 chiffres dans le dossier parent dédié."""
    siret_propre = nettoyer_siret(siret)
    if len(siret_propre) != 14:
        raise ValueError("Le SIRET doit contenir exactement 14 chiffres.")
        
    # Recherche du dossier SIRET à l'intérieur du dossier parent GOOGLE_DRIVE_FOLDER_ID
    query = f"'{GOOGLE_DRIVE_FOLDER_ID}' in parents and mimeType = 'application/vnd.google-apps.folder' and name = '{siret_propre}' and trashed = false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    folders = results.get('files', [])
    
    if folders:
        return folders[0]['id']
    else:
        file_metadata = {
            'name': siret_propre,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [GOOGLE_DRIVE_FOLDER_ID]
        }
        folder = service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')

def pousser_sauvegarde_vers_drive(zip_filename, siret):
    """Pousse la sauvegarde, en écrasant l'ancien fichier du même jour s'il existe."""
    service = get_drive_service()
    folder_id = obtenir_ou_creer_dossier_siret(service, siret)
    
    file_name = os.path.basename(zip_filename)
    
    # 1. Rechercher si un fichier avec le même nom existe déjà dans ce dossier
    query = f"'{folder_id}' in parents and name = '{file_name}' and trashed = false"
    results = service.files().list(q=query, fields="files(id)").execute()
    existing_files = results.get('files', [])
    
    # 2. Supprimer les fichiers trouvés (écrasement)
    for f in existing_files:
        service.files().delete(fileId=f['id']).execute()
    
    # 3. Upload du nouveau fichier
    file_metadata = {
        'name': file_name,
        'parents': [folder_id]
    }
    media = MediaFileUpload(zip_filename, mimetype='application/zip')
    service.files().create(body=file_metadata, media_body=media, fields='id').execute()

def lister_sauvegardes_drive_par_siret(siret):
    """Liste uniquement les sauvegardes du dossier correspondant au SIRET dans le répertoire dédié."""
    try:
        siret_propre = nettoyer_siret(siret)
        if len(siret_propre) != 14:
            return []

        service = get_drive_service()
        query_folder = f"'{GOOGLE_DRIVE_FOLDER_ID}' in parents and mimeType = 'application/vnd.google-apps.folder' and name = '{siret_propre}' and trashed = false"
        res_folder = service.files().list(q=query_folder, fields="files(id)").execute()
        folders = res_folder.get('files', [])
        
        if not folders:
            return []
        
        folder_id = folders[0]['id']
        
        query_files = f"'{folder_id}' in parents and trashed = false"
        results = service.files().list(
            q=query_files,
            spaces='drive',
            fields="files(id, name, size, createdTime)",
            orderBy="createdTime desc"
        ).execute()
        
        return results.get('files', [])
    except Exception as e:
        print(f"Erreur lors de la récupération des sauvegardes Drive : {e}")
        return []

def telecharger_sauvegarde_drive(file_id, chemin_destination):
    """Télécharge un fichier de sauvegarde depuis le Drive."""
    try:
        service = get_drive_service()
        request = service.files().get_media(fileId=file_id)
        
        fh = io_import.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
            
        fh.seek(0)
        with open(chemin_destination, 'wb') as f:
            f.write(fh.read())
            
        return True
    except Exception as e:
        print(f"Erreur lors du téléchargement du fichier Drive : {e}")
        return False