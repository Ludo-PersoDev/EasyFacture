<script setup>
import { ref, computed, onMounted } from 'vue'
import { supabase } from './supabase'
import InfosEntreprise from './components/modules/InfosEntreprise.vue'
import Catalogue from './components/modules/Catalogue.vue'
import Clients from './components/modules/GestionClients.vue'
import DevisList from './components/modules/DevisList.vue'

const session = ref(null)
const emailInput = ref('')
const passwordInput = ref('')
const authLoading = ref(false)
const authError = ref('')
const authSuccess = ref('')
const isRegistering = ref(false)

// État d'onboarding dynamique et navigation
const niveauOnboarding = ref(1)
const currentPage = ref('Accueil')

// Fonction de calcul automatique du niveau d'onboarding
const checkOnboardingStatus = async () => {
  const { data: { user } } = await supabase.auth.getUser()
  if (!user) return

  try {
    // 1. Vérifier si l'entreprise a des infos configurées
    const { data: entrepriseData } = await supabase
      .from('parametres')
      .select('*')
      .eq('user_id', user.id)
      .maybeSingle()

    if (!entrepriseData || !entrepriseData.siret) {
      niveauOnboarding.value = 1
      return
    }

    // 2. Vérifier si le catalogue contient au moins une prestation
    const { count: countPrestations } = await supabase
      .from('prestations')
      .select('*', { count: 'exact', head: true })
      .eq('user_id', user.id)

    if (!countPrestations || countPrestations === 0) {
      niveauOnboarding.value = 2
      return
    }

    // 3. Vérifier si la table clients contient au moins un client
    const { count: countClients } = await supabase
      .from('clients')
      .select('*', { count: 'exact', head: true })
      .eq('user_id', user.id)

    if (!countClients || countClients === 0) {
      niveauOnboarding.value = 3
      return
    }

    // 4. Si tout est bon -> Niveau 4 (Accès total)
    niveauOnboarding.value = 4
  } catch (err) {
    console.error("Erreur lors de la vérification de l'onboarding :", err)
  }
}

onMounted(async () => {
  const { data } = await supabase.auth.getSession()
  session.value = data.session
  if (data.session) {
    await checkOnboardingStatus()
  }

  supabase.auth.onAuthStateChange(async (_event, _session) => {
    session.value = _session
    if (_session) {
      await checkOnboardingStatus()
    }
  })
})

const handleAuth = async () => {
  authLoading.value = true
  authError.value = ''
  authSuccess.value = ''

  if (isRegistering.value) {
    const { error } = await supabase.auth.signUp({
      email: emailInput.value,
      password: passwordInput.value,
    })
    if (error) {
      authError.value = error.message
    } else {
      authSuccess.value = 'Compte créé ! Vérifie tes e-mails pour confirmer ou connecte-toi.'
      isRegistering.value = false
    }
  } else {
    const { error } = await supabase.auth.signInWithPassword({
      email: emailInput.value,
      password: passwordInput.value,
    })
    if (error) {
      authError.value = error.message
    } else {
      await checkOnboardingStatus()
    }
  }
  authLoading.value = false
}

const handleLogout = async () => {
  await supabase.auth.signOut()
  currentPage.value = 'Accueil'
}

const modules = [
  { id: 'Infos de mon entreprise', icon: 'business', title: 'Infos de mon entreprise', color: 'text-slate-600', desc: 'Configuration/modification de mon entreprise', minLevel: 1 },
  { id: 'Clients', icon: 'group', title: 'Clients', color: 'text-teal-600', desc: 'Fichier clients & grille tarifaire', minLevel: 3 },
  { id: 'Catalogue', icon: 'list_alt', title: 'Catalogue', color: 'text-amber-600', desc: 'Liste des prestations & formations', minLevel: 2 },
  { id: 'Devis', icon: 'description', title: 'Devis', color: 'text-blue-600', desc: 'Gestion et conversion des devis', minLevel: 4 },
  { id: 'Interventions', icon: 'event_available', title: 'Suivi des prestations réalisées', color: 'text-emerald-600', desc: 'Saisie et suivi des prestations', minLevel: 4 },
  { id: 'Factures', icon: 'receipt', title: 'Factures', color: 'text-purple-600', desc: 'Facturation & avoirs', minLevel: 4 },
  { id: 'CRM & Analytics', icon: 'bar_chart', title: 'CRM & Analytics', color: 'text-indigo-600', desc: 'Suivi du CA et statistiques', minLevel: 4 },
  { id: 'Passerelle Factur-X', icon: 'cloud_upload', title: 'Passerelle Factur-X', color: 'text-sky-600', desc: 'Export et envoi des PDF vers la plateforme', minLevel: 4 },
  { id: 'Sauvegarde & Maintenance', icon: 'settings_backup_restore', title: 'Sauvegarde & Maintenance', color: 'text-zinc-600', desc: 'Export/Import de la BDD et transfert PC', minLevel: 2 },
]

const onboardingMessage = computed(() => {
  switch (niveauOnboarding.value) {
    case 1:
      return { title: '⚠️ Étape 1 : Configuration de l’entreprise requise', desc: 'Veuillez renseigner les informations de votre entreprise dans les paramètres pour commencer.' }
    case 2:
      return { title: '⚠️ Étape 2 : Votre catalogue de prestations est vide', desc: 'Veuillez ajouter vos prestations ou formations dans le Catalogue avant de pouvoir créer des clients.' }
    case 3:
      return { title: '⚠️ Étape 3 : Aucun client enregistré', desc: 'Veuillez ajouter au moins un client pour pouvoir commencer à réaliser des devis et factures.' }
    default:
      return { title: '🎉 Configuration terminée !', desc: 'Tous vos modules sont déverrouillés.' }
  }
})

const handleModuleClick = async (mod) => {
  await checkOnboardingStatus()

  if (niveauOnboarding.value < mod.minLevel) {
    let msg = 'Accès restreint : '
    if (niveauOnboarding.value === 1) msg += 'Veuillez d’abord configurer votre entreprise dans les paramètres.'
    else if (niveauOnboarding.value === 2) msg += 'Veuillez d’abord ajouter des prestations dans le Catalogue.'
    else msg += 'Veuillez d’abord enregistrer au moins un client.'
    alert(msg)
    return
  }
  currentPage.value = mod.id
}
</script>

<template>
  <!-- CAS 1 : UTILISATEUR NON CONNECTÉ -->
  <div v-if="!session" class="auth-wrapper">
    <div class="auth-card">
      <div class="auth-header">
        <h1>EasyFacture</h1>
        <p>{{ isRegistering ? 'Créer un nouveau compte' : 'Connectez-vous pour accéder à votre espace' }}</p>
      </div>

      <form @submit.prevent="handleAuth" class="auth-form">
        <div class="input-group">
          <label>E-mail</label>
          <input v-model="emailInput" type="email" required class="input-field" />
        </div>
        <div class="input-group">
          <label>Mot de passe</label>
          <input v-model="passwordInput" type="password" required class="input-field" />
        </div>

        <div v-if="authError" class="alert-error">
          {{ authError }}
        </div>

        <div v-if="authSuccess" class="alert-success">
          {{ authSuccess }}
        </div>

        <button type="submit" :disabled="authLoading" class="btn-primary">
          {{ authLoading ? 'Chargement...' : (isRegistering ? "S'inscrire" : 'Se connecter') }}
        </button>

        <div class="auth-switch">
          <button type="button" @click="isRegistering = !isRegistering">
            {{ isRegistering ? 'Déjà un compte ? Connectez-vous' : "Pas encore de compte ? S'inscrire" }}
          </button>
        </div>
      </form>
    </div>
  </div>

  <!-- CAS 2 : UTILISATEUR CONNECTÉ -->
  <div v-else class="app-layout">
    <!-- Header -->
    <header class="app-header">
      <div class="brand-group">
        <button @click="async () => { await checkOnboardingStatus(); currentPage = 'Accueil'; }" class="icon-btn" title="Menu Principal">
          <span class="material-icons">grid_view</span>
        </button>
        <span class="brand-title">EasyFacture</span>
      </div>

      <div class="header-right">
        <span class="version-badge">v1.9.3.2 (Cloud)</span>
        <button @click="handleLogout" class="btn-logout">
          <span class="material-icons text-sm">exit_to_app</span> Déconnexion
        </button>
      </div>
    </header>

    <!-- Contenu Principal -->
    <main class="app-main">
      <!-- VUE ACCUEIL -->
      <div v-if="currentPage === 'Accueil'" class="home-view">
        <div class="welcome-box">
          <h1>Bienvenue sur EasyFacture</h1>
          <p class="onboarding-title" :class="niveauOnboarding === 1 ? 'text-amber' : niveauOnboarding === 2 ? 'text-orange' : niveauOnboarding === 3 ? 'text-teal' : 'text-emerald-600'">
            {{ onboardingMessage.title }}
          </p>
          <p class="onboarding-desc">{{ onboardingMessage.desc }}</p>
        </div>

        <!-- Grille des modules -->
        <div class="dashboard-grid">
          <div 
            v-for="mod in modules" 
            :key="mod.id"
            @click="handleModuleClick(mod)"
            class="tile-card"
            :class="{ 'tile-disabled': niveauOnboarding < mod.minLevel }"
          >
            <span class="material-icons tile-icon" :class="mod.color">{{ mod.icon }}</span>
            <h2 class="tile-title">{{ mod.title }}</h2>
            <p class="tile-desc">{{ mod.desc }}</p>
          </div>
        </div>

        <!-- Simulation Onboarding -->
        <div class="simulation-box">
          <span>Simulation Onboarding (Niveau actuel : {{ niveauOnboarding }}) :</span>
          <button @click="niveauOnboarding = 1" class="sim-btn">Niv 1</button>
          <button @click="niveauOnboarding = 2" class="sim-btn">Niv 2</button>
          <button @click="niveauOnboarding = 3" class="sim-btn">Niv 3</button>
          <button @click="niveauOnboarding = 4" class="sim-btn">Niv 4</button>
        </div>
      </div>

      <!-- VUE SECONDAIRE / MODULES -->
      <div v-else class="module-view">
        <div class="module-nav-bar">
          <button @click="async () => { await checkOnboardingStatus(); currentPage = 'Accueil'; }" class="btn-back">
            <span class="material-icons text-sm">arrow_back</span> Retour
          </button>
        </div>
        
        <!-- Injection dynamique des modules -->
        <InfosEntreprise v-if="currentPage === 'Infos de mon entreprise'" />
        <Catalogue v-else-if="currentPage === 'Catalogue'" />
        <Clients v-else-if="currentPage === 'Clients'" />
        <DevisList v-else-if="currentPage === 'Devis'" />
        
        <!-- Modules par défaut en cours de dev -->
        <div v-else class="construction-card">
          <span class="material-icons text-4xl mb-2 text-slate-300">construction</span>
          <p>Le module <b>{{ currentPage }}</b> est en cours de développement.</p>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.auth-wrapper {
  min-height: 100vh;
  background: #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  font-family: system-ui, -apple-system, sans-serif;
}
.auth-card {
  max-width: 400px;
  width: 100%;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
  padding: 32px;
  box-sizing: border-box;
}
.auth-header h1 { font-size: 24px; font-weight: bold; color: #1e293b; margin: 0 0 8px 0; text-align: center; }
.auth-header p { font-size: 13px; color: #64748b; margin: 0 0 24px 0; text-align: center; }
.auth-form { display: flex; flex-direction: column; gap: 16px; }
.input-group { display: flex; flex-direction: column; gap: 6px; }
.input-group label { font-size: 13px; font-weight: 500; color: #334155; }
.input-field { width: 100%; border: 1px solid #cbd5e1; padding: 10px 12px; border-radius: 8px; font-size: 14px; outline: none; box-sizing: border-box; background: #f8fafc; }
.input-field:focus { background: white; border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1); }
.alert-error { padding: 12px; background: #fef2f2; border: 1px solid #fecaca; color: #dc2626; font-size: 12px; border-radius: 8px; }
.alert-success { padding: 12px; background: #ecfdf5; border: 1px solid #a7f3d0; color: #059669; font-size: 12px; border-radius: 8px; }
.btn-primary { width: 100%; padding: 12px; background: #2563eb; color: white; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; transition: background 0.2s; }
.btn-primary:hover { background: #1d4ed8; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.auth-switch { text-align: center; margin-top: 8px; }
.auth-switch button { background: none; border: none; color: #2563eb; font-size: 12px; cursor: pointer; padding: 0; }
.auth-switch button:hover { text-decoration: underline; }

.app-layout { min-height: 100vh; background: #f8fafc; display: flex; flex-direction: column; font-family: system-ui, -apple-system, sans-serif; color: #1e293b; }
.app-header { background: white; border-bottom: 1px solid #e2e8f0; padding: 12px 24px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
.brand-group { display: flex; align-items: center; gap: 12px; }
.icon-btn { background: none; border: none; padding: 8px; border-radius: 50%; cursor: pointer; color: #2563eb; display: flex; align-items: center; justify-content: center; transition: background 0.2s; }
.icon-btn:hover { background: #f1f5f9; }
.brand-title { font-weight: bold; font-size: 18px; color: #0f172a; }
.header-right { display: flex; align-items: center; gap: 12px; }
.version-badge { padding: 4px 8px; font-size: 11px; font-weight: 600; background: #f1f5f9; color: #475569; border: 1px solid #e2e8f0; border-radius: 6px; }
.btn-logout { display: flex; align-items: center; gap: 4px; background: none; border: none; color: #dc2626; padding: 6px 12px; border-radius: 8px; transition: background 0.2s; font-size: 13px; font-weight: 500; cursor: pointer; }
.btn-logout:hover { background: #fef2f2; }
.app-main { flex: 1; padding: 24px; display: flex; flex-direction: column; align-items: center; box-sizing: border-box; }

.home-view { width: 100%; max-width: 1000px; display: flex; flex-direction: column; align-items: center; gap: 24px; }
.welcome-box { text-align: center; max-width: 600px; }
.welcome-box h1 { font-size: 28px; font-weight: 800; color: #0f172a; margin: 0 0 8px 0; }
.onboarding-title { font-weight: 700; font-size: 14px; margin: 0 0 4px 0; }
.text-amber { color: #d97706; }
.text-orange { color: #ea580c; }
.text-teal { color: #0d9488; }
.onboarding-desc { font-size: 13px; color: #64748b; margin: 0; }

.dashboard-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; width: 100%; }
@media (max-width: 1024px) { .dashboard-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 640px) { .dashboard-grid { grid-template-columns: 1fr; } }

.tile-card { background: white; padding: 24px; border-radius: 12px; border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.05); display: flex; flex-direction: column; align-items: center; text-align: center; gap: 12px; cursor: pointer; transition: all 0.2s ease; box-sizing: border-box; }
.tile-card:hover { transform: translateY(-3px); box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1); border-color: #2563eb; }
.tile-disabled { opacity: 0.5; cursor: not-allowed; }
.tile-disabled:hover { transform: none; box-shadow: 0 1px 3px rgba(0,0,0,0.05); border-color: #e2e8f0; }
.tile-icon { font-size: 36px; }
.tile-title { font-size: 16px; font-weight: bold; color: #0f172a; margin: 0; }
.tile-desc { font-size: 12px; color: #64748b; margin: 0; line-height: 1.4; }

.simulation-box { display: flex; gap: 8px; align-items: center; font-size: 12px; color: #64748b; margin-top: 16px; padding-top: 16px; border-top: 1px solid #e2e8f0; }
.sim-btn { background: #e2e8f0; border: none; padding: 4px 8px; border-radius: 4px; cursor: pointer; font-size: 11px; color: #334155; }
.sim-btn:hover { background: #cbd5e1; }

.module-view { width: 100%; max-width: 1200px; display: flex; flex-direction: column; gap: 20px; }
.module-nav-bar { display: flex; align-items: center; }
.btn-back { display: flex; align-items: center; gap: 4px; background: white; border: 1px solid #e2e8f0; color: #475569; padding: 8px 14px; border-radius: 8px; font-weight: 500; font-size: 13px; cursor: pointer; box-shadow: 0 1px 2px rgba(0,0,0,0.05); transition: background 0.2s; }
.btn-back:hover { background: #f1f5f9; color: #0f172a; }
.construction-card { background: white; padding: 60px 20px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; text-align: center; color: #64748b; }
</style>