<script setup>
import { ref, onMounted } from 'vue'
import { supabase } from '../../supabase'

const activeTab = ref('factures')
const documents = ref([])
const loading = ref(true)
const debugError = ref(null)

const fetchDocuments = async () => {
  loading.value = true
  debugError.value = null
  try {
    const table = activeTab.value === 'factures' ? 'factures' : 'devis'
    console.log("Tentative de récupération de la table :", table)
    
    const { data, error } = await supabase
      .from(table)
      .select('*')

    console.log("Résultat brut Supabase - Data:", data)
    console.log("Résultat brut Supabase - Error:", error)

    if (error) throw error
    documents.value = data || []
  } catch (err) {
    console.error('Erreur attrapée :', err)
    debugError.value = err.message || JSON.stringify(err)
  } finally {
    loading.value = false
  }
}

onMounted(fetchDocuments)
</script>

<template>
  <div class="space-y-4">
    <!-- Sélecteur Factures / Devis -->
    <div class="flex bg-slate-200 p-1 rounded-xl">
      <button 
        @click="activeTab = 'factures'; fetchDocuments()" 
        :class="activeTab === 'factures' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600'"
        class="flex-1 py-2 text-xs font-bold rounded-lg transition"
      >
        Factures
      </button>
      <button 
        @click="activeTab = 'devis'; fetchDocuments()" 
        :class="activeTab === 'devis' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-600'"
        class="flex-1 py-2 text-xs font-bold rounded-lg transition"
      >
        Devis
      </button>
    </div>

    <!-- Affichage d'une éventuelle erreur à l'écran pour diagnostic -->
    <div v-if="debugError" class="bg-red-50 border border-red-200 text-red-700 p-3 rounded-xl text-xs">
      <strong>Erreur Supabase :</strong> {{ debugError }}
    </div>

    <div v-if="loading" class="text-center py-8 text-xs text-slate-400">Chargement...</div>
    <div v-else-if="documents.length === 0" class="bg-white p-6 rounded-xl border border-slate-200 text-center text-xs text-slate-500">
      Aucun document trouvé dans la table "{{ activeTab }}".
    </div>
    <div v-else class="space-y-3">
      <div v-for="doc in documents" :key="doc.id || doc.numero" class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col gap-2">
        <div class="flex justify-between items-start">
          <div>
            <span class="text-xs font-bold text-slate-900">{{ doc.numero || 'Brouillon' }}</span>
            <p class="text-xs font-medium text-slate-600 mt-0.5">
              Client ID : {{ doc.client_id }}
            </p>
            <p class="text-[10px] text-slate-400 mt-0.5" v-if="doc.date_echeance">
              Échéance : {{ doc.date_echeance }}
            </p>
          </div>
          <span class="text-[10px] px-2 py-0.5 rounded-full border font-medium bg-amber-50 text-amber-700 border-amber-100">
            {{ doc.statut || 'En attente' }}
          </span>
        </div>

        <div class="flex justify-between items-center pt-2 border-t border-slate-100 mt-1">
          <span class="text-sm font-extrabold text-slate-900">{{ doc.montant_ttc || 0 }} €</span>
        </div>
      </div>
    </div>
  </div>
</template>