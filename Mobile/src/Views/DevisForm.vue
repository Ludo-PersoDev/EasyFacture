<template>
  <div class="p-6 max-w-4xl mx-auto bg-white rounded-xl shadow-sm border border-slate-200">
    <h2 class="text-2xl font-bold text-slate-800 mb-6">Créer un Devis</h2>

    <form @submit.prevent="handleSave" class="space-y-4">
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-medium text-slate-700">Client</label>
          <input v-model="form.clientNom" type="text" required class="mt-1 block w-full border border-slate-300 rounded-lg p-2.5" />
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-700">Numéro de Devis</label>
          <input v-model="form.numeroDevis" type="text" readonly class="mt-1 block w-full border border-slate-300 rounded-lg p-2.5 bg-slate-50 text-slate-500 font-mono" />
        </div>
      </div>

      <div>
        <label class="block text-sm font-medium text-slate-700">Prestation / Description</label>
        <textarea v-model="form.description" rows="3" required class="mt-1 block w-full border border-slate-300 rounded-lg p-2.5"></textarea>
      </div>

      <div class="grid grid-cols-3 gap-4">
        <div>
          <label class="block text-sm font-medium text-slate-700">Montant HT (€)</label>
          <input v-model.number="form.montantHt" type="number" step="0.01" @input="calculerTotaux" required class="mt-1 block w-full border border-slate-300 rounded-lg p-2.5" />
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-700">TVA (20%)</label>
          <input v-model.number="form.montantTva" type="number" step="0.01" readonly class="mt-1 block w-full border border-slate-300 rounded-lg p-2.5 bg-slate-50 text-slate-500" />
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-700">Montant TTC (€)</label>
          <input v-model.number="form.montantTtc" type="number" step="0.01" readonly class="mt-1 block w-full border border-slate-300 rounded-lg p-2.5 bg-slate-50 font-bold text-primary" />
        </div>
      </div>

      <div class="flex justify-end space-x-3 pt-4 border-t border-slate-100">
        <button type="submit" :disabled="loading" class="bg-blue-600 text-white font-bold px-5 py-2.5 rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors">
          {{ loading ? 'Génération et Enregistrement...' : 'Enregistrer et Générer le PDF' }}
        </button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { createClient } from '@supabase/supabase-js'
import { generateDevisPdfBlob } from '@/services/pdfGenerator'

// Configuration Supabase (à relier à ton instance globale si tu en as une)
const supabase = createClient('TON_SUPABASE_URL', 'TON_SUPABASE_ANON_KEY')

const loading = ref(false)
const form = ref({
  clientNom: '',
  numeroDevis: 'DEV-2026-001', // À générer dynamiquement via la BDD
  description: '',
  montantHt: 0,
  montantTva: 0,
  montantTtc: 0
})

const calculerTotaux = () => {
  const ht = form.value.montantHt || 0
  const tva = ht * 0.20
  form.value.montantTva = parseFloat(tva.toFixed(2))
  form.value.montantTtc = parseFloat((ht + tva).toFixed(2))
}

const handleSave = async () => {
  loading.value = true
  try {
    // 1. Génération du Blob PDF via le service
    const pdfBlob = await generateDevisPdfBlob(form.value)

    // 2. Nettoyage du nom pour respecter l'arborescence (ex: "Client A" -> "Client_A")
    const cleanClient = form.value.clientNom.replace(/[\\/*?:"<>|]/g, '_').trim()
    const filePath = `${cleanClient}/Devis/Devis_${form.value.numeroDevis}.pdf`

    // 3. Upload dans Supabase Storage
    const { error: uploadError } = await supabase.storage
      .from('documents-comptables')
      .upload(filePath, pdfBlob, { upsert: true })

    if (uploadError) throw uploadError

    // 4. Récupération de l'URL du fichier stocké
    const { data: urlData } = supabase.storage
      .from('documents-comptables')
      .getPublicUrl(filePath)

    // 5. Insertion des métadonnées en base de données
    const { error: dbError } = await supabase
      .from('devis')
      .insert([{
        numero_devis: form.value.numeroDevis,
        client_nom: form.value.clientNom,
        total_ht: form.value.montantHt,
        total_tva: form.value.montantTva,
        total_ttc: form.value.montantTtc,
        pdf_url: urlData.publicUrl,
        statut: 'Brouillon'
      }])

    if (dbError) throw dbError

    alert('Devis créé et archivé dans Supabase avec succès !')
  } catch (err) {
    console.error("Erreur :", err.message)
    alert("Une erreur est survenue lors de la création du devis.")
  } finally {
    loading.value = false
  }
}
</script>