from datetime import datetime, timedelta
import os
import platform
import subprocess
import webbrowser
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
import database
import re


MOIS_FR = {
    1: "janvier", 2: "février", 3: "mars", 4: "avril",
    5: "mai", 6: "juin", 7: "juillet", 8: "août",
    9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre"
}


def format_date_fr(date_str):
    """Convertit 'AAAA-MM-JJ' en 'JJ/MM/AAAA'[cite: 4]."""
    if not date_str:
        return ""
    try:
        dt = datetime.strptime(str(date_str).strip(), "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    except ValueError:
        return date_str


def nettoyer_nom_dossier(nom):
    """Supprime les caractères spéciaux non autorisés dans les noms de dossiers Windows[cite: 4]."""
    if not nom:
        return "Client_Inconnu"
    nom_propre = re.sub(r"[\\/*?:\"<>|]", "_", str(nom).strip())
    return nom_propre or "Client_Inconnu"


def obtenir_chemin_export_facture(nom_client, numero_facture):
    """Génère l'arborescence : Export/NomClient/Factures/FAC-2026-XXXX.pdf[cite: 4]."""
    base_dir = os.getcwd()
    client_folder = nettoyer_nom_dossier(nom_client)
    export_dir = os.path.join(base_dir, "Export", client_folder, "Factures")
    os.makedirs(export_dir, exist_ok=True)
    return os.path.join(export_dir, f"{numero_facture}.pdf")


def obtenir_chemin_export_recap(nom_client, numero_facture=None):
    """
    Garantit et retourne le chemin d'exportation pour le récapitulatif du client[cite: 4].
    """
    client_folder = nettoyer_nom_dossier(nom_client)
    dossier_base = os.path.join(os.getcwd(), "Export", client_folder, "Recaps")
    os.makedirs(dossier_base, exist_ok=True)
    
    if numero_facture:
        filename = f"Recap_{numero_facture}.pdf"
    else:
        filename = f"Recap_{client_folder}.pdf"
        
    return os.path.join(dossier_base, filename)


def generer_pdf_facture(facture_id, output_path=None):
    """
    Aiguille vers la facture condensée ou détaillée selon le choix du client en base,
    et génère automatiquement le récapitulatif si 'recap_interventions' est à 1[cite: 4].
    """
    conn = database.get_conn()
    query = """
        SELECT c.modele_facture, c.recap_interventions, c.nom_societe, f.numero_facture
        FROM factures f 
        JOIN clients c ON f.client_id = c.id 
        WHERE f.id = ?
    """
    res = conn.execute(query, (facture_id,)).fetchone()
    conn.close()

    if not res:
        raise ValueError(f"Facture ID {facture_id} introuvable.")

    res_dict = dict(res)
    modele = res_dict.get('modele_facture', 'condense')
    recap_auto = res_dict.get('recap_interventions', 0)

    if modele == 'detaille':
        pdf_path = generer_pdf_facture_detaillee(facture_id, output_path)
    else:
        pdf_path = generer_pdf_facture_condensee(facture_id, output_path)

    if recap_auto == 1:
        try:
            generer_pdf_recap_facture(facture_id)
        except Exception as e:
            print(f"Erreur lors de la génération automatique du récapitulatif : {e}")

    return pdf_path


def generer_pdf_facture_condensee(facture_id, output_path=None):
    """Génère le document PDF d'une facture condensée par prestation et l'enregistre[cite: 4]."""
    conn = database.get_conn()

    query_facture = """
        SELECT f.*, 
               c.nom_societe, c.contact, c.adresse AS client_adresse, 
               c.cp AS client_cp, c.ville AS client_ville, c.siret AS client_siret,
               c.est_particulier, c.sans_tva
        FROM factures f
        JOIN clients c ON f.client_id = c.id
        WHERE f.id = ?
    """
    facture = conn.execute(query_facture, (facture_id,)).fetchone()
    if not facture:
        conn.close()
        raise ValueError(f"Facture ID {facture_id} introuvable.")

    facture_dict = dict(facture)

    query_items = """
        SELECT i.*, p.designation, p.unite 
        FROM interventions i
        LEFT JOIN prestations p ON i.prestation_id = p.id
        WHERE i.facture_id = ?
        ORDER BY i.date ASC
    """
    items = conn.execute(query_items, (facture_id,)).fetchall()
    params = database.recuperer_parametres()
    conn.close()

    if not output_path:
        output_path = obtenir_chemin_export_facture(
            facture_dict["nom_societe"], facture_dict["numero_facture"]
        )

    date_emiss_fr = format_date_fr(facture_dict["date_creation"])
    date_ech_fr = format_date_fr(facture_dict["date_echeance"])

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()

    COLOR_PRIMARY = colors.HexColor("#1e3a8a")
    COLOR_SECONDARY = colors.HexColor("#0284c7")
    COLOR_TEXT = colors.HexColor("#334155")
    COLOR_BG_LIGHT = colors.HexColor("#f8fafc")
    COLOR_BORDER = colors.HexColor("#e2e8f0")

    style_normal = ParagraphStyle(
        "NormalStyle",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        textColor=COLOR_TEXT,
    )
    style_company = ParagraphStyle(
        "CompanyStyle",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        textColor=COLOR_TEXT,
    )
    style_th = ParagraphStyle(
        "THStyle",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.white,
        fontName="Helvetica-Bold",
    )
    style_total_lbl = ParagraphStyle(
        "TotLbl",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=COLOR_TEXT,
        alignment=2,
    )
    style_total_val = ParagraphStyle(
        "TotVal",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=COLOR_TEXT,
        alignment=2,
    )
    style_ttc_val = ParagraphStyle(
        "TTCVal",
        parent=styles["Normal"],
        fontSize=11,
        leading=14,
        textColor=COLOR_PRIMARY,
        fontName="Helvetica-Bold",
        alignment=2,
    )

    elements = []

    header_elements = []
    logo_path_bdd = params.get("logo_path", "")
    if logo_path_bdd:
        logo_path = (
            logo_path_bdd
            if os.path.isabs(logo_path_bdd)
            else os.path.abspath(logo_path_bdd)
        )
        if os.path.exists(logo_path) and os.path.getsize(logo_path) > 0:
            try:
                img = Image(
                    logo_path, width=5.5 * cm, height=2.5 * cm, kind="proportional"
                )
                img.hAlign = "LEFT"
                header_elements.append(img)
                header_elements.append(Spacer(1, 0.3 * cm))
            except Exception:
                pass

    e_text = f"<b><font size='11' color='{COLOR_PRIMARY.hexval()}'>{params.get('nom_entreprise', 'Mon Entreprise')}</font></b><br/>"
    if params.get("adresse"):
        e_text += f"{params.get('adresse')}<br/>"
    if params.get("code_postal") or params.get("ville"):
        e_text += f"{params.get('code_postal', '')} {params.get('ville', '')}<br/>"
    if params.get("telephone"):
        e_text += f"Tél : {params.get('telephone')}<br/>"
    if params.get("email"):
        e_text += f"Email : {params.get('email')}<br/>"
    if params.get("siret"):
        e_text += f"SIRET : {params.get('siret')}"

    header_elements.append(Paragraph(e_text, style_company))

    cond_reg = facture_dict.get("conditions_reglement", "30 jours net")
    doc_title_text = f"""
    <font color="{COLOR_PRIMARY.hexval()}" size="22"><b>FACTURE</b></font><br/>
    <font color="{COLOR_SECONDARY.hexval()}" size="12"><b>N° {facture_dict['numero_facture']}</b></font><br/><br/>
    <b>Date d'émission :</b> {date_emiss_fr}<br/>
    <b>Date d'échéance :</b> {date_ech_fr}<br/>
    <b>Conditions :</b> {cond_reg}<br/>
    """
    cell_right = Paragraph(doc_title_text, style_normal)

    top_table = Table([[header_elements, cell_right]], colWidths=[10 * cm, 8 * cm])
    top_table.setStyle(
        TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (1, 0), (1, 0), "RIGHT")])
    )
    elements.append(top_table)
    elements.append(Spacer(1, 0.4 * cm))
    elements.append(
        HRFlowable(
            width="100%", thickness=1.5, color=COLOR_PRIMARY, spaceAfter=15, spaceBefore=0
        )
    )

    client_text = f"""
    <font size="9" color="{COLOR_PRIMARY.hexval()}"><b>DESTINATAIRE :</b></font><br/><br/>
    <font size="11" color="#0f172a"><b>{facture_dict['nom_societe']}</b></font><br/>
    """
    if facture_dict.get("contact"):
        client_text += f"À l'attention de : {facture_dict['contact']}<br/>"
    if facture_dict.get("client_adresse"):
        client_text += f"{facture_dict['client_adresse']}<br/>"
    if facture_dict.get("client_cp") or facture_dict.get("client_ville"):
        client_text += f"{facture_dict.get('client_cp', '')} {facture_dict.get('client_ville', '')}<br/>"
    if facture_dict.get("client_siret") and not facture_dict.get("est_particulier"):
        client_text += f"SIRET : {facture_dict['client_siret']}<br/>"

    client_table = Table([[Paragraph(client_text, style_normal)]], colWidths=[8.5 * cm])
    client_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_BG_LIGHT),
                ("BOX", (0, 0), (-1, -1), 1, COLOR_BORDER),
                ("PADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )

    dest_row = Table([["", client_table]], colWidths=[9.5 * cm, 8.5 * cm])
    dest_row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elements.append(dest_row)
    elements.append(Spacer(1, 1.2 * cm))

    items_groupes = {}
    for it in items:
        i_dict = dict(it)
        desig = i_dict.get("designation") or "Prestation réalisée"
        px_u = i_dict["prix_final_ht"] or 0.0
        taux_tva = i_dict.get("taux_tva") or 0.0
        unite = i_dict.get("unite") or "h"
        
        key = (desig, px_u, taux_tva, unite)
        if key not in items_groupes:
            items_groupes[key] = 0.0
        items_groupes[key] += (i_dict["quantite"] or 1.0)

    table_data = [
        [
            Paragraph("<b>Désignation / Prestation</b>", style_th),
            Paragraph("<b>Qté Totale</b>", ParagraphStyle("THRight", parent=style_th, alignment=2)),
            Paragraph("<b>P.U. HT</b>", ParagraphStyle("THRight", parent=style_th, alignment=2)),
            Paragraph("<b>TVA</b>", ParagraphStyle("THRight", parent=style_th, alignment=2)),
            Paragraph("<b>Total HT</b>", ParagraphStyle("THRight", parent=style_th, alignment=2)),
        ]
    ]

    for (desig, px_u, taux_tva, unite), qte_totale in items_groupes.items():
        tot_ligne_ht = qte_totale * px_u
        table_data.append(
            [
                Paragraph(f"<b>{desig}</b>", style_normal),
                Paragraph(f"{qte_totale:.2f} {unite}", ParagraphStyle("R", parent=style_normal, alignment=2)),
                Paragraph(f"{px_u:.2f} €", ParagraphStyle("R", parent=style_normal, alignment=2)),
                Paragraph(f"{taux_tva:.1f} %", ParagraphStyle("R", parent=style_normal, alignment=2)),
                Paragraph(f"<b>{tot_ligne_ht:.2f} €</b>", ParagraphStyle("R", parent=style_normal, alignment=2)),
            ]
        )

    prest_table = Table(
        table_data, colWidths=[7.5 * cm, 2.5 * cm, 2.8 * cm, 2.2 * cm, 3.0 * cm]
    )
    t_style = [
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARY),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            t_style.append(("BACKGROUND", (0, i), (-1, i), COLOR_BG_LIGHT))

    prest_table.setStyle(TableStyle(t_style))
    elements.append(prest_table)
    elements.append(Spacer(1, 0.6 * cm))

    tot_ht = facture_dict["total_ht"] or 0.0
    tot_tva = facture_dict["total_tva"] or 0.0
    tot_ttc = facture_dict["total_ttc"] or 0.0

    reglement_text = ""
    if params.get("iban"):
        reglement_text = f"""
        <b>Règlement par virement bancaire :</b><br/>
        <b>Banque :</b> {params.get('nom_banque', '')}<br/>
        <b>IBAN :</b> {params.get('iban', '')}<br/>
        <b>BIC :</b> {params.get('bic', '')}
        """
    cell_reglement = Paragraph(reglement_text, style_normal)

    totaux_data = [
        [Paragraph("<b>Total HT :</b>", style_total_lbl), Paragraph(f"{tot_ht:.2f} €", style_total_val)],
        [Paragraph("<b>Total TVA :</b>", style_total_lbl), Paragraph(f"{tot_tva:.2f} €", style_total_val)],
        [
            Paragraph(
                "<b>Total TTC :</b>",
                ParagraphStyle("TTCLbl", parent=style_total_lbl, fontName="Helvetica-Bold", fontSize=11, textColor=COLOR_PRIMARY),
            ),
            Paragraph(f"<b>{tot_ttc:.2f} €</b>", style_ttc_val),
        ],
    ]

    totaux_table = Table(totaux_data, colWidths=[3.5 * cm, 3.5 * cm])
    totaux_table.setStyle(
        TableStyle(
            [
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("LINEABOVE", (0, 2), (1, 2), 1.5, COLOR_PRIMARY),
                ("BACKGROUND", (0, 2), (1, 2), COLOR_BG_LIGHT),
            ]
        )
    )

    bottom_table = Table([[cell_reglement, totaux_table]], colWidths=[11 * cm, 7 * cm])
    bottom_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elements.append(bottom_table)
    elements.append(Spacer(1, 0.8 * cm))

    if params.get("tva_exoneree", 1) or facture_dict.get("sans_tva"):
        mention_tva = params.get("mention_tva_exoneree", "TVA non applicable, art. 293 B du CGI")
        elements.append(Paragraph(f"<i><font color='#64748b'>{mention_tva}</font></i>", style_normal))
        elements.append(Spacer(1, 0.4 * cm))

    if params.get("mentions_legales"):
        elements.append(Paragraph(f"<font size='7' color='#94a3b8'>{params.get('mentions_legales')}</font>", style_normal))

    doc.build(elements)

    conn = database.get_conn()
    conn.execute("UPDATE factures SET pdf_path = ? WHERE id = ?", (output_path, facture_id))
    conn.commit()
    conn.close()

    return os.path.abspath(output_path)


def generer_pdf_facture_detaillee(facture_id, output_path=None):
    """Génère le document PDF d'une facture détaillée (ligne par ligne par intervention) et l'enregistre[cite: 4]."""
    conn = database.get_conn()

    query_facture = """
        SELECT f.*, 
               c.nom_societe, c.contact, c.adresse AS client_adresse, 
               c.cp AS client_cp, c.ville AS client_ville, c.siret AS client_siret,
               c.est_particulier, c.sans_tva
        FROM factures f
        JOIN clients c ON f.client_id = c.id
        WHERE f.id = ?
    """
    facture = conn.execute(query_facture, (facture_id,)).fetchone()
    if not facture:
        conn.close()
        raise ValueError(f"Facture ID {facture_id} introuvable.")

    facture_dict = dict(facture)

    query_items = """
        SELECT i.*, p.designation, p.unite, e.nom_site AS etablissement_nom
        FROM interventions i
        LEFT JOIN prestations p ON i.prestation_id = p.id
        LEFT JOIN etablissements e ON i.etablissement_id = e.id
        WHERE i.facture_id = ?
        ORDER BY i.date ASC
    """
    items = conn.execute(query_items, (facture_id,)).fetchall()
    params = database.recuperer_parametres()
    conn.close()

    if not output_path:
        output_path = obtenir_chemin_export_facture(
            facture_dict["nom_societe"], facture_dict["numero_facture"]
        )

    date_emiss_fr = format_date_fr(facture_dict["date_creation"])
    date_ech_fr = format_date_fr(facture_dict["date_echeance"])

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()

    COLOR_PRIMARY = colors.HexColor("#1e3a8a")
    COLOR_SECONDARY = colors.HexColor("#0284c7")
    COLOR_TEXT = colors.HexColor("#334155")
    COLOR_BG_LIGHT = colors.HexColor("#f8fafc")
    COLOR_BORDER = colors.HexColor("#e2e8f0")

    style_normal = ParagraphStyle(
        "NormalStyle",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        textColor=COLOR_TEXT,
    )
    style_company = ParagraphStyle(
        "CompanyStyle",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        textColor=COLOR_TEXT,
    )
    style_th = ParagraphStyle(
        "THStyle",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.white,
        fontName="Helvetica-Bold",
    )
    style_total_lbl = ParagraphStyle(
        "TotLbl",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=COLOR_TEXT,
        alignment=2,
    )
    style_total_val = ParagraphStyle(
        "TotVal",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=COLOR_TEXT,
        alignment=2,
    )
    style_ttc_val = ParagraphStyle(
        "TTCVal",
        parent=styles["Normal"],
        fontSize=11,
        leading=14,
        textColor=COLOR_PRIMARY,
        fontName="Helvetica-Bold",
        alignment=2,
    )

    elements = []

    header_elements = []
    logo_path_bdd = params.get("logo_path", "")
    if logo_path_bdd:
        logo_path = (
            logo_path_bdd
            if os.path.isabs(logo_path_bdd)
            else os.path.abspath(logo_path_bdd)
        )
        if os.path.exists(logo_path) and os.path.getsize(logo_path) > 0:
            try:
                img = Image(
                    logo_path, width=5.5 * cm, height=2.5 * cm, kind="proportional"
                )
                img.hAlign = "LEFT"
                header_elements.append(img)
                header_elements.append(Spacer(1, 0.3 * cm))
            except Exception:
                pass

    e_text = f"<b><font size='11' color='{COLOR_PRIMARY.hexval()}'>{params.get('nom_entreprise', 'Mon Entreprise')}</font></b><br/>"
    if params.get("adresse"):
        e_text += f"{params.get('adresse')}<br/>"
    if params.get("code_postal") or params.get("ville"):
        e_text += f"{params.get('code_postal', '')} {params.get('ville', '')}<br/>"
    if params.get("telephone"):
        e_text += f"Tél : {params.get('telephone')}<br/>"
    if params.get("email"):
        e_text += f"Email : {params.get('email')}<br/>"
    if params.get("siret"):
        e_text += f"SIRET : {params.get('siret')}"

    header_elements.append(Paragraph(e_text, style_company))

    cond_reg = facture_dict.get("conditions_reglement", "30 jours net")
    doc_title_text = f"""
    <font color="{COLOR_PRIMARY.hexval()}" size="22"><b>FACTURE</b></font><br/>
    <font color="{COLOR_SECONDARY.hexval()}" size="12"><b>N° {facture_dict['numero_facture']}</b></font><br/><br/>
    <b>Date d'émission :</b> {date_emiss_fr}<br/>
    <b>Date d'échéance :</b> {date_ech_fr}<br/>
    <b>Conditions :</b> {cond_reg}<br/>
    """
    cell_right = Paragraph(doc_title_text, style_normal)

    top_table = Table([[header_elements, cell_right]], colWidths=[10 * cm, 8 * cm])
    top_table.setStyle(
        TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (1, 0), (1, 0), "RIGHT")])
    )
    elements.append(top_table)
    elements.append(Spacer(1, 0.4 * cm))
    elements.append(
        HRFlowable(
            width="100%", thickness=1.5, color=COLOR_PRIMARY, spaceAfter=15, spaceBefore=0
        )
    )

    client_text = f"""
    <font size="9" color="{COLOR_PRIMARY.hexval()}"><b>DESTINATAIRE :</b></font><br/><br/>
    <font size="11" color="#0f172a"><b>{facture_dict['nom_societe']}</b></font><br/>
    """
    if facture_dict.get("contact"):
        client_text += f"À l'attention de : {facture_dict['contact']}<br/>"
    if facture_dict.get("client_adresse"):
        client_text += f"{facture_dict['client_adresse']}<br/>"
    if facture_dict.get("client_cp") or facture_dict.get("client_ville"):
        client_text += f"{facture_dict.get('client_cp', '')} {facture_dict.get('client_ville', '')}<br/>"
    if facture_dict.get("client_siret") and not facture_dict.get("est_particulier"):
        client_text += f"SIRET : {facture_dict['client_siret']}<br/>"

    client_table = Table([[Paragraph(client_text, style_normal)]], colWidths=[8.5 * cm])
    client_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_BG_LIGHT),
                ("BOX", (0, 0), (-1, -1), 1, COLOR_BORDER),
                ("PADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )

    dest_row = Table([["", client_table]], colWidths=[9.5 * cm, 8.5 * cm])
    dest_row.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elements.append(dest_row)
    elements.append(Spacer(1, 1.2 * cm))

    table_data = [
        [
            Paragraph("<b>Date / Site / Prestation</b>", style_th),
            Paragraph("<b>Qté</b>", ParagraphStyle("THRight", parent=style_th, alignment=2)),
            Paragraph("<b>P.U. HT</b>", ParagraphStyle("THRight", parent=style_th, alignment=2)),
            Paragraph("<b>TVA</b>", ParagraphStyle("THRight", parent=style_th, alignment=2)),
            Paragraph("<b>Total HT</b>", ParagraphStyle("THRight", parent=style_th, alignment=2)),
        ]
    ]

    for it in items:
        i_dict = dict(it)
        date_interv = format_date_fr(i_dict.get("date"))
        site_nom = i_dict.get("etablissement_nom")
        desig = i_dict.get("designation") or "Prestation réalisée"
        
        libelle_ligne = f"<b>{date_interv}</b>"
        if site_nom:
            libelle_ligne += f" - <i>{site_nom}</i>"
        libelle_ligne += f"<br/>{desig}"
        
        if i_dict.get("commentaire"):
            libelle_ligne += f"<br/><font color='#64748b' size='7'>({i_dict['commentaire']})</font>"

        qte = i_dict.get("quantite") or 1.0
        px_u = i_dict.get("prix_final_ht") or 0.0
        taux_tva = i_dict.get("taux_tva") or 0.0
        unite = i_dict.get("unite") or "h"
        tot_ligne_ht = qte * px_u

        table_data.append(
            [
                Paragraph(libelle_ligne, style_normal),
                Paragraph(f"{qte:.2f} {unite}", ParagraphStyle("R", parent=style_normal, alignment=2)),
                Paragraph(f"{px_u:.2f} €", ParagraphStyle("R", parent=style_normal, alignment=2)),
                Paragraph(f"{taux_tva:.1f} %", ParagraphStyle("R", parent=style_normal, alignment=2)),
                Paragraph(f"<b>{tot_ligne_ht:.2f} €</b>", ParagraphStyle("R", parent=style_normal, alignment=2)),
            ]
        )

    prest_table = Table(
        table_data, colWidths=[7.5 * cm, 2.5 * cm, 2.8 * cm, 2.2 * cm, 3.0 * cm]
    )
    t_style = [
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARY),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            t_style.append(("BACKGROUND", (0, i), (-1, i), COLOR_BG_LIGHT))

    prest_table.setStyle(TableStyle(t_style))
    elements.append(prest_table)
    elements.append(Spacer(1, 0.6 * cm))

    tot_ht = facture_dict["total_ht"] or 0.0
    tot_tva = facture_dict["total_tva"] or 0.0
    tot_ttc = facture_dict["total_ttc"] or 0.0

    reglement_text = ""
    if params.get("iban"):
        reglement_text = f"""
        <b>Règlement par virement bancaire :</b><br/>
        <b>Banque :</b> {params.get('nom_banque', '')}<br/>
        <b>IBAN :</b> {params.get('iban', '')}<br/>
        <b>BIC :</b> {params.get('bic', '')}
        """
    cell_reglement = Paragraph(reglement_text, style_normal)

    totaux_data = [
        [Paragraph("<b>Total HT :</b>", style_total_lbl), Paragraph(f"{tot_ht:.2f} €", style_total_val)],
        [Paragraph("<b>Total TVA :</b>", style_total_lbl), Paragraph(f"{tot_tva:.2f} €", style_total_val)],
        [
            Paragraph(
                "<b>Total TTC :</b>",
                ParagraphStyle("TTCLbl", parent=style_total_lbl, fontName="Helvetica-Bold", fontSize=11, textColor=COLOR_PRIMARY),
            ),
            Paragraph(f"<b>{tot_ttc:.2f} €</b>", style_ttc_val),
        ],
    ]

    totaux_table = Table(totaux_data, colWidths=[3.5 * cm, 3.5 * cm])
    totaux_table.setStyle(
        TableStyle(
            [
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("LINEABOVE", (0, 2), (1, 2), 1.5, COLOR_PRIMARY),
                ("BACKGROUND", (0, 2), (1, 2), COLOR_BG_LIGHT),
            ]
        )
    )

    bottom_table = Table([[cell_reglement, totaux_table]], colWidths=[11 * cm, 7 * cm])
    bottom_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    elements.append(bottom_table)
    elements.append(Spacer(1, 0.8 * cm))

    if params.get("tva_exoneree", 1) or facture_dict.get("sans_tva"):
        mention_tva = params.get("mention_tva_exoneree", "TVA non applicable, art. 293 B du CGI")
        elements.append(Paragraph(f"<i><font color='#64748b'>{mention_tva}</font></i>", style_normal))
        elements.append(Spacer(1, 0.4 * cm))

    if params.get("mentions_legales"):
        elements.append(Paragraph(f"<font size='7' color='#94a3b8'>{params.get('mentions_legales')}</font>", style_normal))

    doc.build(elements)

    conn = database.get_conn()
    conn.execute("UPDATE factures SET pdf_path = ? WHERE id = ?", (output_path, facture_id))
    conn.commit()
    conn.close()

    return os.path.abspath(output_path)


def generer_pdf_recap_facture(facture_id, output_path=None, intitule="Intervention(s)"):
    """Génère le PDF du récapitulatif détaillé des interventions (avec totaux et nombre de prestations)."""
    conn = database.get_conn()

    query_facture = """
        SELECT f.*, c.nom_societe 
        FROM factures f
        JOIN clients c ON f.client_id = c.id
        WHERE f.id = ?
    """
    facture = conn.execute(query_facture, (facture_id,)).fetchone()
    conn.close()
    if not facture:
        raise ValueError(f"Facture ID {facture_id} introuvable.")
    facture_dict = dict(facture)

    conn = database.get_conn()
    query_items = """
        SELECT 
            i.*, 
            p.designation AS prest_nom,
            e.nom_site AS etablissement_nom
        FROM interventions i
        LEFT JOIN prestations p ON i.prestation_id = p.id
        LEFT JOIN etablissements e ON i.etablissement_id = e.id
        WHERE i.facture_id = ?
        ORDER BY i.date ASC
    """
    interventions = conn.execute(query_items, (facture_id,)).fetchall()
    conn.close()

    if not output_path:
        output_path = obtenir_chemin_export_recap(
            facture_dict["nom_societe"], facture_dict["numero_facture"]
        )

    doc = SimpleDocTemplate(
        output_path,
        pagesize=landscape(A4),
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()
    COLOR_PRIMARY = colors.HexColor("#1e3a8a")
    COLOR_TEXT = colors.HexColor("#334155")
    COLOR_BG_LIGHT = colors.HexColor("#f8fafc")
    COLOR_BORDER = colors.HexColor("#e2e8f0")

    style_title = ParagraphStyle(
        "TitleStyle", parent=styles["Normal"], fontSize=16, leading=20, textColor=COLOR_PRIMARY, fontName="Helvetica-Bold"
    )
    style_sub = ParagraphStyle(
        "SubStyle", parent=styles["Normal"], fontSize=10, leading=14, textColor=COLOR_TEXT
    )
    style_th = ParagraphStyle(
        "THStyle", parent=styles["Normal"], fontSize=9, leading=12, textColor=colors.white, fontName="Helvetica-Bold", alignment=1
    )
    style_cell = ParagraphStyle(
        "Cell", parent=styles["Normal"], fontSize=8, leading=11, textColor=COLOR_TEXT
    )
    style_cell_center = ParagraphStyle(
        "CellC", parent=styles["Normal"], fontSize=8, leading=11, textColor=COLOR_TEXT, alignment=1
    )

    elements = []
    elements.append(Paragraph(f"RÉCAPITULATIF DES PRESTATIONS - FACTURE {facture_dict['numero_facture']}", style_title))
    elements.append(Paragraph(f"<b>Client :</b> {facture_dict['nom_societe']} | Émis le {format_date_fr(facture_dict['date_creation'])}", style_sub))
    elements.append(Spacer(1, 0.5 * cm))

    if not interventions:
        elements.append(Paragraph("Aucune prestation détaillée liée à cette facture.", style_sub))
    else:
        etabs_set = set()
        for it in interventions:
            etab = it["etablissement_nom"] or "Autre"
            etabs_set.add(etab)
        etabs_list = sorted(list(etabs_set))

        semaines_dict = {}
        for it in interventions:
            dt = datetime.strptime(str(it["date"]).strip(), "%Y-%m-%d")
            debut_sem = dt - timedelta(days=dt.weekday())
            fin_sem = debut_sem + timedelta(days=6)
            
            # Utilisation du dictionnaire français pour les mois
            m_debut = MOIS_FR[debut_sem.month]
            m_fin = MOIS_FR[fin_sem.month]
            
            if debut_sem.month == fin_sem.month:
                sem_key = f"Semaine du {debut_sem.strftime('%d')} au {fin_sem.strftime('%d')} {m_fin}"
            else:
                sem_key = f"Semaine du {debut_sem.strftime('%d')} {m_debut} au {fin_sem.strftime('%d')} {m_fin}"

            if sem_key not in semaines_dict:
                semaines_dict[sem_key] = []
            semaines_dict[sem_key].append(dict(it))

        num_cols = len(etabs_list) + 2
        page_width = landscape(A4)[0] - 3 * cm
        col_width = page_width / num_cols
        col_widths = [4 * cm] + [col_width] * (len(etabs_list) + 1)

        table_data = []
        header_row = [Paragraph("<b>Semaines / Sites</b>", style_th)]
        for etab in etabs_list:
            header_row.append(Paragraph(f"<b>{etab}</b>", style_th))
        header_row.append(Paragraph("<b>Total Semaine</b>", style_th))
        table_data.append(header_row)

        total_general_mois = 0.0
        total_general_nombre = 0

        for sem_lib, items_sem in semaines_dict.items():
            row = [Paragraph(f"<b>{sem_lib}</b>", style_cell)]
            total_semaine = 0.0
            nombre_semaine = 0

            for etab in etabs_list:
                matches = [x for x in items_sem if (x["etablissement_nom"] or "Autre") == etab]
                cell_texts = []
                for m in matches:
                    d_fr = format_date_fr(m["date"])
                    montant_ligne = (m["prix_final_ht"] or 0.0) * (m["quantite"] or 1.0)
                    total_semaine += montant_ligne
                    nombre_semaine += 1
                    
                    desc_courte = m["prest_nom"] or f"Interv. {m['id']}"
                    if m.get('commentaire'):
                        desc_courte += f"<br/><font color='#64748b' size='7'>({m['commentaire']})</font>"
                        
                    cell_texts.append(f"{d_fr}<br/>{desc_courte} : <b>{montant_ligne:.0f}€</b>")

                contenu = "<br/><br/>".join(cell_texts) if cell_texts else "-"
                row.append(Paragraph(contenu, style_cell_center))

            total_general_mois += total_semaine
            total_general_nombre += nombre_semaine

            row.append(Paragraph(f"<b>{total_semaine:.0f} €</b><br/><font size='7' color='#64748b'>({nombre_semaine} {intitule})</font>", style_cell_center))
            table_data.append(row)

        total_row = [Paragraph("<b>TOTAL MOIS</b>", style_th)]
        for etab in etabs_list:
            total_row.append(Paragraph("-", style_th))
        total_row.append(Paragraph(f"<b>{total_general_mois:.0f} €</b><br/><font size='7'>({total_general_nombre} {intitule})</font>", style_th))
        table_data.append(total_row)

        t_style = [
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARY),
            ("BACKGROUND", (0, -1), (-1, -1), COLOR_PRIMARY),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("GRID", (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]

        recap_table = Table(table_data, colWidths=col_widths)
        recap_table.setStyle(TableStyle(t_style))
        elements.append(recap_table)

    doc.build(elements)
    return os.path.abspath(output_path)


def generer_et_ouvrir_pdf_facture(facture_id, output_path=None):
    """Génère le PDF d'une facture (et son récap si configuré) ET l'ouvre automatiquement."""
    pdf_path = generer_pdf_facture(facture_id, output_path=output_path)
    webbrowser.open(os.path.abspath(pdf_path))
    return pdf_path


def generer_et_ouvrir_pdf_recap(facture_id, output_path=None, intitule="Intervention(s)"):
    """Génère le PDF du récapitulatif ET l'ouvre automatiquement."""
    pdf_path = generer_pdf_recap_facture(facture_id, output_path, intitule=intitule)
    webbrowser.open(os.path.abspath(pdf_path))
    return pdf_path

def generer_pdf_facture_recap_explicite(facture_id, output_path=None):
    return generer_pdf_recap_facture(facture_id, output_path)