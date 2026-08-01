import customtkinter as ctk
import database
import os
from tkinter import filedialog, messagebox
from PIL import Image
import shutil

class ParametresTab:
    def __init__(self, tab):
        self.tab = tab
        self.logo_path = ""
        self.setup_ui()
        self.charger_donnees()

    def setup_ui(self):
        self.tab.configure(padx=20, pady=20)
        self.tab.grid_columnconfigure(1, weight=1)
        
        # Mapping des noms de champs vers les colonnes de la BDD
        self.champs_config = [
            ("Raison Sociale", "raison_sociale"), ("Adresse", "adresse"),
            ("Code Postal", "code_postal"), ("Ville", "ville"),
            ("Pays", "pays"), ("RCS", "rcs"),
            ("SIRET", "siret"), ("APE", "ape")
        ]
        
        self.entries = {}
        for i, (label_text, db_key) in enumerate(self.champs_config):
            ctk.CTkLabel(self.tab, text=label_text).grid(row=i, column=0, padx=10, pady=5, sticky="e")
            entry = ctk.CTkEntry(self.tab)
            entry.grid(row=i, column=1, padx=10, pady=5, sticky="ew")
            self.entries[db_key] = entry

        # --- Gestion TVA ---
        row_idx = len(self.champs_config)
        self.var_tva = ctk.BooleanVar()
        self.chk_tva = ctk.CTkCheckBox(self.tab, text="Exonération TVA (Art. 293 B)", 
                                       variable=self.var_tva, command=self.toggle_tva)
        self.chk_tva.grid(row=row_idx, column=1, padx=10, pady=10, sticky="w")

        row_idx += 1
        ctk.CTkLabel(self.tab, text="N° TVA Intra").grid(row=row_idx, column=0, padx=10, pady=5, sticky="e")
        self.entry_tva = ctk.CTkEntry(self.tab)
        self.entry_tva.grid(row=row_idx, column=1, padx=10, pady=5, sticky="ew")

        # --- Logo ---
        row_idx += 1
        ctk.CTkButton(self.tab, text="Choisir Logo", command=self.choisir_logo).grid(row=row_idx, column=1, padx=10, pady=5, sticky="w")
        
        row_idx += 1
        self.img_logo = ctk.CTkLabel(self.tab, text="Aucun logo")
        self.img_logo.grid(row=row_idx, column=1, padx=10, pady=5, sticky="w")

        # --- Mentions ---
        row_idx += 1
        self.txt_mentions = ctk.CTkTextbox(self.tab, height=80)
        self.txt_mentions.grid(row=row_idx, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        
        row_idx += 1
        ctk.CTkButton(self.tab, text="Enregistrer Paramètres", command=self.sauvegarder).grid(row=row_idx, column=0, columnspan=2, pady=20)

    def choisir_logo(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg")])
        if path:
            self.logo_path = path
            self.afficher_apercu(path)

    def afficher_apercu(self, path):
        if path and os.path.isfile(path):
            try:
                img = Image.open(path)
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(100, 50))
                self.img_logo.configure(image=ctk_img, text="")
            except Exception as e:
                print(f"Erreur image: {e}")
        else:
            self.img_logo.configure(image=None, text="Logo introuvable")

    def charger_donnees(self):
        data = database.recuperer_parametres()
        if data:
            # Remplissage des entries via les clés du dictionnaire (objet Row)
            for db_key, entry in self.entries.items():
                entry.insert(0, data[db_key] or "")
            
            self.var_tva.set(bool(data['tva_exoneree']))
            self.entry_tva.insert(0, data['num_tva'] or "")
            self.toggle_tva()
            
            self.logo_path = data['logo_path'] or ""
            if self.logo_path:
                self.afficher_apercu(self.logo_path)
            
            self.txt_mentions.insert("0.0", data['mentions_legales'] or "")

    def sauvegarder(self):
        # 1. Gestion du logo
        dossier_assets = r"C:\FacturEx\assets"
        if not os.path.exists(dossier_assets):
            os.makedirs(dossier_assets)
            
        nouveau_chemin = os.path.join(dossier_assets, "logo.png")
        
        # Si un nouveau logo a été sélectionné et qu'il est différent de l'actuel
        if self.logo_path and self.logo_path != nouveau_chemin:
            try:
                shutil.copy2(self.logo_path, nouveau_chemin)
                self.logo_path = nouveau_chemin # On met à jour le path vers le dossier assets
            except Exception as e:
                messagebox.showerror("Erreur", f"Impossible de copier le logo : {e}")
                return

        # 2. Reste de la sauvegarde
        data = {db_key: entry.get() for db_key, entry in self.entries.items()}
        data['tva_exoneree'] = int(self.var_tva.get())
        data['num_tva'] = self.entry_tva.get()
        data['logo_path'] = self.logo_path # On enregistre le chemin vers assets/logo.png
        data['mentions_legales'] = self.txt_mentions.get("0.0", "end").strip()
        
        database.sauvegarder_parametres(data)
        messagebox.showinfo("Succès", "Paramètres enregistrés !")

    def toggle_tva(self):
        state = "disabled" if self.var_tva.get() else "normal"
        self.entry_tva.configure(state=state)
