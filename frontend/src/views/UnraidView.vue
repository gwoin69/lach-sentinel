<template>
  <div>
    <h1 style="font-size:20px;font-weight:700;color:#e6edf3;margin:0 0 24px;">Unraid — Détail système</h1>
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px;">
      <KpiCard label="CPU" :value="(m.current.cpu??0).toFixed(1)+'%'" :percent="m.current.cpu" :warn="70" :danger="90" />
      <KpiCard label="RAM" :value="(m.current.ram_used_gb??0).toFixed(1)+' GB'" :percent="ramPct" :warn="80" :danger="90" />
      <KpiCard label="Temp. CPU" :value="(m.current.temp_cpu??0).toFixed(0)+'°C'" :percent="m.current.temp_cpu" :warn="70" :danger="85" />
      <KpiCard label="Uptime" :value="m.uptimeFormatted" />
    </div>
    <StorageWidget style="max-width:600px;" />
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted } from 'vue'
import KpiCard from '../components/widgets/KpiCard.vue'
import StorageWidget from '../components/widgets/StorageWidget.vue'
import { useMetricsStore } from '../stores/metrics'
const m = useMetricsStore()
const ramPct = computed(()=>{ const t=m.current.ram_total_gb??0; return t>0?Math.round((m.current.ram_used_gb??0)/t*100):0 })
onMounted(()=>m.fetchCurrent())
</script>
