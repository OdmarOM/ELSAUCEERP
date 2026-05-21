<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'

const API_URL = 'http://127.0.0.1:8000/api'
 //const API_URL = 'http://192.168.50.101:8000/api'
const moduloActual = ref('bascula') // 'bascula' o 'frio'
const vistaActual = ref('lista')

const cargando = ref(false)

const acopiadores = ref([])
const clientes = ref([])
const tiposFruta = ref([])
const viajes = ref([])
const registros = ref([]) 
const ubicacionesFrio = ref([])
const viajeSeleccionado = ref(null)
const mostrarModalViaje = ref(false)

// NUEVO: Filtro de fecha para viajes
const fechaFiltroViajes = ref(new Date().toISOString().split('T')[0])

// NUEVO: Modal Edición Tarima
const mostrarModalEditarTarima = ref(false)
const tarimaEditando = ref({})

const nuevoViaje = ref({ tipo_operacion: 'ACOPIO', acopiador_id: '', cliente_id: '', placa: '' })
const nuevaPesada = ref({ tipo_fruta_id: '', cantidad_cajas: 42, tara_caja: 1.7, cantidad_tarimas: 1, tara_tarima: 21.0, peso_bruto: '', promedio_peso_caja: 0.0 })

const formatearPeso = (valor) => {
  return parseFloat(valor || 0).toFixed(2);
}

// ================= LECTURA DE BÁSCULA ESP32 =================
const pesoLectura = ref(0.0)
const basculaConectada = ref(false)
let intervaloLectura = null

const conectarBascula = () => {
  if (basculaConectada.value) {
    clearInterval(intervaloLectura)
    basculaConectada.value = false
    return
  }
  
  basculaConectada.value = true
  intervaloLectura = setInterval(async () => {
    try {
      const res = await fetch(`${API_URL}/bascula/peso-actual`)
      const data = await res.json()
      if (data.peso !== undefined && viajeSeleccionado.value) {
        nuevaPesada.value.peso_bruto = data.peso
      }
    } catch (e) {
      console.error("Error leyendo báscula", e)
    }
  }, 1000)
}

onUnmounted(() => {
  if (intervaloLectura) clearInterval(intervaloLectura)
})

const taraTotalCalculada = computed(() => (parseFloat(nuevaPesada.value.cantidad_cajas || 0) * parseFloat(nuevaPesada.value.tara_caja || 0)) + (parseFloat(nuevaPesada.value.cantidad_tarimas || 0) * parseFloat(nuevaPesada.value.tara_tarima || 0)))
const pesoNetoCalculado = computed(() => Math.max(0, (parseFloat(nuevaPesada.value.peso_bruto || 0) - taraTotalCalculada.value)).toFixed(2))

const fetchCatalogos = async () => {
  try {
    const [resAcop, resProv, resCli, resFruta, resViajes, resRegistros, resFrio] = await Promise.all([
      fetch(`${API_URL}/acopiadores`), fetch(`${API_URL}/proveedores`), fetch(`${API_URL}/clientes`), fetch(`${API_URL}/tipos-fruta`), 
      fetch(`${API_URL}/viajes`), fetch(`${API_URL}/registros-bascula`), fetch(`${API_URL}/cuarto-frio`)
    ])
    acopiadores.value = await resAcop.json(); clientes.value = await resCli.json(); tiposFruta.value = await resFruta.json(); 
    viajes.value = await resViajes.json(); registros.value = await resRegistros.json(); ubicacionesFrio.value = await resFrio.json();
  } catch (e) { console.error('Error:', e) }
}

onMounted(() => fetchCatalogos())

// ================= BASCULA LÓGICA =================
const viajesDelDia = computed(() => {
  return viajes.value.filter(v => v.fecha_entrada.startsWith(fechaFiltroViajes.value)).sort((a, b) => b.id - a.id)
})

const nombreResponsableViaje = (v) => {
  if (v.tipo_operacion === 'MAQUILA') return clientes.value.find(c => c.id === v.cliente_id)?.nombre || 'Cliente Desconocido'
  return acopiadores.value.find(a => a.id === v.acopiador_id)?.nombre || 'Acopiador Desconocido'
}

const abrirModalViaje = () => { nuevoViaje.value = { tipo_operacion: 'ACOPIO', acopiador_id: '', cliente_id: '', placa: '' }; mostrarModalViaje.value = true }

const registrarViaje = async () => { 
  if (nuevoViaje.value.tipo_operacion === 'ACOPIO' && !nuevoViaje.value.acopiador_id) return alert("Selecciona un acopiador");
  if (nuevoViaje.value.tipo_operacion === 'MAQUILA' && !nuevoViaje.value.cliente_id) return alert("Selecciona un cliente");

  cargando.value = true; 
  try { 
    const payload = {
      tipo_operacion: nuevoViaje.value.tipo_operacion,
      placa: nuevoViaje.value.tipo_operacion === 'ACOPIO' ? nuevoViaje.value.placa : 'N/A', 
      acopiador_id: nuevoViaje.value.tipo_operacion === 'ACOPIO' ? parseInt(nuevoViaje.value.acopiador_id) : null,
      cliente_id: nuevoViaje.value.tipo_operacion === 'MAQUILA' ? parseInt(nuevoViaje.value.cliente_id) : null
    };

    const res = await fetch(`${API_URL}/viajes`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }); 
    if (!res.ok) { alert("Hubo un error al guardar. Revisa la consola."); return; }

    const viajeCreado = await res.json(); 
    mostrarModalViaje.value = false; await fetchCatalogos(); abrirDetalleViaje(viajeCreado); 
  } catch (error) { alert("Error de conexión con el servidor."); } finally { cargando.value = false; } 
}

const abrirDetalleViaje = (viaje) => { viajeSeleccionado.value = viaje; vistaActual.value = 'detalle'; nuevaPesada.value = { tipo_fruta_id: '', cantidad_cajas: 42, tara_caja: 1.7, cantidad_tarimas: 1, tara_tarima: 21.0, peso_bruto: '', promedio_peso_caja: 0.0 } }
const cerrarViaje = async () => { if (!confirm("¿Cerrar viaje?")) return; cargando.value = true; try { await fetch(`${API_URL}/viajes/${viajeSeleccionado.value.id}/cerrar`, { method: 'PUT' }); await fetchCatalogos(); vistaActual.value = 'lista'; viajeSeleccionado.value = null } finally { cargando.value = false } }
const registrosDelViaje = computed(() => { if (!viajeSeleccionado.value) return []; return registros.value.filter(t => t.viaje_id === viajeSeleccionado.value.id).sort((a, b) => b.id - a.id) })

const registrarPesada = async () => { 
  cargando.value = true; 
  try { 
    const payload = { 
      ...nuevaPesada.value, 
      viaje_id: viajeSeleccionado.value.id, 
      maquila_id: viajeSeleccionado.value.tipo_operacion === 'MAQUILA' ? 1 : null, 
      numero_tarima: registrosDelViaje.value.length + 1, 
      tara_total: taraTotalCalculada.value, 
      peso_neto: pesoNetoCalculado.value, 
      promedio_peso_caja: nuevaPesada.value.cantidad_cajas > 0 ? (pesoNetoCalculado.value / nuevaPesada.value.cantidad_cajas) : 0 
    }; 
    await fetch(`${API_URL}/registros-bascula`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) }); 
    nuevaPesada.value.peso_bruto = ''; await fetchCatalogos() 
  } finally { cargando.value = false } 
}

// ================= CUARTO FRÍO Y BODEGA LÓGICA =================
// MODIFICADO: 5 FILAS x 10 COLUMNAS (Orientación Horizontal)
const FILAS = 5
const COLUMNAS = 10

const tarimasEnBodega = computed(() => {
  return registros.value
    .filter(r => r.estado_ubicacion === 'EN_BODEGA')
    .map(r => {
      const viaje = viajes.value.find(v => v.id === r.viaje_id);
      const d = viaje ? new Date(viaje.fecha_entrada) : new Date();
      const es_maquila = viaje?.tipo_operacion === 'MAQUILA';
      
      let nombre_dueno = 'Desconocido'
      if (es_maquila) {
         nombre_dueno = clientes.value.find(c => c.id === viaje.cliente_id)?.nombre || 'MAQUILA'
      } else {
         nombre_dueno = acopiadores.value.find(a => a.id === viaje?.acopiador_id)?.nombre || 'ACOPIO'
      }

      return {
        ...r,
        es_maquila,
        nombre_dueno,
        fecha_viaje: d.toLocaleDateString(),
        fruta_nombre: tiposFruta.value.find(f => f.id === r.tipo_fruta_id)?.nombre || 'N/A'
      }
    })
    .sort((a, b) => b.id - a.id)
})

const modalAsignarVacio = ref(false)
const modalOpcionesOcupado = ref(false)
const celdaSeleccionada = ref({ x: 0, y: 0 })
const tarimaAAsignarId = ref('')
const tarimaOcupadaSeleccionada = ref(null)
const modoReubicar = ref(false)

const detallesTarimaOcupada = computed(() => {
  if(!tarimaOcupadaSeleccionada.value) return null;
  const viaje = viajes.value.find(v => v.id === tarimaOcupadaSeleccionada.value.viaje_id);
  const es_maquila = viaje?.tipo_operacion === 'MAQUILA';
  let nombre_dueno = 'Desconocido'
  
  if (es_maquila) {
     nombre_dueno = clientes.value.find(c => c.id === viaje.cliente_id)?.nombre || 'MAQUILA'
  } else {
     nombre_dueno = acopiadores.value.find(a => a.id === viaje?.acopiador_id)?.nombre || 'ACOPIO'
  }

  return {
    ...tarimaOcupadaSeleccionada.value,
    nombre_dueno,
    es_maquila,
    fecha_viaje: viaje ? new Date(viaje.fecha_entrada).toLocaleDateString() : 'N/A'
  }
})

const matrizFrio = computed(() => {
  let grid = []
  for(let y=1; y<=FILAS; y++) {
    let row = []
    for(let x=1; x<=COLUMNAS; x++) {
      let celdaOcupada = null
      const original = ubicacionesFrio.value.find(u => u.fila_x === x && u.columna_y === y)
      
      if (original) {
        celdaOcupada = { ...original } 
        const registro = registros.value.find(r => r.id === celdaOcupada.tarima_id)
        celdaOcupada.peso_neto = registro ? registro.peso_neto : 0
        celdaOcupada.numero_tarima = registro ? registro.numero_tarima : '?'
        celdaOcupada.tipo_fruta_id = registro ? registro.tipo_fruta_id : null
        celdaOcupada.fruta_nombre = registro ? (tiposFruta.value.find(f => f.id === registro.tipo_fruta_id)?.nombre || 'N/A') : 'N/A'
        
        const viaje = viajes.value.find(v => v.id === registro?.viaje_id)
        if (viaje) {
          const d = new Date(viaje.fecha_entrada)
          celdaOcupada.fecha_corta = `${d.getDate().toString().padStart(2, '0')}/${(d.getMonth() + 1).toString().padStart(2, '0')}`
          celdaOcupada.es_maquila = viaje.tipo_operacion === 'MAQUILA'
          celdaOcupada.viaje_id = viaje.id
          if (celdaOcupada.es_maquila) {
            celdaOcupada.nombre_dueno = clientes.value.find(c => c.id === viaje.cliente_id)?.nombre || 'MAQUILA'
          } else {
            celdaOcupada.nombre_dueno = acopiadores.value.find(a => a.id === viaje.acopiador_id)?.nombre || 'ACOPIO'
          }
        }
      }
      row.push({ x, y, ocupada: celdaOcupada })
    }
    grid.push(row)
  }
  return grid
})

const colorClasesPorViaje = (viajeId, esMaquila) => {
  if (esMaquila) return 'bg-purple-800 border-purple-500 text-white'
  const colores = ['bg-blue-600 border-blue-400 text-white', 'bg-emerald-600 border-emerald-400 text-white', 'bg-orange-600 border-orange-400 text-white', 'bg-pink-600 border-pink-400 text-white', 'bg-cyan-600 border-cyan-400 text-white', 'bg-indigo-600 border-indigo-400 text-white']
  return colores[(viajeId || 0) % colores.length]
}

// Color base para el encabezado del modal de detalle
const colorCabeceraModal = (viajeId, esMaquila) => {
  if (esMaquila) return 'bg-purple-100 text-purple-800'
  const colores = ['bg-blue-100 text-blue-800', 'bg-emerald-100 text-emerald-800', 'bg-orange-100 text-orange-800', 'bg-pink-100 text-pink-800', 'bg-cyan-100 text-cyan-800', 'bg-indigo-100 text-indigo-800']
  return colores[(viajeId || 0) % colores.length]
}

const manejarClickCelda = (celda) => {
  celdaSeleccionada.value = { x: celda.x, y: celda.y }
  if(modoReubicar.value) { if(celda.ocupada) return alert("Esa posición ya está ocupada."); moverTarima(celda.x, celda.y); return; }
  if (celda.ocupada) { tarimaOcupadaSeleccionada.value = celda.ocupada; modalOpcionesOcupado.value = true } 
  else { tarimaAAsignarId.value = ''; modalAsignarVacio.value = true }
}

const asignarNuevaTarima = async () => {
  if(!tarimaAAsignarId.value) return;
  cargando.value = true
  try {
    const res = await fetch(`${API_URL}/cuarto-frio`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ tarima_id: tarimaAAsignarId.value, fila_x: celdaSeleccionada.value.x, columna_y: celdaSeleccionada.value.y }) })
    if(!res.ok) alert((await res.json()).detail)
    modalAsignarVacio.value = false; await fetchCatalogos()
  } finally { cargando.value = false }
}

const retirarTarima = async (destino) => {
  cargando.value = true; try { await fetch(`${API_URL}/cuarto-frio/${tarimaOcupadaSeleccionada.value.tarima_id}?destino=${destino}`, { method: 'DELETE' }); modalOpcionesOcupado.value = false; await fetchCatalogos() } finally { cargando.value = false }
}

const prepararReubicacion = () => { modoReubicar.value = true; modalOpcionesOcupado.value = false }
const moverTarima = async (nueva_x, nueva_y) => {
  cargando.value = true; try { const res = await fetch(`${API_URL}/cuarto-frio/${tarimaOcupadaSeleccionada.value.tarima_id}/mover`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ fila_x: nueva_x, columna_y: nueva_y }) }); if(!res.ok) alert((await res.json()).detail); modoReubicar.value = false; tarimaOcupadaSeleccionada.value = null; await fetchCatalogos() } finally { cargando.value = false }
}
const cancelarReubicacion = () => { modoReubicar.value = false; tarimaOcupadaSeleccionada.value = null }

const abrirEdicionTarima = (tarima) => {
  tarimaEditando.value = { 
    id: tarima.tarima_id || tarima.id, 
    peso_neto: tarima.peso_neto, 
    tipo_fruta_id: tarima.tipo_fruta_id 
  }
  mostrarModalEditarTarima.value = true
}

const guardarEdicionTarima = async () => {
  cargando.value = true
  try {
    await fetch(`${API_URL}/registros-bascula/${tarimaEditando.value.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(tarimaEditando.value)
    })
    mostrarModalEditarTarima.value = false
    modalOpcionesOcupado.value = false
    await fetchCatalogos()
  } finally { cargando.value = false }
}

const pesadaEditandoViaje = ref({})
const mostrarModalEdicionPesada = ref(false)

const abrirEdicionPesada = (pesada) => {
  pesadaEditandoViaje.value = { ...pesada }
  mostrarModalEdicionPesada.value = true
}

const guardarEdicionPesada = async () => {
  cargando.value = true
  try {
    await fetch(`${API_URL}/registros-bascula/${pesadaEditandoViaje.value.id}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(pesadaEditandoViaje.value)
    })
    mostrarModalEdicionPesada.value = false
    await fetchCatalogos()
  } finally { cargando.value = false }
}

const eliminarPesada = async (id) => {
  if (!confirm("¿Estás seguro de eliminar esta pesada? Se borrará permanentemente.")) return
  cargando.value = true
  try {
    await fetch(`${API_URL}/registros-bascula/${id}`, { method: 'DELETE' })
    await fetchCatalogos()
  } finally { cargando.value = false }
}

// Edición de Viaje
const mostrarModalEdicionViaje = ref(false)
const viajeEditando = ref({})

const abrirEdicionViaje = () => {
  viajeEditando.value = { ...viajeSeleccionado.value }
  mostrarModalEdicionViaje.value = true
}

const guardarEdicionViaje = async () => {
  if (viajeEditando.value.tipo_operacion === 'ACOPIO' && !viajeEditando.value.acopiador_id) return alert("Selecciona un acopiador");
  if (viajeEditando.value.tipo_operacion === 'MAQUILA' && !viajeEditando.value.cliente_id) return alert("Selecciona un cliente");

  cargando.value = true
  try {
    const payload = {
      tipo_operacion: viajeEditando.value.tipo_operacion,
      placa: viajeEditando.value.tipo_operacion === 'ACOPIO' ? viajeEditando.value.placa : 'N/A', 
      acopiador_id: viajeEditando.value.tipo_operacion === 'ACOPIO' ? parseInt(viajeEditando.value.acopiador_id) : null,
      cliente_id: viajeEditando.value.tipo_operacion === 'MAQUILA' ? parseInt(viajeEditando.value.cliente_id) : null
    }
    
    await fetch(`${API_URL}/viajes/${viajeEditando.value.id}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
    })
    
    mostrarModalEdicionViaje.value = false
    await fetchCatalogos()
    // Actualizar la vista actual con los nuevos datos
    viajeSeleccionado.value = viajes.value.find(v => v.id === viajeEditando.value.id)
  } finally { cargando.value = false }
}

</script>

<template>
  <div class="min-h-screen bg-gray-50 p-4 md:p-8 relative">
    <div v-if="cargando" class="fixed inset-0 bg-white/60 backdrop-blur-sm z-50 flex items-center justify-center"><div class="bg-white p-6 rounded-3xl shadow-xl flex flex-col items-center"><div class="w-10 h-10 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin mb-3"></div><span class="text-gray-700 font-medium">Cargando...</span></div></div>

    <div class="flex justify-between items-center mb-6">
      <h1 class="text-3xl font-light text-gray-800 tracking-tight mt-1">Módulo Operativo</h1>
      <span class="text-xs font-bold text-gray-400 bg-white px-4 py-2 border rounded-full shadow-sm">ZONA A</span>
    </div>

    <div class="flex gap-4 mb-6">
      <button @click="moduloActual = 'bascula'" :class="moduloActual === 'bascula' ? 'bg-emerald-500 text-white' : 'bg-white text-gray-600'" class="px-6 py-3 rounded-2xl font-bold shadow-sm transition border">⚖️ Báscula de Recepción</button>
      <button @click="moduloActual = 'frio'" :class="moduloActual === 'frio' ? 'bg-blue-500 text-white' : 'bg-white text-gray-600'" class="px-6 py-3 rounded-2xl font-bold shadow-sm transition border">❄️ Cuarto Frío y Bodega</button>
    </div>

    <div v-if="moduloActual === 'frio'" class="animate-fade-in space-y-8">
      
      <div v-if="modoReubicar" class="bg-orange-100 border border-orange-300 p-4 rounded-2xl flex justify-between items-center animate-pulse">
        <span class="text-orange-800 font-bold">Modo Reubicación: Haz clic en un espacio vacío para mover la Tarima.</span>
        <button @click="cancelarReubicacion" class="bg-white text-orange-600 px-4 py-2 rounded-xl font-bold shadow-sm">Cancelar</button>
      </div>

      <div class="bg-white p-8 rounded-3xl shadow-sm border overflow-x-auto text-center md:text-left">
        <h2 class="text-xl font-bold text-blue-800 mb-6 flex items-center gap-2">❄️ Matriz del Cuarto Frío <span class="text-xs font-normal text-gray-500 ml-4">(10 Columnas x 5 Filas)</span></h2>
        
        <div class="inline-grid grid-cols-10 gap-2 w-full min-w-[800px]">
          <template v-for="fila in matrizFrio" :key="'fila-'+fila[0].y">
            <div v-for="celda in fila" :key="`celda-${celda.x}-${celda.y}`" 
                 @click="manejarClickCelda(celda)"
                 class="h-28 rounded-xl border-2 flex flex-col items-center justify-center cursor-pointer transition-all active:scale-95 relative overflow-hidden"
                 :class="[
                   celda.ocupada ? (colorClasesPorViaje(celda.ocupada.viaje_id, celda.ocupada.es_maquila) + ' shadow-md') : 'border-dashed hover:border-emerald-300',
                   // NUEVO: Resaltar columnas centrales (5 y 6) si NO están ocupadas
                   !celda.ocupada && (celda.x === 5 || celda.x === 6) ? 'bg-gray-200 border-gray-400' : (!celda.ocupada ? 'bg-gray-50 border-gray-300 hover:bg-emerald-50' : ''),
                   modoReubicar && celda.ocupada ? 'opacity-50 cursor-not-allowed' : ''
                 ]">
                 
                 <template v-if="celda.ocupada">
                   <div v-if="celda.ocupada.es_maquila" class="absolute top-0 left-0 bg-pink-500 text-white text-[8px] font-black px-1.5 py-0.5 rounded-br-lg z-10">MAQ</div>
                   <span class="text-[9px] uppercase font-black truncate w-full text-center px-1 opacity-90 mt-2 z-0">{{celda.ocupada.nombre_dueno}}</span>
                   <span class="text-base font-black leading-tight my-1">{{formatearPeso(celda.ocupada.peso_neto)}}</span>
                   <span class="text-[8px] font-bold">{{celda.ocupada.fecha_corta}} | T-#{{celda.ocupada.numero_tarima}}</span>
                   <span class="text-[8px] font-bold bg-black/20 px-1.5 py-0.5 rounded-full mt-1 mb-1 truncate max-w-[90%]">{{celda.ocupada.fruta_nombre}}</span>
                 </template>

                 <template v-else>
                    <span v-if="modoReubicar" class="text-orange-400 font-bold text-[10px] text-center px-1">Mover<br>Aquí</span>
                    <span v-else class="text-gray-400 font-mono text-[10px] font-bold">{{celda.x}}, {{celda.y}}</span>
                 </template>
            </div>
          </template>
        </div>
      </div>

      <div class="bg-white p-8 rounded-3xl shadow-sm border overflow-x-auto">
         <h2 class="text-xl font-bold text-orange-700 mb-6">🧱 Tarimas Físicas en Bodega</h2>
         <table class="min-w-full text-left text-sm text-gray-600">
           <thead class="bg-orange-50 text-orange-800 border-b border-orange-100">
             <tr><th class="p-3">Tarima</th><th class="p-3">Dueño</th><th class="p-3">Fruta</th><th class="p-3 text-right">Peso</th><th class="p-3 text-center">Acciones</th></tr>
           </thead>
           <tbody>
             <tr v-for="t in tarimasEnBodega" :key="t.id" class="border-b hover:bg-gray-50">
               <td class="p-3 font-bold text-gray-800">
                 T-#{{ t.numero_tarima }} 
                 <span v-if="t.es_maquila" class="bg-purple-100 text-purple-700 text-[9px] px-1 rounded ml-1 font-black">MAQUILA</span>
               </td>
               <td class="p-3 font-medium">{{ t.nombre_dueno }}</td>
               <td class="p-3">{{ t.fruta_nombre }}</td>
               <td class="p-3 text-right font-bold text-orange-600">{{ formatearPeso(t.peso_neto) }} kg</td>
               <td class="p-3 text-center">
                 <button @click="abrirEdicionTarima(t)" class="text-blue-500 hover:scale-110 transition mr-2">✏️</button>
               </td>
             </tr>
           </tbody>
         </table>
      </div>
    </div>

    <div v-if="mostrarModalEditarTarima" class="fixed inset-0 bg-gray-900 bg-opacity-50 flex items-center justify-center z-[60] p-4">
      <div class="bg-white rounded-3xl w-full max-w-sm p-8 text-center shadow-2xl">
        <h2 class="text-2xl font-bold mb-6 text-gray-800">Editar Tarima</h2>
        <div class="space-y-4 text-left">
          <div><label class="text-xs font-bold text-gray-400">PESO NETO (KG)</label><input type="number" step="0.1" v-model="tarimaEditando.peso_neto" class="w-full border p-3 rounded-xl font-bold text-lg outline-none focus:border-blue-500 text-gray-700"></div>
          <div><label class="text-xs font-bold text-gray-400">TIPO DE FRUTA</label><select v-model="tarimaEditando.tipo_fruta_id" class="w-full border p-3 rounded-xl outline-none focus:border-blue-500 text-gray-700 font-medium"><option v-for="f in tiposFruta" :value="f.id" :key="f.id">{{f.nombre}}</option></select></div>
        </div>
        <div class="flex gap-4 mt-8"><button @click="mostrarModalEditarTarima = false" class="flex-1 bg-gray-100 py-3 rounded-xl font-bold text-gray-600 hover:bg-gray-200 transition">Cancelar</button><button @click="guardarEdicionTarima" class="flex-1 bg-blue-500 text-white font-bold py-3 rounded-xl hover:bg-blue-600 transition shadow-md">Guardar</button></div>
      </div>
    </div>

    <div v-if="moduloActual === 'bascula'">
      <div v-if="vistaActual === 'lista'" class="space-y-6 animate-fade-in">
        <div class="flex flex-col md:flex-row justify-between items-center gap-4 bg-white p-6 rounded-3xl border shadow-sm">
          <div>
            <h2 class="text-xl font-bold text-gray-800">Viajes Registrados</h2>
            <p class="text-xs text-gray-400 uppercase font-black">Historial por Fecha</p>
          </div>
          <div class="flex items-center gap-4">
            <input type="date" v-model="fechaFiltroViajes" class="border p-3 rounded-2xl outline-none font-bold text-gray-700 focus:ring-2 focus:ring-emerald-400" />
            <button @click="abrirModalViaje" class="bg-emerald-500 text-white px-5 py-3 rounded-2xl shadow-sm font-bold">+ Nuevo Viaje</button>
          </div>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div v-for="(v, index) in viajesDelDia" :key="v.id" @click="abrirDetalleViaje(v)" class="bg-white p-6 rounded-3xl shadow-sm border cursor-pointer hover:shadow-md transition">
            <div class="flex justify-between items-start mb-4">
              <span class="text-xs font-bold text-gray-400">ID #{{v.id}}</span>
              <div class="flex gap-2">
                <span v-if="v.tipo_operacion === 'MAQUILA'" class="bg-purple-100 text-purple-700 px-3 py-0.5 rounded-full text-xs font-bold">MAQUILA</span>
                <span v-else class="bg-blue-100 text-blue-700 px-3 py-0.5 rounded-full text-xs font-bold">ACOPIO</span>
              </div>
            </div>
            <h3 class="text-lg font-bold text-gray-800 mb-1">{{ nombreResponsableViaje(v) }}</h3>
            <p class="text-gray-500 text-sm mb-4">Placa: <span class="font-mono text-gray-700">{{ v.placa }}</span></p>
            <div class="flex justify-between items-center border-t pt-4 mt-4">
              <span :class="v.estado === 'ACTIVO' ? 'text-emerald-600' : 'text-gray-500'" class="text-xs font-black uppercase">{{ v.estado }}</span>
              <span class="text-emerald-500 text-sm font-bold">Ver Detalles →</span>
            </div>
          </div>
          <div v-if="viajesDelDia.length === 0" class="col-span-full py-20 text-center text-gray-400 font-bold border-2 border-dashed rounded-3xl">No hay viajes registrados en esta fecha.</div>
        </div>
      </div>

      <div v-if="vistaActual === 'detalle' && viajeSeleccionado" class="space-y-6 animate-fade-in">
        <div class="flex flex-col md:flex-row justify-between bg-white p-6 rounded-3xl border gap-4">
          <div>
            <button @click="vistaActual = 'lista'; viajeSeleccionado = null;" class="bg-gray-100 px-4 py-2 rounded-xl mb-3 text-sm font-medium">← Volver</button>
            <div class="flex items-center gap-3"><h2 class="text-2xl font-light">Viaje <span class="font-medium font-mono">#{{ viajeSeleccionado.id }}</span></h2><span :class="viajeSeleccionado.tipo_operacion === 'MAQUILA' ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'" class="px-3 py-1 rounded-md text-xs font-bold">{{ viajeSeleccionado.tipo_operacion }}</span></div>
            <p class="text-sm text-gray-500 mt-2 font-bold">{{ nombreResponsableViaje(viajeSeleccionado) }}</p>
          </div>
          <div v-if="viajeSeleccionado.estado === 'ACTIVO'" class="flex gap-3">
            <button @click="abrirEdicionViaje" class="bg-blue-50 text-blue-600 px-5 py-2.5 rounded-2xl font-bold hover:bg-blue-100 transition">✏️ Editar Viaje</button>
            <button @click="cerrarViaje" class="bg-red-50 text-red-600 px-5 py-2.5 rounded-2xl font-bold hover:bg-red-100 transition">🔒 Finalizar</button>
          </div>
        </div>

        <div v-if="viajeSeleccionado.estado === 'ACTIVO'" class="bg-white p-8 rounded-3xl border max-w-2xl mx-auto shadow-sm">
          <div class="bg-blue-50 border border-blue-200 rounded-3xl p-6 text-center mb-6">
            <label class="block text-xs text-blue-500 font-bold uppercase mb-1">Peso Bruto (kg)</label>
            <div class="flex flex-col md:flex-row items-center justify-center gap-4 mt-2">
              <input type="number" step="0.5" v-model="nuevaPesada.peso_bruto" placeholder="0.00" class="bg-transparent text-center text-5xl font-black text-blue-600 outline-none font-mono w-64" />
              <button @click="conectarBascula" :class="basculaConectada ? 'bg-red-500 text-white' : 'bg-blue-500 text-white'" class="px-4 py-3 rounded-xl text-sm font-bold transition shadow-sm">
                {{ basculaConectada ? '🔴 Parar' : '🟢 Conectar' }}
              </button>
            </div>
          </div>
          
          <div class="space-y-5">
            <div>
              <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Tipo de Fruta</label>
              <select v-model="nuevaPesada.tipo_fruta_id" class="w-full bg-gray-50 border p-3.5 rounded-2xl outline-none font-bold text-gray-700 focus:ring-2 focus:ring-blue-400">
                <option v-for="f in tiposFruta" :value="f.id" :key="f.id">{{ f.nombre }}</option>
              </select>
            </div>

            <div class="grid grid-cols-2 gap-5 border-t pt-5">
              <div>
                <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Cajas Físicas</label>
                <input type="number" v-model="nuevaPesada.cantidad_cajas" class="w-full bg-gray-50 border p-3.5 rounded-2xl font-bold text-gray-700 outline-none focus:ring-2 focus:ring-blue-400" />
              </div>
              <div>
                <label class="block text-xs font-bold text-gray-500 uppercase mb-1">Tarimas</label>
                <input type="number" v-model="nuevaPesada.cantidad_tarimas" class="w-full bg-gray-50 border p-3.5 rounded-2xl font-bold text-gray-700 outline-none focus:ring-2 focus:ring-blue-400" />
              </div>
            </div>

            <div class="grid grid-cols-2 gap-5 border-t pt-5">
              <div>
                <label class="block text-xs font-bold text-orange-500 uppercase mb-1">Tara Caja (kg)</label>
                <input type="number" step="0.01" v-model="nuevaPesada.tara_caja" class="w-full bg-orange-50 border border-orange-100 p-3.5 rounded-2xl font-bold text-orange-700 outline-none focus:ring-2 focus:ring-orange-400" />
              </div>
              <div>
                <label class="block text-xs font-bold text-orange-500 uppercase mb-1">Tara Tarima (kg)</label>
                <input type="number" step="0.1" v-model="nuevaPesada.tara_tarima" class="w-full bg-orange-50 border border-orange-100 p-3.5 rounded-2xl font-bold text-orange-700 outline-none focus:ring-2 focus:ring-orange-400" />
              </div>
            </div>

            <div class="bg-gray-100 p-4 rounded-2xl flex justify-between items-center mt-4">
              <span class="text-xs font-bold text-gray-500 uppercase">Peso Neto a Guardar:</span>
              <span class="text-xl font-black text-gray-800">{{ pesoNetoCalculado }} kg</span>
            </div>
          </div>

          <div class="mt-8">
            <button @click="registrarPesada" :disabled="!nuevaPesada.peso_bruto || cargando" class="w-full bg-emerald-500 text-white py-4 rounded-2xl font-black text-lg shadow-md disabled:opacity-50 transition uppercase hover:bg-emerald-600">
              Confirmar y Guardar Pesada
            </button>
          </div>
        </div>

        <div class="bg-white rounded-3xl border overflow-hidden max-w-2xl mx-auto shadow-sm">
          <div class="p-5 border-b bg-gray-50"><h3 class="font-bold text-gray-700">Resumen de Pesadas ({{ registrosDelViaje.length }})</h3></div>
          <table class="min-w-full text-left text-sm">
            <thead class="bg-gray-50 text-gray-400 text-[10px] uppercase font-black">
              <tr><th class="p-4">Tarima</th><th class="p-4 text-center">Cajas</th><th class="p-4 text-right">Peso Neto</th><th class="p-4 text-center">Acciones</th></tr>
            </thead>
            <tbody>
              <tr v-for="r in registrosDelViaje" :key="r.id" class="border-b hover:bg-gray-50">
                <td class="p-4 font-bold text-gray-700">#{{ r.numero_tarima }}</td>
                <td class="p-4 text-center font-medium text-gray-600">{{ r.cantidad_cajas }}</td>
                <td class="p-4 text-right font-black text-emerald-600">{{ formatearPeso(r.peso_neto) }} kg</td>
                <td class="p-4 text-center">
                  <button @click="abrirEdicionPesada(r)" class="text-blue-500 hover:scale-110 transition mr-3">✏️</button>
                  <button @click="eliminarPesada(r.id)" class="text-red-500 hover:scale-110 transition">🗑️</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div v-if="modalAsignarVacio" class="fixed inset-0 bg-gray-900 bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-3xl w-full max-w-md p-8 text-center shadow-2xl">
        <h2 class="text-2xl font-bold mb-2 text-gray-800">Asignar Espacio</h2>
        <p class="text-gray-500 mb-6 font-mono bg-gray-100 py-1 px-3 rounded-full inline-block">Columna {{celdaSeleccionada.x}}, Fila {{celdaSeleccionada.y}}</p>
        <div class="text-left mb-6">
          <label class="block text-sm text-gray-500 mb-2 font-bold uppercase">Tarima disponible en piso:</label>
          <select v-model="tarimaAAsignarId" class="w-full border border-gray-300 p-4 rounded-2xl outline-none focus:ring-2 focus:ring-blue-400 font-bold text-gray-700">
            <option value="" disabled>-- Elige una tarima --</option>
            <option v-for="t in tarimasEnBodega" :value="t.id" :key="t.id">T-#{{ t.numero_tarima }} | {{t.nombre_dueno}} ({{formatearPeso(t.peso_neto)}}kg)</option>
          </select>
        </div>
        <div class="flex gap-4"><button @click="modalAsignarVacio = false" class="flex-1 bg-gray-100 py-3 rounded-2xl font-bold text-gray-600 hover:bg-gray-200 transition">Cancelar</button><button @click="asignarNuevaTarima" :disabled="!tarimaAAsignarId" class="flex-1 bg-blue-500 text-white py-3 rounded-2xl font-bold shadow-sm disabled:opacity-50 hover:bg-blue-600 transition">Meter al Frío</button></div>
      </div>
    </div>

    <div v-if="modalOpcionesOcupado" class="fixed inset-0 bg-gray-900 bg-opacity-60 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
      <div class="bg-white rounded-3xl w-full max-w-md overflow-hidden shadow-2xl">
        
        <div class="p-6 text-center border-b" :class="colorCabeceraModal(detallesTarimaOcupada?.viaje_id, detallesTarimaOcupada?.es_maquila)">
          <div class="text-3xl mb-3 bg-white/50 w-16 h-16 rounded-full flex items-center justify-center mx-auto shadow-sm">📦</div>
          <h2 class="text-3xl font-black mb-1">Tarima #{{detallesTarimaOcupada?.numero_tarima}}</h2>
          <p class="font-bold text-xl">{{detallesTarimaOcupada?.fruta_nombre}} | {{formatearPeso(detallesTarimaOcupada?.peso_neto)}} kg</p>
        </div>

        <div class="p-8 text-center">
          <p class="mb-8 text-lg border-b border-gray-100 pb-6 uppercase font-black tracking-tight text-gray-800">
            {{detallesTarimaOcupada?.nombre_dueno}} <br> 
            <span class="text-sm font-bold text-gray-500 mt-1 block">Viaje #{{detallesTarimaOcupada?.viaje_id}} • {{detallesTarimaOcupada?.fecha_viaje}}</span>
          </p>
          
          <div class="space-y-3">
            <button @click="abrirEdicionTarima(detallesTarimaOcupada)" class="w-full bg-blue-50 text-blue-700 hover:bg-blue-100 py-3.5 text-base rounded-2xl font-bold transition border border-blue-100">✏️ Corregir Peso / Fruta</button>
            <button @click="prepararReubicacion" class="w-full bg-gray-50 text-gray-700 hover:bg-gray-100 py-3.5 text-base rounded-2xl font-bold transition border border-gray-200">↔️ Reubicar en el Frío</button>
            <button @click="retirarTarima('EN_BODEGA')" class="w-full bg-orange-50 text-orange-700 hover:bg-orange-100 py-3.5 text-base rounded-2xl font-bold transition border border-orange-200">👇 Bajar a Bodega (Piso)</button>
            <button @click="retirarTarima('ENVIADA')" class="w-full bg-gray-800 text-white hover:bg-black py-3.5 text-base rounded-2xl font-bold transition shadow-md mt-2">🚚 Marcar como Enviada</button>
          </div>
          
          <button @click="modalOpcionesOcupado = false" class="mt-6 text-sm font-bold text-gray-400 hover:text-gray-600 uppercase tracking-widest transition">Cerrar</button>
        </div>

      </div>
    </div>

    <div v-if="mostrarModalViaje" class="fixed inset-0 bg-gray-900 bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-3xl w-full max-w-lg p-8 shadow-2xl">
        <h2 class="text-2xl font-bold mb-6 text-gray-800">Apertura de Viaje</h2>
        <div class="space-y-5">
          <div>
            <label class="block text-xs font-bold text-gray-400 uppercase mb-1">1. Tipo de Operación</label>
            <select v-model="nuevoViaje.tipo_operacion" class="w-full border border-gray-300 p-4 rounded-2xl bg-gray-50 font-black text-gray-800 outline-none focus:ring-2 focus:ring-emerald-400 transition">
              <option value="ACOPIO">ACOPIO (Compra)</option>
              <option value="MAQUILA">MAQUILA (Servicio)</option>
            </select>
          </div>
          <div v-if="nuevoViaje.tipo_operacion === 'ACOPIO'" class="space-y-5 border-t border-gray-100 pt-5">
            <div><label class="block text-xs font-bold text-gray-400 uppercase mb-1">Acopiador</label><select v-model="nuevoViaje.acopiador_id" class="w-full border border-gray-300 p-4 rounded-2xl outline-none font-bold text-gray-700 focus:ring-2 focus:ring-emerald-400"><option value="" disabled>-- Seleccionar --</option><option v-for="a in acopiadores" :value="a.id" :key="a.id">{{ a.nombre }}</option></select></div>
            <div><label class="block text-xs font-bold text-gray-400 uppercase mb-1">Placa</label><input v-model="nuevoViaje.placa" placeholder="ABC-123" class="w-full border border-gray-300 p-4 rounded-2xl uppercase outline-none font-bold text-gray-700 focus:ring-2 focus:ring-emerald-400" /></div>
          </div>
          <div v-if="nuevoViaje.tipo_operacion === 'MAQUILA'" class="space-y-5 border-t border-gray-100 pt-5">
            <div><label class="block text-xs font-bold text-purple-500 uppercase mb-1">Cliente</label><select v-model="nuevoViaje.cliente_id" class="w-full border border-purple-200 p-4 rounded-2xl outline-none font-bold text-gray-700 focus:ring-2 focus:ring-purple-400"><option value="" disabled>-- Seleccionar --</option><option v-for="c in clientes" :value="c.id" :key="c.id">{{ c.nombre }}</option></select></div>
          </div>
        </div>
        <div class="mt-8 flex gap-4"><button @click="mostrarModalViaje = false" class="flex-1 bg-gray-100 py-4 rounded-2xl font-bold text-gray-600 hover:bg-gray-200 transition">Cancelar</button><button @click="registrarViaje" class="flex-1 bg-emerald-500 text-white py-4 rounded-2xl font-bold hover:bg-emerald-600 transition shadow-md">Abrir Viaje</button></div>
      </div>
    </div>

    <div v-if="mostrarModalEdicionPesada" class="fixed inset-0 bg-gray-900 bg-opacity-60 flex items-center justify-center z-[60] p-4 backdrop-blur-sm">
      <div class="bg-white rounded-3xl w-full max-w-md p-8 shadow-2xl">
        <h2 class="text-2xl font-bold mb-6 text-gray-800">Corregir Pesada #{{pesadaEditandoViaje.numero_tarima}}</h2>
        <div class="space-y-4">
          <div><label class="text-xs font-bold text-gray-400">TIPO DE FRUTA</label><select v-model="pesadaEditandoViaje.tipo_fruta_id" class="w-full border p-3 rounded-xl outline-none text-gray-700 font-medium"><option v-for="f in tiposFruta" :value="f.id" :key="f.id">{{f.nombre}}</option></select></div>
          <div class="grid grid-cols-2 gap-4">
            <div><label class="text-xs font-bold text-gray-400">PESO BRUTO</label><input type="number" step="0.5" v-model="pesadaEditandoViaje.peso_bruto" class="w-full border p-3 rounded-xl font-bold"></div>
            <div><label class="text-xs font-bold text-gray-400">CAJAS</label><input type="number" v-model="pesadaEditandoViaje.cantidad_cajas" class="w-full border p-3 rounded-xl font-bold"></div>
            <div><label class="text-xs font-bold text-orange-400">TARA CAJA</label><input type="number" step="0.01" v-model="pesadaEditandoViaje.tara_caja" class="w-full border p-3 rounded-xl font-bold text-orange-600 bg-orange-50"></div>
            <div><label class="text-xs font-bold text-orange-400">TARA TARIMA</label><input type="number" step="0.1" v-model="pesadaEditandoViaje.tara_tarima" class="w-full border p-3 rounded-xl font-bold text-orange-600 bg-orange-50"></div>
          </div>
        </div>
        <div class="flex gap-4 mt-8">
          <button @click="mostrarModalEdicionPesada = false" class="flex-1 bg-gray-100 py-3 rounded-xl font-bold text-gray-600 hover:bg-gray-200">Cancelar</button>
          <button @click="guardarEdicionPesada" class="flex-1 bg-blue-500 text-white font-bold py-3 rounded-xl hover:bg-blue-600 shadow-md">Guardar</button>
        </div>
      </div>
    </div>

  </div>

  <div v-if="mostrarModalEdicionViaje" class="fixed inset-0 bg-gray-900 bg-opacity-50 flex items-center justify-center z-[60] p-4 backdrop-blur-sm">
      <div class="bg-white rounded-3xl w-full max-w-lg p-8 shadow-2xl">
        <h2 class="text-2xl font-bold mb-6 text-gray-800">Editar Viaje #{{viajeEditando.id}}</h2>
        <div class="space-y-5">
          <div>
            <label class="block text-xs font-bold text-gray-400 uppercase mb-1">Tipo de Operación</label>
            <select v-model="viajeEditando.tipo_operacion" class="w-full border border-gray-300 p-4 rounded-2xl bg-gray-50 font-black text-gray-800 outline-none">
              <option value="ACOPIO">ACOPIO (Compra)</option>
              <option value="MAQUILA">MAQUILA (Servicio)</option>
            </select>
          </div>
          <div v-if="viajeEditando.tipo_operacion === 'ACOPIO'" class="space-y-5 border-t border-gray-100 pt-5">
            <div><label class="block text-xs font-bold text-gray-400 uppercase mb-1">Acopiador</label><select v-model="viajeEditando.acopiador_id" class="w-full border border-gray-300 p-4 rounded-2xl outline-none font-bold"><option v-for="a in acopiadores" :value="a.id" :key="a.id">{{ a.nombre }}</option></select></div>
            <div><label class="block text-xs font-bold text-gray-400 uppercase mb-1">Placa</label><input v-model="viajeEditando.placa" class="w-full border border-gray-300 p-4 rounded-2xl uppercase outline-none font-bold" /></div>
          </div>
          <div v-if="viajeEditando.tipo_operacion === 'MAQUILA'" class="space-y-5 border-t border-gray-100 pt-5">
            <div><label class="block text-xs font-bold text-purple-500 uppercase mb-1">Cliente</label><select v-model="viajeEditando.cliente_id" class="w-full border border-purple-200 p-4 rounded-2xl outline-none font-bold"><option v-for="c in clientes" :value="c.id" :key="c.id">{{ c.nombre }}</option></select></div>
          </div>
        </div>
        <div class="mt-8 flex gap-4">
          <button @click="mostrarModalEdicionViaje = false" class="flex-1 bg-gray-100 py-4 rounded-2xl font-bold text-gray-600 hover:bg-gray-200">Cancelar</button>
          <button @click="guardarEdicionViaje" class="flex-1 bg-blue-500 text-white py-4 rounded-2xl font-bold shadow-md hover:bg-blue-600">Guardar Cambios</button>
        </div>
      </div>
    </div>
</template>

<style>
.animate-fade-in { animation: fadeIn 0.3s ease-out; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
</style>