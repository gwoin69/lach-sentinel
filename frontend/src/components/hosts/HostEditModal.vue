<template>
  <div class="overlay" @click.self="$emit('close')">
    <div class="modal">
      <h3>Éditer — {{ host.ip }}</h3>
      <div class="fg"><label>Nom personnalisé</label><input v-model="f.label" class="inp" /></div>
      <div class="fg"><label>Notes</label><textarea v-model="f.notes" class="inp" rows="3"></textarea></div>
      <div class="fg"><label>Tags (virgule)</label><input v-model="tagsRaw" class="inp" /></div>
      <div class="fg row"><label>Monitoring activé</label><input type="checkbox" v-model="f.monitoring_enabled" /></div>
      <div class="actions">
        <button class="btn-sec" @click="$emit('close')">Annuler</button>
        <button class="btn-pri" @click="save">Enregistrer</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useHostsStore } from '../../stores/hosts'
const props = defineProps<{ host: any }>()
const emit = defineEmits(['close'])
const store = useHostsStore()
const f = reactive({ label: props.host.label||'', notes: props.host.notes||'', monitoring_enabled: props.host.monitoring_enabled })
const tagsRaw = ref((props.host.tags||[]).join(', '))
async function save() {
  const tags = tagsRaw.value.split(',').map((t:string)=>t.trim()).filter(Boolean)
  await store.updateHost(props.host.id, { ...f, tags })
  emit('close')
}
</script>

<style scoped>
.overlay { position:fixed;inset:0;background:rgba(0,0,0,.6);display:flex;align-items:center;justify-content:center;z-index:100; }
.modal { background:#161b22;border:1px solid #30363d;border-radius:10px;padding:24px;width:480px;max-width:95vw; }
h3 { margin:0 0 20px;font-size:16px;color:#e6edf3; }
.fg { margin-bottom:16px; }
label { display:block;font-size:12px;color:#6e7681;margin-bottom:6px; }
.inp { width:100%;background:#0d1117;border:1px solid #30363d;border-radius:6px;padding:8px 12px;color:#e6edf3;font-size:14px; }
.row { display:flex;justify-content:space-between;align-items:center; }
.actions { display:flex;gap:10px;justify-content:flex-end;margin-top:20px; }
.btn-sec { background:#21262d;border:1px solid #30363d;color:#8b949e;padding:8px 16px;border-radius:6px;cursor:pointer; }
.btn-pri { background:#4f8ef7;border:none;color:#fff;padding:8px 16px;border-radius:6px;cursor:pointer;font-weight:600; }
</style>
