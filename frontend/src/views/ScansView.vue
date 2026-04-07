<template>
  <div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;">
      <h1 style="font-size:20px;font-weight:700;color:#e6edf3;">Scans Nmap</h1>
      <button class="btn-pri" @click="trigger" :disabled="running">{{ running ? 'En cours…' : '▶ Lancer un scan' }}</button>
    </div>
    <table class="table">
      <thead><tr><th>Date</th><th>Plage</th><th>Hôtes</th><th>Durée</th><th>Statut</th></tr></thead>
      <tbody>
        <tr v-for="s in scans" :key="s.id">
          <td>{{ fmt(s.started_at) }}</td><td class="mono">{{ s.range }}</td>
          <td>{{ s.hosts_found ?? '—' }}</td><td>{{ dur(s.started_at, s.finished_at) }}</td>
          <td><span class="badge" :class="s.status">{{ s.status }}</span></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
const scans = ref<any[]>([])
const running = ref(false)
const fmt = (iso: string) => new Date(iso).toLocaleString('fr-FR')
const dur = (a: string, b: string|null) => { if(!b)return'—'; const s=Math.floor((new Date(b).getTime()-new Date(a).getTime())/1000); return s<60?`${s}s`:`${Math.floor(s/60)}m${s%60}s` }
async function fetch_() { const r=await fetch('/api/v1/scans?limit=50'); if(r.ok)scans.value=await r.json() }
async function trigger() { running.value=true; await fetch('/api/v1/scans/trigger',{method:'POST'}); setTimeout(async()=>{await fetch_();running.value=false},3000) }
onMounted(fetch_)
</script>
<style scoped>
.btn-pri{background:#4f8ef7;border:none;color:#fff;padding:8px 16px;border-radius:6px;cursor:pointer;font-weight:600;}
.btn-pri:disabled{opacity:.5;cursor:not-allowed;}
.table{width:100%;border-collapse:collapse;font-size:13px;}
.table th{text-align:left;padding:10px 12px;color:#6e7681;font-size:11px;text-transform:uppercase;border-bottom:1px solid #21262d;}
.table td{padding:10px 12px;border-bottom:1px solid #161b22;color:#e6edf3;}
.mono{font-family:monospace;}
.badge{border-radius:4px;padding:2px 8px;font-size:11px;font-weight:600;}
.badge.completed{background:rgba(66,184,131,.15);color:#42b883;}
.badge.running{background:rgba(79,142,247,.15);color:#4f8ef7;}
.badge.failed{background:rgba(248,81,73,.15);color:#f85149;}
</style>
