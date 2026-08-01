import sqlite3
from datetime import date, datetime

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
                        etablissement_id INTEGER NULLABLE,
                        prestation_id INTEGER,
                        quantite REAL,
                        prix_final REAL DEFAULT 0.0,
                        date TEXT,
                        heure_debut TEXT,     
                        heure_fin TEXT,        
                        etat TEXT,
                        numero_devis TEXT,
                        commentaire TEXT,
                        facture_id INTEGER,
                        statut_paiement TEXT DEFAULT 'Non facturé',
                        FOREIGN KEY(client_id) REFERENCES clients(id),
                        FOREIGN KEY(prestation_id) REFERENCES prestations(id))''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS factures (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        numero_facture TEXT UNIQUE NOT NULL, -- ex: FAC-2026-0001
                        client_id INTEGER,
                        date_creation DATE,
                        date_paiement DATE,
                        statut TEXT DEFAULT 'En attente', -- 'En attente', 'Payé'
                        total_ttc REAL,
                        recap_genere BOOLEAN DEFAULT 0,
                        FOREIGN KEY(client_id) REFERENCES clients(id))''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS facture_items (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        facture_id INTEGER,
                        prestation_id INTEGER,
                        FOREIGN KEY(facture_id) REFERENCES factures(id),
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
    # On force sqlite3 à nous rendre un dictionnaire pur
    conn.row_factory = sqlite3.Row 
    cursor = conn.execute("SELECT * FROM entreprise WHERE id=1")
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row) # <--- C'est ici que tu transformes l'objet Row en dict
    return {}

# --- CRUD Prestations ---
def ajouter_prestation(designation, prix_ht, unite, tva_manuelle=None):
    conn = get_conn()
    cursor = conn.cursor()
    
    # 1. Vérifier si l'option "Non assujetti" est activée dans tes paramètres
    # (Supposons que tu as une table 'parametres' ou une logique équivalente)
    cursor.execute("SELECT tva_exoneree FROM entreprise WHERE id = 1")
    param = cursor.fetchone()
    
    # 2. Logique : si sans_tva est vrai, on force 0.0, sinon on prend la tva passée
    if param and param[0] == 1:
        tva_finale = 0.0
    else:
        tva_finale = tva_manuelle if tva_manuelle is not None else 20.0 # 20% par défaut
        
    cursor.execute("INSERT INTO prestations (designation, prix_ht, unite, tva) VALUES (?, ?, ?, ?)", 
                   (designation, prix_ht, unite, tva_finale))
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

def ajouter_etablissement(client_id, nom_site, adresse, cp, ville, pays):
    conn = get_conn()
    cursor = conn.cursor()
    query = """INSERT INTO etablissements (client_id, nom_site, adresse, cp, ville, pays)
               VALUES (?, ?, ?, ?, ?, ?)"""
    cursor.execute(query, (client_id, nom_site, adresse, cp, ville, pays))
    conn.commit()
    conn.close()

def recuperer_infos_client(client_id):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT nom_societe, contact, adresse, cp, ville, est_particulier, recap_interventions 
        FROM clients WHERE id = ?
    """, (client_id,))
    row = cursor.fetchone()
    if row:
        return {
            'nom': row[0],
            'contact': row[1],
            'adresse': row[2],
            'cp': row[3],
            'ville': row[4],
            'est_particulier': row[5],
            'recap_interventions': row[6] # Ajout de la clé dans le dictionnaire
        }
    return None

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

def ajouter_intervention(data):
    conn = get_conn()
    cursor = conn.cursor()
    # Utilisation de NULL si la clé n'est pas présente dans le dictionnaire
    query = """
        INSERT INTO interventions (
            client_id, prestation_id, quantite, prix_final, date, 
            heure_debut, heure_fin, etat, commentaire, etablissement_id, numero_devis
        ) VALUES (
            :client_id, :prestation_id, :quantite, :prix_final, :date, 
            :heure_debut, :heure_fin, :etat, :commentaire, :etablissement_id, :numero_devis
        )
    """
    try:
        # Si 'numero_devis' n'est pas dans 'data', on ajoute None manuellement
        if 'numero_devis' not in data:
            data['numero_devis'] = None
            
        cursor.execute(query, data)
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        print(f"Erreur insertion BDD : {e}")
        return None
    
def recuperer_suivi_prestations():
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    # On ajoute LEFT JOIN etablissements et on récupère le commentaire
    query = """
        SELECT i.id, c.nom_societe, e.nom_site, p.designation, i.quantite, 
               i.date, i.heure_debut, i.heure_fin, i.statut_paiement as etat, i.prix_final, i.commentaire
        FROM interventions i
        JOIN clients c ON i.client_id = c.id
        LEFT JOIN etablissements e ON i.etablissement_id = e.id
        JOIN prestations p ON i.prestation_id = p.id
        ORDER BY i.id ASC
    """
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
    try:
        conn = get_conn()
        query = """UPDATE interventions SET 
                    client_id = :client_id, 
                    prestation_id = :prestation_id, 
                    quantite = :quantite, 
                    prix_final = :prix_final,  # <--- AJOUTE CETTE LIGNE
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
        print(f"ERREUR BDD : {e}")
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

def get_tarif_unitaire(client_id, prestation_id):
    conn = get_conn()
    query = """
        SELECT COALESCE(tp.prix, p.prix_ht) as prix_unitaire 
        FROM prestations p
        LEFT JOIN tarifs_personnalises tp ON p.id = tp.prestation_id AND tp.client_id = ?
        WHERE p.id = ?
    """
    row = conn.execute(query, (client_id, prestation_id)).fetchone()
    conn.close()
    return float(row['prix_unitaire']) if row else 0.0

def transformer_devis_en_prestation(id_intervention, date_c, h_debut, h_fin, commentaire):
    from datetime import datetime as dt
    
    # Récupération des infos de base
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    # On récupère tout ce dont on a besoin en une seule fois
    intervention = conn.execute("SELECT client_id, prestation_id FROM interventions WHERE id=?", (id_intervention,)).fetchone()
    conn.close()
    
    if not intervention: return False

    # Calcul durée
    t1 = dt.strptime(h_debut, "%H:%M")
    t2 = dt.strptime(h_fin, "%H:%M")
    duree = (t2 - t1).total_seconds() / 3600
    
    # CALCUL FRAIS : On va chercher le prix unitaire actuel (c'est lui qui prime)
    prix_unitaire = get_tarif_unitaire(intervention['client_id'], intervention['prestation_id'])
    nouveau_prix = round(duree * prix_unitaire, 2)
    
    # Mise à jour
    conn = get_conn()
    conn.execute("""
        UPDATE interventions 
        SET date=?, heure_debut=?, heure_fin=?, quantite=?, prix_final=?, etat=?, commentaire=? 
        WHERE id=?
    """, (date_c, h_debut, h_fin, round(duree, 2), nouveau_prix, "Réalisée", commentaire, id_intervention))
    conn.commit()
    conn.close()
    return True
        
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

def generer_numero_devis():
    mois_actuel = datetime.now().strftime("%Y%m") # Ex: 202607
    conn = get_conn()
    cursor = conn.cursor()
    
    # On cherche le dernier numéro pour ce mois-ci
    # On filtre sur le format "DEV-202607-%"
    pattern = f"DEV-{mois_actuel}-%"
    cursor.execute("""SELECT numero_devis FROM interventions 
                      WHERE numero_devis LIKE ? 
                      ORDER BY numero_devis DESC LIMIT 1""", (pattern,))
    dernier = cursor.fetchone()
    
    if dernier:
        # On extrait la partie après le dernier '-'
        sequence = int(dernier[0].split('-')[2]) + 1
    else:
        sequence = 1
        
    return f"DEV-{mois_actuel}-{sequence:02d}"

def recuperer_prix_intervention(id_intervention):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT prix_final FROM interventions WHERE id = ?", (id_intervention,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else 0.0

def recuperer_numero_devis(id_intervention):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT numero_devis FROM interventions WHERE id = ?", (id_intervention,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else "DEVIS-INCONNU"

def recuperer_donnees_recap(client_id, date_debut, date_fin):
    conn = get_conn()
    conn.row_factory = sqlite3.Row # Très pratique pour accéder par nom de colonne
    cursor = conn.cursor()
    
    query = """SELECT i.date, i.heure_debut, i.heure_fin, i.commentaire, 
                      p.designation, e.nom_site 
               FROM interventions i
               LEFT JOIN prestations p ON i.prestation_id = p.id
               LEFT JOIN etablissements e ON i.etablissement_id = e.id
               WHERE i.client_id = ? AND i.date BETWEEN ? AND ?
               ORDER BY i.date ASC"""
               
    cursor.execute(query, (client_id, date_debut, date_fin))
    resultats = cursor.fetchall()
    conn.close()
    return resultats

def obtenir_prochain_numero_facture():
    cursor.execute("SELECT MAX(id) FROM factures")
    max_id = cursor.fetchone()[0] or 0
    return f"FAC-{date.today().year}-{max_id + 1:04d}"

def creer_facture_et_items(client_id, list_prestations_ids):
    conn = get_conn()
    cursor = conn.cursor()
    
    try:
        # 1. Générer le numéro de facture (Format: FAC-YYYY-XXXX)
        # On récupère le nombre de factures existantes pour l'année en cours
        annee = datetime.now().year
        cursor.execute("SELECT COUNT(*) FROM factures WHERE numero_facture LIKE ?", (f'FAC-{annee}-%',))
        count = cursor.fetchone()[0]
        numero = f"FAC-{annee}-{count + 1:04d}"
        
        # 2. Calculer le total TTC (en sommant les prix des prestations sélectionnées)
        placeholders = ','.join(['?'] * len(list_prestations_ids))
        cursor.execute(f"SELECT SUM(prix_final) FROM interventions WHERE id IN ({placeholders})", list_prestations_ids)
        total = cursor.fetchone()[0] or 0.0
        
        # 3. Créer la facture
        cursor.execute('''INSERT INTO factures (numero_facture, client_id, date_creation, total_ttc, statut) 
                          VALUES (?, ?, ?, ?, ?)''', 
                       (numero, client_id, date.today(), total, 'En attente'))
        
        facture_id = cursor.lastrowid
        
        # 4. Lier les prestations à la facture et mettre à jour leur statut
        for p_id in list_prestations_ids:
            cursor.execute("INSERT INTO facture_items (facture_id, prestation_id) VALUES (?, ?)", (facture_id, p_id))
            cursor.execute("UPDATE interventions SET facture_id = ?, statut_paiement = 'Facturé' WHERE id = ?", (facture_id, p_id))
            print(f"DEBUG: Nombre de lignes impactées par le UPDATE -> {cursor.rowcount}")
        print(f"DEBUG: {len(list_prestations_ids)} prestations marquées 'Facturé' pour facture {facture_id}")
        conn.commit()
        return numero, total # On retourne ces infos pour le PDF
    
    except Exception as e:
        conn.rollback()
        print(f"Erreur lors de la création de la facture : {e}")
        return None, 0.0
    finally:
        conn.close()


def recuperer_toutes_prestations_non_facturees():
    conn = get_conn()
    cursor = conn.cursor()
    # On sélectionne les interventions non facturées
    cursor.execute('''SELECT i.id, i.client_id, c.nom_societe, i.date, p.designation, i.prix_final 
                      FROM interventions i
                      JOIN clients c ON i.client_id = c.id
                      JOIN prestations p ON i.prestation_id = p.id
                      WHERE i.statut_paiement = 'Non facturé'
                      ORDER BY i.id ASC''')
    rows = cursor.fetchall()
    conn.close()
    return rows

def recuperer_details_recap(numero_facture):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute('''SELECT i.date, e.nom_site, p.designation, i.heure_debut, i.heure_fin 
                      FROM facture_items fi
                      JOIN interventions i ON fi.prestation_id = i.id
                      JOIN prestations p ON i.prestation_id = p.id
                      LEFT JOIN etablissements e ON i.etablissement_id = e.id
                      WHERE fi.facture_id = (SELECT id FROM factures WHERE numero_facture = ?)
                      ORDER BY i.id ASC''', (numero_facture,))
    return cursor.fetchall()

def recuperer_prestations_realisees_par_client(client_id):
    conn = get_conn()
    cursor = conn.cursor()
    # On sélectionne les interventions liées au client, non encore facturées
    # Assure-toi que les noms de colonnes correspondent à ta table 'interventions'
    cursor.execute('''SELECT i.id, i.date, p.designation, i.quantite, i.prix_final, i.prix_final
                      FROM interventions i
                      JOIN prestations p ON i.prestation_id = p.id
                      WHERE i.client_id = ? AND i.statut_paiement = 'Non facturé'
                      ORDER BY i.id ASC''', (client_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def recuperer_lignes_facture(numero_facture):
    conn = get_conn()
    cursor = conn.cursor()
    # Récupère les détails des prestations pour le PDF
    cursor.execute('''SELECT p.designation, i.quantite, i.prix_final
                      FROM facture_items fi
                      JOIN interventions i ON fi.prestation_id = i.id
                      JOIN prestations p ON i.prestation_id = p.id
                      WHERE fi.facture_id = (SELECT id FROM factures WHERE numero_facture = ?)''', (numero_facture,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def passer_au_statut_facture(ids):
    conn = get_conn()
    cursor = conn.cursor()
    # Utilisation de executemany pour être efficace
    cursor.execute(f"UPDATE interventions SET statut_paiement = 'Facturé' WHERE id IN ({','.join(['?']*len(ids))})", ids)
    conn.commit()
    conn.close()

def recuperer_historique_factures():
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    query = """
        SELECT f.numero_facture, c.nom_societe, f.date_creation, 
               f.total_ttc, f.statut, f.date_paiement
        FROM factures f
        JOIN clients c ON f.client_id = c.id
        ORDER BY f.numero_facture ASC
    """
    return conn.execute(query).fetchall()

def recuperer_interventions_par_facture(numero_facture):
    conn = get_conn()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # On fait le lien via la table 'factures' et la table 'facture_items'
    query = """
        SELECT i.date, i.heure_debut, i.heure_fin, i.commentaire, i.prix_final,
               p.designation, e.nom_site 
        FROM interventions i
        JOIN facture_items fi ON i.id = fi.prestation_id
        JOIN factures f ON fi.facture_id = f.id
        JOIN prestations p ON i.prestation_id = p.id
        JOIN etablissements e ON i.etablissement_id = e.id
        WHERE f.numero_facture = ?
        ORDER BY i.date ASC
    """
    print(f"DEBUG SQL: Recherche interventions liées à la facture : {numero_facture}")
    cursor.execute(query, (numero_facture,))
    resultats = cursor.fetchall()
    print(f"DEBUG SQL: {len(resultats)} interventions trouvées.")
    for r in resultats:
        print(f" - Intervention trouvée : Date={r['date']}, Site={r['nom_site']}")
    conn.close()
    return resultats