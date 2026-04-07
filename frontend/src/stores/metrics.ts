import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

interface CurrentMetrics {
  cpu?: number
  ram_used_gb?: number
  ram_total_gb?: number
  temp_cpu?: number
  uptime_seconds?: number
  array_used_tb?: number
  array_total_tb?: number
  [key: string]: number | undefined
}

export const useMetricsStore = defineStore('metrics', () => {
  const current = ref<CurrentMetrics>({})

  async function fetchCurrent() {
    const resp = await fetch('/api/v1/metrics/current')
    if (resp.ok) current.value = await resp.json()
  }

  function updateCurrent(data: CurrentMetrics) {
    current.value = { ...current.value, ...data }
  }

  const uptimeFormatted = computed(() => {
    const s = current.value.uptime_seconds ?? 0
    const days = Math.floor(s / 86400)
    const hours = Math.floor((s % 86400) / 3600)
    return `${days}j ${hours}h`
  })

  return { current, fetchCurrent, updateCurrent, uptimeFormatted }
})
