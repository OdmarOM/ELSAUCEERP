<script setup>
import { ref, onMounted, computed } from 'vue'

const API_URL = '/api'
const cuentas = ref([])
const cargando = ref(false)

const mostrarModalAbono = ref(false)
const cuentaSeleccionada = ref(null)
const nuevoAbono = ref({ monto_pagado: 0, metodo_pago: 'TRANSFERENCIA', referencia: '' })

const mostrarModalDetalle = ref(false)
const cuentaDetalle = ref(null)
const historialAbonos = ref([])

// Filtros
const filtroProveedor = ref('')
const fechaFiltro = ref('')
const modoFecha = ref('todo') // 'todo', 'dia', 'semana'

const fetchCuentasPagar = async () => {
  cargando.value = true
  try {
    const res = await fetch(`${API_URL}/finanzas/pagar`)
    cuentas.value = await res.json()
  } catch (e) {
    console.error(e)
  } finally {
    cargando.value = false
  }
}

onMounted(() => fetchCuentasPagar())

const formatearMoneda = (valor) => {
  if (valor == null) return '0.00'
  return parseFloat(valor).toFixed(2)
}

const abrirAbono = (cuenta) => {
  cuentaSeleccionada.value = cuenta
  nuevoAbono.value = { 
    monto_pagado: parseFloat(cuenta.saldo_pendiente).toFixed(2), 
    metodo_pago: 'TRANSFERENCIA', 
    referencia: '' 
  }
  mostrarModalAbono.value = true
}

const abrirDetalle = async (cuenta) => {
  cuentaDetalle.value = cuenta
  mostrarModalDetalle.value = true
  cargando.value = true
  try {
    const res = await fetch(`${API_URL}/finanzas/pagar/${cuenta.id}/historial`)
    historialAbonos.value = await res.json()
  } catch (e) {
    console.error(e)
  } finally {
    cargando.value = false
  }
}

const registrarAbono = async () => {
  if (nuevoAbono.value.monto_pagado <= 0 || nuevoAbono.value.monto_pagado > cuentaSeleccionada.value.saldo_pendiente) {
    return alert("Monto inválido")
  }
  cargando.value = true
  try {
    const res = await fetch(`${API_URL}/finanzas/pagar/${cuentaSeleccionada.value.id}/abono`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(nuevoAbono.value)
    })
    if (res.ok) {
      mostrarModalAbono.value = false
      await fetchCuentasPagar()
    } else {
      const data = await res.json()
      alert(data.detail || "Error registrando abono")
    }
  } catch (e) {
    alert("Error registrando abono")
    console.error(e)
  } finally {
    cargando.value = false
  }
}

// Lógica de filtro por fecha semanal (Lunes a Sábado)
const obtenerLunesYSabado = (fechaStr) => {
  const fecha = new Date(fechaStr + 'T00:00:00')
  const diaSemana = fecha.getDay() // 0 = Domingo, 1 = Lunes, etc.
  
  // Calcular diferencia al lunes (si es domingo (0), el lunes es -6 días atrás)
  const diffLunes = diaSemana === 0 ? -6 : 1 - diaSemana
  const lunes = new Date(fecha)
  lunes.setDate(fecha.getDate() + diffLunes)
  
  // Sábado es lunes + 5 días
  const sabado = new Date(lunes)
  sabado.setDate(lunes.getDate() + 5)
  
  return { lunes, sabado }
}

const cuentasFiltradas = computed(() => {
  return cuentas.value.filter(c => {
    // 1. Filtro por proveedor/acopiador
    if (filtroProveedor.value) {
      const query = filtroProveedor.value.toLowerCase()
      if (!c.proveedor_nombre.toLowerCase().includes(query)) {
        return false
      }
    }
    
    // 2. Filtro por fecha
    if (fechaFiltro.value && modoFecha.value !== 'todo') {
      const fechaCuenta = c.fecha_emision ? c.fecha_emision.split('T')[0] : ''
      if (modoFecha.value === 'dia') {
        if (fechaCuenta !== fechaFiltro.value) return false
      } else if (modoFecha.value === 'semana') {
        const { lunes, sabado } = obtenerLunesYSabado(fechaFiltro.value)
        const dateCuenta = new Date(fechaCuenta + 'T00:00:00')
        // Normalizar a fechas sin hora para comparación limpia
        const dateLunes = new Date(lunes.getFullYear(), lunes.getMonth(), lunes.getDate())
        const dateSabado = new Date(sabado.getFullYear(), sabado.getMonth(), sabado.getDate())
        if (dateCuenta < dateLunes || dateCuenta > dateSabado) return false
      }
    }
    
    return true
  })
})

const cuentasPendientes = computed(() => {
  return cuentasFiltradas.value.filter(c => c.estado === 'PENDIENTE')
})

const cuentasResueltas = computed(() => {
  return cuentasFiltradas.value.filter(c => c.estado === 'PAGADO')
})
</script>

<template>
  <div class="min-h-screen bg-gray-50 p-8">
    <div class="flex justify-between items-center mb-8">
      <h1 class="text-3xl font-black text-gray-800">🧾 Cuentas por Pagar (Proveedores y Acopiadores)</h1>
      <router-link to="/" class="bg-gray-200 hover:bg-gray-300 text-gray-800 font-bold px-5 py-2.5 rounded-xl transition">
        Volver
      </router-link>
    </div>

    <!-- Barra de Filtros -->
    <div class="bg-white p-6 rounded-3xl shadow-sm border mb-8 flex flex-wrap gap-4 items-center">
      <div class="flex-1 min-w-[250px]">
        <label class="block text-xs font-bold text-gray-500 uppercase mb-2">Buscar Proveedor/Acopiador</label>
        <input 
          type="text" 
          v-model="filtroProveedor" 
          placeholder="Escribe el nombre..." 
          class="w-full border rounded-xl p-3 text-sm focus:outline-none focus:ring-2 focus:ring-red-500" 
        />
      </div>

      <div class="w-48">
        <label class="block text-xs font-bold text-gray-500 uppercase mb-2">Modo Fecha</label>
        <select 
          v-model="modoFecha" 
          class="w-full border rounded-xl p-3 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-red-500"
        >
          <option value="todo">Mostrar Todo</option>
          <option value="dia">Por Día</option>
          <option value="semana">Por Semana (Lun-Sáb)</option>
        </select>
      </div>

      <div v-if="modoFecha !== 'todo'" class="w-48">
        <label class="block text-xs font-bold text-gray-500 uppercase mb-2">Seleccionar Fecha</label>
        <input 
          type="date" 
          v-model="fechaFiltro" 
          class="w-full border rounded-xl p-3 text-sm focus:outline-none focus:ring-2 focus:ring-red-500" 
        />
      </div>
    </div>

    <div v-if="cargando" class="text-center p-12 text-gray-500 font-bold">
      Cargando cuentas por pagar...
    </div>

    <!-- Layout en 2 Columnas: Pendientes vs Resueltas -->
    <div v-else class="grid grid-cols-1 lg:grid-cols-2 gap-8">
      
      <!-- COLUMNA IZQUIERDA: CUENTAS PENDIENTES -->
      <div class="bg-white p-6 rounded-3xl shadow-sm border">
        <div class="flex justify-between items-center mb-6 border-b pb-4">
          <h2 class="text-xl font-black text-red-600 flex items-center">
            <span class="w-3.5 h-3.5 rounded-full bg-red-500 mr-2.5 animate-pulse"></span>
            Cuentas Pendientes ({{ cuentasPendientes.length }})
          </h2>
          <span class="text-sm bg-red-50 text-red-700 font-bold px-3 py-1 rounded-full">
            Total: ${{ formatearMoneda(cuentasPendientes.reduce((acc, c) => acc + c.saldo_pendiente, 0)) }}
          </span>
        </div>

        <div v-if="cuentasPendientes.length === 0" class="text-center py-12 text-gray-400">
          No hay cuentas pendientes con los filtros aplicados.
        </div>

        <div class="space-y-4 max-h-[70vh] overflow-y-auto pr-1">
          <div 
            v-for="c in cuentasPendientes" 
            :key="c.id" 
            class="p-5 rounded-2xl border border-red-100 bg-red-50/30 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 hover:shadow-md transition"
          >
            <div>
              <h3 class="text-lg font-black text-gray-800">{{ c.proveedor_nombre }}</h3>
              <p class="text-xs text-gray-500">Nota Folio: <strong class="text-gray-700">{{ c.nota_folio || 'S/F' }}</strong></p>
              <p class="text-xs text-gray-400">Fecha: {{ c.fecha_emision.split('T')[0] }}</p>
              <div class="mt-2 text-sm text-gray-500">
                Total nota: <span class="font-bold">${{ formatearMoneda(c.monto_total) }}</span>
              </div>
            </div>
            <div class="text-left md:text-right w-full md:w-auto">
              <div class="text-2xl font-black text-red-600 mb-2">
                ${{ formatearMoneda(c.saldo_pendiente) }}
              </div>
              <div class="flex gap-2 justify-start md:justify-end">
                <button 
                  @click="abrirAbono(c)" 
                  class="bg-red-600 hover:bg-red-700 text-white font-bold text-xs px-3.5 py-2 rounded-xl transition"
                >
                  Abonar
                </button>
                <button 
                  @click="abrirDetalle(c)" 
                  class="bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold text-xs px-3.5 py-2 rounded-xl transition"
                >
                  Detalle
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- COLUMNA DERECHA: CUENTAS RESUELTAS -->
      <div class="bg-white p-6 rounded-3xl shadow-sm border">
        <div class="flex justify-between items-center mb-6 border-b pb-4">
          <h2 class="text-xl font-black text-emerald-600 flex items-center">
            <span class="w-3.5 h-3.5 rounded-full bg-emerald-500 mr-2.5"></span>
            Cuentas Pagadas ({{ cuentasResueltas.length }})
          </h2>
          <span class="text-sm bg-emerald-50 text-emerald-700 font-bold px-3 py-1 rounded-full">
            Total: ${{ formatearMoneda(cuentasResueltas.reduce((acc, c) => acc + c.monto_total, 0)) }}
          </span>
        </div>

        <div v-if="cuentasResueltas.length === 0" class="text-center py-12 text-gray-400">
          No hay cuentas pagadas con los filtros aplicados.
        </div>

        <div class="space-y-4 max-h-[70vh] overflow-y-auto pr-1">
          <div 
            v-for="c in cuentasResueltas" 
            :key="c.id" 
            class="p-5 rounded-2xl border border-emerald-100 bg-emerald-50/20 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 hover:shadow-md transition"
          >
            <div>
              <h3 class="text-lg font-bold text-gray-800">{{ c.proveedor_nombre }}</h3>
              <p class="text-xs text-gray-500">Nota Folio: <strong class="text-gray-700">{{ c.nota_folio || 'S/F' }}</strong></p>
              <p class="text-xs text-gray-400">Fecha: {{ c.fecha_emision.split('T')[0] }}</p>
            </div>
            <div class="text-left md:text-right w-full md:w-auto">
              <div class="text-2xl font-black text-emerald-600 mb-2">
                ${{ formatearMoneda(c.monto_total) }}
              </div>
              <button 
                @click="abrirDetalle(c)" 
                class="bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold text-xs px-4 py-2 rounded-xl transition"
              >
                Ver Historial
              </button>
            </div>
          </div>
        </div>
      </div>

    </div>

    <!-- Modal Registrar Abono -->
    <div v-if="mostrarModalAbono" class="fixed inset-0 bg-black/60 flex justify-center items-center z-50 p-4">
      <div class="bg-white p-6 rounded-3xl w-full max-w-md shadow-2xl">
        <h2 class="text-xl font-black text-gray-800 mb-4">Registrar Abono</h2>
        <div class="mb-4 text-sm bg-gray-50 p-4 rounded-xl space-y-1">
          <p>Proveedor: <strong>{{ cuentaSeleccionada?.proveedor_nombre }}</strong></p>
          <p>Nota Folio: <strong>{{ cuentaSeleccionada?.nota_folio || 'S/F' }}</strong></p>
          <p class="text-red-600 font-black text-base mt-1">Saldo pendiente: ${{ formatearMoneda(cuentaSeleccionada?.saldo_pendiente) }}</p>
        </div>
        
        <div class="space-y-4">
          <div>
            <label class="block text-xs font-bold text-gray-500 uppercase mb-2">Monto a Pagar ($)</label>
            <input 
              type="number" 
              v-model="nuevoAbono.monto_pagado" 
              class="w-full border rounded-xl p-3 text-sm focus:outline-none focus:ring-2 focus:ring-red-500" 
            />
          </div>

          <div>
            <label class="block text-xs font-bold text-gray-500 uppercase mb-2">Método de Pago</label>
            <select 
              v-model="nuevoAbono.metodo_pago" 
              class="w-full border rounded-xl p-3 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-red-500"
            >
              <option value="EFECTIVO">Efectivo</option>
              <option value="TRANSFERENCIA">Transferencia</option>
              <option value="CHEQUE">Cheque</option>
            </select>
          </div>

          <div>
            <label class="block text-xs font-bold text-gray-500 uppercase mb-2">Referencia / Observación (Opcional)</label>
            <input 
              type="text" 
              v-model="nuevoAbono.referencia" 
              placeholder="Ej. Transferencia Bancomer"
              class="w-full border rounded-xl p-3 text-sm focus:outline-none focus:ring-2 focus:ring-red-500" 
            />
          </div>
        </div>

        <div class="flex justify-end gap-3 mt-6">
          <button 
            @click="mostrarModalAbono = false" 
            class="bg-gray-100 hover:bg-gray-200 text-gray-600 font-bold px-4 py-2 rounded-xl text-sm"
          >
            Cancelar
          </button>
          <button 
            @click="registrarAbono" 
            class="bg-red-600 hover:bg-red-700 text-white font-bold px-5 py-2 rounded-xl text-sm transition"
          >
            Guardar Abono
          </button>
        </div>
      </div>
    </div>

    <!-- Modal Detalle & Historial de Abonos -->
    <div v-if="mostrarModalDetalle" class="fixed inset-0 bg-black/60 flex justify-center items-center z-50 p-4">
      <div class="bg-white p-8 rounded-3xl w-full max-w-2xl max-h-[85vh] overflow-y-auto shadow-2xl">
        <div class="flex justify-between items-center mb-6 border-b pb-4">
          <h2 class="text-2xl font-black text-gray-800">Detalles e Historial de Abonos</h2>
          <button @click="mostrarModalDetalle = false" class="text-gray-400 hover:text-gray-600 text-2xl font-black">&times;</button>
        </div>

        <div class="bg-gray-50 p-5 rounded-2xl mb-6 grid grid-cols-2 gap-4 text-sm">
          <div>
            <p class="text-gray-400 uppercase text-xs font-bold">Proveedor/Acopiador</p>
            <p class="font-bold text-gray-800 text-base">{{ cuentaDetalle?.proveedor_nombre }}</p>
          </div>
          <div>
            <p class="text-gray-400 uppercase text-xs font-bold">Nota Folio</p>
            <p class="font-bold text-gray-800 text-base">{{ cuentaDetalle?.nota_folio || 'S/F' }}</p>
          </div>
          <div>
            <p class="text-gray-400 uppercase text-xs font-bold">Monto Original</p>
            <p class="font-bold text-gray-700">${{ formatearMoneda(cuentaDetalle?.monto_total) }}</p>
          </div>
          <div>
            <p class="text-gray-400 uppercase text-xs font-bold">Saldo Pendiente</p>
            <p class="font-bold text-red-600">${{ formatearMoneda(cuentaDetalle?.saldo_pendiente) }}</p>
          </div>
        </div>

        <h3 class="text-lg font-black text-gray-800 mb-4 flex items-center">
          💵 Abonos Realizados
        </h3>

        <div class="overflow-x-auto border rounded-2xl">
          <table class="min-w-full text-left text-sm">
            <thead class="bg-gray-50 border-b text-gray-600 font-bold uppercase text-xs">
              <tr>
                <th class="p-3">Fecha</th>
                <th class="p-3">Monto</th>
                <th class="p-3">Método</th>
                <th class="p-3">Referencia</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="h in historialAbonos" :key="h.id" class="border-b hover:bg-gray-50/50">
                <td class="p-3">{{ h.fecha_pago.replace('T', ' ').substring(0, 16) }}</td>
                <td class="p-3 font-bold text-emerald-600">${{ formatearMoneda(h.monto_pagado) }}</td>
                <td class="p-3 font-medium">{{ h.metodo_pago }}</td>
                <td class="p-3 text-gray-500">{{ h.referencia || 'N/A' }}</td>
              </tr>
              <tr v-if="historialAbonos.length === 0">
                <td colspan="4" class="p-6 text-center text-gray-400">No hay abonos registrados para esta cuenta.</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="flex justify-end mt-6">
          <button 
            @click="mostrarModalDetalle = false" 
            class="bg-gray-100 hover:bg-gray-200 text-gray-700 font-bold px-6 py-2.5 rounded-xl text-sm"
          >
            Cerrar
          </button>
        </div>
      </div>
    </div>

  </div>
</template>
