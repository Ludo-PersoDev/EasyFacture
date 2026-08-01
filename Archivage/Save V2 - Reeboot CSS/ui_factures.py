import customtkinter as ctk
from tkinter import ttk, messagebox
import database
from pdf_generator import creer_pdf_facture
from tkcalendar import DateEntry
from datetime import datetime

class FacturesTab(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.setup_ui()

    def setup_ui(self):
        # On utilise 'self' comme master pour tout, car FacturesTab est déjà un Frame
        self.controls_frame = ctk.CTkFrame(self)
        self.controls_frame.pack(fill="x", padx=10, pady=10)
        
        self.combo_client = ttk.Combobox(self.controls_frame, values=[c[1] for c in database.recuperer_tous_les_clients()])
        self.combo_client.pack(side="left", padx=5)
        
        ctk.CTkButton(self.controls_frame, text="Charger à Facturer", command=self.charger_a_facturer).pack(side="left", padx=5)

        self.date_debut = DateEntry(self.controls_frame, width=12, date_pattern='dd/mm/yyyy')
        self.date_debut.pack(side="left", padx=5)

        self.date_fin = DateEntry(self.controls_frame, width=12, date_pattern='dd/mm/yyyy')
        self.date_fin.pack(side="left", padx=5)

        ctk.CTkButton(self.controls_frame, text="Sélectionner", command=self.selectionner_par_dates).pack(side="left", padx=5)

        # Bouton Action
        self.btn_valider = ctk.CTkButton(self, text="Facturer les sélectionnés", fg_color="green", command=self.valider_facturation)
        self.btn_valider.pack(pady=5)
        
        # Sélecteur de vue
        self.view_selector = ctk.CTkSegmentedButton(self, values=["À facturer", "Historique factures"], 
                                                    command=self.switch_view)
        self.view_selector.pack(pady=5)
        self.view_selector.set("À facturer")
        
        # Treeview
        self.tree = ttk.Treeview(self, show="headings")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        self.tree.bind("<Button-1>", self.toggle_check)
        
        # Initialisation
        self.setup_columns_a_facturer()
       
    def charger_a_facturer(self):
        nom_c = self.combo_client.get()
        
        # Sécurité : si le champ est vide, on arrête ou on affiche un message
        if not nom_c:
            return
            
        c_id = database.recuperer_id_client_par_nom(nom_c)
        
        # On vide toujours le tableau avant d'ajouter les nouvelles données
        for i in self.tree.get_children(): 
            self.tree.delete(i)
            
        if c_id:
            rows = database.recuperer_prestations_realisees_par_client(c_id)
            for row in rows:
                data_tuple = tuple(row) 
                self.tree.insert("", "end", values=("[ ]",) + data_tuple)
        else:
            # Optionnel : un petit message pour dire qu'aucun client n'a été trouvé
            pass

    def generer_facture(self):
        # 1. Récupération des données du tableau
        items = [self.tree.item(item)['values'] for item in self.tree.get_children()]
        nom_client = self.combo_client.get()
        
        # Correction : On force la conversion en float avant de sommer
        total = sum(float(item[4]) for item in items)
        
        # 2. Génération PDF
        creer_pdf_facture(nom_client, items, total)
        
        # 3. Mise à jour BDD (statut 'Facturé')
        ids = [item[0] for item in items]
        database.passer_au_statut_facture(ids)
        
        messagebox.showinfo("Succès", "Facture générée avec succès !")
        self.charger_a_facturer()

    def toggle_check(self, event):
        if self.view_selector.get() != "À facturer":
            return
        # Identifier si on a cliqué sur une cellule de la colonne 1 (Check)
        region = self.tree.identify("region", event.x, event.y)
        column = self.tree.identify_column(event.x)
        
        if region == "cell" and column == "#1":
            item = self.tree.identify_row(event.y)
            values = list(self.tree.item(item, "values"))
            
            # Inverser l'état
            values[0] = "[X]" if values[0] == "[ ]" else "[ ]"
            self.tree.item(item, values=values)

    def valider_facturation(self):
        items_selectionnes = [self.tree.item(i)['values'] for i in self.tree.get_children() if self.tree.item(i)['values'][0] == "[X]"]
        
        if not items_selectionnes:
            messagebox.showwarning("Erreur", "Aucune ligne sélectionnée !")
            return
            
        nom_client = self.combo_client.get()
        client_id = database.recuperer_id_client_par_nom(nom_client)
        
        # 1. Création facture et items (IDs des prestations)
        ids = [item[1] for item in items_selectionnes]
        num_facture, total = database.creer_facture_et_items(client_id, ids)
        
        # 2. Mise à jour du statut dans la BDD (Le chaînon manquant)
        database.passer_au_statut_facture(ids)
        
        # 3. Génération PDF Facture
        creer_pdf_facture(client_id, num_facture, total)
        
        # 4. Génération conditionnelle du Récap
        infos_client = database.recuperer_infos_client(client_id)
        print(f"DEBUG: Valeur de recap_interventions pour client {client_id} -> {infos_client.get('recap_interventions')}")
        if infos_client.get('recap_interventions'):
            try:
                from pdf_generator import creer_pdf_recap
                creer_pdf_recap(client_id, num_facture)
                print("DEBUG: creer_pdf_recap a été appelé avec succès.")
            except Exception as e:
                print(f"DEBUG: Erreur dans creer_pdf_recap -> {e}")
        else:
            print("DEBUG: Le récap est désactivé pour ce client (case non cochée).")

        if hasattr(self, 'prestations'):
            self.prestations.rafraichir_treeview()   
        messagebox.showinfo("Succès", f"Facture {num_facture} générée et prestations mises à jour !")
        self.charger_a_facturer()

    def selectionner_par_dates(self):
        d_debut = self.date_debut.get_date()
        d_fin = self.date_fin.get_date()
        
        for item in self.tree.get_children():
            values = list(self.tree.item(item, "values"))
            # La date est dans la 3ème colonne (index 2)
            try:
                date_presta = datetime.strptime(values[2], '%Y-%m-%d').date()
                
                # Cocher si dans l'intervalle
                if d_debut <= date_presta <= d_fin:
                    values[0] = "[X]"
                else:
                    values[0] = "[ ]"
                self.tree.item(item, values=values)
            except ValueError:
                continue

    def switch_view(self, value):
        # Vider le tableau
        for i in self.tree.get_children():
            self.tree.delete(i)
        
        if value == "À facturer":
            self.controls_frame.pack(fill="x", padx=10, pady=5) # Afficher les filtres
            self.btn_valider.pack(pady=5)                        # Afficher le bouton
            self.setup_columns_a_facturer()
            self.charger_a_facturer()
        else:
            self.controls_frame.pack_forget()                    # Masquer les filtres
            self.btn_valider.pack_forget()                       # Masquer le bouton
            self.setup_columns_historique()
            self.charger_historique_factures()
    
    def setup_columns_a_facturer(self):
        self.tree["columns"] = ("select", "id", "Date", "prestation", "prix")
        for col in self.tree["columns"]:
            self.tree.column(col, width=100)
        
        self.tree.heading("select", text="[ ]")
        self.tree.heading("id", text="ID")
        self.tree.heading("Date", text="Date")
        self.tree.heading("prestation", text="Prestation")
        self.tree.heading("prix", text="Prix")
        
        
    def setup_columns_historique(self):
        self.tree["columns"] = ("numero", "client", "date", "total", "statut", "reglement")
        self.tree.column("#0", width=0, stretch=False) # Masque la colonne fantôme
        for col in self.tree["columns"]:
            self.tree.column(col, width=120)
            
        self.tree.heading("numero", text="N° Facture")
        self.tree.heading("client", text="Client")
        self.tree.heading("date", text="Date Créa.")
        self.tree.heading("total", text="Total TTC")
        self.tree.heading("statut", text="Statut")
        self.tree.heading("reglement", text="Date Règl.")
        
    def charger_historique_factures(self):
        factures = database.recuperer_historique_factures()
        print(f"DEBUG: Nombre de factures trouvées -> {len(factures)}")
        for f in factures:
            # On affiche '-' si date_reglement est NULL
            date_r = f['date_paiement'] if f['date_paiement'] else "-"
            self.tree.insert("", "end", values=(
                f['numero_facture'], 
                f['nom_societe'], 
                f['date_creation'], 
                f"{f['total_ttc']:.2f} €", 
                f['statut'], 
                date_r
            ))
            
    