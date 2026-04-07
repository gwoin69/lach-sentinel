<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <div class="logo-icon"></div>
      <div>
        <span class="logo-name">lach-sentinel</span>
        <span class="logo-status" :class="{ online: ws.connected }">
          {{ ws.connected ? '● En ligne' : '○ Déconnecté' }}
        </span>
      </div>
    </div>
    <nav class="sidebar-nav">
      <router-link to="/" class="nav-item">Dashboard</router-link>
      <router-link to="/unraid" class="nav-item">Unraid</router-link>
      <router-link to="/containers" class="nav-item">Conteneurs</router-link>
      <router-link to="/vms" class="nav-item">VMs</router-link>
      <div class="nav-divider"></div>
      <router-link to="/network" class="nav-item">Réseau</router-link>
      <router-link to="/hosts" class="nav-item">Hôtes</router-link>
      <router-link to="/scans" class="nav-item">Scans Nmap</router-link>
      <div class="nav-divider"></div>
      <router-link to="/settings" class="nav-item">Paramètres</router-link>
    </nav>
    <div class="sidebar-footer">192.168.111.253</div>
  </aside>
</template>

<script setup lang="ts">
import { useWsStore } from '../../stores/ws'
const ws = useWsStore()
</script>

<style scoped>
.sidebar { width:200px;background:#010409;border-right:1px solid #21262d;display:flex;flex-direction:column;height:100vh;position:fixed;left:0;top:0; }
.sidebar-header { display:flex;align-items:center;gap:10px;padding:16px 14px;border-bottom:1px solid #21262d; }
.logo-icon { width:28px;height:28px;background:linear-gradient(135deg,#4f8ef7,#7c3aed);border-radius:6px;flex-shrink:0; }
.logo-name { display:block;font-weight:700;color:#fff;font-size:13px; }
.logo-status { display:block;font-size:10px;color:#6e7681; }
.logo-status.online { color:#4f8ef7; }
.sidebar-nav { padding:8px 0;flex:1; }
.nav-item { display:block;padding:8px 14px;color:#8b949e;text-decoration:none;font-size:14px; }
.nav-item:hover { color:#fff; }
.nav-item.router-link-active { color:#4f8ef7;background:rgba(79,142,247,0.1);border-right:2px solid #4f8ef7;font-weight:600; }
.nav-divider { height:1px;background:#21262d;margin:6px 0; }
.sidebar-footer { padding:10px 14px;border-top:1px solid #21262d;color:#6e7681;font-size:11px; }
</style>
