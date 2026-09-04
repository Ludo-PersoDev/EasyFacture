<script setup>
import { ref, onMounted } from 'vue'
import { supabase } from '../../supabase'

const totalCaMois = ref(0)
const totalEncaisse = ref(0)
const facturesARecouvrir = ref(0)
const loading = ref(true)

// Simulation de récupération rapide des indicateurs financiers et de Factur-X
const fetchDashboardData = async () => {
  try {
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) return

    // Exemple de requête sur les factures pour alimenter les chiffres clés du mois
    const { data: factures, error } = await supabase
      .from('factures')
      .select('montant_ttc, statut, facturx_statut')
      .eq('user_id', user.id)

    if (error) throw error

    if (factures) {
      totalCaMois.value = factures.reduce((acc, f) => acc + (f.montant_ttc || 0), 0)
      totalEncaisse.value = factures.filter(f => f.statut === 'Payée').reduce((acc, f) => acc + (f.montant_ttc || 0), 0)
      facturesARecouvrir.value = factures.filter(f => f.statut !== 'Payée').length
    }
  } catch (err) {
    console.error("Erreur chargement dashboard :", err)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchDashboardData()
})
</script>

<template>
  <div class="space-y-4">
    <!-- En-tête de bienvenue -->
    <div class="bg-gradient-to-r from-blue-600 to-indigo-700 text-white p-5 rounded-2xl shadow-md">
      <h1 class="text-lg font-bold">Bonjour 👋</h1>
      <p class="text-xs text-blue-100 mt-1">Vue d'ensemble de votre activité sur le terrain.</p>
    </div>

    <!-- Indicateurs Clés (Chiffres et infos clés) -->
    <div class="grid grid-cols-2 gap-3">
      <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
        <span class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">CA Total / En cours</span>
        <div class="text-xl font-extrabold text-slate-900 mt-1">
          {{ loading ? '...' : totalCaMois.toFixed(2) }} €
        </div>
      </div>

      <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
        <span class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Encaissé</span>
        <div class="text-xl font-extrabold text-emerald-600 mt-1">
          {{ loading ? '...' : totalEncaisse.toFixed(2) }} €
        </div>
      </div>
    </div>

    <!-- Widget Statut Factur-X (Lecture seule terrain) -->
    <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
      <div class="flex items-center justify-between mb-3">
        <h2 class="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
          <span class="material-icons text-sky-500 text-base">cloud_done</span> Passerelle Factur-X
        </h2>
        <span class="text-[10px] font-medium px-2 py-0.5 bg-sky-50 text-sky-700 rounded-full border border-sky-100">Mode Lecture</span>
      </div>
      
      <div class="flex justify-between items-center text-xs py-2 border-t border-slate-100">
        <span class="text-slate-600">Factures à transmettre :</span>
        <span class="font-bold text-amber-600">3 en attente</span>
      </div>
      <div class="flex justify-between items-center text-xs py-2 border-t border-slate-100">
        <span class="text-slate-600">Dernière transmission :</span>
        <span class="font-medium text-slate-800">Hier, 18:42</span>
      </div>
    </div>
  </div>
</template>