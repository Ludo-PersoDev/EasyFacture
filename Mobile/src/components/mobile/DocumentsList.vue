<script setup>
import { ref, onMounted } from 'vue'
import { supabase } from '../../supabase'

const activeTab = ref('factures')
const documents = ref([])
const loading = ref(true)

const fetchDocuments = async () => {
  loading.value = true
  try {
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) return

    const table = activeTab.value === 'factures' ? 'factures' : 'devis'
    const { data, error } = await supabase
      .from(table)
      .select('*')
      .eq('user_id', user.id)
      .order('date_creation', { ascending: false })

    if (error) throw error
    documents.value = data || []
  } catch (err) {
    console.error('Erreur chargement documents:', err)
  } finally {
    loading.value = false
  }
}

const viewPdf = async (doc) => {
  if (!doc.pdf_url) {
    alert('Aucun PDF disponible pour ce document.')
    return
  }
  const { data } = supabase.storage.from('documents').getPublicUrl(doc.pdf_url)
  if (data?.publicUrl) {
    window.open(data.publicUrl, '_blank')
  }
}

onMounted(fetchDocuments)
</script>

<template>
  <div class="space-y-4">
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

    <div v-if="loading" class="text-center py-8 text-xs text-slate-400">Chargement...</div>
    <div v-else-if="documents.length === 0" class="bg-white p-6 rounded-xl border border-slate-200 text-center text-xs text-slate-500">
      Aucun document trouvé.
    </div>
    <div v-else class="space-y-3">
      <div v-for="doc in documents" :key="doc.id" class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col gap-2">
        <div class="flex justify-between items-start">
          <div>
            <span class="text-xs font-bold text-slate-900">{{ doc.numero_facture || doc.numero_devis || 'Brouillon' }}</span>
            <p class="text-xs text-slate-500">{{ doc.client_id || 'Client inconnu' }}</p>
          </div>
          <span :class="doc.statut === 'Payée' ? 'bg-emerald-50 text-emerald-700 border-emerald-100' : 'bg-amber-50 text-amber-700 border-amber-100'" class="text-[10px] px-2 py-0.5 rounded-full border font-medium">
            {{ doc.statut || 'En attente' }}
          </span>
        </div>

        <div class="flex justify-between items-center pt-2 border-t border-slate-100 mt-1">
          <span class="text-sm font-extrabold text-slate-900">{{ doc.total_ttc || 0 }} €</span>
          <button @click="viewPdf(doc)" class="flex items-center gap-1 text-xs bg-blue-50 text-blue-600 px-3 py-1.5 rounded-lg font-medium hover:bg-blue-100 transition">
            <span class="material-icons text-sm">visibility</span> Voir PDF
          </button>
        </div>
      </div>
    </div>
  </div>
</template>