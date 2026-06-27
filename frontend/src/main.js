import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router' // <-- Importamos el router
import { mountNotifications } from './utils/notifications.js' // Importar sistema de notificaciones

const app = createApp(App)
app.use(router) // <-- Le decimos a Vue que lo use

// Montar sistema de notificaciones
mountNotifications()

app.mount('#app')