<script setup>
import { ref, computed, onMounted } from 'vue'
import { supabase } from '../../supabase'

const loading = ref(true)
const clients = ref([])
const searchFilter = ref('')
const selectedClient = ref(null)

// Modals state
const isClientModalOpen = ref(false)
const isEditMode = ref(false)
const clientEditeId = ref(null)

const formClient = ref({
  est_particulier: false,
  nom_societe: '',
  contact: '',
  email: '',
  telephone: '',
  adresse: '',
  cp: '',
  ville: '',
  siret: '',
  tva_intra: '',
  rcs: '',
  ape: '',
  sans_tva: false,
  recap_interventions: false,
  multi_etab: false,
  modele_facture: 'condense'
})

const optionsModeleFacture = [
  { label: 'Facture condensée (Regroupée)', value: 'condense' },
  { label: 'Facture détaillée (Ligne par ligne)', value: 'detaille' }
]

// Sites Modal
const isSitesModalOpen = ref(false)
const sitesList = ref([])
const siteEditeId = ref(null)
const formSite = ref({ nom_site: '', adresse: '', cp: '', ville: '' })

// Tarifs Modal (Refondue plus propre)
const isTarifsModalOpen = ref(false)
const prestationsList = ref([])
const tarifsMap = ref({})

// PDF Modal
const isPdfModalOpen = ref(false)
const pdfTypesDisponibles = ["Factures", "Devis"]
const pdfTypeSelectionne = ref("Factures")
const pdfFichiersBruts = ref([])
const pdfFichierActif = ref(null)
const isViewerPdfOpen = ref(false)
const pdfUrlVisionneuse = ref('')

const userId = ref(null)

const fetchData = async () => {
  loading.value = true
  const { data: { user } } = await supabase.auth.getUser()
  if (user) {
    userId.value = user.id
    await chargerClients()
  }
  loading.value = false
}

onMounted(() => {
  fetchData()
})

async function chargerClients() {
  if (!userId.value) return
  const { data, error } = await supabase
    .from("clients")
    .select("*")
    .eq("user_id", userId.value)
    .order("nom_societe", { ascending: true })

  if (error) {
    console.error(error)
    alert("Erreur lors du chargement des clients.")
  } else {
    clients.value = (data || []).map(r => ({
      ...r,
      type_client: r.est_particulier ? "Particulier" : "Professionnel",
      multisite_txt: r.multi_etab ? "Oui" : "Non",
      recap_txt: r.recap_interventions ? "Oui" : "Non",
      adresse_txt: r.adresse || "-",
      cp_ville_txt: (r.cp || r.ville) ? `${r.cp || ''} ${r.ville || ''}`.trim() : "-",
      contact_nom: r.contact || "-",
      contact_email: r.email || ""
    }))
  }
}

const filteredClients = computed(() => {
  if (!searchFilter.value) return clients.value
  const q = searchFilter.value.toLowerCase()
  return clients.value.filter(c => 
    c.nom_societe?.toLowerCase().includes(q) ||
    c.contact?.toLowerCase().includes(q) ||
    c.ville?.toLowerCase().includes(q) ||
    c.email?.toLowerCase().includes(q)
  )
})

function selectRow(client) {
  selectedClient.value = client
}

function openClientModal(client = null) {
  if (client) {
    isEditMode.value = true
    clientEditeId.value = client.id
    formClient.value = { ...client }
  } else {
    isEditMode.value = false
    clientEditeId.value = null
    formClient.value = {
      est_particulier: false,
      nom_societe: '',
      contact: '',
      email: '',
      telephone: '',
      adresse: '',
      cp: '',
      ville: '',
      siret: '',
      tva_intra: '',
      rcs: '',
      ape: '',
      sans_tva: false,
      recap_interventions: false,
      multi_etab: false,
      modele_facture: 'condense'
    }
  }
  isClientModalOpen.value = true
}

// Nettoyage immédiat des champs pros si Particulier est coché
function toggleTypeClient(val) {
  if (val) {
    formClient.value.siret = ''
    formClient.value.tva_intra = ''
    formClient.value.rcs = ''
    formClient.value.ape = ''
    formClient.value.sans_tva = false
    formClient.value.recap_interventions = false
    formClient.value.multi_etab = false
    formClient.value.modele_facture = 'condense'
  }
}

async function sauvegarderClient() {
  if (!formClient.value.nom_societe?.trim()) {
    alert("Le nom / raison sociale est obligatoire.")
    return
  }

  const est_part = Boolean(formClient.value.est_particulier)
  const payload = {
    user_id: userId.value,
    nom_societe: formClient.value.nom_societe.trim(),
    contact: formClient.value.contact,
    adresse: formClient.value.adresse,
    cp: formClient.value.cp,
    ville: formClient.value.ville,
    email: formClient.value.email,
    telephone: formClient.value.telephone,
    est_particulier: est_part,
    siret: est_part ? '' : formClient.value.siret,
    tva_intra: est_part ? '' : formClient.value.tva_intra,
    rcs: est_part ? '' : formClient.value.rcs,
    ape: est_part ? '' : formClient.value.ape,
    sans_tva: est_part ? false : Boolean(formClient.value.sans_tva),
    recap_interventions: est_part ? false : Boolean(formClient.value.recap_interventions),
    multi_etab: est_part ? false : Boolean(formClient.value.multi_etab),
    modele_facture: est_part ? 'condense' : (formClient.value.modele_facture || 'condense')
  }

  if (clientEditeId.value) {
    const { error } = await supabase.from("clients").update(payload).eq("id", clientEditeId.value)
    if (error) { alert("Erreur mise à jour."); return; }
  } else {
    const { error } = await supabase.from("clients").insert(payload)
    if (error) { alert("Erreur création."); return; }
  }

  isClientModalOpen.value = false
  await chargerClients()
}

async function supprimerClient(client) {
  if (!confirm(`Voulez-vous supprimer le client « ${client.nom_societe} » ?`)) return
  const { error } = await supabase.from("clients").delete().eq("id", client.id)
  if (error) { alert("Erreur lors de la suppression."); return; }
  selectedClient.value = null
  await chargerClients()
}

// Sites / Multisite
async function ouvrirDialogueSites(client) {
  selectedClient.value = client
  siteEditeId.value = null
  formSite.value = { nom_site: '', adresse: '', cp: '', ville: '' }
  await chargerSites(client.id)
  isSitesModalOpen.value = true
}

async function chargerSites(clientId) {
  const { data } = await supabase.from("etablissements").select("*").eq("client_id", clientId).order("nom_site", { ascending: true })
  sitesList.value = data || []
}

function chargerSitePourEdition(site) {
  siteEditeId.value = site.id
  formSite.value = { nom_site: site.nom_site, adresse: site.adresse, cp: site.cp, ville: site.ville }
}

async function sauvegarderSite() {
  if (!formSite.value.nom_site?.trim()) {
    alert("Veuillez donner un nom au site.")
    return
  }
  const payload = {
    user_id: userId.value,
    client_id: selectedClient.value.id,
    nom_site: formSite.value.nom_site.trim(),
    adresse: formSite.value.adresse,
    cp: formSite.value.cp,
    ville: formSite.value.ville
  }

  if (siteEditeId.value) {
    await supabase.from("etablissements").update(payload).eq("id", siteEditeId.value)
  } else {
    await supabase.from("etablissements").insert(payload)
  }

  siteEditeId.value = null
  formSite.value = { nom_site: '', adresse: '', cp: '', ville: '' }
  await chargerSites(selectedClient.value.id)
}

async function supprimerSite(siteId) {
  await supabase.from("etablissements").delete().eq("id", siteId)
  await chargerSites(selectedClient.value.id)
}

// Tarifs
async function ouvrirDialogueTarifs(client) {
  selectedClient.value = client
  const [resPres, resTarifs] = await Promise.all([
    supabase.from("prestations").select("*").eq("user_id", userId.value).order("designation", { ascending: true }),
    supabase.from("client_tarifs").select("*").eq("client_id", client.id)
  ])

  prestationsList.value = resPres.data || []
  const tarifsExistants = {}
  ;(resTarifs.data || []).forEach(t => { tarifsExistants[t.prestation_id] = t })

  const map = {}
  prestationsList.value.forEach(p => {
    const t = tarifsExistants[p.id]
    map[p.id] = {
      actif: t ? (t.est_actif ?? true) : true,
      prix: t && t.prix_specifique_ht !== null ? Number(t.prix_specifique_ht) : Number(p.prix_ht)
    }
  })
  tarifsMap.value = map
  isTarifsModalOpen.value = true
}

async function enregistrerTarifs() {
  const upserts = []
  for (const p of prestationsList.value) {
    const item = tarifsMap.value[p.id]
    upserts.push({
      user_id: userId.value,
      client_id: selectedClient.value.id,
      prestation_id: p.id,
      prix_specifique_ht: Number(item.prix || 0),
      est_actif: Boolean(item.actif)
    })
  }

  const { error } = await supabase.from("client_tarifs").upsert(upserts, { onConflict: 'client_id,prestation_id' })
  if (error) {
    alert("Erreur lors de l’enregistrement des tarifs.")
    return
  }
  isTarifsModalOpen.value = false
}

// PDF
function ouvrirExplorateurPdfClient(client) {
  selectedClient.value = client
  pdfTypeSelectionne.value = "Factures"
  isPdfModalOpen.value = true
}

function ouvrirNoteImportante() {
  alert("Points d'attention - Fichier Clients:\n\n• Pour un professionnel, indiquez le nom de l'entreprise ; pour un particulier, le nom et le prénom.\n• L'adresse de facturation est obligatoire.\n• L'e-mail de contact est indispensable pour l'envoi automatisé.")
}
</script>

<template>
  <div class="page-container">
    
    <!-- En-tête -->
    <div class="header-card">
      <div>
        <h1 class="page-title">Gestion des Clients</h1>
        <p class="page-subtitle">Gérez votre fichier clients et leurs paramètres spécifiques.</p>
      </div>
      
      <div class="header-actions">
        <button @click="ouvrirNoteImportante()" class="btn-secondary-clean">
          <span class="material-icons text-sm text-amber-600">warning</span> Infos Importantes
        </button>
        <button @click="openClientModal()" class="btn-primary-clean">
          <span class="material-icons text-sm">person_add</span> Nouveau Client
        </button>
      </div>
    </div>

    <!-- Contenu -->
    <div class="content-card">
      <div class="search-bar">
        <span class="material-icons text-slate-400">search</span>
        <input 
          v-model="searchFilter" 
          type="text" 
          placeholder="Rechercher un client..." 
          class="search-input"
        />
      </div>

      <div v-if="loading" class="loading-state">
        Chargement des clients...
      </div>

      <div v-else-if="filteredClients.length === 0" class="empty-state">
        Aucun client enregistré pour le moment.
      </div>

      <!-- Tableau Responsive Amélioré pour Mobile -->
      <div v-else class="table-responsive-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>Nom / Société</th>
              <th class="text-center">Type</th>
              <th class="hide-mobile">Contact / Email</th>
              <th class="hide-mobile">Adresse</th>
              <th class="hide-mobile">CP / Ville</th>
              <th class="text-center hide-mobile">Multisite</th>
              <th class="text-center hide-mobile">Récap. Auto</th>
            </tr>
          </thead>
          <tbody>
            <tr 
              v-for="item in filteredClients" 
              :key="item.id" 
              @click="selectRow(item)" 
              class="clickable-row"
              :class="{ 'bg-blue-50': selectedClient?.id === item.id }"
            >
              <td class="font-medium text-slate-900">
                {{ item.nom_societe }}
                <div class="text-xs text-slate-500 font-normal sm:hidden mt-0.5" v-if="item.contact_email">
                  {{ item.contact_email }}
                </div>
              </td>
              <td class="text-center">
                <span :class="item.est_particulier ? 'badge-purple' : 'badge-blue'">
                  {{ item.type_client }}
                </span>
              </td>
              <td class="hide-mobile">
                <div class="font-medium text-slate-800">{{ item.contact_nom }}</div>
                <div v-if="item.contact_email" class="text-xs text-slate-500">{{ item.contact_email }}</div>
              </td>
              <td class="hide-mobile">{{ item.adresse_txt }}</td>
              <td class="hide-mobile">{{ item.cp_ville_txt }}</td>
              <td class="text-center hide-mobile">
                <span :class="item.multi_etab ? 'badge-teal' : 'badge-grey'">{{ item.multisite_txt }}</span>
              </td>
              <td class="text-center hide-mobile">
                <span :class="item.recap_interventions ? 'badge-emerald' : 'badge-grey'">{{ item.recap_txt }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Barre d'actions contextuelles -->
      <div v-if="selectedClient" class="action-bar-card">
        <div class="font-semibold text-slate-700 text-sm">
          Client sélectionné : {{ selectedClient.nom_societe }}
        </div>
        <div class="flex gap-2 flex-wrap">
          <button @click="ouvrirExplorateurPdfClient(selectedClient)" class="btn-action text-cyan-700 border-cyan-300 hover:bg-cyan-50">
            <span class="material-icons text-sm">search</span> Chercher PDF
          </button>
          <button v-if="selectedClient.multi_etab" @click="ouvrirDialogueSites(selectedClient)" class="btn-action text-amber-700 border-amber-300 hover:bg-amber-50">
            <span class="material-icons text-sm">business</span> Établissements
          </button>
          <button @click="ouvrirDialogueTarifs(selectedClient)" class="btn-action text-teal-700 border-teal-300 hover:bg-teal-50">
            <span class="material-icons text-sm">sell</span> Tarifs & Prestations
          </button>
          <button @click="openClientModal(selectedClient)" class="btn-action text-blue-700 border-blue-300 hover:bg-blue-50">
            <span class="material-icons text-sm">edit</span> Modifier
          </button>
          <button @click="supprimerClient(selectedClient)" class="btn-action text-red-700 border-red-300 hover:bg-red-50">
            <span class="material-icons text-sm">delete</span> Supprimer
          </button>
        </div>
      </div>
    </div>

    <!-- MODALE CLIENT -->
    <div v-if="isClientModalOpen" class="modal-overlay">
      <div class="modal-card max-w-3xl">
        <div class="modal-header">
          <h2>{{ isEditMode ? 'Modifier le client' : 'Nouveau client' }}</h2>
          <button @click="isClientModalOpen = false" class="close-btn">&times;</button>
        </div>

        <div class="modal-body space-y-4">
          <label class="flex items-center gap-2 cursor-pointer bg-slate-50 p-3 rounded-lg border">
            <input type="checkbox" v-model="formClient.est_particulier" @change="toggleTypeClient(formClient.est_particulier)" class="w-4 h-4 text-blue-600 rounded" />
            <span class="text-sm font-semibold text-slate-800">Client Particulier (désactive les champs professionnels)</span>
          </label>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div class="space-y-3">
              <div class="text-xs font-bold text-slate-500 uppercase">Coordonnées générales</div>
              <div class="input-group">
                <label>Nom Société / Nom Complet *</label>
                <input v-model="formClient.nom_societe" type="text" class="input-field" required />
              </div>
              <div class="input-group">
                <label>Contact Référent</label>
                <input v-model="formClient.contact" type="text" class="input-field" />
              </div>
              <div class="grid grid-cols-2 gap-2">
                <div class="input-group"><label>Email</label><input v-model="formClient.email" type="email" class="input-field" /></div>
                <div class="input-group"><label>Téléphone</label><input v-model="formClient.telephone" type="text" class="input-field" /></div>
              </div>
              <div class="input-group">
                <label>Adresse</label>
                <input v-model="formClient.adresse" type="text" class="input-field" />
              </div>
              <div class="grid grid-cols-3 gap-2">
                <div class="input-group"><label>Code Postal</label><input v-model="formClient.cp" type="text" class="input-field" /></div>
                <div class="input-group col-span-2"><label>Ville</label><input v-model="formClient.ville" type="text" class="input-field" /></div>
              </div>
            </div>

            <div class="space-y-3">
              <div class="p-3 bg-slate-50 border rounded-lg space-y-2 transition-opacity" :class="{ 'opacity-40 pointer-events-none bg-slate-100': formClient.est_particulier }">
                <div class="text-xs font-bold text-slate-500 uppercase">Informations Professionnelles</div>
                <div class="grid grid-cols-2 gap-2">
                  <div class="input-group"><label>SIRET</label><input v-model="formClient.siret" type="text" class="input-field" :disabled="formClient.est_particulier" /></div>
                  <div class="input-group"><label>TVA Intra</label><input v-model="formClient.tva_intra" type="text" class="input-field" :disabled="formClient.est_particulier" /></div>
                </div>
              </div>

              <div class="p-3 bg-slate-50 border rounded-lg space-y-2 transition-opacity" :class="{ 'opacity-40 pointer-events-none bg-slate-100': formClient.est_particulier }">
                <div class="text-xs font-bold text-slate-500 uppercase">Paramètres de Facturation</div>
                <label class="flex items-center gap-2 text-xs font-medium text-slate-700 cursor-pointer"><input type="checkbox" v-model="formClient.sans_tva" :disabled="formClient.est_particulier" /> Exonérer de TVA</label>
                <label class="flex items-center gap-2 text-xs font-medium text-slate-700 cursor-pointer"><input type="checkbox" v-model="formClient.recap_interventions" :disabled="formClient.est_particulier" /> Récap. auto PDF</label>
                <label class="flex items-center gap-2 text-xs font-medium text-slate-700 cursor-pointer"><input type="checkbox" v-model="formClient.multi_etab" :disabled="formClient.est_particulier" /> Client Multisite</label>
                <div class="input-group mt-2">
                  <label>Modèle de Facture</label>
                  <select v-model="formClient.modele_facture" class="input-field" :disabled="formClient.est_particulier">
                    <option v-for="m in optionsModeleFacture" :key="m.value" :value="m.value">{{ m.label }}</option>
                  </select>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="isClientModalOpen = false" class="btn-secondary">Annuler</button>
          <button @click="sauvegarderClient" class="btn-primary">Enregistrer</button>
        </div>
      </div>
    </div>

    <!-- MODALE SITES -->
    <div v-if="isSitesModalOpen" class="modal-overlay">
      <div class="modal-card max-w-lg">
        <div class="modal-header">
          <h2>Établissements : {{ selectedClient?.nom_societe }}</h2>
          <button @click="isSitesModalOpen = false" class="close-btn">&times;</button>
        </div>
        <div class="modal-body space-y-3">
          <div v-if="sitesList.length === 0" class="text-slate-400 italic text-sm">Aucun site secondaire.</div>
          <div v-for="s in sitesList" :key="s.id" class="flex justify-between items-center p-2 bg-slate-50 border rounded">
            <div>
              <div class="font-bold text-sm">{{ s.nom_site }}</div>
              <div class="text-xs text-slate-500">{{ s.adresse }}, {{ s.cp }} {{ s.ville }}</div>
            </div>
            <div class="flex gap-1">
              <button @click="chargerSitePourEdition(s)" class="p-1 text-blue-600"><span class="material-icons text-sm">edit</span></button>
              <button @click="supprimerSite(s.id)" class="p-1 text-red-600"><span class="material-icons text-sm">delete</span></button>
            </div>
          </div>

          <div class="border-t pt-3 space-y-2">
            <input v-model="formSite.nom_site" placeholder="Nom du site" class="input-field" />
            <input v-model="formSite.adresse" placeholder="Adresse" class="input-field" />
            <div class="grid grid-cols-3 gap-2">
              <input v-model="formSite.cp" placeholder="CP" class="input-field" />
              <input v-model="formSite.ville" placeholder="Ville" class="input-field col-span-2" />
            </div>
            <button @click="sauvegarderSite" class="w-full btn-primary mt-2">{{ siteEditeId ? 'Modifier le site' : 'Ajouter le site' }}</button>
          </div>
        </div>
        <div class="modal-footer">
          <button @click="isSitesModalOpen = false" class="btn-secondary">Fermer</button>
        </div>
      </div>
    </div>

    <!-- MODALE TARIFS (REFONDUE & PROPRE) -->
    <div v-if="isTarifsModalOpen" class="modal-overlay">
      <div class="modal-card max-w-2xl">
        <div class="modal-header">
          <div>
            <h2>Tarifs spécifiques</h2>
            <p class="text-xs text-slate-500 mt-0.5">Client : {{ selectedClient?.nom_societe }}</p>
          </div>
          <button @click="isTarifsModalOpen = false" class="close-btn">&times;</button>
        </div>

        <div class="modal-body space-y-3 max-h-[60vh] overflow-y-auto">
          <div class="text-xs text-slate-600 bg-blue-50 border border-blue-100 p-3 rounded-lg mb-2">
            Activez ou désactivez les prestations pour ce client et ajustez les prix unitaires HT spécifiques si nécessaire.
          </div>

          <div class="tarifs-table-container">
            <div v-for="p in prestationsList" :key="p.id" class="tarif-row" :class="{ 'opacity-50 bg-slate-100': !tarifsMap[p.id]?.actif }">
              <div class="flex items-center gap-3">
                <input type="checkbox" v-model="tarifsMap[p.id].actif" class="w-4 h-4 text-blue-600 rounded cursor-pointer" />
                <div>
                  <div class="text-sm font-semibold text-slate-800">{{ p.designation }}</div>
                  <div class="text-xs text-slate-500">Prix catalogue de base : {{ Number(p.prix_ht).toFixed(2) }} € HT</div>
                </div>
              </div>
              <div class="flex items-center gap-1.5">
                <input 
                  v-model.number="tarifsMap[p.id].prix" 
                  type="number" 
                  step="0.01" 
                  class="input-field w-28 text-right font-mono font-medium" 
                  :disabled="!tarifsMap[p.id]?.actif" 
                />
                <span class="text-xs font-semibold text-slate-600">€ HT</span>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="isTarifsModalOpen = false" class="btn-secondary">Annuler</button>
          <button @click="enregistrerTarifs" class="btn-primary">Enregistrer les tarifs</button>
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
  box-sizing: border-box;
}

.header-card {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  background: white;
  padding: 16px;
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  border: 1px solid #e2e8f0;
  margin-bottom: 16px;
  flex-direction: column;
  gap: 12px;
}

@media (min-width: 640px) {
  .header-card {
    flex-direction: row;
    align-items: center;
    padding: 20px;
    margin-bottom: 20px;
  }
}

.header-actions {
  display: flex;
  gap: 8px;
  width: 100%;
  flex-wrap: wrap;
}

@media (min-width: 640px) {
  .header-actions {
    width: auto;
  }
}

.page-title { font-size: 20px; font-weight: bold; margin: 0; color: #0f172a; }
.page-subtitle { font-size: 12px; color: #64748b; margin: 4px 0 0 0; }

.btn-primary-clean {
  display: inline-flex; align-items: center; justify-content: center; gap: 6px; background: #2563eb; color: white; border: none; padding: 8px 12px; border-radius: 8px; font-weight: 500; font-size: 13px; cursor: pointer; flex: 1;
}
.btn-secondary-clean {
  display: inline-flex; align-items: center; justify-content: center; gap: 6px; background: white; color: #475569; border: 1px solid #cbd5e1; padding: 8px 12px; border-radius: 8px; font-weight: 500; font-size: 13px; cursor: pointer; flex: 1;
}

@media (min-width: 640px) {
  .btn-primary-clean, .btn-secondary-clean {
    flex: unset;
    padding: 10px 16px;
    font-size: 14px;
  }
}

.content-card {
  background: white; padding: 12px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border: 1px solid #e2e8f0; display: flex; flex-direction: column; gap: 12px;
}

@media (min-width: 640px) {
  .content-card {
    padding: 16px;
    gap: 16px;
  }
}

.search-bar {
  display: flex; align-items: center; gap: 8px; background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 8px 12px;
}
.search-input { border: none; background: transparent; outline: none; font-size: 14px; width: 100%; color: #1e293b; }

.table-responsive-wrapper {
  width: 100%;
  overflow-x: auto;
}

.data-table { 
  width: 100%; 
  border-collapse: collapse; 
  text-align: left; 
  font-size: 13px; 
}

@media (min-width: 640px) {
  .data-table {
    font-size: 14px;
  }
}

.data-table th { background: #f8fafc; padding: 10px 12px; font-weight: 600; color: #475569; border-bottom: 1px solid #e2e8f0; text-transform: uppercase; font-size: 10px; }
.data-table td { padding: 12px; border-bottom: 1px solid #f1f5f9; }

@media (min-width: 640px) {
  .data-table th { padding: 12px 16px; font-size: 11px; }
  .data-table td { padding: 14px 16px; }
}

/* Masquer les colonnes trop larges sur mobile pour éviter l'écrasement */
.hide-mobile {
  display: none;
}
@media (min-width: 768px) {
  .hide-mobile {
    display: table-cell;
  }
}

.clickable-row { cursor: pointer; transition: background 0.15s; }
.clickable-row:hover td { background: #f8fafc; }

.action-bar-card { display: flex; justify-content: space-between; align-items: center; padding: 12px 16px; background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; margin-top: 12px; flex-wrap: wrap; gap: 10px; }
.btn-action { display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 6px; font-size: 13px; font-weight: 500; background: white; border: 1px solid; cursor: pointer; }

/* Badges */
.badge-purple { background: #f3e8ff; color: #6b21a8; padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 500; }
.badge-blue { background: #eff6ff; color: #1e40af; padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 500; }
.badge-teal { background: #f0fdf4; color: #166534; padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 500; }
.badge-emerald { background: #ecfdf5; color: #047857; padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 500; }
.badge-grey { background: #f1f5f9; color: #475569; padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 500; }

/* Modales */
.modal-overlay { position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 12px; box-sizing: border-box; }
.modal-card { background: white; width: 100%; border-radius: 14px; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.15); border: 1px solid #e2e8f0; display: flex; flex-direction: column; overflow: hidden; max-height: 90vh; }
.modal-header { padding: 16px 20px; display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e2e8f0; }
.modal-header h2 { font-size: 17px; font-weight: bold; margin: 0; color: #0f172a; }
.close-btn { background: none; border: none; font-size: 24px; color: #64748b; cursor: pointer; }
.modal-body { padding: 16px 20px; overflow-y: auto; }
.modal-footer { padding: 14px 20px; background: #f8fafc; border-top: 1px solid #e2e8f0; display: flex; justify-content: flex-end; gap: 10px; }

.input-group { display: flex; flex-direction: column; gap: 4px; }
.input-group label { font-size: 11px; font-weight: 600; color: #475569; text-transform: uppercase; }
.input-field { width: 100%; padding: 8px 10px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px; background: #f8fafc; outline: none; box-sizing: border-box; }
.input-field:focus { background: white; border-color: #2563eb; }

/* Tarifs Modal Specific Styles */
.tarifs-table-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.tarif-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  transition: all 0.2s ease;
}
.tarif-row:hover {
  border-color: #cbd5e1;
  background: #f1f5f9;
}

.btn-primary { background: #2563eb; color: white; border: none; padding: 8px 16px; border-radius: 6px; font-weight: 500; font-size: 14px; cursor: pointer; }
.btn-secondary { background: white; color: #475569; border: 1px solid #cbd5e1; padding: 8px 14px; border-radius: 6px; font-weight: 500; font-size: 14px; cursor: pointer; }

.loading-state, .empty-state { text-align: center; padding: 30px; color: #64748b; font-style: italic; font-size: 14px; }
</style>