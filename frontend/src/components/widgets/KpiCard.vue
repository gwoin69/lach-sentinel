<template>
  <div class="kpi-card">
    <div class="label">{{ label }}</div>
    <div class="value">{{ value }}</div>
    <div class="bar" v-if="percent !== undefined">
      <div class="bar-fill" :style="{ width: clamp(percent) + '%', background: color }"></div>
    </div>
    <div class="sub" v-if="sub">{{ sub }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
const props = defineProps<{ label: string; value: string | number; percent?: number; sub?: string; warn?: number; danger?: number }>()
const clamp = (v: number) => Math.min(Math.max(v, 0), 100)
const color = computed(() => {
  if (props.percent === undefined) return '#4f8ef7'
  if (props.danger !== undefined && props.percent >= props.danger) return '#f85149'
  if (props.warn !== undefined && props.percent >= props.warn) return '#ffc107'
  return '#4f8ef7'
})
</script>

<style scoped>
.kpi-card { background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px; }
.label { color:#6e7681;font-size:11px;margin-bottom:4px; }
.value { font-size:22px;font-weight:700;color:#e6edf3; }
.bar { height:4px;background:#21262d;border-radius:2px;margin-top:8px; }
.bar-fill { height:4px;border-radius:2px;transition:width .3s; }
.sub { font-size:11px;color:#6e7681;margin-top:4px; }
</style>
