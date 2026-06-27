<!-- Dashboard.vue - Dashboard con métricas y reportes -->
<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { get } from '../utils/api.js'
import { useCatalogsPolling } from '../utils/polling.js'
import { format } from 'date-fns'
import { es } from 'date-fns/locale'

const API_URL = '/api'

// Datos
const acopiadores = ref([])
const proveedores = ref([])
const clientes = ref([])
const tiposFruta = ref([])
const viajes = ref([])
const notas = ref([])
const registrosBascula = ref([])
const pagos = ref([])
const inventarioFrio = ref([])
const ubicacionesFrio = ref([])

// Filtros
const fechaInicio = ref(new Date(new Date().setDate(new Date().getDate() - 30)).toISOString().split('T')[0])
const fechaFin = ref(new Date().toISOString().split('T')[0])
const periodoSeleccionado = ref('mes') // semana, mes, trimestre, año

// Polling
const { data: catalogsData, loading } = useCatalogsPolling(fetchCatalogos, {
  interval: 30000,
  immediate: true
})

async function fetchCatalogos() {
  try {
    const [resAcop, resProv, resCli, resFruta, resViajes, resNotas, resRegistros, resPagos, resInventario, resFrio] = await Promise.all([
      get(`${API_URL}/acopiadores`),
      get(`${API_URL}/proveedores`),
      get(`${API_URL}/clientes`),
      get(`${API_URL}/tipos-fruta`),
      get(`${API_URL}/viajes`),
      get(`${API_URL}/notas`),
      get(`${API_URL}/registros-bascula`),
      get(`${API_URL}/pagos`),
      get(`${API_URL}/inventario-frio`),
      get(`${API_URL}/cuarto-frio`)
    ])
    
    acopiadores.value = resAcop
    proveedores.value = resProv
    clientes.value = resCli
    tiposFruta.value = resFruta
    viajes.value = resViajes
    notas.value = resNotas
    registrosBascula.value = resRegistros
    pagos.value = resPagos
    inventarioFrio.value = resInventario
    ubicacionesFrio.value = resFrio
  } catch (error) {
    console.error('Error fetching catalogs:', error)
  }
}

// Métricas principales
const metricasPrincipales = computed(() => {
  const viajesDelPeriodo = viajes.value.filter(v => 
    v.fecha_entrada && v.fecha_entrada >= fechaInicio.value && v.fecha_entrada <= fechaFin.value
  )
  
  const pesoTotalFisico = viajesDelPeriodo.reduce((sum, v) => {
    const tarimas = registrosBascula.value.filter(r => r.viaje_id === v.id)
    return sum + tarimas.reduce((s, t) => s + parseFloat(t.peso_neto || 0), 0)
  }, 0)
  
  const pesoTotalTeorico = viajesDelPeriodo.reduce((sum, v) => 
    sum + parseFloat(v.peso_total_teorico || 0), 0
  )
  
  const totalPagado = pagos.value.filter(p => 
    p.fecha_pago && p.fecha_pago >= fechaInicio.value && p.fecha_pago <= fechaFin.value
  ).reduce((sum, p) => sum + parseFloat(p.monto_total || 0), 0)
  
  const deudaPendiente = notas.value.filter(n => n.estado_pago === 'PENDIENTE')
    .reduce((sum, n) => sum + parseFloat(n.total_monetario || 0), 0)
  
  const ocupacionFrio = ubicacionesFrio.value.filter(u => u.inventario_frio_id).length
  const tarimasEnBodega = inventarioFrio.value.filter(i => i.activo === 1 && 
    !ubicacionesFrio.value.some(u => u.inventario_frio_id === i.id)
  ).length
  
  return {
    viajesCount: viajesDelPeriodo.length,
    pesoTotalFisico: pesoTotalFisico.toFixed(2),
    pesoTotalTeorico: pesoTotalTeorico.toFixed(2),
    diferencia: (pesoTotalFisico - pesoTotalTeorico).toFixed(2),
    totalPagado: totalPagado.toFixed(2),
    deudaPendiente: deudaPendiente.toFixed(2),
    ocupacionFrio: ocupacionFrio,
    capacidadFrio: 50,
    tarimasEnBodega: tarimasEnBodega
  }
})

// Producción por día
const produccionPorDia = computed(() => {
  const dias = {}
  
  viajes.value.forEach(v => {
    if (!v.fecha_entrada) return
    
    const fecha = v.fecha_entrada.split('T')[0]
    if (!dias[fecha]) {
      dias[fecha] = { fecha, peso: 0, viajes: 0 }
    }
    
    const tarimas = registrosBascula.value.filter(r => r.viaje_id === v.id)
    const peso = tarimas.reduce((s, t) => s + parseFloat(t.peso_neto || 0), 0)
    
    dias[fecha].peso += peso
    dias[fecha].viajes += 1
  })
  
  return Object.values(dias)
    .sort((a, b) => new Date(b.fecha) - new Date(a.fecha))
    .slice(0, 14) // Últimos 14 días
})

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
  
  const hoy = new Date()
  let inicio
  
  switch (periodo) {
    case 'semana':
      inicio = new Date(hoy.setDate(hoy.getDate() - 7))
      break
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

// Formatear fecha
const formatearFecha = (fecha) => {
  return format(new Date(fecha), 'dd/MM/yyyy', { locale: es })
}

// Formatear moneda
const formatearMoneda = (valor) => {
  return new Intl.NumberFormat('es-MX', {
    style: 'currency',
    currency: 'MXN'
  }).format(valor)
}

// Formatear peso
const formatearPeso = (valor) => {
  return parseFloat(valor || 0).toFixed(2) + ' kg'
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
      <div class="flex gap-2">
        <button 
          v-for="periodo in ['semana', 'mes', 'trimestre', 'año']"
          :key="periodo"
          @click="cambiarPeriodo(periodo)"
          :class="periodoSeleccionado === periodo ? 'bg-emerald-500 text-white' : 'bg-white text-gray-600'"
          class="px-4 py-2 rounded-xl text-sm font-medium shadow-sm border transition"
        >
          {{ periodo.charAt(0).toUpperCase() + periodo.slice(1) }}
        </button>
      </div>
    </div>

    <!-- Métricas principales -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      <div class="bg-white p-6 rounded-2xl shadow-sm border">
        <div class="flex items-center justify-between mb-4">
          <span class="text-gray-500 text-sm font-medium">Viajes del Periodo</span>
          <span class="text-2xl">🚚</span>
        </div>
        <div class="text-3xl font-black text-gray-800">{{ metricasPrincipales.viajesCount }}</div>
        <div class="text-xs text-gray-400 mt-2">Desde {{ formatearFecha(fechaInicio) }}</div>
      </div>
      
      <div class="bg-white p-6 rounded-2xl shadow-sm border">
        <div class="flex items-center justify-between mb-4">
          <span class="text-gray-500 text-sm font-medium">Peso Total Físico</span>
          <span class="text-2xl">⚖️</span>
        </div>
        <div class="text-3xl font-black text-blue-600">{{ formatearPeso(metricasPrincipales.pesoTotalFisico) }}</div>
        <div class="text-xs text-gray-400 mt-2">Peso neto de báscula</div>
      </div>
      
      <div class="bg-white p-6 rounded-2xl shadow-sm border">
        <div class="flex items-center justify-between mb-4">
          <span class="text-gray-500 text-sm font-medium">Total Pagado</span>
          <span class="text-2xl">💰</span>
        </div>
        <div class="text-3xl font-black text-emerald-600">{{ formatearMoneda(metricasPrincipales.totalPagado) }}</div>
        <div class="text-xs text-gray-400 mt-2">Pagos en el periodo</div>
      </div>
      
      <div class="bg-white p-6 rounded-2xl shadow-sm border">
        <div class="flex items-center justify-between mb-4">
          <span class="text-gray-500 text-sm font-medium">Deuda Pendiente</span>
          <span class="text-2xl">📊</span>
        </div>
        <div class="text-3xl font-black text-orange-600">{{ formatearMoneda(metricasPrincipales.deudaPendiente) }}</div>
        <div class="text-xs text-gray-400 mt-2">Notas por pagar</div>
      </div>
    </div>

    <!-- Segunda fila de métricas -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
      <div class="bg-white p-6 rounded-2xl shadow-sm border">
        <div class="flex items-center justify-between mb-4">
          <span class="text-gray-500 text-sm font-medium">Ocupación Cuarto Frío</span>
          <span class="text-2xl">❄️</span>
        </div>
        <div class="flex items-end gap-2">
          <div class="text-3xl font-black text-blue-600">{{ metricasPrincipales.ocupacionFrio }}</div>
          <div class="text-lg text-gray-400 mb-1">/ {{ metricasPrincipales.capacidadFrio }}</div>
        </div>
        <div class="w-full bg-gray-200 rounded-full h-2 mt-3">
          <div 
            class="bg-blue-500 h-2 rounded-full transition-all"
            :style="{ width: (metricasPrincipales.ocupacionFrio / metricasPrincipales.capacidadFrio * 100) + '%' }"
          ></div>
        </div>
        <div class="text-xs text-gray-400 mt-2">{{ ((metricasPrincipales.ocupacionFrio / metricasPrincipales.capacidadFrio) * 100).toFixed(1) }}% ocupado</div>
      </div>
      
      <div class="bg-white p-6 rounded-2xl shadow-sm border">
        <div class="flex items-center justify-between mb-4">
          <span class="text-gray-500 text-sm font-medium">Tarimas en Bodega</span>
          <span class="text-2xl">🧱</span>
        </div>
        <div class="text-3xl font-black text-orange-600">{{ metricasPrincipales.tarimasEnBodega }}</div>
        <div class="text-xs text-gray-400 mt-2">Sin ubicación en frío</div>
      </div>
      
      <div class="bg-white p-6 rounded-2xl shadow-sm border">
        <div class="flex items-center justify-between mb-4">
          <span class="text-gray-500 text-sm font-medium">Diferencia Físico vs Teórico</span>
          <span class="text-2xl">📉</span>
        </div>
        <div 
          class="text-3xl font-black"
          :class="parseFloat(metricasPrincipales.diferencia) >= 0 ? 'text-emerald-600' : 'text-red-600'"
        >
          {{ parseFloat(metricasPrincipales.diferencia) >= 0 ? '+' : '' }}{{ formatearPeso(metricasPrincipales.diferencia) }}
        </div>
        <div class="text-xs text-gray-400 mt-2">Conciliación de pesos</div>
      </div>
    </div>

    <!-- Gráficos y tablas -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
      <!-- Producción por día -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border">
        <h3 class="text-lg font-bold text-gray-800 mb-4">Producción por Día (Últimos 14 días)</h3>
        <div class="space-y-3 max-h-80 overflow-y-auto">
          <div 
            v-for="dia in produccionPorDia" 
            :key="dia.fecha"
            class="flex items-center gap-4"
          >
            <div class="w-24 text-sm text-gray-600">{{ formatearFecha(dia.fecha) }}</div>
            <div class="flex-1 bg-gray-100 rounded-full h-6 overflow-hidden">
              <div 
                class="bg-emerald-500 h-full rounded-full flex items-center justify-end pr-2"
                :style="{ width: Math.min((dia.peso / Math.max(...produccionPorDia.map(d => d.peso))) * 100, 100) + '%' }"
              >
                <span class="text-xs text-white font-bold">{{ formatearPeso(dia.peso) }}</span>
              </div>
            </div>
            <div class="w-16 text-sm text-gray-500 text-right">{{ dia.viajes }} viajes</div>
          </div>
        </div>
      </div>
      
      <!-- Producción por tipo de fruta -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border">
        <h3 class="text-lg font-bold text-gray-800 mb-4">Producción por Tipo de Fruta</h3>
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
    <div class="bg-white p-6 rounded-2xl shadow-sm border">
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
  </div>
</template>
