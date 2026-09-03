from datetime import datetime
import os
import shutil
import sys

# Le client Supabase et l'utilisateur connecté seront injectés depuis app.py
_supabase_client = None
_current_user_id = None

def init_database_supabase(supabase_client, user_id):
    global _supabase_client, _current_user_id
    _supabase_client = supabase_client
    _current_user_id = user_id
    print("✓ Connexion BDD Supabase initialisée pour l'utilisateur:", user_id)

def get_db():
    if not _supabase_client:
        raise Exception("Client Supabase non initialisé dans database.py")
    return _supabase_client
    
# --- AJOUTS POUR COMPATIBILITÉ AVEC LES UI ---
def get_client():
    return get_db()

def get_conn():
    return get_db()


# --- FONCTIONS UTILITAIRES ---

def generer_numero_document(type_doc: str) -> str:
    annee = datetime.now().strftime("%Y")
    prefixe = f"{type_doc}-{annee}-"
    db = get_db()

    # On cherche le dernier numéro pour cet utilisateur
    table = "devis" if type_doc == "DEV" else ("interventions" if type_doc in ["PREST", "INT"] else "factures")
    colonne = "numero_devis" if type_doc == "DEV" else ("numero_intervention" if type_doc in ["PREST", "INT"] else "numero_facture")

    try:
        response = db.table(table)\
            .select(colonne)\
            .eq("user_id", _current_user_id)\
            .like(colonne, f"{prefixe}%")\
            .order("id", desc=True)\
            .limit(1)\
            .execute()
        
        rows = response.data
        if rows and rows[0].get(colonne):
            dernier_num = int(rows[0][colonne].split("-")[-1])
            nouveau_num = dernier_num + 1
        else:
            nouveau_num = 1
    except Exception as e:
        print(f"Erreur génération numéro {type_doc}: {e}")
        nouveau_num = 1

    return f"{prefixe}{nouveau_num:04d}"


def recuperer_parametres():
    db = get_db()
    try:
        res = db.table("parametres").select("*").eq("user_id", _current_user_id).limit(1).execute()
        if res.data:
            return res.data[0]
    except Exception as e:
        print(f"Erreur recuperer_parametres: {e}")
    return {}


def recuperer_tous_les_clients():
    db = get_db()
    try:
        res = db.table("clients").select("*").eq("user_id", _current_user_id).order("nom_societe").execute()
        return res.data if res.data else []
    except Exception as e:
        print(f"Erreur recuperer_tous_les_clients: {e}")
        return []


def get_backup_path():
    params = recuperer_parametres()
    return params.get("backup_folder_path", "auto_backups")


def save_backup_path(path_str):
    db = get_db()
    try:
        db.table("parametres").update({"backup_folder_path": path_str}).eq("user_id", _current_user_id).execute()
    except Exception as e:
        print(f"Erreur enregistrement backup_path : {e}")


def verifier_progression_onboarding():
    """
    Détermine le niveau d'avancement de la configuration de l'application sur Supabase :
    - Niveau 1 : Entreprise non configurée (SIRET ou Nom vide)
    - Niveau 2 : Catalogue vide
    - Niveau 3 : Clients vide
    - Niveau 4 : Tout est OK
    """
    db = get_db()
    try:
        params = recuperer_parametres()
        nom = params.get("nom_entreprise", "").strip()
        siret = params.get("siret", "").strip()
        
        if not nom or not siret:
            return 1
            
        # Vérification du catalogue
        cat_res = db.table("prestations").select("id", count="exact").eq("user_id", _current_user_id).execute()
        if cat_res.count == 0:
            return 2
            
        # Vérification des clients
        cli_res = db.table("clients").select("id", count="exact").eq("user_id", _current_user_id).execute()
        if cli_res.count == 0:
            return 3
            
        return 4
    except Exception as e:
        print(f"Erreur verifier_progression_onboarding: {e}")
        return 1