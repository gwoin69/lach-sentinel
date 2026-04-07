<template>
  <div>
    <h1 style="font-size:20px;font-weight:700;color:#e6edf3;margin:0 0 24px;">Conteneurs Docker</h1>
    <div v-if="loading" style="color:#6e7681;">Chargement…</div>
    <table v-else class="table">
      <thead><tr><th>Statut</th><th>Nom</th><th>CPU</th><th>Mémoire</th></tr></thead>
      <tbody>
        <tr v-for="c in containers" :key="c.name">
          <td><span class="dot" :class="c.status"></span></td>
          <td>{{ c.name }}</td>
          <td>{{ c.status==='running'?(c.stats?.cpu??0).toFixed(2)+'%':'—' }}</td>
          <td>{{ c.status==='running'&&c.stats?.memory?(c.stats.memory/1024/1024).toFixed(0)+' MB':'—' }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
const containers=ref<any[]>([]);const loading=ref(true)
onMounted(async()=>{const r=await fetch('/api/v1/containers');if(r.ok)containers.value=await r.json();loading.value=false})
</script>
<style scoped>
.table{width:100%;border-collapse:collapse;font-size:13px;}
.table th{text-align:left;padding:10px 12px;color:#6e7681;font-size:11px;text-transform:uppercase;border-bottom:1px solid #21262d;}
.table td{padding:10px 12px;border-bottom:1px solid #161b22;color:#e6edf3;}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;}
.dot.running{background:#42b883;}.dot.stopped,.dot.exited{background:#f85149;}
</style>
