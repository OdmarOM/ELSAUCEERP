<script setup>
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'

//const API_URL = 'http://127.0.0.1:8000/api'
//const API_URL = 'http://192.168.50.101:8000/api'
const API_URL = '/api'

const pestanaActual = ref('notas')
const subPestanaNotas = ref('captura')
const vistaConciliacion = ref('historial')
const cargando = ref(false)
const viajesSalida = ref([])
const tarimasDetalleSalida = ref([])
const mostrarModalDetalleSalida = ref(false)
const salidaSeleccionada = ref(null)

// Variables para Maquilas y Datos Facturacion Salidas
const maquilasCerradas = ref([])
const mostrarModalCostoMaquila = ref(false)
const maquilaSeleccionada = ref(null)
const costoMaquila = ref(0.0)

const mostrarModalFactura = ref(false)
const viajeSalidaFacturando = ref(null)
const datosFactura = ref({ peso_cliente: 0.0, numero_factura: '', fecha_facturacion: '', fecha_vencimiento: '' })

const nuevoViajeSalida = ref({ cliente_id: '', placa: '', precio_kg_venta: 0.0, fecha_salida: '', numero_guia: '' })

const crearViajeSalida = async () => {
  if (!nuevoViajeSalida.value.cliente_id || !nuevoViajeSalida.value.placa || nuevoViajeSalida.value.precio_kg_venta <= 0) {
    alert('Por favor completa todos los campos y establece un precio válido.')
    return
  }

  cargando.value = true
  try {
    const res = await fetch(`${API_URL}/viajes-salida`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(nuevoViajeSalida.value)
    })
    if (res.ok) {
      nuevoViajeSalida.value = { cliente_id: '', placa: '', precio_kg_venta: 0.0, fecha_salida: '', numero_guia: '' }
      alert("Viaje planeado exitosamente. Ahora el operador de báscula podrá cargarlo.")
      await fetchCatalogos()
    }
  } catch (e) {
    console.error('Error planeando viaje de salida:', e)
    alert('Error al planear viaje de salida')
  } finally {
    cargando.value = false
  }
}

const mostrarModalEdicionSalida = ref(false)
const salidaEditando = ref({})

const abrirEdicionSalida = (viaje) => {
  salidaEditando.value = { ...viaje }
  mostrarModalEdicionSalida.value = true
}

const guardarEdicionSalida = async () => {
  cargando.value = true
  try {
    const res = await fetch(`${API_URL}/viajes-salida/${salidaEditando.value.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(salidaEditando.value)
    })
    if (res.ok) {
      mostrarModalEdicionSalida.value = false
      await fetchCatalogos()
    } else {
      alert('Error al guardar cambios del viaje.')
    }
  } catch (e) {
    console.error(e)
    alert('Error actualizando viaje')
  } finally {
    cargando.value = false
  }
}

const eliminarSalida = async (id) => {
  if (!confirm('¿Estás seguro de eliminar este viaje de salida?')) return
  cargando.value = true
  try {
    const res = await fetch(`${API_URL}/viajes-salida/${id}`, { method: 'DELETE' })
    if (res.ok) {
      await fetchCatalogos()
    } else {
      const data = await res.json()
      alert(data.detail || 'Error al eliminar viaje.')
    }
  } catch (e) {
    console.error(e)
    alert('Error al eliminar viaje')
  } finally {
    cargando.value = false
  }
}

const acopiadores = ref([])
const proveedores = ref([])
const clientes = ref([])
const tiposFruta = ref([])
const viajes = ref([])
const notas = ref([])
const registrosBascula = ref([])
const pagos = ref([])

let intervaloCarga = null

const formatearPeso = (valor) => parseFloat(valor || 0).toFixed(2)

// ================= MODELOS =================
const nuevoAcopiador = ref({ nombre: '', telefono: '' })
const nuevoProveedor = ref({ nombre: '', contacto: '' })
const nuevoCliente = ref({ nombre: '', contacto: '' })
const nuevoTipoFruta = ref({ nombre: '', descripcion: '' })

// Función para obtener fecha local en formato YYYY-MM-DD (evita problema de zona horaria)
const getFechaLocal = () => {
  const fecha = new Date()
  const year = fecha.getFullYear()
  const month = String(fecha.getMonth() + 1).padStart(2, '0')
  const day = String(fecha.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

// Función para formatear fecha sin conversión de zona horaria (evita mostrar día anterior)
const formatearFecha = (fechaStr) => {
  if (!fechaStr) return 'N/A'
  // Extraer solo la parte de la fecha (YYYY-MM-DD) ignorando la hora si existe
  const fechaSolo = fechaStr.split('T')[0]
  const [year, month, day] = fechaSolo.split('-')
  return `${day}/${month}/${year}`
}

// NOTA CON FECHA MANUAL Y CÁLCULOS
const nuevaNota = ref({ fecha: getFechaLocal(), folio: '', proveedor_id: '', tipo_fruta_id: '', cantidad_cajas: '', tara_tarima: '', tara_caja: '', peso_bruto: '', peso_neto: 0, precio_kg: '', total_monetario: 0 })
const nuevoPago = ref({ proveedor_id: '', folio_pago: '', fecha_pago: getFechaLocal(), metodo_pago: 'TRANSFERENCIA', monto_total: 0, nota_ids: [] })

const fechaFiltroConciliacion = ref(getFechaLocal())
const fechaFiltroNotasHistorial = ref(getFechaLocal())

// Modales
const mostrarModalPago = ref(false)
const mostrarModalDetallePago = ref(false)
const modoEdicionPago = ref(false)
const pagoSeleccionado = ref(null)
const pagoEditando = ref({})

const editandoNota = ref(null)
const mostrarModalEdicionNota = ref(false)

const mostrarModalEdicionCatalogo = ref(false)
const tipoCatalogoEdicion = ref('') 
const itemEditando = ref({})

const mostrarModalAdminViaje = ref(false)
const viajeAdminEditando = ref({})

// LÓGICA DE CÁLCULO EN NUEVA NOTA (AUTO)
watch([
  () => nuevaNota.value.peso_bruto,
  () => nuevaNota.value.cantidad_cajas,
  () => nuevaNota.value.tara_tarima,
  () => nuevaNota.value.tara_caja,
  () => nuevaNota.value.precio_kg
], () => {
  const bruto = parseFloat(nuevaNota.value.peso_bruto) || 0
  const cajas = parseInt(nuevaNota.value.cantidad_cajas) || 0
  const t_tarima = parseFloat(nuevaNota.value.tara_tarima) || 0
  const t_caja = parseFloat(nuevaNota.value.tara_caja) || 0
  const precio = parseFloat(nuevaNota.value.precio_kg) || 0

  const tara_total = t_tarima + (t_caja * cajas)
  nuevaNota.value.peso_neto = Math.max(0, bruto - tara_total).toFixed(2)
  nuevaNota.value.total_monetario = (nuevaNota.value.peso_neto * precio).toFixed(2)
})

watch(() => nuevoPago.value.nota_ids, (idsSeleccionados) => {
  nuevoPago.value.monto_total = idsSeleccionados.reduce((sum, id) => sum + parseFloat(notas.value.find(n => n.id === id)?.total_monetario || 0), 0).toFixed(2)
}, { deep: true })

const fetchCatalogos = async () => {
  try {
    const [resAcop, resProv, resCli, resFruta, resViajes, resNotas, resRegistros, resPagos, resViajesSalida, resMaquilas] = await Promise.all([
      fetch(`${API_URL}/acopiadores`), fetch(`${API_URL}/proveedores`), fetch(`${API_URL}/clientes`), fetch(`${API_URL}/tipos-fruta`),
      fetch(`${API_URL}/viajes`), fetch(`${API_URL}/notas`), fetch(`${API_URL}/registros-bascula`), fetch(`${API_URL}/pagos`), fetch(`${API_URL}/viajes-salida`),
      fetch(`${API_URL}/maquilas/cerradas`)
    ])
    acopiadores.value = await resAcop.json(); proveedores.value = await resProv.json(); clientes.value = await resCli.json();
    tiposFruta.value = await resFruta.json(); viajes.value = await resViajes.json(); notas.value = await resNotas.json();
    registrosBascula.value = await resRegistros.json(); pagos.value = await resPagos.json(); viajesSalida.value = await resViajesSalida.json();
    maquilasCerradas.value = await resMaquilas.json();
  } catch (e) { console.error('Error auto-update:', e) }
}

// Métodos para facturación de salidas y cobros de maquilas
const abrirFacturacion = (viaje) => {
  viajeSalidaFacturando.value = viaje
  // Estimar el peso a partir del total físico del viaje como base
  datosFactura.value = {
    peso_cliente: viaje.peso_total_fisico || 0,
    numero_factura: '',
    fecha_facturacion: new Date().toISOString().split('T')[0],
    fecha_vencimiento: ''
  }
  mostrarModalFactura.value = true
}

const guardarFactura = async () => {
  if (datosFactura.value.peso_cliente <= 0 || !datosFactura.value.numero_factura) {
    alert("Por favor ingresa un peso de cliente válido y número de factura.")
    return
  }
  cargando.value = true
  try {
    const res = await fetch(`${API_URL}/viajes-salida/${viajeSalidaFacturando.value.id}/datos-factura`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(datosFactura.value)
    })
    if (res.ok) {
      mostrarModalFactura.value = false
      alert("Facturación y merma registradas correctamente. Cuenta por cobrar enviada a finanzas.")
      await fetchCatalogos()
    } else {
      alert("Error al registrar factura")
    }
  } catch (e) {
    console.error(e)
    alert("Error al registrar factura")
  } finally {
    cargando.value = false
  }
}

const abrirCostoMaquila = (maquila) => {
  maquilaSeleccionada.value = maquila
  costoMaquila.value = 0.0
  mostrarModalCostoMaquila.value = true
}

const guardarCostoMaquila = async () => {
  if (costoMaquila.value <= 0) {
    alert("Por favor ingresa un costo válido.")
    return
  }
  cargando.value = true
  try {
    const res = await fetch(`${API_URL}/maquilas/${maquilaSeleccionada.value.id}/generar-cobro`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ costo: costoMaquila.value })
    })
    if (res.ok) {
      mostrarModalCostoMaquila.value = false
      alert("Costo registrado. Se ha enviado a cuentas por cobrar.")
      await fetchCatalogos()
    } else {
      alert("Error al registrar costo")
    }
  } catch (e) {
    console.error(e)
    alert("Error al registrar costo")
  } finally {
    cargando.value = false
  }
}

onMounted(() => { fetchCatalogos(); intervaloCarga = setInterval(fetchCatalogos, 5000) })
onUnmounted(() => { if (intervaloCarga) clearInterval(intervaloCarga) })

const fechaFiltroTarimas = ref(new Date().toISOString().split('T')[0])
const fechaFiltroSalidas = ref(new Date().toISOString().split('T')[0])

const registrosBasculaFiltrados = computed(() => {
  return registrosBascula.value.filter(r => {
    const v = viajes.value.find(viaje => viaje.id === r.viaje_id)
    if (!v || !v.fecha_entrada) return false
    return v.fecha_entrada.startsWith(fechaFiltroTarimas.value)
  })
})

const viajesSalidaFiltrados = computed(() => {
  return viajesSalida.value.filter(v => {
    const fecha = v.fecha_salida || v.fecha_entrada
    if (!fecha) return false
    return fecha.startsWith(fechaFiltroSalidas.value)
  })
})

const notasOrdenadas = computed(() => [...notas.value].sort((a, b) => b.id - a.id))
const notasLibres = computed(() => notasOrdenadas.value.filter(n => n.viaje_id === null))
const notasPendientes = computed(() => notasOrdenadas.value.filter(n => n.estado_pago === 'PENDIENTE' && n.viaje_id !== null))
const totalDeudaPendiente = computed(() => notasPendientes.value.reduce((sum, n) => sum + parseFloat(n.total_monetario), 0).toFixed(2))
const notasDelProveedorSeleccionado = computed(() => notasPendientes.value.filter(n => n.proveedor_id === nuevoPago.value.proveedor_id))
const viajesCerradosParaConciliar = computed(() => viajes.value.filter(v => v.estado === 'CERRADO' && v.tipo_operacion === 'ACOPIO'))
const viajesConciliadosFiltrados = computed(() => viajes.value.filter(v => v.estado === 'CONCILIADO' && v.fecha_entrada.startsWith(fechaFiltroConciliacion.value)).sort((a, b) => b.id - a.id))

const notasHistorialFiltradas = computed(() => {
  return notasOrdenadas.value.filter(n => n.fecha && n.fecha.startsWith(fechaFiltroNotasHistorial.value))
})

const deudasAgrupadas = computed(() => {
  const grupos = {}
  notasPendientes.value.forEach(n => {
    if (!grupos[n.proveedor_id]) {
      grupos[n.proveedor_id] = { id: n.proveedor_id, nombre: n.proveedor_nombre, totalDeuda: 0, notas: [] }
    }
    grupos[n.proveedor_id].notas.push(n)
    grupos[n.proveedor_id].totalDeuda += parseFloat(n.total_monetario)
  })
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
  try {
    await fetch(`${API_URL}/notas`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({...nuevaNota.value, viaje_id: null}) });
    nuevaNota.value = { fecha: getFechaLocal(), folio: '', proveedor_id: '', tipo_fruta_id: '', cantidad_cajas: '', tara_tarima: '', tara_caja: '', peso_bruto: '', peso_neto: 0, precio_kg: '', total_monetario: 0 };
    await fetchCatalogos()
  } finally { cargando.value = false }
}
const eliminarNota = async (id) => { 
  if(!confirm("¿Eliminar nota?")) return;
  cargando.value = true; try { await fetch(`${API_URL}/notas/${id}`, { method: 'DELETE' }); await fetchCatalogos() } finally { cargando.value = false } 
}
const prepararEdicionNota = (nota) => { 
  editandoNota.value = { ...nota } 
  if (editandoNota.value.fecha) editandoNota.value.fecha = editandoNota.value.fecha.split('T')[0]
  mostrarModalEdicionNota.value = true 
}
const guardarCambiosNota = async () => {
  cargando.value = true
  try {
    await fetch(`${API_URL}/notas/${editandoNota.value.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(editandoNota.value) })
    mostrarModalEdicionNota.value = false; await fetchCatalogos()
  } finally { cargando.value = false }
}

// ================= CONCILIACIÓN Y VIAJES =================
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
  try { await fetch(`${API_URL}/viajes/${viajeAConciliarId.value}/conciliar`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nota_ids: notasSeleccionadasParaConciliar.value, peso_fisico: detallesViajeAConciliar.value.pesoFisicoTotal, peso_teorico: pesoTeoricoSeleccionado.value, difference: diferenciaConciliacion.value }) }); vistaConciliacion.value = 'historial'; await fetchCatalogos() } finally { cargando.value = false }
}
const deshacerConciliacion = async (viajeId) => {
  if (!confirm("¿Seguro que quieres deshacer esta conciliación? Las notas quedarán libres nuevamente.")) return
  cargando.value = true; try { await fetch(`${API_URL}/viajes/${viajeId}/deshacer-conciliacion`, { method: 'POST' }); await fetchCatalogos() } finally { cargando.value = false }
}

// Función para abrir la edición del Viaje desde la tabla de PESADAS (Gestión de Tarimas)
const abrirAdminViajePorTarima = (viajeId) => {
  const v = viajes.value.find(vi => vi.id === viajeId)
  if(v) {
    if (v.estado === 'CONCILIADO') {
      alert("Bloqueado: El viaje asociado a esta pesada ya está CONCILIADO contablemente.\n\nPara poder modificar quién es el Acopiador o Cliente, debes ir a la pestaña 'Conciliación de Viajes' y Deshacer la conciliación primero.")
      return
    }
    viajeAdminEditando.value = { ...v }
    mostrarModalAdminViaje.value = true
  } else {
    alert("Error: No se encontró el viaje.")
  }
}

const guardarAdminViaje = async () => {
  cargando.value = true
  try {
    const res = await fetch(`${API_URL}/viajes/${viajeAdminEditando.value.id}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(viajeAdminEditando.value)
    })
    if(!res.ok) { const err = await res.json(); alert(err.detail || "Error al modificar viaje") } 
    else { mostrarModalAdminViaje.value = false; await fetchCatalogos() }
  } finally { cargando.value = false }
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
  try { await fetch(`${API_URL}/pagos/${pagoEditando.value.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(pagoEditando.value) }); mostrarModalDetallePago.value = false; await fetchCatalogos() } finally { cargando.value = false }
}

const verDetalleSalida = async (viaje) => {
  salidaSeleccionada.value = viaje
  mostrarModalDetalleSalida.value = true

  try {
    const res = await fetch(`${API_URL}/viajes-salida/${viaje.id}/tarimas`)
    tarimasDetalleSalida.value = await res.json()
  } catch (e) {
    console.error('Error cargando detalle de salida:', e)
  }
}

const anularPago = async () => {
  if (!confirm("🚨 ¿ESTÁS SEGURO DE ANULAR ESTE PAGO?\n\nEl pago se eliminará y las facturas/notas asociadas volverán a aparecer deudas pendientes.")) return
  cargando.value = true
  try { await fetch(`${API_URL}/pagos/${pagoSeleccionado.value.id}`, { method: 'DELETE' }); mostrarModalDetallePago.value = false; await fetchCatalogos() } finally { cargando.value = false }
}

// ================= HELPERS Y BÚSQUEDAS =================
const nombreResponsableViaje = (v) => {
  if (!v) return 'Desconocido'
  if (v.tipo_operacion === 'MAQUILA') {
    return clientes.value.find(c => c.id === v.cliente_id)?.nombre || 'Cliente Borrado'
  } else {
    return acopiadores.value.find(a => a.id === v.acopiador_id)?.nombre || 'Acopiador Borrado'
  }
}

const formatoViajeSelect = (v) => `Viaje #${v.id} - ${nombreResponsableViaje(v)} - ${formatearFecha(v.fecha_entrada)}`

const obtenerDuenoViaje = (viaje_id) => {
  const v = viajes.value.find(vi => vi.id === viaje_id)
  return nombreResponsableViaje(v)
}

const obtenerTipoViaje = (viaje_id) => {
  const v = viajes.value.find(vi => vi.id === viaje_id)
  return v ? v.tipo_operacion : ''
}

// ================= EDICIÓN DE PESADAS (ADMIN) =================
const eliminarPesadaAdmin = async (id) => {
  if (!confirm("🚨 ADVERTENCIA: Estás a punto de eliminar esta pesada.\nSi está en el cuarto frío desaparecerá.\n¿Deseas continuar?")) return
  cargando.value = true
  try {
    const res = await fetch(`${API_URL}/registros-bascula/${id}`, { method: 'DELETE' })
    if(!res.ok) { const err = await res.json(); alert(err.detail || "Error en eliminación") } 
    else { await fetchCatalogos() }
  } finally { cargando.value = false }
}

const mostrarModalEdicionPesada = ref(false)
const pesadaEditando = ref({})

const abrirEdicionPesada = (pesada) => {
  pesadaEditando.value = { ...pesada }
  mostrarModalEdicionPesada.value = true
}

const guardarEdicionPesada = async () => {
  cargando.value = true
  try {
    const res = await fetch(`${API_URL}/registros-bascula/${pesadaEditando.value.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(pesadaEditando.value) })
    if(!res.ok) { const err = await res.json(); alert(err.detail || "Error al actualizar") } 
    else { mostrarModalEdicionPesada.value = false; await fetchCatalogos() }
  } finally { cargando.value = false }
}
</script>

<template>
  <div class="min-h-screen bg-gray-50 p-6 md:p-12 relative">
    <div v-if="cargando" class="fixed inset-0 bg-white/60 backdrop-blur-sm z-50 flex items-center justify-center"><div class="bg-white p-6 rounded-3xl shadow-xl flex flex-col items-center"><div class="w-10 h-10 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin mb-3"></div><span class="text-gray-700 font-medium">Procesando...</span></div></div>

    <div class="flex justify-between items-center mb-8">
      <h1 class="text-4xl font-light tracking-tight text-gray-800 mt-1">Administración y Finanzas</h1>
      <span class="text-xs font-bold text-gray-400 bg-white px-4 py-2 border rounded-full shadow-sm flex items-center"><span class="w-2 h-2 rounded-full bg-emerald-500 mr-2 animate-pulse"></span> OFICINA</span>
    </div>

    <div class="flex flex-wrap gap-4 mb-8">
      <button @click="pestanaActual = 'notas'" :class="{'bg-emerald-500 text-white': pestanaActual === 'notas', 'bg-white text-gray-600': pestanaActual !== 'notas'}" class="px-5 py-2.5 rounded-2xl text-sm transition shadow-sm border font-medium">📝 Captura y Visualización de Notas</button>
      <button @click="pestanaActual = 'tarimas'" :class="{'bg-emerald-500 text-white': pestanaActual === 'tarimas', 'bg-white text-gray-600': pestanaActual !== 'tarimas'}" class="px-5 py-2.5 rounded-2xl text-sm transition shadow-sm border font-medium">📦 Gestión de Pesadas</button>
      <button @click="pestanaActual = 'conciliacion'; vistaConciliacion = 'historial'" :class="{'bg-emerald-500 text-white': pestanaActual === 'conciliacion', 'bg-white text-gray-600': pestanaActual !== 'conciliacion'}" class="px-5 py-2.5 rounded-2xl text-sm transition shadow-sm border font-medium">📊 Conciliación de Viajes</button>
      <button @click="pestanaActual = 'salidas'" :class="{'bg-emerald-500 text-white': pestanaActual === 'salidas', 'bg-white text-gray-600': pestanaActual !== 'salidas'}" class="px-5 py-2.5 rounded-2xl text-sm transition shadow-sm border font-medium">🚚 Planear Salida</button>
      <button @click="pestanaActual = 'maquilas'" :class="{'bg-emerald-500 text-white': pestanaActual === 'maquilas', 'bg-white text-gray-600': pestanaActual !== 'maquilas'}" class="px-5 py-2.5 rounded-2xl text-sm transition shadow-sm border font-medium">🏭 Maquilas Cerradas</button>
      <button @click="pestanaActual = 'pagos'" :class="{'bg-emerald-500 text-white': pestanaActual === 'pagos', 'bg-white text-gray-600': pestanaActual !== 'pagos'}" class="px-5 py-2.5 rounded-2xl text-sm transition shadow-sm border font-medium">💰 Pagos</button>
      <button @click="pestanaActual = 'catalogos'" :class="{'bg-emerald-500 text-white': pestanaActual === 'catalogos', 'bg-white text-gray-600': pestanaActual !== 'catalogos'}" class="px-5 py-2.5 rounded-2xl text-sm transition shadow-sm border font-medium">📇 Catálogos Base</button>
    </div>

    <div v-if="pestanaActual === 'notas'" class="space-y-6 animate-fade-in">
      <div class="flex gap-4 border-b pb-3">
        <button @click="subPestanaNotas = 'captura'" :class="subPestanaNotas === 'captura' ? 'border-b-2 border-emerald-500 font-bold text-emerald-600' : 'text-gray-400 font-medium'" class="pb-1 text-sm px-2">Capturar Nueva Nota</button>
        <button @click="subPestanaNotas = 'historial'" :class="subPestanaNotas === 'historial' ? 'border-b-2 border-emerald-500 font-bold text-emerald-600' : 'text-gray-400 font-medium'" class="pb-1 text-sm px-2">Visualizador e Historial General</button>
      </div>

      <div v-if="subPestanaNotas === 'captura'" class="space-y-8">
        <div class="bg-white p-8 rounded-3xl shadow-sm border">
          <h2 class="text-xl font-medium mb-4 text-gray-700">Registrar Nota Detallada de Proveedor</h2>
          <div class="grid grid-cols-1 md:grid-cols-4 gap-6 mb-6">
            <div><label class="block text-sm text-gray-500 mb-1">Fecha Emisión</label><input type="date" v-model="nuevaNota.fecha" class="w-full border border-gray-200 p-3.5 rounded-2xl text-sm outline-none font-bold text-gray-700" /></div>
            <div><label class="block text-sm text-gray-500 mb-1">Folio Físico</label><input v-model="nuevaNota.folio" placeholder="Ej. A-1234" class="w-full border border-gray-200 p-3.5 rounded-2xl text-sm outline-none font-bold text-emerald-700 uppercase" /></div>
            <div><label class="block text-sm text-gray-500 mb-1">Proveedor</label><select v-model="nuevaNota.proveedor_id" class="w-full border border-gray-200 p-3.5 rounded-2xl text-sm outline-none"><option value="" disabled>Selecciona...</option><option v-for="p in proveedores" :value="p.id" :key="p.id">{{ p.nombre }}</option></select></div>
            <div><label class="block text-sm text-gray-500 mb-1">Tipo de Fruta</label><select v-model="nuevaNota.tipo_fruta_id" class="w-full border border-gray-200 p-3.5 rounded-2xl text-sm outline-none"><option value="" disabled>Selecciona...</option><option v-for="f in tiposFruta" :value="f.id" :key="f.id">{{ f.nombre }}</option></select></div>
          </div>
          <div class="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6 border-t pt-6">
            <div><label class="block text-sm text-gray-500 mb-1">Peso Bruto (kg)</label><input type="number" v-model="nuevaNota.peso_bruto" class="w-full border p-3.5 rounded-2xl text-sm outline-none font-medium" /></div>
            <div><label class="block text-sm text-gray-500 mb-1">Cajas</label><input type="number" v-model="nuevaNota.cantidad_cajas" class="w-full border p-3.5 rounded-2xl text-sm outline-none font-medium" /></div>
            <div><label class="block text-sm text-gray-500 mb-1">Tara Tarima (kg)</label><input type="number" step="0.1" v-model="nuevaNota.tara_tarima" placeholder="21.0" class="w-full border p-3.5 rounded-2xl text-sm outline-none font-medium" /></div>
            <div><label class="block text-sm text-gray-500 mb-1">Tara Caja (kg)</label><input type="number" step="0.01" v-model="nuevaNota.tara_caja" placeholder="1.7" class="w-full border p-3.5 rounded-2xl text-sm outline-none font-medium" /></div>
            <div><label class="block text-sm text-gray-500 mb-1">Precio ($/kg)</label><input type="number" step="0.01" v-model="nuevaNota.precio_kg" class="w-full border p-3.5 rounded-2xl text-sm outline-none font-bold" /></div>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6 bg-gray-50 p-4 rounded-2xl border mb-6">
            <div class="flex justify-between items-center"><span class="text-sm text-gray-500 font-bold">Peso Neto Calculado:</span><span class="text-xl font-black text-gray-800">{{ nuevaNota.peso_neto }} kg</span></div>
            <div class="flex justify-between items-center"><span class="text-sm text-gray-500 font-bold">Total Liquidación Automático:</span><span class="text-xl font-black text-emerald-600">${{ nuevaNota.total_monetario }}</span></div>
          </div>
          <button @click="agregarNota" :disabled="cargando" class="bg-emerald-500 text-white px-8 py-3.5 rounded-2xl text-sm font-medium hover:bg-emerald-600 disabled:opacity-50 shadow-sm">Guardar Nota Calculada</button>
        </div>

        <div class="bg-white p-8 rounded-3xl shadow-sm border overflow-x-auto">
          <h2 class="text-xl font-medium mb-4 text-gray-700">Bandeja de Notas Libres (Por Conciliar)</h2>
          <table class="min-w-full text-left text-sm text-gray-600">
            <thead class="bg-gray-50 border-b"><tr><th class="p-3">Fecha</th><th class="p-3">Folio</th><th class="p-3">Proveedor</th><th class="p-3">Fruta</th><th class="p-3 text-right">P. Bruto</th><th class="p-3 text-right">P. Neto</th><th class="p-3 text-right">Total</th><th class="p-3 text-right">Acción</th></tr></thead>
            <tbody>
              <tr v-for="n in notasLibres" :key="n.id" class="border-b hover:bg-gray-50">
                <td class="p-3 text-gray-500 font-medium text-xs">{{ formatearFecha(n.fecha) }}</td>
                <td class="p-3 font-mono font-bold text-gray-800">{{ n.folio || 'S/F' }}</td>
                <td class="p-3 font-medium text-gray-800">{{ n.proveedor_nombre }}</td><td class="p-3">{{ n.fruta_nombre }}</td>
                <td class="p-3 text-right">{{ formatearPeso(n.peso_bruto) }}</td>
                <td class="p-3 text-right font-semibold text-blue-600">{{ formatearPeso(n.peso_neto) }}</td><td class="p-3 text-right font-bold text-emerald-600">${{ n.total_monetario }}</td>
                <td class="p-3 text-right">
                  <button @click="prepararEdicionNota(n)" class="text-blue-500 font-bold mr-3 hover:text-blue-700">✏️</button>
                  <button @click="eliminarNota(n.id)" :disabled="cargando" class="text-red-500 hover:text-red-700 font-medium">❌</button>
                </td>
              </tr>
              <tr v-if="notasLibres.length === 0"><td colspan="8" class="p-6 text-center text-gray-400">No hay notas libres pendientes.</td></tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-if="subPestanaNotas === 'historial'" class="space-y-6">
        <div class="flex justify-between items-center bg-white p-6 rounded-3xl border shadow-sm">
          <div><h2 class="text-lg font-bold text-gray-800">Visualizador General de Notas</h2><p class="text-xs text-gray-400 uppercase font-black">Auditoría por fecha de emisión</p></div>
          <input type="date" v-model="fechaFiltroNotasHistorial" class="border p-3 rounded-xl outline-none font-bold text-gray-700" />
        </div>
        <div class="bg-white p-8 rounded-3xl border overflow-x-auto shadow-sm">
          <table class="min-w-full text-left text-sm text-gray-600">
            <thead class="bg-gray-50 border-b"><tr><th class="p-3">Fecha</th><th class="p-3">Folio</th><th class="p-3">Viaje Asociado</th><th class="p-3">Proveedor</th><th class="p-3">Fruta</th><th class="p-3 text-center">Cajas</th><th class="p-3 text-right">Peso Neto</th><th class="p-3 text-right">Total</th><th class="p-3 text-center">Estado Pago</th></tr></thead>
            <tbody>
              <tr v-for="n in notasHistorialFiltradas" :key="n.id" class="border-b hover:bg-gray-50">
                <td class="p-3 text-gray-500 font-medium text-xs">{{ formatearFecha(n.fecha) }}</td>
                <td class="p-3 font-mono font-bold text-gray-800">{{ n.folio }}</td>
                <td class="p-3 font-bold text-blue-600">{{ n.viaje_id ? 'Viaje #' + n.viaje_id : 'LIBRE (Sin Conciliar)' }}</td>
                <td class="p-3 font-medium">{{ n.proveedor_nombre }}</td>
                <td class="p-3">{{ n.fruta_nombre }}</td>
                <td class="p-3 text-center">{{ n.cantidad_cajas }}</td>
                <td class="p-3 text-right font-medium">{{ formatearPeso(n.peso_neto) }} kg</td>
                <td class="p-3 text-right font-black text-emerald-600">${{ n.total_monetario }}</td>
                <td class="p-3 text-center">
                  <span :class="n.estado_pago === 'PAGADO' ? 'bg-emerald-100 text-emerald-700' : 'bg-orange-100 text-orange-700'" class="px-2.5 py-1 rounded-full text-xs font-black">
                    {{ n.estado_pago }}
                  </span>
                </td>
                <td class="p-3 text-right">
                  <button @click="prepararEdicionNota(n)" class="text-blue-500 font-bold mr-3 hover:text-blue-700">✏️</button>
                  <button @click="eliminarNota(n.id)" :disabled="cargando" class="text-red-500 hover:text-red-700 font-medium">❌</button>
                </td>
              </tr>
              <tr v-if="notasHistorialFiltradas.length === 0"><td colspan="8" class="p-6 text-center text-gray-400">No se encontraron notas registradas en esta fecha seleccionada.</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div v-if="pestanaActual === 'tarimas'" class="animate-fade-in space-y-6">
      <div class="flex justify-between items-center bg-white p-6 rounded-3xl border shadow-sm">
        <div class="flex items-center gap-3">
          <label class="text-sm font-bold text-gray-500 uppercase ml-1">Filtrar por Fecha:</label>
          <input type="date" v-model="fechaFiltroTarimas" class="border p-3 rounded-xl outline-none font-bold text-gray-700 shadow-sm" />
        </div>
      </div>
      <div class="bg-white p-8 rounded-3xl shadow-sm border overflow-x-auto">
        <h2 class="text-2xl font-light mb-6 text-gray-700">Historial de Pesadas (Tarimas)</h2>
        <table class="min-w-full text-left text-sm text-gray-600">
          <thead class="bg-gray-50 border-b">
            <tr>
              <th class="p-3">Viaje</th>
              <th class="p-3">Propietario / Dueño</th>
              <th class="p-3">Tarima</th>
              <th class="p-3">Fruta</th>
              <th class="p-3 text-center">Cajas</th>
              <th class="p-3 text-right">Peso Bruto</th>
              <th class="p-3 text-right">Tara</th>
              <th class="p-3 text-right text-emerald-600">Peso Neto</th>
              <th class="p-3 text-center">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in registrosBasculaFiltrados" :key="r.id" class="border-b hover:bg-gray-50">
              <td class="p-3 font-bold text-blue-600">
                Viaje #{{ r.viaje_id }}
                <span class="block text-[10px] text-gray-400 font-black uppercase" :class="obtenerTipoViaje(r.viaje_id) === 'MAQUILA' ? 'text-purple-500' : ''">
                  {{ obtenerTipoViaje(r.viaje_id) }}
                </span>
              </td>
              <td class="p-3 font-bold text-gray-800">{{ obtenerDuenoViaje(r.viaje_id) }}</td>
              <td class="p-3 font-bold text-gray-600">T-#{{ r.numero_tarima }}</td>
              <td class="p-3">{{ r.fruta_nombre || 'N/A' }}</td>
              <td class="p-3 text-center font-medium">{{ r.cantidad_cajas }}</td>
              <td class="p-3 text-right">{{ formatearPeso(r.peso_bruto) }} kg</td>
              <td class="p-3 text-right text-orange-500">{{ formatearPeso(r.tara_total) }} kg</td>
              <td class="p-3 text-right font-black text-emerald-600">{{ formatearPeso(r.peso_neto) }} kg</td>
              <td class="p-3 text-center flex justify-center gap-2">
                <button @click="abrirAdminViajePorTarima(r.viaje_id)" class="text-purple-600 hover:scale-110 transition bg-purple-50 px-3 py-1.5 rounded-lg font-bold" title="Modificar Acopiador/Cliente del Viaje">🚚 Viaje</button>
                <button @click="abrirEdicionPesada(r)" class="text-blue-500 hover:scale-110 transition bg-blue-50 px-3 py-1.5 rounded-lg font-bold" title="Editar pesos y fruta de la tarima">📦 Tarima</button>
                <button @click="eliminarPesadaAdmin(r.id)" class="text-red-500 hover:scale-110 transition bg-red-50 px-3 py-1.5 rounded-lg font-bold">🗑️</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="pestanaActual === 'conciliacion'" class="animate-fade-in">
       <div v-if="vistaConciliacion === 'historial'" class="space-y-6">
        <div class="flex justify-between items-center bg-white p-6 rounded-3xl border shadow-sm"><input type="date" v-model="fechaFiltroConciliacion" class="border p-3 rounded-xl outline-none font-bold text-gray-700" /><button @click="iniciarNuevaConciliacion" class="bg-emerald-500 text-white px-8 py-3.5 rounded-2xl font-bold shadow-sm">+ Conciliar Nuevo</button></div>
        <div class="bg-white p-8 rounded-3xl border overflow-x-auto shadow-sm">
          <table class="min-w-full text-left text-sm text-gray-600"><thead class="bg-gray-50 border-b"><tr><th class="p-3">Viaje</th><th class="p-3">Tipo</th><th class="p-3">Responsable Operativo</th><th class="p-3 text-right">Físico</th><th class="p-3 text-right">Teórico</th><th class="p-3 text-right">Diferencia</th><th class="p-3 text-center">Gestión</th></tr></thead>
            <tbody>
              <tr v-for="v in viajes" :key="v.id" v-show="v.estado === 'CONCILIADO' && v.fecha_entrada.startsWith(fechaFiltroConciliacion)" class="border-b hover:bg-gray-50">
                <td class="p-3 font-bold">#{{ v.id }}</td>
                <td class="p-3"><span :class="v.tipo_operacion === 'MAQUILA' ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'" class="px-2 py-0.5 rounded text-xs font-bold">{{ v.tipo_operacion }}</span></td>
                <td class="p-3 font-medium text-gray-800">{{ nombreResponsableViaje(v) }}</td>
                <td class="p-3 text-right text-blue-600 font-bold">{{ formatearPeso(v.peso_total_fisico) }} kg</td>
                <td class="p-3 text-right text-orange-600 font-bold">{{ formatearPeso(v.peso_total_teorico) }} kg</td>
                <td class="p-3 text-right font-black" :class="v.diferencia_peso >= 0 ? 'text-emerald-500' : 'text-red-500'">{{ v.diferencia_peso > 0 ? '+' : ''}}{{ formatearPeso(v.diferencia_peso) }} kg</td>
                <td class="p-3 text-center flex items-center justify-center gap-2">
                  <button @click="deshacerConciliacion(v.id)" class="bg-orange-50 text-orange-600 border border-orange-200 px-3 py-1.5 rounded-xl text-xs font-bold hover:bg-orange-100">⚠️ Deshacer Conciliación</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      
      <div v-if="vistaConciliacion === 'formulario'" class="space-y-6">
        <button @click="vistaConciliacion = 'historial'" class="text-gray-500 font-medium">← Cancelar y Volver</button>
        <div class="bg-white p-6 rounded-3xl border shadow-sm"><select v-model="viajeAConciliarId" class="w-full border p-4 rounded-2xl text-lg font-medium outline-none"><option value="" disabled>-- Elige un viaje cerrado --</option><option v-for="v in viajesCerradosParaConciliar" :value="v.id" :key="v.id">{{ formatoViajeSelect(v) }}</option></select></div>
        <div v-if="detallesViajeAConciliar" class="grid grid-cols-2 gap-6">
          <div class="bg-white p-6 rounded-3xl border text-center shadow-sm"><span class="text-blue-600 block mb-1 font-bold">Peso Físico (Báscula)</span><span class="text-4xl font-black text-blue-700">{{ formatearPeso(detallesViajeAConciliar.pesoFisicoTotal) }} kg</span></div>
          <div class="bg-white p-6 rounded-3xl border text-center shadow-sm"><span class="text-orange-600 block mb-1 font-bold">Peso Teórico (Notas)</span><span class="text-4xl font-black text-orange-700">{{ formatearPeso(pesoTeoricoSeleccionado) }} kg</span></div>
        </div>
        <div v-if="detallesViajeAConciliar" class="bg-white p-6 rounded-3xl border shadow-sm">
          <h3 class="font-bold text-gray-700 mb-4">Selecciona las notas que amparan este viaje:</h3>
          <div class="space-y-2 max-h-60 overflow-y-auto pr-2">
            <label v-for="n in notasLibres" :key="n.id" class="flex items-center p-4 bg-gray-50 rounded-xl cursor-pointer border hover:bg-emerald-50 transition">
              <input type="checkbox" :value="n.id" v-model="notasSeleccionadasParaConciliar" class="w-6 h-6 text-emerald-500 mr-4 rounded">
              <div class="flex-1"><p class="text-sm font-bold text-gray-800">Folio: {{n.folio}} | {{ n.proveedor_nombre }}</p></div><div class="font-bold text-orange-600 text-lg">{{ formatearPeso(n.peso_neto) }} kg</div>
            </label>
          </div>
        </div>
        <div v-if="detallesViajeAConciliar" class="bg-gray-800 p-8 rounded-3xl text-white flex flex-col md:flex-row justify-between items-center gap-6 shadow-md">
          <div><span class="text-gray-400 text-sm block mb-1">Diferencia Físico vs Teórico</span><div class="text-4xl font-black tracking-tight" :class="diferenciaConciliacion >= 0 ? 'text-emerald-400' : 'text-red-400'">{{ diferenciaConciliacion > 0 ? '+' : '' }}{{ formatearPeso(diferenciaConciliacion) }} kg</div></div>
          <button @click="guardarConciliacion" :disabled="cargando" class="w-full md:w-auto bg-emerald-500 hover:bg-emerald-400 px-10 py-4 rounded-2xl font-bold text-lg transition shadow-lg">Aprobar Conciliación</button>
        </div>
      </div>
    </div>

    <div v-if="pestanaActual === 'pagos'" class="space-y-8 animate-fade-in">
      <div class="flex justify-between items-center"><h2 class="text-2xl font-light text-gray-700">Gestión de Pagos</h2><button @click="abrirModalPagos" class="bg-emerald-500 text-white px-6 py-3 rounded-2xl font-bold shadow-sm">+ Registrar Pago</button></div>
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div class="bg-white p-6 rounded-3xl border overflow-x-auto shadow-sm">
          <h3 class="text-lg font-bold text-orange-600 mb-4 border-b pb-2">Deudas por Proveedor</h3>
          <div class="bg-orange-50 border border-orange-100 p-5 rounded-2xl mb-4 flex justify-between items-center"><span class="text-orange-800 font-bold">Deuda Global Total:</span><span class="text-3xl font-black text-orange-600">${{ totalDeudaPendiente }}</span></div>
          <div class="space-y-3">
            <div v-for="prov in deudasAgrupadas" :key="prov.id" class="border rounded-2xl overflow-hidden shadow-sm">
              <button @click="proveedorExpandido = proveedorExpandido === prov.id ? null : prov.id" class="w-full flex justify-between items-center p-4 bg-gray-50 hover:bg-gray-100 transition"><span class="font-bold text-gray-800 text-lg">{{ prov.nombre }}</span><div class="flex items-center gap-4"><span class="text-xl font-black text-orange-600">${{ prov.totalDeuda.toFixed(2) }}</span><span class="text-gray-400 font-bold text-sm">{{ proveedorExpandido === prov.id ? '▲' : '▼' }}</span></div></button>
              <div v-if="proveedorExpandido === prov.id" class="p-4 bg-white border-t border-gray-100 animate-fade-in">
                <table class="w-full text-sm text-left">
                  <thead><tr class="text-gray-400 border-b"><th class="pb-2">Folio Nota</th><th class="pb-2">Fruta</th><th class="pb-2 text-right">Monto</th></tr></thead>
                  <tbody>
                    <tr v-for="nota in prov.notas" :key="nota.id" class="border-b last:border-0 hover:bg-gray-50 transition">
                      <td class="py-2 font-mono font-bold text-gray-700">{{ nota.folio }}</td><td class="py-2">{{ nota.fruta_nombre }}</td><td class="py-2 text-right font-bold text-gray-800">${{ nota.total_monetario }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
        <div class="bg-white p-6 rounded-3xl border overflow-x-auto shadow-sm">
          <h3 class="text-lg font-bold text-emerald-600 mb-4 border-b pb-2">Últimos Pagos Realizados</h3>
          <table class="min-w-full text-left text-sm text-gray-600">
            <thead><tr><th class="pb-2">Fecha</th><th class="pb-2">Proveedor</th><th class="pb-2 text-right">Monto</th><th class="pb-2 text-center">Acción</th></tr></thead>
            <tbody>
              <tr v-for="p in pagos.slice().reverse()" :key="p.id" class="border-t hover:bg-gray-50 transition">
                <td class="py-3 text-xs font-bold text-gray-500">{{ formatearFecha(p.fecha_pago) }}</td><td class="py-3 font-medium">{{ p.proveedor_nombre }} <span class="block text-[10px] text-gray-400 font-mono">{{ p.folio_pago }}</span></td><td class="py-3 text-right font-bold text-emerald-600">${{ p.monto_total }}</td><td class="py-3 text-center"><button @click="abrirDetallePago(p)" class="bg-blue-50 text-blue-600 px-3 py-1.5 rounded-lg text-xs font-bold hover:bg-blue-100 transition">Ver Detalle</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div v-if="pestanaActual === 'salidas'" class="space-y-6 animate-fade-in">
      <h2 class="text-2xl font-light text-gray-700">🚚 Planeación de Salidas (Ventas)</h2>
      
      <!-- Formulario para planear nueva salida -->
      <div class="bg-white p-8 rounded-3xl border shadow-sm mb-8">
        <h3 class="text-lg font-bold text-gray-700 mb-4">Generar Nuevo Viaje de Salida</h3>
        <div class="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div>
            <label class="block text-sm text-gray-500 mb-1 font-bold">Cliente</label>
            <select v-model="nuevoViajeSalida.cliente_id" class="w-full border border-gray-200 p-3 rounded-2xl text-sm outline-none font-bold text-gray-700">
              <option value="" disabled>Selecciona...</option>
              <option v-for="c in clientes" :value="c.id" :key="c.id">{{ c.nombre }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm text-gray-500 mb-1 font-bold">Placa/Transporte</label>
            <input v-model="nuevoViajeSalida.placa" placeholder="Ej. T-999" class="w-full border border-gray-200 p-3 rounded-2xl text-sm outline-none font-bold uppercase" />
          </div>
          <div>
            <label class="block text-sm text-gray-500 mb-1 font-bold">Precio Pactado ($/kg)</label>
            <input type="number" step="0.5" v-model="nuevoViajeSalida.precio_kg_venta" class="w-full border border-gray-200 p-3 rounded-2xl text-sm outline-none font-bold text-blue-600" />
          </div>
          <div>
            <label class="block text-sm text-gray-500 mb-1 font-bold">Fecha de Salida</label>
            <input type="date" v-model="nuevoViajeSalida.fecha_salida" class="w-full border border-gray-200 p-3 rounded-2xl text-sm outline-none font-bold text-gray-600" />
          </div>
          <div>
            <label class="block text-sm text-gray-500 mb-1 font-bold">Número de Guía</label>
            <input v-model="nuevoViajeSalida.numero_guia" placeholder="Guía #" class="w-full border border-gray-200 p-3 rounded-2xl text-sm outline-none font-bold text-gray-600" />
          </div>
        </div>
        <div class="flex justify-end mt-4">
          <button @click="crearViajeSalida" :disabled="cargando" class="bg-emerald-500 text-white px-8 py-3 rounded-2xl font-bold hover:bg-emerald-600 disabled:opacity-50 shadow-sm">
            Crear Viaje
          </button>
        </div>
      </div>

      <div class="bg-white p-8 rounded-3xl border overflow-x-auto shadow-sm">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-bold text-gray-700">Viajes Planeados / Activos</h3>
          <div class="flex items-center gap-3">
            <label class="text-sm font-bold text-gray-500 uppercase">Filtrar por Fecha:</label>
            <input type="date" v-model="fechaFiltroSalidas" class="border p-2 rounded-xl outline-none font-bold text-gray-700 shadow-sm" />
          </div>
        </div>
        <table class="min-w-full text-left text-sm text-gray-600">
          <thead class="bg-gray-50 border-b">
            <tr>
              <th class="p-3">ID</th>
              <th class="p-3">Cliente</th>
              <th class="p-3">Placa</th>
              <th class="p-3">Fecha de Salida</th>
              <th class="p-3">Guía</th>
              <th class="p-3 text-right">Precio Pactado</th>
              <th class="p-3 text-center">Estado</th>
              <th class="p-3 text-center">Acción</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="viaje in viajesSalidaFiltrados" :key="viaje.id" class="border-b hover:bg-gray-50">
              <td class="p-3 font-bold">#{{ viaje.id }}</td>
              <td class="p-3">
                <div class="font-bold text-gray-800">{{ viaje.cliente_nombre }}</div>
                <!-- Mostrar info de factura si está conciliado -->
                <div v-if="viaje.estado === 'CONCILIADO'" class="text-xs text-gray-500 mt-1 bg-emerald-50 p-2 rounded-lg border border-emerald-100/50">
                  📄 Fac: <strong>{{ viaje.numero_factura || 'S/N' }}</strong> | ⚖️ Peso Clie: <strong>{{ formatearPeso(viaje.peso_cliente) }} kg</strong><br/>
                  📉 Merma: <span class="text-red-500 font-bold">{{ formatearPeso(viaje.merma_salida) }} kg</span>
                </div>
              </td>
              <td class="p-3 font-mono">{{ viaje.placa }}</td>
              <td class="p-3">{{ formatearFecha(viaje.fecha_salida) }}</td>
              <td class="p-3 font-medium text-gray-500">{{ viaje.numero_guia || 'N/A' }}</td>
              <td class="p-3 text-right font-bold text-blue-600">${{ viaje.precio_kg_venta || 0 }} / kg</td>
              <td class="p-3 text-center">
                <span :class="viaje.estado === 'ACTIVO' ? 'bg-amber-100 text-amber-700' : (viaje.estado === 'CERRADO' ? 'bg-blue-100 text-blue-700' : 'bg-emerald-100 text-emerald-700')" class="px-2 py-1 rounded text-xs font-bold uppercase">
                  {{ viaje.estado === 'ACTIVO' ? 'En Báscula (Carga)' : (viaje.estado === 'CERRADO' ? 'Cerrado (Pendiente Factura)' : viaje.estado) }}
                </span>
              </td>
              <td class="p-3 text-center flex justify-center gap-2">
                <button @click="verDetalleSalida(viaje)" class="bg-blue-50 text-blue-600 hover:bg-blue-100 font-bold px-3 py-1 rounded text-xs transition">Ver</button>
                <button v-if="viaje.estado === 'ACTIVO'" @click="abrirEdicionSalida(viaje)" class="bg-amber-50 text-amber-600 hover:bg-amber-100 font-bold px-3 py-1 rounded text-xs transition">Editar</button>
                <button v-if="viaje.estado === 'CERRADO'" @click="abrirFacturacion(viaje)" class="bg-emerald-50 text-emerald-600 hover:bg-emerald-100 font-bold px-3 py-1 rounded text-xs transition">Facturar</button>
                <button v-if="viaje.estado === 'ACTIVO'" @click="eliminarSalida(viaje.id)" class="bg-red-50 text-red-600 hover:bg-red-100 font-bold px-3 py-1 rounded text-xs transition">Eliminar</button>
              </td>
            </tr>
            <tr v-if="viajesSalida.length === 0">
              <td colspan="8" class="p-6 text-center text-gray-400">No hay viajes de salida planeados</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- PESTAÑA MAQUILAS CERRADAS -->
    <div v-if="pestanaActual === 'maquilas'" class="space-y-6 animate-fade-in">
      <h2 class="text-2xl font-light text-gray-700">🏭 Servicios de Maquila Cerrados (Pendientes de Cobro)</h2>
      
      <div class="bg-white p-8 rounded-3xl border overflow-x-auto shadow-sm">
        <table class="min-w-full text-left text-sm text-gray-600">
          <thead class="bg-gray-50 border-b">
            <tr>
              <th class="p-3">ID Viaje</th>
              <th class="p-3">Cliente</th>
              <th class="p-3">Placa</th>
              <th class="p-3">Fecha Entrada</th>
              <th class="p-3 text-center">Estado</th>
              <th class="p-3 text-center">Acción</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="m in maquilasCerradas" :key="m.id" class="border-b hover:bg-gray-50">
              <td class="p-3 font-bold">#{{ m.id }}</td>
              <td class="p-3">{{ m.cliente_nombre }}</td>
              <td class="p-3 font-mono">{{ m.placa }}</td>
              <td class="p-3">{{ formatearFecha(m.fecha_entrada) }}</td>
              <td class="p-3 text-center">
                <span class="bg-amber-100 text-amber-700 px-2 py-1 rounded text-xs font-bold">
                  {{ m.estado }}
                </span>
              </td>
              <td class="p-3 text-center">
                <button @click="abrirCostoMaquila(m)" class="bg-emerald-50 text-emerald-600 hover:bg-emerald-100 font-bold px-4 py-2 rounded-xl text-xs transition">
                  Agregar Costo y Cobrar
                </button>
              </td>
            </tr>
            <tr v-if="maquilasCerradas.length === 0">
              <td colspan="6" class="p-6 text-center text-gray-400">No hay viajes de maquila cerrados pendientes de costo.</td>
            </tr>
          </tbody>
        </table>
      </div>
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
              <div><button @click="abrirEdicionCatalogo('acopiadores', a)" class="text-blue-500 mr-3 text-lg hover:scale-110 transition">✏️</button><button @click="eliminarCatalogo('acopiadores', a.id)" class="text-red-500 text-sm font-bold">X</button></div>
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
              <div><button @click="abrirEdicionCatalogo('proveedores', p)" class="text-blue-500 mr-3 text-lg hover:scale-110 transition">✏️</button><button @click="eliminarCatalogo('proveedores', p.id)" class="text-red-500 text-sm font-bold">X</button></div>
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
              <div><button @click="abrirEdicionCatalogo('clientes', c)" class="text-blue-500 mr-3 text-lg hover:scale-110 transition">✏️</button><button @click="eliminarCatalogo('clientes', c.id)" class="text-red-500 text-sm font-bold">X</button></div>
            </li>
          </ul>
        </div>

          <div class="bg-white p-6 rounded-3xl shadow-sm border">
        <h2 class="text-lg font-bold mb-4 text-green-700">Tipos de Fruta</h2>
        <form @submit.prevent="agregarCatalogo('tipos-fruta', nuevoTipoFruta, nuevoTipoFruta, {nombre:'', descripcion:''})" class="flex flex-col gap-2 mb-4">
          <input v-model="nuevoTipoFruta.nombre" placeholder="Nombre (ej. negra proceso)" class="border p-3 rounded-xl text-sm outline-none" required />
          <div class="flex gap-2">
            <input v-model="nuevoTipoFruta.descripcion" placeholder="Descripción (opcional)" class="border p-3 rounded-xl w-full text-sm outline-none" />
            <button type="submit" class="bg-green-500 text-white px-4 rounded-xl font-bold hover:bg-green-600">+</button>
          </div>
        </form>
        <ul class="text-sm text-gray-600 space-y-2 max-h-40 overflow-y-auto">
          <li v-for="f in tiposFruta" :key="f.id" class="flex justify-between border-b pb-2 items-center">
            <div>
              <span class="font-medium text-gray-800">{{f.nombre}}</span>
              <span v-if="f.descripcion" class="block text-xs text-gray-400">{{f.descripcion}}</span>
            </div>
            <div>
              <button @click="abrirEdicionCatalogo('tipos-fruta', f)" class="text-blue-500 mr-3 text-lg hover:scale-110 transition">✏️</button>
              <button @click="eliminarCatalogo('tipos-fruta', f.id)" class="text-red-500 text-sm font-bold">X</button>
            </div>
          </li>
        </ul>
      </div>
      </div>
    </div>

    <div v-if="mostrarModalAdminViaje" class="fixed inset-0 bg-gray-900 bg-opacity-50 flex items-center justify-center z-[60] p-4 backdrop-blur-sm">
      <div class="bg-white rounded-3xl w-full max-w-lg p-8 shadow-2xl">
        <h2 class="text-2xl font-bold mb-6 text-gray-800">Modificar Datos del Viaje #{{viajeAdminEditando.id}}</h2>
        <div class="space-y-5">
          <div>
            <label class="block text-xs font-bold text-gray-400 uppercase mb-1">Tipo de Operación</label>
            <select v-model="viajeAdminEditando.tipo_operacion" class="w-full border border-gray-300 p-4 rounded-2xl bg-gray-50 font-bold">
              <option value="ACOPIO">ACOPIO (Compra)</option>
              <option value="MAQUILA">MAQUILA (Servicio)</option>
            </select>
          </div>
          <div v-if="viajeAdminEditando.tipo_operacion === 'ACOPIO'" class="space-y-5 border-t pt-4">
            <div><label class="block text-xs font-bold text-gray-400 uppercase mb-1">Cambiar Acopiador</label><select v-model="viajeAdminEditando.acopiador_id" class="w-full border p-4 rounded-2xl font-medium"><option v-for="a in acopiadores" :value="a.id" :key="a.id">{{ a.nombre }}</option></select></div>
            <div><label class="block text-xs font-bold text-gray-400 uppercase mb-1">Placas</label><input v-model="viajeAdminEditando.placa" class="w-full border p-4 rounded-2xl uppercase font-bold" /></div>
          </div>
          <div v-if="viajeAdminEditando.tipo_operacion === 'MAQUILA'" class="space-y-5 border-t pt-4">
            <div><label class="block text-xs font-bold text-purple-500 uppercase mb-1">Cambiar Cliente</label><select v-model="viajeAdminEditando.cliente_id" class="w-full border p-4 rounded-2xl font-medium"><option v-for="c in clientes" :value="c.id" :key="c.id">{{ c.nombre }}</option></select></div>
          </div>
        </div>
        <div class="mt-8 flex gap-4">
          <button @click="mostrarModalAdminViaje = false" class="flex-1 bg-gray-100 py-4 rounded-2xl font-bold text-gray-600 hover:bg-gray-200">Cancelar</button>
          <button @click="guardarAdminViaje" class="flex-1 bg-blue-500 text-white py-4 rounded-2xl font-bold shadow-md hover:bg-blue-600">Guardar Cambios</button>
        </div>
      </div>
    </div>

    <div v-if="mostrarModalEdicionNota" class="fixed inset-0 bg-gray-900 bg-opacity-60 flex items-center justify-center p-4 z-50 backdrop-blur-sm">
      <div class="bg-white p-8 rounded-3xl w-full max-w-lg shadow-2xl">
        <h2 class="text-2xl font-bold mb-6 text-gray-800">Corregir Nota #{{editandoNota.id}}</h2>
        <div class="grid grid-cols-2 gap-4">
          <div class="col-span-2 md:col-span-1"><label class="text-xs font-bold text-gray-500 uppercase ml-1">Fecha</label><input type="date" v-model="editandoNota.fecha" class="border border-gray-300 p-3.5 rounded-2xl w-full font-bold"></div>
          <div class="col-span-2 md:col-span-1"><label class="text-xs font-bold text-gray-500 uppercase ml-1">Folio Físico</label><input v-model="editandoNota.folio" class="border border-gray-300 p-3.5 rounded-2xl w-full font-bold uppercase"></div>
          <div><label class="text-xs font-bold text-gray-500 uppercase ml-1">Peso Bruto</label><input type="number" v-model="editandoNota.peso_bruto" class="border border-gray-300 p-3.5 rounded-2xl w-full font-bold"></div>
          <div><label class="text-xs font-bold text-gray-500 uppercase ml-1">Cajas</label><input type="number" v-model="editandoNota.cantidad_cajas" class="border border-gray-300 p-3.5 rounded-2xl w-full font-bold"></div>
          <div><label class="text-xs font-bold text-gray-500 uppercase ml-1">Tara Tarima</label><input type="number" step="0.1" v-model="editandoNota.tara_tarima" class="border border-gray-300 p-3.5 rounded-2xl w-full"></div>
          <div><label class="text-xs font-bold text-gray-500 uppercase ml-1">Tara Caja</label><input type="number" step="0.01" v-model="editandoNota.tara_caja" class="border border-gray-300 p-3.5 rounded-2xl w-full"></div>
          <div class="col-span-2"><label class="text-xs font-bold text-gray-500 uppercase ml-1">Precio Unitario ($/kg)</label><input type="number" step="0.01" v-model="editandoNota.precio_kg" class="border border-gray-300 p-3.5 rounded-2xl w-full font-bold"></div>
        </div>
        <div class="mt-8 flex gap-4">
          <button @click="mostrarModalEdicionNota = false" class="flex-1 bg-gray-100 py-3.5 rounded-2xl font-bold text-gray-600">Cancelar</button>
          <button @click="guardarCambiosNota" class="flex-1 bg-blue-500 text-white py-3.5 rounded-2xl font-bold hover:bg-blue-400 shadow-md">Guardar Corrección</button>
        </div>
      </div>
    </div>

    <div v-if="mostrarModalPago" class="fixed inset-0 bg-gray-900 bg-opacity-60 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
      <div class="bg-white rounded-3xl w-full max-w-2xl p-8 max-h-[90vh] overflow-y-auto shadow-2xl">
        <h2 class="text-2xl font-bold mb-6 text-gray-800">Generar Liquidación / Pago</h2>
        <div class="grid grid-cols-2 gap-5 mb-6">
          <select v-model="nuevoPago.proveedor_id" @change="nuevoPago.nota_ids = []" class="w-full border border-gray-300 p-3.5 rounded-2xl font-medium">
            <option value="" disabled>Selecciona Proveedor...</option>
            <option v-for="p in proveedores" :value="p.id" :key="p.id">{{ p.nombre }}</option>
          </select>
          <input type="date" v-model="nuevoPago.fecha_pago" class="w-full border border-gray-300 p-3.5 rounded-2xl font-medium" />
        </div>
        <div class="mb-6"><input v-model="nuevoPago.folio_pago" placeholder="Referencia bancaria o Folio interno de pago" class="w-full border border-gray-300 p-3.5 rounded-2xl uppercase font-bold" /></div>
        <div v-if="nuevoPago.proveedor_id" class="border-t pt-4">
          <p class="text-sm font-bold text-gray-500 mb-2">Selecciona las notas a liquidar:</p>
          <div class="max-h-40 overflow-y-auto space-y-2 mb-6 bg-gray-50 p-3 rounded-2xl border">
            <label v-for="n in notasDelProveedorSeleccionado" :key="n.id" class="flex items-center p-3 bg-white rounded-xl cursor-pointer border hover:border-emerald-300 transition shadow-sm">
              <input type="checkbox" :value="n.id" v-model="nuevoPago.nota_ids" class="w-5 h-5 text-emerald-500 mr-4 rounded">
              <div class="flex-1"><p class="text-sm font-bold text-gray-800">Folio Nota: {{n.folio}}</p></div><div class="font-black text-orange-600">${{ n.total_monetario }}</div>
            </label>
          </div>
          <div class="bg-emerald-50 p-6 rounded-3xl flex justify-between items-center border border-emerald-100"><span class="text-emerald-800 font-bold text-lg">Total a Liquidar:</span><span class="text-4xl font-black text-emerald-600">${{ nuevoPago.monto_total }}</span></div>
        </div>
        <div class="mt-8 flex gap-4"><button @click="mostrarModalPago = false" class="flex-1 bg-gray-100 py-4 rounded-2xl font-bold text-gray-600">Cancelar</button><button @click="registrarPago" :disabled="cargando || nuevoPago.monto_total <= 0" class="flex-1 bg-emerald-500 text-white py-4 rounded-2xl font-bold text-lg hover:bg-emerald-400 shadow-md disabled:opacity-50">Procesar Pago</button></div>
      </div>
    </div>

    <div v-if="mostrarModalDetallePago" class="fixed inset-0 bg-gray-900 bg-opacity-60 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
      <div class="bg-white rounded-3xl w-full max-w-2xl p-8 max-h-[90vh] overflow-y-auto shadow-2xl">
        <div class="flex justify-between items-start mb-6 border-b pb-4">
          <div><h2 class="text-2xl font-black text-gray-800">Detalle de Pago</h2><p class="text-gray-500 font-medium">{{ pagoSeleccionado.proveedor_nombre }}</p></div>
          <button @click="modoEdicionPago = !modoEdicionPago" :class="modoEdicionPago ? 'bg-blue-500 text-white' : 'bg-gray-100 text-blue-600'" class="px-4 py-2 rounded-xl font-bold transition">{{ modoEdicionPago ? 'Cancelar Edición' : '✏️ Editar Datos' }}</button>
        </div>
        <div class="grid grid-cols-2 gap-6 mb-6">
          <div v-if="!modoEdicionPago" class="col-span-2 flex gap-6 p-4 bg-gray-50 rounded-2xl border">
            <div class="flex-1"><span class="block text-xs text-gray-400 font-bold uppercase">Folio / Referencia</span><span class="font-mono font-bold text-lg">{{ pagoSeleccionado.folio_pago }}</span></div>
            <div class="flex-1"><span class="block text-xs text-gray-400 font-bold uppercase">Fecha</span><span class="font-bold text-lg">{{ formatearFecha(pagoSeleccionado.fecha_pago) }}</span></div>
          </div>
          <template v-else>
            <div><label class="text-xs font-bold text-gray-500 uppercase ml-1">Folio / Referencia</label><input v-model="pagoEditando.folio_pago" class="border p-3.5 rounded-2xl w-full uppercase"></div>
            <div><label class="text-xs font-bold text-gray-500 uppercase ml-1">Fecha</label><input type="date" v-model="pagoEditando.fecha_pago" class="border p-3.5 rounded-2xl w-full"></div>
          </template>
        </div>
        <h3 class="font-bold text-gray-700 mb-3">Notas amparadas:</h3>
        <div class="max-h-48 overflow-y-auto mb-6 border rounded-2xl bg-white"><table class="min-w-full text-left text-sm"><thead class="bg-gray-50 border-b"><tr><th class="p-3">Folio Nota</th><th class="p-3">Fruta</th><th class="p-3 text-right">Peso</th><th class="p-3 text-right">Monto</th></tr></thead><tbody><tr v-for="n in  notasDelPagoSeleccionado" :key="n.id" class="border-b"><td class="p-3 font-bold font-mono">{{ n.folio }}</td><td class="p-3">{{ n.fruta_nombre }}</td><td class="p-3 text-right">{{ formatearPeso(n.peso_neto) }} kg</td><td class="p-3 text-right font-bold text-emerald-600">${{ n.total_monetario }}</td></tr></tbody></table></div>
        <div class="flex justify-between items-center mb-8"><button @click="anularPago" class="text-red-500 hover:text-red-700 font-bold underline text-sm">❌ Anular Pago Completamente</button><div class="text-right"><span class="block text-xs font-bold text-gray-400 uppercase">Total Pagado</span><span class="text-3xl font-black text-emerald-600">${{ pagoSeleccionado.monto_total }}</span></div></div>
        <div class="flex gap-4 border-t pt-6"><button @click="mostrarModalDetallePago = false" class="flex-1 bg-gray-100 py-3.5 rounded-2xl font-bold text-gray-600">Cerrar</button><button v-if="modoEdicionPago" @click="guardarEdicionPago" class="flex-1 bg-blue-500 text-white py-3.5 rounded-2xl font-bold">Guardar Cambios</button></div>
      </div>
    </div>

    <div v-if="mostrarModalEdicionCatalogo" class="fixed inset-0 bg-gray-900 bg-opacity-60 flex items-center justify-center p-4 z-50 backdrop-blur-sm">
      <div class="bg-white p-8 rounded-3xl w-full max-w-sm shadow-2xl">
        <h2 class="text-2xl font-bold mb-6 text-gray-800 capitalize">Editar {{tipoCatalogoEdicion}}</h2>
        <div class="space-y-5">
          <div><label class="text-xs font-bold text-gray-500 uppercase ml-1">Nombre</label><input v-model="itemEditando.nombre" class="border p-3.5 rounded-2xl w-full font-medium"></div>
          <div v-if="tipoCatalogoEdicion === 'acopiadores'"><label class="text-xs font-bold text-gray-500 uppercase ml-1">Teléfono</label><input v-model="itemEditando.telefono" class="border p-3.5 rounded-2xl w-full font-medium"></div>
          <div v-if="tipoCatalogoEdicion === 'proveedores' || tipoCatalogoEdicion === 'clientes'"><label class="text-xs font-bold text-gray-500 uppercase ml-1">Contacto</label><input v-model="itemEditando.contacto" class="border p-3.5 rounded-2xl w-full font-medium"></div>
          <div v-if="tipoCatalogoEdicion === 'tipos-fruta'"><label class="text-xs font-bold text-gray-500 uppercase ml-1">Descripción</label><input v-model="itemEditando.descripcion" class="border p-3.5 rounded-2xl w-full font-medium"></div>
        </div>
        <div class="mt-8 flex gap-4"><button @click="mostrarModalEdicionCatalogo = false" class="flex-1 bg-gray-100 py-3.5 rounded-2xl font-bold text-gray-600">Cancelar</button><button @click="guardarEdicionCatalogo" class="flex-1 bg-blue-500 text-white py-3.5 rounded-2xl font-bold">Actualizar</button></div>
      </div>
    </div>

    <div v-if="mostrarModalEdicionPesada" class="fixed inset-0 bg-gray-900 bg-opacity-60 flex items-center justify-center z-[60] p-4 backdrop-blur-sm">
      <div class="bg-white rounded-3xl w-full max-w-md p-8 shadow-2xl">
        <h2 class="text-2xl font-bold mb-6 text-gray-800">Corregir Pesada #{{pesadaEditando.numero_tarima}}</h2>
        <div class="space-y-4">
          <div><label class="text-xs font-bold text-gray-400">TIPO DE FRUTA</label><select v-model="pesadaEditando.tipo_fruta_id" class="w-full border p-3 rounded-xl text-gray-700 font-medium"><option v-for="f in tiposFruta" :value="f.id" :key="f.id">{{f.nombre}}</option></select></div>
          <div class="grid grid-cols-2 gap-4">
            <div><label class="text-xs font-bold text-gray-400">PESO BRUTO</label><input type="number" step="0.5" v-model="pesadaEditando.peso_bruto" class="w-full border p-3 rounded-xl font-bold"></div>
            <div><label class="text-xs font-bold text-gray-400">CAJAS</label><input type="number" v-model="pesadaEditando.cantidad_cajas" class="w-full border p-3 rounded-xl font-bold"></div>
            <div><label class="text-xs font-bold text-orange-400">TARA CAJA</label><input type="number" step="0.01" v-model="pesadaEditando.tara_caja" class="w-full border p-3 rounded-xl font-bold text-orange-600 bg-orange-50"></div>
            <div><label class="text-xs font-bold text-orange-400">TARA TARIMA</label><input type="number" step="0.1" v-model="pesadaEditando.tara_tarima" class="w-full border p-3 rounded-xl font-bold text-orange-600 bg-orange-50"></div>
          </div>
        </div>
        <div class="flex gap-4 mt-8"><button @click="mostrarModalEdicionPesada = false" class="flex-1 bg-gray-100 py-3 rounded-xl font-bold text-gray-600">Cancelar</button><button @click="guardarEdicionPesada" class="flex-1 bg-blue-500 text-white font-bold py-3 rounded-xl shadow-md">Guardar Cambios</button></div>
      </div>
    </div>

    <!-- Modal de detalle de salida -->
    <div v-if="mostrarModalDetalleSalida" class="fixed inset-0 bg-gray-900 bg-opacity-60 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-3xl w-full max-w-2xl p-8 max-h-[90vh] overflow-y-auto">
        <h2 class="text-2xl font-bold mb-4 text-gray-800">Detalle de Salida #{{ salidaSeleccionada.id }}</h2>
        <div class="space-y-2 mb-6">
          <p><span class="font-bold text-gray-500">Cliente:</span> {{ salidaSeleccionada.cliente_nombre }}</p>
          <p><span class="font-bold text-gray-500">Placa:</span> {{ salidaSeleccionada.placa }}</p>
          <p><span class="font-bold text-gray-500">Fecha:</span> {{ formatearFecha(salidaSeleccionada.fecha_salida) }}</p>
          <p><span class="font-bold text-gray-500">Peso Total:</span> {{ formatearPeso(salidaSeleccionada.peso_total_fisico) }} kg</p>
        </div>
        <h3 class="font-bold text-gray-700 mb-3">Tarimas en esta salida:</h3>
        <div class="max-h-60 overflow-y-auto mb-6 border rounded-xl">
          <table class="min-w-full text-left text-sm">
            <thead class="bg-gray-50 border-b">
              <tr>
                <th class="p-3">Tarima</th>
                <th class="p-3">Fruta</th>
                <th class="p-3 text-right">Peso Bruto</th>
                <th class="p-3 text-right">Cajas</th>
                <th class="p-3 text-right">Tara</th>
                <th class="p-3 text-right">Peso Neto</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="tarima in tarimasDetalleSalida" :key="tarima.id" class="border-b">
                <td class="p-3 font-bold">{{ tarima.numero_tarima_display }}</td>
                <td class="p-3">{{ tarima.fruta_nombre }}</td>
                <td class="p-3 text-right">{{ formatearPeso(tarima.peso_bruto) }} kg</td>
                <td class="p-3 text-right">{{ tarima.cantidad_cajas }}</td>
                <td class="p-3 text-right">{{ formatearPeso(tarima.tara_total) }} kg</td>
                <td class="p-3 text-right font-bold text-orange-600">{{ formatearPeso(tarima.peso_neto) }} kg</td>
              </tr>
            </tbody>
          </table>
        </div>
        <button @click="mostrarModalDetalleSalida = false" class="w-full bg-gray-100 py-3 rounded-xl font-bold text-gray-600">
          Cerrar
        </button>
      </div>
    </div>

    <!-- Modal Edición Viaje Salida -->
    <div v-if="mostrarModalEdicionSalida" class="fixed inset-0 bg-gray-900 bg-opacity-60 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-3xl w-full max-w-md shadow-2xl overflow-hidden flex flex-col">
        <div class="bg-amber-50 border-b border-amber-100 p-6 flex justify-between items-center">
          <h2 class="text-2xl font-bold text-amber-800">Editar Viaje #{{ salidaEditando.id }}</h2>
          <button @click="mostrarModalEdicionSalida = false" class="text-amber-400 hover:text-amber-600 text-3xl font-light">&times;</button>
        </div>
        <div class="p-6 overflow-y-auto max-h-[70vh]">
          <form @submit.prevent="guardarEdicionSalida" class="space-y-4">
            <div>
              <label class="block text-sm font-bold text-gray-700 mb-1">Cliente</label>
              <select v-model="salidaEditando.cliente_id" required class="w-full border border-gray-200 p-3 rounded-xl outline-none font-bold">
                <option v-for="c in clientes" :value="c.id" :key="c.id">{{ c.nombre }}</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-bold text-gray-700 mb-1">Placa/Transporte</label>
              <input v-model="salidaEditando.placa" required class="w-full border border-gray-200 p-3 rounded-xl outline-none font-bold uppercase" />
            </div>
            <div>
              <label class="block text-sm font-bold text-gray-700 mb-1">Precio Pactado ($/kg)</label>
              <input type="number" step="0.5" v-model="salidaEditando.precio_kg_venta" required class="w-full border border-gray-200 p-3 rounded-xl outline-none font-bold text-blue-600" />
            </div>
            <div>
              <label class="block text-sm font-bold text-gray-700 mb-1">Fecha de Salida</label>
              <input type="date" v-model="salidaEditando.fecha_salida" required class="w-full border border-gray-200 p-3 rounded-xl outline-none font-bold" />
            </div>
            <div>
              <label class="block text-sm font-bold text-gray-700 mb-1">Número de Guía</label>
              <input v-model="salidaEditando.numero_guia" class="w-full border border-gray-200 p-3 rounded-xl outline-none font-bold" />
            </div>
            <div class="flex gap-4 mt-6">
              <button type="button" @click="mostrarModalEdicionSalida = false" class="flex-1 bg-gray-100 text-gray-600 p-3 rounded-xl font-bold hover:bg-gray-200 transition">Cancelar</button>
              <button type="submit" :disabled="cargando" class="flex-1 bg-amber-500 text-white p-3 rounded-xl font-bold hover:bg-amber-600 transition disabled:opacity-50">Guardar</button>
            </div>
          </form>
        </div>
      </div>
    </div>
    <!-- Modal Registrar Costo de Maquila -->
    <div v-if="mostrarModalCostoMaquila" class="fixed inset-0 bg-gray-900 bg-opacity-60 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
      <div class="bg-white rounded-3xl w-full max-w-sm p-6 shadow-2xl">
        <h2 class="text-xl font-black text-gray-800 mb-4">Ingresar Costo de Maquila</h2>
        <div class="bg-purple-50 text-purple-800 p-4 rounded-xl text-sm mb-4">
          Viaje: <strong>#{{ maquilaSeleccionada?.id }}</strong><br/>
          Cliente: <strong>{{ maquilaSeleccionada?.cliente_nombre }}</strong>
        </div>
        <div>
          <label class="block text-xs font-bold text-gray-400 uppercase mb-2">Costo del Servicio ($)</label>
          <input type="number" v-model="costoMaquila" class="w-full border p-3 rounded-xl font-bold text-lg outline-none focus:ring-2 focus:ring-purple-500" />
        </div>
        <div class="flex gap-3 mt-6">
          <button @click="mostrarModalCostoMaquila = false" class="flex-1 bg-gray-100 text-gray-600 py-3 rounded-xl font-bold hover:bg-gray-200 transition">Cancelar</button>
          <button @click="guardarCostoMaquila" :disabled="cargando" class="flex-1 bg-purple-600 text-white py-3 rounded-xl font-bold hover:bg-purple-700 shadow-md transition">Guardar y Cobrar</button>
        </div>
      </div>
    </div>

    <!-- Modal Registrar Factura (Salida) -->
    <div v-if="mostrarModalFactura" class="fixed inset-0 bg-gray-900 bg-opacity-60 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
      <div class="bg-white rounded-3xl w-full max-w-md p-8 shadow-2xl">
        <h2 class="text-2xl font-black text-gray-800 mb-4">Ingresar Datos de Facturación</h2>
        <div class="bg-emerald-50 text-emerald-800 p-4 rounded-xl text-sm mb-6">
          Viaje Salida: <strong>#{{ viajeSalidaFacturando?.id }}</strong> | Cliente: <strong>{{ viajeSalidaFacturando?.cliente_nombre }}</strong><br/>
          Nuestro Peso Neto: <strong>{{ formatearPeso(viajeSalidaFacturando?.peso_total_fisico) }} kg</strong>
        </div>
        <div class="space-y-4">
          <div>
            <label class="block text-xs font-bold text-gray-500 uppercase mb-2">Peso Recibido por Cliente (kg)</label>
            <input type="number" step="0.5" v-model="datosFactura.peso_cliente" class="w-full border p-3 rounded-xl font-bold outline-none focus:ring-2 focus:ring-emerald-500" />
            <p class="text-xs text-gray-400 mt-1">Diferencia (Merma): <span class="font-bold text-red-500">{{ formatearPeso(viajeSalidaFacturando?.peso_total_fisico - datosFactura.peso_cliente) }} kg</span></p>
          </div>
          <div>
            <label class="block text-xs font-bold text-gray-500 uppercase mb-2">Número de Factura</label>
            <input type="text" v-model="datosFactura.numero_factura" placeholder="Ej. FAC-1029" class="w-full border p-3 rounded-xl font-bold outline-none uppercase focus:ring-2 focus:ring-emerald-500" />
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-xs font-bold text-gray-500 uppercase mb-2">Fecha Facturación</label>
              <input type="date" v-model="datosFactura.fecha_facturacion" class="w-full border p-3 rounded-xl text-sm font-medium outline-none" />
            </div>
            <div>
              <label class="block text-xs font-bold text-gray-500 uppercase mb-2">Fecha Vencimiento</label>
              <input type="date" v-model="datosFactura.fecha_vencimiento" class="w-full border p-3 rounded-xl text-sm font-medium outline-none" />
            </div>
          </div>
        </div>
        <div class="flex gap-4 mt-8">
          <button @click="mostrarModalFactura = false" class="flex-1 bg-gray-100 text-gray-600 py-3.5 rounded-2xl font-bold hover:bg-gray-200 transition">Cancelar</button>
          <button @click="guardarFactura" :disabled="cargando" class="flex-1 bg-emerald-600 text-white py-3.5 rounded-2xl font-bold hover:bg-emerald-500 shadow-md transition">Guardar Factura</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style>
.animate-fade-in { animation: fadeIn 0.3s ease-out; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
</style>