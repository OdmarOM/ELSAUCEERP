
# ==========================================
# MÓDULO DE SALIDAS Y CUENTAS POR COBRAR / PAGAR
# ==========================================

class ViajeSalidaCreate(BaseModel):
    cliente_id: Optional[int] = None
    placa: str = ""

class TarimasSalidaRequest(BaseModel):
    inventario_frio_ids: List[int]
    peso_salida_total: float
    observaciones: str = ""

class CobroClienteCreate(BaseModel):
    monto_cobrado: float
    metodo_pago: str
    referencia: str = ""

@app.post("/api/viajes/salida")
def crear_viaje_salida(viaje: ViajeSalidaCreate):
    """Crea un nuevo viaje de tipo SALIDA"""
    with get_db() as conn:
        cursor = conn.cursor()
        fecha_actual = datetime.now().isoformat()
        try:
            # Crear viaje de salida
            cursor.execute(
                "INSERT INTO viaje (cliente_id, placa, fecha_entrada, estado, tipo_operacion, tipo) VALUES (?, ?, ?, 'ACTIVO', 'SALIDA', 'SALIDA')",
                (viaje.cliente_id, viaje.placa, fecha_actual)
            )
            conn.commit()
            nuevo_id = cursor.lastrowid
            return {"id": nuevo_id, "mensaje": "Viaje de salida creado exitosamente"}
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creando viaje de salida: {e}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.post("/api/viajes-salida/{viaje_id}/procesar")
def procesar_salida_inventario(viaje_id: int, req: TarimasSalidaRequest):
    """Selecciona tarimas del cuarto frío y las asigna a un viaje de salida, generando la cuenta por cobrar"""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            # Validar que el viaje exista
            cursor.execute("SELECT * FROM viaje WHERE id = ?", (viaje_id,))
            viaje = cursor.fetchone()
            if not viaje:
                raise HTTPException(status_code=404, detail="Viaje no encontrado")
            
            cliente_id = viaje['cliente_id']

            for inv_id in req.inventario_frio_ids:
                # Marcar inventario como inactivo
                cursor.execute("""
                    UPDATE inventario_frio 
                    SET activo = 0, fecha_salida = CURRENT_TIMESTAMP, viaje_salida_id = ?
                    WHERE id = ?
                """, (viaje_id, inv_id))
                
                # Registrar en viaje_salida_tarima
                cursor.execute("""
                    INSERT INTO viaje_salida_tarima (viaje_id, inventario_frio_id, peso_salida, observaciones)
                    VALUES (?, ?, 0, ?)
                """, (viaje_id, inv_id, req.observaciones))
                
                # Quitar del cuarto frío físico
                cursor.execute("DELETE FROM cuartofrio WHERE inventario_frio_id = ?", (inv_id,))

            # Si hay un cliente_id, generar cuenta por cobrar
            if cliente_id:
                # Mapeo simple: el monto total podría ser ingresado por el usuario o calculado.
                # Aquí lo dejaremos pendiente para que el admin lo llene después o asigne un monto total
                # En un caso real, esto se calcularía en base al peso y precio por kg.
                cursor.execute("""
                    INSERT INTO cuenta_cobrar (cliente_id, viaje_salida_id, estado)
                    VALUES (?, ?, 'PENDIENTE')
                """, (cliente_id, viaje_id))

            conn.commit()
            return {"mensaje": "Salida procesada correctamente"}
        except HTTPException as he:
            raise he
        except Exception as e:
            conn.rollback()
            logger.error(f"Error procesando salida: {e}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.get("/api/finanzas/cobrar")
def listar_cuentas_cobrar():
    """Obtiene todas las cuentas por cobrar a clientes"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT cc.*, c.nombre as cliente_nombre, v.placa as viaje_placa 
            FROM cuenta_cobrar cc
            JOIN cliente c ON cc.cliente_id = c.id
            LEFT JOIN viaje v ON cc.viaje_salida_id = v.id
            ORDER BY cc.fecha_emision DESC
        """)
        data = [dict(row) for row in cursor.fetchall()]
        return data

@app.post("/api/finanzas/cobrar/{id}/pagar")
def registrar_cobro_cliente(id: int, cobro: CobroClienteCreate):
    """Registra un pago realizado por un cliente para una cuenta por cobrar"""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT saldo_pendiente FROM cuenta_cobrar WHERE id = ?", (id,))
            cuenta = cursor.fetchone()
            if not cuenta:
                raise HTTPException(status_code=404, detail="Cuenta por cobrar no encontrada")

            # Insertar cobro
            cursor.execute("""
                INSERT INTO cobro_cliente (cuenta_cobrar_id, monto_cobrado, metodo_pago, referencia)
                VALUES (?, ?, ?, ?)
            """, (id, cobro.monto_cobrado, cobro.metodo_pago, cobro.referencia))

            # Actualizar saldo y estado
            cursor.execute("""
                UPDATE cuenta_cobrar 
                SET saldo_pendiente = saldo_pendiente - ?,
                    estado = CASE WHEN (saldo_pendiente - ?) <= 0 THEN 'PAGADO' ELSE 'PENDIENTE' END
                WHERE id = ?
            """, (cobro.monto_cobrado, cobro.monto_cobrado, id))

            conn.commit()
            return {"mensaje": "Cobro registrado exitosamente"}
        except Exception as e:
            conn.rollback()
            logger.error(f"Error registrando cobro: {e}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.get("/api/finanzas/pagar")
def listar_cuentas_pagar():
    """Obtiene un resumen de cuentas por pagar a proveedores (acopiadores)"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.id as proveedor_id, p.nombre as proveedor_nombre,
                   SUM(CASE WHEN n.estado_pago = 'PENDIENTE' THEN n.total_monetario ELSE 0 END) as total_deuda,
                   COUNT(CASE WHEN n.estado_pago = 'PENDIENTE' THEN n.id END) as notas_pendientes
            FROM proveedor p
            LEFT JOIN notaproveedor n ON p.id = n.proveedor_id
            GROUP BY p.id
            HAVING total_deuda > 0
        """)
        data = [dict(row) for row in cursor.fetchall()]
        return data
