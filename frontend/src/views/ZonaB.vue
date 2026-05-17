<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'

//onst API_URL = 'http://127.0.0.1:8000/api'
const API_URL = 'http://192.168.50.101:8000/api'
const pestanaActual = ref('notas')
const vistaConciliacion = ref('historial')

const cargando = ref(false)

const acopiadores = ref([])
const proveedores = ref([])
const clientes = ref([])
const tiposFruta = ref([])
const viajes = ref([])
const notas = ref([])
const registrosBascula = ref([])
const pagos = ref([])

let intervaloCarga = null

// Formateo estricto para coma flotante
const formatearPeso = (valor) => parseFloat(valor || 0).toFixed(2)

// ================= MODELOS =================
const nuevoAcopiador = ref({ nombre: '', telefono: '' })
const nuevoProveedor = ref({ nombre: '', contacto: '' })
const nuevoCliente = ref({ nombre: '', contacto: '' })
const nuevoTipoFruta = ref({ nombre: '', descripcion: '' })

const nuevaNota = ref({ folio: '', proveedor_id: '', tipo_fruta_id: '', cantidad_cajas: '', peso_neto: '', precio_kg: '', total_monetario: 0 })
const nuevoPago = ref({ proveedor_id: '', folio_pago: '', fecha_pago: new Date().toISOString().split('T')[0], metodo_pago: 'TRANSFERENCIA', monto_total: 0, nota_ids: [] })

const fechaFiltroConciliacion = ref(new Date().toISOString().split('T')[0])

// Modales
const mostrarModalPago = ref(false)
const mostrarModalDetallePago = ref(false)
const modoEdicionPago = ref(false)
const pagoSeleccionado = ref(null)
const pagoEditando = ref({})

const editandoNota = ref(null)
const mostrarModalEdicionNota = ref(false)

const mostrarModalEdicionCatalogo = ref(false)
const tipoCatalogoEdicion = ref('') // 'acopiadores', 'proveedores', 'clientes', 'tipos-fruta'
const itemEditando = ref({})

watch([() => nuevaNota.value.peso_neto, () => nuevaNota.value.precio_kg], ([neto, precio]) => {
  nuevaNota.value.total_monetario = ((parseFloat(neto) || 0) * (parseFloat(precio) || 0)).toFixed(2)
})

watch(() => nuevoPago.value.nota_ids, (idsSeleccionados) => {
  nuevoPago.value.monto_total = idsSeleccionados.reduce((sum, id) => sum + parseFloat(notas.value.find(n => n.id === id)?.total_monetario || 0), 0).toFixed(2)
}, { deep: true })

const fetchCatalogos = async () => {
  try {
    const [resAcop, resProv, resCli, resFruta, resViajes, resNotas, resRegistros, resPagos] = await Promise.all([
      fetch(`${API_URL}/acopiadores`), fetch(`${API_URL}/proveedores`), fetch(`${API_URL}/clientes`), fetch(`${API_URL}/tipos-fruta`),
      fetch(`${API_URL}/viajes`), fetch(`${API_URL}/notas`), fetch(`${API_URL}/registros-bascula`), fetch(`${API_URL}/pagos`)
    ])
    acopiadores.value = await resAcop.json(); proveedores.value = await resProv.json(); clientes.value = await resCli.json(); 
    tiposFruta.value = await resFruta.json(); viajes.value = await resViajes.json(); notas.value = await resNotas.json(); 
    registrosBascula.value = await resRegistros.json(); pagos.value = await resPagos.json();
  } catch (e) { console.error('Error auto-update:', e) }
}

onMounted(() => { fetchCatalogos(); intervaloCarga = setInterval(fetchCatalogos, 5000) })
onUnmounted(() => { if (intervaloCarga) clearInterval(intervaloCarga) })

const notasOrdenadas = computed(() => [...notas.value].sort((a, b) => b.id - a.id))
const notasLibres = computed(() => notasOrdenadas.value.filter(n => n.viaje_id === null))
const notasPendientes = computed(() => notasOrdenadas.value.filter(n => n.estado_pago === 'PENDIENTE' && n.viaje_id !== null))
const totalDeudaPendiente = computed(() => notasPendientes.value.reduce((sum, n) => sum + parseFloat(n.total_monetario), 0).toFixed(2))
const notasDelProveedorSeleccionado = computed(() => notasPendientes.value.filter(n => n.proveedor_id === nuevoPago.value.proveedor_id))
const viajesCerradosParaConciliar = computed(() => viajes.value.filter(v => v.estado === 'CERRADO' && v.tipo_operacion === 'ACOPIO'))
const viajesConciliadosFiltrados = computed(() => viajes.value.filter(v => v.estado === 'CONCILIADO' && v.fecha_entrada.startsWith(fechaFiltroConciliacion.value)).sort((a, b) => b.id - a.id))

// ================= LÓGICA ACORDEÓN DEUDAS =================
const proveedorExpandido = ref(null)

const deudasAgrupadas = computed(() => {
  const grupos = {}
  notasPendientes.value.forEach(n => {
    if (!grupos[n.proveedor_id]) {
      grupos[n.proveedor_id] = { 
        id: n.proveedor_id, 
        nombre: n.proveedor_nombre, 
        totalDeuda: 0, 
        notas: [] 
      }
    }
    grupos[n.proveedor_id].notas.push(n)
    grupos[n.proveedor_id].totalDeuda += parseFloat(n.total_monetario)
  })
  // Ordenamos para que los proveedores con mayor deuda aparezcan arriba
  return Object.values(grupos).sort((a, b) => b.totalDeuda - a.totalDeuda)
})

// ================= CATÁLOGOS =================
const agregarCatalogo = async (endpoint, data, refVar, clearData) => {
  cargando.value = true; try { await fetch(`${API_URL}/${endpoint}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) }); refVar.value = clearData; await fetchCatalogos() } finally { cargando.value = false }
}
const eliminarCatalogo = async (endpoint, id) => {
  if(!confirm("¿Eliminar registro?")) return;
  cargando.value = true; try { await fetch(`${API_URL}/${endpoint}/${id}`, { method: 'DELETE' }); await fetchCatalogos(); } finally { cargando.value = false }
}

const abrirEdicionCatalogo = (tipo, item) => {
  tipoCatalogoEdicion.value = tipo
  itemEditando.value = { ...item }
  mostrarModalEdicionCatalogo.value = true
}

const guardarEdicionCatalogo = async () => {
  cargando.value = true
  try {
    await fetch(`${API_URL}/${tipoCatalogoEdicion.value}/${itemEditando.value.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(itemEditando.value) })
    mostrarModalEdicionCatalogo.value = false
    await fetchCatalogos()
  } finally { cargando.value = false }
}

// ================= NOTAS =================
const agregarNota = async () => {
  if (!nuevaNota.value.folio) return alert("El folio es obligatorio para identificar la nota.")
  cargando.value = true
  try { await fetch(`${API_URL}/notas`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({...nuevaNota.value, viaje_id: null}) }); nuevaNota.value = { folio: '', proveedor_id: '', tipo_fruta_id: '', cantidad_cajas: '', peso_neto: '', precio_kg: '', total_monetario: 0 }; await fetchCatalogos() } finally { cargando.value = false }
}
const eliminarNota = async (id) => { 
  if(!confirm("¿Eliminar nota?")) return;
  cargando.value = true; try { await fetch(`${API_URL}/notas/${id}`, { method: 'DELETE' }); await fetchCatalogos() } finally { cargando.value = false } 
}
const prepararEdicionNota = (nota) => { editandoNota.value = { ...nota }; mostrarModalEdicionNota.value = true }
const guardarCambiosNota = async () => {
  cargando.value = true
  try {
    editandoNota.value.total_monetario = (editandoNota.value.peso_neto * editandoNota.value.precio_kg).toFixed(2)
    await fetch(`${API_URL}/notas/${editandoNota.value.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(editandoNota.value) })
    mostrarModalEdicionNota.value = false; await fetchCatalogos()
  } finally { cargando.value = false }
}

// ================= CONCILIACIÓN =================
const viajeAConciliarId = ref('')
const notasSeleccionadasParaConciliar = ref([])
const detallesViajeAConciliar = computed(() => {
  if (!viajeAConciliarId.value) return null
  const viaje = viajes.value.find(v => v.id === viajeAConciliarId.value)
  const tarimas = registrosBascula.value.filter(r => r.viaje_id === viaje.id)
  return { ...viaje, tarimas, pesoFisicoTotal: tarimas.reduce((sum, t) => sum + parseFloat(t.peso_neto || 0), 0) }
})
const pesoTeoricoSeleccionado = computed(() => notasSeleccionadasParaConciliar.value.reduce((sum, id) => sum + parseFloat(notas.value.find(n => n.id === id)?.peso_neto || 0), 0))
const diferenciaConciliacion = computed(() => detallesViajeAConciliar.value ? detallesViajeAConciliar.value.pesoFisicoTotal - pesoTeoricoSeleccionado.value : 0)

const iniciarNuevaConciliacion = () => { vistaConciliacion.value = 'formulario'; viajeAConciliarId.value = ''; notasSeleccionadasParaConciliar.value = [] }
const guardarConciliacion = async () => {
  if (!viajeAConciliarId.value || notasSeleccionadasParaConciliar.value.length === 0) return alert("Selecciona viaje y notas.")
  cargando.value = true
  try { await fetch(`${API_URL}/viajes/${viajeAConciliarId.value}/conciliar`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nota_ids: notasSeleccionadasParaConciliar.value, peso_fisico: detallesViajeAConciliar.value.pesoFisicoTotal, peso_teorico: pesoTeoricoSeleccionado.value, diferencia: diferenciaConciliacion.value }) }); vistaConciliacion.value = 'historial'; await fetchCatalogos() } finally { cargando.value = false }
}
const deshacerConciliacion = async (viajeId) => {
  if (!confirm("¿Seguro que quieres deshacer esta conciliación? Las notas quedarán libres nuevamente.")) return
  cargando.value = true; try { await fetch(`${API_URL}/viajes/${viajeId}/deshacer-conciliacion`, { method: 'POST' }); await fetchCatalogos() } finally { cargando.value = false }
}

// ================= PAGOS =================
const abrirModalPagos = () => { nuevoPago.value = { proveedor_id: '', folio_pago: '', fecha_pago: new Date().toISOString().split('T')[0], metodo_pago: 'TRANSFERENCIA', monto_total: 0, nota_ids: [] }; mostrarModalPago.value = true }
const registrarPago = async () => {
  if (nuevoPago.value.nota_ids.length === 0 || !nuevoPago.value.folio_pago) return alert("Faltan datos para el pago.")
  cargando.value = true
  try { await fetch(`${API_URL}/pagos`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(nuevoPago.value) }); mostrarModalPago.value = false; await fetchCatalogos() } finally { cargando.value = false }
}

const notasDelPagoSeleccionado = computed(() => {
  if (!pagoSeleccionado.value) return []
  return notas.value.filter(n => n.pago_id === pagoSeleccionado.value.id)
})

const abrirDetallePago = (pago) => {
  pagoSeleccionado.value = pago
  pagoEditando.value = { ...pago }
  if(pagoEditando.value.fecha_pago) pagoEditando.value.fecha_pago = pagoEditando.value.fecha_pago.split('T')[0]
  modoEdicionPago.value = false
  mostrarModalDetallePago.value = true
}

const guardarEdicionPago = async () => {
  cargando.value = true
  try {
    await fetch(`${API_URL}/pagos/${pagoEditando.value.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(pagoEditando.value) })
    mostrarModalDetallePago.value = false
    await fetchCatalogos()
  } finally { cargando.value = false }
}

const anularPago = async () => {
  if (!confirm("🚨 ¿ESTÁS SEGURO DE ANULAR ESTE PAGO?\n\nEl pago se eliminará y las facturas/notas asociadas volverán a aparecer como deudas pendientes por liquidar.")) return
  cargando.value = true
  try {
    await fetch(`${API_URL}/pagos/${pagoSeleccionado.value.id}`, { method: 'DELETE' })
    mostrarModalDetallePago.value = false
    await fetchCatalogos()
  } finally { cargando.value = false }
}

const nombreAcopiador = (id) => acopiadores.value.find(a => a.id === id)?.nombre || 'Desconocido'
const formatoViajeSelect = (v) => `Viaje #${v.id} - ${nombreAcopiador(v.acopiador_id)} - ${new Date(v.fecha_entrada).toLocaleDateString()}`
</script>

<template>
  <div class="min-h-screen bg-gray-50 p-6 md:p-12 relative">
    <div v-if="cargando" class="fixed inset-0 bg-white/60 backdrop-blur-sm z-50 flex items-center justify-center"><div class="bg-white p-6 rounded-3xl shadow-xl flex flex-col items-center"><div class="w-10 h-10 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin mb-3"></div><span class="text-gray-700 font-medium">Procesando...</span></div></div>

    <div class="flex justify-between items-center mb-8"><h1 class="text-4xl font-light tracking-tight text-gray-800 mt-1">Administración y Finanzas</h1><span class="text-xs font-bold text-gray-400 bg-white px-4 py-2 border rounded-full shadow-sm flex items-center"><span class="w-2 h-2 rounded-full bg-emerald-500 mr-2 animate-pulse"></span> ZONA B</span></div>

    <div class="flex flex-wrap gap-4 mb-8">
      <button @click="pestanaActual = 'notas'; vistaConciliacion = 'historial'" :class="{'bg-emerald-500 text-white': pestanaActual === 'notas', 'bg-white text-gray-600': pestanaActual !== 'notas'}" class="px-5 py-2.5 rounded-2xl text-sm transition shadow-sm border font-medium">📝 Captura de Notas</button>
      <button @click="pestanaActual = 'conciliacion'" :class="{'bg-emerald-500 text-white': pestanaActual === 'conciliacion', 'bg-white text-gray-600': pestanaActual !== 'conciliacion'}" class="px-5 py-2.5 rounded-2xl text-sm transition shadow-sm border font-medium">📊 Conciliación de Viajes</button>
      <button @click="pestanaActual = 'pagos'" :class="{'bg-emerald-500 text-white': pestanaActual === 'pagos', 'bg-white text-gray-600': pestanaActual !== 'pagos'}" class="px-5 py-2.5 rounded-2xl text-sm transition shadow-sm border font-medium">💰 Pagos</button>
      <button @click="pestanaActual = 'catalogos'" :class="{'bg-emerald-500 text-white': pestanaActual === 'catalogos', 'bg-white text-gray-600': pestanaActual !== 'catalogos'}" class="px-5 py-2.5 rounded-2xl text-sm transition shadow-sm border font-medium">📇 Catálogos Base</button>
    </div>

    <div v-if="pestanaActual === 'catalogos'" class="space-y-8 animate-fade-in">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        <div class="bg-white p-6 rounded-3xl shadow-sm border">
          <h2 class="text-lg font-bold mb-4 text-gray-700">Acopiadores</h2>
          <form @submit.prevent="agregarCatalogo('acopiadores', nuevoAcopiador, nuevoAcopiador, {nombre:'', telefono:''})" class="flex flex-col gap-2 mb-4">
            <input v-model="nuevoAcopiador.nombre" placeholder="Nombre" class="border p-3 rounded-xl text-sm outline-none" required />
            <div class="flex gap-2"><input v-model="nuevoAcopiador.telefono" placeholder="Teléfono" class="border p-3 rounded-xl w-full text-sm outline-none" /><button type="submit" class="bg-emerald-500 text-white px-4 rounded-xl font-bold hover:bg-emerald-600">+</button></div>
          </form>
          <ul class="text-sm text-gray-600 space-y-2 max-h-40 overflow-y-auto">
            <li v-for="a in acopiadores" :key="a.id" class="flex justify-between border-b pb-2 items-center">
              <div><span class="font-medium text-gray-800">{{a.nombre}}</span><span class="block text-xs text-gray-400">{{a.telefono || 'Sin tel'}}</span></div>
              <div><button @click="abrirEdicionCatalogo('acopiadores', a)" class="text-blue-500 mr-3 text-lg hover:scale-110 transition">✏️</button><button @click="eliminarCatalogo('acopiadores', a.id)" class="text-red-500 text-sm font-bold hover:text-red-700">X</button></div>
            </li>
          </ul>
        </div>
        <div class="bg-white p-6 rounded-3xl shadow-sm border">
          <h2 class="text-lg font-bold mb-4 text-gray-700">Proveedores</h2>
          <form @submit.prevent="agregarCatalogo('proveedores', nuevoProveedor, nuevoProveedor, {nombre:'', contacto:''})" class="flex flex-col gap-2 mb-4">
            <input v-model="nuevoProveedor.nombre" placeholder="Nombre" class="border p-3 rounded-xl text-sm outline-none" required />
            <div class="flex gap-2"><input v-model="nuevoProveedor.contacto" placeholder="Contacto" class="border p-3 rounded-xl w-full text-sm outline-none" /><button type="submit" class="bg-emerald-500 text-white px-4 rounded-xl font-bold hover:bg-emerald-600">+</button></div>
          </form>
          <ul class="text-sm text-gray-600 space-y-2 max-h-40 overflow-y-auto">
            <li v-for="p in proveedores" :key="p.id" class="flex justify-between border-b pb-2 items-center">
              <div><span class="font-medium text-gray-800">{{p.nombre}}</span><span class="block text-xs text-gray-400">{{p.contacto || 'Sin contacto'}}</span></div>
              <div><button @click="abrirEdicionCatalogo('proveedores', p)" class="text-blue-500 mr-3 text-lg hover:scale-110 transition">✏️</button><button @click="eliminarCatalogo('proveedores', p.id)" class="text-red-500 text-sm font-bold hover:text-red-700">X</button></div>
            </li>
          </ul>
        </div>
        <div class="bg-white p-6 rounded-3xl shadow-sm border">
          <h2 class="text-lg font-bold mb-4 text-purple-700">Clientes (Maquila)</h2>
          <form @submit.prevent="agregarCatalogo('clientes', nuevoCliente, nuevoCliente, {nombre:'', contacto:''})" class="flex flex-col gap-2 mb-4">
            <input v-model="nuevoCliente.nombre" placeholder="Nombre Empresa" class="border p-3 rounded-xl text-sm outline-none" required />
            <div class="flex gap-2"><input v-model="nuevoCliente.contacto" placeholder="Contacto" class="border p-3 rounded-xl w-full text-sm outline-none" /><button type="submit" class="bg-purple-500 text-white px-4 rounded-xl font-bold hover:bg-purple-600">+</button></div>
          </form>
          <ul class="text-sm text-gray-600 space-y-2 max-h-40 overflow-y-auto">
            <li v-for="c in clientes" :key="c.id" class="flex justify-between border-b pb-2 items-center">
              <div><span class="font-medium text-gray-800">{{c.nombre}}</span><span class="block text-xs text-gray-400">{{c.contacto || 'Sin contacto'}}</span></div>
              <div><button @click="abrirEdicionCatalogo('clientes', c)" class="text-blue-500 mr-3 text-lg hover:scale-110 transition">✏️</button><button @click="eliminarCatalogo('clientes', c.id)" class="text-red-500 text-sm font-bold hover:text-red-700">X</button></div>
            </li>
          </ul>
        </div>
        <div class="bg-white p-6 rounded-3xl shadow-sm border md:col-span-2 lg:col-span-3">
          <h2 class="text-lg font-bold mb-4 text-gray-700">Tipos de Fruta</h2>
          <form @submit.prevent="agregarCatalogo('tipos-fruta', nuevoTipoFruta, nuevoTipoFruta, {nombre:'', descripcion:''})" class="flex gap-2 mb-4">
            <input v-model="nuevoTipoFruta.nombre" placeholder="Fruta" class="border p-3 rounded-xl w-1/3 text-sm outline-none" required />
            <input v-model="nuevoTipoFruta.descripcion" placeholder="Descripción" class="border p-3 rounded-xl w-1/2 text-sm outline-none" />
            <button type="submit" class="bg-emerald-500 text-white px-6 rounded-xl text-sm font-medium hover:bg-emerald-600 transition">Agregar Fruta</button>
          </form>
          <div class="flex gap-4 flex-wrap">
            <span v-for="f in tiposFruta" :key="f.id" class="bg-gray-50 px-4 py-2 rounded-full text-sm flex items-center gap-3 border shadow-sm">
              <span class="font-medium">{{f.nombre}}</span> 
              <button @click="abrirEdicionCatalogo('tipos-fruta', f)" class="text-blue-500 text-sm hover:scale-110">✏️</button>
              <button @click="eliminarCatalogo('tipos-fruta', f.id)" class="text-red-500 font-bold hover:text-red-700">X</button>
            </span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="pestanaActual === 'notas'" class="space-y-8 animate-fade-in">
      <div class="bg-white p-8 rounded-3xl shadow-sm border">
        <h2 class="text-xl font-medium mb-4 text-gray-700">Registrar Nueva Nota</h2>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <div><label class="block text-sm text-gray-500 mb-1">Folio Físico</label><input v-model="nuevaNota.folio" placeholder="Ej. A-1234" class="w-full border border-gray-200 p-3.5 rounded-2xl text-sm outline-none focus:ring-2 focus:ring-emerald-400 uppercase font-bold text-emerald-700" /></div>
          <div><label class="block text-sm text-gray-500 mb-1">Proveedor</label><select v-model="nuevaNota.proveedor_id" class="w-full border border-gray-200 p-3.5 rounded-2xl text-sm outline-none"><option value="" disabled>Selecciona...</option><option v-for="p in proveedores" :value="p.id" :key="p.id">{{ p.nombre }}</option></select></div>
          <div><label class="block text-sm text-gray-500 mb-1">Tipo de Fruta</label><select v-model="nuevaNota.tipo_fruta_id" class="w-full border border-gray-200 p-3.5 rounded-2xl text-sm outline-none"><option value="" disabled>Selecciona...</option><option v-for="f in tiposFruta" :value="f.id" :key="f.id">{{ f.nombre }}</option></select></div>
        </div>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-6 mb-6 border-t pt-6">
          <div><label class="block text-sm text-gray-500 mb-1">Cajas</label><input type="number" v-model="nuevaNota.cantidad_cajas" class="w-full border p-3.5 rounded-2xl text-sm outline-none" /></div>
          <div><label class="block text-sm text-gray-500 mb-1">Peso Neto (kg)</label><input type="number" step="0.1" v-model="nuevaNota.peso_neto" class="w-full border p-3.5 rounded-2xl text-sm outline-none" /></div>
          <div><label class="block text-sm text-gray-500 mb-1">Precio ($/kg)</label><input type="number" step="0.01" v-model="nuevaNota.precio_kg" class="w-full border p-3.5 rounded-2xl text-sm outline-none" /></div>
          <div><label class="block text-sm text-gray-500 mb-1">Total (Auto)</label><input type="text" disabled :value="'$' + nuevaNota.total_monetario" class="w-full bg-emerald-50 text-emerald-800 font-bold border p-3.5 rounded-2xl text-sm outline-none" /></div>
        </div>
        <button @click="agregarNota" :disabled="cargando" class="bg-emerald-500 text-white px-8 py-3.5 rounded-2xl text-sm font-medium hover:bg-emerald-600 disabled:opacity-50">Guardar Nota</button>
      </div>

      <div class="bg-white p-8 rounded-3xl shadow-sm border overflow-x-auto">
        <h2 class="text-xl font-medium mb-4 text-gray-700">Bandeja de Notas Libres</h2>
        <table class="min-w-full text-left text-sm text-gray-600">
          <thead class="bg-gray-50 border-b"><tr><th class="p-3">Folio</th><th class="p-3">Estado</th><th class="p-3">Proveedor</th><th class="p-3">Fruta</th><th class="p-3 text-right">Peso Neto</th><th class="p-3 text-right">Total</th><th class="p-3 text-right">Acción</th></tr></thead>
          <tbody>
            <tr v-for="n in notasLibres" :key="n.id" class="border-b hover:bg-gray-50">
              <td class="p-3 font-mono font-bold text-gray-800">{{ n.folio || 'S/F' }}</td>
              <td class="p-3"><span class="bg-orange-100 text-orange-700 px-2 py-1 rounded text-xs font-bold">POR CONCILIAR</span></td>
              <td class="p-3 font-medium text-gray-800">{{ n.proveedor_nombre }}</td><td class="p-3">{{ n.fruta_nombre }}</td>
              <td class="p-3 text-right">{{ formatearPeso(n.peso_neto) }} kg</td><td class="p-3 text-right font-bold text-emerald-600">${{ n.total_monetario }}</td>
              <td class="p-3 text-right">
                <button @click="prepararEdicionNota(n)" class="text-blue-500 font-bold mr-3 hover:text-blue-700">✏️ Editar</button>
                <button @click="eliminarNota(n.id)" :disabled="cargando" class="text-red-500 hover:text-red-700 font-medium disabled:opacity-50">Eliminar</button>
              </td>
            </tr>
            <tr v-if="notasLibres.length === 0"><td colspan="7" class="p-6 text-center text-gray-400">No hay notas libres para conciliar.</td></tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="pestanaActual === 'conciliacion'" class="animate-fade-in">
       <div v-if="vistaConciliacion === 'historial'" class="space-y-6">
        <div class="flex justify-between items-center bg-white p-6 rounded-3xl border"><input type="date" v-model="fechaFiltroConciliacion" class="border p-3 rounded-xl outline-none" /><button @click="iniciarNuevaConciliacion" class="bg-emerald-500 text-white px-8 py-3.5 rounded-2xl font-bold">+ Conciliar Nuevo</button></div>
        <div class="bg-white p-8 rounded-3xl border overflow-x-auto">
          <table class="min-w-full text-left text-sm text-gray-600"><thead class="bg-gray-50 border-b"><tr><th class="p-3">Viaje</th><th class="p-3">Acopiador</th><th class="p-3 text-right">Físico</th><th class="p-3 text-right">Teórico</th><th class="p-3 text-right">Diferencia</th><th class="p-3 text-center">Gestión</th></tr></thead>
            <tbody>
              <tr v-for="v in viajesConciliadosFiltrados" :key="v.id" class="border-b">
                <td class="p-3 font-bold">#{{ v.id }}</td>
                <td class="p-3">{{ nombreAcopiador(v.acopiador_id) }}</td>
                <td class="p-3 text-right text-blue-600">{{ formatearPeso(v.peso_total_fisico) }} kg</td>
                <td class="p-3 text-right text-orange-600">{{ formatearPeso(v.peso_total_teorico) }} kg</td>
                <td class="p-3 text-right font-bold" :class="v.diferencia_peso >= 0 ? 'text-emerald-500' : 'text-red-500'">{{ v.diferencia_peso > 0 ? '+' : ''}}{{ formatearPeso(v.diferencia_peso) }} kg</td>
                <td class="p-3 text-center"><button @click="deshacerConciliacion(v.id)" class="bg-orange-50 text-orange-600 border border-orange-200 px-3 py-1 rounded-lg text-xs font-bold hover:bg-orange-100 transition">⚠️ Deshacer</button></td>
              </tr>
              <tr v-if="viajesConciliadosFiltrados.length === 0"><td colspan="6" class="p-6 text-center text-gray-400">No hay viajes conciliados en esta fecha.</td></tr>
            </tbody>
          </table>
        </div>
      </div>
      <div v-if="vistaConciliacion === 'formulario'" class="space-y-6">
        <button @click="vistaConciliacion = 'historial'" class="text-gray-500 font-medium">← Cancelar y Volver</button>
        <div class="bg-white p-6 rounded-3xl border"><select v-model="viajeAConciliarId" class="w-full border p-4 rounded-2xl text-lg font-medium outline-none"><option value="" disabled>-- Elige un viaje cerrado --</option><option v-for="v in viajesCerradosParaConciliar" :value="v.id" :key="v.id">{{ formatoViajeSelect(v) }}</option></select></div>
        <div v-if="detallesViajeAConciliar" class="grid grid-cols-2 gap-6">
          <div class="bg-white p-6 rounded-3xl border text-center"><span class="text-blue-600 block mb-1 font-bold">Peso Físico (Báscula)</span><span class="text-4xl font-black text-blue-700">{{ formatearPeso(detallesViajeAConciliar.pesoFisicoTotal) }} kg</span></div>
          <div class="bg-white p-6 rounded-3xl border text-center"><span class="text-orange-600 block mb-1 font-bold">Peso Teórico (Notas)</span><span class="text-4xl font-black text-orange-700">{{ formatearPeso(pesoTeoricoSeleccionado) }} kg</span></div>
        </div>
        <div v-if="detallesViajeAConciliar" class="bg-white p-6 rounded-3xl border">
          <h3 class="font-bold text-gray-700 mb-4">Selecciona las notas que amparan este viaje:</h3>
          <div class="space-y-2 max-h-60 overflow-y-auto pr-2">
            <label v-for="n in notasLibres" :key="n.id" class="flex items-center p-4 bg-gray-50 rounded-xl cursor-pointer border hover:bg-emerald-50 transition">
              <input type="checkbox" :value="n.id" v-model="notasSeleccionadasParaConciliar" class="w-6 h-6 text-emerald-500 mr-4 rounded">
              <div class="flex-1"><p class="text-sm font-bold text-gray-800">Folio: {{n.folio}} | {{ n.proveedor_nombre }}</p></div><div class="font-bold text-orange-600 text-lg">{{ formatearPeso(n.peso_neto) }} kg</div>
            </label>
            <p v-if="notasLibres.length === 0" class="text-gray-400 italic">No hay notas libres disponibles.</p>
          </div>
        </div>
        <div v-if="detallesViajeAConciliar" class="bg-gray-800 p-8 rounded-3xl text-white flex flex-col md:flex-row justify-between items-center gap-6">
          <div><span class="text-gray-400 text-sm block mb-1">Diferencia Físico vs Teórico</span><div class="text-4xl font-black tracking-tight" :class="diferenciaConciliacion >= 0 ? 'text-emerald-400' : 'text-red-400'">{{ diferenciaConciliacion > 0 ? '+' : '' }}{{ formatearPeso(diferenciaConciliacion) }} kg</div></div>
          <button @click="guardarConciliacion" :disabled="cargando" class="w-full md:w-auto bg-emerald-500 hover:bg-emerald-400 px-10 py-4 rounded-2xl font-bold text-lg transition shadow-lg disabled:opacity-50">Aprobar Conciliación</button>
        </div>
      </div>
    </div>

    <div v-if="pestanaActual === 'pagos'" class="space-y-8 animate-fade-in">
      <div class="flex justify-between items-center"><h2 class="text-2xl font-light text-gray-700">Gestión de Pagos</h2><button @click="abrirModalPagos" class="bg-emerald-500 text-white px-6 py-3 rounded-2xl font-bold shadow-sm">+ Registrar Pago</button></div>
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        <div class="bg-white p-6 rounded-3xl border overflow-x-auto shadow-sm">
          <h3 class="text-lg font-bold text-orange-600 mb-4 border-b pb-2">Deudas por Proveedor</h3>
          
          <div class="bg-orange-50 border border-orange-100 p-5 rounded-2xl mb-4 flex justify-between items-center">
            <span class="text-orange-800 font-bold">Deuda Global Total:</span>
            <span class="text-3xl font-black text-orange-600">${{ totalDeudaPendiente }}</span>
          </div>
          
          <div class="space-y-3">
            <div v-for="prov in deudasAgrupadas" :key="prov.id" class="border rounded-2xl overflow-hidden shadow-sm">
              
              <button @click="proveedorExpandido = proveedorExpandido === prov.id ? null : prov.id" 
                      class="w-full flex justify-between items-center p-4 bg-gray-50 hover:bg-gray-100 transition">
                <span class="font-bold text-gray-800 text-lg">{{ prov.nombre }}</span>
                <div class="flex items-center gap-4">
                  <span class="text-xl font-black text-orange-600">${{ prov.totalDeuda.toFixed(2) }}</span>
                  <span class="text-gray-400 font-bold text-sm">{{ proveedorExpandido === prov.id ? '▲' : '▼' }}</span>
                </div>
              </button>
              
              <div v-if="proveedorExpandido === prov.id" class="p-4 bg-white border-t border-gray-100 animate-fade-in">
                <table class="w-full text-sm text-left">
                  <thead>
                    <tr class="text-gray-400 border-b">
                      <th class="pb-2">Fecha</th>
                      <th class="pb-2">Folio Nota</th>
                      <th class="pb-2">Fruta</th>
                      <th class="pb-2 text-right">Monto</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="nota in prov.notas" :key="nota.id" class="border-b last:border-0 hover:bg-gray-50 transition">
                      <td class="py-2 text-gray-500 font-medium">
                        {{ nota.fecha ? new Date(nota.fecha).toLocaleDateString() : 'S/F' }}
                      </td>
                      <td class="py-2 font-mono font-bold text-gray-700">{{ nota.folio }}</td>
                      <td class="py-2">{{ nota.fruta_nombre }}</td>
                      <td class="py-2 text-right font-bold text-gray-800">${{ nota.total_monetario }}</td>
                    </tr>
                  </tbody>
                </table>
                
                <div class="mt-4 flex justify-end">
                    <button @click="nuevoPago.proveedor_id = prov.id; abrirModalPagos()" 
                            class="text-xs bg-emerald-100 text-emerald-700 px-3 py-1 rounded-lg font-bold hover:bg-emerald-200">
                        Preparar Liquidación
                    </button>
                </div>
              </div>
            </div>

            <div v-if="deudasAgrupadas.length === 0" class="text-center py-6 text-gray-400 italic">
                No hay deudas pendientes en el sistema.
            </div>
          </div>
        </div>

        <div class="bg-white p-6 rounded-3xl border overflow-x-auto shadow-sm">
          <h3 class="text-lg font-bold text-emerald-600 mb-4 border-b pb-2">Últimos Pagos Realizados</h3>
          <table class="min-w-full text-left text-sm text-gray-600">
            <thead><tr><th class="pb-2">Fecha</th><th class="pb-2">Proveedor</th><th class="pb-2 text-right">Monto</th><th class="pb-2 text-center">Acción</th></tr></thead>
            <tbody>
              <tr v-for="p in pagos.slice().reverse()" :key="p.id" class="border-t hover:bg-gray-50 transition">
                <td class="py-3 text-xs font-bold text-gray-500">{{ p.fecha_pago ? new Date(p.fecha_pago).toLocaleDateString() : 'N/A' }}</td>
                <td class="py-3 font-medium">{{ p.proveedor_nombre }} <span class="block text-[10px] text-gray-400 font-mono">{{ p.folio_pago }}</span></td>
                <td class="py-3 text-right font-bold text-emerald-600">${{ p.monto_total }}</td>
                <td class="py-3 text-center"><button @click="abrirDetallePago(p)" class="bg-blue-50 text-blue-600 px-3 py-1.5 rounded-lg text-xs font-bold hover:bg-blue-100 transition">Ver Detalle</button></td>
              </tr>
              <tr v-if="pagos.length === 0"><td colspan="4" class="text-center py-6 text-gray-400">Aún no hay pagos registrados.</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div v-if="mostrarModalPago" class="fixed inset-0 bg-gray-900 bg-opacity-60 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
      <div class="bg-white rounded-3xl w-full max-w-2xl p-8 max-h-[90vh] overflow-y-auto shadow-2xl">
        <h2 class="text-2xl font-bold mb-6 text-gray-800">Generar Liquidación / Pago</h2>
        <div class="grid grid-cols-2 gap-5 mb-6">
          <select v-model="nuevoPago.proveedor_id" @change="nuevoPago.nota_ids = []" class="w-full border border-gray-300 p-3.5 rounded-2xl outline-none focus:ring-2 focus:ring-emerald-400 font-medium">
            <option value="" disabled>Selecciona Proveedor...</option>
            <option v-for="p in proveedores" :value="p.id" :key="p.id">{{ p.nombre }}</option>
          </select>
          <input type="date" v-model="nuevoPago.fecha_pago" class="w-full border border-gray-300 p-3.5 rounded-2xl outline-none focus:ring-2 focus:ring-emerald-400 font-medium" />
        </div>
        <div class="mb-6">
          <input v-model="nuevoPago.folio_pago" placeholder="Referencia bancaria o Folio interno de pago" class="w-full border border-gray-300 p-3.5 rounded-2xl uppercase outline-none focus:ring-2 focus:ring-emerald-400 font-bold" />
        </div>
        <div v-if="nuevoPago.proveedor_id" class="border-t pt-4">
          <p class="text-sm font-bold text-gray-500 mb-2">Selecciona las notas a liquidar:</p>
          <div class="max-h-40 overflow-y-auto space-y-2 mb-6 bg-gray-50 p-3 rounded-2xl border border-gray-100">
            <label v-for="n in notasDelProveedorSeleccionado" :key="n.id" class="flex items-center p-3 bg-white rounded-xl cursor-pointer border hover:border-emerald-300 transition shadow-sm">
              <input type="checkbox" :value="n.id" v-model="nuevoPago.nota_ids" class="w-5 h-5 text-emerald-500 mr-4 rounded">
              <div class="flex-1"><p class="text-sm font-bold text-gray-800">Folio Nota: {{n.folio}}</p></div><div class="font-black text-orange-600">${{ n.total_monetario }}</div>
            </label>
            <p v-if="notasDelProveedorSeleccionado.length === 0" class="text-center text-sm text-gray-400 py-2">Este proveedor no tiene notas pendientes.</p>
          </div>
          <div class="bg-emerald-50 p-6 rounded-3xl flex justify-between items-center border border-emerald-100"><span class="text-emerald-800 font-bold text-lg">Total a Liquidar:</span><span class="text-4xl font-black text-emerald-600">${{ nuevoPago.monto_total }}</span></div>
        </div>
        <div class="mt-8 flex gap-4"><button @click="mostrarModalPago = false" class="flex-1 bg-gray-100 py-4 rounded-2xl font-bold text-gray-600 hover:bg-gray-200 transition">Cancelar</button><button @click="registrarPago" :disabled="cargando || nuevoPago.monto_total <= 0" class="flex-1 bg-emerald-500 text-white py-4 rounded-2xl font-bold text-lg hover:bg-emerald-400 transition shadow-md disabled:opacity-50">Procesar Pago</button></div>
      </div>
    </div>

    <div v-if="mostrarModalDetallePago" class="fixed inset-0 bg-gray-900 bg-opacity-60 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
      <div class="bg-white rounded-3xl w-full max-w-2xl p-8 max-h-[90vh] overflow-y-auto shadow-2xl">
        <div class="flex justify-between items-start mb-6 border-b pb-4">
          <div>
            <h2 class="text-2xl font-black text-gray-800">Detalle de Pago</h2>
            <p class="text-gray-500 font-medium">{{ pagoSeleccionado.proveedor_nombre }}</p>
          </div>
          <button @click="modoEdicionPago = !modoEdicionPago" :class="modoEdicionPago ? 'bg-blue-500 text-white' : 'bg-gray-100 text-blue-600'" class="px-4 py-2 rounded-xl font-bold transition">
            {{ modoEdicionPago ? 'Cancelar Edición' : '✏️ Editar Datos' }}
          </button>
        </div>

        <div class="grid grid-cols-2 gap-6 mb-6">
          <div v-if="!modoEdicionPago" class="col-span-2 flex gap-6 p-4 bg-gray-50 rounded-2xl border">
            <div class="flex-1"><span class="block text-xs text-gray-400 font-bold uppercase">Folio / Referencia</span><span class="font-mono font-bold text-lg">{{ pagoSeleccionado.folio_pago }}</span></div>
            <div class="flex-1"><span class="block text-xs text-gray-400 font-bold uppercase">Fecha</span><span class="font-bold text-lg">{{ pagoSeleccionado.fecha_pago ? new Date(pagoSeleccionado.fecha_pago).toLocaleDateString() : 'N/A' }}</span></div>
          </div>
          <template v-else>
            <div><label class="text-xs font-bold text-gray-500 uppercase ml-1">Folio / Referencia</label><input v-model="pagoEditando.folio_pago" class="border border-gray-300 p-3.5 rounded-2xl w-full uppercase outline-none focus:border-blue-400"></div>
            <div><label class="text-xs font-bold text-gray-500 uppercase ml-1">Fecha</label><input type="date" v-model="pagoEditando.fecha_pago" class="border border-gray-300 p-3.5 rounded-2xl w-full outline-none focus:border-blue-400"></div>
          </template>
        </div>

        <h3 class="font-bold text-gray-700 mb-3">Notas amparadas en este pago:</h3>
        <div class="max-h-48 overflow-y-auto mb-6 border rounded-2xl bg-white shadow-sm">
          <table class="min-w-full text-left text-sm">
            <thead class="bg-gray-50 border-b"><tr><th class="p-3">Folio Nota</th><th class="p-3">Fruta</th><th class="p-3 text-right">Peso</th><th class="p-3 text-right">Monto</th></tr></thead>
            <tbody>
              <tr v-for="n in notasDelPagoSeleccionado" :key="n.id" class="border-b">
                <td class="p-3 font-bold font-mono">{{ n.folio }}</td><td class="p-3">{{ n.fruta_nombre }}</td>
                <td class="p-3 text-right">{{ formatearPeso(n.peso_neto) }} kg</td><td class="p-3 text-right font-bold text-emerald-600">${{ n.total_monetario }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="flex justify-between items-center mb-8">
          <button @click="anularPago" class="text-red-500 hover:text-red-700 font-bold underline text-sm transition">❌ Anular Pago Completamente</button>
          <div class="text-right"><span class="block text-xs font-bold text-gray-400 uppercase">Total Pagado</span><span class="text-3xl font-black text-emerald-600">${{ pagoSeleccionado.monto_total }}</span></div>
        </div>

        <div class="flex gap-4 border-t pt-6">
          <button @click="mostrarModalDetallePago = false" class="flex-1 bg-gray-100 py-3.5 rounded-2xl font-bold text-gray-600 hover:bg-gray-200 transition">Cerrar</button>
          <button v-if="modoEdicionPago" @click="guardarEdicionPago" :disabled="cargando" class="flex-1 bg-blue-500 text-white py-3.5 rounded-2xl font-bold hover:bg-blue-400 transition shadow-md disabled:opacity-50">Guardar Cambios</button>
        </div>
      </div>
    </div>

    <div v-if="mostrarModalEdicionNota" class="fixed inset-0 bg-gray-900 bg-opacity-60 flex items-center justify-center p-4 z-50 backdrop-blur-sm">
      <div class="bg-white p-8 rounded-3xl w-full max-w-lg shadow-2xl">
        <h2 class="text-2xl font-bold mb-6 text-gray-800">Corregir Nota #{{editandoNota.id}}</h2>
        <div class="grid grid-cols-2 gap-5">
          <div class="col-span-2"><label class="text-xs font-bold text-gray-500 uppercase ml-1">Folio Físico</label><input v-model="editandoNota.folio" class="border border-gray-300 p-3.5 rounded-2xl w-full font-bold uppercase outline-none focus:border-blue-400"></div>
          <div class="col-span-2"><label class="text-xs font-bold text-gray-500 uppercase ml-1">Proveedor</label><select v-model="editandoNota.proveedor_id" class="w-full border border-gray-300 p-3.5 rounded-2xl outline-none focus:border-blue-400"><option v-for="p in proveedores" :value="p.id" :key="p.id">{{ p.nombre }}</option></select></div>
          <div class="col-span-2"><label class="text-xs font-bold text-gray-500 uppercase ml-1">Fruta</label><select v-model="editandoNota.tipo_fruta_id" class="w-full border border-gray-300 p-3.5 rounded-2xl outline-none focus:border-blue-400"><option v-for="f in tiposFruta" :value="f.id" :key="f.id">{{ f.nombre }}</option></select></div>
          <div><label class="text-xs font-bold text-gray-500 uppercase ml-1">Cajas</label><input type="number" v-model="editandoNota.cantidad_cajas" class="border border-gray-300 p-3.5 rounded-2xl w-full outline-none focus:border-blue-400"></div>
          <div><label class="text-xs font-bold text-gray-500 uppercase ml-1">Peso Neto (kg)</label><input type="number" step="0.1" v-model="editandoNota.peso_neto" class="border border-gray-300 p-3.5 rounded-2xl w-full outline-none focus:border-blue-400"></div>
          <div class="col-span-2"><label class="text-xs font-bold text-gray-500 uppercase ml-1">Precio Unitario ($/kg)</label><input type="number" step="0.01" v-model="editandoNota.precio_kg" class="border border-gray-300 p-3.5 rounded-2xl w-full outline-none focus:border-blue-400"></div>
        </div>
        <div class="mt-8 flex gap-4">
          <button @click="mostrarModalEdicionNota = false" class="flex-1 bg-gray-100 py-3.5 rounded-2xl font-bold text-gray-600 hover:bg-gray-200 transition">Cancelar</button>
          <button @click="guardarCambiosNota" class="flex-1 bg-blue-500 text-white py-3.5 rounded-2xl font-bold hover:bg-blue-400 transition shadow-md">Guardar Corrección</button>
        </div>
      </div>
    </div>

    <div v-if="mostrarModalEdicionCatalogo" class="fixed inset-0 bg-gray-900 bg-opacity-60 flex items-center justify-center p-4 z-50 backdrop-blur-sm">
      <div class="bg-white p-8 rounded-3xl w-full max-w-sm shadow-2xl">
        <h2 class="text-2xl font-bold mb-6 text-gray-800 capitalize">Editar {{tipoCatalogoEdicion.replace('-', ' ')}}</h2>
        <div class="space-y-5">
          <div><label class="text-xs font-bold text-gray-500 uppercase ml-1">Nombre</label><input v-model="itemEditando.nombre" class="border border-gray-300 p-3.5 rounded-2xl w-full font-medium outline-none focus:border-blue-400"></div>
          <div v-if="tipoCatalogoEdicion === 'acopiadores'"><label class="text-xs font-bold text-gray-500 uppercase ml-1">Teléfono</label><input v-model="itemEditando.telefono" class="border border-gray-300 p-3.5 rounded-2xl w-full font-medium outline-none focus:border-blue-400"></div>
          <div v-if="tipoCatalogoEdicion === 'proveedores' || tipoCatalogoEdicion === 'clientes'"><label class="text-xs font-bold text-gray-500 uppercase ml-1">Contacto</label><input v-model="itemEditando.contacto" class="border border-gray-300 p-3.5 rounded-2xl w-full font-medium outline-none focus:border-blue-400"></div>
          <div v-if="tipoCatalogoEdicion === 'tipos-fruta'"><label class="text-xs font-bold text-gray-500 uppercase ml-1">Descripción</label><input v-model="itemEditando.descripcion" class="border border-gray-300 p-3.5 rounded-2xl w-full font-medium outline-none focus:border-blue-400"></div>
        </div>
        <div class="mt-8 flex gap-4">
          <button @click="mostrarModalEdicionCatalogo = false" class="flex-1 bg-gray-100 py-3.5 rounded-2xl font-bold text-gray-600 hover:bg-gray-200 transition">Cancelar</button>
          <button @click="guardarEdicionCatalogo" class="flex-1 bg-blue-500 text-white py-3.5 rounded-2xl font-bold hover:bg-blue-400 transition shadow-md">Actualizar</button>
        </div>
      </div>
    </div>

  </div>
</template>

<style>
.animate-fade-in { animation: fadeIn 0.3s ease-out; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
</style>