import customtkinter as ctk
from tkinter import ttk, messagebox
import database

class ClientsTab:
    def __init__(self, tab):
        self.tab = tab
        self.setup_ui()
        self.charger_clients()

    def setup_ui(self):
        # --- Barre de filtre ---
        frame_filter = ctk.CTkFrame(self.tab, fg_color="transparent")
        frame_filter.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(frame_filter, text="Afficher les clients :").pack(side="left", padx=5)
        self.combo_filter = ctk.CTkComboBox(frame_filter, values=["Tous", "Sociétés", "Particuliers"], command=self.filtrer_liste)
        self.combo_filter.pack(side="left", padx=5)

        # Recherche inclusive
        ctk.CTkLabel(frame_filter, text="Rechercher :").pack(side="left", padx=(15, 5))
        self.ent_recherche = ctk.CTkEntry(frame_filter, placeholder_text="Nom du client...", width=200)
        self.ent_recherche.pack(side="left", padx=5)
        self.ent_recherche.bind("<KeyRelease>", lambda event: self.charger_clients())

        # --- Tableau Central ---
        cols = ("ID", "Type", "Nom", "Contact", "Adresse", "CP", "Ville", "Pays", "Multi-Sites", "Récap")
        self.tree = ttk.Treeview(self.tab, columns=cols, show='headings')
        
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=80) 
        
        self.tree.column("ID", width=40, anchor="center")
        self.tree.column("Nom", width=150)
        self.tree.pack(fill="both", expand=True, padx=10, pady=(5, 5))

        # --- Barre de boutons d'action ---
        frame_actions = ctk.CTkFrame(self.tab, fg_color="transparent")
        frame_actions.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkButton(frame_actions, text="Ajouter Client", fg_color="green", command=self.ouvrir_ajout).pack(side="left", padx=5)
        ctk.CTkButton(frame_actions, text="Modifier Client", command=self.ouvrir_modification).pack(side="left", padx=5)
        ctk.CTkButton(frame_actions, text="Supprimer Client", fg_color="red", command=self.supprimer_client).pack(side="right", padx=5)
        self.btn_prest = ctk.CTkButton(frame_actions, text="Gérer Prestations", fg_color="gray", state="disabled", command=self.ouvrir_prestations)
        self.btn_prest.pack(side="left", padx=5)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.btn_prest.configure(state="normal"))
        
    def filtrer_liste(self, choice):
        self.charger_clients(filtre=choice)

    def ouvrir_ajout(self):
        ClientFormWindow(self.tab.winfo_toplevel(), callback=self.charger_clients)
        
    def ouvrir_modification(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Attention", "Veuillez sélectionner un client.")
            return
        id_client = self.tree.item(selected[0])['values'][0]
        ClientFormWindow(self.tab.winfo_toplevel(), client_id=id_client, callback=self.charger_clients)

    def supprimer_client(self):
        selected = self.tree.selection()
        if selected:
            id_client = self.tree.item(selected[0])['values'][0]
            nom = self.tree.item(selected[0])['values'][2]
            if messagebox.askyesno("Confirmation", f"Supprimer '{nom}' ?"):
                succes, message = database.supprimer_client(id_client)
                if succes: self.charger_clients()
                else: messagebox.showerror("Erreur", message)

    def charger_clients(self, filtre="Tous"):
        if isinstance(filtre, str) and filtre not in ["Tous", "Sociétés", "Particuliers"]:
            filtre = self.combo_filter.get()
            
        search_text = self.ent_recherche.get().lower()
        for i in self.tree.get_children(): self.tree.delete(i)
        
        for c in database.recuperer_tous_les_clients():
            nom_client = c['nom_societe'].lower()
            type_cl = "Particulier" if c['est_particulier'] else "Société"
            
            if filtre == "Sociétés" and type_cl == "Particulier": continue
            if filtre == "Particuliers" and type_cl == "Société": continue
            if search_text and search_text not in nom_client: continue
                
            val = (
                c['id'], type_cl, c['nom_societe'], c['contact'], 
                c['adresse'], c['cp'], c['ville'], c['pays'],
                "Oui" if c['multi_etab'] else "Non", 
                "Oui" if c['recap_interventions'] else "Non"
            )
            self.tree.insert("", "end", values=val)
            
    def ouvrir_prestations(self):
        selected = self.tree.selection()
        if selected:
            id_client = self.tree.item(selected[0])['values'][0]
            nom_client = self.tree.item(selected[0])['values'][2]
            PrestationsClientWindow(self.tab.winfo_toplevel(), id_client, nom_client)

# ==========================================
# FENÊTRE : FORMULAIRE CLIENT
# ==========================================
class ClientFormWindow(ctk.CTkToplevel):
    def __init__(self, parent, client_id=None, callback=None):
        super().__init__(parent)
        self.title("Client" if client_id is None else "Modifier le Client")
        self.geometry("600x750")
        self.grab_set()
        self.client_id, self.callback = client_id, callback
        
        self.var_particulier = ctk.IntVar(value=0)
        self.var_sans_tva = ctk.IntVar(value=0)
        self.var_recap = ctk.IntVar(value=0)
        self.var_multi = ctk.IntVar(value=0)

        self.setup_ui()
        if self.client_id: self.charger_donnees()
        self.var_sans_tva.trace_add("write", self.toggle_tva_field)

    def setup_ui(self):
        scroll = ctk.CTkScrollableFrame(self)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkCheckBox(scroll, text="Client Particulier", variable=self.var_particulier, command=self.toggle_particulier).pack(pady=10)
        
        self.lbl_nom = ctk.CTkLabel(scroll, text="Nom Société *") # Correction : ajout du label manquant
        self.lbl_nom.pack(anchor="w", padx=5)
        self.ent_nom = ctk.CTkEntry(scroll, placeholder_text="Nom Société / Nom Client")
        self.ent_nom.pack(fill="x", pady=5)
        self.ent_contact = ctk.CTkEntry(scroll, placeholder_text="Contact")
        self.ent_contact.pack(fill="x", pady=5)
        self.ent_adresse = ctk.CTkEntry(scroll, placeholder_text="Adresse")
        self.ent_adresse.pack(fill="x", pady=5)
        self.ent_cp = ctk.CTkEntry(scroll, placeholder_text="CP")
        self.ent_cp.pack(fill="x", pady=5)
        self.ent_ville = ctk.CTkEntry(scroll, placeholder_text="Ville")
        self.ent_ville.pack(fill="x", pady=5)
        self.ent_pays = ctk.CTkEntry(scroll)
        if not self.ent_pays.get(): 
            self.ent_pays.insert(0, "France")
        self.ent_pays.pack(fill="x", pady=5)
        self.ent_pays.pack(fill="x", pady=5)
        self.ent_email = ctk.CTkEntry(scroll, placeholder_text="Email")
        self.ent_email.pack(fill="x", pady=5)
        self.ent_tel = ctk.CTkEntry(scroll, placeholder_text="Téléphone")
        self.ent_tel.pack(fill="x", pady=5)

        self.ent_siret = ctk.CTkEntry(scroll, placeholder_text="SIRET")
        self.ent_siret.pack(fill="x", pady=5)
        self.ent_rcs = ctk.CTkEntry(scroll, placeholder_text="RCS")
        self.ent_rcs.pack(fill="x", pady=5)
        self.ent_ape = ctk.CTkEntry(scroll, placeholder_text="APE")
        self.ent_ape.pack(fill="x", pady=5)
        self.ent_tva = ctk.CTkEntry(scroll, placeholder_text="TVA Intra")
        self.ent_tva.pack(fill="x", pady=5)
        self.chk_sans_tva = ctk.CTkCheckBox(scroll, text="Non soumis à la TVA", variable=self.var_sans_tva)
        self.chk_sans_tva.pack(pady=10)

        ctk.CTkCheckBox(scroll, text="Récapitulatif prestations", variable=self.var_recap).pack(pady=5)
        ctk.CTkCheckBox(scroll, text="Gère plusieurs établissements", variable=self.var_multi, command=self.toggle_etab).pack(pady=5)
        self.btn_gerer_etab = ctk.CTkButton(scroll, text="Gérer établissements", state="disabled", command=self.ouvrir_gestion_sites)
        self.btn_gerer_etab.pack(pady=5)
        
        ctk.CTkButton(self, text="Enregistrer", command=self.sauvegarder).pack(pady=10)

    def ouvrir_gestion_sites(self):
        if self.client_id:
            GestionSitesWindow(self, self.client_id, self.ent_nom.get())
        else:
            messagebox.showwarning("Attention", "Veuillez d'abord enregistrer le client.")

    def toggle_tva_field(self, *args):
        state = "disabled" if self.var_sans_tva.get() == 1 else "normal"
        self.ent_tva.configure(state=state)
        if state == "disabled": self.ent_tva.delete(0, 'end')

    def toggle_particulier(self):
        if self.var_particulier.get() == 1:
            self.lbl_nom.configure(text="Nom du Client *")
            for ent in [self.ent_siret, self.ent_rcs, self.ent_ape, self.ent_tva]:
                ent.delete(0, 'end')
                ent.configure(state="disabled")
            self.chk_sans_tva.configure(state="disabled")
        else:
            self.lbl_nom.configure(text="Nom Société *")
            for ent in [self.ent_siret, self.ent_rcs, self.ent_ape, self.ent_tva]:
                ent.configure(state="normal")
            self.chk_sans_tva.configure(state="normal")

    def toggle_etab(self):
        if self.var_multi.get() == 1:
            if self.client_id: self.btn_gerer_etab.configure(state="normal")
            else: self.btn_gerer_etab.configure(state="disabled", text="Enregistrez le client d'abord")
        else: self.btn_gerer_etab.configure(state="disabled", text="Gérer les établissements")

    def charger_donnees(self):
        data = database.recuperer_client_par_id(self.client_id)
        if data:
            self.ent_nom.insert(0, data['nom_societe'] or "")
            self.ent_contact.insert(0, data['contact'] or "")
            self.ent_adresse.insert(0, data['adresse'] or "")
            self.ent_cp.insert(0, data['cp'] or "")
            self.ent_ville.insert(0, data['ville'] or "")
            self.ent_pays.delete(0, 'end') # ON VIDE D'ABORD
            self.ent_pays.insert(0, data['pays'] if data['pays'] else "France")
            self.ent_email.insert(0, data['email'] or "")
            self.ent_tel.insert(0, data['telephone'] or "")
            self.ent_siret.insert(0, data['siret'] or "")
            self.ent_tva.insert(0, data['tva_intra'] or "")
            self.ent_rcs.insert(0, data['rcs'] or "")
            self.ent_ape.insert(0, data['ape'] or "")
            self.var_particulier.set(data['est_particulier'])
            self.var_sans_tva.set(data['sans_tva'])
            self.var_recap.set(data['recap_interventions'])
            self.var_multi.set(data['multi_etab'])
            self.toggle_particulier()
            self.toggle_etab()

    def sauvegarder(self):
        nom = self.ent_nom.get().strip()
        if not nom:
            messagebox.showwarning("Erreur", "Le nom est obligatoire.")
            return
        client_data = {
            'nom_societe': nom, 'contact': self.ent_contact.get(), 'adresse': self.ent_adresse.get(),
            'cp': self.ent_cp.get(), 'ville': self.ent_ville.get(), 'pays': self.ent_pays.get(),
            'email': self.ent_email.get(), 'telephone': self.ent_tel.get(), 'siret': self.ent_siret.get(),
            'tva_intra': self.ent_tva.get(), 'rcs': self.ent_rcs.get(), 'ape': self.ent_ape.get(),
            'est_particulier': self.var_particulier.get(), 'sans_tva': self.var_sans_tva.get(),
            'recap_interventions': self.var_recap.get(), 'multi_etab': self.var_multi.get()
        }
        if self.client_id:
            database.modifier_client(self.client_id, client_data)
        else:
            print("DEBUG: Contenu de client_data envoyé à la BDD :", client_data)
            database.ajouter_client(client_data)
        if self.callback:
            self.callback()
        self.destroy()


# ==========================================
# FENÊTRE : GESTION DES ÉTABLISSEMENTS
# ==========================================
class GestionSitesWindow(ctk.CTkToplevel):
    def __init__(self, parent, client_id, nom_client):
        super().__init__(parent)
        self.title(f"Établissements de {nom_client}")
        self.geometry("600x500")
        self.grab_set()
        self.client_id = client_id
        
        self.setup_ui()
        self.charger_sites()

    def setup_ui(self):
        # Formulaire d'ajout
        frame_form = ctk.CTkFrame(self)
        frame_form.pack(fill="x", padx=10, pady=10)
        
        self.ent_nom = ctk.CTkEntry(frame_form, placeholder_text="Nom du site (ex: Boutique Centre) *")
        self.ent_nom.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        
        self.ent_adresse = ctk.CTkEntry(frame_form, placeholder_text="Adresse")
        self.ent_adresse.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
        
        self.ent_cp = ctk.CTkEntry(frame_form, placeholder_text="Code Postal", width=100)
        self.ent_cp.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        
        self.ent_ville = ctk.CTkEntry(frame_form, placeholder_text="Ville")
        self.ent_ville.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        self.ent_pays = ctk.CTkEntry(frame_form, placeholder_text="Pays")
        self.ent_pays.insert(0, "France")
        self.ent_pays.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

        # Pour que la colonne prenne l'espace dispo
        frame_form.columnconfigure(1, weight=1)

        ctk.CTkButton(frame_form, text="Ajouter ce site", command=self.ajouter_site).grid(row=4, column=0, columnspan=2, pady=10)

        # Tableau des sites
        self.tree = ttk.Treeview(self, columns=("ID", "Nom", "Ville"), show='headings')
        self.tree.heading("ID", text="ID")
        self.tree.heading("Nom", text="Nom du Site")
        self.tree.heading("Ville", text="Ville")
        self.tree.column("ID", width=40, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        ctk.CTkButton(self, text="Supprimer le site sélectionné", fg_color="red", command=self.supprimer_site).pack(pady=10)

    def ajouter_site(self):
        nom = self.ent_nom.get().strip()
        if not nom:
            messagebox.showwarning("Erreur", "Le nom du site est obligatoire.")
            return
            
        database.ajouter_etablissement(
            self.client_id, nom, self.ent_adresse.get(), 
            self.ent_cp.get(), self.ent_ville.get(), self.ent_pays.get()
        )
        self.charger_sites()
        
        # Vider les champs après ajout
        for ent in [self.ent_nom, self.ent_adresse, self.ent_cp, self.ent_ville]:
            ent.delete(0, 'end')

    def supprimer_site(self):
        selected = self.tree.selection()
        if selected:
            id_site = self.tree.item(selected[0])['values'][0]
            database.supprimer_etablissement(id_site)
            self.charger_sites()

    def charger_sites(self):
        for i in self.tree.get_children(): 
            self.tree.delete(i)
        
        # 's' est maintenant un objet Row, accédez par le nom de la colonne
        for s in database.recuperer_etablissements_par_client(self.client_id):
            self.tree.insert("", "end", values=(s['id'], s['nom_site'], s['ville']))

# ==========================================
# FENÊTRE : GESTION PRESTATIONS CLIENT
# ==========================================
class PrestationsClientWindow(ctk.CTkToplevel):
    def __init__(self, parent, client_id, nom_client):
        super().__init__(parent)
        self.title(f"Tarifs personnalisés - {nom_client}")
        self.geometry("500x600")
        self.grab_set()
        self.client_id = client_id
        
        # Récupérer tout le catalogue et les tarifs déjà définis
        self.toutes_prestations = database.recuperer_toutes_les_prestations()
        # CORRECTION : Utilise les noms de colonnes plutôt que des index [0], [1]
        raw_tarifs = database.recuperer_tarifs_client(client_id)
        # On suppose que ton Row possède une clé 'prestation_id' et 'prix'
        # Adapte les noms 'prestation_id' et 'prix' selon ta base de données
        self.tarifs_existants = {t['prestation_id']: t['prix'] for t in raw_tarifs}

        self.setup_ui()

    def setup_ui(self):
        scroll = ctk.CTkScrollableFrame(self)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.rows = []
        for p in self.toutes_prestations:
            frame = ctk.CTkFrame(scroll)
            frame.pack(fill="x", pady=2)
            
            var_active = ctk.BooleanVar(value=(p['id'] in self.tarifs_existants))
            ent_prix = ctk.CTkEntry(frame, width=80)
            
            # --- CORRECTION SÉCURISÉE ---
            # On vérifie si la clé existe avant d'y accéder
            valeur_par_defaut = 0.0
            if 'prix_ht' in p.keys():
                valeur_par_defaut = p['prix_ht']
            # Ajoute ici d'autres noms de colonnes possibles si nécessaire
            elif 'prix' in p.keys():
                valeur_par_defaut = p['prix']

            prix_a_afficher = self.tarifs_existants.get(p['id'], valeur_par_defaut)
            # ----------------------------
            
            ent_prix.insert(0, str(prix_a_afficher))
            
            chk = ctk.CTkCheckBox(frame, text=p['designation'], variable=var_active, 
                                  command=lambda v=var_active, e=ent_prix: self.toggle_prix(v, e))
            chk.pack(side="left", padx=10)
            ent_prix.pack(side="right", padx=10)
            
            if not var_active.get():
                ent_prix.configure(state="disabled")
            
            self.rows.append((p['id'], var_active, ent_prix))

        ctk.CTkButton(self, text="Enregistrer les tarifs", command=self.enregistrer).pack(pady=10)

    def toggle_prix(self, var, entry):
        entry.configure(state="normal" if var.get() else "disabled")

    def enregistrer(self):
        for p_id, var, ent in self.rows:
            if var.get():
                database.sauvegarder_tarif_client(self.client_id, p_id, ent.get())
            else:
                database.supprimer_tarif_client(self.client_id, p_id)
        self.destroy()
