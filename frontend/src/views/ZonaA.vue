<!-- ZonaA.vue - Versión Corregida -->
<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'

const API_URL = '/api'

const moduloActual = ref('bascula')
const vistaActual = ref('lista')
const cargando = ref(false)

// Datos de catálogos
const acopiadores = ref([])
const clientes = ref([])
const tiposFruta = ref([])
const viajes = ref([])
const registros = ref([])
const inventarioFrio = ref([])
const ubicacionesFrio = ref([])

// Estados de UI
const viajeSeleccionado = ref(null)
const mostrarModalViaje = ref(false)
const fechaFiltroViajes = ref(new Date().toISOString().split('T')[0])
const mostrarModalEditarTarima = ref(false)
const tarimaEditando = ref({})

// Formularios
const nuevoViaje = ref({ tipo_operacion: 'ACOPIO', acopiador_id: '', cliente_id: '', placa: '' })
const nuevaPesada = ref({ tipo_fruta_id: '', cantidad_cajas: 42, tara_caja: 1.7, cantidad_tarimas: 1, tara_tarima: 21.0, peso_bruto: '', promedio_peso_caja: 0.0 })

// Modal crear tarima manual
const modalCrearTarimaManual = ref(false)
const nuevaTarimaManual = ref({
  viaje_id: null,
  tipo_fruta_id: '',
  numero_tarima_display: '',
  cantidad_cajas: 1,
  peso_neto: 0,
  notas_referencia: ''
})

// Modal unión de tarimas - VERSIÓN SIMPLIFICADA
const modalUnirTarimas = ref(false)
const tarimaParaUnir = ref(null)  // Tarima base seleccionada
const listaTarimasDisponibles = ref([])  // Lista de tarimas disponibles para unir
const tarimaSeleccionadaParaUnir = ref(null)
const nuevoNombreUnion = ref('')
const ubicacionUnionX = ref(1)
const ubicacionUnionY = ref(1)

// Utilidades
const formatearPeso = (valor) => parseFloat(valor || 0).toFixed(2)

// ================= LECTURA DE BÁSCULA ESP32 =================
let intervaloLectura = null
const basculaConectada = ref(false)

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

// ================= LÓGICA DE CÁLCULO =================
const taraTotalCalculada = computed(() => 
  (parseFloat(nuevaPesada.value.cantidad_cajas || 0) * parseFloat(nuevaPesada.value.tara_caja || 0)) + 
  (parseFloat(nuevaPesada.value.cantidad_tarimas || 0) * parseFloat(nuevaPesada.value.tara_tarima || 0))
)

const pesoNetoCalculado = computed(() => 
  Math.max(0, (parseFloat(nuevaPesada.value.peso_bruto || 0) - taraTotalCalculada.value)).toFixed(2)
)

// ================= API CENTRALIZADA =================
const fetchCatalogos = async () => {
  try {
    const [resAcop, resCli, resFruta, resViajes, resRegistros, resInventario, resFrio] = await Promise.all([
      fetch(`${API_URL}/acopiadores`), 
      fetch(`${API_URL}/clientes`), 
      fetch(`${API_URL}/tipos-fruta`), 
      fetch(`${API_URL}/viajes`), 
      fetch(`${API_URL}/registros-bascula`), 
      fetch(`${API_URL}/inventario-frio`),
      fetch(`${API_URL}/cuarto-frio`)
    ])
    
    acopiadores.value = await resAcop.json()
    clientes.value = await resCli.json()
    tiposFruta.value = await resFruta.json()
    viajes.value = await resViajes.json()
    registros.value = await resRegistros.json()
    inventarioFrio.value = await resInventario.json()
    ubicacionesFrio.value = await resFrio.json()
    
    if (viajeSeleccionado.value) {
      viajeSeleccionado.value = viajes.value.find(v => v.id === viajeSeleccionado.value.id) || null
    }
  } catch (e) { 
    console.error('Error al cargar catálogos:', e) 
  }
}

onMounted(() => fetchCatalogos())

// ================= MÓDULO BÁSCULA =================
const viajesDelDia = computed(() => {
  return viajes.value
    .filter(v => v.fecha_entrada && v.fecha_entrada.startsWith(fechaFiltroViajes.value))
    .sort((a, b) => b.id - a.id)
})

const nombreResponsableViaje = (v) => {
  if (!v) return 'Desconocido'
  if (v.tipo_operacion === 'MAQUILA') 
    return clientes.value.find(c => c.id === v.cliente_id)?.nombre || 'Cliente Desconocido'
  return acopiadores.value.find(a => a.id === v.acopiador_id)?.nombre || 'Acopiador Desconocido'
}

const abrirModalViaje = () => { 
  nuevoViaje.value = { tipo_operacion: 'ACOPIO', acopiador_id: '', cliente_id: '', placa: '' }
  mostrarModalViaje.value = true 
}

const registrarViaje = async () => { 
  if (nuevoViaje.value.tipo_operacion === 'ACOPIO' && !nuevoViaje.value.acopiador_id) 
    return alert("Selecciona un acopiador")
  if (nuevoViaje.value.tipo_operacion === 'MAQUILA' && !nuevoViaje.value.cliente_id) 
    return alert("Selecciona un cliente")

  cargando.value = true
  try { 
    const payload = {
      tipo_operacion: nuevoViaje.value.tipo_operacion,
      placa: nuevoViaje.value.tipo_operacion === 'ACOPIO' ? nuevoViaje.value.placa : 'N/A', 
      acopiador_id: nuevoViaje.value.tipo_operacion === 'ACOPIO' ? parseInt(nuevoViaje.value.acopiador_id) : null,
      cliente_id: nuevoViaje.value.tipo_operacion === 'MAQUILA' ? parseInt(nuevoViaje.value.cliente_id) : null
    }

    const res = await fetch(`${API_URL}/viajes`, { 
      method: 'POST', 
      headers: { 'Content-Type': 'application/json' }, 
      body: JSON.stringify(payload) 
    })
    
    if (!res.ok) {
      const err = await res.json()
      alert(err.detail || "Error al guardar el viaje.")
      return
    }

    const viajeCreado = await res.json()
    mostrarModalViaje.value = false
    await fetchCatalogos()
    abrirDetalleViaje(viajeCreado)
  } catch (error) { 
    alert("Error de conexión con el servidor.") 
  } finally { 
    cargando.value = false 
  } 
}

const abrirDetalleViaje = (viaje) => { 
  viajeSeleccionado.value = viaje
  vistaActual.value = 'detalle'
  nuevaPesada.value = { 
    tipo_fruta_id: '', cantidad_cajas: 42, tara_caja: 1.7, 
    cantidad_tarimas: 1, tara_tarima: 21.0, peso_bruto: '', promedio_peso_caja: 0.0 
  } 
}

const cerrarViaje = async () => { 
  if (!confirm("¿Cerrar viaje? Esto inhabilitará la carga de nuevas pesadas.")) return
  
  cargando.value = true
  try { 
    const res = await fetch(`${API_URL}/viajes/${viajeSeleccionado.value.id}/cerrar`, { method: 'PUT' })
    if (!res.ok) {
      const err = await res.json()
      alert(err.detail || "Error al cerrar el viaje.")
      return
    }
    await fetchCatalogos()
    vistaActual.value = 'lista'
    viajeSeleccionado.value = null 
  } finally { 
    cargando.value = false 
  } 
}

const eliminarViajeCompleto = async (viajeId) => {
  if(!confirm("🚨 ATENCIÓN: Vas a borrar este viaje y TODAS sus pesadas asociadas de forma irreversible.\n\n¿Deseas continuar?")) 
    return

  cargando.value = true
  try {
    const res = await fetch(`${API_URL}/viajes/${viajeId}`, { method: 'DELETE' })
    if(!res.ok) {
      const err = await res.json()
      alert(err.detail || "Error al eliminar el viaje")
    } else {
      viajeSeleccionado.value = null
      vistaActual.value = 'lista'
      await fetchCatalogos()
    }
  } finally { 
    cargando.value = false 
  }
}

const registrosDelViaje = computed(() => { 
  if (!viajeSeleccionado.value) return []
  return registros.value
    .filter(t => t.viaje_id === viajeSeleccionado.value.id)
    .sort((a, b) => b.id - a.id) 
})

const registrarPesada = async () => { 
  if (!nuevaPesada.value.peso_bruto) return alert("El peso bruto es obligatorio.")
  
  cargando.value = true
  try { 
    const payload = { 
      ...nuevaPesada.value, 
      viaje_id: viajeSeleccionado.value.id, 
      maquila_id: viajeSeleccionado.value.tipo_operacion === 'MAQUILA' ? 1 : null, 
      numero_tarima: registrosDelViaje.value.length + 1, 
      tara_total: taraTotalCalculada.value, 
      peso_neto: pesoNetoCalculado.value, 
      promedio_peso_caja: nuevaPesada.value.cantidad_cajas > 0 
        ? (pesoNetoCalculado.value / nuevaPesada.value.cantidad_cajas) 
        : 0 
    }
    
    const res = await fetch(`${API_URL}/registros-bascula`, { 
      method: 'POST', 
      headers: { 'Content-Type': 'application/json' }, 
      body: JSON.stringify(payload) 
    })
    
    if (!res.ok) {
      const err = await res.json()
      alert(err.detail || "Error de validación al guardar la pesada.")
      return
    }
    
    nuevaPesada.value.peso_bruto = ''
    await fetchCatalogos() 
  } finally { 
    cargando.value = false 
  } 
}

// ================= CUARTO FRÍO Y BODEGA =================
const FILAS = 5
const COLUMNAS = 10

const tarimasEnBodega = computed(() => {
  const idsEnFrio = new Set(ubicacionesFrio.value.map(u => u.inventario_frio_id).filter(id => id))
  
  return inventarioFrio.value
    .filter(i => i.activo === 1 && !idsEnFrio.has(i.id))
    .map(i => {
      const viaje = viajes.value.find(v => v.id === i.viaje_id)
      const es_maquila = viaje?.tipo_operacion === 'MAQUILA'
      
      let nombre_dueno = 'Desconocido'
      if (i.viaje_id) {
        const viaje = viajes.value.find(v => v.id === i.viaje_id)
        if (viaje) {
          const es_maquila = viaje.tipo_operacion === 'MAQUILA'
          if (es_maquila) {
            nombre_dueno = clientes.value.find(c => c.id === viaje.cliente_id)?.nombre || 'MAQUILA'
          } else {
            nombre_dueno = acopiadores.value.find(a => a.id === viaje.acopiador_id)?.nombre || 'ACOPIO'
          }
        }
      } else {
        nombre_dueno = '📦 Inventario General'
      }

      return {
        id: i.id,
        inventario_id: i.id,
        numero_tarima_display: i.numero_tarima_display,
        peso_neto: i.peso_neto,
        cantidad_cajas: i.cantidad_cajas,
        tipo_fruta_id: i.tipo_fruta_id,
        fruta_nombre: tiposFruta.value.find(f => f.id === i.tipo_fruta_id)?.nombre || 'N/A',
        nombre_dueno: nombre_dueno,
        es_maquila: es_maquila,
        origen: i.origen,
        viaje_id: i.viaje_id
      }
    })
})

const modalAsignarVacio = ref(false)
const modalOpcionesOcupado = ref(false)
const celdaSeleccionada = ref({ x: 0, y: 0 })
const tarimaAAsignarId = ref('')
const tarimaOcupadaSeleccionada = ref(null)
const modoReubicar = ref(false)

const detallesTarimaOcupada = computed(() => {
  if(!tarimaOcupadaSeleccionada.value) return null
  const viaje = viajes.value.find(v => v.id === tarimaOcupadaSeleccionada.value.viaje_id)
  const es_maquila = viaje?.tipo_operacion === 'MAQUILA'
  let nombre_dueno = 'Desconocido'
  
  if (es_maquila) {
     nombre_dueno = clientes.value.find(c => c.id === viaje?.cliente_id)?.nombre || 'MAQUILA'
  } else {
     nombre_dueno = acopiadores.value.find(a => a.id === viaje?.acopiador_id)?.nombre || 'ACOPIO'
  }

  return {
    ...tarimaOcupadaSeleccionada.value,
    nombre_dueno,
    es_maquila
  }
})

const matrizFrio = computed(() => {
  let grid = []
  for(let y=1; y<=FILAS; y++) {
    let row = []
    for(let x=1; x<=COLUMNAS; x++) {
      let celdaOcupada = null
      const ubicacion = ubicacionesFrio.value.find(u => u.fila_x === x && u.columna_y === y)
      
      if (ubicacion && ubicacion.inventario_frio_id) {
        const tarima = inventarioFrio.value.find(i => i.id === ubicacion.inventario_frio_id && i.activo === 1)
        if (tarima) {
          const viaje = viajes.value.find(v => v.id === tarima.viaje_id)
          const d = viaje ? new Date(viaje.fecha_entrada) : new Date()
          
          let nombre_dueno = 'Desconocido'
          let es_maquila = false
          if (viaje) {
            es_maquila = viaje.tipo_operacion === 'MAQUILA'
            if (es_maquila) {
              nombre_dueno = clientes.value.find(c => c.id === viaje.cliente_id)?.nombre || 'MAQUILA'
            } else {
              nombre_dueno = acopiadores.value.find(a => a.id === viaje.acopiador_id)?.nombre || 'ACOPIO'
            }
          }
          
          celdaOcupada = {
            inventario_id: tarima.id,
            viaje_id: tarima.viaje_id,
            numero_tarima_display: tarima.numero_tarima_display,
            peso_neto: tarima.peso_neto,
            cantidad_cajas: tarima.cantidad_cajas,
            fruta_nombre: tiposFruta.value.find(f => f.id === tarima.tipo_fruta_id)?.nombre || 'N/A',
            origen: tarima.origen,
            fecha_corta: `${d.getDate().toString().padStart(2, '0')}/${(d.getMonth() + 1).toString().padStart(2, '0')}`,
            nombre_dueno,
            es_maquila
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

const colorCabeceraModal = (viajeId, esMaquila) => {
  if (esMaquila) return 'bg-purple-100 text-purple-800'
  const colores = ['bg-blue-100 text-blue-800', 'bg-emerald-100 text-emerald-800', 'bg-orange-100 text-orange-800', 'bg-pink-100 text-pink-800', 'bg-cyan-100 text-cyan-800', 'bg-indigo-100 text-indigo-800']
  return colores[(viajeId || 0) % colores.length]
}

const manejarClickCelda = (celda) => {
  celdaSeleccionada.value = { x: celda.x, y: celda.y }
  if(modoReubicar.value) { 
    if(celda.ocupada) return alert("Esa posición ya está ocupada.")
    moverTarima(celda.x, celda.y)
    return
  }
  if (celda.ocupada) { 
    tarimaOcupadaSeleccionada.value = celda.ocupada
    modalOpcionesOcupado.value = true 
  } else { 
    tarimaAAsignarId.value = ''
    modalAsignarVacio.value = true 
  }
}

const asignarNuevaTarima = async () => {
  if(!tarimaAAsignarId.value) return
  cargando.value = true
  try {
    const res = await fetch(`${API_URL}/cuarto-frio`, { 
      method: 'POST', 
      headers: { 'Content-Type': 'application/json' }, 
      body: JSON.stringify({ 
        inventario_frio_id: parseInt(tarimaAAsignarId.value), 
        fila_x: celdaSeleccionada.value.x, 
        columna_y: celdaSeleccionada.value.y 
      }) 
    })
    if(!res.ok) alert((await res.json()).detail || "Error al asignar tarima")
    modalAsignarVacio.value = false
    await fetchCatalogos()
  } finally { cargando.value = false }
}

const retirarTarima = async () => {
  if(!tarimaOcupadaSeleccionada.value) return
  cargando.value = true
  try { 
    await fetch(`${API_URL}/cuarto-frio/${tarimaOcupadaSeleccionada.value.inventario_id}`, { method: 'DELETE' })
    modalOpcionesOcupado.value = false
    await fetchCatalogos() 
  } finally { cargando.value = false }
}

const marcarTarimaEnviada = async () => {
  if(!tarimaOcupadaSeleccionada.value) return
  if (!confirm(`🚚 ¿Marcar tarima ${tarimaOcupadaSeleccionada.value.numero_tarima_display} como ENVIADA?`)) return
  
  cargando.value = true
  try {
    const res = await fetch(`${API_URL}/inventario-frio/${tarimaOcupadaSeleccionada.value.inventario_id}/enviar`, { method: 'DELETE' })
    if (!res.ok) {
      const err = await res.json()
      alert(err.detail || "Error al marcar la tarima como enviada")
    } else {
      alert("✅ Tarima marcada como enviada")
      modalOpcionesOcupado.value = false
      await fetchCatalogos()
    }
  } finally { cargando.value = false }
}

const prepararReubicacion = () => { 
  modoReubicar.value = true
  modalOpcionesOcupado.value = false 
}

const moverTarima = async (nueva_x, nueva_y) => {
  if(!tarimaOcupadaSeleccionada.value) return
  cargando.value = true
  try { 
    const res = await fetch(`${API_URL}/cuarto-frio/${tarimaOcupadaSeleccionada.value.inventario_id}/mover`, { 
      method: 'PUT', 
      headers: { 'Content-Type': 'application/json' }, 
      body: JSON.stringify({ fila_x: nueva_x, columna_y: nueva_y }) 
    })
    if(!res.ok) alert((await res.json()).detail || "Error al reubicar")
    modoReubicar.value = false
    tarimaOcupadaSeleccionada.value = null
    await fetchCatalogos() 
  } finally { cargando.value = false }
}

const cancelarReubicacion = () => { 
  modoReubicar.value = false
  tarimaOcupadaSeleccionada.value = null 
}

// ================= FUNCIONES DE UNIÓN DE TARIMAS (SIMPLIFICADAS) =================
const abrirModalUnion = () => {
  if (!tarimaOcupadaSeleccionada.value) {
    alert("No hay tarima seleccionada")
    return
  }
  
  // Guardar la tarima base
  tarimaParaUnir.value = tarimaOcupadaSeleccionada.value
  
  // Generar lista de tarimas disponibles para unir (excluyendo la actual)
  const idsEnFrio = new Set(ubicacionesFrio.value.map(u => u.inventario_frio_id))
  const disponibles = []
  
  // Agregar tarimas en bodega
  for (const t of tarimasEnBodega.value) {
    if (t.id !== tarimaParaUnir.value.inventario_id) {
      disponibles.push({
        id: t.id,
        display: `[Bodega] ${t.numero_tarima_display} - ${formatearPeso(t.peso_neto)} kg (${t.nombre_dueno})`,
        ...t
      })
    }
  }
  
  // Agregar tarimas en frío
  for (const fila of matrizFrio.value) {
    for (const celda of fila) {
      if (celda.ocupada && celda.ocupada.inventario_id !== tarimaParaUnir.value.inventario_id) {
        disponibles.push({
          id: celda.ocupada.inventario_id,
          display: `[Frío ${celda.x},${celda.y}] ${celda.ocupada.numero_tarima_display} - ${formatearPeso(celda.ocupada.peso_neto)} kg`,
          ...celda.ocupada
        })
      }
    }
  }
  
  listaTarimasDisponibles.value = disponibles
  tarimaSeleccionadaParaUnir.value = null
  
  // Generar nombre sugerido
  const fecha = new Date()
  nuevoNombreUnion.value = `UNION-${fecha.getFullYear()}${(fecha.getMonth()+1).toString().padStart(2,'0')}${fecha.getDate().toString().padStart(2,'0')}-${Math.floor(Math.random()*1000)}`
  
  ubicacionUnionX.value = celdaSeleccionada.value.x || 1
  ubicacionUnionY.value = celdaSeleccionada.value.y || 1
  
  modalUnirTarimas.value = true
  modalOpcionesOcupado.value = false
}

const ejecutarUnion = async () => {
  if (!tarimaParaUnir.value) {
    alert("No hay tarima base seleccionada")
    return
  }
  
  if (!tarimaSeleccionadaParaUnir.value) {
    alert("Selecciona una segunda tarima para unir")
    return
  }
  
  if (tarimaParaUnir.value.inventario_id === tarimaSeleccionadaParaUnir.value.id) {
    alert("No puedes unir una tarima consigo misma")
    return
  }
  
  if (!nuevoNombreUnion.value || nuevoNombreUnion.value.trim() === '') {
    alert("Ingresa un nombre para la tarima unida")
    return
  }
  
  cargando.value = true
  
  try {
    const payload = {
      id_inventario_1: parseInt(tarimaParaUnir.value.inventario_id),
      id_inventario_2: parseInt(tarimaSeleccionadaParaUnir.value.id),
      nueva_fila_x: ubicacionUnionX.value,
      nueva_columna_y: ubicacionUnionY.value,
      nuevo_numero_tarima: nuevoNombreUnion.value.trim()
    }
    
    const response = await fetch(`${API_URL}/inventario-frio/unir`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    
    const result = await response.json()
    
    if (!response.ok) {
      throw new Error(result.detail || "Error al unir las tarimas")
    }
    
    alert(`✅ Tarimas unidas exitosamente!\n\nNueva tarima: ${nuevoNombreUnion.value}\nPeso total: ${result.nuevo_peso?.toFixed(2) || 'calculado'} kg`)
    
    modalUnirTarimas.value = false
    tarimaParaUnir.value = null
    tarimaSeleccionadaParaUnir.value = null
    await fetchCatalogos()
    
  } catch (error) {
    console.error("Error uniendo tarimas:", error)
    alert(error.message || "Error al unir las tarimas")
  } finally {
    cargando.value = false
  }
}

const cancelarUnion = () => {
  modalUnirTarimas.value = false
  tarimaParaUnir.value = null
  tarimaSeleccionadaParaUnir.value = null
}

// Crear tarima manual (con viaje opcional)
const crearTarimaManual = async () => {
  // Solo validar tipo de fruta y datos básicos
  if (!nuevaTarimaManual.value.tipo_fruta_id) return alert("Selecciona un tipo de fruta")
  if (!nuevaTarimaManual.value.numero_tarima_display) return alert("Ingresa un identificador para la tarima")
  if (nuevaTarimaManual.value.peso_neto <= 0) return alert("El peso debe ser mayor a 0")
  
  cargando.value = true
  try {
    // Preparar payload - viaje_id puede ser null
    const payload = {
      tipo_fruta_id: parseInt(nuevaTarimaManual.value.tipo_fruta_id),
      numero_tarima_display: nuevaTarimaManual.value.numero_tarima_display,
      cantidad_cajas: parseInt(nuevaTarimaManual.value.cantidad_cajas) || 1,
      peso_neto: parseFloat(nuevaTarimaManual.value.peso_neto),
      notas_referencia: nuevaTarimaManual.value.notas_referencia || "Creación manual",
      origen: "MANUAL"
    }
    
    // Solo incluir viaje_id si tiene valor
    if (nuevaTarimaManual.value.viaje_id) {
      payload.viaje_id = parseInt(nuevaTarimaManual.value.viaje_id)
    } else {
      payload.viaje_id = null
      payload.notas_referencia += " | Sin viaje asociado"
    }
    
    const res = await fetch(`${API_URL}/inventario-frio`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    
    if (!res.ok) {
      const err = await res.json()
      alert(err.detail || "Error al crear la tarima manual")
    } else {
      alert("✅ Tarima creada exitosamente" + (payload.viaje_id ? "" : " (sin viaje asociado)"))
      modalCrearTarimaManual.value = false
      nuevaTarimaManual.value = {
        viaje_id: null,
        tipo_fruta_id: '',
        numero_tarima_display: '',
        cantidad_cajas: 1,
        peso_neto: 0,
        notas_referencia: ''
      }
      await fetchCatalogos()
    }
  } finally {
    cargando.value = false
  }
}

// Editar tarima en frío
const abrirEdicionTarimaFrio = (tarima) => {
  tarimaEditando.value = {
    id: tarima.inventario_id,
    numero_tarima_display: tarima.numero_tarima_display,
    peso_neto: tarima.peso_neto,
    cantidad_cajas: tarima.cantidad_cajas,
    tipo_fruta_id: tarima.tipo_fruta_id
  }
  mostrarModalEditarTarima.value = true
}

const guardarEdicionTarimaFrio = async () => {
  cargando.value = true
  try {
    const res = await fetch(`${API_URL}/inventario-frio/${tarimaEditando.value.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        numero_tarima_display: tarimaEditando.value.numero_tarima_display,
        peso_neto: parseFloat(tarimaEditando.value.peso_neto),
        cantidad_cajas: parseInt(tarimaEditando.value.cantidad_cajas),
        tipo_fruta_id: parseInt(tarimaEditando.value.tipo_fruta_id)
      })
    })
    if (!res.ok) {
      const err = await res.json()
      alert(err.detail || "Error al actualizar la tarima")
    } else {
      mostrarModalEditarTarima.value = false
      modalOpcionesOcupado.value = false
      await fetchCatalogos()
    }
  } finally {
    cargando.value = false
  }
}

// Ediciones de pesadas
const pesadaEditandoViaje = ref({})
const mostrarModalEdicionPesada = ref(false)

const abrirEdicionPesada = (pesada) => {
  pesadaEditandoViaje.value = { ...pesada }
  mostrarModalEdicionPesada.value = true
}

const guardarEdicionPesada = async () => {
  cargando.value = true
  try {
    const res = await fetch(`${API_URL}/registros-bascula/${pesadaEditandoViaje.value.id}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(pesadaEditandoViaje.value)
    })
    if(!res.ok) {
      const err = await res.json()
      alert(err.detail || "Error de validación al editar la pesada")
    } else {
      mostrarModalEdicionPesada.value = false
      await fetchCatalogos()
    }
  } finally { cargando.value = false }
}

const eliminarPesada = async (id) => {
  if (!confirm("¿Estás seguro de eliminar esta pesada?")) return
  cargando.value = true
  try {
    const res = await fetch(`${API_URL}/registros-bascula/${id}`, { method: 'DELETE' })
    if(!res.ok) {
      const err = await res.json()
      alert(err.detail || "Error al eliminar la pesada")
    } else {
      await fetchCatalogos()
    }
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
  if (viajeEditando.value.tipo_operacion === 'ACOPIO' && !viajeEditando.value.acopiador_id) 
    return alert("Selecciona un acopiador")
  if (viajeEditando.value.tipo_operacion === 'MAQUILA' && !viajeEditando.value.cliente_id) 
    return alert("Selecciona un cliente")

  cargando.value = true
  try {
    const payload = {
      tipo_operacion: viajeEditando.value.tipo_operacion,
      placa: viajeEditando.value.tipo_operacion === 'ACOPIO' ? viajeEditando.value.placa : 'N/A', 
      acopiador_id: viajeEditando.value.tipo_operacion === 'ACOPIO' ? parseInt(viajeEditando.value.acopiador_id) : null,
      cliente_id: viajeEditando.value.tipo_operacion === 'MAQUILA' ? parseInt(viajeEditando.value.cliente_id) : null
    }
    
    const res = await fetch(`${API_URL}/viajes/${viajeEditando.value.id}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
    })
    if(!res.ok) {
      const err = await res.json()
      alert(err.detail || "Error en el guardado del viaje")
    } else {
      mostrarModalEdicionViaje.value = false
      await fetchCatalogos()
      viajeSeleccionado.value = viajes.value.find(v => v.id === viajeEditando.value.id)
    }
  } finally { cargando.value = false }
}

</script>

<template>
  <div class="min-h-screen bg-gray-50 p-4 md:p-8 relative">
    <!-- Overlay de Carga -->
    <div v-if="cargando" class="fixed inset-0 bg-white/60 backdrop-blur-sm z-50 flex items-center justify-center">
      <div class="bg-white p-6 rounded-3xl shadow-xl flex flex-col items-center">
        <div class="w-10 h-10 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin mb-3"></div>
        <span class="text-gray-700 font-medium">Cargando...</span>
      </div>
    </div>

    <!-- Cabecera -->
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-3xl font-light text-gray-800 tracking-tight mt-1">Módulo Operativo</h1>
      <span class="text-xs font-bold text-gray-400 bg-white px-4 py-2 border rounded-full shadow-sm">ZONA A</span>
    </div>

    <!-- Selector de Módulo -->
    <div class="flex gap-4 mb-6 flex-wrap">
      <button @click="moduloActual = 'bascula'" :class="moduloActual === 'bascula' ? 'bg-emerald-500 text-white' : 'bg-white text-gray-600'" class="px-6 py-3 rounded-2xl font-bold shadow-sm transition border">⚖️ Báscula de Recepción</button>
      <button @click="moduloActual = 'frio'" :class="moduloActual === 'frio' ? 'bg-blue-500 text-white' : 'bg-white text-gray-600'" class="px-6 py-3 rounded-2xl font-bold shadow-sm transition border">❄️ Cuarto Frío y Bodega</button>
    </div>

    <!-- ================= MÓDULO CUARTO FRÍO ================= -->
    <div v-if="moduloActual === 'frio'" class="animate-fade-in space-y-8">
      
      <div class="flex justify-between items-center">
        <h2 class="text-xl font-bold text-blue-800">Gestión de Inventario en Frío</h2>
        <button @click="modalCrearTarimaManual = true" class="bg-amber-500 text-white px-5 py-2.5 rounded-2xl font-bold shadow-sm hover:bg-amber-600 transition">✨ Crear Tarima Manual</button>
      </div>

      <div v-if="modoReubicar" class="bg-orange-100 border border-orange-300 p-4 rounded-2xl flex justify-between items-center animate-pulse">
        <span class="text-orange-800 font-bold">Modo Reubicación: Haz clic en un espacio vacío para mover la Tarima.</span>
        <button @click="cancelarReubicacion" class="bg-white text-orange-600 px-4 py-2 rounded-xl font-bold shadow-sm">Cancelar</button>
      </div>

      <div class="bg-white p-8 rounded-3xl shadow-sm border overflow-x-auto text-center md:text-left">
        <h2 class="text-xl font-bold text-blue-800 mb-6 flex items-center gap-2">❄️ Matriz del Cuarto Frío <span class="text-xs font-normal text-gray-500 ml-4">(10 Columnas x 5 Filas)</span></h2>
        
        <div class="inline-grid grid-cols-10 gap-2 w-full min-w-[800px]">
          <template v-for="fila in matrizFrio" :key="'fila-'+fila[0]?.y">
            <div v-for="celda in fila" :key="`celda-${celda.x}-${celda.y}`" 
                 @click="manejarClickCelda(celda)"
                 class="h-28 rounded-xl border-2 flex flex-col items-center justify-center cursor-pointer transition-all active:scale-95 relative overflow-hidden"
                 :class="[
                   celda.ocupada ? (colorClasesPorViaje(celda.ocupada.viaje_id, celda.ocupada.es_maquila) + ' shadow-md') : 'border-dashed hover:border-emerald-300',
                   !celda.ocupada && (celda.x === 5 || celda.x === 6) ? 'bg-gray-200 border-gray-400' : (!celda.ocupada ? 'bg-gray-50 border-gray-300 hover:bg-emerald-50' : ''),
                   modoReubicar && celda.ocupada ? 'opacity-50 cursor-not-allowed' : ''
                 ]">
                 
                 <template v-if="celda.ocupada">
                   <div v-if="celda.ocupada.origen === 'MANUAL'" class="absolute top-0 right-0 bg-amber-500 text-white text-[8px] font-black px-1.5 py-0.5 rounded-bl-lg z-10">MAN</div>
                   <div v-if="celda.ocupada.origen === 'UNION'" class="absolute top-0 right-0 bg-indigo-500 text-white text-[8px] font-black px-1.5 py-0.5 rounded-bl-lg z-10">UNI</div>
                   <div v-if="celda.ocupada.es_maquila" class="absolute top-0 left-0 bg-pink-500 text-white text-[8px] font-black px-1.5 py-0.5 rounded-br-lg z-10">MAQ</div>
                   <span class="text-[9px] uppercase font-black truncate w-full text-center px-1 opacity-90 mt-2 z-0">{{celda.ocupada.nombre_dueno}}</span>
                   <span class="text-base font-black leading-tight my-1">{{formatearPeso(celda.ocupada.peso_neto)}}</span>
                   <span class="text-[8px] font-bold">{{celda.ocupada.fecha_corta}} | {{celda.ocupada.numero_tarima_display}}</span>
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
         <h2 class="text-xl font-bold text-orange-700 mb-6">🧱 Tarimas en Bodega (Piso - Sin Ubicación)</h2>
         <table class="min-w-full text-left text-sm text-gray-600">
           <thead class="bg-orange-50 text-orange-800 border-b border-orange-100">
             <tr><th class="p-3">Tarima</th><th class="p-3">Dueño</th><th class="p-3">Fruta</th><th class="p-3 text-right">Peso</th><th class="p-3 text-center">Origen</th><th class="p-3 text-center">Acciones</th></tr>
           </thead>
           <tbody>
             <tr v-for="t in tarimasEnBodega" :key="t.id" class="border-b hover:bg-gray-50">
               <td class="p-3 font-bold text-gray-800">{{ t.numero_tarima_display }}</td>
               <td class="p-3 font-medium">{{ t.nombre_dueno }}<span v-if="t.es_maquila" class="bg-purple-100 text-purple-700 text-[9px] px-1 rounded ml-1 font-black">MAQUILA</span></td>
               <td class="p-3">{{ t.fruta_nombre }}</td>
               <td class="p-3 text-right font-bold text-orange-600">{{ formatearPeso(t.peso_neto) }} kg</td>
               <td class="p-3 text-center"><span :class="{'bg-amber-100 text-amber-700': t.origen === 'MANUAL', 'bg-indigo-100 text-indigo-700': t.origen === 'UNION', 'bg-blue-100 text-blue-700': t.origen === 'PESADA'}" class="px-2 py-0.5 rounded text-[10px] font-bold">{{ t.origen || 'PESADA' }}</span></td>
               <td class="p-3 text-center"><button @click="abrirEdicionTarimaFrio(t)" class="text-blue-500 hover:scale-110 transition mr-2">✏️</button></td>
             </tr>
             <tr v-if="tarimasEnBodega.length === 0"><td colspan="6" class="p-8 text-center text-gray-400">No hay tarimas en bodega</td></tr>
           </tbody>
         </table>
      </div>
    </div>

    <!-- ================= MÓDULO BÁSCULA ================= -->
    <div v-if="moduloActual === 'bascula'">
      <!-- LISTA DE VIAJES -->
      <div v-if="vistaActual === 'lista'" class="space-y-6 animate-fade-in">
        <div class="flex flex-col md:flex-row justify-between items-center gap-4 bg-white p-6 rounded-3xl border shadow-sm">
          <div><h2 class="text-xl font-bold text-gray-800">Viajes Registrados</h2><p class="text-xs text-gray-400 uppercase font-black">Historial por Fecha</p></div>
          <div class="flex items-center gap-4"><input type="date" v-model="fechaFiltroViajes" class="border p-3 rounded-2xl outline-none font-bold text-gray-700" /><button @click="abrirModalViaje" class="bg-emerald-500 text-white px-5 py-3 rounded-2xl shadow-sm font-bold">+ Nuevo Viaje</button></div>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div v-for="v in viajesDelDia" :key="v.id" @click="abrirDetalleViaje(v)" class="bg-white p-6 rounded-3xl shadow-sm border cursor-pointer hover:shadow-md transition">
            <div class="flex justify-between items-start mb-4"><span class="text-xs font-bold text-gray-400">ID #{{v.id}}</span><div class="flex gap-2"><span v-if="v.tipo_operacion === 'MAQUILA'" class="bg-purple-100 text-purple-700 px-3 py-0.5 rounded-full text-xs font-bold">MAQUILA</span><span v-else class="bg-blue-100 text-blue-700 px-3 py-0.5 rounded-full text-xs font-bold">ACOPIO</span></div></div>
            <h3 class="text-lg font-bold text-gray-800 mb-1">{{ nombreResponsableViaje(v) }}</h3>
            <p class="text-gray-500 text-sm mb-4">Placa: <span class="font-mono text-gray-700">{{ v.placa }}</span></p>
            <div class="flex justify-between items-center border-t pt-4 mt-4"><span :class="v.estado === 'ACTIVO' ? 'text-emerald-600' : (v.estado === 'CERRADO' ? 'text-orange-500' : 'text-purple-600')" class="text-xs font-black uppercase">{{ v.estado }}</span><span class="text-emerald-500 text-sm font-bold">Ver Detalles →</span></div>
          </div>
          <div v-if="viajesDelDia.length === 0" class="col-span-full py-20 text-center text-gray-400 font-bold border-2 border-dashed rounded-3xl">No hay viajes registrados en esta fecha.</div>
        </div>
      </div>

      <!-- DETALLE DE VIAJE -->
      <div v-if="vistaActual === 'detalle' && viajeSeleccionado" class="space-y-6 animate-fade-in">
        <div class="flex flex-col md:flex-row justify-between bg-white p-6 rounded-3xl border gap-4">
          <div><button @click="vistaActual = 'lista'; viajeSeleccionado = null;" class="bg-gray-100 px-4 py-2 rounded-xl mb-3 text-sm font-medium">← Volver</button><div class="flex items-center gap-3"><h2 class="text-2xl font-light">Viaje <span class="font-medium font-mono">#{{ viajeSeleccionado.id }}</span></h2><span :class="viajeSeleccionado.tipo_operacion === 'MAQUILA' ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'" class="px-3 py-1 rounded-md text-xs font-bold">{{ viajeSeleccionado.tipo_operacion }}</span></div><p class="text-sm text-gray-500 mt-2 font-bold">{{ nombreResponsableViaje(viajeSeleccionado) }}</p></div>
          <div class="flex gap-3 items-center"><button v-if="viajeSeleccionado.estado !== 'CONCILIADO'" @click="abrirEdicionViaje" class="bg-blue-50 text-blue-600 px-5 py-2.5 rounded-2xl font-bold hover:bg-blue-100 transition">✏️ Editar Viaje</button><button v-if="viajeSeleccionado.estado === 'ACTIVO'" @click="cerrarViaje" class="bg-red-50 text-red-600 px-5 py-2.5 rounded-2xl font-bold hover:bg-red-100 transition">🔒 Finalizar</button><button v-if="viajeSeleccionado.estado !== 'CONCILIADO'" @click="eliminarViajeCompleto(viajeSeleccionado.id)" class="bg-red-600 text-white px-5 py-2.5 rounded-2xl font-bold hover:bg-red-700 transition">🗑️ Eliminar Viaje</button></div>
        </div>

        <div v-if="viajeSeleccionado.estado === 'ACTIVO'" class="bg-white p-8 rounded-3xl border max-w-2xl mx-auto shadow-sm">
          <div class="bg-blue-50 border border-blue-200 rounded-3xl p-6 text-center mb-6"><label class="block text-xs text-blue-500 font-bold uppercase mb-1">Peso Bruto (kg)</label><div class="flex flex-col md:flex-row items-center justify-center gap-4 mt-2"><input type="number" step="0.5" v-model="nuevaPesada.peso_bruto" placeholder="0.00" class="bg-transparent text-center text-5xl font-black text-blue-600 outline-none font-mono w-64" /><button @click="conectarBascula" :class="basculaConectada ? 'bg-red-500 text-white' : 'bg-blue-500 text-white'" class="px-4 py-3 rounded-xl text-sm font-bold transition shadow-sm">{{ basculaConectada ? '🔴 Parar' : '🟢 Conectar' }}</button></div></div>
          <div class="space-y-5"><div><label class="block text-xs font-bold text-gray-500 uppercase mb-1">Tipo de Fruta</label><select v-model="nuevaPesada.tipo_fruta_id" class="w-full bg-gray-50 border p-3.5 rounded-2xl outline-none font-bold"><option value="" disabled>-- Seleccionar fruta --</option><option v-for="f in tiposFruta" :value="f.id" :key="f.id">{{ f.nombre }}</option></select></div><div class="grid grid-cols-2 gap-5 border-t pt-5"><div><label class="block text-xs font-bold text-gray-500 uppercase mb-1">Cajas Físicas</label><input type="number" v-model="nuevaPesada.cantidad_cajas" class="w-full bg-gray-50 border p-3.5 rounded-2xl font-bold" /></div><div><label class="block text-xs font-bold text-gray-500 uppercase mb-1">Tarimas</label><input type="number" v-model="nuevaPesada.cantidad_tarimas" class="w-full bg-gray-50 border p-3.5 rounded-2xl font-bold" /></div></div><div class="grid grid-cols-2 gap-5 border-t pt-5"><div><label class="block text-xs font-bold text-orange-500 uppercase mb-1">Tara Caja (kg)</label><input type="number" step="0.01" v-model="nuevaPesada.tara_caja" class="w-full bg-orange-50 border border-orange-100 p-3.5 rounded-2xl font-bold text-orange-700" /></div><div><label class="block text-xs font-bold text-orange-500 uppercase mb-1">Tara Tarima (kg)</label><input type="number" step="0.1" v-model="nuevaPesada.tara_tarima" class="w-full bg-orange-50 border border-orange-100 p-3.5 rounded-2xl font-bold text-orange-700" /></div></div><div class="bg-gray-100 p-4 rounded-2xl flex justify-between items-center mt-4"><span class="text-xs font-bold text-gray-500 uppercase">Peso Neto a Guardar:</span><span class="text-xl font-black text-gray-800">{{ pesoNetoCalculado }} kg</span></div></div>
          <div class="mt-8"><button @click="registrarPesada" :disabled="!nuevaPesada.peso_bruto || cargando" class="w-full bg-emerald-500 text-white py-4 rounded-2xl font-black text-lg shadow-md disabled:opacity-50 transition uppercase hover:bg-emerald-600">Confirmar y Guardar Pesada</button></div>
        </div>

        <div class="bg-white rounded-3xl border overflow-hidden max-w-2xl mx-auto shadow-sm">
          <div class="p-5 border-b bg-gray-50"><h3 class="font-bold text-gray-700">Resumen de Pesadas ({{ registrosDelViaje.length }})</h3></div>
          <table class="min-w-full text-left text-sm"><thead class="bg-gray-50 text-gray-400 text-[10px] uppercase font-black"><tr><th class="p-4">Tarima</th><th class="p-4 text-center">Cajas</th><th class="p-4 text-right">Peso Neto</th><th class="p-4 text-center">Acciones</th></tr></thead><tbody><tr v-for="r in registrosDelViaje" :key="r.id" class="border-b hover:bg-gray-50"><td class="p-4 font-bold text-gray-700">#{{ r.numero_tarima }}</td><td class="p-4 text-center font-medium text-gray-600">{{ r.cantidad_cajas }}</td><td class="p-4 text-right font-black text-emerald-600">{{ formatearPeso(r.peso_neto) }} kg</td><td class="p-4 text-center"><template v-if="viajeSeleccionado.estado !== 'CONCILIADO'"><button @click="abrirEdicionPesada(r)" class="text-blue-500 hover:scale-110 transition mr-3">✏️</button><button @click="eliminarPesada(r.id)" class="text-red-500 hover:scale-110 transition">🗑️</button></template><span v-else class="text-xs text-gray-400 font-bold uppercase">Consolidado</span></td></tr><tr v-if="registrosDelViaje.length === 0"><td colspan="4" class="text-center p-8 text-gray-400 font-bold">No hay pesadas registradas para este viaje.</td></tr></tbody></table>
        </div>
      </div>
    </div>

    <!-- ================= MODALES ================= -->

    <!-- Modal: Asignar Espacio Vacío -->
    <div v-if="modalAsignarVacio" class="fixed inset-0 bg-gray-900 bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-3xl w-full max-w-md p-8 text-center shadow-2xl"><h2 class="text-2xl font-bold mb-2 text-gray-800">Asignar Espacio</h2><p class="text-gray-500 mb-6 font-mono bg-gray-100 py-1 px-3 rounded-full inline-block">Columna {{celdaSeleccionada.x}}, Fila {{celdaSeleccionada.y}}</p><div class="text-left mb-6"><label class="block text-sm text-gray-500 mb-2 font-bold uppercase">Tarima disponible en piso:</label><select v-model="tarimaAAsignarId" class="w-full border border-gray-300 p-4 rounded-2xl outline-none focus:ring-2 focus:ring-blue-400 font-bold text-gray-700"><option value="" disabled>-- Elige una tarima --</option><option v-for="t in tarimasEnBodega" :value="t.id" :key="t.id">{{ t.numero_tarima_display }} | {{t.nombre_dueno}} ({{formatearPeso(t.peso_neto)}}kg)</option></select></div><div class="flex gap-4"><button @click="modalAsignarVacio = false" class="flex-1 bg-gray-100 py-3 rounded-2xl font-bold text-gray-600 hover:bg-gray-200 transition">Cancelar</button><button @click="asignarNuevaTarima" :disabled="!tarimaAAsignarId" class="flex-1 bg-blue-500 text-white py-3 rounded-2xl font-bold shadow-sm disabled:opacity-50 hover:bg-blue-600 transition">Meter al Frío</button></div></div>
    </div>

    <!-- Modal: Opciones de Celda Ocupada -->
    <div v-if="modalOpcionesOcupado" class="fixed inset-0 bg-gray-900 bg-opacity-60 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
      <div class="bg-white rounded-3xl w-full max-w-md overflow-hidden shadow-2xl">
        <div class="p-6 text-center border-b" :class="colorCabeceraModal(detallesTarimaOcupada?.viaje_id, detallesTarimaOcupada?.es_maquila)">
          <div class="text-3xl mb-3 bg-white/50 w-16 h-16 rounded-full flex items-center justify-center mx-auto shadow-sm">📦</div>
          <h2 class="text-3xl font-black mb-1">{{detallesTarimaOcupada?.numero_tarima_display}}</h2>
          <p class="font-bold text-xl">{{detallesTarimaOcupada?.fruta_nombre}} | {{formatearPeso(detallesTarimaOcupada?.peso_neto)}} kg</p>
          <p class="text-sm mt-1">{{ detallesTarimaOcupada?.origen === 'MANUAL' ? '📝 Manual' : detallesTarimaOcupada?.origen === 'UNION' ? '🔗 Unión' : '⚖️ Pesada' }}</p>
        </div>
        <div class="p-8 text-center">
          <p class="mb-4 text-lg border-b border-gray-100 pb-6 uppercase font-black tracking-tight text-gray-800">{{detallesTarimaOcupada?.nombre_dueno}}<br><span class="text-sm font-bold text-gray-500 mt-1 block">Viaje #{{detallesTarimaOcupada?.viaje_id}}</span><span v-if="detallesTarimaOcupada?.cantidad_cajas" class="text-xs text-gray-400 block">Cajas: {{detallesTarimaOcupada?.cantidad_cajas}}</span></p>
          <div class="space-y-3"><button @click="abrirEdicionTarimaFrio(detallesTarimaOcupada)" class="w-full bg-blue-50 text-blue-700 hover:bg-blue-100 py-3.5 text-base rounded-2xl font-bold transition border border-blue-100">✏️ Editar Tarima</button><button @click="prepararReubicacion" class="w-full bg-gray-50 text-gray-700 hover:bg-gray-100 py-3.5 text-base rounded-2xl font-bold transition border border-gray-200">↔️ Reubicar en el Frío</button><button @click="abrirModalUnion" class="w-full bg-indigo-50 text-indigo-700 hover:bg-indigo-100 py-3.5 text-base rounded-2xl font-bold transition border border-indigo-200">🔗 Unir con Otra Tarima</button><button @click="retirarTarima" class="w-full bg-orange-50 text-orange-700 hover:bg-orange-100 py-3.5 text-base rounded-2xl font-bold transition border border-orange-200">👇 Bajar a Bodega (Piso)</button><button @click="marcarTarimaEnviada" class="w-full bg-red-50 text-red-700 hover:bg-red-100 py-3.5 text-base rounded-2xl font-bold transition border border-red-200">🚚 Marcar como Enviada</button></div>
          <button @click="modalOpcionesOcupado = false" class="mt-6 text-sm font-bold text-gray-400 hover:text-gray-600 uppercase tracking-widest transition">Cerrar</button>
        </div>
      </div>
    </div>

    <!-- Modal: Unir Tarimas (VERSIÓN SIMPLIFICADA) -->
    <div v-if="modalUnirTarimas" class="fixed inset-0 bg-gray-900 bg-opacity-60 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
      <div class="bg-white rounded-3xl w-full max-w-lg p-8 shadow-2xl">
        <h2 class="text-2xl font-bold mb-6 text-gray-800">🔗 Unir Tarimas</h2>
        
        <div class="mb-4 p-4 bg-blue-50 rounded-2xl">
          <p class="text-sm font-bold text-blue-800">Tarima 1 (Base):</p>
          <p class="font-mono font-bold">{{ tarimaParaUnir?.numero_tarima_display }}</p>
          <p>{{ formatearPeso(tarimaParaUnir?.peso_neto) }} kg | {{ tarimaParaUnir?.cantidad_cajas || 0 }} cajas</p>
        </div>
        
        <div class="mb-4">
          <label class="block text-sm font-bold text-gray-700 mb-2">Selecciona la segunda tarima:</label>
          <select v-model="tarimaSeleccionadaParaUnir" class="w-full border p-3 rounded-xl">
            <option :value="null">-- Selecciona una tarima --</option>
            <option v-for="t in listaTarimasDisponibles" :key="t.id" :value="t">{{ t.display }}</option>
          </select>
        </div>
        
        <div v-if="tarimaSeleccionadaParaUnir" class="mb-4 p-4 bg-green-50 rounded-2xl">
          <p class="text-sm font-bold text-green-800">Tarima 2:</p>
          <p class="font-mono font-bold">{{ tarimaSeleccionadaParaUnir.numero_tarima_display }}</p>
          <p>{{ formatearPeso(tarimaSeleccionadaParaUnir.peso_neto) }} kg | {{ tarimaSeleccionadaParaUnir.cantidad_cajas || 0 }} cajas</p>
          <div class="mt-2 pt-2 border-t border-green-200">
            <p class="font-bold">Total: {{ (parseFloat(tarimaParaUnir?.peso_neto || 0) + parseFloat(tarimaSeleccionadaParaUnir.peso_neto || 0)).toFixed(2) }} kg | {{ (parseInt(tarimaParaUnir?.cantidad_cajas || 0) + parseInt(tarimaSeleccionadaParaUnir.cantidad_cajas || 0)) }} cajas</p>
          </div>
        </div>
        
        <div class="mb-4">
          <label class="block text-sm font-bold text-gray-700 mb-2">Nombre para la nueva tarima:</label>
          <input v-model="nuevoNombreUnion" class="w-full border p-3 rounded-xl font-mono" placeholder="Ej: UNION-001">
        </div>
        
        <div class="mb-6">
          <label class="block text-sm font-bold text-gray-700 mb-2">Ubicación destino:</label>
          <div class="flex gap-4">
            <div><span class="text-xs text-gray-500">Columna (1-10)</span><input type="number" v-model.number="ubicacionUnionX" class="w-24 border p-3 rounded-xl text-center" min="1" max="10"></div>
            <div><span class="text-xs text-gray-500">Fila (1-5)</span><input type="number" v-model.number="ubicacionUnionY" class="w-24 border p-3 rounded-xl text-center" min="1" max="5"></div>
          </div>
        </div>
        
        <div class="flex gap-4">
          <button @click="cancelarUnion" class="flex-1 bg-gray-100 py-3 rounded-2xl font-bold text-gray-600">Cancelar</button>
          <button @click="ejecutarUnion" :disabled="!tarimaSeleccionadaParaUnir || cargando" class="flex-1 bg-indigo-500 text-white py-3 rounded-2xl font-bold shadow-md disabled:opacity-50">Unir Tarimas</button>
        </div>
      </div>
    </div>

    <!-- Modal: Editar Tarima -->
    <div v-if="mostrarModalEditarTarima" class="fixed inset-0 bg-gray-900 bg-opacity-50 flex items-center justify-center z-[60] p-4">
      <div class="bg-white rounded-3xl w-full max-w-sm p-8 text-center shadow-2xl"><h2 class="text-2xl font-bold mb-6 text-gray-800">Editar Tarima</h2><div class="space-y-4 text-left"><div><label class="text-xs font-bold text-gray-400">IDENTIFICADOR</label><input v-model="tarimaEditando.numero_tarima_display" class="w-full border p-3 rounded-xl font-mono text-lg"></div><div><label class="text-xs font-bold text-gray-400">PESO NETO (KG)</label><input type="number" step="0.1" v-model="tarimaEditando.peso_neto" class="w-full border p-3 rounded-xl font-bold text-lg"></div><div><label class="text-xs font-bold text-gray-400">CAJAS</label><input type="number" v-model="tarimaEditando.cantidad_cajas" class="w-full border p-3 rounded-xl"></div><div><label class="text-xs font-bold text-gray-400">TIPO DE FRUTA</label><select v-model="tarimaEditando.tipo_fruta_id" class="w-full border p-3 rounded-xl"><option v-for="f in tiposFruta" :value="f.id" :key="f.id">{{f.nombre}}</option></select></div></div><div class="flex gap-4 mt-8"><button @click="mostrarModalEditarTarima = false" class="flex-1 bg-gray-100 py-3 rounded-xl font-bold text-gray-600">Cancelar</button><button @click="guardarEdicionTarimaFrio" class="flex-1 bg-blue-500 text-white font-bold py-3 rounded-xl shadow-md">Guardar</button></div></div>
    </div>

    <!-- Modal: Nuevo Viaje -->
    <div v-if="mostrarModalViaje" class="fixed inset-0 bg-gray-900 bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-3xl w-full max-w-lg p-8 shadow-2xl"><h2 class="text-2xl font-bold mb-6 text-gray-800">Apertura de Viaje</h2><div class="space-y-5"><div><label class="block text-xs font-bold text-gray-400 uppercase mb-1">1. Tipo de Operación</label><select v-model="nuevoViaje.tipo_operacion" class="w-full border border-gray-300 p-4 rounded-2xl bg-gray-50 font-black"><option value="ACOPIO">ACOPIO (Compra)</option><option value="MAQUILA">MAQUILA (Servicio)</option></select></div><div v-if="nuevoViaje.tipo_operacion === 'ACOPIO'" class="space-y-5 border-t border-gray-100 pt-5"><div><label class="block text-xs font-bold text-gray-400 uppercase mb-1">Acopiador</label><select v-model="nuevoViaje.acopiador_id" class="w-full border border-gray-300 p-4 rounded-2xl outline-none font-bold"><option value="" disabled>-- Seleccionar --</option><option v-for="a in acopiadores" :value="a.id" :key="a.id">{{ a.nombre }}</option></select></div><div><label class="block text-xs font-bold text-gray-400 uppercase mb-1">Placa</label><input v-model="nuevoViaje.placa" placeholder="ABC-123" class="w-full border border-gray-300 p-4 rounded-2xl uppercase font-bold" /></div></div><div v-if="nuevoViaje.tipo_operacion === 'MAQUILA'" class="space-y-5 border-t border-gray-100 pt-5"><div><label class="block text-xs font-bold text-purple-500 uppercase mb-1">Cliente</label><select v-model="nuevoViaje.cliente_id" class="w-full border border-purple-200 p-4 rounded-2xl outline-none font-bold"><option value="" disabled>-- Seleccionar --</option><option v-for="c in clientes" :value="c.id" :key="c.id">{{ c.nombre }}</option></select></div></div></div><div class="mt-8 flex gap-4"><button @click="mostrarModalViaje = false" class="flex-1 bg-gray-100 py-4 rounded-2xl font-bold text-gray-600">Cancelar</button><button @click="registrarViaje" class="flex-1 bg-emerald-500 text-white py-4 rounded-2xl font-bold shadow-md">Abrir Viaje</button></div></div>
    </div>

    <!-- Modal: Editar Pesada -->
    <div v-if="mostrarModalEdicionPesada" class="fixed inset-0 bg-gray-900 bg-opacity-60 flex items-center justify-center z-[60] p-4 backdrop-blur-sm">
      <div class="bg-white rounded-3xl w-full max-w-md p-8 shadow-2xl"><h2 class="text-2xl font-bold mb-6 text-gray-800">Corregir Pesada #{{pesadaEditandoViaje.numero_tarima}}</h2><div class="space-y-4"><div><label class="text-xs font-bold text-gray-400">TIPO DE FRUTA</label><select v-model="pesadaEditandoViaje.tipo_fruta_id" class="w-full border p-3 rounded-xl"><option v-for="f in tiposFruta" :value="f.id" :key="f.id">{{f.nombre}}</option></select></div><div class="grid grid-cols-2 gap-4"><div><label class="text-xs font-bold text-gray-400">PESO BRUTO</label><input type="number" step="0.5" v-model="pesadaEditandoViaje.peso_bruto" class="w-full border p-3 rounded-xl font-bold"></div><div><label class="text-xs font-bold text-gray-400">CAJAS</label><input type="number" v-model="pesadaEditandoViaje.cantidad_cajas" class="w-full border p-3 rounded-xl font-bold"></div><div><label class="text-xs font-bold text-orange-400">TARA CAJA</label><input type="number" step="0.01" v-model="pesadaEditandoViaje.tara_caja" class="w-full border p-3 rounded-xl font-bold text-orange-600 bg-orange-50"></div><div><label class="text-xs font-bold text-orange-400">TARA TARIMA</label><input type="number" step="0.1" v-model="pesadaEditandoViaje.tara_tarima" class="w-full border p-3 rounded-xl font-bold text-orange-600 bg-orange-50"></div></div></div><div class="flex gap-4 mt-8"><button @click="mostrarModalEdicionPesada = false" class="flex-1 bg-gray-100 py-3 rounded-xl font-bold text-gray-600">Cancelar</button><button @click="guardarEdicionPesada" class="flex-1 bg-blue-500 text-white font-bold py-3 rounded-xl shadow-md">Guardar</button></div></div>
    </div>

    <!-- Modal: Editar Viaje -->
    <div v-if="mostrarModalEdicionViaje" class="fixed inset-0 bg-gray-900 bg-opacity-50 flex items-center justify-center z-[60] p-4 backdrop-blur-sm">
      <div class="bg-white rounded-3xl w-full max-w-lg p-8 shadow-2xl"><h2 class="text-2xl font-bold mb-6 text-gray-800">Editar Viaje #{{viajeEditando.id}}</h2><div class="space-y-5"><div><label class="block text-xs font-bold text-gray-400 uppercase mb-1">Tipo de Operación</label><select v-model="viajeEditando.tipo_operacion" class="w-full border border-gray-300 p-4 rounded-2xl bg-gray-50 font-black"><option value="ACOPIO">ACOPIO (Compra)</option><option value="MAQUILA">MAQUILA (Servicio)</option></select></div><div v-if="viajeEditando.tipo_operacion === 'ACOPIO'" class="space-y-5 border-t border-gray-100 pt-5"><div><label class="block text-xs font-bold text-gray-400 uppercase mb-1">Acopiador</label><select v-model="viajeEditando.acopiador_id" class="w-full border border-gray-300 p-4 rounded-2xl outline-none font-bold"><option v-for="a in acopiadores" :value="a.id" :key="a.id">{{ a.nombre }}</option></select></div><div><label class="block text-xs font-bold text-gray-400 uppercase mb-1">Placa</label><input v-model="viajeEditando.placa" class="w-full border border-gray-300 p-4 rounded-2xl uppercase font-bold" /></div></div><div v-if="viajeEditando.tipo_operacion === 'MAQUILA'" class="space-y-5 border-t border-gray-100 pt-5"><div><label class="block text-xs font-bold text-purple-500 uppercase mb-1">Cliente</label><select v-model="viajeEditando.cliente_id" class="w-full border border-purple-200 p-4 rounded-2xl outline-none font-bold"><option v-for="c in clientes" :value="c.id" :key="c.id">{{ c.nombre }}</option></select></div></div></div><div class="mt-8 flex gap-4"><button @click="mostrarModalEdicionViaje = false" class="flex-1 bg-gray-100 py-4 rounded-2xl font-bold text-gray-600">Cancelar</button><button @click="guardarEdicionViaje" class="flex-1 bg-blue-500 text-white py-4 rounded-2xl font-bold shadow-md">Guardar Cambios</button></div></div>
    </div>

    <!-- Modal: Crear Tarima Manual -->
    <!-- Modal: Crear Tarima Manual -->
<div v-if="modalCrearTarimaManual" class="fixed inset-0 bg-gray-900 bg-opacity-60 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
  <div class="bg-white rounded-3xl w-full max-w-lg p-8 shadow-2xl">
    <h2 class="text-2xl font-bold mb-6 text-gray-800">✨ Crear Tarima Manual</h2>
    
    <div class="space-y-4">
      <!-- Viaje - Ahora es OPCIONAL -->
      <div>
        <label class="block text-sm font-bold text-gray-600 mb-1">
          Viaje (Dueño) - <span class="text-gray-400 font-normal">Opcional</span>
        </label>
        <select v-model="nuevaTarimaManual.viaje_id" class="w-full border p-3 rounded-xl bg-white">
          <option :value="null">-- Sin viaje asociado (Inventario general) --</option>
          <option v-for="v in viajes" :key="v.id" :value="v.id">
            Viaje #{{ v.id }} - {{ nombreResponsableViaje(v) }} ({{ v.tipo_operacion }})
          </option>
        </select>
        <p class="text-xs text-gray-400 mt-1">Si no seleccionas un viaje, la tarima quedará como inventario general</p>
      </div>
      
      <div>
        <label class="block text-sm font-bold text-gray-600 mb-1">Tipo de Fruta *</label>
        <select v-model="nuevaTarimaManual.tipo_fruta_id" class="w-full border p-3 rounded-xl">
          <option value="" disabled>-- Seleccionar fruta --</option>
          <option v-for="f in tiposFruta" :key="f.id" :value="f.id">{{ f.nombre }}</option>
        </select>
      </div>
      
      <div>
        <label class="block text-sm font-bold text-gray-600 mb-1">Identificador de Tarima *</label>
        <input v-model="nuevaTarimaManual.numero_tarima_display" placeholder="Ej: T-100, MIX-01, INV-001" class="w-full border p-3 rounded-xl font-mono">
        <p class="text-xs text-gray-400 mt-1">Ejemplo: T-001, INVENTARIO-01, AJUSTE-01</p>
      </div>
      
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-sm font-bold text-gray-600 mb-1">Cantidad de Cajas *</label>
          <input type="number" v-model.number="nuevaTarimaManual.cantidad_cajas" class="w-full border p-3 rounded-xl" min="1">
        </div>
        <div>
          <label class="block text-sm font-bold text-gray-600 mb-1">Peso Neto (kg) *</label>
          <input type="number" step="0.1" v-model.number="nuevaTarimaManual.peso_neto" class="w-full border p-3 rounded-xl" min="0">
        </div>
      </div>
      
      <div>
        <label class="block text-sm font-bold text-gray-600 mb-1">Notas/Referencia (opcional)</label>
        <textarea v-model="nuevaTarimaManual.notas_referencia" rows="2" class="w-full border p-3 rounded-xl" placeholder="Ej: Ajuste manual de inventario, Tarima de reserva, etc."></textarea>
      </div>
    </div>
    
    <div class="mt-8 flex gap-4">
      <button @click="modalCrearTarimaManual = false" class="flex-1 bg-gray-100 py-3 rounded-2xl font-bold text-gray-600 hover:bg-gray-200 transition">Cancelar</button>
      <button @click="crearTarimaManual" :disabled="cargando" class="flex-1 bg-amber-500 text-white py-3 rounded-2xl font-bold shadow-md hover:bg-amber-600 transition">
        {{ cargando ? 'Creando...' : '✨ Crear Tarima' }}
      </button>
    </div>
  </div>
</div>

  </div>
</template>

<style>
.animate-fade-in { animation: fadeIn 0.3s ease-out; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
</style>