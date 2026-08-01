import customtkinter as ctk
import database
# On importe nos modules
from ui_catalogue import CatalogueTab
from ui_clients import ClientsTab
from ui_prestations import PrestationsTab
from ui_factures import FacturesTab
from ui_parametres import ParametresTab

class FacturexApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("FacturEx - Gestion Pro")
        self.state('zoomed')
        
        # Initialisation de la BDD
        database.initialiser_bdd()
        database.mise_a_jour_prix_historique()
        
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=20, pady=20)

        # Ajout des onglets métier
        self.tabview.add("Catalogue des prestations")
        self.tabview.add("Gestion des Clients")
        self.tabview.add("Suivi des Prestations")
        self.tabview.add("Factures et Récaps")

        # Initialisation des classes d'onglets
        self.catalogue = CatalogueTab(self.tabview.tab("Catalogue des prestations"))
        self.clients = ClientsTab(self.tabview.tab("Gestion des Clients"))
        self.prestations = PrestationsTab(self.tabview.tab("Suivi des Prestations"))
        self.factures = FacturesTab(self.tabview.tab("Factures et Récaps"))

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



