<script setup>
import { ref, onMounted } from 'vue'

const API_URL = '/api'
const cuentas = ref([])
const cargando = ref(false)

const mostrarModalCobro = ref(false)
const cuentaSeleccionada = ref(null)
const nuevoCobro = ref({ monto_cobrado: 0, metodo_pago: 'TRANSFERENCIA', referencia: '' })

const mostrarModalDetalle = ref(false)
const cuentaDetalle = ref(null)
const tarimasDetalle = ref([])
const historialCobros = ref([])

const fetchCuentas = async () => {
  try {
    const res = await fetch(`${API_URL}/finanzas/cobrar`)
    cuentas.value = await res.json()
  } catch (e) { console.error(e) }
}

onMounted(() => fetchCuentas())

const abrirCobro = (cuenta) => {
  cuentaSeleccionada.value = cuenta
  nuevoCobro.value = { monto_cobrado: parseFloat(cuenta.saldo_pendiente).toFixed(2), metodo_pago: 'TRANSFERENCIA', referencia: '' }
  mostrarModalCobro.value = true
}

const abrirDetalle = async (cuenta) => {
  cuentaDetalle.value = cuenta
  mostrarModalDetalle.value = true
  cargando.value = true
  try {
    const resCobros = await fetch(`${API_URL}/finanzas/cobrar/${cuenta.id}/historial`)
    historialCobros.value = await resCobros.json()
    
    if (cuenta.viaje_salida_id) {
      const resTarimas = await fetch(`${API_URL}/viajes-salida/${cuenta.viaje_salida_id}/tarimas`)
      tarimasDetalle.value = await resTarimas.json()
    } else {
      tarimasDetalle.value = []
    }
  } catch (e) {
    console.error(e)
  } finally {
    cargando.value = false
  }
}

const formatearMoneda = (valor) => {
  if (valor == null) return '0.00'
  return parseFloat(valor).toFixed(2)
}

const registrarCobro = async () => {
  if (nuevoCobro.value.monto_cobrado <= 0 || nuevoCobro.value.monto_cobrado > cuentaSeleccionada.value.saldo_pendiente) {
    return alert("Monto inválido")
  }
  cargando.value = true
  try {
    await fetch(`${API_URL}/finanzas/cobrar/${cuentaSeleccionada.value.id}/pagar`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(nuevoCobro.value)
    })
    mostrarModalCobro.value = false
    await fetchCuentas()
  } catch (e) {
    alert("Error registrando cobro")
    console.error(e)
  } finally {
    cargando.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-gray-50 p-8">
    <div class="flex justify-between items-center mb-8">
      <h1 class="text-3xl font-bold">💰 Cuentas por Cobrar (Clientes)</h1>
      <router-link to="/" class="bg-gray-200 px-4 py-2 rounded-lg">Volver</router-link>
    </div>

    <div class="bg-white rounded-3xl shadow-sm border overflow-hidden">
      <table class="min-w-full text-left">
        <thead class="bg-gray-50 border-b">
          <tr>
            <th class="p-4">Fecha</th>
            <th class="p-4">Cliente</th>
            <th class="p-4">Ref (Viaje Salida)</th>
            <th class="p-4">Total</th>
            <th class="p-4">Saldo Pendiente</th>
            <th class="p-4">Estado</th>
            <th class="p-4">Acción</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in cuentas" :key="c.id" class="border-b">
            <td class="p-4">{{ c.fecha_emision.split('T')[0] }}</td>
            <td class="p-4 font-bold">{{ c.cliente_nombre }}</td>
            <td class="p-4">{{ c.viaje_placa || 'N/A' }}</td>
            <td class="p-4 text-gray-500">${{ formatearMoneda(c.monto_total) }}</td>
            <td class="p-4 font-bold text-red-500">${{ formatearMoneda(c.saldo_pendiente) }}</td>
            <td class="p-4">
              <span :class="c.estado === 'PAGADO' ? 'bg-emerald-100 text-emerald-800' : 'bg-amber-100 text-amber-800'" class="px-3 py-1 rounded-full text-xs font-bold">
                {{ c.estado }}
              </span>
            </td>
            <td class="p-4 flex gap-2">
              <button v-if="c.estado === 'PENDIENTE'" @click="abrirCobro(c)" class="bg-blue-500 text-white px-3 py-1.5 rounded-lg text-sm font-bold">
                Abonar
              </button>
              <button @click="abrirDetalle(c)" class="bg-gray-200 text-gray-700 px-3 py-1.5 rounded-lg text-sm font-bold">
                Detalle
              </button>
            </td>
          </tr>
          <tr v-if="cuentas.length === 0">
            <td colspan="7" class="p-8 text-center text-gray-400">No hay cuentas por cobrar registradas.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Modal Cobro -->
    <div v-if="mostrarModalCobro" class="fixed inset-0 bg-black/50 flex justify-center items-center z-50">
      <div class="bg-white p-6 rounded-2xl w-full max-w-md">
        <h2 class="text-xl font-bold mb-4">Registrar Abono</h2>
        <p class="mb-4">Cliente: <strong>{{ cuentaSeleccionada?.cliente_nombre }}</strong></p>
        <p class="mb-4 text-red-500 font-bold">Deuda actual: ${{ formatearMoneda(cuentaSeleccionada?.saldo_pendiente) }}</p>
        
        <label class="block mb-2 text-sm">Monto a abonar ($)</label>
        <input type="number" v-model="nuevoCobro.monto_cobrado" class="w-full border p-2 rounded-lg mb-4" />

        <label class="block mb-2 text-sm">Método de Pago</label>
        <select v-model="nuevoCobro.metodo_pago" class="w-full border p-2 rounded-lg mb-4">
          <option value="EFECTIVO">Efectivo</option>
          <option value="TRANSFERENCIA">Transferencia</option>
          <option value="CHEQUE">Cheque</option>
        </select>

        <label class="block mb-2 text-sm">Referencia (Opcional)</label>
        <input v-model="nuevoCobro.referencia" class="w-full border p-2 rounded-lg mb-6" />

        <div class="flex justify-end gap-2">
          <button @click="mostrarModalCobro = false" class="bg-gray-200 px-4 py-2 rounded-lg">Cancelar</button>
          <button @click="registrarCobro" class="bg-blue-500 text-white px-4 py-2 rounded-lg font-bold">Guardar</button>
        </div>
      </div>
    </div>

    <!-- Modal Detalle -->
    <div v-if="mostrarModalDetalle" class="fixed inset-0 bg-black/50 flex justify-center items-center z-50 p-4">
      <div class="bg-white p-8 rounded-3xl w-full max-w-3xl max-h-[90vh] overflow-y-auto">
        <div class="flex justify-between items-center mb-6">
          <h2 class="text-2xl font-bold">Detalle de Cuenta</h2>
          <button @click="mostrarModalDetalle = false" class="text-gray-400 hover:text-gray-600 text-2xl">&times;</button>
        </div>
        
        <div class="bg-gray-50 p-4 rounded-2xl mb-6">
          <p><strong>Cliente:</strong> {{ cuentaDetalle?.cliente_nombre }}</p>
          <p><strong>Total:</strong> ${{ formatearMoneda(cuentaDetalle?.monto_total) }}</p>
          <p><strong>Saldo Pendiente:</strong> ${{ formatearMoneda(cuentaDetalle?.saldo_pendiente) }}</p>
          <p><strong>Referencia Viaje:</strong> {{ cuentaDetalle?.viaje_placa || 'N/A' }}</p>
        </div>

        <h3 class="text-xl font-bold mb-4 text-emerald-700">Historial de Pagos</h3>
        <table class="min-w-full text-left text-sm mb-6 border">
          <thead class="bg-emerald-50 border-b border-emerald-100 text-emerald-800">
            <tr><th class="p-3">Fecha</th><th class="p-3">Monto</th><th class="p-3">Método</th><th class="p-3">Referencia</th></tr>
          </thead>
          <tbody>
            <tr v-for="h in historialCobros" :key="h.id" class="border-b">
              <td class="p-3">{{ h.fecha_cobro.replace('T', ' ').substring(0, 16) }}</td>
              <td class="p-3 font-bold text-emerald-600">${{ formatearMoneda(h.monto_cobrado) }}</td>
              <td class="p-3">{{ h.metodo_pago }}</td>
              <td class="p-3">{{ h.referencia || 'N/A' }}</td>
            </tr>
            <tr v-if="historialCobros.length === 0"><td colspan="4" class="p-4 text-center text-gray-400">No hay pagos registrados</td></tr>
          </tbody>
        </table>

        <h3 class="text-xl font-bold mb-4 text-orange-700">Tarimas Enviadas</h3>
        <table class="min-w-full text-left text-sm border">
          <thead class="bg-orange-50 border-b border-orange-100 text-orange-800">
            <tr><th class="p-3">Tarima</th><th class="p-3">Fruta</th><th class="p-3 text-right">Cajas</th><th class="p-3 text-right">Peso Neto</th></tr>
          </thead>
          <tbody>
            <tr v-for="t in tarimasDetalle" :key="t.id" class="border-b">
              <td class="p-3 font-bold">{{ t.numero_tarima_display }}</td>
              <td class="p-3">{{ t.fruta_nombre }}</td>
              <td class="p-3 text-right">{{ t.cantidad_cajas }}</td>
              <td class="p-3 text-right font-bold text-orange-600">{{ t.peso_salida || t.peso_neto }} kg</td>
            </tr>
            <tr v-if="tarimasDetalle.length === 0"><td colspan="4" class="p-4 text-center text-gray-400">No hay tarimas vinculadas a este viaje</td></tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>
