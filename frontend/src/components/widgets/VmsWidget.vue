<template>
  <div class="widget">
    <h3>Machines Virtuelles <span class="count">({{ vms.length }})</span></h3>
    <div v-for="vm in vms" :key="vm.name" class="row">
      <span class="dot" :class="vm.status"></span>
      <span class="name">{{ vm.name }}</span>
      <span class="meta">{{ vm.status === 'running' ? `${vm.vcpus} vCPU · ${fmtMem(vm.memory)}` : 'Éteinte' }}</span>
    </div>
    <div v-if="!vms.length" class="empty">Aucune VM</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
const vms = ref<any[]>([])
const fmtMem = (b?: number) => b ? (b/1024/1024/1024).toFixed(0)+' GB' : ''
onMounted(async () => { const r = await fetch('/api/v1/vms'); if (r.ok) vms.value = await r.json() })
</script>

<style scoped>
.widget { background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px; }
h3 { font-size:13px;font-weight:600;color:#e6edf3;margin:0 0 12px; }
.count { font-weight:400;color:#6e7681; }
.row { display:flex;align-items:center;gap:8px;margin-bottom:6px;font-size:13px; }
.dot { width:7px;height:7px;border-radius:50%;flex-shrink:0; }
.dot.running { background:#42b883; } .dot.stopped,.dot.shutoff { background:#6e7681; }
.name { flex:1;color:#e6edf3; }
.meta { color:#6e7681;font-size:11px; }
.empty { color:#6e7681;font-size:13px; }
</style>
