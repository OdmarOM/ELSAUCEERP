append_code = """

class ViajeSalidaCreate(BaseModel):
    cliente_id: Optional[int] = None
    placa: str = ""
    precio_kg_venta: float = 0.0

class TarimasSalidaRequest(BaseModel):
    inventario_frio_ids: List[int]
    peso_salida_total: float
    observaciones: str = ""

class CobroClienteCreate(BaseModel):
    monto_cobrado: float
    metodo_pago: str
    referencia: str = ""

class PesadaSalidaRequest(BaseModel):
    viaje_id: int
    inventario_frio_id: Optional[int] = None
    peso_neto: float
    observaciones: str = ""
    
    # Agregado para compatibilidad con ZonaA.vue
    tipo_fruta_id: Optional[int] = None
    cantidad_cajas: Optional[int] = None
    tara_total: Optional[float] = None
    promedio_peso_caja: Optional[float] = None


@app.post("/api/viajes/salida")
def crear_viaje_salida(viaje: ViajeSalidaCreate):
    with get_db() as conn:
        cursor = conn.cursor()
        fecha_actual = datetime.now().isoformat()
        try:
            cursor.execute(
                "INSERT INTO viaje (cliente_id, placa, fecha_entrada, estado, tipo_operacion, tipo, precio_kg_venta) VALUES (?, ?, ?, 'ACTIVO', 'SALIDA', 'SALIDA', ?)",
                (viaje.cliente_id, viaje.placa, fecha_actual, viaje.precio_kg_venta)
            )
            conn.commit()
            nuevo_id = cursor.lastrowid
            return {"id": nuevo_id, "mensaje": "Viaje de salida creado"}
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.post("/api/registros-bascula-salida")
def registrar_pesada_salida(req: PesadaSalidaRequest):
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            if req.inventario_frio_id:
                cursor.execute("UPDATE inventario_frio SET activo = 0, fecha_salida = CURRENT_TIMESTAMP, viaje_salida_id = ? WHERE id = ?", (req.viaje_id, req.inventario_frio_id))
                cursor.execute("DELETE FROM cuartofrio WHERE inventario_frio_id = ?", (req.inventario_frio_id,))
            
            cursor.execute("INSERT INTO viaje_salida_tarima (viaje_id, inventario_frio_id, peso_salida, observaciones) VALUES (?, ?, ?, ?)", (req.viaje_id, req.inventario_frio_id, req.peso_neto, req.observaciones))
            conn.commit()
            return {"mensaje": "Pesada de salida registrada"}
        except Exception as e:
            conn.rollback()
            logger.error(f"Error registrando pesada salida: {e}")
            raise HTTPException(status_code=500, detail="Error interno")

@app.get("/api/finanzas/cobrar")
def listar_cuentas_cobrar():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT cc.*, c.nombre as cliente_nombre, v.placa as viaje_placa FROM cuenta_cobrar cc JOIN cliente c ON cc.cliente_id = c.id LEFT JOIN viaje v ON cc.viaje_salida_id = v.id ORDER BY cc.fecha_emision DESC")
        return [dict(row) for row in cursor.fetchall()]

@app.post("/api/finanzas/cobrar/{id}/pagar")
def registrar_cobro_cliente(id: int, cobro: CobroClienteCreate):
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT saldo_pendiente FROM cuenta_cobrar WHERE id = ?", (id,))
            cuenta = cursor.fetchone()
            if not cuenta: raise HTTPException(status_code=404, detail="Cuenta no encontrada")
            cursor.execute("INSERT INTO cobro_cliente (cuenta_cobrar_id, monto_cobrado, metodo_pago, referencia) VALUES (?, ?, ?, ?)", (id, cobro.monto_cobrado, cobro.metodo_pago, cobro.referencia))
            cursor.execute("UPDATE cuenta_cobrar SET saldo_pendiente = saldo_pendiente - ?, estado = CASE WHEN (saldo_pendiente - ?) <= 0 THEN 'PAGADO' ELSE 'PENDIENTE' END WHERE id = ?", (cobro.monto_cobrado, cobro.monto_cobrado, id))
            conn.commit()
            return {"mensaje": "Cobro registrado"}
        except Exception as e:
            conn.rollback()
            raise HTTPException(status_code=500, detail="Error interno")

@app.get("/api/finanzas/pagar")
def listar_cuentas_pagar():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT p.id as proveedor_id, p.nombre as proveedor_nombre, SUM(CASE WHEN n.estado_pago = 'PENDIENTE' THEN n.total_monetario ELSE 0 END) as total_deuda, COUNT(CASE WHEN n.estado_pago = 'PENDIENTE' THEN n.id END) as notas_pendientes FROM proveedor p LEFT JOIN notaproveedor n ON p.id = n.proveedor_id GROUP BY p.id HAVING total_deuda > 0")
        return [dict(row) for row in cursor.fetchall()]
"""
with open('app/main.py', 'a', encoding='utf-8') as f:
    f.write(append_code)
