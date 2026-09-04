<script setup>
import { ref, onMounted } from 'vue'
import { supabase } from './supabase'
// Import des composants mobiles allégés
import DashboardMobile from './components/mobile/DashboardMobile.vue'
import DocumentsList from './components/mobile/DocumentsList.vue'
import ClientsCatalogue from './components/mobile/ClientsCatalogue.vue'
import InterventionsMobile from './components/mobile/InterventionsMobile.vue'

const session = ref(null)
const emailInput = ref('')
const passwordInput = ref('')
const authLoading = ref(false)
const authError = ref('')

// Onglet actif pour la navigation basse mobile
const currentTab = ref('dashboard')

onMounted(async () => {
  const { data } = await supabase.auth.getSession()
  session.value = data.session

  supabase.auth.onAuthStateChange((_event, _session) => {
    session.value = _session
  })
})

const handleLogin = async () => {
  authLoading.value = true
  authError.value = ''
  const { error } = await supabase.auth.signInWithPassword({
    email: emailInput.value,
    password: passwordInput.value,
  })
  if (error) authError.value = error.message
  authLoading.value = false
}

const handleLogout = async () => {
  await supabase.auth.signOut()
}
</script>

<template>
  <!-- 1. AUTHENTIFICATION -->
  <div v-if="!session" class="min-h-screen bg-slate-100 flex items-center justify-center p-4">
    <div class="max-w-md w-full bg-white rounded-2xl shadow-sm p-8 border border-slate-200">
      <div class="text-center mb-6">
        <h1 class="text-2xl font-bold text-slate-900">EasyFacture Mobile</h1>
        <p class="text-xs text-slate-500 mt-1">Accès terrain</p>
      </div>

      <form @submit.prevent="handleLogin" class="space-y-4">
        <div>
          <label class="block text-xs font-medium text-slate-700 mb-1">E-mail</label>
          <input v-model="emailInput" type="email" required class="w-full border border-slate-300 p-3 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>
        <div>
          <label class="block text-xs font-medium text-slate-700 mb-1">Mot de passe</label>
          <input v-model="passwordInput" type="password" required class="w-full border border-slate-300 p-3 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 outline-none" />
        </div>

        <div v-if="authError" class="p-3 bg-red-50 border border-red-200 text-red-600 text-xs rounded-xl">
          {{ authError }}
        </div>

        <button type="submit" :disabled="authLoading" class="w-full py-3 bg-blue-600 text-white rounded-xl font-semibold text-sm shadow-md hover:bg-blue-700 transition">
          {{ authLoading ? 'Connexion...' : 'Se connecter' }}
        </button>
      </form>
    </div>
  </div>

  <!-- 2. APPLICATION MOBILE (TERRAIN) -->
  <div v-else class="min-h-screen bg-slate-50 flex flex-col pb-20 font-sans text-slate-800">
    <!-- Header épuré -->
    <header class="bg-white border-b border-slate-200 px-4 py-3 flex justify-between items-center sticky top-0 z-20">
      <div class="font-bold text-base text-slate-900 flex items-center gap-2">
        <span class="material-icons text-blue-600">bolt</span> EasyFacture <span class="text-xs font-normal text-slate-400">Mobile</span>
      </div>
      <button @click="handleLogout" class="text-slate-400 hover:text-red-600 p-1">
        <span class="material-icons text-sm">logout</span>
      </button>
    </header>

    <!-- Corps dynamique selon l'onglet -->
    <main class="flex-1 p-4 max-w-lg mx-auto w-full">
      <DashboardMobile v-if="currentTab === 'dashboard'" />
      <DocumentsList v-else-if="currentTab === 'documents'" />
      <ClientsCatalogue v-else-if="currentTab === 'clients'" />
      <InterventionsMobile v-else-if="currentTab === 'interventions'" />
    </main>

    <!-- Barre de Navigation Basse (Bottom Nav) -->
    <nav class="fixed bottom-0 left-0 right-0 bg-white border-t border-slate-200 py-2 px-6 flex justify-around items-center z-30 shadow-lg">
      <button @click="currentTab = 'dashboard'" :class="currentTab === 'dashboard' ? 'text-blue-600' : 'text-slate-400'" class="flex flex-col items-center gap-1">
        <span class="material-icons text-xl">home</span>
        <span class="text-[10px] font-medium">Accueil</span>
      </button>

      <button @click="currentTab = 'documents'" :class="currentTab === 'documents' ? 'text-blue-600' : 'text-slate-400'" class="flex flex-col items-center gap-1">
        <span class="material-icons text-xl">description</span>
        <span class="text-[10px] font-medium">Documents</span>
      </button>

      <button @click="currentTab = 'interventions'" :class="currentTab === 'interventions' ? 'text-blue-600' : 'text-slate-400'" class="flex flex-col items-center gap-1">
        <span class="material-icons text-xl">event_available</span>
        <span class="text-[10px] font-medium">Prestations</span>
      </button>

      <button @click="currentTab = 'clients'" :class="currentTab === 'clients' ? 'text-blue-600' : 'text-slate-400'" class="flex flex-col items-center gap-1">
        <span class="material-icons text-xl">group</span>
        <span class="text-[10px] font-medium">Annuaire</span>
      </button>
    </nav>
  </div>
</template>