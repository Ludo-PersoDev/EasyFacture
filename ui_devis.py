from datetime import datetime, timedelta
import os
import subprocess
import sys
import database
import pdf_generator
from nicegui import ui
import utils
import sys
import codecs

if sys.stdout.encoding != 'utf-8':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    
def formater_date_fr(date_str):
  """Convertit AAAA-MM-JJ en JJ/MM/AAAA pour l'affichage."""
  if not date_str:
    return ""
  try:
    d = datetime.strptime(str(date_str).strip(), "%Y-%m-%d")
    return d.strftime("%d/%m/%Y")
  except Exception:
    return str(date_str)


def render_devis():
  ui.label("Gestion des Devis").classes(
      "text-2xl font-bold text-slate-800 mb-6"
  )

  with ui.card().classes(
      "w-full p-6 bg-white border border-slate-200 rounded-xl space-y-4"
  ):

    # ESTHÉTIQUE & FILTRES EN HAUT
    top_bar = ui.row().classes(
        "w-full justify-between items-center mb-2 gap-4 flex-wrap"
    )

    selection_holder = {"selected_row": None}

    # Colonnes AG Grid
    columns = [
        {
            "headerName": "N° Devis",
            "field": "numero_devis",
            "align": "left",
            "sortable": True,
            "filter": "agTextColumnFilter",
        },
        {
            "headerName": "Client",
            "field": "nom_societe",
            "align": "left",
            "sortable": True,
            "filter": "agTextColumnFilter",
        },
        {
            "headerName": "Émission",
            "field": "date_creation_fr",
            "align": "center",
            "sortable": True,
            "filter": "agDateColumnFilter",
        },
        {
            "headerName": "Échéance",
            "field": "date_validite_fr",
            "align": "center",
            "sortable": True,
        },
        {
            "headerName": "Total HT",
            "field": "total_ht_txt",
            "align": "right",
            "sortable": True,
        },
        {
            "headerName": "Total TTC",
            "field": "total_ttc_txt",
            "align": "right",
            "sortable": True,
        },
        {
            "headerName": "Statut",
            "field": "statut",
            "align": "center",
            "sortable": True,
            "filter": "agTextColumnFilter",
            "cellClassRules": {
                (
                    "bg-slate-100 text-slate-700 font-bold border-slate-300"
                ): 'x === "Brouillon"',
                (
                    "bg-blue-100 text-blue-800 font-bold border-blue-300"
                ): 'x === "Envoyé"',
                (
                    "bg-emerald-100 text-emerald-800 font-bold"
                    " border-emerald-300"
                ): 'x === "Accepté"',
                (
                    "bg-red-100 text-red-800 font-bold border-red-300"
                ): 'x === "Refusé"',
            },
        },
    ]

    # Tableau fixe (créé une seule fois)
    grid = ui.aggrid({
        "columnDefs": columns,
        "rowData": [],
        "rowSelection": "single",
        "pagination": True,
        "paginationPageSize": 12,
        "defaultColDef": {"resizable": True, "sortable": True, "filter": True},
    }).classes("h-96 w-full cursor-pointer")

    # BARRE D'ACTIONS EN BAS
    with ui.row().classes(
        "w-full justify-between items-center pt-3 border-t border-slate-200"
        " min-h-[48px]"
    ):
      action_label = ui.label(
          "💡 Cliquez sur une ligne du tableau pour interagir."
      ).classes("text-xs text-slate-400 font-medium italic py-1")

      with ui.row().classes("items-center gap-2 flex-wrap") as action_buttons:
        btn_print = ui.button(
            "Voir PDF", icon="picture_as_pdf", on_click=lambda: tenter_impression()
        ).props("dense color=primary font-bold")
        btn_email = ui.button(
            "Envoyer", icon="send", on_click=lambda: tenter_envoi_email()
        ).props("dense outline color=info font-bold")
        btn_convertir = ui.button(
            "Convertir en Prestation",
            icon="event_available",
            on_click=lambda: tenter_conversion(),
        ).props("dense color=positive font-bold")
        btn_editer = ui.button(
            "Éditer", icon="edit", on_click=lambda: tenter_edition()
        ).props("dense outline color=primary font-bold")
        btn_refuser = ui.button(
            "Refuser", icon="cancel", on_click=lambda: tenter_refus()
        ).props("dense flat color=warning font-bold")
        btn_supprimer = ui.button(
            "Supprimer", icon="delete", on_click=lambda: tenter_suppression()
        ).props("dense flat color=negative font-bold")

        # Masqués par défaut
        for btn in [
            btn_print,
            btn_email,
            btn_convertir,
            btn_editer,
            btn_refuser,
            btn_supprimer,
        ]:
          btn.set_visibility(False)

    def update_action_bar():
      selected = selection_holder["selected_row"]
      if selected:
        num = selected.get("numero_devis", "")
        statut = selected.get("statut", "")

        action_label.set_text(f"Devis sélectionné : {num} ({statut})")
        action_label.classes(
            replace=(
                "text-sm font-bold text-slate-700 bg-slate-100 px-3 py-1.5"
                " rounded-lg border border-slate-200"
            )
        )

        # Toujours possible d'imprimer / supprimer
        btn_print.set_visibility(True)
        btn_supprimer.set_visibility(True)

        # Visibilité contextuelle
        btn_email.set_visibility(statut == "Brouillon")
        btn_convertir.set_visibility(statut not in ["Accepté", "Refusé"])
        btn_editer.set_visibility(statut not in ["Accepté", "Refusé"])
        btn_refuser.set_visibility(statut not in ["Accepté", "Refusé"])
      else:
        action_label.set_text(
            "💡 Cliquez sur une ligne du tableau pour interagir."
        )
        action_label.classes(
            replace="text-xs text-slate-400 font-medium italic py-1"
        )
        for btn in [
            btn_print,
            btn_email,
            btn_convertir,
            btn_editer,
            btn_refuser,
            btn_supprimer,
        ]:
          btn.set_visibility(False)

    def on_cell_clicked(e):
      data = e.args.get("data")
      if data:
        selection_holder["selected_row"] = data
        update_action_bar()

    grid.on("cellClicked", on_cell_clicked)

    def charger_donnees():
      selection_holder["selected_row"] = None
      update_action_bar()

      filtre_statut = select_statut.value
      filtre_client = select_client.value

      conn = database.get_conn()
      try:
        query = """
                    SELECT d.*, c.nom_societe, c.email as client_email
                    FROM devis d
                    JOIN clients c ON d.client_id = c.id
                    ORDER BY d.id DESC
                """
        rows = conn.execute(query).fetchall()
      finally:
        conn.close()

      devis_list = []
      for r in rows:
        item = dict(r)
        item["date_creation_fr"] = formater_date_fr(item["date_creation"])
        item["date_validite_fr"] = formater_date_fr(item["date_validite"])
        item["total_ht_txt"] = f"{(item['total_ht'] or 0.0):.2f} €"
        item["total_ttc_txt"] = f"{(item['total_ttc'] or 0.0):.2f} €"

        if filtre_statut != "Tous" and item["statut"] != filtre_statut:
          continue
        if (
            filtre_client != "Tous"
            and str(item["client_id"]) != str(filtre_client)
        ):
          continue

        devis_list.append(item)

      grid.options["rowData"] = devis_list
      grid.update()

    # BARRE DU HAUT (FILTRES + CRÉATION)
    with top_bar:
      with ui.row().classes("items-center gap-4 flex-wrap flex-1"):
        ui.label("Devis").classes("text-lg font-semibold text-slate-700")

        select_statut = ui.select(
            ["Tous", "Brouillon", "Envoyé", "Accepté", "Refusé"],
            value="Tous",
            label="Filtrer par Statut",
        ).classes("w-44")

        clients_list = database.recuperer_tous_les_clients()
        client_filter_opts = {"Tous": "Tous les clients"}
        client_filter_opts.update(
            {str(c["id"]): c["nom_societe"] for c in clients_list}
        )

        select_client = ui.select(
            client_filter_opts, value="Tous", label="Filtrer par Client"
        ).classes("w-52")

        select_statut.on_value_change(lambda _: charger_donnees())
        select_client.on_value_change(lambda _: charger_donnees())

      ui.button(
          "Créer un Devis",
          icon="add",
          on_click=lambda: ouvrir_dialogue_devis(),
      ).props("color=primary font-bold")

    # --- ACTIONS DE LA BARRE DYNAMIQUE ---
    def tenter_impression():
      d = selection_holder["selected_row"]
      if not d:
        return
      
      try:
        dossier_export = pdf_generator.obtenir_chemin_export(
            d["nom_societe"], type_doc="Devis"
        )
        os.makedirs(dossier_export, exist_ok=True)
        filename = f"Devis_{d['numero_devis']}.pdf"
        pdf_path = os.path.join(dossier_export, filename)

        pdf_generator.generer_pdf_devis(d["id"], pdf_path)

        if os.path.exists(pdf_path):
          dossier_export_base = os.path.join(os.getcwd(), "Export")
          rel_path = os.path.relpath(pdf_path, dossier_export_base).replace(
              "\\", "/"
          )
          pdf_url = f"/pdf/{rel_path}"

          with ui.dialog() as viewer_dialog, ui.card().classes(
              "w-[80vw] !max-w-[80vw] h-[85vh] p-4 flex flex-col"
          ):
            with ui.row().classes("w-full justify-between items-center mb-2"):
              ui.label(filename).classes("font-bold text-slate-700 text-base")
              ui.button(
                  icon="close", on_click=viewer_dialog.close
              ).props("flat dense")
            ui.element("iframe").props(f'src="{pdf_url}"').classes(
                "w-full flex-grow border-0 rounded-lg"
            )
          viewer_dialog.open()
        else:
          ui.notify(
              "Erreur : Impossible de generer ou trouver le PDF du devis.",
              type="negative",
          )
      except Exception as e:
        ui.notify(f"Erreur lors de l'affichage du devis : {str(e)}", type="negative")

    def tenter_envoi_email():
      d = selection_holder["selected_row"]
      if not d:
        return
      ouvrir_dialogue_envoi_email(d)

    def tenter_conversion():
      d = selection_holder["selected_row"]
      if not d:
        return
      convertir_devis_en_prestation(d["id"], d["numero_devis"])

    def tenter_edition():
      d = selection_holder["selected_row"]
      if not d:
        return
      ouvrir_dialogue_devis(devis_id=d["id"])

    def tenter_refus():
      d = selection_holder["selected_row"]
      if not d:
        return
      conn = database.get_conn()
      try:
        conn.execute("UPDATE devis SET statut='Refusé' WHERE id=?", (d["id"],))
        conn.commit()
      finally:
        conn.close()
      ui.notify(f"Devis {d['numero_devis']} marqué comme Refusé.", type="warning")
      charger_donnees()

    def tenter_suppression():
      d = selection_holder["selected_row"]
      if not d:
        return
      confirmer_suppression(d["id"], d["numero_devis"])

    # --- DIALOGUE CRÉATION / ÉDITION DEVIS (RÉORGANISÉ) ---
    def ouvrir_dialogue_devis(devis_id=None):
      is_edit = devis_id is not None
      conn = database.get_conn()
      try:
        clients_rows = conn.execute(
            "SELECT id, nom_societe, sans_tva FROM clients ORDER BY nom_societe"
            " ASC"
        ).fetchall()
        clients_dict = {c["id"]: c["nom_societe"] for c in clients_rows}
        clients_tva_map = {c["id"]: bool(c["sans_tva"]) for c in clients_rows}

        params = database.recuperer_parametres()
        entreprise_exoneree = bool(params.get("tva_exoneree", 1))

        if not clients_dict:
          ui.notify(
              "Veuillez d'abord enregistrer au moins un client.", type="warning"
          )
          return

        devis_data = None
        items_data = []
        if is_edit:
          devis_data = dict(
              conn.execute(
                  "SELECT * FROM devis WHERE id=?", (devis_id,)
              ).fetchone()
          )
          items_data = [
              dict(r)
              for r in conn.execute(
                  "SELECT * FROM devis_items WHERE devis_id=?", (devis_id,)
              ).fetchall()
          ]
      finally:
        conn.close()

      statut_actuel = devis_data["statut"] if is_edit else "Brouillon"

      dialog = ui.dialog()
      with dialog, ui.card().classes("w-full max-w-6xl p-6 space-y-4"):
        titre = (
            f"Modifier Devis {devis_data['numero_devis']}"
            if is_edit
            else "Créer un Devis"
        )

        with ui.row().classes("w-full justify-between items-center border-b pb-2"):
          ui.label(titre).classes("text-xl font-bold text-slate-800")
          ui.badge(statut_actuel).props("color=blue outline font-bold").classes(
              "text-sm p-2"
          )

        with ui.row().classes("w-full gap-6 items-start"):

          with ui.column().classes("w-96 gap-4"):
            ui.label("Paramètres & Client").classes(
                "text-xs font-bold text-slate-500 uppercase"
            )

            client_select = ui.select(
                options=clients_dict,
                value=(
                    devis_data["client_id"]
                    if is_edit
                    else list(clients_dict.keys())[0]
                ),
                label="Client *",
            ).classes("w-full")

            with ui.row().classes("w-full gap-2"):
              date_crea_val = (
                  devis_data["date_creation"]
                  if is_edit
                  else datetime.now().strftime("%Y-%m-%d")
              )
              date_crea = ui.input(
                  "Date d'émission", value=date_crea_val
              ).props("readonly dense outlined").classes("flex-1 bg-slate-50")

              duree_options = {
                  15: "15 jours",
                  30: "1 mois",
                  60: "2 mois",
                  90: "3 mois",
              }
              duree_select = ui.select(
                  options=duree_options, value=30, label="Validité"
              ).props("dense outlined").classes("w-28")

            with ui.row().classes("w-full gap-2"):
              date_val_defaut = (
                  devis_data["date_validite"]
                  if is_edit
                  else (datetime.now() + timedelta(days=30)).strftime(
                      "%Y-%m-%d"
                  )
              )
              date_val = ui.input("Date d'échéance", value=date_val_defaut).props(
                  "readonly dense outlined"
              ).classes("flex-1 bg-slate-50")

              date_exec_val = (
                  devis_data["date_prevue_execution"] if is_edit else ""
              )
              date_exec = ui.input(
                  "Exécution prévue", value=date_exec_val
              ).props("dense outlined").classes("flex-1")
              with date_exec:
                with ui.menu() as menu_cal:
                  ui.date().bind_value(date_exec)
                with date_exec.add_slot("append"):
                  ui.icon("event").classes("cursor-pointer").on(
                      "click", menu_cal.open
                  )

            def recalculer_echeance(e):
              try:
                dt_crea = datetime.strptime(date_crea.value, "%Y-%m-%d")
                dt_val = dt_crea + timedelta(days=int(e.value))
                date_val.value = dt_val.strftime("%Y-%m-%d")
              except Exception:
                pass

            duree_select.on_value_change(recalculer_echeance)
            remarque_in = ui.textarea(
                "Remarques / Conditions particulières",
                value=devis_data["remarque"] if is_edit else "",
            ).classes("w-full mt-2")

          with ui.column().classes("flex-1 gap-4"):
            ui.label("Lignes du Devis & Totaux").classes(
                "text-xs font-bold text-slate-500 uppercase"
            )

            lignes_container = ui.column().classes(
                "w-full space-y-2 max-h-72 overflow-y-auto pr-1"
            )
            lignes_state = []

            with ui.row().classes(
                "w-full justify-between items-center p-4 bg-slate-50 border"
                " border-slate-200 rounded-xl mt-2"
            ):
              with ui.column().classes("gap-0"):
                ui.label("Total HT :").classes(
                    "text-xs text-slate-500 uppercase font-bold"
                )
                lbl_total_ht = ui.label("0.00 €").classes(
                    "font-bold text-base text-slate-800"
                )

              with ui.column().classes("gap-0"):
                ui.label("Total TVA :").classes(
                    "text-xs text-slate-500 uppercase font-bold"
                )
                lbl_total_tva = ui.label("0.00 €").classes(
                    "text-sm text-slate-600"
                )

              with ui.column().classes("gap-0 items-end"):
                ui.label("Total TTC :").classes(
                    "text-xs text-slate-500 uppercase font-bold"
                )
                lbl_total_ttc = ui.label("0.00 €").classes(
                    "font-extrabold text-xl text-primary"
                )

        def calculer_totaux():
          tot_ht = 0.0
          tot_tva = 0.0
          client_id = client_select.value
          client_exonere = clients_tva_map.get(client_id, False)
          is_exo = entreprise_exoneree or client_exonere

          for line in lignes_state:
            qte = float(line["qte"].value or 0.0)
            pu = float(line["pu"].value or 0.0)
            taux_tva = (
                float(line["tva"].value or 0.0) if not is_exo else 0.0
            )

            line_ht = qte * pu
            line_tva = 0.0 if is_exo else line_ht * (taux_tva / 100.0)

            tot_ht += line_ht
            tot_tva += line_tva

          tot_ttc = tot_ht + tot_tva
          lbl_total_ht.set_text(f"{tot_ht:.2f} €")
          lbl_total_tva.set_text(f"{tot_tva:.2f} €")
          lbl_total_ttc.set_text(f"{tot_ttc:.2f} €")

        def ajouter_ligne(item_initial=None):
          client_id = client_select.value
          client_exonere = clients_tva_map.get(client_id, False)
          is_exo = entreprise_exoneree or client_exonere

          conn = database.get_conn()
          try:
            query = """
                            SELECT p.id, p.designation, p.unite, p.taux_tva,
                                   COALESCE(ct.prix_specifique_ht, p.prix_ht) as prix_effectif,
                                   COALESCE(ct.est_actif, 1) as est_actif
                            FROM prestations p
                            LEFT JOIN client_tarifs ct ON p.id = ct.prestation_id AND ct.client_id = ?
                            WHERE COALESCE(ct.est_actif, 1) = 1
                            ORDER BY p.designation ASC
                        """
            prestations = conn.execute(query, (client_id,)).fetchall()
          finally:
            conn.close()

          if not prestations:
            ui.notify(
                "Aucune prestation disponible pour ce client.", type="warning"
            )
            return

          p_options = {
              p["id"]: f"{p['designation']} ({p['prix_effectif']:.2f} €)"
              for p in prestations
          }
          p_details = {p["id"]: p for p in prestations}

          with lignes_container:
            with ui.row().classes(
                "w-full items-center gap-2 p-2 bg-slate-50 border rounded-lg"
            ) as row_element:
              p_sel = ui.select(
                  options=p_options,
                  value=(
                      item_initial["prestation_id"]
                      if item_initial
                      else prestations[0]["id"]
                  ),
                  label="Prestation",
              ).classes("flex-1").props("dense outlined")

              qte_in = ui.number(
                  label="Qté",
                  value=item_initial["quantite"] if item_initial else 1.0,
                  format="%.2f",
              ).classes("w-20").props("dense outlined")

              pu_in = ui.number(
                  label="Prix HT (€)",
                  value=(
                      item_initial["prix_unitaire_ht"]
                      if item_initial
                      else prestations[0]["prix_effectif"]
                  ),
                  format="%.2f",
              ).classes("w-28").props("dense outlined")

              valeur_tva_init = (
                  0.0
                  if is_exo
                  else (
                      item_initial["taux_tva"]
                      if item_initial
                      else prestations[0]["taux_tva"]
                  )
              )
              tva_in = ui.select(
                  options={0.0: "0%", 5.5: "5.5%", 10.0: "10%", 20.0: "20%"},
                  value=valeur_tva_init,
                  label="TVA",
              ).classes("w-24").props("dense outlined")

              if is_exo:
                tva_in.props("disable")

              btn_del = ui.button(icon="delete", color="negative").props(
                  "flat round dense"
              )

              line_obj = {
                  "row": row_element,
                  "prest": p_sel,
                  "qte": qte_in,
                  "pu": pu_in,
                  "tva": tva_in,
              }
              lignes_state.append(line_obj)

              def on_prestation_change(e, pu_field=pu_in, tva_field=tva_in):
                selected_p = p_details.get(e.value)
                if selected_p:
                  pu_field.value = selected_p["prix_effectif"]
                  tva_field.value = 0.0 if is_exo else selected_p["taux_tva"]
                calculer_totaux()

              def supprimer_ligne(obj=line_obj):
                lignes_container.remove(obj["row"])
                lignes_state.remove(obj)
                calculer_totaux()

              p_sel.on_value_change(on_prestation_change)
              qte_in.on_value_change(lambda _: calculer_totaux())
              pu_in.on_value_change(lambda _: calculer_totaux())
              tva_in.on_value_change(lambda _: calculer_totaux())
              btn_del.on_click(supprimer_ligne)

          calculer_totaux()

        def on_client_change(e):
          lignes_container.clear()
          lignes_state.clear()
          ajouter_ligne()

        client_select.on_value_change(on_client_change)

        ui.button(
            "Ajouter une prestation",
            icon="add",
            on_click=lambda: ajouter_ligne(),
        ).props("color=emerald outline dense").classes("mt-1")

        if is_edit and items_data:
          for item in items_data:
            ajouter_ligne(item)
        else:
          ajouter_ligne()

        def sauvegarder():
          if not lignes_state:
            ui.notify(
                "Veuillez ajouter au moins une ligne au devis.", type="warning"
            )
            return

          tot_ht = 0.0
          tot_tva = 0.0
          client_exonere = clients_tva_map.get(client_select.value, False)
          is_exo = entreprise_exoneree or client_exonere

          for line in lignes_state:
            qte = float(line["qte"].value or 0.0)
            pu = float(line["pu"].value or 0.0)
            taux_tva = 0.0 if is_exo else float(line["tva"].value or 0.0)

            line_ht = qte * pu
            line_tva = 0.0 if is_exo else line_ht * (taux_tva / 100.0)

            tot_ht += line_ht
            tot_tva += line_tva

          tot_ttc = tot_ht + tot_tva

          conn = database.get_conn()
          try:
            cursor = conn.cursor()
            if is_edit:
              num_devis = devis_data["numero_devis"]
              cursor.execute(
                  """
                                UPDATE devis SET
                                    client_id=?, date_creation=?, date_validite=?, date_prevue_execution=?,
                                    statut=?, total_ht=?, total_tva=?, total_ttc=?, remarque=?
                                WHERE id=?
                            """,
                  (
                      client_select.value,
                      date_crea.value,
                      date_val.value,
                      date_exec.value,
                      statut_actuel,
                      tot_ht,
                      tot_tva,
                      tot_ttc,
                      remarque_in.value,
                      devis_id,
                  ),
              )
              cursor.execute(
                  "DELETE FROM devis_items WHERE devis_id=?", (devis_id,)
              )
              target_devis_id = devis_id
            else:
              num_devis = database.generer_numero_document("DEV")
              cursor.execute(
                  """
                                INSERT INTO devis (
                                    numero_devis, client_id, date_creation, date_validite, date_prevue_execution,
                                    statut, total_ht, total_tva, total_ttc, remarque
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                  (
                      num_devis,
                      client_select.value,
                      date_crea.value,
                      date_val.value,
                      date_exec.value,
                      "Brouillon",
                      tot_ht,
                      tot_tva,
                      tot_ttc,
                      remarque_in.value,
                  ),
              )
              target_devis_id = cursor.lastrowid

            for line in lignes_state:
              taux_tva_sauvegarder = (
                  0.0 if is_exo else float(line["tva"].value or 0.0)
              )
              cursor.execute(
                  """
                                INSERT INTO devis_items (devis_id, prestation_id, quantite, prix_unitaire_ht, taux_tva)
                                VALUES (?, ?, ?, ?, ?)
                            """,
                  (
                      target_devis_id,
                      line["prest"].value,
                      float(line["qte"].value or 0.0),
                      float(line["pu"].value or 0.0),
                      taux_tva_sauvegarder,
                  ),
              )

            conn.commit()
          finally:
            conn.close()

          ui.notify(f"Devis {num_devis} enregistré !", type="positive")
          dialog.close()
          charger_donnees()

        with ui.row().classes("w-full justify-end gap-2 mt-4 pt-2 border-t"):
          ui.button("Annuler", on_click=dialog.close).props("flat color=slate")
          ui.button(
              "Enregistrer le devis", icon="check", on_click=sauvegarder
          ).props("color=primary font-bold")

      dialog.open()

    # --- ENVOI PAR EMAIL ---
    def ouvrir_dialogue_envoi_email(devis):
      conn = database.get_conn()
      try:
        client = conn.execute(
            "SELECT nom_societe, email FROM clients WHERE id=?",
            (devis["client_id"],),
        ).fetchone()
      finally:
        conn.close()

      email_client = client["email"] if client else ""
      if not email_client:
        ui.notify(
            "Attention : Ce client n'a pas d'adresse e-mail renseignée !",
            type="warning",
            icon="warning",
        )
        return

      dialog = ui.dialog()
      with dialog, ui.card().classes("w-full max-w-md p-6 space-y-4"):
        ui.label(f"Envoyer le Devis {devis['numero_devis']}").classes(
            "text-xl font-bold text-slate-800"
        )
        ui.label(
            f"Le devis sera envoyé à : {client['nom_societe']}"
            f" ({email_client})"
        ).classes("text-sm text-slate-600")

        def confirmer_envoi():
          dossier_export = pdf_generator.obtenir_chemin_export(
              client["nom_societe"], type_doc="Devis"
          )
          filename = f"Devis_{devis['numero_devis']}.pdf"
          pdf_path = os.path.join(dossier_export, filename)
          pdf_generator.generer_pdf_devis(devis["id"], pdf_path)

          succes, message = utils.envoyer_email_devis(
              email_destinataire=email_client,
              nom_client=client["nom_societe"],
              num_devis=devis["numero_devis"],
              montant_ttc=devis["total_ttc"],
              pdf_path=pdf_path,
          )

          if succes:
            conn_e = database.get_conn()
            try:
              conn_e.execute(
                  "UPDATE devis SET statut='Envoyé' WHERE id=?", (devis["id"],)
              )
              conn_e.commit()
            finally:
              conn_e.close()

            ui.notify(
                f"Devis {devis['numero_devis']} envoyé !",
                type="positive",
                icon="send",
            )
            dialog.close()
            charger_donnees()
          else:
            ui.notify(message, type="negative")

        with ui.row().classes("w-full justify-end gap-2 mt-4"):
          ui.button("Annuler", on_click=dialog.close).props("flat color=slate")
          ui.button(
              "Envoyer par E-mail", icon="send", on_click=confirmer_envoi
          ).props("color=primary font-bold")

      dialog.open()

    # --- SUPPRESSION ---
    def confirmer_suppression(devis_id, num_devis):
      dialog = ui.dialog()
      with dialog, ui.card().classes("p-6 space-y-4 max-w-md"):
        ui.label("Confirmer la suppression").classes(
            "text-lg font-bold text-slate-800"
        )
        ui.label(
            f"Voulez-vous supprimer définitivement le devis « {num_devis} » ?"
        ).classes("text-slate-600")

        def supprimer():
          conn = database.get_conn()
          try:
            conn.execute("DELETE FROM devis WHERE id=?", (devis_id,))
            conn.commit()
          finally:
            conn.close()
          dialog.close()
          ui.notify("Devis supprimé.", type="info")
          charger_donnees()

        with ui.row().classes("w-full justify-end gap-2"):
          ui.button("Annuler", on_click=dialog.close).props("flat color=slate")
          ui.button("Supprimer", on_click=supprimer).props(
              "color=negative font-bold"
          )

      dialog.open()

    # Chargement initial des données
    charger_donnees()