import customtkinter as ctk
import database
# On importe nos modules
from ui_catalogue import CatalogueTab
from ui_clients import ClientsTab
from ui_prestations import PrestationsTab
from ui_factures import FacturesTab
from ui_parametres import ParametresTab
import os
# Force la création du dossier racine au démarrage
if not os.path.exists(r"C:\FacturEx\Exports"):
    os.makedirs(r"C:\FacturEx\Exports", exist_ok=True)

class FacturexApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("FacturEx - Gestion Pro")
        self.state('zoomed')
        
        # Initialisation de la BDD
        database.initialiser_bdd()
        
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=20)

        # Ajout des onglets métier
        # Initialisation des classes d'onglets
        self.catalogue = CatalogueTab(self.tabview.add("Catalogue des prestations"))
        self.clients = ClientsTab(self.tabview.add("Gestion des Clients"))
        
        # CORRECTION : Ne faire le add qu'une seule fois
        self.prestations = PrestationsTab(self.tabview.add("Suivi des Prestations"))
        
        self.factures = FacturesTab(self.tabview.add("Factures et Récaps"))
        self.factures.pack(fill="both", expand=True) # <--- C'est cette ligne qui manque !
        self.factures.prestations = self.prestations

        # Bouton Paramètres en bas à gauche
        self.btn_params = ctk.CTkButton(self, text="⚙️ Paramètres de l'entreprise", command=self.ouvrir_parametres)
        self.btn_params.pack(side="left", padx=20, pady=20)

    def ouvrir_parametres(self):
        # Création de la fenêtre Toplevel
        toplevel = ctk.CTkToplevel(self)
        toplevel.title("Configuration Entreprise")
        toplevel.geometry("500x700")
        toplevel.resizable(False, False)
        
        # Rendre la fenêtre modale (bloque l'accès à la fenêtre principale tant qu'elle est ouverte)
        toplevel.grab_set()
        
        # Initialisation de l'interface des paramètres dans la nouvelle fenêtre
        ParametresTab(toplevel)

if __name__ == "__main__":
    app = FacturexApp()
    app.mainloop()



