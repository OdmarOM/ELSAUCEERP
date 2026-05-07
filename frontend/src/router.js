import { createRouter, createWebHistory } from 'vue-router'

// Importaremos las vistas que vamos a crear
import Home from './views/Home.vue'
import ZonaA from './views/ZonaA.vue'
import ZonaB from './views/ZonaB.vue'
import TVFrio from './views/TVFrio.vue'

const routes = [
    { path: '/', component: Home },
    { path: '/bascula', component: ZonaA },
    { path: '/admin', component: ZonaB },
    { path: '/tv', name: 'TVFrio',component: TVFrio}
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

export default router