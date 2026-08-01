import fpdf
from fpdf import FPDF
import os
import database
from collections import defaultdict
from datetime import datetime, timedelta
import locale


try:
    locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
except:
    pass
print(f"FICHIER FPDF UTILISÉ : {fpdf.__file__}")
def preparer_dossier_export(nom_client, type_doc):
    # Nettoyer le nom pour éviter les erreurs de chemin Windows
    nom_propre = "".join([c for c in nom_client if c.isalnum() or c in (' ', '_', '-')]).strip()
    dossier = os.path.join(r"C:\FacturEx\Exports", nom_propre, type_doc)
    if not os.path.exists(dossier):
        os.makedirs(dossier, exist_ok=True)
    return dossier

def creer_pdf_devis(client_id, nom_client, designation, quantite, prix_ht, id_devis):
    # 1. Préparation des données
    couleur_primaire = (41, 128, 185)
    numero_devis_formate = database.recuperer_numero_devis(id_devis)
    if numero_devis_formate == "DEVIS-INCONNU": return None
    params = database.recuperer_parametres()
    nom_propre = "".join([c for c in nom_client if c.isalnum() or c in (' ', '_', '-')]).strip()
    infos_client = database.recuperer_infos_client(client_id)
    
    pdf = FPDF()
    pdf.add_page()

    chemin_logo = r"C:\FacturEx\assets\logo.png"
    if os.path.exists(chemin_logo):
        pdf.image(chemin_logo, 10, 8, 60)
    
    # 2. HEADER
    pdf.set_left_margin(70)
    pdf.set_xy(70, 10)
    pdf.set_text_color(*couleur_primaire)
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(100, 7, params['raison_sociale'], ln=0)
    pdf.set_font("Helvetica", 'B', 20)
    pdf.cell(0, 10, "DEVIS", ln=1, align='R')

    pdf.set_font("Helvetica", size=10)
    pdf.cell(100, 5, f"{params['adresse']}", ln=0)
    pdf.cell(0, 5, f"N° : {numero_devis_formate}", ln=1, align='R')
    pdf.cell(100, 5, f"{params['code_postal']} {params['ville']}", ln=1)
    pdf.cell(100, 5, f"SIRET : {params['siret']}", ln=1)
    pdf.set_left_margin(10)
    pdf.ln(10)

    # 3. BLOC CLIENT (Correction indentation ici)
    if infos_client:
        bloc_adresse = (
            f"{infos_client['nom']}\n"
            f"À l'attention de : {infos_client['contact']}\n"
            f"{infos_client['adresse']}\n"
            f"{infos_client['cp']} {infos_client['ville']}"
        )
    else:
        bloc_adresse = nom_client

    pdf.set_fill_color(230, 240, 250)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(100)
    pdf.cell(90, 8, "DESTINATAIRE", 1, 1, 'C', True)
    pdf.set_font("Helvetica", size=11)
    pdf.cell(100)
    pdf.multi_cell(90, 7, bloc_adresse, 1, 'L')
    pdf.ln(10)
    # 3. Tableau professionnel
    # Entêtes
    pdf.set_fill_color(230, 240, 250)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(80, 10, "Prestation", 1, 0, 'C', True)
    pdf.cell(30, 10, "Qté", 1, 0, 'C', True)
    pdf.cell(30, 10, "Prix Uni. HT", 1, 0, 'C', True) # Nouvelle colonne
    pdf.cell(40, 10, "Total HT", 1, 1, 'C', True)
    
    # Contenu
    pdf.set_font("Helvetica", size=12)
    pdf.cell(80, 10, str(designation), 1)
    pdf.cell(30, 10, f"{float(quantite):.2f}", 1, 0, 'C')
    pdf.cell(30, 10, f"{float(prix_ht/quantite):.2f} EUR", 1, 0, 'C') # Calcul : prix_ht / quantite
    pdf.cell(40, 10, f"{float(prix_ht):.2f} EUR", 1, 1, 'R')
    
    # 4. Total et Mentions
    pdf.ln(5)
    pdf.set_font("Helvetica", 'B', 12)
    # On laisse de l'espace vide à gauche (120mm) pour pousser le total à droite
    pdf.cell(110, 10, "", 0, 0) 
    pdf.cell(30, 10, "TOTAL HT", 1, 0, 'L', True)
    pdf.cell(40, 10, f"{float(prix_ht):.2f} EUR", 1, 1, 'R')
    
    # 5. PIED DE PAGE "PRO" (Signature + Mentions)
    pdf.set_y(-60)
    pdf.set_font("Helvetica", 'B', 10)
    pdf.cell(90, 10, "Bon pour accord (Date et Signature):", 0, 0)
   
    pdf.ln(20)
    pdf.set_font("Helvetica", 'I', 8)
    if params.get('tva_exoneree'):
        mention_tva = "TVA non applicable, art. 293 B du CGI."
    else:
        mention_tva = f"TVA intracommunautaire : {params.get('num_tva', 'Non renseigné')}"
    pdf.multi_cell(0, 4, f"{mention_tva}{params['mentions_legales']}\nCapital : {params.get('capital', 'N/A')} EUR | RCS : {params['rcs']}")

    # Préparation du chemin avec le nom nettoyé
    dossier = preparer_dossier_export(nom_client, "Devis")
    filename = os.path.join(dossier, f"Devis_{numero_devis_formate}_{nom_propre}.pdf")
    
    try:
        pdf.output(filename)
        print(f"DEBUG: Fichier généré avec succès à : {filename}")
        return filename
    except Exception as e:
        print(f"ERREUR FATALE PDF: {e}")
        return None

def creer_pdf_facture(client_id, numero_facture, total_ttc):
    # 1. Préparation des données
    couleur_primaire = (41, 128, 185)
    params = database.recuperer_parametres()
    infos_client = database.recuperer_infos_client(client_id)
    
    # Récupération des lignes de facture en base via le numéro de facture
    items = database.recuperer_lignes_facture(numero_facture) 
    
    nom_client = infos_client['nom']
    nom_propre = "".join([c for c in nom_client if c.isalnum() or c in (' ', '_', '-')]).strip()
    
    pdf = FPDF()
    pdf.add_page()

    # Logo
    chemin_logo = r"C:\FacturEx\assets\logo.png"
    if os.path.exists(chemin_logo):
        pdf.image(chemin_logo, 10, 8, 60)
    
    # 2. HEADER
    pdf.set_left_margin(70)
    pdf.set_xy(70, 10)
    pdf.set_text_color(*couleur_primaire)
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(100, 7, params['raison_sociale'], ln=0)
    pdf.set_font("Helvetica", 'B', 20)
    pdf.cell(0, 10, "FACTURE", ln=1, align='R')

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", size=10)
    pdf.cell(100, 5, f"{params['adresse']}", ln=0)
    pdf.cell(0, 5, f"N° : {numero_facture}", ln=1, align='R')
    pdf.cell(100, 5, f"{params['code_postal']} {params['ville']}", ln=1)
    pdf.cell(100, 5, f"SIRET : {params['siret']}", ln=1)
    pdf.set_left_margin(10)
    pdf.ln(10)

    # 3. BLOC CLIENT
    bloc_adresse = (
        f"{infos_client['nom']}\n"
        f"À l'attention de : {infos_client['contact']}\n"
        f"{infos_client['adresse']}\n"
        f"{infos_client['cp']} {infos_client['ville']}"
    )

    pdf.set_fill_color(230, 240, 250)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(100)
    pdf.cell(90, 8, "DESTINATAIRE", 1, 1, 'C', True)
    pdf.set_font("Helvetica", size=11)
    pdf.cell(100)
    pdf.multi_cell(90, 7, bloc_adresse, 1, 'L')
    pdf.ln(10)

    # 4. Tableau des prestations
    pdf.set_fill_color(230, 240, 250)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(100, 10, "Prestation", 1, 0, 'C', True)
    pdf.cell(30, 10, "Qté", 1, 0, 'C', True)
    pdf.cell(60, 10, "Total HT", 1, 1, 'C', True)
    
    pdf.set_font("Helvetica", size=12)
    for item in items:
        # item structure attendue: (designation, quantite, prix_final)
        pdf.cell(100, 10, str(item[0]), 1)
        pdf.cell(30, 10, f"{float(item[1]):.2f}", 1, 0, 'C')
        pdf.cell(60, 10, f"{float(item[2]):.2f} EUR", 1, 1, 'R')
    
    # 5. Total
    pdf.ln(5)
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(130, 10, "", 0, 0) 
    pdf.cell(30, 10, "TOTAL HT", 1, 0, 'L', True)
    pdf.cell(30, 10, f"{float(total_ttc):.2f} EUR", 1, 1, 'R')
    
    # 6. Pied de page
    pdf.set_y(-60)
    pdf.set_font("Helvetica", 'I', 8)
    mention_tva = "TVA non applicable, art. 293 B du CGI." if params.get('tva_exoneree') else f"TVA : {params.get('num_tva')}"
    pdf.multi_cell(0, 4, f"{mention_tva}\n{params['mentions_legales']}\nRCS : {params['rcs']}")

    # Export
    dossier = preparer_dossier_export(nom_client, "Factures")
    filename = os.path.join(dossier, f"Facture_{numero_facture}_{nom_propre}.pdf")
    pdf.output(filename)
    return filename

def creer_pdf_recap(client_id, numero_facture):
    data = database.recuperer_interventions_par_facture(numero_facture)
    if not data: return None

    sites = sorted(list(set(r['nom_site'] for r in data)))
    
    # 1 & 2. Calcul des semaines (logique inchangée)
    dates_intervs = [datetime.strptime(r['date'], '%Y-%m-%d') for r in data]
    debut_mois = datetime(min(dates_intervs).year, min(dates_intervs).month, 1)
    fin_mois = (datetime(debut_mois.year, debut_mois.month % 12 + 1, 1) - timedelta(days=1)) if debut_mois.month < 12 else datetime(debut_mois.year, 12, 31)
    semaines = []
    curr = debut_mois
    while curr <= fin_mois:
        lundi = curr if curr.weekday() == 0 else curr - timedelta(days=curr.weekday())
        dimanche = lundi + timedelta(days=6)
        lundi = max(lundi, debut_mois)
        dimanche = min(dimanche, fin_mois)
        cle = f"{lundi.strftime('%d/%m')} au {dimanche.strftime('%d/%m')}"
        if cle not in [s[0] for s in semaines]: semaines.append((cle, lundi, dimanche))
        curr = dimanche + timedelta(days=1)

    matrice = {s[0]: {site: [] for site in sites} for s in semaines}
    for row in data:
        d = datetime.strptime(row['date'], '%Y-%m-%d')
        for cle, l, dim in semaines:
            if l <= d <= dim:
                matrice[cle][row['nom_site']].append(row)
                break

    pdf = FPDF('L', 'mm', 'A4')
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, f"Récapitulatif - Facture {numero_facture}", ln=1, align='C')
    col_width = 170 / (len(sites) + 1)
    pdf.set_font("Helvetica", 'B', 8)
    pdf.cell(40, 10, "Semaines", 1)
    for site in sites: pdf.cell(col_width, 10, site, 1, 0, 'C')
    pdf.cell(30, 10, "Totaux", 1, 1, 'C')

    grand_total_heures, grand_total_prix, grand_total_seances = 0, 0, 0

    for cle, _, _ in semaines:
        max_int = max([len(matrice[cle][s]) for s in sites] + [1])
        h_ligne = max_int * 15
        x_debut_ligne, y_debut_ligne = pdf.get_x(), pdf.get_y()
        
        pdf.cell(40, h_ligne, f"Semaine du {cle}", 1)
        
        semaine_h, semaine_p, semaine_s = 0, 0, 0
        
        for site in sites:
            x, y = pdf.get_x(), pdf.get_y()
            intervs = matrice[cle][site]
            # Dessine le cadre de la cellule pour éviter les décalages
            pdf.cell(col_width, h_ligne, "", 1)
            
            for i, it in enumerate(intervs):
                d = datetime.strptime(it['date'], '%Y-%m-%d')
                # Ligne 1 : Date + Horaire
                txt_haut = f"{d.strftime('%d %B')} | {it['heure_debut']}-{it['heure_fin']}"
                # Ligne 2 : Prix + Commentaire
                comm = ""
                if 'commentaire' in it.keys() and it['commentaire']:
                    comm = f" | {it['commentaire']}"
                
                txt_bas = f"{it['prix_final']:.2f} EUR{comm}"
                
                pdf.set_xy(x, y + (i * 15))
                pdf.cell(col_width, 7.5, txt_haut, 0, 2, 'C')
                pdf.cell(col_width, 7.5, txt_bas, 0, 0, 'C')
                
                semaine_h += (datetime.strptime(it['heure_fin'], '%H:%M') - datetime.strptime(it['heure_debut'], '%H:%M')).seconds / 3600
                semaine_p += it['prix_final']
                semaine_s += 1
            
            pdf.set_xy(x + col_width, y)
            
        # 4. Totaux semaine (Agencement propre)
        x_tot, y_tot = pdf.get_x(), pdf.get_y()
        
        # Dessiner le cadre de la colonne Totaux
        pdf.cell(30, h_ligne, "", 1)
        
        # Positionner le texte pour les 3 lignes
        pdf.set_font("Helvetica", '', 7)
        pdf.set_xy(x_tot, y_tot + (h_ligne / 2) - 9) # Centrage vertical approximatif
        
        pdf.set_x(x_tot)
        pdf.cell(30, 6, f"{semaine_s} seanc.", 0, 2, 'C')
        pdf.set_x(x_tot)
        pdf.cell(30, 6, f"{semaine_h:.1f}h", 0, 2, 'C')
        pdf.set_x(x_tot)
        pdf.cell(30, 6, f"{semaine_p:.2f} EUR", 0, 0, 'C')
        
        # Retour au début de la ligne suivante
        pdf.set_xy(x_debut_ligne, y_debut_ligne + h_ligne)
        
        grand_total_heures += semaine_h
        grand_total_prix += semaine_p
        grand_total_seances += semaine_s

    pdf.set_font("Helvetica", 'B', 8)
    largeur_precedente = 40 + (len(sites) * col_width)
    x_total_gen, y_total_gen = pdf.get_x(), pdf.get_y()

    # On dessine une cellule de hauteur fixe 12 pour contenir le texte empilé
    pdf.cell(largeur_precedente, 12, "TOTAL GENERAL", 1, 0, 'R')
    pdf.cell(30, 12, "", 1) # Cadre vide pour les chiffres

    # Positionnement manuel précis pour éviter le débordement
    pdf.set_xy(x_total_gen + largeur_precedente, y_total_gen + 1)
    
    # Écriture ligne par ligne dans la colonne des totaux
    pdf.cell(30, 3.3, f"{grand_total_seances} seanc.", 0, 2, 'C') # Hauteur adaptée
    pdf.set_x(x_total_gen + largeur_precedente)
    pdf.cell(30, 3.3, f"{grand_total_heures:.1f}h", 0, 2, 'C')
    pdf.set_x(x_total_gen + largeur_precedente)
    pdf.cell(30, 3.3, f"{grand_total_prix:.2f} EUR", 0, 0, 'C')

    # ... (Sauvegarde identique)
    infos_client = database.recuperer_infos_client(client_id)
    nom_propre = "".join([c for c in infos_client['nom'] if c.isalnum() or c in (' ', '_', '-')]).strip()
    dossier = os.path.join(r"C:\FacturEx\Exports", nom_propre, "Recaps")
    os.makedirs(dossier, exist_ok=True)
    filename = os.path.join(dossier, f"Recap_{numero_facture}_{nom_propre}.pdf")
    pdf.output(filename)
    return filename

def preparer_donnees_recap(client_id):
    # 1. On récupère tes interventions brutes
    interventions = database.recuperer_interventions_pour_recap(client_id)
    
    recap_data = {}
    
    for row in interventions:
        date_obj = datetime.strptime(row['date'], '%Y-%m-%d')
        
        # Trouver le lundi de la semaine
        lundi = date_obj - timedelta(days=date_obj.weekday())
        semaine_key = lundi.strftime('%Y-%m-%d')
        
        if semaine_key not in recap_data:
            recap_data[semaine_key] = {"interventions": [], "total_heures": 0}
            
        # Calcul de la durée
        h_d = datetime.strptime(row['heure_debut'], '%H:%M')
        h_f = datetime.strptime(row['heure_fin'], '%H:%M')
        duree = (h_f - h_d).total_seconds() / 3600 # en heures décimales
        
        # Ajout des infos dans la liste de la semaine
        recap_data[semaine_key]["interventions"].append({
            "site": row['nom_site'],
            "date": row['date'],
            "presta": row['designation'],
            "horaire": f"{row['heure_debut']} à {row['heure_fin']}",
            "duree": duree,
            "comment": row['commentaire']
        })
        recap_data[semaine_key]["total_heures"] += duree
        
    return recap_data

def get_semaine_bornes(date_str):
    d = datetime.strptime(date_str, '%Y-%m-%d')
    # On force le premier jour du mois si la date est antérieure
    debut_mois = datetime(d.year, d.month, 1)
    # Calcul du lundi de la semaine en cours
    lundi = d - timedelta(days=d.weekday())
    # On ne laisse pas la date commencer avant le 1er du mois
    lundi = max(lundi, debut_mois)
    dimanche = lundi + timedelta(days=6)
    return f"Semaine {d.isocalendar()[1]}\n{lundi.strftime('%d/%m')} - {dimanche.strftime('%d/%m')}"