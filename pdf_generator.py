import os
import re
import platform
import subprocess
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
import database

def format_date_fr(date_str):
    """Convertit 'AAAA-MM-JJ' en 'JJ/MM/AAAA'."""
    if not date_str:
        return ""
    try:
        dt = datetime.strptime(str(date_str).strip(), "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    except ValueError:
        return date_str

def generer_pdf_devis(devis_id, output_path="devis_temp.pdf"):
    conn = database.get_conn()
    
    # 1. Chargement des données
    devis = conn.execute("SELECT * FROM devis WHERE id=?", (devis_id,)).fetchone()
    if not devis:
        conn.close()
        return None

    client = conn.execute("SELECT * FROM clients WHERE id=?", (devis['client_id'],)).fetchone()
    items = conn.execute("""
        SELECT di.*, p.designation, p.unite 
        FROM devis_items di
        JOIN prestations p ON di.prestation_id = p.id
        WHERE di.devis_id=?
    """, (devis_id,)).fetchall()
    
    params = database.recuperer_parametres()
    conn.close()

    # Formater les dates au format FR (JJ/MM/AAAA)
    date_creation_fr = format_date_fr(devis['date_creation'])
    date_validite_fr = format_date_fr(devis['date_validite'])
    date_exec_fr = format_date_fr(devis['date_prevue_execution'])

    # 2. Configuration du document PDF
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm
    )

    styles = getSampleStyleSheet()
    
    # Palette de couleurs
    COLOR_PRIMARY = colors.HexColor("#1e3a8a")     # Bleu marine
    COLOR_SECONDARY = colors.HexColor("#0284c7")   # Bleu vif
    COLOR_TEXT = colors.HexColor("#334155")        # Ardoise
    COLOR_BG_LIGHT = colors.HexColor("#f8fafc")    # Gris clair
    COLOR_BORDER = colors.HexColor("#e2e8f0")      # Bordure

    # Styles texte
    style_normal = ParagraphStyle('NormalStyle', parent=styles['Normal'], fontSize=9, leading=13, textColor=COLOR_TEXT)
    style_company = ParagraphStyle('CompanyStyle', parent=styles['Normal'], fontSize=9, leading=13, textColor=COLOR_TEXT)
    style_th = ParagraphStyle('THStyle', parent=styles['Normal'], fontSize=9, leading=12, textColor=colors.white, fontName="Helvetica-Bold")
    style_total_lbl = ParagraphStyle('TotLbl', parent=styles['Normal'], fontSize=9, leading=12, textColor=COLOR_TEXT, alignment=2)
    style_total_val = ParagraphStyle('TotVal', parent=styles['Normal'], fontSize=9, leading=12, textColor=COLOR_TEXT, alignment=2)
    style_ttc_val = ParagraphStyle('TTCVal', parent=styles['Normal'], fontSize=11, leading=14, textColor=COLOR_PRIMARY, fontName="Helvetica-Bold", alignment=2)

    elements = []

    # --- 1. EN-TÊTE AVEC LOGO & INFOS ENTREPRISE ---
    header_elements = []
    
    # Intégration du logo
    logo_path_bdd = params.get('logo_path', '')
    
    if logo_path_bdd:
        # Reconstitution du chemin absolu sur la machine courante
        if not os.path.isabs(logo_path_bdd):
            logo_path = os.path.abspath(logo_path_bdd)
        else:
            logo_path = logo_path_bdd

        if os.path.exists(logo_path) and os.path.getsize(logo_path) > 0:
            try:
                img = Image(logo_path, width=5.5*cm, height=2.5*cm, kind='proportional')
                img.hAlign = 'LEFT'
                header_elements.append(img)
                header_elements.append(Spacer(1, 0.3*cm))
                print(f"[PDF LOGO] ✓ Logo inséré depuis : {logo_path}")
            except Exception as e:
                print(f"[PDF LOGO] ❌ Erreur d'affichage : {e}")
        else:
            print(f"[PDF LOGO] ❌ Fichier introuvable sur le disque : {logo_path}")
    # Infos entreprise
    e_text = f"<b><font size='11' color='{COLOR_PRIMARY.hexval()}'>{params.get('nom_entreprise', 'Mon Entreprise')}</font></b><br/>"
    if params.get('adresse'): e_text += f"{params.get('adresse')}<br/>"
    if params.get('code_postal') or params.get('ville'): e_text += f"{params.get('code_postal', '')} {params.get('ville', '')}<br/>"
    if params.get('telephone'): e_text += f"Tél : {params.get('telephone')}<br/>"
    if params.get('email'): e_text += f"Email : {params.get('email')}<br/>"
    if params.get('siret'): e_text += f"SIRET : {params.get('siret')}"

    header_elements.append(Paragraph(e_text, style_company))

    # Titre du document & Numéro à droite
    doc_title_text = f"""
    <font color="{COLOR_PRIMARY.hexval()}" size="22"><b>DEVIS</b></font><br/>
    <font color="{COLOR_SECONDARY.hexval()}" size="12"><b>N° {devis['numero_devis']}</b></font><br/><br/>
    <b>Date d'émission :</b> {date_creation_fr}<br/>
    <b>Date de validité :</b> {date_validite_fr}<br/>
    """
    if date_exec_fr:
        doc_title_text += f"<b>Date d'intervention :</b> {date_exec_fr}<br/>"

    cell_right = Paragraph(doc_title_text, style_normal)

    top_table = Table([[header_elements, cell_right]], colWidths=[10*cm, 8*cm])
    top_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))
    elements.append(top_table)
    elements.append(Spacer(1, 0.4*cm))

    # Ligne de séparation colorée
    elements.append(HRFlowable(width="100%", thickness=1.5, color=COLOR_PRIMARY, spaceAfter=15, spaceBefore=0))

    # --- 2. DESTINATAIRE / CLIENT ---
    elements.append(Spacer(1, 0.3*cm))
    
    client_text = f"""
    <font size="9" color="{COLOR_PRIMARY.hexval()}"><b>DESTINATAIRE :</b></font><br/><br/>
    <font size="11" color="#0f172a"><b>{client['nom_societe']}</b></font><br/>
    """
    if client['contact']: client_text += f"À l'attention de : {client['contact']}<br/>"
    if client['adresse']: client_text += f"{client['adresse']}<br/>"
    if client['cp'] or client['ville']: client_text += f"{client['cp']} {client['ville']}<br/>"
    if client['siret'] and not client['est_particulier']: client_text += f"SIRET : {client['siret']}<br/>"

    client_table = Table([[Paragraph(client_text, style_normal)]], colWidths=[8.5*cm])
    client_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), COLOR_BG_LIGHT),
        ('BOX', (0,0), (-1,-1), 1, COLOR_BORDER),
        ('PADDING', (0,0), (-1,-1), 10),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))

    dest_row = Table([["", client_table]], colWidths=[9.5*cm, 8.5*cm])
    dest_row.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    elements.append(dest_row)
    elements.append(Spacer(1, 1.2*cm))

    # --- 3. TABLEAU DES PRESTATIONS ---
    table_data = [[
        Paragraph("<b>Désignation</b>", style_th),
        Paragraph("<b>Qté</b>", ParagraphStyle('THRight', parent=style_th, alignment=2)),
        Paragraph("<b>P.U. HT</b>", ParagraphStyle('THRight', parent=style_th, alignment=2)),
        Paragraph("<b>TVA</b>", ParagraphStyle('THRight', parent=style_th, alignment=2)),
        Paragraph("<b>Total HT</b>", ParagraphStyle('THRight', parent=style_th, alignment=2))
    ]]

    for idx, it in enumerate(items):
        tot_ligne_ht = it['quantite'] * it['prix_unitaire_ht']
        table_data.append([
            Paragraph(f"{it['designation']}", style_normal),
            Paragraph(f"{it['quantite']:.2f} {it['unite']}", ParagraphStyle('R', parent=style_normal, alignment=2)),
            Paragraph(f"{it['prix_unitaire_ht']:.2f} €", ParagraphStyle('R', parent=style_normal, alignment=2)),
            Paragraph(f"{it['taux_tva']:.1f} %", ParagraphStyle('R', parent=style_normal, alignment=2)),
            Paragraph(f"<b>{tot_ligne_ht:.2f} €</b>", ParagraphStyle('R', parent=style_normal, alignment=2))
        ])

    prest_table = Table(table_data, colWidths=[8*cm, 2.5*cm, 2.5*cm, 2*cm, 3*cm])
    t_style = [
        ('BACKGROUND', (0,0), (-1,0), COLOR_PRIMARY),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('TOPPADDING', (0,0), (-1,-1), 7),
        ('GRID', (0,0), (-1,-1), 0.5, COLOR_BORDER),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]
    
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            t_style.append(('BACKGROUND', (0, i), (-1, i), COLOR_BG_LIGHT))

    prest_table.setStyle(TableStyle(t_style))
    elements.append(prest_table)
    elements.append(Spacer(1, 0.6*cm))

    # --- 4. TOTAUX & REMARQUES ---
    remarque_text = f"<b>Remarques / Conditions :</b><br/>{devis['remarque']}" if devis['remarque'] else ""
    cell_remarque = Paragraph(remarque_text, style_normal)

    totaux_data = [
        [Paragraph("<b>Total HT :</b>", style_total_lbl), Paragraph(f"{devis['total_ht']:.2f} €", style_total_val)],
        [Paragraph("<b>Total TVA :</b>", style_total_lbl), Paragraph(f"{devis['total_tva']:.2f} €", style_total_val)],
        [Paragraph("<b>Total TTC :</b>", ParagraphStyle('TTCLbl', parent=style_total_lbl, fontName="Helvetica-Bold", fontSize=11, textColor=COLOR_PRIMARY)), 
         Paragraph(f"<b>{devis['total_ttc']:.2f} €</b>", style_ttc_val)]
    ]

    totaux_table = Table(totaux_data, colWidths=[3.5*cm, 3.5*cm])
    totaux_table.setStyle(TableStyle([
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('LINEABOVE', (0,2), (1,2), 1.5, COLOR_PRIMARY),
        ('BACKGROUND', (0,2), (1,2), COLOR_BG_LIGHT),
    ]))

    bottom_table = Table([[cell_remarque, totaux_table]], colWidths=[11*cm, 7*cm])
    bottom_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    elements.append(bottom_table)
    elements.append(Spacer(1, 0.8*cm))

    # --- 5. MENTION DE TVA & BON POUR ACCORD ---
    bottom_left_elements = []

    if params.get('tva_exoneree', 1) or client['sans_tva']:
        mention_tva = params.get('mention_tva_exoneree', 'TVA non applicable, art. 293 B du CGI')
        bottom_left_elements.append(Paragraph(f"<i><font color='#64748b'>{mention_tva}</font></i>", style_normal))
        bottom_left_elements.append(Spacer(1, 0.4*cm))

    accord_text = """
    <b>BON POUR ACCORD</b><br/>
    <font size="8" color="#64748b">Date, Nom, Signature et Cachet :</font><br/><br/><br/><br/><br/>
    """
    accord_table = Table([[Paragraph(accord_text, style_normal)]], colWidths=[8*cm])
    accord_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 0.8, COLOR_BORDER),
        ('BACKGROUND', (0,0), (-1,-1), COLOR_BG_LIGHT),
        ('PADDING', (0,0), (-1,-1), 8),
    ]))
    
    bottom_left_elements.append(accord_table)

    footer_block = Table([[bottom_left_elements, ""]], colWidths=[10*cm, 8*cm])
    footer_block.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'TOP')]))
    elements.append(footer_block)

    # Génération du PDF
    doc.build(elements)
    return output_path
def nettoyer_nom_dossier(nom):
    """Supprime les caractères spéciaux non autorisés dans les noms de dossiers Windows."""
    if not nom:
        return "Client_Inconnu"
    # Remplace les caractères interdits par un underscore
    nom_propre = re.sub(r'[\\/*?:"<>|]', "_", str(nom).strip())
    return nom_propre or "Client_Inconnu"

def obtenir_chemin_export(nom_client, type_doc="Devis"):
    r"""
    Génère l'arborescence : C:\FactureX\Export\NomClient\TypeDocument\
    et renvoie le chemin complet du dossier.
    """
    # Chemin racine de l'application (ex: C:\FactureX ou le dossier d'exécution)
    base_dir = os.getcwd()
    
    client_folder = nettoyer_nom_dossier(nom_client)
    doc_folder = "Devis" if "devis" in type_doc.lower() else "Factures"

    # Construction du chemin complet
    export_dir = os.path.join(base_dir, "Export", client_folder, doc_folder)
    
    # Création automatique des sous-dossiers s'ils n'existent pas
    os.makedirs(export_dir, exist_ok=True)
    
    return export_dir

def ouvrir_dossier_windows(chemin_dossier):
    """Ouvre l'explorateur de fichiers Windows directement sur le dossier cible."""
    try:
        if platform.system() == "Windows":
            os.startfile(chemin_dossier)
        elif platform.system() == "Darwin": # macOS
            subprocess.Popen(["open", chemin_dossier])
        else: # Linux
            subprocess.Popen(["xdg-open", chemin_dossier])
    except Exception as e:
        print(f"Impossible d'ouvrir le dossier : {e}")
