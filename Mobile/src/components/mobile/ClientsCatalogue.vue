<script setup>
import { ref, onMounted } from 'vue'
import { supabase } from '../../supabase'

const tab = ref('clients')

// --- CLIENTS ---
const clients = ref([])
const loadingClients = ref(false)
const showModalClient = ref(false)
const isEditClient = ref(false)
const currentClientId = ref(null)

// Formulaire Client
const formClient = ref({
  nom_societe: '',
  contact: '',
  email: '',
  telephone: '',
  adresse: '',
  cp: '',
  ville: '',
  multi_etab: false
})

// --- TARIFS SPÉCIFIQUES ---
const showModalTarifs = ref(false)
const clientSelectionneTarifs = ref(null)
const cataloguePrestations = ref([])
const tarifsClient = ref({})

// --- PRESTATATIONS (Catalogue - Création simple) ---
const formPresta = ref({
  designation: '',
  unite: 'Heure',
  prix_ht: 0,
  taux_tva: 20.0
})

// Charger les clients
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

// Ouvrir modale client (Création / Edition)
const ouvrirModalClient = (client = null) => {
  if (client) {
    isEditClient.value = true
    currentClientId.value = client.id
    formClient.value = {
      nom_societe: client.nom_societe || '',
      contact: client.contact || '',
      email: client.email || '',
      telephone: client.telephone || '',
      adresse: client.adresse || '',
      cp: client.cp || '',
      ville: client.ville || '',
      multi_etab: !!client.multi_etab
    }
  } else {
    isEditClient.value = false
    currentClientId.value = null
    formClient.value = {
      nom_societe: '',
      contact: '',
      email: '',
      telephone: '',
      adresse: '',
      cp: '',
      ville: '',
      multi_etab: false
    }
  }
  showModalClient.value = true
}

const sauvegarderClient = async () => {
  if (!formClient.value.nom_societe.trim()) {
    alert('Le nom de la société ou du client est obligatoire.')
    return
  }

  try {
    if (isEditClient.value) {
      const { error } = await supabase
        .from('clients')
        .update(formClient.value)
        .eq('id', currentClientId.value)
      if (error) throw error
    } else {
      const { error } = await supabase
        .from('clients')
        .insert([formClient.value])
      if (error) throw error
    }
    showModalClient.value = false
    await fetchClients()
  } catch (err) {
    alert('Erreur lors de l’enregistrement du client : ' + err.message)
  }
}

const supprimerClient = async (id) => {
  if (!confirm('Voulez-vous vraiment supprimer ce client ?')) return
  try {
    const { error } = await supabase.from('clients').delete().eq('id', id)
    if (error) throw error
    await fetchClients()
  } catch (err) {
    alert('Erreur lors de la suppression : ' + err.message)
  }
}

// Ouvrir gestion des tarifs spécifiques d'un client
const ouvrirModalTarifs = async (client) => {
  clientSelectionneTarifs.value = client
  try {
    // 1. Récupérer le catalogue global
    const { data: catData } = await supabase.from('prestations').select('*').order('designation')
    cataloguePrestations.value = catData || []

    // 2. Récupérer les tarifs existants pour ce client
    const { data: tarifsData } = await supabase.from('client_tarifs').select('*').eq('client_id', client.id)
    
    const mapTarifs = {}
    if (tarifsData) {
      tarifsData.forEach(t => {
        mapTarifs[t.prestation_id] = t.prix_specifique_ht
      })
    }
    
    // Initialiser les inputs
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
    alert('Tarifs mis à jour avec succès !')
  } catch (err) {
    alert('Erreur lors de l’enregistrement des tarifs : ' + err.message)
  }
}

// --- CREATION PRESTATION ---
const creerPrestation = async () => {
  if (!formPresta.value.designation.trim()) {
    alert('Veuillez saisir une désignation.')
    return
  }

  try {
    const { error } = await supabase.from('prestations').insert([formPresta.value])
    if (error) throw error

    alert('Prestation ajoutée au catalogue avec succès !')
    formPresta.value = {
      designation: '',
      unite: 'Heure',
      prix_ht: 0,
      taux_tva: 20.0
    }
  } catch (err) {
    alert('Erreur lors de la création de la prestation : ' + err.message)
  }
}

onMounted(() => {
  fetchClients()
})
</script>

<template>
  <div class="space-y-4">
    <!-- Navigation par onglets internes -->
    <div class="flex border-b border-slate-200">
      <button 
        @click="tab = 'clients'" 
        class="flex-1 pb-3 text-xs font-bold uppercase tracking-wider transition border-b-2"
        :class="tab === 'clients' ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-400 hover:text-slate-600'">
        Gestion des Clients
      </button>
      <button 
        @click="tab = 'pre prestations'" 
        class="flex-1 pb-3 text-xs font-bold uppercase tracking-wider transition border-b-2"
        :class="tab === 'pre prestations' ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-400 hover:text-slate-600'">
        Créer une Prestation
      </button>
    </div>

    <!-- ONGLET 1 : GESTION DES CLIENTS -->
    <div v-if="tab === 'clients'" class="space-y-4">
      <div class="flex justify-between items-center">
        <h2 class="text-xs font-bold text-slate-700 uppercase tracking-wider">Annuaire des clients</h2>
        <button @click="ouvrirModalClient()" class="bg-blue-600 text-white text-xs px-3 py-1.5 rounded-xl font-medium shadow-sm hover:bg-blue-700 transition">
          + Nouveau Client
        </button>
      </div>

      <div v-if="loadingClients" class="text-center py-8 text-xs text-slate-400">Chargement des clients...</div>
      <div v-else-if="clients.length === 0" class="bg-white p-6 rounded-xl border border-slate-200 text-center text-xs text-slate-500">
        Aucun client enregistré.
      </div>
      <div v-else class="space-y-3">
        <div v-for="client in clients" :key="client.id" class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col gap-2">
          <div class="flex justify-between items-start">
            <div>
              <h3 class="text-xs font-bold text-slate-900">{{ client.nom_societe }}</h3>
              <p class="text-xs text-slate-500" v-if="client.contact">Contact : {{ client.contact }}</p>
              <p class="text-xs text-slate-400">{{ client.adresse || 'Adresse non renseignée' }} - {{ client.cp }} {{ client.ville }}</p>
            </div>
            <div class="flex gap-1">
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

    <!-- ONGLET 2 : CRÉATION DE PRESTATION -->
    <div v-if="tab === 'pre prestations'" class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-4">
      <h2 class="text-xs font-bold text-slate-700 uppercase tracking-wider border-b border-slate-100 pb-2">Ajouter une prestation au catalogue</h2>

      <div class="space-y-3">
        <div>
          <label class="block text-[11px] font-medium text-slate-500 mb-1">Désignation *</label>
          <input v-model="formPresta.designation" type="text" placeholder="Ex: Cours particulier, Intervention technique..." class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500" />
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
          <select v-model.number="formPresta.taux_tva" class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500 bg-white">
            <option :value="0.0">0 % (Exonéré)</option>
            <option :value="5.5">5.5 %</option>
            <option :value="10.0">10 %</option>
            <option :value="20.0">20 % (Standard)</option>
          </select>
        </div>

        <button @click="creerPrestation" class="w-full py-2.5 bg-blue-600 text-white font-bold text-xs rounded-xl shadow-sm hover:bg-blue-700 transition uppercase tracking-wider mt-2">
          Enregistrer la prestation
        </button>
      </div>
    </div>

    <!-- MODALE CLIENT (Création / Edition) -->
    <div v-if="showModalClient" class="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4 overflow-y-auto">
      <div class="bg-white w-full max-w-md rounded-2xl p-5 space-y-4 shadow-xl my-auto">
        <div class="flex justify-between items-center border-b border-slate-100 pb-3">
          <h3 class="text-sm font-bold text-slate-900">{{ isEditClient ? 'Modifier le client' : 'Nouveau client' }}</h3>
          <button @click="showModalClient = false" class="text-slate-400 hover:text-slate-600 text-sm font-bold">✕</button>
        </div>

        <div class="space-y-3">
          <div>
            <label class="block text-[11px] font-medium text-slate-500 mb-1">Nom / Société *</label>
            <input v-model="formClient.nom_societe" type="text" class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500" />
          </div>

          <div>
            <label class="block text-[11px] font-medium text-slate-500 mb-1">Nom du contact</label>
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

          <div class="flex gap-2 pt-3 border-t border-slate-100 mt-2">
            <button type="button" @click="showModalClient = false" class="flex-1 py-2.5 bg-slate-100 text-slate-700 font-bold text-xs rounded-xl hover:bg-slate-200 transition uppercase tracking-wider">
              Annuler
            </button>
            <button type="button" @click="sauvegarderClient" class="flex-1 py-2.5 bg-emerald-600 text-white font-bold text-xs rounded-xl shadow-sm hover:bg-emerald-700 transition uppercase tracking-wider flex items-center justify-center gap-1.5">
              <span>✓</span> Enregistrer
            </button>
          </div>
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