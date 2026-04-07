<template>
  <div>
    <div class="toolbar">
      <input v-model="q" class="search" placeholder="Rechercher IP, nom, vendor…" />
      <span class="count">{{ filtered.length }} hôtes</span>
    </div>
    <table class="table">
      <thead><tr><th>Statut</th><th>IP</th><th>Nom / Label</th><th>MAC / Vendor</th><th>OS</th><th>Tags</th><th>Vu</th><th>Actions</th></tr></thead>
      <tbody>
        <tr v-for="h in filtered" :key="h.id" :class="{absent: h.status==='absent'}">
          <td><span class="dot" :class="h.status"></span></td>
          <td class="mono">{{ h.ip }}</td>
          <td>{{ h.label || h.hostname || '—' }}</td>
          <td class="small">{{ h.vendor ? `${h.vendor} (${h.mac})` : h.mac || '—' }}</td>
          <td>{{ h.os || '—' }}</td>
          <td><span v-for="t in h.tags" :key="t" class="tag">{{ t }}</span></td>
          <td class="small">{{ rel(h.last_seen) }}</td>
          <td>
            <button class="act" @click="editing=h">Éditer</button>
            <button class="act danger" @click="del(h)">Sup.</button>
          </td>
        </tr>
      </tbody>
    </table>
    <HostEditModal v-if="editing" :host="editing" @close="editing=null" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useHostsStore } from '../../stores/hosts'
import HostEditModal from './HostEditModal.vue'
const store = useHostsStore()
const q = ref('')
const editing = ref<any>(null)
const filtered = computed(() => {
  const s = q.value.toLowerCase()
  return store.hosts.filter(h => h.ip.includes(s)||(h.label||'').toLowerCase().includes(s)||(h.hostname||'').toLowerCase().includes(s)||(h.vendor||'').toLowerCase().includes(s))
})
const rel = (iso: string) => { const m=Math.floor((Date.now()-new Date(iso).getTime())/60000); if(m<1)return'à l\'instant'; if(m<60)return`il y a ${m}min`; if(m<1440)return`il y a ${Math.floor(m/60)}h`; return`il y a ${Math.floor(m/1440)}j` }
async function del(h: any) { if(confirm(`Supprimer ${h.ip} ?`)) await store.deleteHost(h.id) }
</script>

<style scoped>
.toolbar { display:flex;justify-content:space-between;align-items:center;margin-bottom:16px; }
.search { background:#161b22;border:1px solid #30363d;border-radius:6px;padding:8px 12px;color:#e6edf3;font-size:14px;width:300px; }
.count { color:#6e7681;font-size:13px; }
.table { width:100%;border-collapse:collapse;font-size:13px; }
.table th { text-align:left;padding:10px 12px;color:#6e7681;font-size:11px;text-transform:uppercase;border-bottom:1px solid #21262d; }
.table td { padding:10px 12px;border-bottom:1px solid #161b22;color:#e6edf3;vertical-align:middle; }
.table tr:hover td { background:#161b22; }
.table tr.absent td { opacity:.5; }
.dot { display:inline-block;width:8px;height:8px;border-radius:50%; }
.dot.active{background:#42b883;} .dot.absent{background:#f85149;} .dot.returned{background:#ffc107;}
.mono { font-family:monospace; }
.small { font-size:11px;color:#6e7681; }
.tag { background:#21262d;border-radius:4px;padding:2px 6px;font-size:10px;color:#8b949e;margin-right:4px; }
.act { background:#21262d;border:1px solid #30363d;color:#8b949e;padding:4px 8px;border-radius:4px;cursor:pointer;font-size:11px;margin-right:4px; }
.act.danger:hover { color:#f85149;border-color:#f85149; }
</style>
