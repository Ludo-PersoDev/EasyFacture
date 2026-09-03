<script setup>
import { ref, computed, onMounted } from 'vue'
import { supabase } from '../../supabase'

const loading = ref(true)
const prestations = ref([])
const searchFilter = ref('')

const isTvaExoneree = ref(false)

const isDialogOpen = ref(false)
const isEditMode = ref(false)
const currentId = ref(null)

const form = ref({
  designation: '',
  unite: 'Heure',
  prix_ht: 0,
  taux_tva: 20.0
})

const uniteOptions = ['Heure', 'Jour', 'Forfait', 'Km', 'Unité']
const tvaOptions = [
  { label: '0 % (Exonéré / Franchise en base)', value: 0.0 },
  { label: '5.5 %', value: 5.5 },
  { label: '10 % (Déplacements / Spectacles)', value: 10.0 },
  { label: '20 % (Standard)', value: 20.0 }
]

const fetchData = async () => {
  loading.value = true
  const { data: { user } } = await supabase.auth.getUser()
  if (user) {
    const { data: paramData } = await supabase
      .from('parametres')
      .select('tva_exoneree')
      .eq('user_id', user.id)
      .maybeSingle()

    if (paramData && paramData.tva_exoneree === true) {
      isTvaExoneree.value = true
    }

    const { data, error } = await supabase
      .from('prestations')
      .select('*')
      .eq('user_id', user.id)
      .order('designation', { ascending: true })

    if (error) {
      console.error(error)
      alert("Erreur lors du chargement du catalogue.")
    } else {
      prestations.value = data || []
    }
  }
  loading.value = false
}

onMounted(() => {
  fetchData()
})

const filteredPrestations = computed(() => {
  if (!searchFilter.value) return prestations.value
  const query = searchFilter.value.toLowerCase()
  return prestations.value.filter(p => p.designation.toLowerCase().includes(query))
})

const openDialog = (item = null, event = null) => {
  if (event) event.stopPropagation()
  if (item) {
    isEditMode.value = true
    currentId.value = item.id
    form.value = { 
      designation: item.designation,
      unite: item.unite,
      prix_ht: item.prix_ht,
      taux_tva: isTvaExoneree.value ? 0 : item.taux_tva
    }
  } else {
    isEditMode.value = false
    currentId.value = null
    form.value = {
      designation: '',
      unite: 'Heure',
      prix_ht: 0,
      taux_tva: isTvaExoneree.value ? 0 : 20.0
    }
  }
  isDialogOpen.value = true
}

const savePrestation = async () => {
  if (!form.value.designation.trim()) {
    alert("Veuillez saisir une désignation.")
    return
  }

  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return

  const tauxTvaFinal = isTvaExoneree.value ? 0 : form.value.taux_tva

  if (isEditMode.value) {
    const { error } = await supabase
      .from('prestations')
      .update({
        designation: form.value.designation.trim(),
        unite: form.value.unite,
        prix_ht: form.value.prix_ht,
        taux_tva: tauxTvaFinal
      })
      .eq('id', currentId.value)

    if (error) {
      alert("Erreur lors de la modification.")
      console.error(error)
    } else {
      isDialogOpen.value = false
      fetchData()
    }
  } else {
    const { error } = await supabase
      .from('prestations')
      .insert({
        user_id: user.id,
        designation: form.value.designation.trim(),
        unite: form.value.unite,
        prix_ht: form.value.prix_ht,
        taux_tva: tauxTvaFinal
      })

    if (error) {
      alert("Erreur lors de l'ajout.")
      console.error(error)
    } else {
      isDialogOpen.value = false
      fetchData()
    }
  }
}

const deletePrestation = async (id, event) => {
  if (event) event.stopPropagation()
  if (!confirm("Voulez-vous vraiment supprimer cette prestation ?")) return

  const { error } = await supabase
    .from('prestations')
    .delete()
    .eq('id', id)

  if (error) {
    alert("Erreur lors de la suppression.")
    console.error(error)
  } else {
    fetchData()
  }
}
</script>

<template>
  <div class="page-container">
    
    <!-- En-tête -->
    <div class="header-card">
      <div>
        <h1 class="page-title">Catalogue des Prestations</h1>
        <p class="page-subtitle">Gérez vos prestations et formations récurrentes.</p>
      </div>
      
      <button @click="openDialog()" class="btn-primary-clean">
        <span class="material-icons text-sm">add</span> Nouvelle Prestation
      </button>
    </div>

    <!-- Barre de recherche & Contenu -->
    <div class="content-card">
      <div class="search-bar">
        <span class="material-icons text-slate-400">search</span>
        <input 
          v-model="searchFilter" 
          type="text" 
          placeholder="Rechercher une prestation..." 
          class="search-input"
        />
      </div>

      <div v-if="loading" class="loading-state">
        Chargement du catalogue...
      </div>

      <div v-else-if="filteredPrestations.length === 0" class="empty-state">
        Aucune prestation trouvée.
      </div>

      <!-- VUE DESKTOP : Tableau classique -->
      <div v-else class="desktop-table-view">
        <table class="data-table">
          <thead>
            <tr>
              <th>Désignation</th>
              <th class="text-center">Unité</th>
              <th class="text-right">Prix HT</th>
              <th class="text-right">TVA</th>
              <th class="text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in filteredPrestations" :key="item.id" @click="openDialog(item)" class="clickable-row">
              <td class="font-medium text-slate-900">{{ item.designation }}</td>
              <td class="text-center">
                <span class="badge-unite">{{ item.unite }}</span>
              </td>
              <td class="text-right font-mono">{{ Number(item.prix_ht).toFixed(2) }} €</td>
              <td class="text-right font-mono">{{ Number(item.taux_tva).toFixed(1) }} %</td>
              <td class="text-right">
                <div class="action-buttons" @click.stop>
                  <button @click="openDialog(item)" class="icon-action-btn text-blue-600 hover:bg-blue-50" title="Modifier">
                    <span class="material-icons text-sm">edit</span>
                  </button>
                  <button @click="deletePrestation(item.id, $event)" class="icon-action-btn text-red-600 hover:bg-red-50" title="Supprimer">
                    <span class="material-icons text-sm">delete</span>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- VUE MOBILE : Cartes empilées -->
      <div v-if="!loading && filteredPrestations.length > 0" class="mobile-cards-view">
        <div 
          v-for="item in filteredPrestations" 
          :key="item.id" 
          @click="openDialog(item)"
          class="mobile-card-item"
        >
          <div class="mobile-card-header">
            <span class="mobile-designation">{{ item.designation }}</span>
            <span class="badge-unite">{{ item.unite }}</span>
          </div>
          
          <div class="mobile-card-footer">
            <div class="mobile-prices">
              <span class="font-mono font-bold text-slate-900">{{ Number(item.prix_ht).toFixed(2) }} € HT</span>
              <span class="text-xs text-slate-500 font-mono">TVA : {{ Number(item.taux_tva).toFixed(1) }}%</span>
            </div>
            <div class="mobile-actions" @click.stop>
              <button @click="deletePrestation(item.id, $event)" class="icon-action-btn text-red-600 bg-red-50" title="Supprimer">
                <span class="material-icons text-sm">delete</span>
              </button>
            </div>
          </div>
        </div>
      </div>

    </div>

    <!-- MODALE CRÉATION / ÉDITION -->
    <div v-if="isDialogOpen" class="modal-overlay">
      <div class="modal-card">
        <div class="modal-header">
          <h2>{{ isEditMode ? 'Modifier la prestation' : 'Créer une prestation' }}</h2>
          <button @click="isDialogOpen = false" class="close-btn">&times;</button>
        </div>

        <div class="modal-body">
          <div v-if="isTvaExoneree" class="alert-info-tva">
            <span class="material-icons text-amber-600 text-sm">info</span>
            <span>Entreprise en franchise de TVA (art. 293 B du CGI). Taux bloqué à 0 %.</span>
          </div>

          <div class="input-group">
            <label>Désignation *</label>
            <input v-model="form.designation" type="text" class="input-field" placeholder="Ex: Intervention technique" required />
          </div>

          <!-- Ligne Unité & Prix HT corrigée pour mobile -->
          <div class="row-flex">
            <div class="input-group col-unite">
              <label>Unité</label>
              <select v-model="form.unite" class="input-field">
                <option v-for="u in uniteOptions" :key="u" :value="u">{{ u }}</option>
              </select>
            </div>
            <div class="input-group col-prix">
              <label>Prix HT (€) *</label>
              <input v-model.number="form.prix_ht" type="number" step="0.01" class="input-field font-mono" />
            </div>
          </div>

          <div class="input-group">
            <label>Taux de TVA</label>
            <select v-model.number="form.taux_tva" class="input-field" :disabled="isTvaExoneree">
              <option v-for="tva in tvaOptions" :key="tva.value" :value="tva.value">{{ tva.label }}</option>
            </select>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="isDialogOpen = false" class="btn-secondary">Annuler</button>
          <button @click="savePrestation" class="btn-primary">Enregistrer</button>
        </div>
      </div>
    </div>

  </div>
</template>

<style scoped>
.page-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 16px;
  font-family: system-ui, -apple-system, sans-serif;
  color: #1e293b;
}

.header-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  border: 1px solid #e2e8f0;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 16px;
}

.page-title {
  font-size: 22px;
  font-weight: bold;
  margin: 0;
  color: #0f172a;
}

.page-subtitle {
  font-size: 13px;
  color: #64748b;
  margin: 4px 0 0 0;
}

.btn-primary-clean {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: #2563eb;
  color: white;
  border: none;
  padding: 10px 16px;
  border-radius: 8px;
  font-weight: 500;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-primary-clean:hover {
  background: #1d4ed8;
}

.content-card {
  background: white;
  padding: 16px;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  border: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.search-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #f8fafc;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  padding: 8px 12px;
  max-width: 100%;
}

.search-input {
  border: none;
  background: transparent;
  outline: none;
  font-size: 14px;
  width: 100%;
  color: #1e293b;
}

.desktop-table-view {
  display: block;
}

.mobile-cards-view {
  display: none;
}

@media (max-width: 768px) {
  .desktop-table-view {
    display: none;
  }
  .mobile-cards-view {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: 14px;
}

.data-table th {
  background: #f8fafc;
  padding: 12px 16px;
  font-weight: 600;
  color: #475569;
  border-bottom: 1px solid #e2e8f0;
  text-transform: uppercase;
  font-size: 11px;
}

.data-table td {
  padding: 14px 16px;
  border-bottom: 1px solid #f1f5f9;
}

.clickable-row {
  cursor: pointer;
  transition: background 0.15s;
}

.clickable-row:hover td {
  background: #f8fafc;
}

.mobile-card-item {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.02);
  cursor: pointer;
}

.mobile-card-item:active {
  background: #f8fafc;
}

.mobile-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
}

.mobile-designation {
  font-weight: 600;
  font-size: 15px;
  color: #0f172a;
}

.mobile-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-top: 1px solid #f1f5f9;
  padding-top: 8px;
}

.mobile-prices {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.badge-unite {
  background: #f1f5f9;
  color: #334155;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 500;
  border: 1px solid #e2e8f0;
  white-space: nowrap;
}

.action-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 4px;
}

.icon-action-btn {
  background: none;
  border: none;
  padding: 6px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading-state, .empty-state {
  text-align: center;
  padding: 30px;
  color: #64748b;
  font-style: italic;
  font-size: 14px;
}

/* Modale optimisée mobile */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 12px;
  box-sizing: border-box;
}

.modal-card {
  background: white;
  width: 100%;
  max-width: 480px;
  border-radius: 14px;
  box-shadow: 0 20px 25px -5px rgba(0,0,0,0.15);
  border: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  max-height: 90vh;
}

.modal-header {
  padding: 16px 20px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid #e2e8f0;
}

.modal-header h2 {
  font-size: 17px;
  font-weight: bold;
  margin: 0;
  color: #0f172a;
}

.close-btn {
  background: none;
  border: none;
  font-size: 24px;
  color: #64748b;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.modal-body {
  padding: 16px 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.alert-info-tva {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  background: #fffbeb;
  border: 1px solid #fde68a;
  color: #b45309;
  padding: 10px 12px;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.4;
}

.modal-footer {
  padding: 14px 20px;
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.input-group label {
  font-size: 11px;
  font-weight: 600;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.input-field {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 14px;
  color: #1e293b;
  background: #f8fafc;
  outline: none;
  box-sizing: border-box;
}

.input-field:focus {
  background: white;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.input-field:disabled {
  background: #f1f5f9;
  color: #94a3b8;
  cursor: not-allowed;
}

.row-flex {
  display: flex;
  gap: 12px;
}

.col-unite {
  flex: 0.4;
}

.col-prix {
  flex: 0.6;
}

.btn-primary {
  background: #2563eb;
  color: white;
  border: none;
  padding: 10px 18px;
  border-radius: 8px;
  font-weight: 500;
  font-size: 14px;
  cursor: pointer;
}

.btn-primary:hover {
  background: #1d4ed8;
}

.btn-secondary {
  background: white;
  color: #475569;
  border: 1px solid #cbd5e1;
  padding: 10px 16px;
  border-radius: 8px;
  font-weight: 500;
  font-size: 14px;
  cursor: pointer;
}

.font-mono {
  font-family: monospace;
}
</style>