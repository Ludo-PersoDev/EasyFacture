import customtkinter as ctk
from tkinter import ttk, messagebox
import database
from ui_suivi_ajout import FenetreAjout
import datetime
from tkcalendar import DateEntry
import os

# Fonction utilitaire globale pour les chemins
def get_base_path():
    return r"C:\FacturEx"

class PrestationsTab:
    def __init__(self, tab):
        self.tab = tab
        self.setup_ui()
        self.rafraichir_treeview()

    def setup_ui(self):
        # Barre de filtres
        self.frame_filtres = ctk.CTkFrame(self.tab)
        self.frame_filtres.pack(fill="x", padx=10, pady=5)
        
        self.search_entry = ctk.CTkEntry(self.frame_filtres, placeholder_text="Rechercher client...")
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<KeyRelease>", lambda e: self.rafraichir_treeview())
        
        self.checkbox_masquer_payees = ctk.CTkCheckBox(self.frame_filtres, text="Masquer payées", 
                                                       command=self.rafraichir_treeview)
        self.checkbox_masquer_payees.pack(side="left", padx=10)
        
        ctk.CTkButton(self.frame_filtres, text="+ Prestation", command=self.ouvrir_fenetre_prestation).pack(side="left", padx=5)
        ctk.CTkButton(self.frame_filtres, text="+ Devis", command=self.lancer_creation_devis).pack(side="left", padx=5)
            
        # Treeview
        colonnes = ("ID", "Client", "Site", "Presta", "Qté", "Montant", "Date", "Début", "Fin", "État", "Commentaire")
        self.tree = ttk.Treeview(self.tab, columns=colonnes, show='headings')
        for col in colonnes:
            self.tree.heading(col, text=col)
            # Ajuste un peu les largeurs pour faire tenir le tout
            self.tree.column(col, width=90) 
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        # Actions bas de page
        self.frame_actions = ctk.CTkFrame(self.tab, fg_color="transparent")
        self.frame_actions.pack(fill="x", side="bottom", padx=10, pady=10)

        # Bas Gauche
        self.frame_gauche = ctk.CTkFrame(self.frame_actions, fg_color="transparent")
        self.frame_gauche.pack(side="left")
        ctk.CTkButton(self.frame_gauche, text="Afficher PDF", command=self.ouvrir_devis_pdf).pack(side="left", padx=5)
        ctk.CTkButton(self.frame_gauche, text="Dossier Client", command=self.ouvrir_dossier_client).pack(side="left", padx=5)

        # Bas Droite
        self.frame_droite = ctk.CTkFrame(self.frame_actions, fg_color="transparent")
        self.frame_droite.pack(side="right")
        self.btn_transf = ctk.CTkButton(self.frame_droite, text="Devis vers Prestation", command=self.transformer_devis)
        self.btn_transf.pack(side="left", padx=5)
        ctk.CTkButton(self.frame_droite, text="Modifier", command=self.modifier_prestation).pack(side="left", padx=5)
        ctk.CTkButton(self.frame_droite, text="Supprimer", command=self.supprimer_prestation, fg_color="red").pack(side="left", padx=5)

    def on_tree_select(self, event):
        selection = self.tree.selection()
        if selection:
            etat = self.tree.item(selection[0])['values'][8]
            self.btn_transf.configure(state="normal" if etat == "Devis" else "disabled")

    def rafraichir_treeview(self):
        data = database.recuperer_suivi_prestations()
        print(f"DEBUG: Nombre de lignes chargées dans Suivi: {len(data)}")
        for i in self.tree.get_children(): self.tree.delete(i)
        
        texte_recherche = self.search_entry.get().lower()
        masquer_payees = self.checkbox_masquer_payees.get()
        data = database.recuperer_suivi_prestations()
        for row in data: 
            if masquer_payees == 1 and row['etat'] == "Payée": continue
            if texte_recherche not in row['nom_societe'].lower(): continue
            
            # Gestion du site (si NULL, afficher "-")
            site = row['nom_site'] if row['nom_site'] else "-"
            # Gestion du commentaire (si NULL, afficher "")
            comment = row['commentaire'] if row['commentaire'] else ""
            
            montant = row['prix_final']

            self.tree.insert("", "end", values=(
                row['id'], row['nom_societe'], site, row['designation'], 
                f"{row['quantite']:.2f}", f"{montant:.2f} €", 
                row['date'], row['heure_debut'], row['heure_fin'], row['etat'], comment
            ))
            self.tree.update_idletasks()

    def transformer_devis(self):
        selected = self.tree.selection()
        if not selected: return
        
        values = self.tree.item(selected[0])['values']
        id_intervention = values[0]
        
        dialog = ctk.CTkToplevel(self.tab)
        dialog.title("Transformation Devis")
        dialog.geometry("300x500")
        dialog.grab_set()
        
        ctk.CTkLabel(dialog, text="Date de réalisation :").pack(pady=5)
        cal = DateEntry(dialog, width=12, date_pattern='dd-mm-yyyy')
        cal.pack(pady=5)
        
        # Heures... (tes combo existantes)
        ctk.CTkLabel(dialog, text="Heure de début :").pack(pady=5)
        frame_hd = ctk.CTkFrame(dialog, fg_color="transparent")
        frame_hd.pack()
        combo_hd = ctk.CTkComboBox(frame_hd, values=[f"{h:02d}" for h in range(24)], width=60)
        combo_hd.pack(side="left", padx=2)
        combo_md = ctk.CTkComboBox(frame_hd, values=[f"{m:02d}" for m in range(0, 60, 5)], width=60)
        combo_md.pack(side="left", padx=2)
        
        ctk.CTkLabel(dialog, text="Heure de fin :").pack(pady=5)
        frame_hf = ctk.CTkFrame(dialog, fg_color="transparent")
        frame_hf.pack()
        combo_hf = ctk.CTkComboBox(frame_hf, values=[f"{h:02d}" for h in range(24)], width=60)
        combo_hf.pack(side="left", padx=2)
        combo_mf = ctk.CTkComboBox(frame_hf, values=[f"{m:02d}" for m in range(0, 60, 5)], width=60)
        combo_mf.pack(side="left", padx=2)

        # NOUVEAU : Champ commentaire
        ctk.CTkLabel(dialog, text="Commentaire :").pack(pady=5)
        entry_comm = ctk.CTkEntry(dialog, width=200)
        entry_comm.pack(pady=5)
        
        def valider():
            date_c = cal.get_date().strftime("%Y-%m-%d")
            h_debut = f"{combo_hd.get()}:{combo_md.get()}"
            h_fin = f"{combo_hf.get()}:{combo_mf.get()}"
            comm = entry_comm.get()
            
            if database.transformer_devis_en_prestation(id_intervention, date_c, h_debut, h_fin, comm):
                dialog.destroy()
                self.rafraichir_treeview()
                messagebox.showinfo("Succès", "Devis transformé.")
        
        ctk.CTkButton(dialog, text="Valider", command=valider).pack(pady=20)

    def ouvrir_devis_pdf(self):
        selected = self.tree.selection()
        if not selected: return
        
        values = self.tree.item(selected[0])['values']
        id_technique = values[0]
        nom_original = values[1]
        
        # 1. On récupère le numéro EXACT stocké en BDD (ex: DEV-202607-01)
        numero_devis = database.recuperer_numero_devis(id_technique)
        
        # 2. On reconstruit le chemin
        nom_propre = "".join([c for c in nom_original if c.isalnum() or c in (' ', '_', '-')]).strip()
        dossier = os.path.join(get_base_path(), "Exports", nom_propre, "Devis")
        
        # On s'assure de chercher le fichier avec le bon format
        filename = os.path.join(dossier, f"Devis_{numero_devis}_{nom_propre}.pdf")
        
        if os.path.exists(filename):
            os.startfile(filename)
        else:
            messagebox.showerror("Erreur", f"Fichier introuvable :\n{filename}")
        
    def lancer_creation_devis(self):
        # Fenêtre de choix
        dialog = ctk.CTkToplevel(self.tab)
        dialog.title("Nouvelle opération")
        dialog.geometry("400x200")
        dialog.grab_set()
        
        ctk.CTkLabel(dialog, text="Avez-vous besoin de créer un nouveau client ?").pack(pady=20)
        
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack()
        
        # Bouton Oui : Redirige vers l'onglet Client
        ctk.CTkButton(btn_frame, text="Oui", command=lambda: self.rediriger_vers_clients(dialog)).pack(side="left", padx=10)
        # Bouton Non : Ouvre la fenêtre d'ajout
        ctk.CTkButton(btn_frame, text="Non", command=lambda: self.ouvrir_fenetre_ajout(dialog)).pack(side="left", padx=10)
           
    def rediriger_vers_clients(self, dialog):
        dialog.destroy()
        # On accède au parent (le Tabview) et on change l'onglet
        self.tab.master.set("Gestion des Clients")

    def ouvrir_fenetre_ajout(self, dialog):
        dialog.destroy()
        fenetre = FenetreAjout(self.tab, mode="devis")
        self.tab.wait_window(fenetre)
        self.rafraichir_treeview()
        
        
    def ouvrir_devis_pdf(self):
        selected = self.tree.selection()
        if not selected: return
        
        values = self.tree.item(selected[0])['values']
        id_technique = values[0]
        nom_original = values[1] 
        
        # 1. On récupère le numéro de devis réel (ex: 202606-01) via la BDD
        num_devis = database.recuperer_numero_devis(id_technique)
        
        # 2. On nettoie le nom du client (toujours nécessaire pour le chemin)
        nom_propre = "".join([c for c in nom_original if c.isalnum() or c in (' ', '_', '-')]).strip()
        
        # 3. Reconstitution du chemin avec le numéro de devis
        dossier = os.path.join(get_base_path(), "Exports", nom_propre, "Devis")
        filename = os.path.join(dossier, f"Devis_{num_devis}_{nom_propre}.pdf")
        
        if os.path.exists(filename):
            os.startfile(filename)
        else:
            messagebox.showerror("Erreur", f"Fichier introuvable :\n{filename}")
            
    def ouvrir_dossier_client(self):
        selected = self.tree.selection()
        if not selected: return
        
        values = self.tree.item(selected[0])['values']
        nom_original = values[1]
        
        # 1. Nettoyage du nom pour correspondre à la structure de dossiers créée
        nom_propre = "".join([c for c in nom_original if c.isalnum() or c in (' ', '_', '-')]).strip()
        
        # 2. Chemin du dossier client
        dossier = os.path.join(get_base_path(), "Exports", nom_propre)
        
        # 3. Vérification
        if os.path.exists(dossier):
            os.startfile(dossier)
        else:
            messagebox.showerror("Erreur", f"Le dossier est introuvable :\n{dossier}")
            
    def ouvrir_fenetre_prestation(self):
        fenetre = FenetreAjout(self.tab, mode="prestation")
        self.tab.wait_window(fenetre)
        self.rafraichir_treeview()

    def peut_modifier(self, etat):
        if etat in ["Facturée", "Payée"]:
            messagebox.showerror("Accès refusé", f"Action impossible : Prestation déjà {etat}.")
            return False
        if etat == "Réalisée":
            return messagebox.askyesno("Confirmation", "Attention, cette prestation est déjà marquée comme 'Réalisée'. Voulez-vous vraiment la modifier ?")
        return True # Autorisé pour Devis / En attente

    def supprimer_prestation(self):
        selected = self.tree.selection()
        if not selected: return
        
        values = self.tree.item(selected[0])['values']
        etat = values[7] # Index de l'état dans le Treeview
        
        if self.peut_modifier(etat):
            if messagebox.askyesno("Supprimer", "Confirmer la suppression ?"):
                database.supprimer_intervention(values[0]) # ID
                self.rafraichir_treeview()

    def modifier_prestation(self):
        # 1. Vérifier qu'une ligne est bien sélectionnée
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Attention", "Veuillez sélectionner une prestation à modifier.")
            return

        # 2. Récupérer les données de la ligne
        item = self.tree.item(selected[0])
        values = item['values']
        id_intervention = values[0]
        etat = values[7]

        # 3. Appliquer le garde-fou
        if self.peut_modifier(etat):
            # 4. Ouvrir la fenêtre de modification
            # On réutilise ta classe FenetreAjout, mais en mode "modification"
            # Tu devras peut-être adapter FenetreAjout pour accepter un ID
            fenetre = FenetreAjout(self.tab, mode="modification", id_intervention=id_intervention)
            self.tab.wait_window(fenetre)
            self.rafraichir_treeview()
