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
        self.mode = mode
        self.id_intervention = id_intervention
        
        # Configuration fenêtre
        titre = f"Nouvelle {self.mode}" if mode != "modification" else "Modifier la prestation"
        self.title(titre)
        self.geometry("400x700")
        self.after(10, self.lift)
        self.attributes("-topmost", True)

        self.sites_data = []
        
        self.setup_ui()
        
        if self.id_intervention:
            self.charger_donnees()

    def setup_ui(self):
        # 1. Sélection Client
        ctk.CTkLabel(self, text="Client :").pack(pady=(10, 0))
        self.combo_client = ctk.CTkComboBox(self, values=self.get_clients(), command=self.on_client_changed, width=250)
        self.combo_client.set("Choisir client")
        self.combo_client.pack(pady=5)

        # 2. Sélection Site (Masqué par défaut)
        self.combo_sites = ctk.CTkComboBox(self, width=250)
        self.combo_sites.set("Choisir Site")
        # On ne le pack pas ici, il sera packé par on_client_changed si nécessaire

        # 3. Sélection Prestation
        ctk.CTkLabel(self, text="Prestation :").pack(pady=(10, 0))
        self.combo_prest = ctk.CTkComboBox(self, values=self.get_prestations(), width=250)
        self.combo_prest.set("Choisir Prestation")
        self.combo_prest.pack(pady=5)

        # 4. Quantité (pour Devis)
        self.label_qt = ctk.CTkLabel(self, text="Quantité :")
        self.entry_qt = ctk.CTkEntry(self, width=250)
        if self.mode == "devis":
            self.label_qt.pack(pady=(10, 0))
            self.entry_qt.pack(pady=5)

        # 5. Date et Heures (Affichées si Prestation ou Modification)
        if self.mode in ["prestation", "modification"]:
            ctk.CTkLabel(self, text="Date :").pack(pady=(10, 0))
            self.cal = DateEntry(self, width=12, date_pattern='dd-mm-yyyy')
            self.cal.pack(pady=5)
            
            ctk.CTkLabel(self, text="Heure début (HH:MM) :").pack()
            self.combo_h_debut = ctk.CTkComboBox(self, values=[f"{h:02d}" for h in range(24)], width=60)
            self.combo_h_debut.pack()
            self.combo_m_debut = ctk.CTkComboBox(self, values=[f"{m:02d}" for m in range(0, 60, 5)], width=60)
            self.combo_m_debut.pack()
            
            ctk.CTkLabel(self, text="Heure fin (HH:MM) :").pack()
            self.combo_h_fin = ctk.CTkComboBox(self, values=[f"{h:02d}" for h in range(24)], width=60)
            self.combo_h_fin.pack()
            self.combo_m_fin = ctk.CTkComboBox(self, values=[f"{m:02d}" for m in range(0, 60, 5)], width=60)
            self.combo_m_fin.pack()

            # 6. Commentaire
            self.check_comment = ctk.CTkCheckBox(self, text="Ajouter un commentaire", command=self.toggle_comment)
            self.check_comment.pack(pady=10)
            self.entry_commentaire = ctk.CTkEntry(self, width=250, placeholder_text="Observations...")

        # 7. Bouton Valider
        self.btn_valider = ctk.CTkButton(self, text="Valider", command=self.valider)
        self.btn_valider.pack(pady=30)

    # --- MÉTHODES UTILES ---
    def toggle_comment(self):
        if self.check_comment.get():
            self.entry_commentaire.pack(pady=5)
        else:
            self.entry_commentaire.pack_forget()
            self.entry_commentaire.delete(0, 'end')

    def on_client_changed(self, choice):
        client_id = database.recuperer_id_client_par_nom(choice)
        
        # 1. Mise à jour prestations (OK)
        prestas = database.recuperer_prestations_actives_par_client(client_id)
        self.combo_prest.configure(values=prestas if prestas else ["Aucune"])
        
        # 2. Mise à jour sites (CORRIGÉ)
        self.sites_data = database.recuperer_etablissements_par_client(client_id)
        noms_sites = [s['nom_site'] for s in self.sites_data]
        
        if noms_sites:
            print(f"DEBUG: Sites trouvés pour {client_id}: {noms_sites}")
            self.combo_sites.configure(values=noms_sites)
            self.combo_sites.set(noms_sites[0]) # Sélectionne le premier par défaut
            self.combo_sites.pack(pady=5)
        else:
            self.combo_sites.set("Choisir Site")
            self.combo_sites.pack_forget()
        
    def get_id_site_selectionne(self):
        nom_site = self.combo_sites.get()
        if not nom_site or nom_site == "Choisir un site": return None
        # Chercher l'ID via le nom (il faudra peut-être une petite fonction dans database.py)
        return None # À compléter si tu veux gérer les IDs de sites

    def valider(self):
        # 1. Protection contre le double clic
        self.btn_valider.configure(state="disabled")
        
        # Récupération IDs
        client_id = database.recuperer_id_client_par_nom(self.combo_client.get())
        prestation_id = database.recuperer_id_prestation_par_nom(self.combo_prest.get())
        
        if not client_id or not prestation_id:
            messagebox.showerror("Erreur", "Sélectionnez un client et une prestation.")
            self.btn_valider.configure(state="normal") # Réactiver si erreur
            return

        tarif_unitaire = database.get_tarif_unitaire(client_id, prestation_id)

        # Construction données
        if self.mode in ["prestation", "modification"]:
            # ... (ta logique de date/heure) ...
            h_debut = f"{self.combo_h_debut.get()}:{self.combo_m_debut.get()}"
            h_fin = f"{self.combo_h_fin.get()}:{self.combo_m_fin.get()}"
            date_choisie = self.cal.get_date()
            date_auj = datetime.date.today()
            etat_calculé = "Réalisée" if date_choisie <= date_auj else "En attente"
            
            data = {
                'client_id': client_id,
                'prestation_id': prestation_id,
                'quantite': self.calculer_duree(h_debut, h_fin),
                'prix_final': round(self.calculer_duree(h_debut, h_fin) * tarif_unitaire, 2),
                'date': date_choisie.strftime("%Y-%m-%d"),
                'heure_debut': h_debut,
                'heure_fin': h_fin,
                'etat': etat_calculé,
                'commentaire': self.entry_commentaire.get() if self.check_comment.get() else "",
                'etablissement_id': self.get_id_site(self.combo_sites.get()),
                'numero_devis': None
            }
        else: # Devis
            try:
                qt_val = float(self.entry_qt.get())
            except:
                qt_val = 1.0
            
            # 1. Générer le numéro
            num = database.generer_numero_devis() 
            
            # 2. L'inclure dans le dictionnaire
            data = {
                'client_id': client_id,
                'prestation_id': prestation_id,
                'quantite': qt_val,
                'prix_final': round(qt_val * tarif_unitaire, 2),
                'date': datetime.date.today().strftime("%Y-%m-%d"),
                'heure_debut': "-",
                'heure_fin': "-",
                'etat': "Devis",
                'commentaire': "",
                'etablissement_id': None,
                'numero_devis': num  # <--- IL MANQUAIT CETTE LIGNE
            }
            
        if self.id_intervention:
            data['id'] = self.id_intervention
            database.modifier_intervention(data)
        else:
            print(f"DEBUG: Données envoyées : {data}")
            id_genere = database.ajouter_intervention(data)
            print(f"DEBUG: ID reçu dans ui_suivi_ajout : {id_genere}")
            
            # Appel PDF uniquement si c'est un nouveau devis
            if self.mode == "devis" and id_genere:
                prix_a_afficher = data['prix_final']
                creer_pdf_devis(
                    client_id,
                    self.combo_client.get(),
                    self.combo_prest.get(),
                    float(data['quantite']),
                    float(prix_a_afficher),
                    id_genere
                )
        
        self.destroy()

    def get_clients(self): return [c['nom_societe'] for c in database.recuperer_tous_les_clients()]

    def get_prestations(self): return [p['designation'] for p in database.recuperer_toutes_les_prestations()]

    def get_id_site(self, nom_site):
        # Vérification si la liste est vide ou si le nom est un placeholder
        if not self.sites_data or nom_site == "Choisir Site":
            return None
        for s in self.sites_data: 
            if s['nom_site'] == nom_site: return s['id']
        return None

    def calculer_duree(self, debut, fin):
        try:
            t1 = datetime.datetime.strptime(debut, "%H:%M")
            t2 = datetime.datetime.strptime(fin, "%H:%M")
            delta = (t2 - t1).total_seconds() / 3600
            return max(0, round(delta, 2))
        except: 
            return 0.0

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
                
                h_d, m_d = row['heure_debut'].split(":")
                self.combo_h_debut.set(h_d)
                self.combo_m_debut.set(m_d)
                
                h_f, m_f = row['heure_fin'].split(":")
                self.combo_h_fin.set(h_f)
                self.combo_m_fin.set(m_f)
