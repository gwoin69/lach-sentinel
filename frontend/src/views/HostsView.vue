<template>
  <div>
    <h1 style="font-size:20px;font-weight:700;color:#e6edf3;margin:0 0 24px;">Hôtes réseau</h1>
    <div v-if="store.loading" style="color:#6e7681;">Chargement…</div>
    <HostTable v-else />
  </div>
</template>
<script setup lang="ts">
import { onMounted } from 'vue'
import HostTable from '../components/hosts/HostTable.vue'
import { useHostsStore } from '../stores/hosts'
const store = useHostsStore()
onMounted(() => store.fetchHosts())
</script>
