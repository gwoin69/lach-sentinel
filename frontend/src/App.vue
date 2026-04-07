<template>
  <AppLayout />
</template>

<script setup lang="ts">
import AppLayout from './components/layout/AppLayout.vue'
import { useWsStore } from './stores/ws'
import { onMounted } from 'vue'

const wsStore = useWsStore()
onMounted(() => wsStore.connect())
</script>
