<script setup>
import { ref, onMounted, watch } from 'vue'
import { supabase } from '../../supabase'

const tab = ref('clients')

// --- PARAMETRES ENTREPRISE (TVA) ---
const entrepriseExoneree = ref(true)

const fetchParametres = async () => {
  try {
    const { data, error } = await supabase.from('parametres').select('*').single()
    if (!error && data) {
      entrepriseExoneree.value = !!data.tva_exoneree
      if (entrepriseExoneree.value) {
        formPresta.value.taux_tva = 0.0
      }
    }
  } catch (err) {
    console.error('Erreur chargement paramètres:', err)
  }
}

// --- CLIENTS ---
const clients = ref([])
const loadingClients = ref(false)
const showModalClient = ref(false)
const isEditClient = ref(false)
const currentClientId = ref(null)

const formClient = ref({
  est_particulier: false,
  nom_societe: '',
  contact: '',
  email: '',
  telephone: '',
  adresse: '',
  cp: '',
  ville: '',
  siret: '',
  tva_intra: '',
  rcs: '',
  ape: '',
  sans_tva: false,
  recap_interventions: false,
  multi_etab: false,
  modele_facture: 'condense'
})

// --- ETABLISSEMENTS / MULTI-SITES ---
const showModalSites = ref(false)
const clientSelectionneSites = ref(null)
const listeSites = ref([])
const formSite = ref({
  id: null,
  nom_site: '',
  adresse: '',
  cp: '',
  ville: ''
})

// --- TARIFS SPÉCIFIQUES ---
const showModalTarifs = ref(false)
const clientSelectionneTarifs = ref(null)
const cataloguePrestations = ref([])
const tarifsClient = ref({})

// --- PRESTATIONS ---
const formPresta = ref({
  designation: '',
  unite: 'Heure',
  prix_ht: 0,
  taux_tva: 20.0
})

// Observer le type de client pour adapter les champs pro
watch(() => formClient.value.est_particulier, (val) => {
  if (val) {
    formClient.value.siret = ''
    formClient.value.tva_intra = ''
    formClient.value.rcs = ''
    formClient.value.ape = ''
    formClient.value.sans_tva = false
    formClient.value.recap_interventions = false
    formClient.value.multi_etab = false
    formClient.value.modele_facture = 'condense'
  }
})

watch(() => formClient.value.sans_tva, (val) => {
  if (val) formClient.value.tva_intra = ''
})

// Chargement initial
const fetchClients = async () => {
  loadingClients.value = true
  try {
    const { data, error } = await supabase.from('clients').select('*').order('nom_societe', { ascending: true })
    if (error) throw error
    clients.value = data || []
  } catch (err) {
    console.error('Erreur chargement clients:', err)
  } finally {
    loadingClients.value = false
  }
}

// Gestion Client
const ouvrirModalClient = (client = null) => {
  if (client) {
    isEditClient.value = true
    currentClientId.value = client.id
    formClient.value = {
      est_particulier: !!client.est_particulier,
      nom_societe: client.nom_societe || '',
      contact: client.contact || '',
      email: client.email || '',
      telephone: client.telephone || '',
      adresse: client.adresse || '',
      cp: client.cp || '',
      ville: client.ville || '',
      siret: client.siret || '',
      tva_intra: client.tva_intra || '',
      rcs: client.rcs || '',
      ape: client.ape || '',
      sans_tva: !!client.sans_tva,
      recap_interventions: !!client.recap_interventions,
      multi_etab: !!client.multi_etab,
      modele_facture: client.modele_facture || 'condense'
    }
  } else {
    isEditClient.value = false
    currentClientId.value = null
    formClient.value = {
      est_particulier: false,
      nom_societe: '',
      contact: '',
      email: '',
      telephone: '',
      adresse: '',
      cp: '',
      ville: '',
      siret: '',
      tva_intra: '',
      rcs: '',
      ape: '',
      sans_tva: false,
      recap_interventions: false,
      multi_etab: false,
      modele_facture: 'condense'
    }
  }
  showModalClient.value = true
}

const sauvegarderClient = async () => {
  if (!formClient.value.nom_societe.trim()) {
    alert('Le nom ou la raison sociale est obligatoire.')
    return
  }

  const payload = { ...formClient.value }
  if (payload.est_particulier) {
    payload.siret = ''
    payload.tva_intra = ''
    payload.rcs = ''
    payload.ape = ''
    payload.sans_tva = false
    payload.recap_interventions = false
    payload.multi_etab = false
    payload.modele_facture = 'condense'
  }

  try {
    if (isEditClient.value) {
      const { error } = await supabase.from('clients').update(payload).eq('id', currentClientId.value)
      if (error) throw error
    } else {
      const { error } = await supabase.from('clients').insert([payload])
      if (error) throw error
    }
    showModalClient.value = false
    await fetchClients()
  } catch (err) {
    alert('Erreur lors de l’enregistrement : ' + err.message)
  }
}

const supprimerClient = async (id) => {
  if (!confirm('Voulez-vous supprimer ce client et ses données associées ?')) return
  try {
    const { error } = await supabase.from('clients').delete().eq('id', id)
    if (error) throw error
    await fetchClients()
  } catch (err) {
    alert('Erreur lors de la suppression : ' + err.message)
  }
}

// Gestion des Établissements (Multi-sites)
const ouvrirModalSites = async (client) => {
  clientSelectionneSites.value = client
  formSite.value = { id: null, nom_site: '', adresse: '', cp: '', ville: '' }
  await chargerSites(client.id)
  showModalSites.value = true
}

const chargerSites = async (clientId) => {
  const { data } = await supabase.from('etablissements').select('*').eq('client_id', clientId).order('nom_site')
  listeSites.value = data || []
}

const sauvegarderSite = async () => {
  if (!formSite.value.nom_site.trim()) {
    alert('Le nom du site est obligatoire.')
    return
  }
  const payload = {
    client_id: clientSelectionneSites.value.id,
    nom_site: formSite.value.nom_site,
    adresse: formSite.value.adresse,
    cp: formSite.value.cp,
    ville: formSite.value.ville
  }

  if (formSite.value.id) {
    await supabase.from('etablissements').update(payload).eq('id', formSite.value.id)
  } else {
    await supabase.from('etablissements').insert([payload])
  }
  formSite.value = { id: null, nom_site: '', adresse: '', cp: '', ville: '' }
  await chargerSites(clientSelectionneSites.value.id)
}

const editerSite = (site) => {
  formSite.value = { ...site }
}

const supprimerSite = async (siteId) => {
  await supabase.from('etablissements').delete().eq('id', siteId)
  await chargerSites(clientSelectionneSites.value.id)
}

// Gestion des Tarifs Spécifiques
const ouvrirModalTarifs = async (client) => {
  clientSelectionneTarifs.value = client
  try {
    const { data: catData } = await supabase.from('prestations').select('*').order('designation')
    cataloguePrestations.value = catData || []

    const { data: tarifsData } = await supabase.from('client_tarifs').select('*').eq('client_id', client.id)
    const mapTarifs = {}
    if (tarifsData) {
      tarifsData.forEach(t => { mapTarifs[t.prestation_id] = t.prix_specifique_ht })
    }
    
    const initialMap = {}
    cataloguePrestations.value.forEach(p => {
      initialMap[p.id] = mapTarifs[p.id] !== undefined ? mapTarifs[p.id] : p.prix_ht
    })
    tarifsClient.value = initialMap
    showModalTarifs.value = true
  } catch (err) {
    alert('Erreur chargement tarifs : ' + err.message)
  }
}

const sauvegarderTarifs = async () => {
  try {
    for (const prestationId of Object.keys(tarifsClient.value)) {
      const prix = parseFloat(tarifsClient.value[prestationId]) || 0
      await supabase.from('client_tarifs').upsert({
        client_id: clientSelectionneTarifs.value.id,
        prestation_id: parseInt(prestationId),
        prix_specifique_ht: prix,
        est_actif: true
      }, { onConflict: 'client_id,prestation_id' })
    }
    showModalTarifs.value = false
    alert('Tarifs enregistrés avec succès !')
  } catch (err) {
    alert('Erreur lors de l’enregistrement : ' + err.message)
  }
}

// Création de Prestation
const creerPrestation = async () => {
  if (!formPresta.value.designation.trim()) {
    alert('Veuillez saisir une désignation.')
    return
  }

  const payload = { ...formPresta.value }
  if (entrepriseExoneree.value) {
    payload.taux_tva = 0.0
  }

  try {
    const { error } = await supabase.from('prestations').insert([payload])
    if (error) throw error

    alert('Prestation ajoutée au catalogue avec succès !')
    formPresta.value = {
      designation: '',
      unite: 'Heure',
      prix_ht: 0,
      taux_tva: entrepriseExoneree.value ? 0.0 : 20.0
    }
  } catch (err) {
    alert('Erreur lors de la création : ' + err.message)
  }
}

onMounted(() => {
  fetchParametres()
  fetchClients()
})
</script>

<template>
  <div class="space-y-4">
    <!-- Navigation par onglets -->
    <div class="flex border-b border-slate-200">
      <button 
        @click="tab = 'clients'" 
        class="flex-1 pb-3 text-xs font-bold uppercase tracking-wider transition border-b-2"
        :class="tab === 'clients' ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-400 hover:text-slate-600'">
        Gestion des Clients
      </button>
      <button 
        @click="tab = 'prester'" 
        class="flex-1 pb-3 text-xs font-bold uppercase tracking-wider transition border-b-2"
        :class="tab === 'prester' ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-400 hover:text-slate-600'">
        Créer une Prestation
      </button>
    </div>

    <!-- ONGLET 1 : CLIENTS -->
    <div v-if="tab === 'clients'" class="space-y-4">
      <div class="flex justify-between items-center">
        <h2 class="text-xs font-bold text-slate-700 uppercase tracking-wider">Annuaire des clients</h2>
        <button @click="ouvrirModalClient()" class="bg-blue-600 text-white text-xs px-3 py-1.5 rounded-xl font-medium shadow-sm hover:bg-blue-700 transition">
          + Nouveau Client
        </button>
      </div>

      <div v-if="loadingClients" class="text-center py-8 text-xs text-slate-400">Chargement...</div>
      <div v-else-if="clients.length === 0" class="bg-white p-6 rounded-xl border border-slate-200 text-center text-xs text-slate-500">
        Aucun client enregistré.
      </div>
      <div v-else class="space-y-3">
        <div v-for="client in clients" :key="client.id" class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col gap-2">
          <div class="flex justify-between items-start">
            <div>
              <div class="flex items-center gap-2">
                <span class="px-2 py-0.5 rounded text-[10px] font-bold" :class="client.est_particulier ? 'bg-purple-100 text-purple-800' : 'bg-blue-100 text-blue-800'">
                  {{ client.est_particulier ? 'Particulier' : 'Pro' }}
                </span>
                <h3 class="text-xs font-bold text-slate-900">{{ client.nom_societe }}</h3>
              </div>
              <p class="text-xs text-slate-500 mt-1" v-if="client.contact">Contact : {{ client.contact }}</p>
              <p class="text-xs text-slate-400">{{ client.adresse || '-' }} - {{ client.cp }} {{ client.ville }}</p>
            </div>
            <div class="flex gap-1">
              <button v-if="client.multi_etab" @click="ouvrirModalSites(client)" class="p-1.5 bg-amber-50 text-amber-700 rounded-lg text-xs font-medium hover:bg-amber-100 transition" title="Établissements / Sites">
                🏢
              </button>
              <button @click="ouvrirModalTarifs(client)" class="p-1.5 bg-teal-50 text-teal-700 rounded-lg text-xs font-medium hover:bg-teal-100 transition" title="Tarifs spécifiques">
                💰
              </button>
              <button @click="ouvrirModalClient(client)" class="p-1.5 bg-slate-100 text-slate-700 rounded-lg text-xs font-medium hover:bg-slate-200 transition" title="Modifier">
                ✏️
              </button>
              <button @click="supprimerClient(client.id)" class="p-1.5 bg-rose-50 text-rose-600 rounded-lg text-xs font-medium hover:bg-rose-100 transition" title="Supprimer">
                🗑️
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ONGLET 2 : PRESTATIONS -->
    <div v-if="tab === 'prester'" class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
      <h2 class="text-xs font-bold text-slate-700 uppercase tracking-wider border-b border-slate-100 pb-2">Ajouter une prestation au catalogue</h2>

      <div class="space-y-3">
        <div>
          <label class="block text-[11px] font-medium text-slate-500 mb-1">Désignation *</label>
          <input v-model="formPresta.designation" type="text" placeholder="Ex: Cours particulier..." class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500" />
        </div>

        <div class="grid grid-cols-2 gap-2">
          <div>
            <label class="block text-[11px] font-medium text-slate-500 mb-1">Unité</label>
            <select v-model="formPresta.unite" class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500 bg-white">
              <option value="Heure">Heure</option>
              <option value="Jour">Jour</option>
              <option value="Forfait">Forfait</option>
              <option value="Km">Km</option>
              <option value="Unité">Unité</option>
            </select>
          </div>
          <div>
            <label class="block text-[11px] font-medium text-slate-500 mb-1">Prix unitaire HT (€) *</label>
            <input v-model.number="formPresta.prix_ht" type="number" step="0.01" class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
        </div>

        <div>
          <label class="block text-[11px] font-medium text-slate-500 mb-1">Taux de TVA</label>
          <select v-model.number="formPresta.taux_tva" :disabled="entrepriseExoneree" class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500 bg-white disabled:bg-slate-100 disabled:text-slate-400">
            <option :value="0.0">0 % (Exonéré)</option>
            <option :value="5.5">5.5 %</option>
            <option :value="10.0">10 %</option>
            <option :value="20.0">20 % (Standard)</option>
          </select>
          <p v-if="entrepriseExoneree" class="text-[10px] text-amber-600 italic mt-1">Entreprise en franchise de TVA (bloquée à 0%).</p>
        </div>

        <button @click="creerPrestation" class="w-full py-2.5 bg-blue-600 text-white font-bold text-xs rounded-xl shadow-sm hover:bg-blue-700 transition uppercase tracking-wider mt-2">
          Enregistrer la prestation
        </button>
      </div>
    </div>

    <!-- MODALE CLIENT COMPLET -->
    <div v-if="showModalClient" class="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4 overflow-y-auto">
      <div class="bg-white w-full max-w-lg rounded-2xl p-5 space-y-4 shadow-xl my-auto max-h-[90vh] overflow-y-auto">
        <div class="flex justify-between items-center border-b border-slate-100 pb-3">
          <h3 class="text-sm font-bold text-slate-900">{{ isEditClient ? 'Modifier le client' : 'Nouveau client' }}</h3>
          <button @click="showModalClient = false" class="text-slate-400 hover:text-slate-600 text-sm font-bold">✕</button>
        </div>

        <div class="space-y-3">
          <div class="flex items-center gap-2 pb-2 border-b border-slate-100">
            <input type="checkbox" id="particulier" v-model="formClient.est_particulier" class="w-4 h-4 text-blue-600 rounded border-slate-300" />
            <label for="particulier" class="text-xs font-medium text-slate-700">Client Particulier (décochez pour Professionnel)</label>
          </div>

          <div>
            <label class="block text-[11px] font-medium text-slate-500 mb-1">Nom / Société *</label>
            <input v-model="formClient.nom_societe" type="text" class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500" />
          </div>

          <div>
            <label class="block text-[11px] font-medium text-slate-500 mb-1">Contact référent</label>
            <input v-model="formClient.contact" type="text" class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500" />
          </div>

          <div class="grid grid-cols-2 gap-2">
            <div>
              <label class="block text-[11px] font-medium text-slate-500 mb-1">Email</label>
              <input v-model="formClient.email" type="email" class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label class="block text-[11px] font-medium text-slate-500 mb-1">Téléphone</label>
              <input v-model="formClient.telephone" type="text" class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
          </div>

          <div>
            <label class="block text-[11px] font-medium text-slate-500 mb-1">Adresse</label>
            <input v-model="formClient.adresse" type="text" class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500" />
          </div>

          <div class="grid grid-cols-3 gap-2">
            <div>
              <label class="block text-[11px] font-medium text-slate-500 mb-1">Code Postal</label>
              <input v-model="formClient.cp" type="text" class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div class="col-span-2">
              <label class="block text-[11px] font-medium text-slate-500 mb-1">Ville</label>
              <input v-model="formClient.ville" type="text" class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
          </div>

          <!-- Bloc Professionnel -->
          <div v-if="!formClient.est_particulier" class="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-3">
            <p class="text-[11px] font-bold text-slate-600 uppercase">Informations Professionnelles</p>
            <div class="grid grid-cols-2 gap-2">
              <div>
                <label class="block text-[10px] text-slate-500 mb-1">SIRET</label>
                <input v-model="formClient.siret" type="text" class="w-full border border-slate-300 p-2 rounded-lg text-xs bg-white" />
              </div>
              <div>
                <label class="block text-[10px] text-slate-500 mb-1">TVA Intracom.</label>
                <input v-model="formClient.tva_intra" :disabled="formClient.sans_tva" type="text" class="w-full border border-slate-300 p-2 rounded-lg text-xs bg-white disabled:bg-slate-100" />
              </div>
            </div>
            <div class="grid grid-cols-2 gap-2">
              <div>
                <label class="block text-[10px] text-slate-500 mb-1">RCS / RM</label>
                <input v-model="formClient.rcs" type="text" class="w-full border border-slate-300 p-2 rounded-lg text-xs bg-white" />
              </div>
              <div>
                <label class="block text-[10px] text-slate-500 mb-1">APE / NAF</label>
                <input v-model="formClient.ape" type="text" class="w-full border border-slate-300 p-2 rounded-lg text-xs bg-white" />
              </div>
            </div>

            <div class="space-y-2 pt-2 border-t border-slate-200">
              <div class="flex items-center gap-2">
                <input type="checkbox" id="sanstva" v-model="formClient.sans_tva" class="w-4 h-4 text-blue-600 rounded border-slate-300" />
                <label for="sanstva" class="text-xs text-slate-700">Exonérer ce client de TVA (Facturation HT)</label>
              </div>
              <div class="flex items-center gap-2">
                <input type="checkbox" id="recap" v-model="formClient.recap_interventions" class="w-4 h-4 text-blue-600 rounded border-slate-300" />
                <label for="recap" class="text-xs text-slate-700">Générer auto. le PDF Récapitulatif</label>
              </div>
              <div class="flex items-center gap-2">
                <input type="checkbox" id="multi" v-model="formClient.multi_etab" class="w-4 h-4 text-blue-600 rounded border-slate-300" />
                <label for="multi" class="text-xs text-slate-700">Client Multisite (Établissements secondaires)</label>
              </div>

              <div>
                <label class="block text-[10px] text-slate-500 mb-1">Modèle de facture</label>
                <select v-model="formClient.modele_facture" class="w-full border border-slate-300 p-2 rounded-lg text-xs bg-white">
                  <option value="condense">Facture condensée (Regroupée)</option>
                  <option value="detaille">Facture détaillée (Ligne par ligne)</option>
                </select>
              </div>
            </div>
          </div>

          <div class="flex gap-2 pt-3 border-t border-slate-100">
            <button type="button" @click="showModalClient = false" class="flex-1 py-2.5 bg-slate-100 text-slate-700 font-bold text-xs rounded-xl hover:bg-slate-200 transition uppercase">
              Annuler
            </button>
            <button type="button" @click="sauvegarderClient" class="flex-1 py-2.5 bg-emerald-600 text-white font-bold text-xs rounded-xl shadow-sm hover:bg-emerald-700 transition uppercase flex items-center justify-center gap-1.5">
              <span>✓</span> Enregistrer
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- MODALE ÉTABLISSEMENTS / MULTI-SITES -->
    <div v-if="showModalSites" class="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4 overflow-y-auto">
      <div class="bg-white w-full max-w-md rounded-2xl p-5 space-y-4 shadow-xl my-auto">
        <div class="flex justify-between items-center border-b border-slate-100 pb-3">
          <h3 class="text-sm font-bold text-slate-900">Sites : {{ clientSelectionneSites?.nom_societe }}</h3>
          <button @click="showModalSites = false" class="text-slate-400 hover:text-slate-600 text-sm font-bold">✕</button>
        </div>

        <div class="space-y-3 max-h-48 overflow-y-auto">
          <div v-if="listeSites.length === 0" class="text-xs text-slate-400 italic text-center py-2">Aucun site secondaire.</div>
          <div v-for="s in listeSites" :key="s.id" class="flex justify-between items-center p-2.5 bg-slate-50 rounded-lg border border-slate-200">
            <div>
              <p class="text-xs font-bold text-slate-800">{{ s.nom_site }}</p>
              <p class="text-[10px] text-slate-500">{{ s.adresse }}, {{ s.cp }} {{ s.ville }}</p>
            </div>
            <div class="flex gap-1">
              <button @click="editerSite(s)" class="p-1 bg-slate-200 text-slate-700 rounded text-xs">✏️</button>
              <button @click="supprimerSite(s.id)" class="p-1 bg-rose-100 text-rose-700 rounded text-xs">🗑️</button>
            </div>
          </div>
        </div>

        <div class="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-2">
          <p class="text-[11px] font-bold text-slate-600">{{ formSite.id ? 'Modifier le site' : 'Ajouter un site' }}</p>
          <input v-model="formSite.nom_site" type="text" placeholder="Nom du site (ex: Entrepôt Nord)" class="w-full border border-slate-300 p-2 rounded-lg text-xs bg-white" />
          <input v-model="formSite.adresse" type="text" placeholder="Adresse" class="w-full border border-slate-300 p-2 rounded-lg text-xs bg-white" />
          <div class="grid grid-cols-3 gap-2">
            <input v-model="formSite.cp" type="text" placeholder="CP" class="border border-slate-300 p-2 rounded-lg text-xs bg-white" />
            <input v-model="formSite.ville" type="text" placeholder="Ville" class="col-span-2 border border-slate-300 p-2 rounded-lg text-xs bg-white" />
          </div>
          <button @click="sauvegarderSite" class="w-full py-2 bg-emerald-600 text-white font-bold text-xs rounded-lg shadow-sm hover:bg-emerald-700 transition">
            {{ formSite.id ? 'Mettre à jour le site' : 'Ajouter ce site' }}
          </button>
        </div>

        <div class="flex justify-end pt-2 border-t border-slate-100">
          <button @click="showModalSites = false" class="py-2 px-4 bg-slate-100 text-slate-700 font-bold text-xs rounded-xl hover:bg-slate-200 transition">
            Fermer
          </button>
        </div>
      </div>
    </div>

    <!-- MODALE TARIFS SPÉCIFIQUES -->
    <div v-if="showModalTarifs" class="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4 overflow-y-auto">
      <div class="bg-white w-full max-w-lg rounded-2xl p-5 space-y-4 shadow-xl my-auto">
        <div class="flex justify-between items-center border-b border-slate-100 pb-3">
          <h3 class="text-sm font-bold text-slate-900">Tarifs spécifiques : {{ clientSelectionneTarifs?.nom_societe }}</h3>
          <button @click="showModalTarifs = false" class="text-slate-400 hover:text-slate-600 text-sm font-bold">✕</button>
        </div>

        <div class="space-y-3 max-h-60 overflow-y-auto pr-1">
          <div v-for="p in cataloguePrestations" :key="p.id" class="flex justify-between items-center bg-slate-50 p-2.5 rounded-xl border border-slate-100">
            <div>
              <p class="text-xs font-bold text-slate-800">{{ p.designation }}</p>
              <p class="text-[10px] text-slate-400">Standard : {{ p.prix_ht }} €</p>
            </div>
            <div class="flex items-center gap-1">
              <input v-model.number="tarifsClient[p.id]" type="number" step="0.01" class="w-24 border border-slate-300 p-1.5 rounded-lg text-xs text-right outline-none focus:ring-2 focus:ring-blue-500 bg-white" />
              <span class="text-xs text-slate-500">€</span>
            </div>
          </div>
        </div>

        <div class="flex gap-2 pt-3 border-t border-slate-100 mt-2">
          <button type="button" @click="showModalTarifs = false" class="flex-1 py-2.5 bg-slate-100 text-slate-700 font-bold text-xs rounded-xl hover:bg-slate-200 transition uppercase tracking-wider">
            Fermer
          </button>
          <button type="button" @click="sauvegarderTarifs" class="flex-1 py-2.5 bg-teal-600 text-white font-bold text-xs rounded-xl shadow-sm hover:bg-teal-700 transition uppercase tracking-wider flex items-center justify-center gap-1.5">
            <span>💾</span> Enregistrer les tarifs
          </button>
        </div>
      </div>
    </div>
  </div>
</template>