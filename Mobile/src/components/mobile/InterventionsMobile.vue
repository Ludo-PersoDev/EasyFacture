<script setup>
import { ref, computed, onMounted } from 'vue'
import { supabase } from '../../supabase'

const interventions = ref([])
const clients = ref([])
const cataloguePrestations = ref([])
const sitesSecondaires = ref([])
const loading = ref(true)
const showModal = ref(false)

// Champs du formulaire modale
const selectedClientId = ref('')
const siteId = ref('')
const selectedCatalogueId = ref('')
const dateIntervention = ref(new Date().toISOString().split('T')[0])
const heureDebut = ref('14:00')
const heureFin = ref('16:00')
const tarif = ref('')
const description = ref('')

// Calcul dynamique de la durée (ex: "2.0 h")
const dureeCalculee = computed(() => {
  if (!heureDebut.value || !heureFin.value) return '0 h'
  const [hDebut, mDebut] = heureDebut.value.split(':').map(Number)
  const [hFin, mFin] = heureFin.value.split(':').map(Number)
  
  const totalMinutesDebut = hDebut * 60 + mDebut
  const totalMinutesFin = hFin * 60 + mFin
  
  let diffMinutes = totalMinutesFin - totalMinutesDebut
  if (diffMinutes < 0) diffMinutes += 24 * 60
  
  const heures = (diffMinutes / 60).toFixed(1)
  return `${heures} h`
})

const fetchData = async () => {
  loading.value = true
  try {
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) return

    // 1. Récupération des interventions avec jointures
    const { data: interData, error: interError } = await supabase
      .from('interventions')
      .select('*, clients(nom_societe), prestations(designation), etablissements(nom_site)')
      .order('date', { ascending: false })

    if (interError) throw interError

    // 2. Récupération des clients
    const { data: clientsData } = await supabase.from('clients').select('*')
    clients.value = clientsData || []

    const clientsMap = {}
    ;(clientsData || []).forEach(c => {
      clientsMap[c.id] = c.nom_societe || `${c.prenom || ''} ${c.nom || ''}`.trim()
    })

    interventions.value = (interData || []).map(item => {
      const clientRel = item.clients
      const clientNom = clientRel ? (clientRel.nom_societe || clientRel[0]?.nom_societe) : null

      const prestRel = item.prestations
      const prestNom = prestRel ? (prestRel.designation || prestRel[0]?.designation) : null

      const etabRel = item.etablissements
      const etabNom = etabRel ? (etabRel.nom_site || etabRel[0]?.nom_site) : null

      return {
        ...item,
        client_nom: clientNom || clientsMap[item.client_id] || 'Client non spécifié',
        titre: prestNom || item.titre || 'Prestation',
        site_txt: etabNom || '-'
      }
    })

  } catch (err) {
    console.error('Erreur chargement global:', err)
  } finally {
    loading.value = false
  }
}

// Chargement des établissements et des prestations (avec tarifs spécifiques) du client
const handleClientChange = async () => {
  sitesSecondaires.value = []
  siteId.value = ''
  cataloguePrestations.value = []
  selectedCatalogueId.value = ''
  tarif.value = ''

  if (!selectedClientId.value) return

  try {
    // 1. Récupération des établissements (etablissements)
    const { data: etabs } = await supabase
      .from('etablissements')
      .select('*')
      .eq('client_id', selectedClientId.value)
    
    if (etabs) sitesSecondaires.value = etabs

    // 2. Récupération des tarifs spécifiques ou du catalogue général (prestations)
    const { data: tarifsSpec } = await supabase
      .from('client_tarifs')
      .select('prestation_id, prix_specifique_ht, prestations(id, designation, prix_ht)')
      .eq('client_id', selectedClientId.value)
      .eq('est_actif', true)

    let options = []
    if (tarifsSpec && tarifsSpec.length > 0) {
      options = tarifsSpec.map(t => {
        const pInfo = t.prestations || {}
        const px = t.prix_specifique_ht !== null ? t.prix_specifique_ht : (pInfo.prix_ht || 0.0)
        return {
          id: t.prestation_id,
          designation: `${pInfo.designation || 'Prestation'} (${px.toFixed(2)} €/h - Tarif spécifique)`,
          prix: px
        }
      })
    } else {
      const { data: cat } = await supabase.from('prestations').select('*').order('designation')
      if (cat) {
        options = cat.map(p => ({
          id: p.id,
          designation: `${p.designation} (${(p.prix_ht || 0).toFixed(2)} €/h)`,
          prix: p.prix_ht || 0
        }))
      }
    }

    cataloguePrestations.value = options
    if (options.length > 0) {
      selectedCatalogueId.value = options[0].id
      tarif.value = options[0].prix
    }
  } catch (e) {
    console.warn("Erreur lors du chargement des données dépendantes du client", e)
  }
}

// Mise à jour du tarif lors du changement de prestation
const handleCatalogueChange = () => {
  const selected = cataloguePrestations.value.find(p => p.id == selectedCatalogueId.value)
  if (selected) {
    tarif.value = selected.prix
  }
}

const handleAddPrestation = async () => {
  try {
    const { data: { user } } = await supabase.auth.getUser()
    if (!user) return

    if (!selectedCatalogueId.value) {
      alert('Veuillez sélectionner une prestation.')
      return
    }

    const qteCalc = parseFloat(dureeCalculee.value) || 1.0
    const numeroInterv = 'PREST-' + Math.floor(1000 + Math.random() * 9000)

    const payload = {
      client_id: parseInt(selectedClientId.value),
      etablissement_id: siteId.value ? parseInt(siteId.value) : null,
      prestation_id: parseInt(selectedCatalogueId.value),
      date: dateIntervention.value,
      heure_debut: heureDebut.value,
      heure_fin: heureFin.value,
      quantite: qteCalc,
      prix_final_ht: tarif.value ? parseFloat(tarif.value) : 0,
      commentaire: description.value,
      numero_intervention: numeroInterv,
      statut: 'En attente'
    }

    const { error } = await supabase.from('interventions').insert([payload])
    if (error) throw error

    // Reset et fermeture
    selectedClientId.value = ''
    siteId.value = ''
    selectedCatalogueId.value = ''
    tarif.value = ''
    description.value = ''
    sitesSecondaires.value = []
    cataloguePrestations.value = []
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

    <!-- LISTE CONCISE -->
    <div v-if="loading" class="text-center py-8 text-xs text-slate-400">Chargement...</div>
    <div v-else-if="interventions.length === 0" class="bg-white p-6 rounded-xl border border-slate-200 text-center text-xs text-slate-500">
      Aucune prestation enregistrée.
    </div>
    <div v-else class="space-y-3">
      <div v-for="item in interventions" :key="item.id" class="bg-white p-4 rounded-xl border border-slate-200 shadow-sm flex flex-col gap-1.5">
        <div class="flex justify-between items-start">
          <div>
            <h3 class="text-xs font-bold text-slate-900">{{ item.titre }}</h3>
            <p class="text-xs font-medium text-slate-600 mt-0.5">{{ item.client_nom }} <span v-if="item.site_txt !== '-'" class="text-slate-400">({{ item.site_txt }})</span></p>
          </div>
          <div class="text-right">
            <span class="text-[10px] text-slate-400 font-medium block">{{ item.date }}</span>
            <span class="text-[10px] text-blue-600 font-semibold" v-if="item.heure_debut">{{ item.heure_debut }} - {{ item.heure_fin }}</span>
          </div>
        </div>
        
        <!-- Ligne inférieure : Montant à gauche, Statut à droite -->
        <div class="flex justify-between items-center pt-2 border-t border-slate-100 mt-1">
          <span class="text-xs font-extrabold text-slate-900" v-if="item.prix_final_ht">
            {{ (item.prix_final_ht * (item.quantite || 1)).toFixed(2) }} € HT
          </span>
          <span v-else class="text-xs text-slate-400">0.00 € HT</span>

          <!-- Badge de statut dynamique -->
          <span class="text-[10px] font-bold px-2 py-0.5 rounded-full" :class="{
            'bg-amber-50 text-amber-700 border border-amber-100': item.statut === 'En attente',
            'bg-emerald-50 text-emerald-700 border border-emerald-100': item.statut === 'Facturée' || item.statut === 'Terminée',
            'bg-slate-100 text-slate-600 border border-slate-200': !item.statut
          }">
            {{ item.statut || 'En attente' }}
          </span>
        </div>
      </div>
    </div>

    <!-- MODALE -->
    <div v-if="showModal" class="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-50 flex items-center justify-center p-4 overflow-y-auto">
      <div class="bg-white w-full max-w-md rounded-2xl p-5 space-y-4 shadow-xl my-auto">
        <div class="flex justify-between items-center border-b border-slate-100 pb-3">
          <h3 class="text-sm font-bold text-slate-900">Nouvelle Prestation Directe</h3>
          <button @click="showModal = false" class="text-slate-400 hover:text-slate-600 text-sm font-bold">✕</button>
        </div>

        <form @submit.prevent="handleAddPrestation" class="space-y-3">
          <!-- 1. Client -->
          <div>
            <label class="block text-[11px] font-medium text-slate-500 mb-1">Client</label>
            <select v-model="selectedClientId" @change="handleClientChange" required class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500 bg-white">
              <option value="" disabled>Sélectionner un client</option>
              <option v-for="c in clients" :key="c.id" :value="c.id">
                {{ c.nom_societe || `${c.prenom || ''} ${c.nom || ''}`.trim() }}
              </option>
            </select>
          </div>

          <!-- 2. Site / Établissement (Masqué s'il n'y a pas d'établissements pour ce client) -->
          <div v-if="sitesSecondaires.length > 0">
            <label class="block text-[11px] font-medium text-slate-500 mb-1">Site / Établissement</label>
            <select v-model="siteId" class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500 bg-white">
              <option value="">Adresse principale du client</option>
              <option v-for="s in sitesSecondaires" :key="s.id" :value="s.id">
                {{ s.nom_site }}
              </option>
            </select>
          </div>

          <!-- 3. Cours / Prestation -->
          <div>
            <label class="block text-[11px] font-medium text-slate-500 mb-1">Cours / Prestation</label>
            <select v-model="selectedCatalogueId" @change="handleCatalogueChange" required class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500 bg-white">
              <option value="" disabled>Sélectionner une prestation</option>
              <option v-for="p in cataloguePrestations" :key="p.id" :value="p.id">
                {{ p.designation }}
              </option>
            </select>
          </div>

          <!-- 4. Date d'exécution -->
          <div>
            <label class="block text-[11px] font-medium text-slate-500 mb-1">Date d'exécution</label>
            <input v-model="dateIntervention" type="date" required class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500" />
          </div>

          <!-- 5. Début / Fin / Durée -->
          <div class="grid grid-cols-3 gap-2 items-center">
            <div>
              <label class="block text-[11px] font-medium text-slate-500 mb-1">Début</label>
              <input v-model="heureDebut" type="time" required class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div>
              <label class="block text-[11px] font-medium text-slate-500 mb-1">Fin</label>
              <input v-model="heureFin" type="time" required class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500" />
            </div>
            <div class="bg-blue-50 border border-blue-100 rounded-lg p-2 text-center mt-4">
              <span class="text-[10px] text-blue-600 font-bold block">Durée</span>
              <span class="text-xs text-slate-800 font-extrabold">{{ dureeCalculee }}</span>
            </div>
          </div>

          <!-- 6. Remarques / Commentaire -->
          <div>
            <label class="block text-[11px] font-medium text-slate-500 mb-1">Remarques / Commentaire</label>
            <input v-model="description" type="text" placeholder="Commentaire optionnel..." class="w-full border border-slate-300 p-2.5 rounded-lg text-xs outline-none focus:ring-2 focus:ring-blue-500" />
          </div>

          <!-- Boutons d'action -->
          <div class="flex gap-2 pt-3 border-t border-slate-100 mt-2">
            <button type="button" @click="showModal = false" class="flex-1 py-2.5 bg-slate-100 text-slate-700 font-bold text-xs rounded-xl hover:bg-slate-200 transition uppercase tracking-wider">
              Annuler
            </button>
            <button type="submit" class="flex-1 py-2.5 bg-emerald-600 text-white font-bold text-xs rounded-xl shadow-sm hover:bg-emerald-700 transition uppercase tracking-wider flex items-center justify-center gap-1.5">
              <span>✓</span> Enregistrer
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>