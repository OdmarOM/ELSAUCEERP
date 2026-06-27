// validation.js - Reglas de validación comunes usando Vuelidate
import { required, requiredIf, minValue, maxValue, minLength, maxLength, numeric, decimal, helpers } from '@vuelidate/validators'

// Validador personalizado para placa de vehículo
const placa = (value) => {
  if (!value) return true
  // Acepta formatos: ABC-123-4, ABC1234, 123-ABC-4, etc.
  return /^[A-Z0-9]{3,4}[-]?[A-Z0-9]{3,6}$/i.test(value)
}

// Validador personalizado para folio
const folio = (value) => {
  if (!value) return true
  // Acepta letras, números, guiones
  return /^[A-Z0-9-]+$/i.test(value)
}

// Validador personalizado para teléfono
const telefono = (value) => {
  if (!value) return true
  // Acepta formatos: 1234567890, 123-456-7890, (123) 456-7890
  return /^[\d\-\(\)\s]+$/.test(value) && value.replace(/\D/g,).length >= 10
}

// Validador personalizado para precio positivo
const precioPositivo = (value) => {
  if (!value) return true
  return parseFloat(value) > 0
}

// Validador personalizado para peso positivo
const pesoPositivo = (value) => {
  if (!value) return true
  return parseFloat(value) > 0
}

// Validador personalizado para cantidad de cajas
const cantidadCajas = (value) => {
  if (!value) return true
  const val = parseInt(value)
  return val > 0 && val <= 1000
}

// Validador personalizado para tara
const tara = (value) => {
  if (!value) return true
  const val = parseFloat(value)
  return val >= 0 && val <= 50
}

// Validador personalizado para fecha futura
const fechaFutura = (value) => {
  if (!value) return true
  return new Date(value) > new Date()
}

// Validador personalizado para fecha pasada
const fechaPasada = (value) => {
  if (!value) return true
  return new Date(value) <= new Date()
}

// Validador personalizado para fecha válida
const fechaValida = (value) => {
  if (!value) return true
  const date = new Date(value)
  return !isNaN(date.getTime())
}

// Validador personalizado para nombre (solo letras y espacios)
const nombre = (value) => {
  if (!value) return true
  return /^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$/.test(value)
}

// Validador personalizado para alfanumérico
const alfanumerico = (value) => {
  if (!value) return true
  return /^[a-zA-Z0-9\s]+$/.test(value)
}

// Validador personalizado para porcentaje (0-100)
const porcentaje = (value) => {
  if (!value) return true
  const val = parseFloat(value)
  return val >= 0 && val <= 100
}

// Validador personalizado para entero positivo
const enteroPositivo = (value) => {
  if (!value) return true
  const val = parseInt(value)
  return Number.isInteger(val) && val > 0
}

// Validador personalizado para email
const email = (value) => {
  if (!value) return true
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)
}

// Validador personalizado para URL
const url = (value) => {
  if (!value) return true
  try {
    new URL(value)
    return true
  } catch {
    return false
  }
}

// Mensajes de error personalizados
const withMessage = (validator, message) => {
  return helpers.withMessage(message, validator)
}

// Exportar validadores con mensajes en español
export const validators = {
  required: withMessage(required, 'Este campo es obligatorio'),
  requiredIf: (condition) => withMessage(requiredIf(condition), 'Este campo es obligatorio'),
  minValue: (min) => withMessage(minValue(min), `Debe ser mayor o igual a ${min}`),
  maxValue: (max) => withMessage(maxValue(max), `Debe ser menor o igual a ${max}`),
  minLength: (min) => withMessage(minLength(min), `Debe tener al menos ${min} caracteres`),
  maxLength: (max) => withMessage(maxLength(max), `Debe tener máximo ${max} caracteres`),
  numeric: withMessage(numeric, 'Debe ser un número'),
  decimal: withMessage(decimal, 'Debe ser un número decimal'),
  placa: withMessage(placa, 'Formato de placa inválido'),
  folio: withMessage(folio, 'Solo letras, números y guiones'),
  telefono: withMessage(telefono, 'Número de teléfono inválido'),
  precioPositivo: withMessage(precioPositivo, 'El precio debe ser mayor a 0'),
  pesoPositivo: withMessage(pesoPositivo, 'El peso debe ser mayor a 0'),
  cantidadCajas: withMessage(cantidadCajas, 'Cantidad entre 1 y 1000'),
  tara: withMessage(tara, 'La tara debe estar entre 0 y 50 kg'),
  fechaFutura: withMessage(fechaFutura, 'La fecha debe ser futura'),
  fechaPasada: withMessage(fechaPasada, 'La fecha debe ser pasada o actual'),
  fechaValida: withMessage(fechaValida, 'Fecha inválida'),
  nombre: withMessage(nombre, 'Solo letras y espacios'),
  alfanumerico: withMessage(alfanumerico, 'Solo letras y números'),
  porcentaje: withMessage(porcentaje, 'Debe estar entre 0 y 100'),
  enteroPositivo: withMessage(enteroPositivo, 'Debe ser un entero positivo'),
  email: withMessage(email, 'Email inválido'),
  url: withMessage(url, 'URL inválida')
}

// Esquemas de validación predefinidos
export const validationSchemas = {
  // Validación para viaje
  viaje: {
    tipo_operacion: { required: validators.required },
    acopiador_id: { 
      requiredIf: withMessage(
        requiredIf((val, siblings) => siblings.tipo_operacion === 'ACOPIO'),
        'Selecciona un acopiador'
      )
    },
    cliente_id: { 
      requiredIf: withMessage(
        requiredIf((val, siblings) => siblings.tipo_operacion === 'MAQUILA'),
        'Selecciona un cliente'
      )
    },
    placa: { 
      requiredIf: withMessage(
        requiredIf((val, siblings) => siblings.tipo_operacion === 'ACOPIO'),
        'La placa es obligatoria'
      ),
      placa: validators.placa
    }
  },

  // Validación para pesada
  pesada: {
    tipo_fruta_id: { required: validators.required },
    cantidad_cajas: { 
      required: validators.required,
      cantidadCajas: validators.cantidadCajas
    },
    tara_caja: { 
      required: validators.required,
      tara: validators.tara
    },
    cantidad_tarimas: { 
      required: validators.required,
      enteroPositivo: validators.enteroPositivo,
      maxValue: validators.maxValue(10)
    },
    tara_tarima: { 
      required: validators.required,
      tara: validators.tara
    },
    peso_bruto: { 
      required: validators.required,
      pesoPositivo: validators.pesoPositivo
    }
  },

  // Validación para nota
  nota: {
    fecha: { 
      required: validators.required,
      fechaValida: validators.fechaValida
    },
    folio: { 
      required: validators.required,
      folio: validators.folio,
      minLength: validators.minLength(2),
      maxLength: validators.maxLength(20)
    },
    proveedor_id: { required: validators.required },
    tipo_fruta_id: { required: validators.required },
    cantidad_cajas: { 
      required: validators.required,
      cantidadCajas: validators.cantidadCajas
    },
    tara_tarima: { 
      required: validators.required,
      tara: validators.tara
    },
    tara_caja: { 
      required: validators.required,
      tara: validators.tara
    },
    peso_bruto: { 
      required: validators.required,
      pesoPositivo: validators.pesoPositivo
    },
    precio_kg: { 
      required: validators.required,
      precioPositivo: validators.precioPositivo
    }
  },

  // Validación para pago
  pago: {
    proveedor_id: { required: validators.required },
    folio_pago: { 
      required: validators.required,
      folio: validators.folio
    },
    fecha_pago: { 
      required: validators.required,
      fechaValida: validators.fechaValida
    },
    metodo_pago: { required: validators.required },
    monto_total: { 
      required: validators.required,
      precioPositivo: validators.precioPositivo
    },
    nota_ids: { 
      required: validators.required,
      minLength: validators.minLength(1)
    }
  },

  // Validación para catálogo (acopiador, proveedor, cliente)
  catalogo: {
    nombre: { 
      required: validators.required,
      nombre: validators.nombre,
      minLength: validators.minLength(2),
      maxLength: validators.maxLength(100)
    },
    contacto: { 
      telefono: validators.telefono
    }
  },

  // Validación para tipo de fruta
  tipoFruta: {
    nombre: { 
      required: validators.required,
      nombre: validators.nombre,
      minLength: validators.minLength(2),
      maxLength: validators.maxLength(50)
    },
    descripcion: { 
      maxLength: validators.maxLength(200)
    }
  },

  // Validación para tarima manual
  tarimaManual: {
    tipo_fruta_id: { required: validators.required },
    numero_tarima_display: { 
      required: validators.required,
      folio: validators.folio
    },
    cantidad_cajas: { 
      required: validators.required,
      cantidadCajas: validators.cantidadCajas
    },
    peso_neto: { 
      required: validators.required,
      pesoPositivo: validators.pesoPositivo
    }
  }
}

// Función helper para obtener mensajes de error
export function getValidationErrors(v$) {
  const errors = {}
  
  for (const key in v$) {
    if (key.startsWith('$')) continue
    
    const field = v$[key]
    if (field && field.$errors && field.$errors.length > 0) {
      errors[key] = field.$errors.map(e => e.$message)
    }
  }
  
  return errors
}

// Función helper para verificar si hay errores
export function hasValidationErrors(v$) {
  return v$.$invalid
}

// Función helper para marcar todos los campos como tocados
export function touchAll(v$) {
  v$.$validate()
}
