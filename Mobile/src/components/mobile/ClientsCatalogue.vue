<script setup>
import { ref, onMounted } from 'vue'
import { supabase } from '../../supabase'

const currentSubTab = ref('clients')
const items = ref([])
const loading = ref(true)

const fetchData = async () => {
  loading.value = true
  try {
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) return

    const table = currentSubTab.value === 'clients' ? 'clients' : 'prestations'
    const { data, error } = await supabase
      .from(table)
      .select('*')
      .eq('user_id', user.id)

    if (error) throw error
    items.value = data || []
  } catch (err) {
    console.error('Erreur chargement:', err)
  } finally {
    loading.value = false
  }
}

onMounted(fetchData)
</script>

<template>
  <div class="space-y-4">
    <div class="flex bg-slate-200 p-1 rounded-xl">
      <button 
        @click="currentSubTab = 'clients'; fetchData()" 
        :class="currentSubTab === 'clients' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600'"
        class="flex-1 py-2 text-xs font-bold rounded-lg transition"
      >
        Clients
      </button>
      <button 
        @click="currentSubTab = 'catalogue'; fetchData()" 
        :class="currentSubTab === 'catalogue' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600'"
        class="flex-1 py-2 text-xs font-bold rounded-lg transition"
      >
        Catalogue
      </button>
    </div>

    <div v-if="loading" class="text-center py-8 text-xs text-slate-400">Chargement...</div>
    <div v-else-if="items.length === 0" class="bg-white p-6 rounded-xl border border-slate-200 text-center text-xs text-slate-500">
      Aucun élément enregistré.
    </div>
    <div v-else class="space-y-3">
      <div v-for="item in items" :key="item.id" class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
        <div v-if="currentSubTab === 'clients'">
          <h3 class="text-xs font-bold text-slate-900">{{ item.nom || item.entreprise || 'Client sans nom' }}</h3>
          <p class="text-xs text-slate-500 mt-0.5">{{ item.email || 'Pas d’email' }} • {{ item.telephone || 'Pas de téléphone' }}</p>
        </div>
        <div v-else>
          <h3 class="text-xs font-bold text-slate-900">{{ item.titre || item.nom || 'Prestation' }}</h3>
          <p class="text-xs text-slate-500 mt-0.5">{{ item.description || 'Aucune description' }}</p>
          <div class="text-xs font-semibold text-blue-600 mt-2">{{ item.prix_ht || item.tarif || 0 }} € HT</div>
        </div>
      </div>
    </div>
  </div>
</template>