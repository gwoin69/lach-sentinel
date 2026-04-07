<template>
  <div>
    <h1 style="font-size:20px;font-weight:700;color:#e6edf3;margin:0 0 24px;">Réseau local</h1>
    <NetworkWidget style="max-width:500px;" />
    <div style="margin-top:20px;"><router-link to="/hosts" style="color:#4f8ef7;text-decoration:none;">Voir tous les hôtes →</router-link></div>
  </div>
</template>
<script setup lang="ts">
import NetworkWidget from '../components/widgets/NetworkWidget.vue'
</script>
