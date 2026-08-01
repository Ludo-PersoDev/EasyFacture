from datetime import datetime
import os
import zipfile
from database import get_backup_path

DB_FILENAME = "FactureX.db"
MAX_BACKUPS = 8


def lancer_sauvegarde_automatique():
  """Effectue une sauvegarde automatique quotidienne vers le dossier configuré."""
  try:
    # 1. Récupération du dossier cible (Dossier personnalisé ou 'auto_backups')
    backup_dir = get_backup_path()

    if not os.path.exists(backup_dir):
      os.makedirs(backup_dir, exist_ok=True)

    aujourdhui = datetime.now().strftime("%Y-%m-%d")
    nom_zip = f"EasyFacture_Auto_{aujourdhui}.zip"
    chemin_zip = os.path.join(backup_dir, nom_zip)

    # 2. Vérifie si une sauvegarde a DÉJÀ été faite aujourd'hui
    if os.path.exists(chemin_zip):
      return

    # 3. Création du fichier ZIP
    with zipfile.ZipFile(chemin_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
      if os.path.exists(DB_FILENAME):
        zipf.write(DB_FILENAME, arcname=DB_FILENAME)

      if os.path.exists("exports"):
        for root, _, files in os.walk("exports"):
          for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, ".")
            zipf.write(full_path, arcname=rel_path)

    # 4. Rotation des 8 plus récents dans ce dossier
    fichiers = [
        os.path.join(backup_dir, f)
        for f in os.listdir(backup_dir)
        if f.startswith("EasyFacture_Auto_") and f.endswith(".zip")
    ]

    fichiers.sort(key=lambda x: os.path.getmtime(x))

    while len(fichiers) > MAX_BACKUPS:
      ancien_fichier = fichiers.pop(0)
      os.remove(ancien_fichier)

  except Exception as e:
    print(f"[Backup Auto Error] Impossible de sauvegarder : {e}")