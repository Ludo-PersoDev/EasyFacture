<script setup>
import { ref, onMounted } from 'vue'
import { supabase } from '../../supabase'

const interventions = ref([])
const clients = ref([])
const cataloguePrestations = ref([])
const sitesSecondaires = ref([])
const loading = ref(true)
const showModal = ref(false)

// Champs du formulaire modale
const selectedClientId = ref('')
const selectedCatalogueId = ref('')
const titre = ref('')
const dateIntervention = ref(new Date().toISOString().split('T')[0])
const heureDebut = ref('09:00')
const heureFin = ref('10:00')
const tarif = ref('')
const siteId = ref('')
const description = ref('')

const fetchData = async () => {
  loading.value = true
  try {
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) return

    // 1. Récupération des interventions / prestations enregistrées
    const { data: interData, error: interError } = await supabase
      .from('interventions')
      .select('*')
      .eq('user_id', user.id)
      .order('date', { ascending: false })

    if (interError) throw interError

    // 2. Récupération des clients
    const { data: clientsData } = await supabase.from('clients').select('*')
    if (clientsData) clients.value = clientsData

    // 3. Récupération du catalogue des prestations de base (table 'catalogue_prestations' ou similaire, adapte si besoin)
    const { data: catData } = await supabase.from('catalogue_prestations').select('*')
    if (catData) cataloguePrestations.value = catData

    // Dictionnaire clients
    const clientsMap = {}
    (clientsData || []).forEach(c => {
      clientsMap[c.id] = c.nom_societe || `${c.prenom || ''} ${c.nom || ''}`.trim()
    })

    interventions.value = (interData || []).map(item => ({
      ...item,
      client_nom: clientsMap[item.client_id] || 'Client non spécifié'
    }))

  } catch (err) {
    console.error('Erreur chargement:', err)
  } finally {
    loading.value = false
  }
}

// Quand on sélectionne un client, on charge ses éventuels sites secondaires
const handleClientChange = async () => {
  sitesSecondaires.value = []
  siteId.value = ''
  if (!selectedClientId.value) return

  try {
    const { data } = await supabase
      .from('clients_sites') // ou la table gérant les sites secondaires de ton appli
      .select('*')
      .eq('client_id', selectedClientId.value)
    
    if (data) sitesSecondaires.value = data
  } catch (e) {
    console.warn("Pas de sites secondaires ou table absente", e)
  }
}

// Quand on choisit une prestation dans le catalogue, on pré-remplit le titre et le tarif de base
const handleCatalogueChange = () => {
  const selected = cataloguePrestations.value.find(p => p.id == selectedCatalogueId.value)
  if (selected) {
    titre.value = selected.titre || selected.nom || ''
    tarif.value = selected.tarif || selected.prix || ''
  }
}

const handleAddPrestation = async () => {
  try {
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) return

    const { error } = await supabase.from('interventions').insert([
      { 
        user_id: user.id,
        client_id: parseInt(selectedClientId.value),
        titre: titre.value,
        date: dateIntervention.value,
        heure_debut: heureDebut.value,
        heure_fin: heureFin.value,
        montant: tarif.value ? parseFloat(tarif.value) : 0,
        site_id: siteId.value ? parseInt(siteId.value) : null,
        description: description.value 
      }
    ])

    if (error) throw error

    // Reset et fermeture de la modale
    selectedClientId.value = ''
    selectedCatalogueId.value = ''
    titre.value = ''
    tarif.value = ''
    description.value = ''
    siteId.value = ''
    showModal.value = false

    await fetchData()
  } catch (err) {
    alert('Erreur lors de l’enregistrement : ' + err.message)
  }
}

onMounted(fetchData)
</script>

<template>
  <div class="space-y-4">
    <!-- En-tête -->
    <div class="flex justify-between items-center">
      <h2 class="text-xs font-bold text-slate-700 uppercase tracking-wider">Prestations de terrain</h2>
      <button @click="showModal = true" class="bg-blue-600 text-white text-xs px-3 py-1.5 rounded-xl font-medium shadow-sm hover:bg-blue-700 transition">
        + Saisir une prestation
      </button>
    </div>

    <!-- LISTE CONCISE DES PRESTATIONS -->
    <div v-if="loading" class="text-center py-8 text-xs text-slate-400">Chargement...</div>
    <div v-else-if="interventions.length === 0" class="bg-white p-6 rounded-xl border border-slate-200 text-center text-xs text-slate-500">
      Aucune prestation enregistrée.
    </div>
    <div v-else class="space-y-3">
      <div v-for="item in interventions" :key="item.id" class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col gap-1.5">
        <div class="flex justify-between items-start">
          <div>
            <h3 class="text-xs font-bold text-slate-900">{{ item.titre }}</h3>
            <p class="text-xs font-medium text-slate-600 mt-0.5">{{ item.client_nom }}</p>
          </div>
          <div class="text-right">
            <span class="text-[10px] text-slate-400 font-medium block">{{ item.date }}</span>
            <span class="text-[10px] text-blue-600 font-semibold" v-if="item.heure_debut">{{ item.heure_debut }} - {{ item.heure_fin }}</span>
          </div>
        </div>
        
        <div class="flex justify-between items-center pt-2 border-t border-slate-100 mt-1">
          <span class="text-xs font-extrabold text-slate-900" v-if="item.montant">{{ item.montant }} €</span>
          <span class="text-[11px] text-slate-500 italic truncate max-w-[200px]" v-if="item.description">{{ item.description }}</span>
        </div>
      </div>
    </div>

    <!-- FENÊTRE MODALE DE SAISIE COMPLÈTE -->
    <div v-if="showModal" class="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4 overflow-y-auto">
      <div class="bg-white w-full max-w-md rounded-2xl p-5 space-y-4 shadow-xl my-auto">
        <div class="flex justify-between items-center border-b border-slate-100 pb-3">
          <h3 class="text-sm font-bold text-slate-900">Saisir une prestation</h3>
          <button @click="showModal = false" class="text-slate-400 hover:text-slate-600 text-sm font-bold">✕</button>
        </div>

        <form @submit.prevent="handleAddPrestation" class="space-y-3">
          <!-- 1. Sélection du client en premier -->
          <div>
            <label class="block text-[11px] font-medium text-slate-700 mb-1">1. Client</label>
            <select v-model="selectedClientId" @change="handleClientChange" required class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500 bg-white">
              <option value="" disabled>Sélectionner un client</option>
              <option v-for="c in clients" :key="c.id" :value="c.id">
                {{ c.nom_societe || `${c.prenom || ''} ${c.nom || ''}`.trim() }}
              </option>
            </select>
          </div>

          <!-- Site secondaire (si le client en possède) -->
          <div v-if="sitesSecondaires.length > 0">
            <label class="block text-[11px] font-medium text-slate-700 mb-1">Site secondaire / Adresse</label>
            <select v-model="siteId" class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500 bg-white">
              <option value="">Adresse principale du client</option>
              <option v-for="s in sitesSecondaires" :key="s.id" :value="s.id">
                {{ s.nom_site || s.adresse }}
              </option>
            </select>
          </div>

          <!-- 2. Choix depuis le catalogue (optionnel pour pré-remplir) -->
          <div v-if="cataloguePrestations.length > 0">
            <label class="block text-[11px] font-medium text-slate-700 mb-1">2. Modèle du Catalogue (Optionnel)</label>
            <select v-model="selectedCatalogueId" @change="handleCatalogueChange" class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500 bg-white">
              <option value="">-- Choisir dans le catalogue ou saisir librement --</option>
              <option v-for="p in cataloguePrestations" :key="p.id" :value="p.id">
                {{ p.titre || p.nom }} ({{ p.tarif || p.prix || 0 }} €)
              </option>
            </select>
          </div>

          <!-- Titre / Intitulé modifiable -->
          <div>
            <label class="block text-[11px] font-medium text-slate-700 mb-1">Intitulé de la prestation</label>
            <input v-model="titre" type="text" required placeholder="Ex: Cours particulier..." class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500" />
          </div>

          <!-- Date et Tarif modifiable -->
          <div class="grid grid-cols-2 gap-2">
            <div>
              <label class="block text-[11px] font-medium text-slate-700 mb-1">Date</label>
              <input v-model="dateIntervention" type="date" required class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label class="block text-[11px] font-medium text-slate-700 mb-1">Tarif (€) (Ajustable)</label>
              <input v-model="tarif" type="number" step="0.01" required class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500 font-bold text-slate-900" />
            </div>
          </div>

          <!-- Horaires : Début et Fin -->
          <div class="grid grid-cols-2 gap-2">
            <div>
              <label class="block text-[11px] font-medium text-slate-700 mb-1">Heure de début</label>
              <input v-model="heureDebut" type="time" required class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label class="block text-[11px] font-medium text-slate-700 mb-1">Heure de fin</label>
              <input v-model="heureFin" type="time" required class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
          </div>

          <!-- Notes / Description -->
          <div>
            <label class="block text-[11px] font-medium text-slate-700 mb-1">Notes / Description</label>
            <textarea v-model="description" rows="2" placeholder="Détails de l'intervention..." class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500"></textarea>
          </div>

          <div class="flex gap-2 pt-2">
            <button type="button" @click="showModal = false" class="flex-1 py-2.5 bg-slate-100 text-slate-700 font-medium text-xs rounded-lg hover:bg-slate-200 transition">
              Annuler
            </button>
            <button type="submit" class="flex-1 py-2.5 bg-emerald-600 text-white font-medium text-xs rounded-lg shadow-sm hover:bg-emerald-700 transition">
              Enregistrer
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>