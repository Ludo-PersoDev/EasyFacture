<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { supabase } from '../../supabase'

const factures = ref([])
const interventions = ref([])
const loading = ref(true)

// Filtres temporels (Année en cours par défaut, mois par défaut "all")
const currentYear = new Date().getFullYear().toString()
const selectedYear = ref(currentYear)
const selectedMonth = ref('all') // 'all' ou '01', '02', etc.
const selectedWeek = ref(null) // null ou { debut: Date, fin: Date }

// Génération dynamique des semaines en fonction du mois et de l'année choisis
const semainesDuMois = computed(() => {
  if (selectedMonth.value === 'all' || !selectedMonth.value) return []

  const annee = parseInt(selectedYear.value)
  const mois = parseInt(selectedMonth.value)
  
  const premierJour = new Date(annee, mois - 1, 1)
  const dernierJour = new Date(annee, mois, 0) // Dernier jour du mois

  let semaines = []
  let debutCourant = new Date(premierJour)

  while (debutCourant <= dernierJour) {
    let finSemaine = new Date(debutCourant)
    
    // Calcul pour aller jusqu'au dimanche (jour 0 ou 7)
    let jourSemaine = finSemaine.getDay() === 0 ? 7 : finSemaine.getDay()
    let joursRestantsAvantDimanche = 7 - jourSemaine
    
    finSemaine.setDate(finSemaine.getDate() + joursRestantsAvantDimanche)

    // Si la fin dépasse le mois, on bloque STRICTEMENT au dernier jour du mois
    if (finSemaine > dernierJour) {
      finSemaine = new Date(dernierJour)
    }

    semaines.push({
      debut: new Date(debutCourant),
      fin: new Date(finSemaine),
      label: `Du ${debutCourant.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' })} au ${finSemaine.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' })}`
    })

    // Passer au lundi suivant
    debutCourant = new Date(finSemaine)
    debutCourant.setDate(debutCourant.getDate() + 1)
  }

  return semaines
})

// Réinitialiser la semaine si on change de mois ou d'année
watch([selectedMonth, selectedYear], () => {
  selectedWeek.value = null
})

const fetchDashboardData = async () => {
  try {
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) return

    // 1. Récupération des factures
    const { data: factData, error: factError } = await supabase
      .from('factures')
      .select('total_ttc, statut, date_creation, date_echeance, Envoi_facturx')
      .eq('user_id', user.id)

    if (factError) throw factError
    factures.value = factData || []

    // 2. Récupération des interventions pour le "Reste à facturer"
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

// Fonction utilitaire pour vérifier si une date correspond aux filtres mois/semaine
const correspondAuxFiltres = (dateString) => {
  if (!dateString) return false
  const date = new Date(dateString)
  const yearMatch = date.getFullYear().toString() === selectedYear.value
  const monthMatch = selectedMonth.value === 'all' || (date.getMonth() + 1).toString().padStart(2, '0') === selectedMonth.value
  
  if (!yearMatch || !monthMatch) return false

  // Si une semaine spécifique est sélectionnée
  if (selectedWeek.value) {
    // Normalisation des heures pour comparer proprement les dates (ignorer l'heure)
    const d = new Date(date.getFullYear(), date.getMonth(), date.getDate())
    const debut = new Date(selectedWeek.value.debut.getFullYear(), selectedWeek.value.debut.getMonth(), selectedWeek.value.debut.getDate())
    const fin = new Date(selectedWeek.value.fin.getFullYear(), selectedWeek.value.fin.getMonth(), selectedWeek.value.fin.getDate())
    
    return d >= debut && d <= fin
  }

  return true
}

// Filtrage des factures selon l'année, le mois et la semaine sélectionnés
const filteredFactures = computed(() => {
  return factures.value.filter(f => correspondAuxFiltres(f.date_creation))
})

// Filtrage des interventions selon l'année, le mois et la semaine sélectionnés
const filteredInterventions = computed(() => {
  return interventions.value.filter(i => correspondAuxFiltres(i.date))
})

// Calculs dynamiques basés sur les filtres
const totalCa = computed(() => filteredFactures.value.reduce((acc, f) => acc + (f.total_ttc || 0), 0))

const totalEncaisse = computed(() => {
  return filteredFactures.value
    .filter(f => f.statut === 'Payée')
    .reduce((acc, f) => acc + (f.total_ttc || 0), 0)
})

const totalEnAttente = computed(() => {
  return filteredFactures.value
    .filter(f => f.statut !== 'Payée')
    .reduce((acc, f) => acc + (f.total_ttc || 0), 0)
})

const retardsList = computed(() => {
  const aujourdHui = new Date()
  return filteredFactures.value.filter(f => {
    if (f.statut === 'Payée' || !f.date_echeance) return false
    return new Date(f.date_echeance) < aujourdHui
  })
})

const totalRetardMontant = computed(() => retardsList.value.reduce((acc, f) => acc + (f.total_ttc || 0), 0))
const totalRetardCount = computed(() => retardsList.value.length)

// Calcul du reste à facturer (interventions sans facture_id rattaché)
const totalResteAFacturer = computed(() => {
  return filteredInterventions.value
    .filter(i => !i.facture_id)
    .reduce((acc, i) => acc + ((i.prix_final_ht || 0) * (i.quantite || 1)), 0)
})

onMounted(() => {
  fetchDashboardData()
})
</script>

<template>
  <div class="space-y-4">
    <!-- En-tête de bienvenue -->
    <div class="bg-gradient-to-r from-blue-600 to-indigo-700 text-white p-4 rounded-2xl shadow-md">
      <h1 class="text-base font-bold">Bonjour Ludovic 👋</h1>
      <p class="text-[11px] text-blue-100 mt-0.5">Pilotage de votre activité sur le terrain.</p>
    </div>

    <!-- Filtres temporels (Année, Mois & Semaine) -->
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

      <!-- Filtre de semaine (dépendant du mois) -->
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
      <!-- 1. CA Total Facturé -->
      <div class="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
        <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">CA Total Facturé</span>
        <div class="text-base font-extrabold text-slate-900 mt-2">
          {{ loading ? '...' : totalCa.toFixed(2) }} €
        </div>
      </div>

      <!-- 2. Encaissé -->
      <div class="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
        <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">Encaissé</span>
        <div class="text-base font-extrabold text-emerald-600 mt-2">
          {{ loading ? '...' : totalEncaisse.toFixed(2) }} €
        </div>
      </div>

      <!-- 3. En attente -->
      <div class="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
        <span class="text-[10px] font-bold text-slate-400 uppercase tracking-wider">En attente Paiement</span>
        <div class="text-base font-extrabold text-amber-600 mt-2">
          {{ loading ? '...' : totalEnAttente.toFixed(2) }} €
        </div>
      </div>

      <!-- 4. Paiements en retard -->
      <div class="bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
        <div class="flex justify-between items-center">
          <span class="text-[10px] font-bold text-red-500 uppercase tracking-wider">En retard Paiement</span>
          <span v-if="!loading && totalRetardCount > 0" class="text-[10px] bg-red-50 text-red-600 font-bold px-1.5 py-0.5 rounded-full border border-red-100">
            {{ totalRetardCount }}
          </span>
        </div>
        <div class="text-base font-extrabold text-red-600 mt-2">
          {{ loading ? '...' : totalRetardMontant.toFixed(2) }} €
        </div>
      </div>

      <!-- 5. Reste à Facturer (Pleine largeur) -->
      <div class="col-span-2 bg-white p-3.5 rounded-xl border border-slate-200 shadow-sm flex flex-col justify-between">
        <span class="text-[10px] font-bold text-indigo-500 uppercase tracking-wider">Reste à Facturer (Prestations non liées)</span>
        <div class="text-base font-extrabold text-indigo-600 mt-2">
          {{ loading ? '...' : totalResteAFacturer.toFixed(2) }} € HT
        </div>
      </div>
    </div>

    <!-- Widget Statut Factur-X (Lecture seule terrain) -->
    <div class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
      <div class="flex items-center justify-between mb-3">
        <h2 class="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
          <span class="material-icons text-sky-500 text-base">cloud_done</span> Passerelle Factur-X
        </h2>
        <span class="text-[10px] font-medium px-2 py-0.5 bg-sky-50 text-sky-700 rounded-full border border-sky-100">Lecture seule</span>
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