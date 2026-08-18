from nicegui import ui
import database
from ui_helpers import afficher_note_importante

def render_prestations():
    params = database.recuperer_parametres()
    entreprise_exoneree = bool(params.get("tva_exoneree", 1))

    with ui.row().classes("w-full justify-between items-center mb-6"):
        ui.label("Catalogue des Prestations").classes("text-2xl font-bold text-slate-800")
        ui.button("Infos Importantes", icon="warning", on_click=lambda: afficher_note_importante(
    "Points d'attention - Catalogue",
    [
        "La TVA est désactivée automatiquement si vous êtes en franchise en base (Micro-entreprise).",
        "Une fois une facture générée, les taux de TVA sont figés : vérifiez bien vos paramètres avant !",
        "L'unité (Heure/Forfait) doit être cohérente pour faciliter votre suivi de prestation plus tard.",
        "Une prestation modifiée ne rétroagit pas sur les factures déjà créées."
    ]
)).props("flat color=amber")

    with ui.card().classes("w-full p-6 bg-white border border-slate-200 rounded-xl space-y-6"):

        table_container = ui.column().classes("w-full")

        def rafraichir_liste():
            table_container.clear()
            
            conn = database.get_conn()
            rows = conn.execute("SELECT * FROM prestations ORDER BY designation ASC").fetchall()
            conn.close()

            prestations = []
            for r in rows:
                item = dict(r)
                item['prix_ht_txt'] = f"{item['prix_ht']:.2f} €"
                item['taux_tva_txt'] = f"{item['taux_tva']:.1f} %"
                prestations.append(item)

            columns = [
                {'name': 'designation', 'label': 'Désignation', 'field': 'designation', 'align': 'left', 'sortable': True},
                {'name': 'unite', 'label': 'Unité', 'field': 'unite', 'align': 'center', 'sortable': True},
                {'name': 'prix_ht_txt', 'label': 'Prix Unitaire HT', 'field': 'prix_ht_txt', 'align': 'right', 'sortable': True},
                {'name': 'taux_tva_txt', 'label': 'Taux TVA', 'field': 'taux_tva_txt', 'align': 'right', 'sortable': True},
            ]

            with table_container:
                with ui.row().classes("w-full justify-between items-center mb-4 gap-4"):
                    search_input = ui.input(placeholder="Rechercher une prestation...").props('dense outlined icon="search"').classes("w-72").props('id="step-catalogue-search"')
                    ui.button("Nouvelle Prestation", icon="add", on_click=lambda: ouvrir_dialogue_edition()).props("color=primary").props('id="step-catalogue-new"')

                if not prestations:
                    ui.label("Aucune prestation dans le catalogue pour le moment.").classes("text-slate-400 italic py-4")
                else:
                    grid = ui.table(columns=columns, rows=prestations, row_key='id', selection='single', pagination=10).classes("w-full cursor-pointer no-checkbox-table").props('id="step-catalogue-table"')
                    grid.props('flat borderless hide-selection-color')

                    search_input.on_value_change(lambda e: grid.set_filter(e.value))

                    # Badge stylisé pour l'unité
                    grid.add_slot('body-cell-unite', '''
                        <q-td :props="props">
                            <q-chip dense color="slate-2" text-color="slate-8">
                                {{ props.value }}
                            </q-chip>
                        </q-td>
                    ''')

                    # --- BARRE D'ACTIONS SOUS LE TABLEAU ---
                    actions_bar = ui.row().classes("w-full justify-between items-center p-4 bg-slate-50 border border-slate-200 rounded-xl mt-4 transition-all")
                    actions_bar.set_visibility(False)

                    label_selection = ui.label().classes("font-semibold text-slate-700")
                    buttons_container = ui.row().classes("gap-2 items-center")

                    def update_actions_bar():
                        if grid.selected:
                            prest_sel = grid.selected[0]
                            label_selection.set_text(f"Prestation sélectionnée : {prest_sel['designation']}")
                            
                            buttons_container.clear()
                            with buttons_container:
                                # Bouton Modifier
                                ui.button("Modifier", icon="edit", 
                                          on_click=lambda: ouvrir_dialogue_edition(prest_sel)).props("color=primary dense")

                                # Bouton Supprimer
                                ui.button("Supprimer", icon="delete", 
                                          on_click=lambda: confirmer_suppression(prest_sel['id'], prest_sel['designation'])).props("color=negative dense")

                            actions_bar.set_visibility(True)
                        else:
                            actions_bar.set_visibility(False)

                    # Sélection au clic sur la ligne
                    def on_row_click(e):
                        prest_row = e.args[1]
                        grid.selected.clear()
                        grid.selected.append(prest_row)
                        update_actions_bar()

                    grid.on('row-click', on_row_click)

                    with actions_bar:
                        label_selection
                        buttons_container

        # --- MODALE CRÉATION / ÉDITION PRESTATION ---
        def ouvrir_dialogue_edition(prestation=None):
            is_edit = prestation is not None
            titre = "Modifier la prestation" if is_edit else "Créer une prestation"

            with ui.dialog() as dialog, ui.card().classes("w-full max-w-md p-6 space-y-4"):
                ui.label(titre).classes("text-xl font-bold text-slate-800 border-b pb-2")

                desig_in = ui.input("Désignation *", value=prestation['designation'] if is_edit else "").classes("w-full")
                
                with ui.row().classes("w-full gap-4"):
                    unite_in = ui.select(
                        options=["Heure", "Jour", "Forfait", "Km", "Unité"], 
                        value=prestation['unite'] if is_edit else "Heure",
                        label="Unité"
                    ).classes("w-1/2").props("dense outlined")
                    
                    prix_in = ui.number("Prix HT (€) *", value=prestation['prix_ht'] if is_edit else 0.0, format="%.2f", precision=2).classes("w-1/2").props("dense outlined")

                options_tva = {
                    0.0: "0 % (Exonéré)",
                    5.5: "5.5 %",
                    10.0: "10 % (Déplacements / Spectacles)",
                    20.0: "20 % (Standard)"
                }
                
                valeur_tva_initiale = 0.0 if entreprise_exoneree else (prestation['taux_tva'] if is_edit else 20.0)

                tva_in = ui.select(
                    options=options_tva,
                    value=valeur_tva_initiale,
                    label="Taux de TVA par défaut"
                ).classes("w-full").props("dense outlined")

                if entreprise_exoneree:
                    tva_in.disable()
                    ui.label("Note : Votre entreprise est configurée en franchise de TVA (0%).").classes("text-xs text-amber-600 italic mt-1")

                def sauvegarder():
                    if not desig_in.value.strip():
                        ui.notify("Veuillez saisir une désignation.", type="warning")
                        return

                    taux_tva_final = 0.0 if entreprise_exoneree else float(tva_in.value or 0.0)

                    conn = database.get_conn()
                    cursor = conn.cursor()

                    if is_edit:
                        cursor.execute("""
                            UPDATE prestations 
                            SET designation=?, unite=?, prix_ht=?, taux_tva=?
                            WHERE id=?
                        """, (desig_in.value.strip(), unite_in.value, float(prix_in.value or 0.0), taux_tva_final, prestation['id']))
                        ui.notify("Prestation modifiée avec succès !", type="positive")
                    else:
                        cursor.execute("""
                            INSERT INTO prestations (designation, unite, prix_ht, taux_tva)
                            VALUES (?, ?, ?, ?)
                        """, (desig_in.value.strip(), unite_in.value, float(prix_in.value or 0.0), taux_tva_final))
                        ui.notify("Nouvelle prestation ajoutée au catalogue !", type="positive")

                    conn.commit()
                    conn.close()
                    dialog.close()
                    rafraichir_liste()

                with ui.row().classes("w-full justify-end gap-2 mt-4"):
                    ui.button("Annuler", on_click=dialog.close).props("flat color=slate")
                    ui.button("Enregistrer", icon="check", on_click=sauvegarder).props("color=primary")

            dialog.open()

        # --- SUPPRESSION PRESTATION ---
        def confirmer_suppression(prestation_id, designation):
            with ui.dialog() as dialog, ui.card().classes("p-6 space-y-4"):
                ui.label("Confirmer la suppression").classes("text-lg font-bold text-slate-800")
                ui.label(f"Voulez-vous vraiment supprimer la prestation « {designation} » ?").classes("text-slate-600")

                def supprimer():
                    conn = database.get_conn()
                    conn.execute("DELETE FROM prestations WHERE id=?", (prestation_id,))
                    conn.commit()
                    conn.close()
                    dialog.close()
                    ui.notify("Prestation supprimée.", type="info")
                    rafraichir_liste()

                with ui.row().classes("w-full justify-end gap-2"):
                    ui.button("Annuler", on_click=dialog.close).props("flat color=slate")
                    ui.button("Supprimer", color="negative", on_click=supprimer)

            dialog.open()

        rafraichir_liste()