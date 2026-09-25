<script setup>
import { ref, onMounted } from 'vue'
import { supabase } from '../../supabase'

const interventions = ref([])
const clients = ref([])
const loading = ref(true)
const showForm = ref(false)

// Champs du formulaire de saisie complète
const titre = ref('')
const clientId = ref('')
const dateIntervention = ref(new Date().toISOString().split('T')[0])
const montant = ref('')
const description = ref('')

const fetchData = async () => {
  loading.value = true
  try {
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) return

    // 1. Récupération des prestations/interventions
    const { data: interData, error: interError } = await supabase
      .from('interventions')
      .select('*')
      .eq('user_id', user.id)
      .order('date', { ascending: false })

    if (interError) throw interError

    // 2. Récupération des clients pour les associer
    const { data: clientsData, error: clientsError } = await supabase
      .from('clients')
      .select('id, nom, nom_societe, prenom')

    if (!clientsError && clientsData) {
      clients.value = clientsData
    }

    // Création d'un dictionnaire client_id -> nom
    const clientsMap = {}
    clients.value.forEach(c => {
      clientsMap[c.id] = c.nom_societe || c.nom || c.prenom || 'Client sans nom'
    })

    // Association des données
    interventions.value = (interData || []).map(item => ({
      ...item,
      client_nom: clientsMap[item.client_id] || 'Client non spécifié'
    }))

  } catch (err) {
    console.error('Erreur chargement prestations:', err)
  } finally {
    loading.value = false
  }
}

const handleAddPrestation = async () => {
  try {
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) return

    const { error } = await supabase.from('interventions').insert([
      { 
        user_id: user.id, 
        titre: titre.value, 
        client_id: clientId.value ? parseInt(clientId.value) : null,
        date: dateIntervention.value,
        montant: montant.value ? parseFloat(montant.value) : 0,
        description: description.value 
      }
    ])

    if (error) throw error

    // Réinitialisation du formulaire
    titre.value = ''
    clientId.value = ''
    montant.value = ''
    description.value = ''
    dateIntervention.value = new Date().toISOString().split('T')[0]
    showForm.value = false

    await fetchData()
  } catch (err) {
    alert('Erreur lors de l’enregistrement : ' + err.message)
  }
}

onMounted(fetchData)
</script>

<template>
  <div class="space-y-4">
    <!-- En-titre et bouton -->
    <div class="flex justify-between items-center">
      <h2 class="text-xs font-bold text-slate-700 uppercase tracking-wider">Prestations de terrain</h2>
      <button @click="showForm = !showForm" class="bg-blue-600 text-white text-xs px-3 py-1.5 rounded-xl font-medium shadow-sm hover:bg-blue-700 transition">
        {{ showForm ? 'Annuler' : '+ Saisir une prestation' }}
      </button>
    </div>

    <!-- Formulaire de saisie complète -->
    <form v-if="showForm" @submit.prevent="handleAddPrestation" class="bg-white p-4 rounded-xl border border-slate-200 space-y-3 shadow-sm">
      <div>
        <label class="block text-[11px] font-medium text-slate-700 mb-1">Titre de la prestation</label>
        <input v-model="titre" type="text" required placeholder="Ex: Cours de danse, Atelier..." class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500" />
      </div>

      <div>
        <label class="block text-[11px] font-medium text-slate-700 mb-1">Client</label>
        <select v-model="clientId" required class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500 bg-white">
          <option value="" disabled>Sélectionner un client</option>
          <option v-for="c in clients" :key="c.id" :value="c.id">
            {{ c.nom_societe || `${c.prenom || ''} ${c.nom || ''}`.trim() }}
          </option>
        </select>
      </div>

      <div class="grid grid-cols-2 gap-2">
        <div>
          <label class="block text-[11px] font-medium text-slate-700 mb-1">Date</label>
          <input v-model="dateIntervention" type="date" required class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
        <div>
          <label class="block text-[11px] font-medium text-slate-700 mb-1">Montant (€)</label>
          <input v-model="montant" type="number" step="0.01" placeholder="0.00" class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500" />
        </div>
      </div>

      <div>
        <label class="block text-[11px] font-medium text-slate-700 mb-1">Description / Notes</label>
        <textarea v-model="description" rows="2" placeholder="Détails de la prestation..." class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500"></textarea>
      </div>

      <button type="submit" class="w-full py-2.5 bg-emerald-600 text-white font-medium text-xs rounded-lg shadow-sm hover:bg-emerald-700 transition">
        Enregistrer la prestation
      </button>
    </form>

    <!-- Liste concise des prestations -->
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
          <span class="text-[10px] text-slate-400 font-medium">{{ item.date }}</span>
        </div>
        
        <div class="flex justify-between items-center pt-2 border-t border-slate-100 mt-1" v-if="item.montant || item.description">
          <span class="text-xs font-extrabold text-slate-900" v-if="item.montant">{{ item.montant }} €</span>
          <span class="text-[11px] text-slate-500 italic truncate max-w-[200px]" v-if="item.description">{{ item.description }}</span>
        </div>
      </div>
    </div>
  </div>
</template>