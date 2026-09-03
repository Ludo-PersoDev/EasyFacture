<template>
  <div class="page-container">
    <!-- En-tête -->
    <div class="header-card">
      <div>
        <h1 class="page-title">Gestion des Devis</h1>
        <p class="page-subtitle">Suivi, édition, conversion et export des devis clients.</p>
      </div>
      
      <button @click="ouvrirModalCreation()" class="btn-primary-clean">
        <span class="material-icons text-sm">add</span> Créer un Devis
      </button>
    </div>

    <!-- Filtres & Liste -->
    <div class="content-card">
      <div class="filters-row">
        <div class="input-group filter-group">
          <label>Filtrer par Statut</label>
          <select v-model="filtreStatut" @change="chargerDevis" class="input-field">
            <option value="Tous">Tous les statuts</option>
            <option value="Brouillon">Brouillon</option>
            <option value="Envoyé">Envoyé</option>
            <option value="Validé">Validé</option>
            <option value="Accepté">Accepté</option>
            <option value="Refusé">Refusé</option>
          </select>
        </div>

        <div class="input-group filter-group">
          <label>Filtrer par Client</label>
          <select v-model="filtreClient" @change="chargerDevis" class="input-field">
            <option value="Tous">Tous les clients</option>
            <option v-for="client in clientsList" :key="client.id" :value="client.id">
              {{ client.nom_societe }}
            </option>
          </select>
        </div>
      </div>

      <div v-if="loading" class="loading-state">
        Chargement des devis...
      </div>

      <div v-else-if="devisList.length === 0" class="empty-state">
        Aucun devis trouvé.
      </div>

      <!-- VUE DESKTOP -->
      <div v-else class="desktop-table-view">
        <table class="data-table">
          <thead>
            <tr>
              <th>N° Devis</th>
              <th>Client</th>
              <th>Émission</th>
              <th>Échéance</th>
              <th class="text-right">Total HT</th>
              <th class="text-right">Total TTC</th>
              <th class="text-center">Statut</th>
              <th class="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="devis in devisList" :key="devis.id" class="clickable-row">
              <td class="font-mono font-medium text-slate-900">{{ devis.numero_devis }}</td>
              <td class="font-medium text-slate-900">{{ devis.clients?.nom_societe || 'Client inconnu' }}</td>
              <td>{{ formaterDate(devis.date_creation) }}</td>
              <td>{{ formaterDate(devis.date_validite) }}</td>
              <td class="text-right font-mono">{{ Number(devis.total_ht || 0).toFixed(2) }} €</td>
              <td class="text-right font-mono font-bold text-slate-900">{{ Number(devis.total_ttc || 0).toFixed(2) }} €</td>
              <td class="text-center">
                <span :class="badgeStatutClass(devis.statut)" class="badge-statut">
                  {{ devis.statut }}
                </span>
              </td>
              <td class="text-right">
                <div class="action-buttons">
                  <button @click="afficherPdf(devis)" class="icon-action-btn text-blue-600 hover:bg-blue-50" title="Afficher le PDF">
                    <span class="material-icons text-sm">visibility</span>
                  </button>

                  <button v-if="devis.statut === 'Brouillon' || devis.statut === 'Envoyé'" @click="validerEtTransformerDevis(devis)" class="icon-action-btn text-emerald-600 hover:bg-emerald-50" title="Valider le Devis (Passer en Validé & Transférer)">
                    <span class="material-icons text-sm">check_circle</span>
                  </button>

                  <button @click="envoyerParMailDirect(devis)" class="icon-action-btn text-emerald-600 hover:bg-emerald-50" title="Envoyer par mail (SMTP)">
                    <span class="material-icons text-sm">mail</span>
                  </button>

                  <button v-if="devis.statut === 'Brouillon'" @click="editerDevis(devis)" class="icon-action-btn text-amber-600 hover:bg-amber-50" title="Éditer le devis">
                    <span class="material-icons text-sm">edit</span>
                  </button>

                  <button v-if="devis.statut !== 'Refusé'" @click="refuserDevis(devis)" class="icon-action-btn text-orange-600 hover:bg-orange-50" title="Refuser le devis">
                    <span class="material-icons text-sm">block</span>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- VUE MOBILE -->
      <div v-if="!loading && devisList.length > 0" class="mobile-cards-view">
        <div v-for="devis in devisList" :key="devis.id" class="mobile-card-item">
          <div class="mobile-card-header">
            <div>
              <span class="mobile-designation font-mono">{{ devis.numero_devis }}</span>
              <p class="text-xs text-slate-500 mt-0.5">{{ devis.clients?.nom_societe || 'Client inconnu' }}</p>
            </div>
            <span :class="badgeStatutClass(devis.statut)" class="badge-statut">
              {{ devis.statut }}
            </span>
          </div>
          
          <div class="mobile-card-footer">
            <div class="mobile-prices">
              <span class="font-mono font-bold text-slate-900">{{ Number(devis.total_ttc || 0).toFixed(2) }} € TTC</span>
              <span class="text-xs text-slate-500">Échéance : {{ formaterDate(devis.date_validite) }}</span>
            </div>
            <div class="action-buttons">
              <button @click="afficherPdf(devis)" class="icon-action-btn text-blue-600 bg-blue-50" title="PDF">
                <span class="material-icons text-sm">visibility</span>
              </button>
              <button v-if="devis.statut === 'Brouillon' || devis.statut === 'Envoyé'" @click="validerEtTransformerDevis(devis)" class="icon-action-btn text-emerald-600 bg-emerald-50" title="Valider">
                <span class="material-icons text-sm">check_circle</span>
              </button>
              <button @click="envoyerParMailDirect(devis)" class="icon-action-btn text-emerald-600 bg-emerald-50" title="Mail">
                <span class="material-icons text-sm">mail</span>
              </button>
              <button v-if="devis.statut === 'Brouillon'" @click="editerDevis(devis)" class="icon-action-btn text-amber-600 bg-amber-50" title="Éditer">
                <span class="material-icons text-sm">edit</span>
              </button>
              <button v-if="devis.statut !== 'Refusé'" @click="refuserDevis(devis)" class="icon-action-btn text-orange-600 bg-orange-50" title="Refuser">
                <span class="material-icons text-sm">block</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- MODALE APERÇU PDF PLEIN ÉCRAN INTERNE -->
    <div v-if="isPdfModalOpen" class="modal-overlay">
      <div class="modal-card modal-large" style="max-width: 600px;">
        <div class="modal-header">
          <h2>Aperçu du Devis : {{ devisActifPdf?.numero_devis }}</h2>
          <button @click="isPdfModalOpen = false" class="close-btn">&times;</button>
        </div>
        
        <div class="modal-body bg-slate-50 p-6 text-center space-y-4">
          <div class="w-16 h-16 bg-blue-50 text-blue-600 rounded-full flex items-center justify-center mx-auto text-2xl shadow-sm">
            <span class="material-icons text-3xl">description</span>
          </div>
          <div>
            <h3 class="font-bold text-slate-800 text-base">Document PDF généré avec succès</h3>
            <p class="text-xs text-slate-500 mt-1">Vous pouvez l'ouvrir pour le consulter ou le télécharger directement.</p>
          </div>
          <div class="pt-2 flex justify-center gap-3">
            <a :href="pdfUrlApercu" target="_blank" class="btn-secondary flex items-center gap-2 text-xs">
              <span class="material-icons text-sm">visibility</span> Ouvrir dans un onglet
            </a>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="telechargerPdf(devisActifPdf)" class="btn-primary flex items-center gap-2">
            <span class="material-icons text-sm">download</span> Télécharger le PDF
          </button>
          <button @click="isPdfModalOpen = false" class="btn-secondary">Fermer</button>
        </div>
      </div>
    </div>

    <!-- MODALE DE CRÉATION / ÉDITION -->
    <div v-if="isModalOpen" class="modal-overlay">
      <div class="modal-card modal-large" style="max-width: 750px;">
        <div class="modal-header">
          <h2>{{ modeEdition ? 'Modifier le devis' : 'Créer un nouveau devis' }}</h2>
          <button @click="isModalOpen = false" class="close-btn">&times;</button>
        </div>

        <div class="modal-body space-y-4">
          <div class="row-flex">
            <div class="input-group" style="flex: 2;">
              <label>Client *</label>
              <select v-model="nouveauDevis.client_id" @change="chargerPrestationsClient" class="input-field">
                <option value="" disabled>Sélectionner un client</option>
                <option v-for="client in clientsList" :key="client.id" :value="client.id">
                  {{ client.nom_societe }}
                </option>
              </select>
            </div>
            <div class="input-group" style="flex: 1;">
              <label>Période de validité</label>
              <select v-model.number="nouveauDevis.validite_jours" class="input-field">
                <option :value="15">15 jours</option>
                <option :value="30">1 mois</option>
                <option :value="90">3 mois</option>
                <option :value="180">6 mois</option>
              </select>
            </div>
          </div>

          <div class="row-flex">
            <div class="input-group" style="flex: 1;">
              <label>Date de réalisation de principe</label>
              <input v-model="nouveauDevis.date_prevue_execution" type="date" class="input-field font-mono" />
            </div>
          </div>

          <div class="input-group">
            <label>Remarques / Conditions particulières</label>
            <textarea v-model="nouveauDevis.remarque" class="input-field" rows="2" placeholder="Conditions de règlement, remarques..."></textarea>
          </div>

          <!-- Lignes de prestations réagencées -->
          <div class="border-t border-slate-200 pt-4 mt-2">
            <div class="flex justify-between items-center mb-3">
              <h3 class="text-sm font-bold text-slate-700 uppercase">Lignes du devis (Tarifs catalogue)</h3>
              <button @click="ajouterLigneCatalogue" class="btn-secondary text-xs py-1.5 px-3 flex items-center gap-1">
                <span class="material-icons text-xs">add</span> Ajouter une ligne
              </button>
            </div>

            <div v-if="!nouveauDevis.client_id" class="text-center p-4 text-xs text-slate-400 italic bg-slate-50 rounded-lg border border-dashed border-slate-200">
              Veuillez sélectionner un client pour afficher ses prestations tarifées.
            </div>

            <div class="space-y-3" v-else>
              <div v-for="(ligne, index) in nouveauDevis.lignes" :key="index" class="ligne-card p-3 bg-slate-50 border border-slate-200 rounded-lg">
                <div class="grid grid-cols-1 md:grid-cols-12 gap-3 items-center">
                  <div class="md:col-span-5">
                    <label class="text-[10px] font-semibold text-slate-500 uppercase">Prestation</label>
                    <select v-model="ligne.prestation_id" @change="selectionnerPrestationCatalogue(ligne)" class="input-field text-xs bg-white">
                      <option value="" disabled>Choisir une prestation</option>
                      <option v-for="p in prestationsDisponibles" :key="p.id" :value="p.id">
                        {{ p.designation }} ({{ p.prix_ht }} €)
                      </option>
                    </select>
                  </div>
                  <div class="md:col-span-2">
                    <label class="text-[10px] font-semibold text-slate-500 uppercase">Quantité</label>
                    <div class="flex gap-1">
                      <input v-model.number="ligne.quantite" type="number" step="0.01" min="0.01" class="input-field text-xs font-mono bg-white" placeholder="Qté" />
                    </div>
                  </div>
                  <div class="md:col-span-2">
                    <label class="text-[10px] font-semibold text-slate-500 uppercase">Unité</label>
                    <input type="text" :value="ligne.unite" disabled class="input-field text-xs bg-slate-100 text-slate-500 cursor-not-allowed" />
                  </div>
                  <div class="md:col-span-2">
                    <label class="text-[10px] font-semibold text-slate-500 uppercase">P.U. HT / TVA</label>
                    <div class="text-xs font-mono font-medium text-slate-700 py-2">
                      {{ Number(ligne.prix_ht || 0).toFixed(2) }} € <span class="text-slate-400">({{ ligne.taux_tva }}%)</span>
                    </div>
                  </div>
                  <div class="md:col-span-1 text-right flex justify-end">
                    <button @click="supprimerLigne(index)" class="icon-action-btn text-red-600 hover:bg-red-50 mt-4 md:mt-0" title="Supprimer la ligne">
                      <span class="material-icons text-sm">delete</span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Totaux -->
          <div class="bg-slate-50 p-4 rounded-xl border border-slate-200 flex flex-col items-end gap-1 font-mono text-sm">
            <div>Total HT : <span class="font-bold text-slate-800">{{ calculTotaux.totalHt.toFixed(2) }} €</span></div>
            <div>Montant TVA : <span class="font-bold text-slate-800">{{ calculTotaux.totalTva.toFixed(2) }} €</span></div>
            <div class="text-base border-t border-slate-200 pt-1 mt-1">Total TTC : <span class="font-extrabold text-blue-600">{{ calculTotaux.totalTtc.toFixed(2) }} €</span></div>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="isModalOpen = false" class="btn-secondary">Annuler</button>
          <button @click="sauvegarderDevis" class="btn-primary" :disabled="saving">
            {{ saving ? 'Enregistrement...' : 'Enregistrer' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { supabase } from '../../supabase'
import jsPDF from 'jspdf'

const devisList = ref([])
const clientsList = ref([])
const loading = ref(false)
const saving = ref(false)
const isTvaExoneree = ref(false)
const parametresEntreprise = ref(null)

const filtreStatut = ref('Tous')
const filtreClient = ref('Tous')

const isModalOpen = ref(false)
const modeEdition = ref(false)
const devisIdEnCours = ref(null)

const isPdfModalOpen = ref(false)
const devisActifPdf = ref(null)
const pdfUrlApercu = ref('')

const nouveauDevis = ref({
  client_id: '',
  validite_jours: 30,
  date_prevue_execution: '',
  remarque: '',
  lignes: []
})

const prestationsDisponibles = ref([])

const chargerParametresUser = async () => {
  const { data: { user } } = await supabase.auth.getUser()
  if (user) {
    const { data } = await supabase.from('parametres').select('*').eq('user_id', user.id).maybeSingle()
    if (data) {
      parametresEntreprise.value = data
      if (data.tva_exoneree === true) {
        isTvaExoneree.value = true
      }
    }
  }
}

const chargerClients = async () => {
  const { data } = await supabase.from('clients').select('id, nom_societe, email, adresse').order('nom_societe')
  if (data) clientsList.value = data
}

const chargerDevis = async () => {
  loading.value = true
  try {
    let query = supabase
      .from('devis')
      .select('*, clients(nom_societe, email, adresse)')
      .order('id', { ascending: false })

    if (filtreStatut.value !== 'Tous') {
      query = query.eq('statut', filtreStatut.value)
    }
    if (filtreClient.value !== 'Tous') {
      query = query.eq('client_id', filtreClient.value)
    }

    const { data, error } = await query
    if (error) throw error
    devisList.value = data || []
  } catch (err) {
    console.error("Erreur chargement devis :", err.message)
  } finally {
    loading.value = false
  }
}

const chargerPrestationsClient = async () => {
  if (!nouveauDevis.value.client_id) return

  try {
    const { data, error } = await supabase
      .from('client_tarifs')
      .select(`
        prix_specifique_ht,
        est_actif,
        prestation_id,
        prestations (
          id,
          designation,
          unite,
          taux_tva
        )
      `)
      .eq('client_id', nouveauDevis.value.client_id)
      .eq('est_actif', true)

    if (error) throw error

    prestationsDisponibles.value = data ? data.map(item => ({
      id: item.prestations?.id,
      designation: item.prestations?.designation || '',
      unite: item.prestations?.unite || 'Heure',
      prix_ht: item.prix_specifique_ht ?? 0,
      taux_tva: isTvaExoneree.value ? 0 : (item.prestations?.taux_tva ?? 20.0)
    })) : []

    // En création, on ajoute une seule ligne vide par défaut si aucune ligne n'est présente
    if (!modeEdition.value && nouveauDevis.value.lignes.length === 0) {
      if (prestationsDisponibles.value.length > 0) {
        const premiere = prestationsDisponibles.value[0]
        nouveauDevis.value.lignes.push({
          prestation_id: premiere.id,
          designation: premiere.designation,
          quantite: 1,
          unite: premiere.unite,
          prix_ht: premiere.prix_ht,
          taux_tva: premiere.taux_tva
        })
      }
    }
  } catch (err) {
    console.error("Erreur chargement tarifs :", err)
  }
}

const genererNumeroDevis = async () => {
  const maintenant = new Date()
  const annee = maintenant.getFullYear()
  const mois = String(maintenant.getMonth() + 1).padStart(2, '0')
  const prefixe = `DEV-${annee}-${mois}-`

  const { count } = await supabase
    .from('devis')
    .select('id', { count: 'exact', head: true })
    .gte('date_creation', `${annee}-${mois}-01`)

  const indexSuivant = (count || 0) + 1
  return `${prefixe}${String(indexSuivant).padStart(2, '0')}`
}

const ouvrirModalCreation = () => {
  modeEdition.value = false
  devisIdEnCours.value = null
  nouveauDevis.value = {
    client_id: '',
    validite_jours: 30,
    date_prevue_execution: new Date().toISOString().split('T')[0],
    remarque: '',
    lignes: []
  }
  prestationsDisponibles.value = []
  isModalOpen.value = true
}

const editerDevis = async (devis) => {
  modeEdition.value = true
  devisIdEnCours.value = devis.id

  const dCreation = new Date(devis.date_creation)
  const dValidite = new Date(devis.date_validite)
  const diffJours = Math.round((dValidite - dCreation) / (1000 * 60 * 60 * 24))

  let validiteSelectionnee = 30
  if ([15, 30, 90, 180].includes(diffJours)) {
    validiteSelectionnee = diffJours
  }

  nouveauDevis.value = {
    client_id: devis.client_id,
    validite_jours: validiteSelectionnee,
    date_prevue_execution: devis.date_prevue_execution || '',
    remarque: devis.remarque || '',
    lignes: []
  }

  await chargerPrestationsClient()

  const { data: items } = await supabase
    .from('devis_items')
    .select('*')
    .eq('devis_id', devis.id)

  if (items && items.length > 0) {
    nouveauDevis.value.lignes = items.map(i => {
      const matchP = prestationsDisponibles.value.find(p => p.id === i.prestation_id)
      return {
        prestation_id: i.prestation_id,
        designation: matchP ? matchP.designation : (i.designation || 'Prestation'),
        quantite: i.quantite,
        unite: i.unite || (matchP ? matchP.unite : 'Heure'),
        prix_ht: i.prix_unitaire_ht,
        taux_tva: i.taux_tva
      }
    })
  }

  isModalOpen.value = true
}

const ajouterLigneCatalogue = () => {
  if (!nouveauDevis.value.client_id) {
    alert("Veuillez d'abord sélectionner un client.")
    return
  }
  if (prestationsDisponibles.value.length === 0) {
    return
  }
  const premiere = prestationsDisponibles.value[0]
  nouveauDevis.value.lignes.push({
    prestation_id: premiere.id,
    designation: premiere.designation,
    quantite: 1,
    unite: premiere.unite,
    prix_ht: premiere.prix_ht,
    taux_tva: premiere.taux_tva
  })
}

const selectionnerPrestationCatalogue = (ligne) => {
  const match = prestationsDisponibles.value.find(p => p.id === ligne.prestation_id)
  if (match) {
    ligne.designation = match.designation
    ligne.prix_ht = match.prix_ht
    ligne.unite = match.unite
    ligne.taux_tva = isTvaExoneree.value ? 0 : match.taux_tva
  }
}

const supprimerLigne = (index) => {
  nouveauDevis.value.lignes.splice(index, 1)
}

const calculTotaux = computed(() => {
  let totalHt = 0
  let totalTva = 0
  for (const l of nouveauDevis.value.lignes) {
    const q = Number(l.quantite) || 0
    const p = Number(l.prix_ht) || 0
    const tva = Number(l.taux_tva) || 0
    const montantHtLigne = q * p
    totalHt += montantHtLigne
    totalTva += montantHtLigne * (tva / 100)
  }
  return {
    totalHt,
    totalTva,
    totalTtc: totalHt + totalTva
  }
})

const sauvegarderDevis = async () => {
  if (!nouveauDevis.value.client_id) {
    alert("Veuillez sélectionner un client.")
    return
  }
  if (nouveauDevis.value.lignes.length === 0) {
    alert("Veuillez ajouter au moins une ligne de prestation.")
    return
  }

  saving.value = true
  try {
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) throw new Error("Utilisateur non authentifié")

    const dateCreation = new Date().toISOString().split('T')[0]
    const dateValiditeObj = new Date()
    dateValiditeObj.setDate(dateValiditeObj.getDate() + (nouveauDevis.value.validite_jours || 30))
    const dateValidite = dateValiditeObj.toISOString().split('T')[0]

    let devisId

    if (modeEdition.value && devisIdEnCours.value) {
      const { error: updateError } = await supabase
        .from('devis')
        .update({
          client_id: nouveauDevis.value.client_id,
          date_validite: dateValidite,
          date_prevue_execution: nouveauDevis.value.date_prevue_execution || null,
          total_ht: calculTotaux.value.totalHt,
          total_tva: calculTotaux.value.totalTva,
          total_ttc: calculTotaux.value.totalTtc,
          remarque: nouveauDevis.value.remarque
        })
        .eq('id', devisIdEnCours.value)

      if (updateError) throw updateError
      devisId = devisIdEnCours.value
      await supabase.from('devis_items').delete().eq('devis_id', devisId)
    } else {
      const numeroDevis = await genererNumeroDevis()
      const { data: devisInserted, error: devisError } = await supabase
        .from('devis')
        .insert({
          user_id: user.id,
          client_id: nouveauDevis.value.client_id,
          numero_devis: numeroDevis,
          date_creation: dateCreation,
          date_validite: dateValidite,
          date_prevue_execution: nouveauDevis.value.date_prevue_execution || null,
          total_ht: calculTotaux.value.totalHt,
          total_tva: calculTotaux.value.totalTva,
          total_ttc: calculTotaux.value.totalTtc,
          statut: 'Brouillon',
          remarque: nouveauDevis.value.remarque
        })
        .select()
        .single()

      if (devisError) throw devisError
      devisId = devisInserted.id
    }

    const lignesData = nouveauDevis.value.lignes.map(l => {
      const matchPresta = prestationsDisponibles.value.find(p => p.id === l.prestation_id)
      return {
        user_id: user.id,
        devis_id: devisId,
        prestation_id: l.prestation_id || null,
        designation: matchPresta ? matchPresta.designation : 'Prestation',
        quantite: l.quantite,
        unite: l.unite,
        prix_unitaire_ht: l.prix_ht,
        taux_tva: l.taux_tva
      }
    })

    const { error: itemsError } = await supabase.from('devis_items').insert(lignesData)
    if (itemsError) throw itemsError

    isModalOpen.value = false
    chargerDevis()
  } catch (err) {
    console.error("Erreur enregistrement devis :", err)
    alert("Erreur lors de l'enregistrement du devis.")
  } finally {
    saving.value = false
  }
}

const genererInstancePdf = async (devis) => {
  const { data: items } = await supabase.from('devis_items').select('*').eq('devis_id', devis.id)
  
  const itemsResolus = []
  if (items) {
    for (const item of items) {
      let nomDesignation = item.designation || 'Prestation'
      if (item.prestation_id) {
        const { data: pData } = await supabase.from('prestations').select('designation').eq('id', item.prestation_id).maybeSingle()
        if (pData?.designation) {
          nomDesignation = pData.designation
        }
      }
      itemsResolus.push({ ...item, designation: nomDesignation })
    }
  }

  const doc = new jsPDF({
    orientation: 'portrait',
    unit: 'mm',
    format: 'a4'
  })

  // --- En-tête Entreprise ---
  doc.setFont("helvetica", "bold")
  doc.setFontSize(14)
  doc.text(parametresEntreprise.value?.nom_entreprise || 'Kassandre LECLERC', 14, 20)

  doc.setFont("helvetica", "normal")
  doc.setFontSize(9)
  doc.setTextColor(100)
  const adresseLines = doc.splitTextToSize(parametresEntreprise.value?.adresse || '18 avenue Charles Bras\n77184 Émerainville', 70)
  doc.text(adresseLines, 14, 26)
  doc.text(`Tél : ${parametresEntreprise.value?.telephone || '06.06.06.06.06'}`, 14, 38)
  doc.text(`Email : ${parametresEntreprise.value?.email || 'leclerckassandre@gmail.com'}`, 14, 43)
  doc.text(`SIRET : ${parametresEntreprise.value?.siret || '123 456 789 00010'}`, 14, 48)

  // --- Bloc DEVIS (Droite) ---
  doc.setFillColor(15, 23, 42)
  doc.rect(130, 15, 66, 16, 'F')
  doc.setTextColor(255, 255, 255)
  doc.setFont("helvetica", "bold")
  doc.setFontSize(11)
  doc.text("DEVIS", 163, 25, { align: 'center' })

  doc.setTextColor(30, 41, 59)
  doc.setFontSize(10)
  doc.text(`N° ${devis.numero_devis}`, 196, 38, { align: 'right' })
  doc.setFont("helvetica", "normal")
  doc.setFontSize(9)
  doc.text(`Émission : ${formaterDate(devis.date_creation)}`, 196, 44, { align: 'right' })
  doc.text(`Validité : ${formaterDate(devis.date_validite)}`, 196, 50, { align: 'right' })

  // --- Bloc Client ---
  doc.setFillColor(248, 250, 252)
  doc.setDrawColor(226, 232, 240)
  doc.roundedRect(14, 60, 90, 30, 2, 2, 'FD')

  doc.setFont("helvetica", "bold")
  doc.setFontSize(8)
  doc.setTextColor(100)
  doc.text("DESTINATAIRE :", 18, 67)

  doc.setFontSize(10)
  doc.setTextColor(15, 23, 42)
  doc.text(devis.clients?.nom_societe || 'Client', 18, 73)
  doc.setFont("helvetica", "normal")
  doc.setFontSize(9)
  doc.setTextColor(100)
  doc.text(`Email : ${devis.clients?.email || ''}`, 18, 80)

  // --- Tableau des Lignes ---
  let startY = 98
  doc.setFillColor(241, 245, 249)
  doc.rect(14, startY, 182, 8, 'F')
  
  doc.setFont("helvetica", "bold")
  doc.setFontSize(9)
  doc.setTextColor(71, 85, 105)
  doc.text("Désignation", 18, startY + 5.5)
  doc.text("Qté", 115, startY + 5.5, { align: 'center' })
  doc.text("P.U. HT", 145, startY + 5.5, { align: 'right' })
  doc.text("TVA", 168, startY + 5.5, { align: 'center' })
  doc.text("Total HT", 192, startY + 5.5, { align: 'right' })

  startY += 8
  doc.setFont("helvetica", "normal")
  doc.setTextColor(30, 41, 59)

  itemsResolus.forEach((item, index) => {
    const rowY = startY + (index * 8) + 6
    doc.text(item.designation || 'Prestation', 18, rowY)
    doc.text(`${item.quantite} ${item.unite || ''}`, 115, rowY, { align: 'center' })
    doc.text(`${Number(item.prix_unitaire_ht).toFixed(2)} €`, 145, rowY, { align: 'right' })
    doc.text(`${Number(item.taux_tva).toFixed(1)}%`, 168, rowY, { align: 'center' })
    doc.text(`${(item.quantite * item.prix_unitaire_ht).toFixed(2)} €`, 192, rowY, { align: 'right' })
    
    doc.setDrawColor(241, 245, 249)
    doc.line(14, rowY + 2, 196, rowY + 2)
  })

  let finalY = startY + (itemsResolus.length * 8) + 10

  // --- Totaux ---
  const xLeft = 120
  doc.setFont("helvetica", "normal")
  doc.setFontSize(9)
  doc.setTextColor(100)
  
  doc.text("Total HT :", xLeft, finalY)
  doc.text(`${Number(devis.total_ht || 0).toFixed(2)} €`, 196, finalY, { align: 'right' })

  doc.text("Total TVA :", xLeft, finalY + 6)
  doc.text(`${Number(devis.total_tva || 0).toFixed(2)} €`, 196, finalY + 6, { align: 'right' })

  doc.setFont("helvetica", "bold")
  doc.setFontSize(11)
  doc.setTextColor(15, 23, 42)
  doc.text("Total TTC :", xLeft, finalY + 14)
  doc.setTextColor(37, 99, 235)
  doc.text(`${Number(devis.total_ttc || 0).toFixed(2)} €`, 196, finalY + 14, { align: 'right' })

  // --- Mentions légales ---
  if (isTvaExoneree.value) {
    doc.setFont("helvetica", "italic")
    doc.setFontSize(8)
    doc.setTextColor(120)
    doc.text("TVA non applicable, art. 293 B du CGI", 14, finalY + 4)
  }

  // --- Cadre Signature ---
  finalY += 26
  doc.setDrawColor(203, 213, 225)
  doc.roundedRect(120, finalY, 76, 35, 2, 2, 'D')
  doc.setFont("helvetica", "bold")
  doc.setFontSize(8)
  doc.setTextColor(71, 85, 105)
  doc.text("Bon pour accord & Signature :", 124, finalY + 6)

  return doc
}

const afficherPdf = async (devis) => {
  devisActifPdf.value = devis
  const doc = await genererInstancePdf(devis)
  const pdfBlob = doc.output('blob')
  pdfUrlApercu.value = URL.createObjectURL(pdfBlob)
  isPdfModalOpen.value = true
}

const telechargerPdf = async (devis) => {
  const doc = await genererInstancePdf(devis)
  doc.save(`Devis_${devis.numero_devis}.pdf`)
  isPdfModalOpen.value = false
}

const validerEtTransformerDevis = async (devis) => {
  if (!confirm(`Valider le devis ${devis.numero_devis} (passer au statut "Validé" et transférer en prestations à réaliser) ?`)) return

  try {
    const { data: { user } } = await supabase.auth.getUser()
    const { data: items } = await supabase.from('devis_items').select('*').eq('devis_id', devis.id)

    if (!items || items.length === 0) {
      alert("Aucune ligne trouvée dans ce devis.")
      return
    }

    let nbAjouts = 0
    const dateJour = devis.date_prevue_execution || new Date().toISOString().split('T')[0]

    for (const item of items) {
      let designationLigne = `Prestation (${devis.numero_devis})`
      if (item.prestation_id) {
        const { data: pData } = await supabase.from('prestations').select('designation').eq('id', item.prestation_id).maybeSingle()
        if (pData) designationLigne = pData.designation
      }

      const { error: errPresta } = await supabase.from('prestations_realisees').insert({
        user_id: user.id,
        client_id: devis.client_id,
        devis_id: devis.id,
        designation: designationLigne,
        quantite: item.quantite,
        unite: item.unite || 'Heure',
        prix_unitaire_ht: item.prix_unitaire_ht,
        taux_tva: item.taux_tva,
        date_realisation: dateJour,
        statut: 'À réaliser'
      })

      if (!errPresta) nbAjouts++
    }

    // Passage du devis au statut "Validé"
    const { error: updateError } = await supabase
      .from('devis')
      .update({ statut: 'Validé' })
      .eq('id', devis.id)

    if (updateError) throw updateError

    alert(`Devis validé et ${nbAjouts} ligne(s) transférée(s) vers le suivi des prestations avec succès !`)
    chargerDevis()
  } catch (err) {
    console.error("Erreur lors de la validation du devis :", err)
    alert("Erreur lors de la validation et du transfert du devis.")
  }
}

const envoyerParMailDirect = async (devis) => {
  if (!devis.clients?.email) {
    alert("Erreur d'envoi : Ce client ne possède pas d'adresse email enregistrée.")
    return
  }

  try {
    saving.value = true

    // 1. Génération et téléchargement automatique du PDF pour que vous puissiez le joindre au mail
    await telechargerPdf(devis)

    // 2. Préparation du message
    const destinataire = encodeURIComponent(devis.clients.email)
    const sujet = encodeURIComponent(`Devis n° ${devis.numero_devis}`)
    const corps = encodeURIComponent(
      `Bonjour,\n\n` +
      `Veuillez trouver ci-joint notre devis n° ${devis.numero_devis}.\n\n` +
      `Restant à votre disposition pour tout échange.\n\n` +
      `Bien cordialement,\n` +
      `${parametresEntreprise.value?.nom_entreprise || ''}`
    )

    // 3. Ouverture du client mail par défaut
    window.location.href = `mailto:${destinataire}?subject=${sujet}&body=${corps}`

    // 4. Mise à jour du statut du devis en "Envoyé" dans Supabase
    const { error: updateError } = await supabase
      .from('devis')
      .update({ statut: 'Envoyé' })
      .eq('id', devis.id)

    if (updateError) throw updateError

    chargerDevis()
  } catch (err) {
    console.error("Erreur préparation e-mail :", err)
    alert("Erreur lors de la préparation de l'e-mail.")
  } finally {
    saving.value = false
  }
}

const refuserDevis = async (devis) => {
  if (!confirm(`Marquer le devis ${devis.numero_devis} comme refusé ?`)) return

  const { error } = await supabase
    .from('devis')
    .update({ statut: 'Refusé' })
    .eq('id', devis.id)

  if (!error) {
    chargerDevis()
  } else {
    alert("Erreur lors de la mise à jour du statut.")
  }
}

const formaterDate = (dateStr) => {
  if (!dateStr) return ''
  const [annee, mois, jour] = dateStr.split('-')
  return `${jour}/${mois}/${annee}`
}

const badgeStatutClass = (statut) => {
  switch (statut) {
    case 'Brouillon': return 'bg-slate-100 text-slate-700 border-slate-200'
    case 'Envoyé': return 'bg-blue-50 text-blue-700 border-blue-200'
    case 'Validé': return 'bg-emerald-50 text-emerald-700 border-emerald-200'
    case 'Accepté': return 'bg-emerald-50 text-emerald-700 border-emerald-200'
    case 'Refusé': return 'bg-orange-50 text-orange-700 border-orange-200'
    default: return 'bg-slate-100 text-slate-700 border-slate-200'
  }
}

onMounted(async () => {
  await chargerParametresUser()
  await chargerClients()
  await chargerDevis()
})
</script>

<style scoped>
.page-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 16px;
  font-family: system-ui, -apple-system, sans-serif;
  color: #1e293b;
}

.header-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  border: 1px solid #e2e8f0;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 16px;
}

.page-title {
  font-size: 22px;
  font-weight: bold;
  margin: 0;
  color: #0f172a;
}

.page-subtitle {
  font-size: 13px;
  color: #64748b;
  margin: 4px 0 0 0;
}

.btn-primary-clean {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: #2563eb;
  color: white;
  border: none;
  padding: 10px 16px;
  border-radius: 8px;
  font-weight: 500;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-primary-clean:hover {
  background: #1d4ed8;
}

.content-card {
  background: white;
  padding: 16px;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  border: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.filters-row {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.filter-group {
  flex: 1;
  min-width: 220px;
}

.desktop-table-view {
  display: block;
  overflow-x: auto;
}

.mobile-cards-view {
  display: none;
}

@media (max-width: 768px) {
  .desktop-table-view {
    display: none;
  }
  .mobile-cards-view {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: 14px;
}

.data-table th {
  background: #f8fafc;
  padding: 12px 16px;
  font-weight: 600;
  color: #475569;
  border-bottom: 1px solid #e2e8f0;
  text-transform: uppercase;
  font-size: 11px;
}

.data-table td {
  padding: 14px 16px;
  border-bottom: 1px solid #f1f5f9;
}

.clickable-row:hover td {
  background: #f8fafc;
}

.mobile-card-item {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.mobile-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}

.mobile-designation {
  font-weight: 600;
  font-size: 15px;
  color: #0f172a;
}

.mobile-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid #f1f5f9;
  padding-top: 8px;
}

.mobile-prices {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.badge-statut {
  padding: 3px 10px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  border: 1px solid;
  display: inline-block;
  white-space: nowrap;
}

.action-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 4px;
}

.icon-action-btn {
  background: none;
  border: none;
  padding: 6px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  text-decoration: none;
}

.loading-state, .empty-state {
  text-align: center;
  padding: 30px;
  color: #64748b;
  font-style: italic;
  font-size: 14px;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 12px;
  box-sizing: border-box;
}

.modal-card {
  background: white;
  width: 100%;
  max-width: 480px;
  border-radius: 14px;
  box-shadow: 0 20px 25px -5px rgba(0,0,0,0.15);
  border: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  max-height: 90vh;
}

.modal-large {
  max-width: 800px;
}

.modal-header {
  padding: 16px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #e2e8f0;
}

.modal-header h2 {
  font-size: 17px;
  font-weight: bold;
  margin: 0;
  color: #0f172a;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  color: #64748b;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.modal-body {
  padding: 16px 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.modal-footer {
  padding: 14px 20px;
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.input-group label {
  font-size: 11px;
  font-weight: 600;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.input-field {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 14px;
  color: #1e293b;
  background: #f8fafc;
  outline: none;
  box-sizing: border-box;
}

.input-field:focus {
  background: white;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.row-flex {
  display: flex;
  gap: 12px;
}

.ligne-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 10px;
}

.btn-primary {
  background: #2563eb;
  color: white;
  border: none;
  padding: 10px 18px;
  border-radius: 8px;
  font-weight: 500;
  font-size: 14px;
  cursor: pointer;
}

.btn-primary:hover {
  background: #1d4ed8;
}

.btn-secondary {
  background: white;
  color: #475569;
  border: 1px solid #cbd5e1;
  padding: 10px 16px;
  border-radius: 8px;
  font-weight: 500;
  font-size: 14px;
  cursor: pointer;
}

.font-mono {
  font-family: monospace;
}
</style>