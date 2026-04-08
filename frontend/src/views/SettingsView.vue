<template>
  <div>
    <h1 style="font-size:20px;font-weight:700;color:#e6edf3;margin:0 0 24px;">Paramètres</h1>
    <div class="section"><h2>Connexion Unraid</h2>
      <div class="fg"><label>IP du serveur</label><input v-model="cfg.UNRAID_HOST" class="inp" /></div>
      <div class="fg"><label>Port API</label><input v-model="cfg.UNRAID_API_PORT" class="inp" type="number" /></div>
      <div class="fg"><label>Clé API</label><input v-model="cfg.UNRAID_API_KEY" class="inp" type="password" placeholder="Laisser vide pour ne pas modifier" /></div>
    </div>
    <div class="section"><h2>Scan réseau</h2>
      <div class="fg"><label>Plage Nmap</label><input v-model="cfg.nmap_range" class="inp" /></div>
      <div class="fg"><label>Intervalle (secondes)</label><input v-model="cfg.nmap_interval" class="inp" type="number" /></div>
    </div>
    <div class="section"><h2>Métriques</h2>
      <div class="fg"><label>Intervalle de collecte (secondes)</label><input v-model="cfg.metrics_interval" class="inp" type="number" /></div>
    </div>
    <button class="btn-pri" @click="save">Enregistrer</button>
    <span v-if="ok" style="margin-left:12px;color:#42b883;font-size:13px;">✓ Enregistré</span>
  </div>
</template>
<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
const cfg = reactive<Record<string,string>>({})
const ok = ref(false)
onMounted(async () => { const r=await fetch('/api/v1/config'); if(r.ok) Object.assign(cfg,await r.json()) })
async function save() {
  await fetch('/api/v1/config',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(cfg)})
  ok.value=true; setTimeout(()=>ok.value=false,2000)
}
</script>
<style scoped>
.section{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:20px;margin-bottom:16px;}
h2{font-size:14px;font-weight:600;color:#e6edf3;margin:0 0 16px;}
.fg{margin-bottom:14px;}
label{display:block;font-size:12px;color:#6e7681;margin-bottom:6px;}
.inp{width:100%;max-width:400px;background:#0d1117;border:1px solid #30363d;border-radius:6px;padding:8px 12px;color:#e6edf3;font-size:14px;}
.btn-pri{background:#4f8ef7;border:none;color:#fff;padding:10px 20px;border-radius:6px;cursor:pointer;font-weight:600;}
</style>
