<!-- TvFrio.vue -->
<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'

const API_URL = '/api'

const tiposFruta = ref([])
const viajes = ref([])
const registros = ref([]) 
const inventarioFrio = ref([])  // NUEVO: Usamos inventario_frio en lugar de registros
const ubicacionesFrio = ref([])
const acopiadores = ref([])
const clientes = ref([])

// 5 Filas x 10 Columnas (Orientación Horizontal)
const FILAS = 5
const COLUMNAS = 10

const fetchDatos = async () => {
  try {
    const promises = [
      fetch(`${API_URL}/tipos-fruta`), 
      fetch(`${API_URL}/viajes`), 
      fetch(`${API_URL}/registros-bascula`), 
      fetch(`${API_URL}/inventario-frio`),
      fetch(`${API_URL}/cuarto-frio`),
      fetch(`${API_URL}/acopiadores`), 
      fetch(`${API_URL}/clientes`)
    ]
    const results = await Promise.allSettled(promises)
    
    // Función segura para extraer JSON o arreglo vacío
    const getJson = async (result) => {
      if (result.status === 'fulfilled' && result.value.ok) {
        try { return await result.value.json() } catch(e) { return [] }
      }
      return []
    }
    
    tiposFruta.value = await getJson(results[0])
    viajes.value = await getJson(results[1])
    registros.value = await getJson(results[2])
    inventarioFrio.value = await getJson(results[3])
    ubicacionesFrio.value = await getJson(results[4])
    acopiadores.value = await getJson(results[5])
    clientes.value = await getJson(results[6])
  } catch (e) { console.error('Error actualizando TV:', e) }
}

let intervalo = null
onMounted(() => {
  fetchDatos()
  intervalo = setInterval(fetchDatos, 5000)
})
onUnmounted(() => clearInterval(intervalo))

const colorClases = (viajeId, esMaquila) => {
  if (esMaquila) return 'bg-purple-800 border-purple-500 text-white'
  
  const colores = [
    'bg-blue-600 border-blue-400 text-white', 'bg-emerald-600 border-emerald-400 text-white', 
    'bg-orange-600 border-orange-400 text-white', 'bg-pink-600 border-pink-400 text-white', 
    'bg-cyan-600 border-cyan-400 text-white', 'bg-indigo-600 border-indigo-400 text-white',
    'bg-yellow-600 border-yellow-400 text-black'
  ]
  return colores[(viajeId || 0) % colores.length]
}

// Helper para obtener información del dueño del viaje
const obtenerInfoViaje = (viajeId) => {
  const viaje = viajes.value.find(v => v.id === viajeId)
  if (!viaje) return { nombre_dueno: 'Desconocido', es_maquila: false, fecha_corta: '??/??' }
  
  const d = new Date(viaje.fecha_entrada)
  const fecha_corta = `${d.getDate().toString().padStart(2, '0')}/${(d.getMonth() + 1).toString().padStart(2, '0')}`
  
  let nombre_dueno = 'Desconocido'
  if (viaje.tipo_operacion === 'MAQUILA') {
    nombre_dueno = clientes.value.find(c => c.id === viaje.cliente_id)?.nombre || 'MAQUILA'
  } else {
    nombre_dueno = acopiadores.value.find(a => a.id === viaje.acopiador_id)?.nombre || 'ACOPIO'
  }
  
  return {
    nombre_dueno,
    es_maquila: viaje.tipo_operacion === 'MAQUILA',
    fecha_corta,
    viaje_id: viaje.id
  }
}

const matrizFrio = computed(() => {
  let grid = []
  for(let y=1; y<=FILAS; y++) {
    let row = []
    for(let x=1; x<=COLUMNAS; x++) {
      let celdaOcupada = null
      // Buscar en cuartofrio usando inventario_frio_id
      const ubicacion = ubicacionesFrio.value.find(u => u.fila_x === x && u.columna_y === y)
      
      if (ubicacion && ubicacion.inventario_frio_id) {
        const tarimaInventario = inventarioFrio.value.find(i => i.id === ubicacion.inventario_frio_id)
        if (tarimaInventario && tarimaInventario.activo === 1) {
          const infoViaje = obtenerInfoViaje(tarimaInventario.viaje_id)
          celdaOcupada = {
            inventario_id: tarimaInventario.id,
            viaje_id: tarimaInventario.viaje_id,
            numero_tarima: tarimaInventario.numero_tarima_display,
            peso_neto: tarimaInventario.peso_neto,
            cantidad_cajas: tarimaInventario.cantidad_cajas,
            tipo_fruta_id: tarimaInventario.tipo_fruta_id,
            fruta_nombre: tiposFruta.value.find(f => f.id === tarimaInventario.tipo_fruta_id)?.nombre || 'N/A',
            notas_referencia: tarimaInventario.notas_referencia,
            origen: tarimaInventario.origen,
            ...infoViaje
          }
        }
      }
      row.push({ x, y, ocupada: celdaOcupada })
    }
    grid.push(row)
  }
  return grid
})

// Tarimas que están en bodega (inventario activo pero sin ubicación en frío)
const tarimasEnBodega = computed(() => {
  // IDs de tarimas que tienen ubicación en cuarto frío
  const idsEnFrio = new Set(ubicacionesFrio.value.map(u => u.inventario_frio_id))
  
  return inventarioFrio.value
    .filter(i => i.activo === 1 && !idsEnFrio.has(i.id))
    .map(i => {
      const infoViaje = obtenerInfoViaje(i.viaje_id)
      return {
        id: i.id,
        inventario_id: i.id,
        viaje_id: i.viaje_id,
        numero_tarima: i.numero_tarima_display,
        peso_neto: i.peso_neto,
        cantidad_cajas: i.cantidad_cajas,
        tipo_fruta_id: i.tipo_fruta_id,
        fruta_nombre: tiposFruta.value.find(f => f.id === i.tipo_fruta_id)?.nombre || 'N/A',
        notas_referencia: i.notas_referencia,
        origen: i.origen,
        ...infoViaje
      }
    })
    .sort((a, b) => {
      // Ordenar por fecha de ingreso (más recientes primero)
      const aFecha = inventarioFrio.value.find(i => i.id === a.id)?.fecha_ingreso || ''
      const bFecha = inventarioFrio.value.find(i => i.id === b.id)?.fecha_ingreso || ''
      return bFecha.localeCompare(aFecha)
    })
})

const leyendaViajes = computed(() => {
  const viajesUnicos = []
  const idsVistos = new Set()
  
  const agregarALeyenda = (item) => {
    if (item && item.viaje_id && !idsVistos.has(item.viaje_id)) {
        idsVistos.add(item.viaje_id)
        viajesUnicos.push({ 
          id: item.viaje_id, 
          nombre: item.nombre_dueno, 
          fecha: item.fecha_corta, 
          es_maquila: item.es_maquila 
        })
    }
  }

  matrizFrio.value.forEach(row => row.forEach(celda => agregarALeyenda(celda.ocupada)))
  tarimasEnBodega.value.forEach(t => agregarALeyenda(t))
  
  return viajesUnicos
})

const stats = computed(() => {
    const ocupadosFrio = ubicacionesFrio.value.filter(u => u.inventario_frio_id).length
    const pesoFrio = ubicacionesFrio.value.reduce((sum, u) => {
        const tarima = inventarioFrio.value.find(i => i.id === u.inventario_frio_id)
        return sum + (tarima ? parseFloat(tarima.peso_neto || 0) : 0)
    }, 0)
    
    const pesoBodega = tarimasEnBodega.value.reduce((sum, t) => sum + parseFloat(t.peso_neto || 0), 0)

    return { 
        ocupadosFrio, 
        disponibles: (FILAS * COLUMNAS) - ocupadosFrio, 
        pesoTotalFrio: pesoFrio.toFixed(2),
        cantidadBodega: tarimasEnBodega.value.length,
        pesoTotalBodega: pesoBodega.toFixed(2)
    }
})
</script>

<template>
  <div class="min-h-screen bg-gray-900 text-white p-4 flex flex-col font-sans overflow-hidden">
    
    <div class="flex justify-between items-center mb-4 bg-gray-800 p-4 rounded-3xl border border-gray-700 shadow-2xl shrink-0">
      <div>
        <h1 class="text-3xl font-black tracking-tighter text-emerald-400">MONITOR GENERAL</h1>
        <p class="text-gray-400 font-bold uppercase tracking-widest text-xs">Estado de Inventario Físico</p>
      </div>
      
      <div class="flex gap-8 text-center items-center">
        <div v-if="stats.cantidadBodega > 0" class="border-r border-gray-700 pr-8">
            <span class="block text-[10px] text-orange-400 font-bold uppercase mb-1">En Bodega (Piso)</span>
            <span class="block text-2xl font-black text-white leading-none">{{stats.cantidadBodega}} <small class="text-xs text-gray-400">Tarimas</small></span>
            <span class="block text-lg font-bold text-orange-500 mt-1">{{stats.pesoTotalBodega}} <small class="text-[10px]">kg</small></span>
        </div>

        <div class="border-r border-gray-700 pr-8">
            <span class="block text-[10px] text-blue-400 font-bold uppercase mb-1">Peso en Frío</span>
            <span class="text-3xl font-black text-blue-500">{{stats.pesoTotalFrio}} <small class="text-sm">kg</small></span>
        </div>

        <div class="pr-2">
            <span class="block text-[10px] text-gray-400 font-bold uppercase mb-1">Ocupación</span>
            <span class="text-3xl font-black text-white">{{stats.ocupadosFrio}} <span class="text-xl text-gray-500">/ 50</span></span>
        </div>

        <div class="bg-gray-700 px-6 py-2 rounded-2xl border border-gray-600 shadow-inner">
            <span class="block text-[10px] text-gray-400 font-bold uppercase mb-1">Libres</span>
            <span class="text-3xl font-black text-emerald-400">{{stats.disponibles}}</span>
        </div>
      </div>
    </div>

    <div class="flex-1 flex justify-center items-center mb-4 overflow-hidden min-h-0">
        <div class="grid grid-cols-10 gap-2 w-full h-full max-w-[98vw]">
            <template v-for="fila in matrizFrio">
                <div v-for="celda in fila" :key="`tv-${celda.x}-${celda.y}`" 
                     class="rounded-xl border flex flex-col items-center justify-center transition-all duration-500 shadow-md relative overflow-hidden"
                     :class="[
                         celda.ocupada ? colorClases(celda.ocupada.viaje_id, celda.ocupada.es_maquila) : '',
                         !celda.ocupada && (celda.x === 5 || celda.x === 6) ? 'bg-gray-700/60 border-gray-500 border-dashed opacity-70' : '',
                         !celda.ocupada && celda.x !== 5 && celda.x !== 6 ? 'bg-gray-800/40 border-gray-700 border-dashed opacity-30' : ''
                     ]">
                    
                    <template v-if="celda.ocupada">
                        <div v-if="celda.ocupada.origen === 'MANUAL'" class="absolute top-0 right-0 bg-amber-500 text-white text-[8px] font-black px-1.5 py-0.5 rounded-bl-lg z-10">MAN</div>
                        <div v-if="celda.ocupada.origen === 'UNION'" class="absolute top-0 right-0 bg-indigo-500 text-white text-[8px] font-black px-1.5 py-0.5 rounded-bl-lg z-10">UNI</div>
                        <div v-if="celda.ocupada.es_maquila" class="absolute top-0 left-0 bg-pink-500 text-white text-[8px] font-black px-1.5 py-0.5 rounded-br-lg z-10">MAQ</div>
                        
                        <span class="text-[10px] font-black uppercase opacity-90 mt-2 truncate w-full text-center px-1 z-0">{{celda.ocupada.nombre_dueno}}</span>
                        <span class="text-sm font-black leading-none my-1">{{celda.ocupada.fecha_corta}} | {{celda.ocupada.numero_tarima}}</span>
                        <span class="text-2xl font-black mb-1 text-yellow-300">{{parseFloat(celda.ocupada.peso_neto || 0).toFixed(2)}}</span>
                        <span class="text-[9px] font-bold bg-black/30 px-2 py-0.5 rounded-full uppercase truncate max-w-[90%]">{{celda.ocupada.fruta_nombre}}</span>
                        <span v-if="celda.ocupada.cantidad_cajas" class="text-[8px] font-bold text-white/80 mt-0.5">{{celda.ocupada.cantidad_cajas}} cjs</span>
                    </template>
                    <template v-else>
                        <span class="text-gray-500 font-mono text-[10px] font-bold">{{celda.x}}-{{celda.y}}</span>
                    </template>
                </div>
            </template>
        </div>
    </div>

    <div v-if="tarimasEnBodega.length > 0" class="shrink-0 bg-gray-800 p-3 rounded-3xl border border-gray-700 mb-4 shadow-2xl">
        <div class="flex items-center justify-between mb-2 px-2">
            <h3 class="text-orange-400 font-bold text-xs tracking-widest uppercase flex items-center gap-2">
                <span class="animate-bounce">🧱</span> EN BODEGA (PISO)
            </h3>
        </div>
        <div class="flex gap-2 overflow-x-auto pb-2 custom-scrollbar">
            <div v-for="t in tarimasEnBodega" :key="'bodega-'+t.id"
                 class="min-w-[120px] h-[75px] rounded-xl border flex flex-col items-center justify-center p-1.5 shadow-md shrink-0 relative overflow-hidden"
                 :class="colorClases(t.viaje_id, t.es_maquila)">
                
                <div v-if="t.origen === 'MANUAL'" class="absolute top-0 right-0 bg-amber-500 text-white text-[7px] font-black px-1 rounded-bl-lg">MAN</div>
                <div v-if="t.origen === 'UNION'" class="absolute top-0 right-0 bg-indigo-500 text-white text-[7px] font-black px-1 rounded-bl-lg">UNI</div>
                <div v-if="t.es_maquila" class="absolute top-0 left-0 bg-pink-500 text-white text-[7px] font-black px-1 rounded-br-lg">MAQ</div>
                
                <span class="text-[9px] font-black uppercase opacity-90 truncate w-full text-center mt-1">{{t.nombre_dueno}}</span>
                <span class="text-2xl font-black leading-none my-0.5 text-yellow-300">{{parseFloat(t.peso_neto || 0).toFixed(2)}}</span>
                <span class="text-[8px] font-bold bg-black/30 px-1.5 py-0.5 rounded-full uppercase truncate max-w-full">{{t.numero_tarima}} | {{t.fruta_nombre}}</span>
                <span v-if="t.cantidad_cajas" class="text-[7px] font-bold text-white/80">{{t.cantidad_cajas}} cjs</span>
            </div>
        </div>
    </div>

    <div class="shrink-0 p-3 bg-gray-800/50 rounded-2xl border border-gray-700 flex justify-between items-center">
        <div class="flex flex-wrap gap-x-6 gap-y-2">
            <div v-for="viaje in leyendaViajes" :key="'leg-'+viaje.id" class="flex items-center gap-2">
                <div class="w-4 h-4 rounded shadow-sm border border-white/20" :class="colorClases(viaje.id, viaje.es_maquila).split(' ')[0]"></div>
                <span class="text-xs font-black uppercase tracking-tight text-gray-200">
                    {{viaje.nombre}} <span class="text-emerald-400 mx-1">!</span> {{viaje.fecha}} <span v-if="viaje.es_maquila" class="text-pink-400 ml-1">(MAQUILA)</span>
                </span>
            </div>
            <div v-if="leyendaViajes.length === 0" class="text-gray-500 text-xs font-bold uppercase italic">
                Cámara y Bodega Vacías
            </div>
        </div>
        <div class="flex items-center gap-2 text-[8px] font-bold text-gray-600 uppercase tracking-widest ml-4 shrink-0">
            <div class="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse"></div> Sinc.
        </div>
    </div>
  </div>
</template>

<style scoped>
.grid { grid-template-rows: repeat(5, minmax(0, 1fr)); }
.custom-scrollbar::-webkit-scrollbar { height: 6px; }
.custom-scrollbar::-webkit-scrollbar-track { background: rgba(31, 41, 55, 0.5); border-radius: 10px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: rgba(75, 85, 99, 0.8); border-radius: 10px; }
</style>