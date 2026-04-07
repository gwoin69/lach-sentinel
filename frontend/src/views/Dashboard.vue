<template>
  <div class="dashboard">
    <div class="dh">
      <h1>Vue d'ensemble</h1>
      <div class="dh-right">
        <span class="upd" v-if="m.current.cpu !== undefined">MàJ en direct</span>
        <button class="btn-sec" @click="show = !show">⚙ Widgets</button>
      </div>
    </div>

    <div class="kpi-grid" v-if="w.kpis">
      <KpiCard label="CPU" :value="(m.current.cpu??0).toFixed(1)+'%'" :percent="m.current.cpu" :warn="70" :danger="90" />
      <KpiCard label="RAM" :value="(m.current.ram_used_gb??0).toFixed(1)+' GB'" :percent="ramPct" :warn="80" :danger="90" />
      <KpiCard label="Temp. CPU" :value="(m.current.temp_cpu??0).toFixed(0)+'°C'" :percent="m.current.temp_cpu" :warn="70" :danger="85" />
      <KpiCard label="Uptime" :value="m.uptimeFormatted" />
    </div>

    <div class="two-col">
      <StorageWidget v-if="w.storage" />
      <ContainersWidget v-if="w.containers" />
    </div>
    <div class="two-col">
      <VmsWidget v-if="w.vms" />
      <NetworkWidget v-if="w.network" />
    </div>

    <div class="panel" v-if="show">
      <h3>Widgets visibles</h3>
      <label v-for="(_, key) in w" :key="key">
        <input type="checkbox" v-model="w[key]" @change="save" /> {{ labels[key] }}
      </label>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted } from 'vue'
import KpiCard from '../components/widgets/KpiCard.vue'
import StorageWidget from '../components/widgets/StorageWidget.vue'
import ContainersWidget from '../components/widgets/ContainersWidget.vue'
import VmsWidget from '../components/widgets/VmsWidget.vue'
import NetworkWidget from '../components/widgets/NetworkWidget.vue'
import { useMetricsStore } from '../stores/metrics'

const m = useMetricsStore()
const show = ref(false)
const labels: Record<string,string> = { kpis:'KPIs système', storage:'Stockage', containers:'Conteneurs', vms:'VMs', network:'Réseau' }
const saved = localStorage.getItem('sentinel-widgets')
const w = reactive<Record<string,boolean>>(saved ? JSON.parse(saved) : { kpis:true, storage:true, containers:true, vms:true, network:true })
const save = () => localStorage.setItem('sentinel-widgets', JSON.stringify(w))
const ramPct = computed(() => { const t = m.current.ram_total_gb??0; return t>0?Math.round((m.current.ram_used_gb??0)/t*100):0 })
onMounted(() => m.fetchCurrent())
</script>

<style scoped>
.dashboard { max-width:1200px; }
.dh { display:flex;justify-content:space-between;align-items:center;margin-bottom:20px; }
h1 { font-size:20px;font-weight:700;color:#e6edf3; }
.dh-right { display:flex;gap:12px;align-items:center; }
.upd { color:#6e7681;font-size:12px; }
.btn-sec { background:#21262d;border:1px solid #30363d;color:#8b949e;padding:6px 12px;border-radius:6px;cursor:pointer;font-size:13px; }
.kpi-grid { display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:12px; }
.two-col { display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px; }
.panel { background:#161b22;border:1px solid #30363d;border-radius:8px;padding:16px;margin-top:12px; }
.panel h3 { margin:0 0 12px;font-size:14px;color:#e6edf3; }
.panel label { display:flex;align-items:center;gap:8px;font-size:13px;color:#8b949e;margin-bottom:8px;cursor:pointer; }
</style>
