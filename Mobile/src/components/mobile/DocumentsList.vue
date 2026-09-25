<script setup>
import { ref, onMounted } from 'vue'
import { supabase } from '../../supabase'

const activeTab = ref('factures')
const documents = ref([])
const loading = ref(true)

const fetchDocuments = async () => {
  loading.value = true
  try {
    const table = activeTab.value === 'factures' ? 'factures' : 'devis'
    
    // 1. Récupération des documents
    const { data: docsData, error: docsError } = await supabase
      .from(table)
      .select('*')

    if (docsError) throw docsError

    // 2. Récupération des clients
    let clientsMap = {}
    try {
      const { data: clientsData, error: clientsError } = await supabase
        .from('clients')
        .select('*')
      
      if (!clientsError && clientsData) {
        clientsData.forEach(client => {
          // On enregistre sous toutes les formes possibles d'ID (string, number) pour être blindé
          if (client.id !== undefined) {
            clientsMap[client.id] = client
            clientsMap[String(client.id)] = client
          }
          if (client.uuid !== undefined) {
            clientsMap[client.uuid] = client
            clientsMap[String(client.uuid)] = client
          }
        })
      }
    } catch (e) {
      console.warn("Exception clients :", e)
    }

    // 3. Association des noms
    documents.value = (docsData || []).map(doc => {
      // Gestion des différents noms possibles pour le numéro et le client
      const numeroDoc = doc.numero_facture || doc.numero_devis || doc.numero || 'Brouillon'
      
      const directName = doc.nom_client || doc.client_nom || doc.client_name || doc.nom
      
      const clientObj = clientsMap[doc.client_id] || clientsMap[String(doc.client_id)] || null
      
      const resolvedName = directName || 
                           clientObj?.nom_societe || 
                           clientObj?.nom || 
                           clientObj?.prenom || 
                           (doc.client_id ? `Client ID: ${doc.client_id}` : 'Client non spécifié')

      return {
        ...doc,
        numero_ffiche: numeroDoc,
        resolved_client_name: resolvedName
      }
    })

  } catch (err) {
    console.error('Erreur chargement documents:', err)
  } finally {
    loading.value = false
  }
}

const viewPdf = (doc) => {
  const url = doc.pdf_url
  if (!url) {
    alert('Aucun lien PDF enregistré pour ce document.')
    return
  }
  
  console.log("Tentative d'ouverture de l'URL :", url)
  window.open(url, '_blank')
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

    <div v-if="loading" class="text-center py-8 text-xs text-slate-400">Chargement...</div>
    <div v-else-if="documents.length === 0" class="bg-white p-6 rounded-xl border border-slate-200 text-center text-xs text-slate-500">
      Aucun document trouvé.
    </div>
    <div v-else class="space-y-3">
      <div v-for="doc in documents" :key="doc.id" class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col gap-2">
        <div class="flex justify-between items-start">
          <div>
            <!-- Utilisation du numéro correct (numero_facture / numero_devis) -->
            <span class="text-xs font-bold text-slate-900">{{ doc.numero_ffiche }}</span>
            
            <!-- Nom du client résolu -->
            <p class="text-xs font-medium text-slate-600 mt-0.5">
              {{ doc.resolved_client_name }}
            </p>
            
            <!-- Date d'échéance -->
            <p class="text-[10px] text-slate-400 mt-0.5" v-if="doc.date_echeance">
              Échéance : {{ doc.date_echeance }}
            </p>
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