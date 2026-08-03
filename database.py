from datetime import datetime
import os
import shutil
import sqlite3

DB_PATH = "FactureX.db"


def get_conn():
  conn = sqlite3.connect(DB_PATH)
  conn.row_factory = sqlite3.Row
  return conn


def initialiser_bdd():
  """Initialise l'ensemble des tables de la base de données SQLite."""
  conn = get_conn()
  cursor = conn.cursor()
  cursor.execute("PRAGMA foreign_keys = ON;")

  # --- 1. PARAMÈTRES ENTREPRISE ---
  cursor.execute("""CREATE TABLE IF NOT EXISTS parametres (
        id INTEGER PRIMARY KEY DEFAULT 1,
        nom_entreprise TEXT DEFAULT '',
        adresse TEXT DEFAULT '',
        code_postal TEXT DEFAULT '',
        ville TEXT DEFAULT '',
        pays TEXT DEFAULT 'France',
        telephone TEXT DEFAULT '',
        email TEXT DEFAULT '',
        siret TEXT DEFAULT '',
        rcs TEXT DEFAULT '',
        ape TEXT DEFAULT '',
        num_tva TEXT DEFAULT '',
        tva_exoneree BOOLEAN DEFAULT 1,
        mention_tva_exoneree TEXT DEFAULT 'TVA non applicable, art. 293 B du CGI',
        iban TEXT DEFAULT '',
        bic TEXT DEFAULT '',
        nom_banque TEXT DEFAULT '',
        mentions_legales TEXT DEFAULT '',
        logo_path TEXT DEFAULT '',
        smtp_server TEXT DEFAULT 'smtp.gmail.com',
        smtp_port INTEGER DEFAULT 587,
        smtp_user TEXT DEFAULT '',
        smtp_password TEXT DEFAULT '',
        backup_folder_path TEXT DEFAULT 'auto_backups'
    )""")

  cursor.execute("SELECT COUNT(*) FROM parametres")
  if cursor.fetchone()[0] == 0:
    cursor.execute(
        "INSERT INTO parametres (id, tva_exoneree, backup_folder_path) VALUES"
        " (1, 1, 'auto_backups')"
    )

  # --- 2. CLIENTS & ÉTABLISSEMENTS MULTISITES ---
  cursor.execute("""CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom_societe TEXT NOT NULL,
        contact TEXT DEFAULT '',
        adresse TEXT DEFAULT '',
        cp TEXT DEFAULT '',
        ville TEXT DEFAULT '',
        pays TEXT DEFAULT 'France',
        email TEXT DEFAULT '',
        telephone TEXT DEFAULT '',
        est_particulier BOOLEAN DEFAULT 0,
        siret TEXT DEFAULT '',
        tva_intra TEXT DEFAULT '',
        rcs TEXT DEFAULT '',
        ape TEXT DEFAULT '',
        sans_tva BOOLEAN DEFAULT 0,
        recap_interventions BOOLEAN DEFAULT 0,
        multi_etab BOOLEAN DEFAULT 0,
        modele_facture TEXT DEFAULT 'condense'
    )""")

  cursor.execute("""CREATE TABLE IF NOT EXISTS etablissements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER NOT NULL,
        nom_site TEXT NOT NULL,
        adresse TEXT DEFAULT '',
        cp TEXT DEFAULT '',
        ville TEXT DEFAULT '',
        FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE
    )""")

  # --- 3. CATALOGUE PRESTATIONS & TARIFS CLIENTS ---
  cursor.execute("""CREATE TABLE IF NOT EXISTS prestations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        designation TEXT NOT NULL,
        prix_ht REAL DEFAULT 0.0,
        unite TEXT DEFAULT 'Heure',
        taux_tva REAL DEFAULT 0.0
    )""")

  cursor.execute("""CREATE TABLE IF NOT EXISTS client_tarifs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER NOT NULL,
        prestation_id INTEGER NOT NULL,
        prix_specifique_ht REAL,
        est_actif BOOLEAN DEFAULT 1,
        FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE,
        FOREIGN KEY(prestation_id) REFERENCES prestations(id) ON DELETE CASCADE,
        UNIQUE(client_id, prestation_id)
    )""")

  # --- 4. MODULE DEVIS ---
  cursor.execute("""CREATE TABLE IF NOT EXISTS devis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_devis TEXT UNIQUE NOT NULL,
        client_id INTEGER NOT NULL,
        date_creation DATE NOT NULL,
        date_validite DATE,
        date_prevue_execution DATE,
        statut TEXT DEFAULT 'Brouillon',
        total_ht REAL DEFAULT 0.0,
        total_tva REAL DEFAULT 0.0,
        total_ttc REAL DEFAULT 0.0,
        remarque TEXT DEFAULT '',
        FOREIGN KEY(client_id) REFERENCES clients(id)
    )""")

  cursor.execute("""CREATE TABLE IF NOT EXISTS devis_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        devis_id INTEGER NOT NULL,
        prestation_id INTEGER NOT NULL,
        quantite REAL DEFAULT 1.0,
        prix_unitaire_ht REAL NOT NULL,
        taux_tva REAL DEFAULT 0.0,
        FOREIGN KEY(devis_id) REFERENCES devis(id) ON DELETE CASCADE,
        FOREIGN KEY(prestation_id) REFERENCES prestations(id)
    )""")

  # --- 5. MODULE FACTURES ---
  cursor.execute("""CREATE TABLE IF NOT EXISTS factures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_facture TEXT UNIQUE NOT NULL,
        client_id INTEGER NOT NULL,
        date_creation DATE NOT NULL,
        date_echeance DATE,
        date_paiement DATE,
        statut TEXT DEFAULT 'Émise', -- 'Brouillon', 'Émise', 'Payée', 'Annulée'
        total_ht REAL DEFAULT 0.0,
        total_tva REAL DEFAULT 0.0,
        total_ttc REAL DEFAULT 0.0,
        mode_reglement TEXT DEFAULT 'Virement bancaire',
        conditions_reglement TEXT DEFAULT 'Paiement à 30 jours',
        pdf_path TEXT DEFAULT '',
        date_envoi_mail TEXT DEFAULT '',
        recap_genere BOOLEAN DEFAULT 0,
        FOREIGN KEY(client_id) REFERENCES clients(id)
    )""")

  cursor.execute("""CREATE TABLE IF NOT EXISTS facture_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        facture_id INTEGER NOT NULL,
        intervention_id INTEGER NOT NULL,
        FOREIGN KEY(facture_id) REFERENCES factures(id) ON DELETE CASCADE,
        FOREIGN KEY(intervention_id) REFERENCES interventions(id)
    )""")

  # --- 6. MODULE INTERVENTIONS ---
  cursor.execute("""CREATE TABLE IF NOT EXISTS interventions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_intervention TEXT UNIQUE,
        client_id INTEGER NOT NULL,
        etablissement_id INTEGER,
        prestation_id INTEGER,
        devis_id INTEGER,
        facture_id INTEGER, -- Clef directe vers la facture associée
        date DATE NOT NULL,
        heure_debut TEXT,
        heure_fin TEXT,
        quantite REAL DEFAULT 1.0,
        prix_final_ht REAL DEFAULT 0.0,
        taux_tva REAL DEFAULT 0.0,
        statut TEXT DEFAULT 'En attente',
        commentaire TEXT DEFAULT '',
        FOREIGN KEY(client_id) REFERENCES clients(id),
        FOREIGN KEY(etablissement_id) REFERENCES etablissements(id),
        FOREIGN KEY(prestation_id) REFERENCES prestations(id),
        FOREIGN KEY(devis_id) REFERENCES devis(id) ON DELETE SET NULL,
        FOREIGN KEY(facture_id) REFERENCES factures(id) ON DELETE SET NULL
    )""")

  # --- MIGRATIONS AUTOMATIQUES ---
  cursor.execute("PRAGMA table_info(parametres)")
  cols_param = [column[1] for column in cursor.fetchall()]
  if "backup_folder_path" not in cols_param:
    cursor.execute(
        "ALTER TABLE parametres ADD COLUMN backup_folder_path TEXT DEFAULT"
        " 'auto_backups'"
    )

  cursor.execute("PRAGMA table_info(clients)")
  cols_client = [column[1] for column in cursor.fetchall()]
  if "modele_facture" not in cols_client:
    cursor.execute(
        "ALTER TABLE clients ADD COLUMN modele_facture TEXT DEFAULT 'condense'"
    )

  cursor.execute("PRAGMA table_info(interventions)")
  cols_interv = [column[1] for column in cursor.fetchall()]
  if "facture_id" not in cols_interv:
    cursor.execute(
        "ALTER TABLE interventions ADD COLUMN facture_id INTEGER REFERENCES"
        " factures(id) ON DELETE SET NULL"
    )

  cursor.execute("PRAGMA table_info(factures)")
  cols_fact = [column[1] for column in cursor.fetchall()]
  if "pdf_path" not in cols_fact:
    cursor.execute(
        "ALTER TABLE factures ADD COLUMN pdf_path TEXT DEFAULT ''"
    )
  if "date_envoi_mail" not in cols_fact:
    cursor.execute(
        "ALTER TABLE factures ADD COLUMN date_envoi_mail TEXT DEFAULT ''"
    )
  if "conditions_reglement" not in cols_fact:
    cursor.execute(
        "ALTER TABLE factures ADD COLUMN conditions_reglement TEXT DEFAULT"
        " 'Paiement à 30 jours'"
    )
  if "mode_reglement" not in cols_fact:
    cursor.execute(
        "ALTER TABLE factures ADD COLUMN mode_reglement TEXT DEFAULT 'Virement"
        " bancaire'"
    )

  conn.commit()
  conn.close()

  # --- INITIALISATION DU LOGO PAR DÉFAUT ---
  os.makedirs("assets", exist_ok=True)
  chemin_logo = os.path.join("assets", "logo.png")
  if not os.path.exists(chemin_logo):
    # Si tu as placé un logo initial de secours dans ton projet (ex: logo_initial.png)
    if os.path.exists("logo_initial.png"):
      shutil.copy("logo_initial.png", chemin_logo)
      print("✓ Logo par défaut initialisé dans assets/logo.png")


# --- FONCTIONS UTILITAIRES ---


def generer_numero_document(type_doc: str) -> str:
  """Génère un identifiant unique annuel.

  type_doc : 'DEV', 'PREST' ou 'FAC'
  """
  annee = datetime.now().strftime("%Y")
  prefixe = f"{type_doc}-{annee}-"

  conn = get_conn()
  cursor = conn.cursor()

  if type_doc == "DEV":
    table, colonne = "devis", "numero_devis"
  elif type_doc in ["PREST", "INT"]:
    table, colonne = "interventions", "numero_intervention"
  else:
    table, colonne = "factures", "numero_facture"

  try:
    cursor.execute(
        f"SELECT {colonne} FROM {table} WHERE {colonne} LIKE ? ORDER BY id DESC"
        " LIMIT 1",
        (f"{prefixe}%",),
    )
    row = cursor.fetchone()
    if row and row[0]:
      dernier_num = int(row[0].split("-")[-1])
      nouveau_num = dernier_num + 1
    else:
      nouveau_num = 1
  except Exception:
    nouveau_num = 1

  conn.close()
  return f"{prefixe}{nouveau_num:04d}"


def recuperer_parametres():
  """Retourne la configuration générale de l'entreprise."""
  conn = get_conn()
  row = conn.execute("SELECT * FROM parametres WHERE id = 1").fetchone()
  conn.close()
  return dict(row) if row else {}


def recuperer_tous_les_clients():
  """Retourne la liste complète des clients."""
  conn = get_conn()
  rows = conn.execute(
      "SELECT * FROM clients ORDER BY nom_societe ASC"
  ).fetchall()
  conn.close()
  return [dict(r) for r in rows]


def get_backup_path():
  """Récupère le chemin personnalisé de sauvegarde depuis la BDD."""
  try:
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT backup_folder_path FROM parametres WHERE id = 1"
    )
    row = cursor.fetchone()
    conn.close()
    return (
        row["backup_folder_path"]
        if row and row["backup_folder_path"]
        else "auto_backups"
    )
  except Exception:
    return "auto_backups"


def save_backup_path(path_str):
  """Enregistre le nouveau chemin de sauvegarde dans la BDD."""
  try:
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE parametres SET backup_folder_path = ? WHERE id = 1",
        (path_str,),
    )
    conn.commit()
    conn.close()
  except Exception as e:
    print(f"Erreur enregistrement backup_path : {e}")


if __name__ == "__main__":
  initialiser_bdd()
  print("✓ Base de données mise à jour avec succès !")