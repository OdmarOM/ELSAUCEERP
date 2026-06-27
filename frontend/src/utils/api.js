// api.js - Módulo centralizado para llamadas API con manejo de errores
import { toast } from './notifications.js'

class APIError extends Error {
  constructor(message, status, details = null) {
    super(message)
    this.name = 'APIError'
    this.status = status
    this.details = details
  }
}

// Configuración de reintentos
const MAX_RETRIES = 3
const RETRY_DELAY = 1000 // ms
const RETRYABLE_STATUS_CODES = [408, 429, 500, 502, 503, 504]

// Función de delay con promise
const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms))

// Determinar si un error es reintentable
const isRetryable = (status) => RETRYABLE_STATUS_CODES.includes(status)

// Función fetch con reintentos automáticos
async function fetchWithRetry(url, options = {}, retryCount = 0) {
  try {
    const response = await fetch(url, options)
    
    // Si la respuesta es exitosa, retornar
    if (response.ok) {
      return response
    }
    
    // Si el error es reintentable y no hemos excedido el máximo de reintentos
    if (isRetryable(response.status) && retryCount < MAX_RETRIES) {
      console.warn(`Retry ${retryCount + 1}/${MAX_RETRIES} for ${url} (status: ${response.status})`)
      await delay(RETRY_DELAY * (retryCount + 1)) // Backoff exponencial
      return fetchWithRetry(url, options, retryCount + 1)
    }
    
    // Si no es reintentable o excedimos reintentos, lanzar error
    const errorData = await response.json().catch(() => ({ detail: 'Error desconocido' }))
    throw new APIError(
      errorData.detail || `Error ${response.status}: ${response.statusText}`,
      response.status,
      errorData
    )
  } catch (error) {
    // Si es un error de red y podemos reintentar
    if (error.name === 'TypeError' && retryCount < MAX_RETRIES) {
      console.warn(`Network error, retry ${retryCount + 1}/${MAX_RETRIES} for ${url}`)
      await delay(RETRY_DELAY * (retryCount + 1))
      return fetchWithRetry(url, options, retryCount + 1)
    }
    
    // Si es un APIError, relanzarlo
    if (error instanceof APIError) {
      throw error
    }
    
    // Error de red u otro tipo
    throw new APIError(
      'Error de conexión con el servidor',
      0,
      { originalError: error.message }
    )
  }
}

// Wrapper para GET
export async function get(url) {
  try {
    const response = await fetchWithRetry(url, { method: 'GET' })
    return await response.json()
  } catch (error) {
    handleAPIError(error)
    throw error
  }
}

// Wrapper para POST
export async function post(url, data) {
  try {
    const response = await fetchWithRetry(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    return await response.json()
  } catch (error) {
    handleAPIError(error)
    throw error
  }
}

// Wrapper para PUT
export async function put(url, data) {
  try {
    const response = await fetchWithRetry(url, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    return await response.json()
  } catch (error) {
    handleAPIError(error)
    throw error
  }
}

// Wrapper para DELETE
export async function del(url) {
  try {
    const response = await fetchWithRetry(url, { method: 'DELETE' })
    if (response.status === 204) return null
    return await response.json()
  } catch (error) {
    handleAPIError(error)
    throw error
  }
}

// Manejador centralizado de errores
function handleAPIError(error) {
  if (error.status === 401) {
    toast.error('Sesión expirada. Por favor inicia sesión nuevamente.')
    // Aquí podrías redirigir al login
  } else if (error.status === 403) {
    toast.error('No tienes permisos para realizar esta acción.')
  } else if (error.status === 404) {
    toast.error('El recurso solicitado no existe.')
  } else if (error.status === 409) {
    toast.error(error.details?.detail || 'Conflicto de datos. El registro ya existe.')
  } else if (error.status === 422) {
    toast.error('Datos inválidos. Por favor verifica la información.')
  } else if (error.status === 429) {
    toast.error('Demasiadas solicitudes. Por favor espera un momento.')
  } else if (error.status >= 500) {
    toast.error('Error del servidor. Por favor intenta nuevamente.')
  } else if (error.status === 0) {
    toast.error('Error de conexión. Verifica tu conexión a internet.')
  } else {
    toast.error(error.message || 'Ocurrió un error inesperado.')
  }
  
  // Log del error para debugging
  console.error('API Error:', error)
}

export { APIError }
