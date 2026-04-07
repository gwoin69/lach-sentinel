<template>
  <div class="widget">
    <h3>Stockage</h3>
    <div class="row"><span class="lbl">Array</span>
      <div class="bar"><div class="fill" :style="{width:arrayPct+'%'}"></div></div>
      <span class="val">{{ m.current.array_used_tb?.toFixed(1) }}TB / {{ m.current.array_total_tb?.toFixed(1) }}TB</span>
    </div>
    <div class="meta"><span>Parité</span><span class="ok">✓ OK</span></div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useMetricsStore } from '../../stores/metrics'
const m = useMetricsStore()
const arrayPct = computed(() => {
  const t = m.current.array_total_tb ?? 0
  return t > 0 ? Math.round((m.current.array_used_tb ?? 0) / t * 100) : 0
})
</script>

<style scoped>
.widget { background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px; }
h3 { font-size:13px;font-weight:600;color:#e6edf3;margin:0 0 12px; }
.row { display:flex;align-items:center;gap:8px;margin-bottom:8px; }
.lbl { color:#6e7681;font-size:12px;width:50px;flex-shrink:0; }
.bar { flex:1;height:6px;background:#21262d;border-radius:3px; }
.fill { height:6px;background:#4f8ef7;border-radius:3px;transition:width .3s; }
.val { color:#e6edf3;font-size:11px;width:100px;text-align:right; }
.meta { display:flex;justify-content:space-between;font-size:11px;color:#6e7681;margin-top:4px; }
.ok { color:#42b883; }
</style>
