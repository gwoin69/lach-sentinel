<template>
  <div class="widget">
    <h3>Conteneurs Docker <span class="count">({{ containers.length }})</span></h3>
    <div v-for="c in containers.slice(0,5)" :key="c.name" class="row">
      <span class="dot" :class="c.status"></span>
      <span class="name">{{ c.name }}</span>
      <span class="meta">{{ c.status === 'running' ? fmtMem(c.stats?.memory) : 'Arrêté' }}</span>
    </div>
    <div v-if="containers.length > 5" class="more">
      + {{ containers.length - 5 }} autres · <router-link to="/containers">Voir tout →</router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
const containers = ref<any[]>([])
const fmtMem = (b?: number) => b ? (b/1024/1024).toFixed(0)+' MB' : ''
onMounted(async () => { const r = await fetch('/api/v1/containers'); if (r.ok) containers.value = await r.json() })
</script>

<style scoped>
.widget { background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px; }
h3 { font-size:13px;font-weight:600;color:#e6edf3;margin:0 0 12px; }
.count { font-weight:400;color:#6e7681; }
.row { display:flex;align-items:center;gap:8px;margin-bottom:6px;font-size:13px; }
.dot { width:7px;height:7px;border-radius:50%;flex-shrink:0; }
.dot.running { background:#42b883; } .dot.stopped,.dot.exited { background:#f85149; }
.name { flex:1;color:#e6edf3; }
.meta { color:#6e7681;font-size:11px; }
.more { font-size:11px;color:#6e7681;margin-top:4px; }
.more a { color:#4f8ef7;text-decoration:none; }
</style>
