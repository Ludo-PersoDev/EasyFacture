<script setup>
import { ref, onMounted } from 'vue'
import { supabase } from '../../supabase'

const interventions = ref([])
const loading = ref(true)
const showForm = ref(false)
const titre = ref('')
const description = ref('')
const dateIntervention = ref(new Date().toISOString().split('T')[0])

const fetchInterventions = async () => {
  loading.value = true
  try {
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) return

    const { data, error } = await supabase
      .from('interventions')
      .select('*')
      .eq('user_id', user.id)
      .order('date', { ascending: false })

    if (error) throw error
    interventions.value = data || []
  } catch (err) {
    console.error('Erreur interventions:', err)
  } finally {
    loading.value = false
  }
}

const handleAddIntervention = async () => {
  try {
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) return

    const { error } = await supabase.from('interventions').insert([
      { user_id: user.id, titre: titre.value, description: description.value, date: dateIntervention.value }
    ])

    if (error) throw error

    titre.value = ''
    description.value = ''
    showForm.value = false
    await fetchInterventions()
  } catch (err) {
    alert('Erreur lors de l’ajout : ' + err.message)
  }
}

onMounted(fetchInterventions)
</script>

<template>
  <div class="space-y-4">
    <div class="flex justify-between items-center">
      <h2 class="text-xs font-bold text-slate-700 uppercase tracking-wider">Prestations de terrain</h2>
      <button @click="showForm = !showForm" class="bg-blue-600 text-white text-xs px-3 py-1.5 rounded-xl font-medium shadow-sm hover:bg-blue-700 transition">
        {{ showForm ? 'Annuler' : '+ Saisir une intervention' }}
      </button>
    </div>

    <form v-if="showForm" @submit.prevent="handleAddIntervention" class="bg-white p-4 rounded-xl border border-slate-200 space-y-3 shadow-sm">
      <div>
        <label class="block text-[11px] font-medium text-slate-700 mb-1">Titre / Prestation</label>
        <input v-model="titre" type="text" required class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500" />
      </div>
      <div>
        <label class="block text-[11px] font-medium text-slate-700 mb-1">Date</label>
        <input v-model="dateIntervention" type="date" required class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500" />
      </div>
      <div>
        <label class="block text-[11px] font-medium text-slate-700 mb-1">Description / Notes</label>
        <textarea v-model="description" rows="2" class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500"></textarea>
      </div>
      <button type="submit" class="w-full py-2.5 bg-emerald-600 text-white font-medium text-xs rounded-lg shadow-sm hover:bg-emerald-700 transition">
        Enregistrer l'intervention
      </button>
    </form>

    <div v-if="loading" class="text-center py-8 text-xs text-slate-400">Chargement...</div>
    <div v-else-if="interventions.length === 0" class="bg-white p-6 rounded-xl border border-slate-200 text-center text-xs text-slate-500">
      Aucune intervention enregistrée sur le terrain.
    </div>
    <div v-else class="space-y-3">
      <div v-for="item in interventions" :key="item.id" class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
        <div class="flex justify-between items-start">
          <h3 class="text-xs font-bold text-slate-900">{{ item.titre }}</h3>
          <span class="text-[10px] text-slate-400 font-medium">{{ item.date }}</span>
        </div>
        <p class="text-xs text-slate-600 mt-1">{{ item.description || 'Aucune note' }}</p>
      </div>
    </div>
  </div>
</template>