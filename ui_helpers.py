from nicegui import ui

def afficher_note_importante(titre, contenu_liste, tuto_titre=None, tuto_etapes=None):
    """Affiche une modale avec des points d'attention stylisés et un encadré bleu optionnel."""
    with ui.dialog() as dialog, ui.card().classes("w-[90vw] max-w-lg p-6 space-y-4"):
        ui.label(titre).classes("text-xl font-bold text-slate-800")
        ui.separator()
        
        # Points d'attention généraux avec un style plus punchy (couleur ambre/jaune)
        with ui.column().classes("gap-2"):
            for point in contenu_liste:
                with ui.row().classes("items-start gap-2"):
                    # Petit point ou icône colorée pour donner du punch
                    ui.icon("warning", color="amber", size="xs").classes("mt-1")
                    ui.label(point).classes("text-sm font-semibold text-amber-900")
                
        # Bloc tuto encadré sur fond bleu (s'il y en a un)
        if tuto_etapes:
            with ui.column().classes("w-full bg-blue-50 p-4 rounded-lg border border-blue-200 gap-2 mt-2"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("info", color="blue", size="sm")
                    ui.label(tuto_titre or "Tutoriel").classes("text-sm font-bold text-blue-900")
                
                with ui.column().classes("gap-1 pl-2"):
                    for etape in tuto_etapes:
                        ui.label(etape).classes("text-xs text-blue-800")
        
        ui.button("J'ai compris", on_click=dialog.close).props("color=primary w-full")
    dialog.open()