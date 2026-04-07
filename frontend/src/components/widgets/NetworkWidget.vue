<template>
  <div class="widget">
    <div class="header">
      <h3>Réseau local</h3>
      <span class="badge" v-if="lastScan">Scan il y a {{ timeSince(lastScan.finished_at) }}</span>
    </div>
    <div class="stats">
      <div class="stat"><div class="val blue">{{ active }}</div><div class="lbl">Actifs</div></div>
      <div class="stat"><div class="val yellow">{{ newHosts }}</div><div class="lbl">Nouveaux</div></div>
      <div class="stat"><div class="val red">{{ absent }}</div><div class="lbl">Disparus</div></div>
    </div>
    <div class="footer">{{ range }} · <router-link to="/hosts">Voir les hôtes →</router-link></div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useHostsStore } from '../../stores/hosts'
const hosts = useHostsStore()
const lastScan = ref<any>(null)
const range = ref('192.168.111.0/24')
const active = computed(() => hosts.hosts.filter(h => h.status === 'active').length)
const absent = computed(() => hosts.hosts.filter(h => h.status === 'absent').length)
const newHosts = computed(() => hosts.hosts.filter(h => Date.now() - new Date(h.first_seen).getTime() < 86400000).length)
const timeSince = (iso: string) => { const m = Math.floor((Date.now()-new Date(iso).getTime())/60000); return m<60?`${m}min`:`${Math.floor(m/60)}h` }
onMounted(async () => {
  await hosts.fetchHosts()
  const r = await fetch('/api/v1/scans?limit=1'); if (r.ok) { const s = await r.json(); if (s.length) lastScan.value = s[0] }
  const c = await fetch('/api/v1/config'); if (c.ok) { const cfg = await c.json(); if (cfg.nmap_range) range.value = cfg.nmap_range }
})
</script>

<style scoped>
.widget { background:#161b22;border:1px solid #30363d;border-radius:8px;padding:14px; }
.header { display:flex;justify-content:space-between;align-items:center;margin-bottom:12px; }
h3 { font-size:13px;font-weight:600;color:#e6edf3;margin:0; }
.badge { font-size:10px;background:rgba(66,184,131,.15);color:#42b883;border-radius:4px;padding:2px 6px; }
.stats { display:flex;gap:16px;margin-bottom:10px; }
.stat { text-align:center; }
.val { font-size:24px;font-weight:700; }
.lbl { font-size:11px;color:#6e7681; }
.blue{color:#4f8ef7;} .yellow{color:#ffc107;} .red{color:#f85149;}
.footer { font-size:11px;color:#6e7681; }
.footer a { color:#4f8ef7;text-decoration:none; }
</style>
