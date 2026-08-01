import sqlite3
from datetime import datetime

DB_PATH = "facturex.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Maintenant correctement placé
    return conn

def initialiser_bdd():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON;")
    
    # --- Tables Principales ---
    cursor.execute('''CREATE TABLE IF NOT EXISTS clients (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nom_societe TEXT NOT NULL, contact TEXT, adresse TEXT,
                        cp TEXT, ville TEXT, pays TEXT, email TEXT, telephone TEXT,
                        siret TEXT, tva_intra TEXT, rcs TEXT, ape TEXT,
                        est_particulier BOOLEAN DEFAULT 0, sans_tva BOOLEAN DEFAULT 0,
                        recap_interventions BOOLEAN DEFAULT 0, multi_etab BOOLEAN DEFAULT 0)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS etablissements (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        client_id INTEGER NOT NULL, nom_site TEXT NOT NULL,
                        adresse TEXT, cp TEXT, ville TEXT, pays TEXT,
                        FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS prestations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        designation TEXT NOT NULL, 
                        prix_ht REAL NOT NULL, 
                        unite TEXT,
                        tva REAL DEFAULT 0.0)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS tarifs_personnalises (
                        client_id INTEGER, prestation_id INTEGER, prix REAL,
                        PRIMARY KEY (client_id, prestation_id),
                        FOREIGN KEY(client_id) REFERENCES clients(id) ON DELETE CASCADE,
                        FOREIGN KEY(prestation_id) REFERENCES prestations(id) ON DELETE CASCADE)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS interventions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    client_id INTEGER,
                    prestation_id INTEGER,
                    quantite REAL,
                    prix_final REAL DEFAULT 0.0,
                    date TEXT,
                    etat TEXT,
                    FOREIGN KEY(client_id) REFERENCES clients(id),
                    FOREIGN KEY(prestation_id) REFERENCES prestations(id))''')

    conn.commit()
    conn.close()
    initialiser_parametres()

def initialiser_parametres():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS entreprise (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            raison_sociale TEXT, adresse TEXT, code_postal TEXT, ville TEXT, pays TEXT,
            rcs TEXT, siret TEXT, ape TEXT,
            tva_exoneree INTEGER DEFAULT 0, num_tva TEXT, logo_path TEXT, mentions_legales TEXT
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO entreprise (id) VALUES (1)")
    conn.commit()
    conn.close()

# --- CRUD Entreprise ---
def sauvegarder_parametres(data):
    # 'data' est un dictionnaire. On extrait les valeurs dans l'ordre attendu :
    tuple_data = (
        data['raison_sociale'],
        data['adresse'],
        data['code_postal'],
        data['ville'],
        data['pays'],
        data['rcs'],
        data['siret'],
        data['ape'],
        data['tva_exoneree'],
        data['num_tva'],
        data['logo_path'],
        data['mentions_legales'],
        1 # Le WHERE id=1
    )
    
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE entreprise 
        SET raison_sociale=?, adresse=?, code_postal=?, ville=?, pays=?, rcs=?, siret=?, ape=?, tva_exoneree=?, num_tva=?, logo_path=?, mentions_legales=? 
        WHERE id=?
    """, tuple_data)
    conn.commit()
    conn.close()

def recuperer_parametres():
    conn = get_conn()
    data = conn.execute("SELECT * FROM entreprise WHERE id=1").fetchone()
    conn.close()
    return data

# --- CRUD Prestations ---
def ajouter_prestation(designation, prix_ht, unite, tva):
    conn = get_conn()
    conn.execute("INSERT INTO prestations (designation, prix_ht, unite, tva) VALUES (?, ?, ?, ?)", (designation, prix_ht, unite, tva))
    conn.commit()
    conn.close()

def modifier_prestation(id, designation, prix_ht, unite, tva):
    conn = get_conn()
    conn.execute("UPDATE prestations SET designation=?, prix_ht=?, unite=?, tva=? WHERE id=?", (designation, prix_ht, unite, tva, id))
    conn.commit()
    conn.close()

def supprimer_prestation(id):
    conn = get_conn()
    conn.execute("DELETE FROM prestations WHERE id=?", (id,))
    conn.commit()
    conn.close()

def recuperer_toutes_les_prestations():
    conn = get_conn()
    data = conn.execute("SELECT * FROM prestations").fetchall()
    conn.close()
    return data

# --- CRUD Clients ---
def ajouter_client(d):
    conn = get_conn()
    conn.execute("""INSERT INTO clients (nom_societe, contact, adresse, cp, ville, pays, email, telephone, 
                    siret, tva_intra, rcs, ape, est_particulier, sans_tva, recap_interventions, multi_etab)
                    VALUES (:nom_societe, :contact, :adresse, :cp, :ville, :pays, :email, :telephone, 
                    :siret, :tva_intra, :rcs, :ape, :est_particulier, :sans_tva, :recap_interventions, :multi_etab)""", d)
    conn.commit()
    conn.close()

def modifier_client(client_id, d):
    conn = get_conn()
    d['id'] = client_id
    conn.execute("""UPDATE clients SET nom_societe=:nom_societe, contact=:contact, adresse=:adresse, cp=:cp, 
                    ville=:ville, pays=:pays, email=:email, telephone=:telephone, siret=:siret, tva_intra=:tva_intra, 
                    rcs=:rcs, ape=:ape, est_particulier=:est_particulier, sans_tva=:sans_tva, 
                    recap_interventions=:recap_interventions, multi_etab=:multi_etab WHERE id=:id""", d)
    conn.commit()
    conn.close()

def supprimer_client(client_id):
    try:
        conn = get_conn()
        conn.execute("DELETE FROM clients WHERE id=?", (client_id,))
        conn.commit()
        conn.close()
        return True, "Client supprimé."
    except Exception as e:
        return False, str(e)

def recuperer_tous_les_clients():
    conn = get_conn()
    # Utilise des AS pour renommer les colonnes à la volée
    query = """SELECT *, 
               multi_etab AS gere_multi_sites, 
               recap_interventions AS recap_presta 
               FROM clients"""
    data = conn.execute(query).fetchall()
    conn.close()
    return data

def recuperer_client_par_id(client_id):
    conn = get_conn()
    data = conn.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
    conn.close()
    return data

# --- CRUD Établissements & Prestations ---
def recuperer_etablissements_par_client(client_id):
    conn = get_conn()
    data = conn.execute("SELECT * FROM etablissements WHERE client_id=?", (client_id,)).fetchall()
    conn.close()
    return data

def recuperer_tarifs_client(client_id):
    conn = get_conn()
    data = conn.execute("SELECT * FROM tarifs_personnalises WHERE client_id=?", (client_id,)).fetchall()
    conn.close()
    return data

def sauvegarder_tarif_client(client_id, prestation_id, prix):
    conn = get_conn()
    conn.execute("INSERT OR REPLACE INTO tarifs_personnalises (client_id, prestation_id, prix) VALUES (?, ?, ?)", (client_id, prestation_id, prix))
    conn.commit()
    conn.close()

def supprimer_tarif_client(client_id, prestation_id):
    conn = get_conn()
    conn.execute("DELETE FROM tarifs_personnalises WHERE client_id=? AND prestation_id=?", (client_id, prestation_id))
    conn.commit()
    conn.close()

def ajouter_intervention(d):
    try:
        conn = get_conn()
        cursor = conn.cursor()
        
        # 1. Récupérer le tarif prioritaire pour ce client/cette prestation
        # On regarde dans tarifs_personnalises, sinon on prend le prix_ht de prestations
        query_tarif = """
            SELECT COALESCE(tp.prix, p.prix_ht) as prix_final
            FROM prestations p
            LEFT JOIN tarifs_personnalises tp ON p.id = tp.prestation_id 
                                              AND tp.client_id = :client_id
            WHERE p.id = :prestation_id
        """
        cursor.execute(query_tarif, {'client_id': d['client_id'], 'prestation_id': d['prestation_id']})
        result = cursor.fetchone()
        
        # On récupère le prix, sinon 0.0 par sécurité
        prix_final = result[0] if result else 0.0
        
        # 2. Insertion avec le prix_final calculé
        query = """INSERT INTO interventions 
                    (client_id, prestation_id, quantite, prix_final, date, heure_debut, heure_fin, etat)
                    VALUES (:client_id, :prestation_id, :quantite, :prix_final, :date, :heure_debut, :heure_fin, :etat)"""
        
        # On ajoute la valeur calculée dans le dictionnaire pour l'insertion
        d['prix_final'] = prix_final
        
        cursor.execute(query, d)
        id_genere = cursor.lastrowid
        
        conn.commit()
        conn.close()
        return id_genere
        
    except Exception as e:
        print(f"ERREUR BDD lors de l'ajout : {e}")
        return None
    
def recuperer_suivi_prestations():
    conn = get_conn()
    # Ajout de heure_debut et heure_fin dans le SELECT
    query = """
        SELECT i.id, c.nom_societe, p.designation, i.quantite, 
               i.date, i.heure_debut, i.heure_fin, i.etat, i.prix_final
        FROM interventions i
        JOIN clients c ON i.client_id = c.id
        JOIN prestations p ON i.prestation_id = p.id
               LEFT JOIN tarifs_personnalises tp ON i.client_id = tp.client_id 
                                                 AND i.prestation_id = tp.prestation_id"""
    data = conn.execute(query).fetchall()
    conn.close()
    return data

def recuperer_id_client_par_nom(nom_societe):
    conn = get_conn()
    # On utilise row_factory ici aussi, donc on accède par ['id']
    res = conn.execute("SELECT id FROM clients WHERE nom_societe=?", (nom_societe,)).fetchone()
    conn.close()
    return res['id'] if res else None

def recuperer_id_prestation_par_nom(designation):
    conn = get_conn()
    res = conn.execute("SELECT id FROM prestations WHERE designation=?", (designation,)).fetchone()
    conn.close()
    return res['id'] if res else None

def recuperer_toutes_les_interventions():
    conn = get_conn()
    # Jointures pour avoir le nom du client et de la presta en un seul objet Row
    query = """
        SELECT i.*, c.nom_societe, p.designation 
        FROM interventions i
        JOIN clients c ON i.client_id = c.id
        JOIN prestations p ON i.prestation_id = p.id
    """
    data = conn.execute(query).fetchall()
    conn.close()
    return data

def supprimer_intervention(intervention_id):
    """Supprime une intervention de la base de données en fonction de son ID."""
    try:
        conn = get_conn()
        query = "DELETE FROM interventions WHERE id = ?"
        conn.execute(query, (intervention_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"ERREUR BDD lors de la suppression : {e}")
        return False

def modifier_intervention(d):
    """Met à jour une intervention existante dans la base de données."""
    try:
        conn = get_conn()
        query = """UPDATE interventions SET 
                    client_id = :client_id, 
                    prestation_id = :prestation_id, 
                    quantite = :quantite, 
                    date = :date, 
                    heure_debut = :heure_debut, 
                    heure_fin = :heure_fin, 
                    etat = :etat 
                   WHERE id = :id"""
        conn.execute(query, d)
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"ERREUR BDD lors de la modification : {e}")
        return False

def recuperer_intervention_par_id(intervention_id):
    """Récupère toutes les infos d'une intervention pour pré-remplir le formulaire."""
    conn = get_conn()
    query = "SELECT * FROM interventions WHERE id = ?"
    cursor = conn.execute(query, (intervention_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def recuperer_nom_client_par_id(client_id):
    conn = get_conn()
    res = conn.execute("SELECT nom_societe FROM clients WHERE id = ?", (client_id,)).fetchone()
    conn.close()
    return res[0] if res else ""

def recuperer_nom_prestation_par_id(presta_id):
    conn = get_conn()
    res = conn.execute("SELECT designation FROM prestations WHERE id = ?", (presta_id,)).fetchone()
    conn.close()
    return res[0] if res else ""

def transformer_devis_en_prestation(id_intervention, date_c, h_debut, h_fin):
    # 1. Convertir la date choisie en objet date
    date_choisie = datetime.strptime(date_c, "%Y-%m-%d").date()
    date_aujourdhui = datetime.now().date()
    
    # 2. Logique de statut : 
    # Si la date est aujourd'hui ou dans le passé, on considère que c'est "Réalisée"
    # Sinon, c'est "En attente"
    nouveau_statut = "Réalisée" if date_choisie <= date_aujourdhui else "En attente"
    
    conn = get_conn()
    try:
        conn.execute("""
            UPDATE prestations 
            SET date_presta=?, heure_debut=?, heure_fin=?, etat=? 
            WHERE id=?
        """, (date_c, h_debut, h_fin, nouveau_statut, id_intervention))
        conn.commit()
        return True
    except Exception as e:
        print(f"Erreur SQL lors de la transformation : {e}")
        return False
    finally:
        conn.close()
        
def recuperer_prestations_actives_par_client(client_id):
    conn = get_conn()
    cursor = conn.cursor()
    # On cherche les prestations qui ont un tarif défini pour ce client
    query = """SELECT p.designation 
               FROM prestations p
               JOIN tarifs_personnalises tp ON p.id = tp.prestation_id
               WHERE tp.client_id = :client_id"""
    cursor.execute(query, {'client_id': client_id})
    prestations = [row[0] for row in cursor.fetchall()]
    conn.close()
    return prestations

def mise_a_jour_prix_historique():
    conn = get_conn()
    cursor = conn.cursor()
    
    # 1. On récupère toutes les interventions ayant un prix_final à 0 ou NULL
    cursor.execute("SELECT id, client_id, prestation_id FROM interventions WHERE prix_final IS NULL OR prix_final = 0")
    interventions_a_corriger = cursor.fetchall()
    
    for row in interventions_a_corriger:
        intervention_id, client_id, presta_id = row
        
        # 2. On calcule le prix correct selon la logique prioritaire
        query = """SELECT COALESCE(tp.prix, p.prix_ht) 
                   FROM prestations p
                   LEFT JOIN tarifs_personnalises tp ON p.id = tp.prestation_id 
                                                     AND tp.client_id = :client_id
                   WHERE p.id = :prestation_id"""
        
        cursor.execute(query, {'client_id': client_id, 'prestation_id': presta_id})
        prix = cursor.fetchone()[0]
        
        # 3. On met à jour l'intervention
        cursor.execute("UPDATE interventions SET prix_final = ? WHERE id = ?", (prix, intervention_id))
    
    conn.commit()
    conn.close()
    print("Mise à jour des prix historiques terminée.")
