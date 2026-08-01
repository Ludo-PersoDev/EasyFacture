from fpdf import FPDF
import os

def preparer_dossier_export(nom_client, type_doc):
    # Nettoyer le nom pour éviter les erreurs de chemin Windows
    nom_propre = "".join([c for c in nom_client if c.isalnum() or c in (' ', '_', '-')]).strip()
    dossier = os.path.join(r"C:\FacturEx\Exports", nom_propre, type_doc)
    if not os.path.exists(dossier):
        os.makedirs(dossier, exist_ok=True)
    return dossier

def creer_pdf_devis(nom_client, designation, quantite, prix_ht, id_devis):
    # Sécurisation du nom pour éviter les erreurs de chemin Windows
    nom_propre = "".join([c for c in nom_client if c.isalnum() or c in (' ', '_', '-')]).strip()
    
    print(f"DEBUG: Tentative de création PDF pour {nom_propre}, Devis N°{id_devis}")
    
    try:
        prix = float(prix_ht)
    except (ValueError, TypeError):
        prix = 0.0

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt=f"Devis N°{id_devis}", ln=True, align='C')
    
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Client : {nom_client}", ln=True)
    pdf.ln(10)

    if not nom_client or not id_devis:
        print("ERREUR: nom_client ou id_devis est vide !")
        return None

    # Détails
    pdf.cell(100, 10, f"Prestation : {designation}", border=1)
    pdf.cell(30, 10, f"Qté : {quantite}", border=1)
    pdf.cell(40, 10, f"{prix:.2f} EUR", border=1, ln=True)
    
    # Préparation du chemin avec le nom nettoyé
    dossier = preparer_dossier_export(nom_propre, "Devis")
    filename = os.path.join(dossier, f"Devis_{id_devis}_{nom_propre}.pdf")
    
    try:
        pdf.output(filename)
        print(f"DEBUG: Fichier généré avec succès à : {filename}")
        return filename
    except Exception as e:
        print(f"ERREUR FATALE PDF: {e}")
        return None

def creer_pdf_facture(nom_client, prestations, total_ht, num_facture):
    """Génère le PDF d'une facture."""
    # ... (ton code de construction PDF ici) ...
    
    # Sauvegarde
    dossier = preparer_dossier_export(nom_client, "Factures")
    filename = os.path.join(dossier, f"Facture_{num_facture}_{nom_client}.pdf")
    pdf.output(filename)
    return filename

def creer_pdf_recap(nom_client, prestations):
    """Génère le récapitulatif d'interventions."""
    # ... (construction PDF) ...
    
    dossier = preparer_dossier_export(nom_client, "Recaps")
    filename = os.path.join(dossier, f"Recap_{nom_client}.pdf")
    pdf.output(filename)
    return filename
