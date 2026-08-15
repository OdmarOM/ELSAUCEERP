<script setup>
import { ref, onMounted } from 'vue'

const API_URL = '/api'
const cuentasPagar = ref([])
const cargando = ref(false)

const fetchCuentasPagar = async () => {
  cargando.value = true
  try {
    const res = await fetch(`${API_URL}/finanzas/pagar`)
    cuentasPagar.value = await res.json()
  } catch (e) {
    console.error(e)
  } finally {
    cargando.value = false
  }
}

onMounted(() => fetchCuentasPagar())
</script>

<template>
  <div class="min-h-screen bg-gray-50 p-8">
    <div class="flex justify-between items-center mb-8">
      <h1 class="text-3xl font-bold">🧾 Cuentas por Pagar (Acopiadores)</h1>
      <router-link to="/" class="bg-gray-200 px-4 py-2 rounded-lg">Volver</router-link>
    </div>

    <div class="bg-white p-8 rounded-3xl shadow-sm border">
      <h2 class="text-xl font-bold mb-6 text-gray-700">Resumen de Deudas</h2>
      
      <div v-if="cuentasPagar.length === 0" class="text-center p-8 text-gray-500">
        No hay cuentas por pagar pendientes.
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div v-for="c in cuentasPagar" :key="c.proveedor_id" class="bg-red-50 p-6 rounded-2xl border border-red-100">
          <h3 class="text-xl font-black text-gray-800 mb-2">{{ c.proveedor_nombre }}</h3>
          <p class="text-gray-500 mb-4">{{ c.notas_pendientes }} nota(s) pendiente(s)</p>
          <div class="text-3xl font-black text-red-600 mb-4">
            ${{ parseFloat(c.total_deuda).toFixed(2) }}
          </div>
          <router-link to="/admin" class="bg-red-500 text-white px-4 py-2 rounded-lg text-sm font-bold block text-center hover:bg-red-600">
            Ir a Pagar en Oficina
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>
