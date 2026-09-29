<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { supabase } from '../../supabase'

const factures = ref([])
const interventions = ref([])
const loading = ref(true)
const userName = ref('')

// Filtres temporels
const currentYear = new Date().getFullYear().toString()
const selectedYear = ref(currentYear)
const selectedMonth = ref('all')
const selectedWeek = ref(null)

const semainesDuMois = computed(() => {
  if (selectedMonth.value === 'all' || !selectedMonth.value) return []

  const annee = parseInt(selectedYear.value)
  const mois = parseInt(selectedMonth.value)
  
  const premierJour = new Date(annee, mois - 1, 1)
  const dernierJour = new Date(annee, mois, 0)

  let semaines = []
  let debutCourant = new Date(premierJour)

  while (debutCourant <= dernierJour) {
    let finSemaine = new Date(debutCourant)
    let jourSemaine = finSemaine.getDay() === 0 ? 7 : finSemaine.getDay()
    let joursRestantsAvantDimanche = 7 - jourSemaine
    
    finSemaine.setDate(finSemaine.getDate() + joursRestantsAvantDimanche)
    if (finSemaine > dernierJour) finSemaine = new Date(dernierJour)

    semaines.push({
      debut: new Date(debutCourant),
      fin: new Date(finSemaine),
      label: `Du ${debutCourant.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' })} au ${finSemaine.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' })}`
    })

    debutCourant = new Date(finSemaine)
    debutCourant.setDate(debutCourant.getDate() + 1)
  }

  return semaines
})

watch([selectedMonth, selectedYear], () => {
  selectedWeek.value = null
})

const fetchDashboardData = async () => {
  try {
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) return

    userName.value = user.user_metadata?.prenom || user.user_metadata?.full_name || 'Utilisateur'

    const { data: factData, error: factError } = await supabase
      .from('factures')
      .select('total_ttc, total_ht, statut, date_creation, date_echeance, mode_reglement')
      .eq('user_id', user.id)

    if (factError) throw factError
    factures.value = factData || []

    const { data: interData, error: interError } = await supabase
      .from('interventions')
      .select('date, prix_final_ht, quantite, facture_id')

    if (interError) throw interError
    interventions.value = interData || []

  } catch (err) {
    console.error("Erreur chargement dashboard :", err)
  } finally {
    loading.value = false
  }
}

const correspondAuxFiltres = (dateString) => {
  if (!dateString) return false
  const date = new Date(dateString)
  const yearMatch = date.getFullYear().toString() === selectedYear.value
  const monthMatch = selectedMonth.value === 'all' || (date.getMonth() + 1).toString().padStart(2, '0') === selectedMonth.value
  
  if (!yearMatch || !monthMatch) return false

  if (selectedWeek.value) {
    const d = new Date(date.getFullYear(), date.getMonth(), date.getDate())
    const debut = new Date(selectedWeek.value.debut.getFullYear(), selectedWeek.value.debut.getMonth(), selectedWeek.value.debut.getDate())
    const fin = new Date(selectedWeek.value.fin.getFullYear(), selectedWeek.value.fin.getMonth(), selectedWeek.value.fin.getDate())
    return d >= debut && d <= fin
  }

  return true
}

const filteredFactures = computed(() => factures.value.filter(f => correspondAuxFiltres(f.date_creation)))
const filteredInterventions = computed(() => interventions.value.filter(i => correspondAuxFiltres(i.date)))

// Indicateurs Financiers
const totalCa = computed(() => filteredFactures.value.reduce((acc, f) => acc + (f.total_ttc || 0), 0))
const totalEncaisse = computed(() => filteredFactures.value.filter(f => f.statut === 'Payée').reduce((acc, f) => acc + (f.total_ttc || 0), 0))
const totalEnAttente = computed(() => filteredFactures.value.filter(f => f.statut !== 'Payée').reduce((acc, f) => acc + (f.total_ttc || 0), 0))

const retardsList = computed(() => {
  const aujourdHui = new Date()
  return filteredFactures.value.filter(f => {
    if (f.statut === 'Payée' || !f.date_echeance) return false
    return new Date(f.date_echeance) < aujourdHui
  })
})
const totalRetardMontant = computed(() => retardsList.value.reduce((acc, f) => acc + (f.total_ttc || 0), 0))
const totalRetardCount = computed(() => retardsList.value.length)

const totalResteAFacturer = computed(() => {
  return filteredInterventions.value
    .filter(i => !i.facture_id)
    .reduce((acc, i) => acc + ((i.prix_final_ht || 0) * (i.quantite || 1)), 0)
})

const totalCaGlobal = computed(() => totalCa.value + totalResteAFacturer.value)

// 1. Détail des modes de règlement
const modesReglementStats = computed(() => {
  const stats = {}
  filteredFactures.value.forEach(f => {
    const mode = f.mode_reglement || 'Non spécifié'
    if (!stats[mode]) stats[mode] = { count: 0, montant: 0 }
    stats[mode].count += 1
    stats[mode].montant += (f.total_ttc || 0)
  })
  
  const totalCount = filteredFactures.value.length || 1
  return Object.keys(stats).map(mode => ({
    mode,
    count: stats[mode].count,
    montant: stats[mode].montant,
    pourcentage: Math.round((stats[mode].count / totalCount) * 100)
  })).sort((a, b) => b.montant - a.montant)
})

// 2. Graphique comparatif mensuel (Barres horizontales fines)
const comparatifAnnuels = computed(() => {
  const anneeCourante = parseInt(selectedYear.value)
  const anneePrecedente = anneeCourante - 1
  const moisNoms = ['Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin', 'Juil', 'Août', 'Sep', 'Oct', 'Nov', 'Déc']
  
  const dataMois = moisNoms.map((nom, index) => ({
    mois: nom,
    courantPaye: 0,
    courantAttente: 0,
    courantNonFacture: 0,
    precedentPaye: 0,
    precedentAttente: 0,
    precedentNonFacture: 0
  }))

  factures.value.forEach(f => {
    if (!f.date_creation) return
    const d = new Date(f.date_creation)
    const y = d.getFullYear()
    const m = d.getMonth()
    const montant = f.total_ttc || 0

    if (y === anneeCourante) {
      if (f.statut === 'Payée') dataMois[m].courantPaye += montant
      else dataMois[m].courantAttente += montant
    } else if (y === anneePrecedente) {
      if (f.statut === 'Payée') dataMois[m].precedentPaye += montant
      else dataMois[m].precedentAttente += montant
    }
  })

  interventions.value.forEach(i => {
    if (!i.date || i.facture_id) return
    const d = new Date(i.date)
    const y = d.getFullYear()
    const m = d.getMonth()
    const montant = (i.prix_final_ht || 0) * (i.quantite || 1)

    if (y === anneeCourante) {
      dataMois[m].courantNonFacture += montant
    } else if (y === anneePrecedente) {
      dataMois[m].precedentNonFacture += montant
    }
  })

  const maxTotal = Math.max(...dataMois.map(d => Math.max(
    d.courantPaye + d.courantAttente + d.courantNonFacture,
    d.precedentPaye + d.precedentAttente + d.precedentNonFacture
  )), 100)

  return dataMois.map(d => {
    const totalCourant = d.courantPaye + d.courantAttente + d.courantNonFacture
    const totalPrecedent = d.precedentPaye + d.precedentAttente + d.precedentNonFacture

    return {
      ...d,
      totalCourant,
      totalPrecedent,
      pctCourantPaye: maxTotal ? (d.courantPaye / maxTotal) * 100 : 0,
      pctCourantAttente: maxTotal ? (d.courantAttente / maxTotal) * 100 : 0,
      pctCourantNonFacture: maxTotal ? (d.courantNonFacture / maxTotal) * 100 : 0,
      pctPrecedentPaye: maxTotal ? (d.precedentPaye / maxTotal) * 100 : 0,
      pctPrecedentAttente: maxTotal ? (d.precedentAttente / maxTotal) * 100 : 0,
      pctPrecedentNonFacture: maxTotal ? (d.precedentNonFacture / maxTotal) * 100 : 0,
    }
  })
})

onMounted(() => {
  fetchDashboardData()
})
</script>

<template>
  <div class="space-y-4">
    <!-- En-tête de bienvenue -->
    <div class="bg-gradient-to-r from-blue-600 to-indigo-700 text-white p-4 rounded-2xl shadow-md">
      <h1 class="text-base font-bold">Bonjour {{ userName }} 👋</h1>
      <p class="text-[11px] text-blue-100 mt-0.5">Pilotage de votre activité sur le terrain.</p>
    </div>

    <!-- Filtres temporels -->
    <div class="bg-white p-3 rounded-xl border border-slate-200 shadow-sm space-y-2">
      <div class="flex gap-2">
        <select v-model="selectedYear" class="flex-1 bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg p-2 font-medium outline-none">
          <option value="2026">2026</option>
          <option value="2025">2025</option>
          <option value="2024">2024</option>
        </select>

        <select v-model="selectedMonth" class="flex-1 bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg p-2 font-medium outline-none">
          <option value="all">Tous les mois</option>
          <option value="01">Janvier</option>
          <option value="02">Février</option>
          <option value="03">Mars</option>
          <option value="04">Avril</option>
          <option value="05">Mai</option>
          <option value="06">Juin</option>
          <option value="07">Juillet</option>
          <option value="08">Août</option>
          <option value="09">Septembre</option>
          <option value="10">Octobre</option>
          <option value="11">Novembre</option>
          <option value="12">Décembre</option>
        </select>
      </div>

      <div>
        <select 
          v-model="selectedWeek" 
          :disabled="selectedMonth === 'all'" 
          class="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs rounded-lg p-2 font-medium outline-none disabled:bg-slate-100 disabled:text-slate-400">
          <option :value="null">Toutes les semaines du mois</option>
          <option v-for="(sem, index) in semainesDuMois" :key="index" :value="sem">
            {{ sem.label }}
          </option>
        </select>
      </div>
    </div>

    <!-- Grille des cartes de pilotage -->
    <div class="grid grid-cols-2 gap-3">
      <div class="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
        <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">CA Facturé</span>
        <div class="text-base font-extrabold text-slate-900 mt-2">{{ loading ? '...' : totalCa.toFixed(2) }} €</div>
      </div>
      <div class="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
        <span class="text-[10px] font-bold text-indigo-500 uppercase tracking-wider">CA Global (Estimé)</span>
        <div class="text-base font-extrabold text-indigo-600 mt-2">{{ loading ? '...' : totalCaGlobal.toFixed(2) }} €</div>
      </div>
      <div class="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
        <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Encaissé</span>
        <div class="text-base font-extrabold text-emerald-600 mt-2">{{ loading ? '...' : totalEncaisse.toFixed(2) }} €</div>
      </div>
      <div class="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
        <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">En attente Paiement</span>
        <div class="text-base font-extrabold text-amber-600 mt-2">{{ loading ? '...' : totalEnAttente.toFixed(2) }} €</div>
      </div>
      <div class="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
        <div class="flex justify-between items-center">
          <span class="text-[10px] font-bold text-red-500 uppercase tracking-wider">En retard</span>
          <span v-if="!loading && totalRetardCount > 0" class="text-[10px] bg-red-50 text-red-600 font-bold px-1.5 py-0.5 rounded-full border border-red-100">{{ totalRetardCount }}</span>
        </div>
        <div class="text-base font-extrabold text-red-600 mt-2">{{ loading ? '...' : totalRetardMontant.toFixed(2) }} €</div>
      </div>
      <div class="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
        <span class="text-[10px] font-bold text-indigo-500 uppercase tracking-wider">Reste à Facturer</span>
        <div class="text-base font-extrabold text-indigo-600 mt-2">{{ loading ? '...' : totalResteAFacturer.toFixed(2) }} € HT</div>
      </div>
    </div>

    <!-- ANALYTICS : Détail des modes de règlement -->
    <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm space-y-3">
      <h2 class="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
        <span class="material-icons text-blue-500 text-base">payments</span> Modes de Règlement
      </h2>
      <div v-if="loading" class="text-xs text-slate-400 text-center py-2">Chargement...</div>
      <div v-else-if="modesReglementStats.length === 0" class="text-xs text-slate-400 text-center py-2">Aucun règlement enregistré sur cette période.</div>
      <div v-else class="space-y-2">
        <div v-for="item in modesReglementStats" :key="item.mode" class="space-y-1">
          <div class="flex justify-between text-xs">
            <span class="font-medium text-slate-700">{{ item.mode }} <span class="text-slate-400 text-[10px]">({{ item.count }} factures)</span></span>
            <span class="font-bold text-slate-900">{{ item.montant.toFixed(2) }} €</span>
          </div>
          <div class="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden">
            <div class="bg-blue-600 h-full rounded-full" :style="{ width: item.pourcentage + '%' }"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- ANALYTICS : Graphique comparatif mensuel (Lignes fines horizontales empilées) -->
    <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm space-y-3">
      <div class="flex justify-between items-center">
        <h2 class="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
          <span class="material-icons text-indigo-500 text-base">bar_chart</span> Comparatif CA Mensuel ({{ selectedYear }} vs {{ parseInt(selectedYear) - 1 }})
        </h2>
      </div>

      <!-- Légende détaillée -->
      <div class="grid grid-cols-2 gap-2 text-[10px] text-slate-600 bg-slate-50 p-2.5 rounded-lg border border-slate-100">
        <div class="space-y-1">
          <div class="font-bold text-slate-700 mb-1">Année {{ selectedYear }} (Vif)</div>
          <div class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 bg-emerald-500 rounded-sm"></span> Facturé et Payé</div>
          <div class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 bg-blue-500 rounded-sm"></span> Facturé en Attente</div>
          <div class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 bg-orange-500 rounded-sm"></span> Non facturé</div>
        </div>
        <div class="space-y-1 border-l pl-2 border-slate-200">
          <div class="font-bold text-slate-500 mb-1">Année {{ parseInt(selectedYear) - 1 }} (Grisé)</div>
          <div class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 bg-emerald-300 rounded-sm"></span> Facturé et Payé N-1</div>
          <div class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 bg-blue-300 rounded-sm"></span> Facturé en Attente N-1</div>
          <div class="flex items-center gap-1.5"><span class="w-2.5 h-2.5 bg-orange-300 rounded-sm"></span> Non facturé N-1</div>
        </div>
      </div>

      <!-- Barres horizontales fines par mois -->
      <div class="space-y-2 pt-1">
        <div v-for="m in comparatifAnnuels" :key="m.mois" class="space-y-1">
          <!-- Nom du mois et totaux discrets -->
          <div class="flex justify-between text-[11px] font-medium text-slate-600">
            <span>{{ m.mois }}</span>
            <div class="space-x-2">
              <span class="text-blue-600 font-bold">{{ m.totalCourant.toFixed(0) }} €</span>
              <span class="text-slate-400">{{ m.totalPrecedent.toFixed(0) }} €</span>
            </div>
          </div>
          
          <div class="flex flex-col gap-1">
            <!-- Barre Année en cours (Vif) -->
            <div class="w-full bg-slate-100 h-2 rounded-full overflow-hidden flex" :title="selectedYear + ' - Total: ' + m.totalCourant.toFixed(0) + '€'">
              <div class="bg-emerald-500 transition-all duration-500" :style="{ width: m.pctCourantPaye + '%' }" title="Facturé et Payé"></div>
              <div class="bg-blue-500 transition-all duration-500" :style="{ width: m.pctCourantAttente + '%' }" title="Facturé en Attente"></div>
              <div class="bg-orange-500 transition-all duration-500" :style="{ width: m.pctCourantNonFacture + '%' }" title="Non facturé"></div>
            </div>

            <!-- Barre Année N-1 (Grisé / Pastel) -->
            <div class="w-full bg-slate-100 h-1.5 rounded-full overflow-hidden flex" :title="(parseInt(selectedYear)-1) + ' - Total: ' + m.totalPrecedent.toFixed(0) + '€'">
              <div class="bg-emerald-300 transition-all duration-500" :style="{ width: m.pctPrecedentPaye + '%' }" title="Facturé et Payé N-1"></div>
              <div class="bg-blue-300 transition-all duration-500" :style="{ width: m.pctPrecedentAttente + '%' }" title="Facturé en Attente N-1"></div>
              <div class="bg-orange-300 transition-all duration-500" :style="{ width: m.pctPrecedentNonFacture + '%' }" title="Non facturé N-1"></div>
            </div>
          </div>
        </div>
      </div>

    </div>
  </div>
</template>