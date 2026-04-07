import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: Dashboard },
    { path: '/unraid', component: () => import('../views/UnraidView.vue') },
    { path: '/containers', component: () => import('../views/ContainersView.vue') },
    { path: '/vms', component: () => import('../views/VmsView.vue') },
    { path: '/network', component: () => import('../views/NetworkView.vue') },
    { path: '/hosts', component: () => import('../views/HostsView.vue') },
    { path: '/scans', component: () => import('../views/ScansView.vue') },
    { path: '/settings', component: () => import('../views/SettingsView.vue') },
  ]
})
