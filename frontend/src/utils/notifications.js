// notifications.js - Sistema de notificaciones (toasts)
import { createApp, ref, computed } from 'vue'

// Estado global de notificaciones
const notifications = ref([])

// Función para agregar notificación
function addNotification(notification) {
  const id = Date.now() + Math.random()
  const newNotification = {
    id,
    type: 'info', // info, success, warning, error
    title: '',
    message: '',
    duration: 4000, // ms
    ...notification
  }
  
  notifications.value.push(newNotification)
  
  // Auto-eliminar después de la duración
  if (newNotification.duration > 0) {
    setTimeout(() => {
      removeNotification(id)
    }, newNotification.duration)
  }
  
  return id
}

// Función para eliminar notificación
function removeNotification(id) {
  const index = notifications.value.findIndex(n => n.id === id)
  if (index > -1) {
    notifications.value.splice(index, 1)
  }
}

// Funciones de atajo
const toast = {
  success(message, title = 'Éxito') {
    return addNotification({ type: 'success', title, message, duration: 3000 })
  },
  
  error(message, title = 'Error') {
    return addNotification({ type: 'error', title, message, duration: 5000 })
  },
  
  warning(message, title = 'Advertencia') {
    return addNotification({ type: 'warning', title, message, duration: 4000 })
  },
  
  info(message, title = 'Información') {
    return addNotification({ type: 'info', title, message, duration: 3000 })
  },
  
  // Notificación persistente (no se auto-elimina)
  persistent(message, title = 'Aviso') {
    return addNotification({ type: 'info', title, message, duration: 0 })
  }
}

// Componente de notificación
const NotificationComponent = {
  props: ['notification'],
  setup(props) {
    const isVisible = ref(true)
    
    const close = () => {
      isVisible.value = false
      setTimeout(() => {
        removeNotification(props.notification.id)
      }, 300) // Esperar animación
    }
    
    const icon = computed(() => {
      switch (props.notification.type) {
        case 'success': return '✅'
        case 'error': return '❌'
        case 'warning': return '⚠️'
        default: return 'ℹ️'
      }
    })
    
    const bgColor = computed(() => {
      switch (props.notification.type) {
        case 'success': return 'bg-emerald-500'
        case 'error': return 'bg-red-500'
        case 'warning': return 'bg-amber-500'
        default: return 'bg-blue-500'
      }
    })
    
    return { isVisible, close, icon, bgColor }
  },
  template: `
    <transition
      enter-active-class="transform transition-all duration-300"
      enter-from-class="translate-x-full opacity-0"
      enter-to-class="translate-x-0 opacity-100"
      leave-active-class="transform transition-all duration-300"
      leave-from-class="translate-x-0 opacity-100"
      leave-to-class="translate-x-full opacity-0"
    >
      <div v-if="isVisible" class="flex items-start gap-3 p-4 rounded-xl shadow-lg border border-white/20 backdrop-blur-sm" :class="bgColor">
        <span class="text-xl">{{ icon }}</span>
        <div class="flex-1">
          <h4 class="font-bold text-white text-sm">{{ notification.title }}</h4>
          <p class="text-white/90 text-sm mt-1">{{ notification.message }}</p>
        </div>
        <button @click="close" class="text-white/70 hover:text-white transition">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      </div>
    </transition>
  `
}

// Contenedor de notificaciones
const NotificationContainer = {
  setup() {
    return { notifications }
  },
  template: `
    <div class="fixed top-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
      <div v-for="notification in notifications" :key="notification.id" class="pointer-events-auto">
        <NotificationComponent :notification="notification" />
      </div>
    </div>
  `
}

// Función para montar el contenedor de notificaciones
let notificationApp = null

export function mountNotifications() {
  if (notificationApp) return
  
  const container = document.createElement('div')
  document.body.appendChild(container)
  
  notificationApp = createApp({
    components: { NotificationComponent, NotificationContainer },
    template: '<NotificationContainer />'
  })
  
  notificationApp.mount(container)
}

// Auto-montar al importar
if (typeof window !== 'undefined') {
  mountNotifications()
}

export { toast, notifications, addNotification, removeNotification }
