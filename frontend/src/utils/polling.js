// polling.js - Sistema de polling optimizado con backoff adaptativo
import { ref, onUnmounted } from 'vue'

// Configuración global de polling
const DEFAULT_INTERVAL = 30000 // 30 segundos (reducido de 5s)
const MIN_INTERVAL = 10000 // 10 segundos mínimo
const MAX_INTERVAL = 120000 // 2 minutos máximo
const BACKOFF_MULTIPLIER = 1.5 // Multiplicador para backoff

// Estado global de polling
const pollingState = ref({
  activePollers: new Map(),
  lastUpdate: null,
  isOnline: navigator.onLine
})

// Detectar cambios de conectividad
if (typeof window !== 'undefined') {
  window.addEventListener('online', () => {
    pollingState.value.isOnline = true
    resumeAllPollers()
  })
  
  window.addEventListener('offline', () => {
    pollingState.value.isOnline = false
    pauseAllPollers()
  })
}

// Clase para manejar un poller individual
class Poller {
  constructor(options) {
    this.id = options.id || Date.now().toString()
    this.fetchFn = options.fetchFn
    this.onSuccess = options.onSuccess
    this.onError = options.onError
    this.interval = options.interval || DEFAULT_INTERVAL
    this.minInterval = options.minInterval || MIN_INTERVAL
    this.maxInterval = options.maxInterval || MAX_INTERVAL
    this.immediate = options.immediate !== false
    this.enabled = true
    this.currentInterval = this.interval
    this.failureCount = 0
    this.timer = null
    this.lastFetch = null
  }

  start() {
    if (!this.enabled) return
    
    if (this.immediate) {
      this.fetch()
    }
    
    this.scheduleNext()
  }

  stop() {
    if (this.timer) {
      clearTimeout(this.timer)
      this.timer = null
    }
  }

  pause() {
    this.stop()
  }

  resume() {
    if (this.enabled) {
      this.start()
    }
  }

  scheduleNext() {
    this.stop()
    
    if (!this.enabled || !pollingState.value.isOnline) return
    
    this.timer = setTimeout(() => {
      this.fetch()
    }, this.currentInterval)
  }

  async fetch() {
    if (!this.enabled || !pollingState.value.isOnline) return
    
    try {
      const result = await this.fetchFn()
      this.lastFetch = new Date()
      this.failureCount = 0
      this.currentInterval = this.interval // Reset interval on success
      
      if (this.onSuccess) {
        this.onSuccess(result)
      }
    } catch (error) {
      this.failureCount++
      
      // Backoff exponencial en caso de fallos
      if (this.failureCount > 0) {
        this.currentInterval = Math.min(
          this.currentInterval * BACKOFF_MULTIPLIER,
          this.maxInterval
        )
      }
      
      if (this.onError) {
        this.onError(error)
      }
    }
    
    this.scheduleNext()
  }

  setInterval(newInterval) {
    this.interval = newInterval
    this.currentInterval = newInterval
    this.scheduleNext()
  }

  enable() {
    this.enabled = true
    this.start()
  }

  disable() {
    this.enabled = false
    this.stop()
  }

  destroy() {
    this.stop()
    this.enabled = false
  }
}

// Función para crear un poller
export function usePoller(options) {
  const poller = new Poller(options)
  
  onUnmounted(() => {
    poller.destroy()
  })
  
  return {
    start: () => poller.start(),
    stop: () => poller.stop(),
    pause: () => poller.pause(),
    resume: () => poller.resume(),
    setInterval: (interval) => poller.setInterval(interval),
    enable: () => poller.enable(),
    disable: () => poller.disable(),
    destroy: () => poller.destroy(),
    isRunning: () => poller.timer !== null,
    getLastFetch: () => poller.lastFetch
  }
}

// Función para pausar todos los pollers
function pauseAllPollers() {
  pollingState.value.activePollers.forEach(poller => {
    poller.pause()
  })
}

// Función para reanudar todos los pollers
function resumeAllPollers() {
  pollingState.value.activePollers.forEach(poller => {
    poller.resume()
  })
}

// Función para obtener estadísticas de polling
export function getPollingStats() {
  return {
    activePollers: pollingState.value.activePollers.size,
    isOnline: pollingState.value.isOnline,
    lastUpdate: pollingState.value.lastUpdate
  }
}

// Hook para polling de catálogos (optimizado)
export function useCatalogsPolling(fetchFn, options = {}) {
  const data = ref(null)
  const loading = ref(false)
  const error = ref(null)
  
  const poller = usePoller({
    id: 'catalogs',
    fetchFn: async () => {
      loading.value = true
      error.value = null
      try {
        const result = await fetchFn()
        data.value = result
        return result
      } catch (err) {
        error.value = err
        throw err
      } finally {
        loading.value = false
      }
    },
    interval: options.interval || 30000, // 30 segundos
    immediate: options.immediate !== false,
    onSuccess: (result) => {
      pollingState.value.lastUpdate = new Date()
    },
    onError: (err) => {
      console.error('Catalogs polling error:', err)
    }
  })
  
  return {
    data,
    loading,
    error,
    start: poller.start,
    stop: poller.stop,
    setInterval: poller.setInterval
  }
}

// Hook para polling de inventario en tiempo real (más frecuente)
export function useInventoryPolling(fetchFn, options = {}) {
  const data = ref(null)
  const loading = ref(false)
  const error = ref(null)
  
  const poller = usePoller({
    id: 'inventory',
    fetchFn: async () => {
      loading.value = true
      error.value = null
      try {
        const result = await fetchFn()
        data.value = result
        return result
      } catch (err) {
        error.value = err
        throw err
      } finally {
        loading.value = false
      }
    },
    interval: options.interval || 15000, // 15 segundos (para TV de frío)
    immediate: options.immediate !== false,
    onSuccess: (result) => {
      pollingState.value.lastUpdate = new Date()
    },
    onError: (err) => {
      console.error('Inventory polling error:', err)
    }
  })
  
  return {
    data,
    loading,
    error,
    start: poller.start,
    stop: poller.stop,
    setInterval: poller.setInterval
  }
}

// Hook para polling inteligente (se adapta a la visibilidad de la página)
export function useSmartPolling(fetchFn, options = {}) {
  const data = ref(null)
  const loading = ref(false)
  const error = ref(null)
  const isVisible = ref(true)
  
  const poller = usePoller({
    id: options.id || 'smart',
    fetchFn: async () => {
      if (!isVisible.value) return null // No fetch si no visible
      
      loading.value = true
      error.value = null
      try {
        const result = await fetchFn()
        data.value = result
        return result
      } catch (err) {
        error.value = err
        throw err
      } finally {
        loading.value = false
      }
    },
    interval: options.interval || DEFAULT_INTERVAL,
    immediate: options.immediate !== false,
    onSuccess: (result) => {
      pollingState.value.lastUpdate = new Date()
    },
    onError: (err) => {
      console.error('Smart polling error:', err)
    }
  })
  
  // Detectar visibilidad de la página
  if (typeof document !== 'undefined') {
    const handleVisibilityChange = () => {
      isVisible.value = !document.hidden
      
      if (isVisible.value) {
        poller.resume()
      } else {
        poller.pause()
      }
    }
    
    document.addEventListener('visibilitychange', handleVisibilityChange)
    
    onUnmounted(() => {
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    })
  }
  
  return {
    data,
    loading,
    error,
    isVisible,
    start: poller.start,
    stop: poller.stop,
    setInterval: poller.setInterval
  }
}

// Exportar configuración
export const pollingConfig = {
  DEFAULT_INTERVAL,
  MIN_INTERVAL,
  MAX_INTERVAL,
  BACKOFF_MULTIPLIER
}
