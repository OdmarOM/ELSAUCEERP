<!-- Dashboard.vue - Dashboard con métricas y reportes -->
<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { get } from '../utils/api.js'
import { useCatalogsPolling } from '../utils/polling.js'
import { format } from 'date-fns'
import { es } from 'date-fns/locale'
import { Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  Title,
  Tooltip,
  Legend,
  BarElement,
  CategoryScale,
  LinearScale
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

const API_URL = '/api'

// Datos
const acopiadores = ref([])
const proveedores = ref([])
const clientes = ref([])
const tiposFruta = ref([])
const viajes = ref([])
const notas = ref([])
const registrosBascula = ref([])
const registrosSalida = ref([])
const pagos = ref([])
const inventarioFrio = ref([])
const ubicacionesFrio = ref([])
const cobrosTotales = ref([])
const cuentasPorCobrar = ref([])
const mermasTarimas = ref([])

// Filtros
const fechaInicio = ref(new Date(new Date().setDate(new Date().getDate() - 30)).toISOString().split('T')[0])
const fechaFin = ref(new Date().toISOString().split('T')[0])
const periodoSeleccionado = ref('mes') // semana, mes, trimestre, año
const modoVista = ref('periodo') // 'periodo' o 'dia'
const fechaDiaEspecifico = ref(new Date().toISOString().split('T')[0])

// Polling
const { data: catalogsData, loading, start: startPolling } = useCatalogsPolling(fetchCatalogos, {
  interval: 30000,
  immediate: true
})

onMounted(() => {
  startPolling()
})

async function fetchCatalogos() {
  try {
    const promises = [
      get(`${API_URL}/acopiadores`),
      get(`${API_URL}/proveedores`),
      get(`${API_URL}/clientes`),
      get(`${API_URL}/tipos-fruta`),
      get(`${API_URL}/viajes`),
      get(`${API_URL}/notas`),
      get(`${API_URL}/registros-bascula`),
      get(`${API_URL}/registros-bascula-salida`),
      get(`${API_URL}/pagos`),
      get(`${API_URL}/inventario-frio`),
      get(`${API_URL}/cuarto-frio`),
      get(`${API_URL}/finanzas/cobrar`),
      get(`${API_URL}/finanzas/cobros`),
      get(`${API_URL}/reportes/mermas-tarimas`)
    ]
    
    const results = await Promise.allSettled(promises)
    
    // Función auxiliar para extraer el valor o [] si falló
    const getValue = (index) => results[index].status === 'fulfilled' ? results[index].value : []
    
    acopiadores.value = getValue(0)
    proveedores.value = getValue(1)
    clientes.value = getValue(2)
    tiposFruta.value = getValue(3)
    viajes.value = getValue(4)
    notas.value = getValue(5)
    registrosBascula.value = getValue(6)
    registrosSalida.value = getValue(7)
    pagos.value = getValue(8)
    inventarioFrio.value = getValue(9)
    ubicacionesFrio.value = getValue(10)
    cuentasPorCobrar.value = getValue(11)
    cobrosTotales.value = getValue(12)
    mermasTarimas.value = results[13]?.status === 'fulfilled' ? results[13].value : []
    
    // Log failures
    results.forEach((r, i) => {
      if (r.status === 'rejected') {
        console.error(`Error fetching catalog index ${i}:`, r.reason)
      }
    })
  } catch (error) {
    console.error('Error in fetchCatalogos:', error)
  }
}

// Métricas Acopio (Entradas)
const metricasAcopio = computed(() => {
  const viajesEntrada = viajes.value.filter(v => {
    if (v.tipo !== 'ENTRADA') return false
    if (!v.fecha_entrada) return false
    const fecha = v.fecha_entrada.substring(0, 10)
    return fecha >= fechaInicio.value && fecha <= fechaFin.value
  })
  
  const pesoTotalFisico = viajesEntrada.reduce((sum, v) => {
    const tarimas = registrosBascula.value.filter(r => r.viaje_id === v.id)
    return sum + tarimas.reduce((s, t) => s + parseFloat(t.peso_neto || 0), 0)
  }, 0)
  
  const pesoTotalTeorico = viajesEntrada.reduce((sum, v) => 
    sum + parseFloat(v.peso_total_teorico || 0), 0
  )
  
  const totalPagado = pagos.value.filter(p => {
    if (!p.fecha_pago) return false
    const fecha = p.fecha_pago.substring(0, 10)
    return fecha >= fechaInicio.value && fecha <= fechaFin.value
  }).reduce((sum, p) => sum + parseFloat(p.monto_total || p.monto || 0), 0)
  
  const deudaPendiente = notas.value.filter(n => n.estado_pago === 'PENDIENTE')
    .reduce((sum, n) => sum + parseFloat(n.total_monetario || 0), 0)
  
  return {
    viajesCount: viajesEntrada.length,
    pesoTotalFisico: pesoTotalFisico.toFixed(2),
    pesoTotalTeorico: pesoTotalTeorico.toFixed(2),
    diferencia: (pesoTotalFisico - pesoTotalTeorico).toFixed(2),
    totalPagado: totalPagado.toFixed(2),
    deudaPendiente: deudaPendiente.toFixed(2)
  }
})

// Métricas Ventas (Salidas)
const metricasVentas = computed(() => {
  const viajesSalida = viajes.value.filter(v => {
    if (v.tipo !== 'SALIDA') return false
    if (!v.fecha_entrada) return false
    const fecha = v.fecha_entrada.substring(0, 10)
    return fecha >= fechaInicio.value && fecha <= fechaFin.value
  })
  
  const pesoTotalEnviado = viajesSalida.reduce((sum, v) => {
    const tarimas = registrosSalida.value.filter(r => r.viaje_id === v.id)
    return sum + tarimas.reduce((s, t) => s + parseFloat(t.peso_salida || t.peso_neto || 0), 0)
  }, 0)
  
  const cuentasDelPeriodo = cuentasPorCobrar.value.filter(c => {
    if (!c.fecha_emision) return false
    const fecha = c.fecha_emision.substring(0, 10)
    return fecha >= fechaInicio.value && fecha <= fechaFin.value
  })
  
  const totalVendido = cuentasDelPeriodo.reduce((sum, c) => sum + parseFloat(c.monto_total || 0), 0)
  const cuentasPorCobrarPendientes = cuentasDelPeriodo
    .reduce((sum, c) => sum + Math.max(0, parseFloat(c.saldo_pendiente || 0)), 0)
  const totalCobrado = totalVendido - cuentasPorCobrarPendientes
  
  return {
    viajesCount: viajesSalida.length,
    pesoTotalEnviado: pesoTotalEnviado.toFixed(2),
    totalCobrado: totalCobrado.toFixed(2),
    cuentasPorCobrar: cuentasPorCobrarPendientes.toFixed(2)
  }
})

// Inventario Físico
const metricasInventario = computed(() => {
  const ocupacionFrio = ubicacionesFrio.value.filter(u => u.inventario_frio_id).length
  const tarimasEnBodega = inventarioFrio.value.filter(i => i.activo === 1 && 
    !ubicacionesFrio.value.some(u => u.inventario_frio_id === i.id)
  ).length
  
  return {
    ocupacionFrio: ocupacionFrio,
    capacidadFrio: 50,
    tarimasEnBodega: tarimasEnBodega
  }
})

// Producción por día
// Producción por día (dividida)
const produccionPorDia = computed(() => {
  const dias = {}
  
  viajes.value.forEach(v => {
    if (!v.fecha_entrada) return
    
    const fecha = v.fecha_entrada.substring(0, 10)
    if (!dias[fecha]) {
      dias[fecha] = { fecha, pesoEntrada: 0, pesoSalida: 0 }
    }
    
    if (v.tipo === 'ENTRADA') {
      const tarimas = registrosBascula.value.filter(r => r.viaje_id === v.id)
      const peso = tarimas.reduce((s, t) => s + parseFloat(t.peso_neto || 0), 0)
      dias[fecha].pesoEntrada += peso
    } else {
      const tarimas = registrosSalida.value.filter(r => r.viaje_id === v.id)
      const peso = tarimas.reduce((s, t) => s + parseFloat(t.peso_salida || t.peso_neto || 0), 0)
      dias[fecha].pesoSalida += peso
    }
  })
  
  return Object.values(dias)
    .sort((a, b) => new Date(b.fecha) - new Date(a.fecha))
    .slice(0, 14) // Últimos 14 días
})

// Finanzas por día (Ingresos vs Egresos)
const finanzasPorDia = computed(() => {
  const dias = {}
  
  pagos.value.forEach(p => {
    if (!p.fecha_pago) return
    const fecha = p.fecha_pago.substring(0, 10)
    if (!dias[fecha]) dias[fecha] = { fecha, ingresos: 0, egresos: 0 }
    dias[fecha].egresos += parseFloat(p.monto_total || p.monto || 0)
  })
  
  cobrosTotales.value.forEach(c => {
    if (!c.fecha_cobro) return
    const fecha = c.fecha_cobro.substring(0, 10)
    if (!dias[fecha]) dias[fecha] = { fecha, ingresos: 0, egresos: 0 }
    dias[fecha].ingresos += parseFloat(c.monto_cobrado || 0)
  })
  
  return Object.values(dias)
    .sort((a, b) => new Date(b.fecha) - new Date(a.fecha))
    .slice(0, 14) // Últimos 14 días
})

// Datos para la gráfica de Volumen
const chartDataVolumen = computed(() => {
  const reversed = [...produccionPorDia.value].reverse()
  return {
    labels: reversed.map(d => formatearFecha(d.fecha)),
    datasets: [
      {
        label: 'Acopio (kg)',
        backgroundColor: '#3b82f6',
        data: reversed.map(d => d.pesoEntrada)
      },
      {
        label: 'Ventas (kg)',
        backgroundColor: '#10b981',
        data: reversed.map(d => d.pesoSalida)
      }
    ]
  }
})

const chartOptionsVolumen = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'bottom' },
    tooltip: {
      callbacks: {
        label: (context) => `${context.dataset.label}: ${context.parsed.y.toFixed(2)} kg`
      }
    }
  }
}

// Datos para la gráfica de Finanzas
const chartDataFinanzas = computed(() => {
  const reversed = [...finanzasPorDia.value].reverse()
  return {
    labels: reversed.map(d => formatearFecha(d.fecha)),
    datasets: [
      {
        label: 'Ingresos',
        backgroundColor: '#f97316',
        data: reversed.map(d => d.ingresos)
      },
      {
        label: 'Egresos',
        backgroundColor: '#3b82f6',
        data: reversed.map(d => d.egresos)
      }
    ]
  }
})

const chartOptionsFinanzas = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'bottom' },
    tooltip: {
      callbacks: {
        label: (context) => {
          const value = context.parsed.y
          return `${context.dataset.label}: ${new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' }).format(value)}`
        }
      }
    }
  }
}

// Producción por tipo de fruta
const produccionPorFruta = computed(() => {
  const frutas = {}
  
  registrosBascula.value.forEach(r => {
    const frutaId = r.tipo_fruta_id
    if (!frutas[frutaId]) {
      const fruta = tiposFruta.value.find(f => f.id === frutaId)
      frutas[frutaId] = {
        id: frutaId,
        nombre: fruta?.nombre || 'Desconocido',
        peso: 0,
        tarimas: 0
      }
    }
    
    frutas[frutaId].peso += parseFloat(r.peso_neto || 0)
    frutas[frutaId].tarimas += 1
  })
  
  registrosSalida.value.forEach(r => {
    const frutaId = r.tipo_fruta_id
    if (!frutas[frutaId]) {
      const fruta = tiposFruta.value.find(f => f.id === frutaId)
      frutas[frutaId] = {
        id: frutaId,
        nombre: fruta?.nombre || 'Desconocido',
        peso: 0,
        tarimas: 0
      }
    }
    
    frutas[frutaId].peso += parseFloat(r.peso_salida || r.peso_neto || 0)
    frutas[frutaId].tarimas += 1
  })
  
  return Object.values(frutas).sort((a, b) => b.peso - a.peso)
})

// Top 5 acopiadores
const topAcopiadores = computed(() => {
  const acopiadoresData = {}
  
  viajes.value.filter(v => v.tipo_operacion === 'ACOPIO').forEach(v => {
    const acopId = v.acopiador_id
    if (!acopiadoresData[acopId]) {
      const acop = acopiadores.value.find(a => a.id === acopId)
      acopiadoresData[acopId] = {
        id: acopId,
        nombre: acop?.nombre || 'Desconocido',
        peso: 0,
        viajes: 0
      }
    }
    
    const tarimas = registrosBascula.value.filter(r => r.viaje_id === v.id)
    const peso = tarimas.reduce((s, t) => s + parseFloat(t.peso_neto || 0), 0)
    
    acopiadoresData[acopId].peso += peso
    acopiadoresData[acopId].viajes += 1
  })
  
  return Object.values(acopiadoresData)
    .sort((a, b) => b.peso - a.peso)
    .slice(0, 5)
})

// Pagos por proveedor
const pagosPorProveedor = computed(() => {
  const proveedoresData = {}
  
  pagos.value.forEach(p => {
    const provId = p.proveedor_id
    if (!proveedoresData[provId]) {
      const prov = proveedores.value.find(pr => pr.id === provId)
      proveedoresData[provId] = {
        id: provId,
        nombre: prov?.nombre || 'Desconocido',
        total: 0,
        pagos: 0
      }
    }
    
    proveedoresData[provId].total += parseFloat(p.monto_total || 0)
    proveedoresData[provId].pagos += 1
  })
  
  return Object.values(proveedoresData)
    .sort((a, b) => b.total - a.total)
    .slice(0, 5)
})

// Viajes por estado
const viajesPorEstado = computed(() => {
  const estados = {
    ACTIVO: 0,
    CERRADO: 0,
    CONCILIADO: 0
  }
  
  viajes.value.forEach(v => {
    if (estados[v.estado] !== undefined) {
      estados[v.estado]++
    }
  })
  
  return estados
})

// Cambiar periodo
const cambiarPeriodo = (periodo) => {
  periodoSeleccionado.value = periodo
  modoVista.value = 'periodo'
  
  const hoy = new Date()
  let inicio
  
  switch (periodo) {
    case 'semana':
      const diaSemana = hoy.getDay() // 0 = Domingo, 1 = Lunes, etc.
      const diffLunes = diaSemana === 0 ? -6 : 1 - diaSemana
      const lunes = new Date(hoy)
      lunes.setDate(hoy.getDate() + diffLunes)
      
      const sabado = new Date(lunes)
      sabado.setDate(lunes.getDate() + 5)
      
      fechaInicio.value = lunes.toISOString().split('T')[0]
      fechaFin.value = sabado.toISOString().split('T')[0]
      return
    case 'mes':
      inicio = new Date(hoy.setDate(hoy.getDate() - 30))
      break
    case 'trimestre':
      inicio = new Date(hoy.setDate(hoy.getDate() - 90))
      break
    case 'año':
      inicio = new Date(hoy.setFullYear(hoy.getFullYear() - 1))
      break
  }
  
  fechaInicio.value = inicio.toISOString().split('T')[0]
  fechaFin.value = new Date().toISOString().split('T')[0]
}

const aplicarDiaEspecifico = () => {
  modoVista.value = 'dia'
  fechaInicio.value = fechaDiaEspecifico.value
  fechaFin.value = fechaDiaEspecifico.value
}

// Formatear fecha
const formatearFecha = (fecha) => {
  if (!fecha) return ''
  try {
    const d = new Date(fecha)
    if (isNaN(d.getTime())) return String(fecha)
    return format(d, 'dd/MM/yyyy', { locale: es })
  } catch (e) {
    return String(fecha)
  }
}

// Formatear moneda
const formatearMoneda = (valor) => {
  try {
    const num = parseFloat(valor || 0)
    if (isNaN(num)) return '$0.00'
    return new Intl.NumberFormat('es-MX', {
      style: 'currency',
      currency: 'MXN'
    }).format(num)
  } catch (e) {
    return '$0.00'
  }
}

// Formatear peso
const formatearPeso = (valor) => {
  try {
    const num = parseFloat(valor || 0)
    if (isNaN(num)) return '0.00 kg'
    return num.toFixed(2) + ' kg'
  } catch (e) {
    return '0.00 kg'
  }
}
</script>

<template>
  <div class="min-h-screen bg-gray-50 p-6 md:p-8">
    <!-- Header -->
    <div class="flex justify-between items-center mb-8">
      <div>
        <h1 class="text-3xl font-light text-gray-800 tracking-tight">Dashboard</h1>
        <p class="text-gray-500 text-sm mt-1">Métricas y reportes en tiempo real</p>
      </div>
      
      <!-- Selector de periodo -->
      <div class="flex gap-3 flex-wrap items-center">
        <div class="flex gap-2">
          <button 
            v-for="periodo in ['semana', 'mes', 'trimestre', 'año']"
            :key="periodo"
            @click="cambiarPeriodo(periodo)"
            :class="modoVista === 'periodo' && periodoSeleccionado === periodo ? 'bg-emerald-500 text-white' : 'bg-white text-gray-600'"
            class="px-4 py-2 rounded-xl text-sm font-medium shadow-sm border transition"
          >
            {{ periodo.charAt(0).toUpperCase() + periodo.slice(1) }}
          </button>
        </div>
        
        <div class="flex gap-2 items-center">
          <button 
            @click="aplicarDiaEspecifico"
            :class="modoVista === 'dia' ? 'bg-emerald-500 text-white' : 'bg-white text-gray-600'"
            class="px-4 py-2 rounded-xl text-sm font-medium shadow-sm border transition"
          >
            📅 Día Específico
          </button>
          
          <input 
            v-if="modoVista === 'dia'"
            type="date"
            v-model="fechaDiaEspecifico"
            @change="aplicarDiaEspecifico"
            class="border rounded-xl px-4 py-2 text-sm font-bold text-gray-700 outline-none focus:ring-2 focus:ring-emerald-500 shadow-sm"
          />
        </div>
      </div>
    </div>

    <!-- Operación de Acopio (Entradas) -->
    <h2 class="text-xl font-bold text-gray-800 mb-4 mt-8">📥 Operación de Acopio (Entradas)</h2>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-l-4 border-l-blue-500">
        <div class="flex items-center justify-between mb-4">
          <span class="text-gray-500 text-sm font-medium">Viajes Recibidos</span>
          <span class="text-2xl">🚚</span>
        </div>
        <div class="text-3xl font-black text-gray-800">{{ metricasAcopio.viajesCount }}</div>
        <div class="text-xs text-gray-400 mt-2">Desde {{ formatearFecha(fechaInicio) }}</div>
      </div>
      
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-l-4 border-l-blue-500">
        <div class="flex items-center justify-between mb-4">
          <span class="text-gray-500 text-sm font-medium">Peso Total Acopiado</span>
          <span class="text-2xl">⚖️</span>
        </div>
        <div class="text-3xl font-black text-blue-600">{{ formatearPeso(metricasAcopio.pesoTotalFisico) }}</div>
        <div class="text-xs text-gray-400 mt-2">Peso neto de báscula</div>
      </div>
      
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-l-4 border-l-blue-500">
        <div class="flex items-center justify-between mb-4">
          <span class="text-gray-500 text-sm font-medium">Total Pagado a Prov.</span>
          <span class="text-2xl">💰</span>
        </div>
        <div class="text-3xl font-black text-emerald-600">{{ formatearMoneda(metricasAcopio.totalPagado) }}</div>
        <div class="text-xs text-gray-400 mt-2">Compras pagadas</div>
      </div>
      
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-l-4 border-l-blue-500">
        <div class="flex items-center justify-between mb-4">
          <span class="text-gray-500 text-sm font-medium">Cuentas por Pagar</span>
          <span class="text-2xl">📉</span>
        </div>
        <div class="text-3xl font-black text-orange-600">{{ formatearMoneda(metricasAcopio.deudaPendiente) }}</div>
        <div class="text-xs text-gray-400 mt-2">Deuda a proveedores</div>
      </div>
    </div>

    <!-- Operación de Ventas (Salidas) -->
    <h2 class="text-xl font-bold text-gray-800 mb-4 mt-8">📤 Operación de Ventas (Salidas)</h2>
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-l-4 border-l-emerald-500">
        <div class="flex items-center justify-between mb-4">
          <span class="text-gray-500 text-sm font-medium">Viajes Enviados</span>
          <span class="text-2xl">🚛</span>
        </div>
        <div class="text-3xl font-black text-gray-800">{{ metricasVentas.viajesCount }}</div>
        <div class="text-xs text-gray-400 mt-2">Desde {{ formatearFecha(fechaInicio) }}</div>
      </div>
      
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-l-4 border-l-emerald-500">
        <div class="flex items-center justify-between mb-4">
          <span class="text-gray-500 text-sm font-medium">Peso Total Enviado</span>
          <span class="text-2xl">📦</span>
        </div>
        <div class="text-3xl font-black text-emerald-600">{{ formatearPeso(metricasVentas.pesoTotalEnviado) }}</div>
        <div class="text-xs text-gray-400 mt-2">Kilos facturados</div>
      </div>
      
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-l-4 border-l-emerald-500">
        <div class="flex items-center justify-between mb-4">
          <span class="text-gray-500 text-sm font-medium">Total Cobrado</span>
          <span class="text-2xl">💳</span>
        </div>
        <div class="text-3xl font-black text-blue-600">{{ formatearMoneda(metricasVentas.totalCobrado) }}</div>
        <div class="text-xs text-gray-400 mt-2">Ventas pagadas</div>
      </div>
      
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-l-4 border-l-emerald-500">
        <div class="flex items-center justify-between mb-4">
          <span class="text-gray-500 text-sm font-medium">Cuentas por Cobrar</span>
          <span class="text-2xl">📈</span>
        </div>
        <div class="text-3xl font-black text-orange-600">{{ formatearMoneda(metricasVentas.cuentasPorCobrar) }}</div>
        <div class="text-xs text-gray-400 mt-2">Deuda de clientes</div>
      </div>
    </div>

    <!-- Inventario Físico -->
    <h2 class="text-xl font-bold text-gray-800 mb-4 mt-8">❄️ Inventario y Conciliación</h2>
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
      <div class="bg-white p-6 rounded-2xl shadow-sm border">
        <div class="flex items-center justify-between mb-4">
          <span class="text-gray-500 text-sm font-medium">Ocupación Cuarto Frío</span>
          <span class="text-2xl">❄️</span>
        </div>
        <div class="flex items-end gap-2">
          <div class="text-3xl font-black text-blue-600">{{ metricasInventario.ocupacionFrio }}</div>
          <div class="text-lg text-gray-400 mb-1">/ {{ metricasInventario.capacidadFrio }}</div>
        </div>
        <div class="w-full bg-gray-200 rounded-full h-2 mt-3">
          <div 
            class="bg-blue-500 h-2 rounded-full transition-all"
            :style="{ width: (metricasInventario.ocupacionFrio / metricasInventario.capacidadFrio * 100) + '%' }"
          ></div>
        </div>
        <div class="text-xs text-gray-400 mt-2">{{ ((metricasInventario.ocupacionFrio / metricasInventario.capacidadFrio) * 100).toFixed(1) }}% ocupado</div>
      </div>
      
      <div class="bg-white p-6 rounded-2xl shadow-sm border">
        <div class="flex items-center justify-between mb-4">
          <span class="text-gray-500 text-sm font-medium">Tarimas en Bodega</span>
          <span class="text-2xl">🧱</span>
        </div>
        <div class="text-3xl font-black text-orange-600">{{ metricasInventario.tarimasEnBodega }}</div>
        <div class="text-xs text-gray-400 mt-2">Sin ubicación en frío</div>
      </div>
      
      <div class="bg-white p-6 rounded-2xl shadow-sm border">
        <div class="flex items-center justify-between mb-4">
          <span class="text-gray-500 text-sm font-medium">Diferencia Acopio (Fís. vs Teór.)</span>
          <span class="text-2xl">📉</span>
        </div>
        <div 
          class="text-3xl font-black"
          :class="parseFloat(metricasAcopio.diferencia) >= 0 ? 'text-emerald-600' : 'text-red-600'"
        >
          {{ parseFloat(metricasAcopio.diferencia) >= 0 ? '+' : '' }}{{ formatearPeso(metricasAcopio.diferencia) }}
        </div>
        <div class="text-xs text-gray-400 mt-2">Conciliación de pesos de entrada</div>
      </div>
    </div>

    <!-- Gráficos y tablas -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
      <!-- Volumen por día -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border">
        <h3 class="text-lg font-bold text-gray-800 mb-4">Volumen por Día (Últimos 14 días)</h3>
        <div class="h-80 w-full">
          <Bar v-if="produccionPorDia.length > 0" :data="chartDataVolumen" :options="chartOptionsVolumen" />
          <div v-else class="text-gray-400 text-sm italic h-full flex items-center justify-center">
            No hay registros de volumen en los últimos días.
          </div>
        </div>
      </div>
      
      <!-- Finanzas por día -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border">
        <h3 class="text-lg font-bold text-gray-800 mb-4">Flujo Financiero por Día (Ingresos vs Egresos)</h3>
        <div class="h-80 w-full">
          <Bar v-if="finanzasPorDia.length > 0" :data="chartDataFinanzas" :options="chartOptionsFinanzas" />
          <div v-else class="text-gray-400 text-sm italic h-full flex items-center justify-center">
            No hay pagos ni cobros registrados en los últimos días.
          </div>
        </div>
      </div>
    </div>

    <!-- Cuarta fila -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
      <!-- Volumen por tipo de fruta -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border">
        <h3 class="text-lg font-bold text-gray-800 mb-4">Volumen por Tipo de Fruta</h3>
        <div class="space-y-3 max-h-80 overflow-y-auto">
          <div 
            v-for="fruta in produccionPorFruta" 
            :key="fruta.id"
            class="flex items-center gap-4"
          >
            <div class="w-32 text-sm text-gray-600 truncate">{{ fruta.nombre }}</div>
            <div class="flex-1 bg-gray-100 rounded-full h-6 overflow-hidden">
              <div 
                class="bg-blue-500 h-full rounded-full flex items-center justify-end pr-2"
                :style="{ width: Math.min((fruta.peso / Math.max(...produccionPorFruta.map(f => f.peso))) * 100, 100) + '%' }"
              >
                <span class="text-xs text-white font-bold">{{ formatearPeso(fruta.peso) }}</span>
              </div>
            </div>
            <div class="w-16 text-sm text-gray-500 text-right">{{ fruta.tarimas }} tarimas</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Tercera fila -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
      <!-- Top 5 acopiadores -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border">
        <h3 class="text-lg font-bold text-gray-800 mb-4">Top 5 Acopiadores</h3>
        <div class="space-y-3">
          <div 
            v-for="(acop, index) in topAcopiadores" 
            :key="acop.id"
            class="flex items-center gap-4 p-3 bg-gray-50 rounded-xl"
          >
            <div class="w-8 h-8 rounded-full bg-emerald-500 text-white flex items-center justify-center font-bold text-sm">
              {{ index + 1 }}
            </div>
            <div class="flex-1">
              <div class="font-medium text-gray-800">{{ acop.nombre }}</div>
              <div class="text-xs text-gray-500">{{ acop.viajes }} viajes</div>
            </div>
            <div class="text-right">
              <div class="font-bold text-emerald-600">{{ formatearPeso(acop.peso) }}</div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- Pagos por proveedor -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border">
        <h3 class="text-lg font-bold text-gray-800 mb-4">Pagos por Proveedor (Top 5)</h3>
        <div class="space-y-3">
          <div 
            v-for="(prov, index) in pagosPorProveedor" 
            :key="prov.id"
            class="flex items-center gap-4 p-3 bg-gray-50 rounded-xl"
          >
            <div class="w-8 h-8 rounded-full bg-blue-500 text-white flex items-center justify-center font-bold text-sm">
              {{ index + 1 }}
            </div>
            <div class="flex-1">
              <div class="font-medium text-gray-800">{{ prov.nombre }}</div>
              <div class="text-xs text-gray-500">{{ prov.pagos }} pagos</div>
            </div>
            <div class="text-right">
              <div class="font-bold text-blue-600">{{ formatearMoneda(prov.total) }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Estados de viajes -->
    <div class="bg-white p-6 rounded-2xl shadow-sm border mb-8">
      <h3 class="text-lg font-bold text-gray-800 mb-4">Viajes por Estado</h3>
      <div class="grid grid-cols-3 gap-4">
        <div class="p-4 bg-blue-50 rounded-xl text-center">
          <div class="text-3xl font-black text-blue-600">{{ viajesPorEstado.ACTIVO }}</div>
          <div class="text-sm text-blue-800 font-medium">Activos</div>
        </div>
        <div class="p-4 bg-orange-50 rounded-xl text-center">
          <div class="text-3xl font-black text-orange-600">{{ viajesPorEstado.CERRADO }}</div>
          <div class="text-sm text-orange-800 font-medium">Cerrados</div>
        </div>
        <div class="p-4 bg-emerald-50 rounded-xl text-center">
          <div class="text-3xl font-black text-emerald-600">{{ viajesPorEstado.CONCILIADO }}</div>
          <div class="text-sm text-emerald-800 font-medium">Conciliados</div>
        </div>
      </div>
    </div>

    <!-- Reporte de Mermas de Aguacate (Trazabilidad Entrada vs Salida) -->
    <div class="bg-white p-8 rounded-3xl border shadow-sm mb-8">
      <h2 class="text-xl font-black text-gray-800 mb-2 flex items-center">
        📉 Reporte de Mermas de Aguacates (Trazabilidad de Tarimas)
      </h2>
      <p class="text-gray-500 text-sm mb-6">Comparativa del peso de báscula de entrada vs el peso de báscula al salir de la cámara fría.</p>

      <div class="overflow-x-auto border rounded-2xl">
        <table class="min-w-full text-left text-sm text-gray-600">
          <thead class="bg-red-50 text-red-800 border-b">
            <tr>
              <th class="p-3">Tarima</th>
              <th class="p-3">Tipo Fruta</th>
              <th class="p-3">Ingreso</th>
              <th class="p-3 text-right">Peso Entrada (kg)</th>
              <th class="p-3">Salida</th>
              <th class="p-3 text-right">Peso Salida (kg)</th>
              <th class="p-3 text-right">Merma (kg)</th>
              <th class="p-3 text-right">% Merma</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="t in mermasTarimas" :key="t.id" class="border-b hover:bg-gray-50/50">
              <td class="p-3 font-bold text-gray-800">{{ t.numero_tarima_display }}</td>
              <td class="p-3">{{ t.tipo_fruta_nombre }}</td>
              <td class="p-3 text-xs">{{ t.fecha_ingreso?.substring(0, 16).replace('T', ' ') }}</td>
              <td class="p-3 text-right font-semibold">{{ formatearPeso(t.peso_entrada) }}</td>
              <td class="p-3 text-xs">{{ t.fecha_salida?.substring(0, 16).replace('T', ' ') }}</td>
              <td class="p-3 text-right font-semibold text-orange-600">{{ formatearPeso(t.peso_salida) }}</td>
              <td class="p-3 text-right font-bold text-red-600">{{ formatearPeso(t.merma) }} kg</td>
              <td class="p-3 text-right font-black text-red-600">{{ t.porc_merma?.toFixed(2) }}%</td>
            </tr>
            <tr v-if="mermasTarimas.length === 0">
              <td colspan="8" class="p-8 text-center text-gray-400">No hay registros de tarimas enviadas para calcular merma.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
