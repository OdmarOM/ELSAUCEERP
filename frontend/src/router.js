import { createRouter, createWebHistory } from 'vue-router'

// Importaremos las vistas que vamos a crear
import Home from './views/Home.vue'
import ZonaA from './views/ZonaA.vue'
import ZonaB from './views/ZonaB.vue'
import TVFrio from './views/TVFrio.vue'
import Dashboard from './views/Dashboard.vue'

import CuentasPorCobrar from './views/CuentasPorCobrar.vue'
import CuentasPorPagar from './views/CuentasPorPagar.vue'

const routes = [
    { path: '/', component: Home },
    { path: '/dashboard', component: Dashboard },
    { path: '/bascula', component: ZonaA },
    { path: '/admin', component: ZonaB },
    { path: '/tv', name: 'TVFrio', component: TVFrio },
    { path: '/cuentas-cobrar', component: CuentasPorCobrar },
    { path: '/cuentas-pagar', component: CuentasPorPagar }
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

export default router