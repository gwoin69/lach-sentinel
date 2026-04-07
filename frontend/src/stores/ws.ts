import { defineStore } from 'pinia'
import { ref } from 'vue'
import { useMetricsStore } from './metrics'

export const useWsStore = defineStore('ws', () => {
  const connected = ref(false)
  let retryDelay = 1000

  function connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const socket = new WebSocket(`${protocol}://${window.location.host}/ws`)

    socket.onopen = () => { connected.value = true; retryDelay = 1000 }

    socket.onmessage = (event) => {
      const msg = JSON.parse(event.data)
      if (msg.type === 'metrics_update') {
        useMetricsStore().updateCurrent(msg.data)
      }
    }

    socket.onclose = () => {
      connected.value = false
      setTimeout(() => { retryDelay = Math.min(retryDelay * 2, 30000); connect() }, retryDelay)
    }

    socket.onerror = () => socket.close()
  }

  return { connected, connect }
})
