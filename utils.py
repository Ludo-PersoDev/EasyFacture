import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import database

def envoyer_email_devis(email_destinataire, nom_client, num_devis, montant_ttc, pdf_path=None):
    """Envoie un e-mail au client pour lui transmettre le devis avec sa pièce jointe PDF."""
    params = database.recuperer_parametres()
    smtp_server = params.get("smtp_server", "smtp.gmail.com")
    smtp_port = int(params.get("smtp_port", 587))
    smtp_user = params.get("smtp_user", "mon.adresse@gmail.com")
    smtp_password = params.get("smtp_password", "mon_mot_de_passe_application")

    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = email_destinataire
    msg['Subject'] = f"Votre devis {num_devis}"

    corps_mail = f"""Bonjour {nom_client},

Veuillez trouver ci-joint votre devis {num_devis} d'un montant total de {montant_ttc:.2f} €.

Restant à votre disposition pour toute question.

Cordialement."""

    msg.attach(MIMEText(corps_mail, 'plain'))

    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            att = MIMEApplication(f.read(), _subtype="pdf")
            att.add_header('Content-Disposition', 'attachment', filename=os.path.basename(pdf_path))
            msg.attach(att)

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, email_destinataire, msg.as_string())
        server.quit()
        return True, "E-mail envoyé avec succès !"
    except Exception as e:
        return False, f"Erreur lors de l'envoi : {str(e)}"


def envoyer_email_facture(destinataire, sujet, corps, pdf_path=None, pdf_recap_path=None):
    """
    Envoie un e-mail avec un ou deux fichiers PDF en pièces jointes.
    """
    params = database.recuperer_parametres()
    smtp_server = params.get("smtp_server", "smtp.gmail.com")
    smtp_port = int(params.get("smtp_port", 587))
    smtp_user = params.get("smtp_user", "mon.adresse@gmail.com")
    smtp_password = params.get("smtp_password", "mon_mot_de_passe_application")

    msg = MIMEMultipart()
    msg['From'] = smtp_user
    msg['To'] = destinataire
    msg['Subject'] = sujet

    msg.attach(MIMEText(corps, 'plain'))

    # Ajout de la facture principale
    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            att = MIMEApplication(f.read(), _subtype="pdf")
            att.add_header('Content-Disposition', 'attachment', filename=os.path.basename(pdf_path))
            msg.attach(att)

    # Ajout du récapitulatif
    if pdf_recap_path and os.path.exists(pdf_recap_path):
        with open(pdf_recap_path, "rb") as f:
            att_recap = MIMEApplication(f.read(), _subtype="pdf")
            att_recap.add_header('Content-Disposition', 'attachment', filename=os.path.basename(pdf_recap_path))
            msg.attach(att_recap)

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, destinataire, msg.as_string())
        server.quit()
        return True, "E-mail envoyé avec succès !"
    except Exception as e:
        return False, f"Erreur lors de l'envoi de l'e-mail : {str(e)}"