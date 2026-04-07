<template>
  <div>
    <h1 style="font-size:20px;font-weight:700;color:#e6edf3;margin:0 0 24px;">Machines Virtuelles</h1>
    <table class="table">
      <thead><tr><th>Statut</th><th>Nom</th><th>vCPU</th><th>Mémoire</th></tr></thead>
      <tbody>
        <tr v-for="v in vms" :key="v.name">
          <td><span class="dot" :class="v.status"></span></td>
          <td>{{ v.name }}</td><td>{{ v.vcpus??'—' }}</td>
          <td>{{ v.memory?(v.memory/1024/1024/1024).toFixed(0)+' GB':'—' }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
const vms=ref<any[]>([])
onMounted(async()=>{const r=await fetch('/api/v1/vms');if(r.ok)vms.value=await r.json()})
</script>
<style scoped>
.table{width:100%;border-collapse:collapse;font-size:13px;}
.table th{text-align:left;padding:10px 12px;color:#6e7681;font-size:11px;text-transform:uppercase;border-bottom:1px solid #21262d;}
.table td{padding:10px 12px;border-bottom:1px solid #161b22;color:#e6edf3;}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;}
.dot.running{background:#42b883;}.dot.stopped,.dot.shutoff{background:#6e7681;}
</style>
