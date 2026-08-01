import customtkinter as ctk
from tkinter import ttk, messagebox
import database

class CatalogueTab:
    def __init__(self, tab):
        self.tab = tab
        self.selected_id = None
        # Accès par clé : 'tva_exoneree' (si c'est le nom de la colonne dans 'entreprise')
        params = database.recuperer_parametres()
        self.est_exonere = bool(params['tva_exoneree']) if params else True
        
        self.setup_ui()
        self.charger_donnees()

    def setup_ui(self):
        # --- Zone de saisie ---
        frame_input = ctk.CTkFrame(self.tab)
        frame_input.pack(fill="x", padx=10, pady=10)

        self.entry_designation = ctk.CTkEntry(frame_input, placeholder_text="Désignation")
        self.entry_designation.pack(side="left", padx=5)

        self.entry_prix = ctk.CTkEntry(frame_input, placeholder_text="Prix HT", width=80)
        self.entry_prix.pack(side="left", padx=5)

        self.entry_unite = ctk.CTkEntry(frame_input, placeholder_text="Unité", width=100)
        self.entry_unite.pack(side="left", padx=5)

        self.entry_tva = ctk.CTkEntry(frame_input, placeholder_text="TVA %", width=60)
        self.entry_tva.pack(side="left", padx=5)
        
        if self.est_exonere:
            self.entry_tva.insert(0, "0")
            self.entry_tva.configure(state="disabled")

        self.btn_save = ctk.CTkButton(frame_input, text="Ajouter", command=self.save_action)
        self.btn_save.pack(side="left", padx=5)

        # --- Tableau ---
        self.tree = ttk.Treeview(self.tab, columns=("ID", "Désignation", "Prix HT", "Unité", "TVA"), show='headings')
        for col in ["ID", "Désignation", "Prix HT", "Unité", "TVA"]:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.tree.bind("<<TreeviewSelect>>", self.remplir_champs)

        # --- Actions ---
        btn_frame = ctk.CTkFrame(self.tab, fg_color="transparent")
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="Supprimer", fg_color="red", command=self.supprimer_action).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Annuler/Nouveau", command=self.reset_form).pack(side="left", padx=5)

    def charger_donnees(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        # Accès par clé ici :
        for p in database.recuperer_toutes_les_prestations():
            self.tree.insert("", "end", values=(p['id'], p['designation'], p['prix_ht'], p['unite'], p['tva']))

    def remplir_champs(self, event):
        selected = self.tree.selection()
        if selected:
            vals = self.tree.item(selected[0])['values']
            self.selected_id = vals[0]
            self.entry_designation.delete(0, 'end'); self.entry_designation.insert(0, vals[1])
            self.entry_prix.delete(0, 'end'); self.entry_prix.insert(0, vals[2])
            self.entry_unite.delete(0, 'end'); self.entry_unite.insert(0, vals[3])
            if not self.est_exonere:
                self.entry_tva.delete(0, 'end'); self.entry_tva.insert(0, vals[4])
            self.btn_save.configure(text="Modifier")

    def save_action(self):
        designation = self.entry_designation.get()
        prix = self.entry_prix.get()
        unite = self.entry_unite.get()
        tva = self.entry_tva.get()
        
        if designation and prix:
            if self.selected_id:
                database.modifier_prestation(self.selected_id, designation, float(prix), unite, float(tva))
            else:
                database.ajouter_prestation(designation, float(prix), unite, float(tva))
            self.reset_form()
            self.charger_donnees()
        else:
            messagebox.showwarning("Erreur", "Veuillez remplir désignation et prix")

    def supprimer_action(self):
        if self.selected_id:
            database.supprimer_prestation(self.selected_id)
            self.reset_form()
            self.charger_donnees()

    def reset_form(self):
        self.selected_id = None
        self.entry_designation.delete(0, 'end')
        self.entry_prix.delete(0, 'end')
        self.entry_unite.delete(0, 'end')
        if not self.est_exonere:
            self.entry_tva.delete(0, 'end')
        self.btn_save.configure(text="Ajouter")
        try:
            self.tree.selection_remove(self.tree.selection())
        except:
            pass
