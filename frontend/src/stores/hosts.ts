import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface Host {
  id: number
  ip: string
  hostname: string | null
  mac: string | null
  vendor: string | null
  os: string | null
  status: string
  label: string | null
  notes: string | null
  tags: string[]
  monitoring_enabled: boolean
  first_seen: string
  last_seen: string
}

export const useHostsStore = defineStore('hosts', () => {
  const hosts = ref<Host[]>([])
  const loading = ref(false)

  async function fetchHosts() {
    loading.value = true
    const resp = await fetch('/api/v1/hosts')
    if (resp.ok) hosts.value = await resp.json()
    loading.value = false
  }

  async function updateHost(id: number, updates: Partial<Host>) {
    const resp = await fetch(`/api/v1/hosts/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    })
    if (resp.ok) {
      const updated = await resp.json()
      const idx = hosts.value.findIndex(h => h.id === id)
      if (idx !== -1) hosts.value[idx] = updated
    }
  }

  async function deleteHost(id: number) {
    await fetch(`/api/v1/hosts/${id}`, { method: 'DELETE' })
    hosts.value = hosts.value.filter(h => h.id !== id)
  }

  return { hosts, loading, fetchHosts, updateHost, deleteHost }
})
