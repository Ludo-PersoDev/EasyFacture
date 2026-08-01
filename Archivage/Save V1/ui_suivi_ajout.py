import customtkinter as ctk
from tkcalendar import DateEntry
import database
import datetime
from tkinter import messagebox
import math
from pdf_generator import creer_pdf_devis

class FenetreAjout(ctk.CTkToplevel):
    def __init__(self, parent, mode="prestation", id_intervention=None):
        super().__init__(parent)
        self.mode = mode  # "prestation", "devis" ou "modification"
        self.id_intervention = id_intervention
        
        # Ajustement du titre selon le mode
        titre = f"Nouvelle {self.mode}" if mode != "modification" else "Modifier la prestation"
        self.title(titre)
        self.geometry("400x650")
        
        # On s'assure que la fenêtre est au premier plan
        self.after(10, self.lift)
        self.attributes("-topmost", True)
        
        self.setup_ui()
        
        # Si on est en modification, on charge les données
        if self.id_intervention:
            self.charger_donnees()

    def setup_ui(self):
        # 1. Sélection Client
        ctk.CTkLabel(self, text="Client :").pack(pady=(10, 0))
        self.combo_client = ctk.CTkComboBox(self, values=self.get_clients(), 
                                            command=self.on_client_changed, # <--- AJOUTER ÇA
                                            width=250)
        self.combo_client.pack(pady=5)

        # 2. Sélection Prestation
        ctk.CTkLabel(self, text="Prestation :").pack(pady=(10, 0))
        self.combo_prest = ctk.CTkComboBox(self, values=self.get_prestations(), width=250)
        self.combo_prest.pack(pady=5)

        # 3. Quantité (Masquée si prestation car calculée par heure)
        self.label_qt = ctk.CTkLabel(self, text="Quantité (forfait) :")
        self.entry_qt = ctk.CTkEntry(self, width=250)
        
        if self.mode == "devis":
            self.label_qt.pack(pady=(10, 0))
            self.entry_qt.pack(pady=5)

        # 4. Zone Date et Heures (Affichée si Prestation ou Modification)
        if self.mode in ["prestation", "modification"]:
            ctk.CTkLabel(self, text="Date :").pack(pady=(10, 0))
            self.cal = DateEntry(self, width=12, date_pattern='dd/mm/yyyy', 
                                 background='darkblue', foreground='white', borderwidth=2)
            self.cal.pack(pady=5)
            
            ctk.CTkLabel(self, text="Heure début :").pack()
            frame_h_d = ctk.CTkFrame(self, fg_color="transparent")
            frame_h_d.pack()
            self.combo_h_debut = ctk.CTkComboBox(frame_h_d, values=[f"{h:02d}" for h in range(24)], width=60)
            self.combo_h_debut.pack(side="left", padx=5)
            self.combo_m_debut = ctk.CTkComboBox(frame_h_d, values=[f"{m:02d}" for m in range(0, 60, 5)], width=60)
            self.combo_m_debut.pack(side="left", padx=5)
            
            ctk.CTkLabel(self, text="Heure fin :").pack()
            frame_h_f = ctk.CTkFrame(self, fg_color="transparent")
            frame_h_f.pack()
            self.combo_h_fin = ctk.CTkComboBox(frame_h_f, values=[f"{h:02d}" for h in range(24)], width=60)
            self.combo_h_fin.pack(side="left", padx=5)
            self.combo_m_fin = ctk.CTkComboBox(frame_h_f, values=[f"{m:02d}" for m in range(0, 60, 5)], width=60)
            self.combo_m_fin.pack(side="left", padx=5)

        # 5. Bouton Valider
        texte_bouton = "Enregistrer les modifications" if self.id_intervention else "Valider"
        self.btn_valider = ctk.CTkButton(self, text=texte_bouton, command=self.valider)
        self.btn_valider.pack(pady=30)

    def get_clients(self):
        clients = database.recuperer_tous_les_clients()
        return [c['nom_societe'] for c in clients]

    def get_prestations(self):
        return [p['designation'] for p in database.recuperer_toutes_les_prestations()]

    def charger_donnees(self):
        """Pré-remplit les champs avec les données de la BDD."""
        row = database.recuperer_intervention_par_id(self.id_intervention)
        if row:
            nom_c = database.recuperer_nom_client_par_id(row['client_id'])
            nom_p = database.recuperer_nom_prestation_par_id(row['prestation_id'])
            
            self.combo_client.set(nom_c)
            self.combo_prest.set(nom_p)
            
            if self.mode == "devis":
                self.entry_qt.insert(0, str(row['quantite']))
            else:
                date_obj = datetime.datetime.strptime(row['date'], "%Y-%m-%d")
                self.cal.set_date(date_obj)
                
                # Découpage HH:MM pour les nouvelles ComboBox
                h_d, m_d = row['heure_debut'].split(":")
                self.combo_h_debut.set(h_d)
                self.combo_m_debut.set(m_d)
                
                h_f, m_f = row['heure_fin'].split(":")
                self.combo_h_fin.set(h_f)
                self.combo_m_fin.set(m_f)

    def calculer_duree(self, debut, fin):
        try:
            t1 = datetime.datetime.strptime(debut, "%H:%M")
            t2 = datetime.datetime.strptime(fin, "%H:%M")
            delta = (t2 - t1).total_seconds() / 3600
            # Arrondi au 0.01 supérieur
            return math.ceil(delta * 100) / 100
            return max(0, delta)
        except: return 0

    def on_client_changed(self, event):
        # 1. On récupère l'ID du client sélectionné
        nom_client = self.combo_client.get()
        client_id = database.recuperer_id_client_par_nom(nom_client)
        
        # 2. On récupère les prestations filtrées
        nouvelles_prestations = database.recuperer_prestations_actives_par_client(client_id)
        
        # 3. On met à jour la ComboBox des prestations
        if nouvelles_prestations:
            self.combo_prest.configure(values=nouvelles_prestations)
            self.combo_prest.set(nouvelles_prestations[0]) # Sélectionne la 1ère par défaut
        else:
            self.combo_prest.configure(values=["Aucune prestation"])
            self.combo_prest.set("Aucune prestation")

    def valider(self):
        client_id = database.recuperer_id_client_par_nom(self.combo_client.get())
        prestation_id = database.recuperer_id_prestation_par_nom(self.combo_prest.get())
        
        # Calcul de la quantité et de l'état
        if self.mode in ["prestation", "modification"]:
            h_debut = f"{self.combo_h_debut.get()}:{self.combo_m_debut.get()}"
            h_fin = f"{self.combo_h_fin.get()}:{self.combo_m_fin.get()}"
            
            qt = self.calculer_duree(h_debut, h_fin)
            date_val = self.cal.get_date().strftime("%Y-%m-%d")
            
            # On détermine l'état
            etat = "Réalisée" if self.cal.get_date() < datetime.date.today() else "En attente"
        else:
            qt = self.entry_qt.get()
            date_val = datetime.date.today().strftime("%Y-%m-%d")
            h_debut, h_fin = "-", "-"
            etat = "Devisé"

        data = {
            'client_id': client_id,
            'prestation_id': prestation_id,
            'quantite': qt,
            'date': date_val,
            'heure_debut': h_debut,
            'heure_fin': h_fin,
            'etat': etat
        }

        if self.id_intervention:
            success = database.modifier_intervention(data)
        else:
            id_genere = database.ajouter_intervention(data)
            success = (id_genere is not None)

        if success:
            # Si c'est un devis, on génère le PDF
            if self.mode == "devis":
                nom_client = self.combo_client.get()
                # On utilise id_genere pour le nommage du fichier
                creer_pdf_devis(nom_client, self.combo_prest.get(), qt, 0, id_genere)
            
            self.destroy()
