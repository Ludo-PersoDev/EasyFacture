<script setup>
import { ref, onMounted } from 'vue'
import { supabase } from '../../supabase'

const loading = ref(true)
const saving = ref(false)
const successMessage = ref('')

const form = ref({
  nom_entreprise: '',
  siret: '',
  rcs: '',
  ape: '',
  adresse: '',
  code_postal: '',
  ville: '',
  telephone: '',
  email: '',
  nom_banque: '',
  iban: '',
  bic: '',
  tva_exoneree: true,
  num_tva: '',
  mention_tva_exoneree: 'TVA non applicable, art. 293 B du CGI',
  smtp_server: 'smtp.gmail.com',
  smtp_port: 587,
  smtp_user: '',
  smtp_password: '',
  logo_path: ''
})

onMounted(async () => {
  const { data: { user } } = await supabase.auth.getUser()
  if (user) {
    const { data } = await supabase
      .from('parametres')
      .select('*')
      .eq('user_id', user.id)
      .single()

    if (data) {
      form.value = { ...form.value, ...data }
    }
  }
  loading.value = false
})

const uploadLogo = async (event) => {
  const file = event.target.files[0]
  if (!file) return

  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return

  const fileExt = file.name.split('.').pop()
  const fileName = `${user.id}_${Date.now()}.${fileExt}`
  const filePath = `${fileName}`

  // 1. Upload du fichier dans le bucket "logos"
  const { error: uploadError } = await supabase.storage
    .from('logos')
    .upload(filePath, file, { upsert: true })

  if (uploadError) {
    alert("Erreur lors de l'upload du logo : " + uploadError.message)
    return
  }

  // 2. Récupération de l'URL publique
  const { data } = supabase.storage
    .from('logos')
    .getPublicUrl(filePath)

  if (data) {
    form.value.logo_path = data.publicUrl
  }
}

const saveInfos = async () => {
  saving.value = true
  successMessage.value = ''
  
  const { data: { user } } = await supabase.auth.getUser()
  
  // On vérifie si une ligne existe déjà pour cet user_id
  const { data: existing } = await supabase
    .from('parametres')
    .select('id')
    .eq('user_id', user.id)
    .single()

  let error = null

  if (existing) {
    // Mise à jour si la ligne existe
    const res = await supabase
      .from('parametres')
      .update(form.value)
      .eq('user_id', user.id)
    error = res.error
  } else {
    // Insertion si c'est la première fois
    const res = await supabase
      .from('parametres')
      .insert({
        user_id: user.id,
        ...form.value
      })
    error = res.error
  }

  if (error) {
    console.error(error)
    alert("Erreur lors de la sauvegarde : " + error.message)
  } else {
    successMessage.value = "Paramètres sauvegardés avec succès !"
    setTimeout(() => successMessage.value = '', 3000)
  }
  saving.value = false
}
</script>

<template>
  <div class="page-container">
    
    <!-- En-tête -->
    <div class="header-card">
      <div>
        <h1 class="page-title">Paramètres de l'entreprise</h1>
        <p class="page-subtitle">Ces informations apparaîtront sur tous vos documents officiels (devis/factures).</p>
      </div>
      
      <button @click="saveInfos" :disabled="saving" class="btn-primary">
        {{ saving ? 'Enregistrement...' : 'Enregistrer les modifications' }}
      </button>
    </div>

    <div v-if="loading" class="loading-state">
      Chargement de vos paramètres...
    </div>

    <!-- Formulaire principal -->
    <form v-else @submit.prevent="saveInfos" class="main-form">
      
      <div class="grid-container">
        
        <!-- COLONNE GAUCHE -->
        <div class="column-group">
          
          <h2 class="section-title">Identité & Image de Marque</h2>
          
          <div class="row-grid-3">
            <div class="span-2 space-y">
              <div class="input-group">
                <label>Nom / Raison Sociale</label>
                <input v-model="form.nom_entreprise" type="text" required class="input-field" />
              </div>
              <div class="input-group">
                <label>Adresse</label>
                <input v-model="form.adresse" type="text" class="input-field" />
              </div>
              
              <div class="row-flex responsive-split">
                <div class="input-group width-33">
                  <label>Code Postal</label>
                  <input v-model="form.code_postal" type="text" class="input-field" />
                </div>
                <div class="input-group width-66">
                  <label>Ville</label>
                  <input v-model="form.ville" type="text" class="input-field" />
                </div>
              </div>
            </div>

            <!-- Bloc Logo -->
			<div class="logo-box">
			  <span class="logo-label">Logo</span>
			  <div class="logo-preview">
				<img v-if="form.logo_path" :src="form.logo_path" class="logo-img" alt="Logo" />
				<span v-else class="logo-empty">Aucun logo</span>
			  </div>
			  <label class="btn-upload">
				📁 Choisir un logo
				<input type="file" accept="image/*" @change="uploadLogo" class="hidden-input" />
			  </label>
			</div>
          </div>

          <div class="row-flex responsive-split gap-4">
            <div class="input-group flex-1">
              <label>Téléphone</label>
              <input v-model="form.telephone" type="tel" class="input-field" />
            </div>
            <div class="input-group flex-1">
              <label>E-mail de contact</label>
              <input v-model="form.email" type="email" class="input-field" />
            </div>
          </div>

          <h2 class="section-title mt-4">Coordonnées Bancaires</h2>
          
          <!-- Banque & BIC sur la même ligne, IBAN sur sa propre ligne -->
          <div class="space-y">
            <div class="row-flex responsive-split gap-4">
              <div class="input-group flex-2">
                <label>Banque</label>
                <input v-model="form.nom_banque" type="text" class="input-field" />
              </div>
              <div class="input-group flex-1">
                <label>BIC / SWIFT</label>
                <input v-model="form.bic" type="text" class="input-field font-mono" />
              </div>
            </div>
            <div class="input-group">
              <label>IBAN</label>
              <input v-model="form.iban" type="text" class="input-field font-mono" />
            </div>
          </div>

        </div>

        <!-- COLONNE DROITE -->
        <div class="column-group">
          
          <h2 class="section-title">Immatriculation & Fiscalité</h2>

          <div class="row-grid-immat">
            <div class="input-group span-siret">
              <label>SIRET</label>
              <input v-model="form.siret" type="text" required class="input-field" />
            </div>
            <div class="input-group span-ape">
              <label>Code APE</label>
              <input v-model="form.ape" type="text" class="input-field" />
            </div>
            <div class="input-group span-rcs">
              <label>RCS</label>
              <input v-model="form.rcs" type="text" class="input-field" />
            </div>
          </div>

          <div class="sub-card">
            <label class="checkbox-label">
              <input v-model="form.tva_exoneree" type="checkbox" class="checkbox-input" />
              <span>Entreprise exonérée de TVA</span>
            </label>
            <div class="input-group">
              <label>Mention légale d'exonération</label>
              <input v-model="form.mention_tva_exoneree" type="text" :disabled="!form.tva_exoneree" class="input-field bg-white disabled-field" />
            </div>
            <div class="input-group">
              <label>N° TVA Intracommunautaire</label>
              <input v-model="form.num_tva" type="text" :disabled="form.tva_exoneree" class="input-field bg-white disabled-field" />
            </div>
          </div>

          <h2 class="section-title mt-4">Configuration E-mail (SMTP)</h2>
          
          <!-- SMTP + Port sur la ligne 1, Email d'envoi sur la ligne 2, Mot de passe sur la ligne 3 -->
          <div class="space-y">
            <div class="row-grid-smtp">
              <div class="input-group span-server">
                <label>Serveur SMTP</label>
                <input v-model="form.smtp_server" type="text" class="input-field" />
              </div>
              <div class="input-group span-port">
                <label>Port SMTP</label>
                <input v-model.number="form.smtp_port" type="number" class="input-field" />
              </div>
            </div>
            <div class="input-group">
              <label>E-mail d'envoi</label>
              <input v-model="form.smtp_user" type="email" class="input-field" />
            </div>
            <div class="input-group">
              <label>Mot de passe d'application</label>
              <input v-model="form.smtp_password" type="password" class="input-field" />
            </div>
          </div>

        </div>

      </div>

      <!-- Bouton bas de page -->
      <div class="form-footer">
        <button type="submit" :disabled="saving" class="btn-primary-full">
          {{ saving ? 'Enregistrement en cours...' : 'Enregistrer les modifications' }}
        </button>
      </div>

      <div v-if="successMessage" class="success-alert">
        {{ successMessage }}
      </div>

    </form>
  </div>
</template>

<style scoped>
.page-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
  font-family: system-ui, -apple-system, sans-serif;
  color: #1e293b;
  background: linear-gradient(135deg, #f8fafc 0%, #eff6ff 100%);
  min-height: 100vh;
}

.header-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
  padding: 24px;
  border-radius: 14px;
  box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.05), 0 2px 4px -2px rgba(37, 99, 235, 0.05);
  border: 1px solid #dbeafe;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 16px;
}

.page-title {
  font-size: 24px;
  font-weight: bold;
  margin: 0;
  color: #1e3a8a;
}

.page-subtitle {
  font-size: 14px;
  color: #64748b;
  margin: 4px 0 0 0;
}

.main-form {
  background: white;
  padding: 32px;
  border-radius: 14px;
  box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
  border: 1px solid #e2e8f0;
}

.grid-container {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 32px;
  align-items: start;
}

@media (max-width: 1024px) {
  .grid-container {
    grid-template-columns: 1fr;
  }
}

.column-group {
  display: flex;
  flex-direction: column;
  gap: 20px;
  background: #fafafa;
  padding: 20px;
  border-radius: 12px;
  border: 1px solid #f1f5f9;
}

.section-title {
  font-size: 15px;
  font-weight: 700;
  color: #1e40af;
  border-bottom: 2px solid #dbeafe;
  padding-bottom: 8px;
  margin: 0 0 4px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.input-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.input-group label, .column-group label {
  font-size: 12px;
  font-weight: 600;
  color: #475569;
  text-transform: uppercase;
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
  transition: all 0.2s;
}

.input-field:focus {
  background: white;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
}

.row-grid-3 {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 16px;
  align-items: start;
}

/* Grille d'immatriculation : 1 info par ligne sur mobile, agencement personnalisé sur desktop */
.row-grid-immat {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

@media (min-width: 768px) {
  .row-grid-immat {
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 12px;
  }
  .span-siret {
    grid-column: 1 / 2;
  }
  .span-ape {
    grid-column: 2 / 3;
  }
  .span-rcs {
    grid-column: 1 / 3;
  }
}

/* Grille SMTP : 1 info par ligne sur mobile, serveur + port côte à côte sur desktop */
.row-grid-smtp {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

@media (min-width: 768px) {
  .row-grid-smtp {
    display: grid;
    grid-template-columns: 3fr 1fr;
    gap: 12px;
  }
  .span-server {
    grid-column: 1 / 2;
  }
  .span-port {
    grid-column: 2 / 3;
  }
}

.row-flex {
  display: flex;
  gap: 12px;
}

@media (max-width: 640px) {
  .responsive-split {
    flex-direction: column;
  }
}

.width-33 { flex: 1; }
.width-66 { flex: 2; }
.flex-1 { flex: 1; }
.flex-2 { flex: 2; }

.span-2 { grid-column: span 2; }
.space-y { display: flex; flex-direction: column; gap: 16px; }

.logo-box {
  border: 2px dashed #93c5fd;
  border-radius: 8px;
  background: #eff6ff;
  padding: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  gap: 8px;
  height: 100%;
  box-sizing: border-box;
}

.logo-label {
  font-size: 11px;
  font-weight: 600;
  color: #1e40af;
  text-transform: uppercase;
}

.logo-preview {
  min-height: 50px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-img {
  max-height: 50px;
  object-fit: contain;
  border-radius: 4px;
}

.logo-empty {
  font-size: 11px;
  color: #3b82f6;
  font-style: italic;
}

.sub-card {
  background: #f0fdf4;
  padding: 16px;
  border-radius: 8px;
  border: 1px solid #bbf7d0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.checkbox-label {
  display: flex;
  align-items: center;
}

.checkbox-label span {
  font-size: 13px;
  font-weight: 600;
  color: #166534;
  text-transform: none;
}

.checkbox-input {
  width: 16px;
  height: 16px;
  margin-right: 8px;
  accent-color: #16a34a;
}

.disabled-field:disabled {
  opacity: 0.5;
  background: #f1f5f9;
}

.btn-primary {
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2);
  transition: all 0.2s;
}

.btn-primary:hover {
  background: linear-gradient(1idg, #1d4ed8 0%, #1e40af 100%);
  box-shadow: 0 4px 6px rgba(37, 99, 235, 0.3);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.form-footer {
  margin-top: 32px;
  padding-top: 20px;
  border-top: 1px solid #e2e8f0;
}

.btn-primary-full {
  width: 100%;
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
  color: white;
  border: none;
  padding: 12px;
  border-radius: 8px;
  font-weight: 600;
  font-size: 15px;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(37, 99, 235, 0.2);
  transition: all 0.2s;
}

.btn-primary-full:hover {
  background: linear-gradient(135deg, #1d4ed8 0%, #1e40af 100%);
  box-shadow: 0 4px 6px rgba(37, 99, 235, 0.3);
}

.btn-upload {
  display: inline-block;
  background: white;
  border: 1px solid #93c5fd;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  color: #1e40af;
  cursor: pointer;
  transition: background 0.2s;
}
.btn-upload:hover {
  background: #dbeafe;
}
.hidden-input {
  display: none;
}

.success-alert {
  margin-top: 16px;
  padding: 12px;
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  color: #065f46;
  text-align: center;
  border-radius: 8px;
  font-weight: 500;
  font-size: 14px;
}

.font-mono {
  font-family: monospace;
}
</style>