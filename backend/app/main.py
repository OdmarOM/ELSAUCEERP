from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
import sqlite3
from pathlib import Path
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

DB_PATH = Path(__file__).parent.parent / "data" / "sauce_erp.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Iniciando FastAPI para El Sauce ERP...")
    yield

app = FastAPI(title="API El Sauce ERP", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConciliacionData(BaseModel):
    nota_ids: list[int]
    peso_fisico: float
    peso_teorico: float
    difference: float

class ViajeCreate(BaseModel):
    tipo_operacion: str
    acopiador_id: Optional[int] = None
    cliente_id: Optional[int] = None
    placa: Optional[str] = ""

class PagoData(BaseModel):
    proveedor_id: int
    folio_pago: str
    monto_total: float
    metodo_pago: str
    nota_ids: list[int]

@app.get("/")
def read_root():
    return {"estado": "En línea", "mensaje": "Servidor de El Sauce ERP activo y funcionando"}

# ==========================================
# VIAJES
# ==========================================
@app.post("/api/viajes", status_code=201)
def crear_viaje(viaje: ViajeCreate):
    conn = get_db()
    cursor = conn.cursor()
    fecha_actual = datetime.now().isoformat()
    try:
        cursor.execute(
            "INSERT INTO viaje (acopiador_id, cliente_id, placa, fecha_entrada, estado, tipo_operacion) VALUES (?, ?, ?, ?, 'ACTIVO', ?)",
            (viaje.acopiador_id, viaje.cliente_id, viaje.placa, fecha_actual, viaje.tipo_operacion)
        )
        conn.commit()
        nuevo_id = cursor.lastrowid
        cursor.execute("SELECT * FROM viaje WHERE id = ?", (nuevo_id,))
        viaje_creado = dict(cursor.fetchone())
        return viaje_creado
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/api/viajes")
def listar_viajes():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM viaje")
    viajes = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return viajes

@app.put("/api/viajes/{viaje_id}/cerrar")
def cerrar_viaje(viaje_id: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE viaje SET estado = 'CERRADO' WHERE id = ?", (viaje_id,))
        conn.commit()
        return {"mensaje": "Viaje cerrado exitosamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.delete("/api/viajes/{viaje_id}")
def eliminar_viaje(viaje_id: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT estado FROM viaje WHERE id = ?", (viaje_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Viaje no encontrado")
        if row['estado'] == 'CONCILIADO':
            raise HTTPException(status_code=400, detail="No se puede eliminar un viaje que ya se encuentra consolidado contablemente.")
        
        cursor.execute("DELETE FROM cuartofrio WHERE tarima_id IN (SELECT id FROM registrobascula WHERE viaje_id = ?)", (viaje_id,))
        cursor.execute("DELETE FROM registrobascula WHERE viaje_id = ?", (viaje_id,))
        cursor.execute("UPDATE notaproveedor SET viaje_id = NULL WHERE viaje_id = ?", (viaje_id,))
        cursor.execute("DELETE FROM viaje WHERE id = ?", (viaje_id,))
        conn.commit()
        return {"status": "ok", "mensaje": "Viaje eliminado correctamente"}
    except HTTPException as he:
        raise he
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# ==========================================
# ACOPIADORES
# ==========================================
@app.post("/api/acopiadores", status_code=201)
def crear_acopiador(acopiador: dict):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO acopiador (nombre, telefono) VALUES (?, ?)",
                (acopiador['nombre'], acopiador.get('telefono')))
    conn.commit()
    nuevo_id = cursor.lastrowid
    conn.close()
    return {"id": nuevo_id, **acopiador}

@app.get("/api/acopiadores")
def listar_acopiadores():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM acopiador")
    data = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return data

@app.delete("/api/acopiadores/{acopiador_id}")
def eliminar_acopiador(acopiador_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM acopiador WHERE id = ?", (acopiador_id,))
    conn.commit()
    conn.close()
    return {"mensaje": "Acopiador eliminado"}

# ==========================================
# PROVEEDORES
# ==========================================
@app.post("/api/proveedores", status_code=201)
def crear_proveedor(proveedor: dict):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO proveedor (nombre, contacto) VALUES (?, ?)",
                (proveedor['nombre'], proveedor.get('contacto')))
    conn.commit()
    nuevo_id = cursor.lastrowid
    conn.close()
    return {"id": nuevo_id, **proveedor}

@app.get("/api/proveedores")
def listar_proveedores():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM proveedor")
    data = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return data

@app.delete("/api/proveedores/{proveedor_id}")
def eliminar_proveedor(proveedor_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM proveedor WHERE id = ?", (proveedor_id,))
    conn.commit()
    conn.close()
    return {"mensaje": "Proveedor eliminado"}

# ==========================================
# CLIENTES (MAQUILA)
# ==========================================
@app.get("/api/clientes")
def listar_clientes():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cliente")
    data = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return data

@app.post("/api/clientes", status_code=201)
def crear_cliente(cliente: dict):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO cliente (nombre, contacto) VALUES (?, ?)", (cliente['nombre'], cliente.get('contacto', '')))
        conn.commit()
        nuevo_id = cursor.lastrowid
        return {"id": nuevo_id, **cliente}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.delete("/api/clientes/{id}")
def eliminar_cliente(id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cliente WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return {"mensaje": "Cliente eliminado"}

# ==========================================
# TIPOS DE FRUTA
# ==========================================
@app.post("/api/tipos-fruta", status_code=201)
def crear_tipo_fruta(fruta: dict):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tipofruta (nombre, descripcion) VALUES (?, ?)",
                (fruta['nombre'], fruta.get('descripcion')))
    conn.commit()
    nuevo_id = cursor.lastrowid
    conn.close()
    return {"id": nuevo_id, **fruta}

@app.get("/api/tipos-fruta")
def listar_tipos_fruta():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tipofruta")
    data = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return data

@app.delete("/api/tipos-fruta/{fruta_id}")
def eliminar_tipo_fruta(fruta_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tipofruta WHERE id = ?", (fruta_id,))
    conn.commit()
    conn.close()
    return {"mensaje": "Tipo de fruta eliminado"}

# ==========================================
# NOTAS DE PROVEEDOR Y CONCILIACIÓN
# ==========================================
@app.post("/api/notas", status_code=201)
def crear_nota(nota: dict):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cajas = int(nota.get('cantidad_cajas', 0))
        t_tarima = float(nota.get('tara_tarima', 0.0))
        t_caja = float(nota.get('tara_caja', 0.0))
        p_bruto = float(nota.get('peso_bruto', 0.0))
        precio = float(nota.get('precio_kg', 0.0))
        
        tara_total = t_tarima + (t_caja * cajas)
        peso_neto = max(0.0, p_bruto - tara_total) if p_bruto > 0 else float(nota.get('peso_neto', 0.0))
        total_monetario = peso_neto * precio

        cursor.execute("""
            INSERT INTO notaproveedor (
                viaje_id, proveedor_id, tipo_fruta_id, fecha, cantidad_cajas, 
                tara_tarima, tara_caja, peso_bruto, peso_neto, precio_kg, 
                total_monetario, estado_pago, folio
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDIENTE', ?)
        """, (
            nota.get('viaje_id'), nota['proveedor_id'], nota['tipo_fruta_id'],
            nota.get('fecha', datetime.now().isoformat()), cajas, t_tarima, t_caja, p_bruto, 
            peso_neto, precio, total_monetario, nota.get('folio', 'S/F')
        ))
        conn.commit()
        nuevo_id = cursor.lastrowid
        return {"id": nuevo_id, **nota}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/api/viajes/{viaje_id}/conciliar")
def conciliar_viaje(viaje_id: int, data: ConciliacionData):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE viaje 
            SET estado = 'CONCILIADO', peso_total_fisico = ?, peso_total_teorico = ?, diferencia_peso = ?
            WHERE id = ?
        """, (data.peso_fisico, data.peso_teorico, data.difference, viaje_id))
        
        for nota_id in data.nota_ids:
            cursor.execute("UPDATE notaproveedor SET viaje_id = ? WHERE id = ?", (viaje_id, nota_id))
            
        conn.commit()
        return {"mensaje": "Viaje conciliado exitosamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/api/notas")
def listar_notas():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT n.*, p.nombre as proveedor_nombre, t.nombre as fruta_nombre 
        FROM notaproveedor n
        JOIN proveedor p ON n.proveedor_id = p.id
        JOIN tipofruta t ON n.tipo_fruta_id = t.id
    """)
    data = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return data

@app.delete("/api/notas/{nota_id}")
def eliminar_nota(nota_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM notaproveedor WHERE id = ?", (nota_id,))
    conn.commit()
    conn.close()
    return {"mensaje": "Nota eliminada"}

# ==========================================
# BÁSCULA Y REGISTRO DE TARIMAS
# ==========================================
@app.post("/api/registros-bascula", status_code=201)
def registrar_tarima(tarima: dict):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cantidad_cajas = tarima.get('cantidad_cajas', 0)
        tara_tarima = tarima.get('tara_tarima', 0.0)
        tara_caja = tarima.get('tara_caja', 0.0)
        peso_bruto = tarima.get('peso_bruto', 0.0)
        
        tara_total = (tara_tarima) + (tara_caja * cantidad_cajas)
        peso_neto = peso_bruto - tara_total
        promedio_peso = peso_neto / cantidad_cajas if cantidad_cajas > 0 else 0.0

        cursor.execute("""
            INSERT INTO registrobascula (
                viaje_id, maquila_id, tipo_fruta_id, numero_tarima, fecha_hora,
                cantidad_cajas, tara_tarima, tara_caja, tara_total, peso_bruto,
                peso_neto, promedio_peso_caja
            ) VALUES (?, ?, ?, ?, datetime('now'), ?, ?, ?, ?, ?, ?, ?)
        """, (
            tarima['viaje_id'], tarima.get('maquila_id'), tarima['tipo_fruta_id'],
            tarima['numero_tarima'], cantidad_cajas, tara_tarima, tara_caja,
            tara_total, peso_bruto, peso_neto, promedio_peso
        ))
        conn.commit()
        nuevo_id = cursor.lastrowid
        return {"id": nuevo_id, "mensaje": "Pesada registrada correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/api/registros-bascula")
def listar_tarimas():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT r.*, t.nombre as fruta_nombre 
        FROM registrobascula r
        LEFT JOIN tipofruta t ON r.tipo_fruta_id = t.id
    """)
    data = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return data

# ==========================================
# PAGOS (LIQUIDACIÓN A PROVEEDORES)
# ==========================================
@app.post("/api/pagos", status_code=201)
def registrar_pago(pago: PagoData):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO pago (proveedor_id, folio_pago, fecha_pago, monto_total, metodo_pago)
            VALUES (?, ?, ?, ?, ?)
        """, (pago.proveedor_id, pago.folio_pago, datetime.now().isoformat(), pago.monto_total, pago.metodo_pago))
        pago_id = cursor.lastrowid

        for nota_id in pago.nota_ids:
            cursor.execute("""
                UPDATE notaproveedor
                SET estado_pago = 'PAGADO', pago_id = ?
                WHERE id = ?
            """, (pago_id, nota_id))
        
        conn.commit()
        return {"mensaje": "Pago registrado exitosamente", "id": pago_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/api/pagos")
def listar_pagos():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, pr.nombre as proveedor_nombre 
        FROM pago p
        JOIN proveedor pr ON p.proveedor_id = pr.id
    """)
    data = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return data

# ==========================================
# CUARTO FRÍO (UBICACIONES)
# ==========================================
@app.get("/api/cuarto-frio")
def listar_cuarto_frio():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.*, r.numero_tarima, r.viaje_id, t.nombre as fruta_nombre
        FROM cuartofrio c
        JOIN registrobascula r ON c.tarima_id = r.id
        LEFT JOIN tipofruta t ON r.tipo_fruta_id = t.id
    """)
    data = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return data

@app.post("/api/cuarto-frio")
def asignar_ubicacion(datos: dict):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM cuartofrio WHERE fila_x = ? AND columna_y = ?", (datos['fila_x'], datos['columna_y']))
        if cursor.fetchone():
            raise Exception("Esa ubicación en el cuarto frío ya está ocupada.")
            
        cursor.execute("""
            INSERT INTO cuartofrio (fila_x, columna_y, tarima_id)
            VALUES (?, ?, ?)
        """, (datos['fila_x'], datos['columna_y'], datos['tarima_id']))
        cursor.execute("UPDATE registrobascula SET estado_ubicacion = 'EN_CUARTO_FRIO' WHERE id = ?", (datos['tarima_id'],))
        conn.commit()
        return {"mensaje": "Ubicación asignada correctamente"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()

@app.put("/api/cuarto-frio/{tarima_id}/mover")
def mover_tarima(tarima_id: int, datos: dict):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM cuartofrio WHERE fila_x = ? AND columna_y = ?", (datos['fila_x'], datos['columna_y']))
        if cursor.fetchone():
            raise Exception("La ubicación destino ya está ocupada.")
            
        cursor.execute("UPDATE cuartofrio SET fila_x = ?, columna_y = ? WHERE tarima_id = ?", (datos['fila_x'], datos['columna_y'], tarima_id))
        conn.commit()
        return {"mensaje": "Movimiento exitoso"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()

@app.delete("/api/cuarto-frio/{tarima_id}")
def sacar_tarima_frio(tarima_id: int, destino: str = "EN_BODEGA"):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM cuartofrio WHERE tarima_id = ?", (tarima_id,))
        cursor.execute("UPDATE registrobascula SET estado_ubicacion = ? WHERE id = ?", (destino, tarima_id))
        conn.commit()
        return {"mensaje": f"Tarima enviada a {destino}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()

# ==========================================
# CONEXIÓN CON BÁSCULA ESP32
# ==========================================
peso_actual_bascula = 0.0

@app.post("/api/bascula/leer")
def recibir_peso_esp32(datos: dict):
    global peso_actual_bascula
    peso_actual_bascula = float(datos.get("peso", 0.0))
    return {"mensaje": "Peso recibido", "peso": peso_actual_bascula}

@app.get("/api/bascula/peso-actual")
def obtener_peso_actual():
    return {"peso": peso_actual_bascula}

# ==========================================
# ENDPOINTS DE EDICIÓN (PUT)
# ==========================================
@app.put("/api/acopiadores/{id}")
def editar_acopiador(id: int, data: dict):
    conn = get_db(); cursor = conn.cursor()
    cursor.execute("UPDATE acopiador SET nombre = ?, telefono = ? WHERE id = ?", (data['nombre'], data.get('telefono', ''), id))
    conn.commit(); conn.close()
    return {"status": "ok"}

@app.put("/api/proveedores/{id}")
def editar_proveedor(id: int, data: dict):
    conn = get_db(); cursor = conn.cursor()
    cursor.execute("UPDATE proveedor SET nombre = ?, contacto = ? WHERE id = ?", (data['nombre'], data.get('contacto', ''), id))
    conn.commit(); conn.close()
    return {"status": "ok"}

@app.put("/api/clientes/{id}")
def editar_cliente(id: int, data: dict):
    conn = get_db(); cursor = conn.cursor()
    cursor.execute("UPDATE cliente SET nombre = ?, contacto = ? WHERE id = ?", (data['nombre'], data.get('contacto', ''), id))
    conn.commit(); conn.close()
    return {"status": "ok"}

@app.put("/api/tipos-fruta/{id}")
def editar_fruta(id: int, data: dict):
    conn = get_db(); cursor = conn.cursor()
    cursor.execute("UPDATE tipofruta SET nombre = ?, descripcion = ? WHERE id = ?", (data['nombre'], data.get('descripcion', ''), id))
    conn.commit(); conn.close()
    return {"status": "ok"}

@app.put("/api/notas/{id}")
def editar_nota(id: int, nota: dict):
    conn = get_db(); cursor = conn.cursor()
    try:
        cajas = int(nota.get('cantidad_cajas', 0))
        t_tarima = float(nota.get('tara_tarima', 0.0))
        t_caja = float(nota.get('tara_caja', 0.0))
        p_bruto = float(nota.get('peso_bruto', 0.0))
        precio = float(nota.get('precio_kg', 0.0))
        
        tara_total = t_tarima + (t_caja * cajas)
        peso_neto = max(0.0, p_bruto - tara_total) if p_bruto > 0 else float(nota.get('peso_neto', 0.0))
        total_monetario = peso_neto * precio

        cursor.execute("""
            UPDATE notaproveedor 
            SET folio = ?, proveedor_id = ?, tipo_fruta_id = ?, 
                cantidad_cajas = ?, tara_tarima = ?, tara_caja = ?, 
                peso_bruto = ?, peso_neto = ?, precio_kg = ?, total_monetario = ?, fecha = ?
            WHERE id = ?
        """, (nota['folio'], nota['proveedor_id'], nota['tipo_fruta_id'], 
            cajas, t_tarima, t_caja, p_bruto, peso_neto, precio, total_monetario, nota.get('fecha', datetime.now().isoformat()), id))
        conn.commit()
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.put("/api/pagos/{id}")
def editar_pago(id: int, data: dict):
    conn = get_db(); cursor = conn.cursor()
    cursor.execute("UPDATE pago SET folio_pago = ?, fecha_pago = ?, metodo_pago = ? WHERE id = ?", 
                (data['folio_pago'], data['fecha_pago'], data['metodo_pago'], id))
    conn.commit(); conn.close()
    return {"status": "ok"}

@app.post("/api/viajes/{id}/deshacer-conciliacion")
def deshacer_conciliacion(id: int):
    conn = get_db(); cursor = conn.cursor()
    try:
        cursor.execute("UPDATE notaproveedor SET viaje_id = NULL WHERE viaje_id = ?", (id,))
        cursor.execute("""
            UPDATE viaje 
            SET estado = 'CERRADO', peso_total_teorico = 0, diferencia_peso = 0 
            WHERE id = ?
        """, (id,))
        conn.commit()
        return {"mensaje": "Conciliación deshecha correctamente"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.put("/api/registros-bascula/{id}")
def editar_tarima(id: int, data: dict):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT v.estado FROM registrobascula r JOIN viaje v ON r.viaje_id = v.id WHERE r.id = ?", (id,))
        v_row = cursor.fetchone()
        if v_row and v_row['estado'] == 'CONCILIADO':
            raise HTTPException(status_code=400, detail="Bloqueado: Esta pesada pertenece a un viaje ya consolidado contablemente.")

        cursor.execute("SELECT * FROM registrobascula WHERE id = ?", (id,))
        actual = dict(cursor.fetchone())
        
        tipo_fruta_id = data.get('tipo_fruta_id', actual['tipo_fruta_id'])
        cantidad_cajas = data.get('cantidad_cajas', actual['cantidad_cajas'])
        peso_bruto = data.get('peso_bruto', actual['peso_bruto'])
        tara_caja = data.get('tara_caja', actual['tara_caja'])
        tara_tarima = data.get('tara_tarima', actual['tara_tarima'])
        
        if 'peso_bruto' in data and 'tara_caja' in data:
            tara_total = tara_tarima + (tara_caja * cantidad_cajas)
            peso_neto = peso_bruto - tara_total
        else:
            peso_neto = data.get('peso_neto', actual['peso_neto'])
            tara_total = actual['tara_total']
            
        promedio = peso_neto / cantidad_cajas if cantidad_cajas > 0 else 0

        cursor.execute("""
            UPDATE registrobascula 
            SET peso_neto = ?, tipo_fruta_id = ?, cantidad_cajas = ?, 
                peso_bruto = ?, tara_caja = ?, tara_tarima = ?, 
                tara_total = ?, promedio_peso_caja = ?
            WHERE id = ?
        """, (peso_neto, tipo_fruta_id, cantidad_cajas, peso_bruto, tara_caja, tara_tarima, tara_total, promedio, id))
        conn.commit()
        return {"status": "ok", "mensaje": "Tarima actualizada"}
    except HTTPException as he:
        raise he
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.put("/api/viajes/{id}")
def editar_viaje(id: int, data: dict):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT estado FROM viaje WHERE id = ?", (id,))
        row = cursor.fetchone()
        if row and row['estado'] == 'CONCILIADO':
            raise HTTPException(status_code=400, detail="Bloqueado: No se puede modificar un viaje que ya se encuentra consolidado.")

        acopiador_id = data.get('acopiador_id') if data.get('acopiador_id') else None
        cliente_id = data.get('cliente_id') if data.get('cliente_id') else None
        
        cursor.execute("""
            UPDATE viaje 
            SET tipo_operacion = ?, acopiador_id = ?, cliente_id = ?, placa = ?
            WHERE id = ?
        """, (data['tipo_operacion'], acopiador_id, cliente_id, data.get('placa', ''), id))
        conn.commit()
        return {"status": "ok", "mensaje": "Viaje actualizado"}
    except HTTPException as he:
        raise he
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.delete("/api/registros-bascula/{id}")
def eliminar_tarima(id: int):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT v.estado FROM registrobascula r JOIN viaje v ON r.viaje_id = v.id WHERE r.id = ?", (id,))
        v_row = cursor.fetchone()
        if v_row and v_row['estado'] == 'CONCILIADO':
            raise HTTPException(status_code=400, detail="Bloqueado: No se puede eliminar pesadas de viajes consolidados.")

        cursor.execute("DELETE FROM cuartofrio WHERE tarima_id = ?", (id,))
        cursor.execute("DELETE FROM registrobascula WHERE id = ?", (id,))
        conn.commit()
        return {"status": "ok", "mensaje": "Pesada eliminada correctamente"}
    except HTTPException as he:
        raise he
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.delete("/api/pagos/{id}")
def anular_pago(id: int):
    conn = get_db(); cursor = conn.cursor()
    try:
        cursor.execute("UPDATE notaproveedor SET estado_pago = 'PENDIENTE', pago_id = NULL WHERE pago_id = ?", (id,))
        cursor.execute("DELETE FROM pago WHERE id = ?", (id,))
        conn.commit()
        return {"status": "ok", "mensaje": "Pago anulado y notas liberadas"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# ==========================================
# SERVIDOR DE FRONTEND (VUE DIST)
# ==========================================
dist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dist")

if os.path.isdir(dist_path):
    app.mount("/assets", StaticFiles(directory=os.path.join(dist_path, "assets")), name="assets")
    
    @app.exception_handler(404)
    async def not_found_exception_handler(request, exc):
        return FileResponse(os.path.join(dist_path, "index.html"))
    
    @app.get("/")
    def serve_vue_app():
        return FileResponse(os.path.join(dist_path, "index.html"))