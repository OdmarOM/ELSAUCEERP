# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import sqlite3
from pathlib import Path
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import logging
from logging.handlers import RotatingFileHandler
from .config import settings
from .database import get_db
from .auth import (
    verify_password, get_password_hash, create_access_token, 
    decode_access_token, security, get_current_user
)

# Configurar logging
def setup_logging():
    log_dir = Path(settings.LOG_FILE).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            RotatingFileHandler(
                settings.LOG_FILE,
                maxBytes=10*1024*1024,  # 10MB
                backupCount=5
            ),
            logging.StreamHandler()
        ]
    )

setup_logging()
logger = logging.getLogger(__name__)

DB_PATH = settings.DB_PATH

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Iniciando FastAPI para El Sauce ERP...")
    yield
    logger.info("Apagando FastAPI...")

app = FastAPI(title="API El Sauce ERP", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# MIDDLEWARE DE MANEJO DE ERRORES
# ==========================================
from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Manejador global de excepciones"""
    logger.error(f"Error no manejado: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor"}
    )

# ================= MODELOS =================
from pydantic import field_validator, constr

class ConciliacionData(BaseModel):
    nota_ids: list[int]
    peso_fisico: float
    peso_teorico: float
    difference: float
    
    @field_validator('peso_fisico', 'peso_teorico', 'difference')
    @classmethod
    def validate_peso(cls, v):
        if v < 0:
            raise ValueError('El peso no puede ser negativo')
        return v

class ViajeCreate(BaseModel):
    tipo_operacion: constr(strip_whitespace=True, to_upper=True)
    acopiador_id: Optional[int] = None
    cliente_id: Optional[int] = None
    placa: Optional[str] = ""
    
    @field_validator('tipo_operacion')
    @classmethod
    def validate_tipo_operacion(cls, v):
        if v not in ['ACOPIO', 'MAQUILA']:
            raise ValueError('tipo_operacion debe ser ACOPIO o MAQUILA')
        return v

class PagoData(BaseModel):
    proveedor_id: int
    folio_pago: constr(strip_whitespace=True, min_length=1)
    monto_total: float
    metodo_pago: constr(strip_whitespace=True)
    nota_ids: list[int]
    
    @field_validator('monto_total')
    @classmethod
    def validate_monto(cls, v):
        if v <= 0:
            raise ValueError('El monto total debe ser mayor a 0')
        return v

class TarimaFrioCreate(BaseModel):
    viaje_id: Optional[int] = None
    tipo_fruta_id: int
    numero_tarima_display: constr(strip_whitespace=True, min_length=1)
    cantidad_cajas: int
    peso_neto: float
    notas_referencia: Optional[str] = None
    origen: Optional[str] = "MANUAL"
    
    @field_validator('cantidad_cajas', 'peso_neto')
    @classmethod
    def validate_positive(cls, v):
        if v < 0:
            raise ValueError('El valor no puede ser negativo')
        return v

class UnirTarimasRequest(BaseModel):
    id_inventario_1: int
    id_inventario_2: int
    nueva_fila_x: int
    nueva_columna_y: int
    nuevo_numero_tarima: constr(strip_whitespace=True, min_length=1)
    
    @field_validator('nueva_fila_x', 'nueva_columna_y')
    @classmethod
    def validate_ubicacion(cls, v):
        if v < 1 or v > 10:
            raise ValueError('Las coordenadas deben estar entre 1 y 10')
        return v

class MoverTarimaRequest(BaseModel):
    fila_x: int
    columna_y: int
    
    @field_validator('fila_x', 'columna_y')
    @classmethod
    def validate_ubicacion(cls, v):
        if v < 1 or v > 10:
            raise ValueError('Las coordenadas deben estar entre 1 y 10')
        return v

class ReasignarViajeRequest(BaseModel):
    viaje_id: int

# Modelos de autenticación
class LoginRequest(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "user"  # "user" o "admin"

@app.get("/")
def read_root():
    return {"estado": "En línea", "mensaje": "Servidor de El Sauce ERP activo y funcionando"}

# ==========================================
# AUTENTICACIÓN
# ==========================================
@app.post("/api/auth/login")
def login(credentials: LoginRequest):
    """Endpoint de login - genera token JWT"""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            # Buscar usuario en base de datos
            cursor.execute("SELECT * FROM usuarios WHERE username = ?", (credentials.username,))
            user = cursor.fetchone()
            
            if not user:
                logger.warning(f"Intento de login fallido: usuario {credentials.username} no encontrado")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Usuario o contraseña incorrectos"
                )
            
            user_dict = dict(user)
            
            # Verificar contraseña
            if not verify_password(credentials.password, user_dict['password_hash']):
                logger.warning(f"Intento de login fallido: contraseña incorrecta para {credentials.username}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Usuario o contraseña incorrectos"
                )
            
            # Crear token de acceso
            access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            access_token = create_access_token(
                data={"sub": user_dict['username'], "role": user_dict['role']},
                expires_delta=access_token_expires
            )
            
            logger.info(f"Login exitoso: {credentials.username}")
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "username": user_dict['username'],
                    "role": user_dict['role']
                }
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error en login: {e}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.post("/api/auth/register")
def register(user_data: UserCreate):
    """Registrar nuevo usuario (requiere autenticación de admin)"""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            # Verificar si el usuario ya existe
            cursor.execute("SELECT id FROM usuarios WHERE username = ?", (user_data.username,))
            if cursor.fetchone():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="El usuario ya existe"
                )
            
            # Verificar que el rol sea válido
            if user_data.role not in ["user", "admin"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Rol inválido. Debe ser 'user' o 'admin'"
                )
            
            # Crear tabla de usuarios si no existe
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'user',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Hashear contraseña y crear usuario
            password_hash = get_password_hash(user_data.password)
            cursor.execute(
                "INSERT INTO usuarios (username, password_hash, role) VALUES (?, ?, ?)",
                (user_data.username, password_hash, user_data.role)
            )
            conn.commit()
            
            logger.info(f"Usuario registrado: {user_data.username} con rol {user_data.role}")
            return {"mensaje": "Usuario registrado exitosamente"}
        except HTTPException:
            raise
        except Exception as e:
            conn.rollback()
            logger.error(f"Error registrando usuario: {e}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.get("/api/auth/me")
def get_me(current_user: dict = Depends(get_current_user)):
    """Obtener información del usuario actual"""
    return current_user

# ==========================================
# VIAJES
# ==========================================
@app.post("/api/viajes", status_code=201)
def crear_viaje(viaje: ViajeCreate):
    with get_db() as conn:
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
            logger.error(f"Error creando viaje: {e}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.get("/api/viajes")
def listar_viajes():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM viaje ORDER BY id DESC")
        viajes = [dict(row) for row in cursor.fetchall()]
        return viajes

@app.put("/api/viajes/{viaje_id}/cerrar")
def cerrar_viaje(viaje_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE viaje SET estado = 'CERRADO' WHERE id = ?", (viaje_id,))
            conn.commit()
            return {"mensaje": "Viaje cerrado exitosamente"}
        except Exception as e:
            logger.error(f"Error cerrando viaje {viaje_id}: {e}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.delete("/api/viajes/{viaje_id}")
def eliminar_viaje(viaje_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT estado FROM viaje WHERE id = ?", (viaje_id,))
            row = cursor.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Viaje no encontrado")
            if row['estado'] == 'CONCILIADO':
                raise HTTPException(status_code=400, detail="No se puede eliminar un viaje que ya se encuentra consolidado contablemente.")
            
            # Eliminar relaciones en cuarto frío (vía inventario_frio)
            cursor.execute("""
                DELETE FROM cuartofrio 
                WHERE inventario_frio_id IN (
                    SELECT id FROM inventario_frio WHERE viaje_id = ?
                )
            """, (viaje_id,))
            cursor.execute("DELETE FROM inventario_frio WHERE viaje_id = ?", (viaje_id,))
            cursor.execute("DELETE FROM registrobascula WHERE viaje_id = ?", (viaje_id,))
            cursor.execute("UPDATE notaproveedor SET viaje_id = NULL WHERE viaje_id = ?", (viaje_id,))
            cursor.execute("DELETE FROM viaje WHERE id = ?", (viaje_id,))
            conn.commit()
            return {"status": "ok", "mensaje": "Viaje eliminado correctamente"}
        except HTTPException as he:
            raise he
        except Exception as e:
            conn.rollback()
            logger.error(f"Error eliminando viaje {viaje_id}: {e}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.put("/api/viajes/{id}")
def editar_viaje(id: int, data: dict):
    with get_db() as conn:
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
            logger.error(f"Error editando viaje {id}: {e}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.post("/api/viajes/{id}/deshacer-conciliacion")
def deshacer_conciliacion(id: int):
    with get_db() as conn:
        cursor = conn.cursor()
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
            logger.error(f"Error deshaciendo conciliación viaje {id}: {e}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")

# ==========================================
# ACOPIADORES
# ==========================================
@app.get("/api/acopiadores")
def listar_acopiadores():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM acopiador")
        data = [dict(row) for row in cursor.fetchall()]
        return data

@app.post("/api/acopiadores", status_code=201)
def crear_acopiador(acopiador: dict):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO acopiador (nombre, telefono) VALUES (?, ?)",
                    (acopiador['nombre'], acopiador.get('telefono')))
        conn.commit()
        nuevo_id = cursor.lastrowid
        return {"id": nuevo_id, **acopiador}

@app.put("/api/acopiadores/{id}")
def editar_acopiador(id: int, data: dict):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE acopiador SET nombre = ?, telefono = ? WHERE id = ?", 
                       (data['nombre'], data.get('telefono', ''), id))
        conn.commit()
        return {"status": "ok"}

@app.delete("/api/acopiadores/{acopiador_id}")
def eliminar_acopiador(acopiador_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM acopiador WHERE id = ?", (acopiador_id,))
        conn.commit()
        return {"mensaje": "Acopiador eliminado"}

# ==========================================
# PROVEEDORES
# ==========================================
@app.get("/api/proveedores")
def listar_proveedores():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM proveedor")
        data = [dict(row) for row in cursor.fetchall()]
        return data

@app.post("/api/proveedores", status_code=201)
def crear_proveedor(proveedor: dict):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO proveedor (nombre, contacto) VALUES (?, ?)",
                    (proveedor['nombre'], proveedor.get('contacto')))
        conn.commit()
        nuevo_id = cursor.lastrowid
        return {"id": nuevo_id, **proveedor}

@app.put("/api/proveedores/{id}")
def editar_proveedor(id: int, data: dict):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE proveedor SET nombre = ?, contacto = ? WHERE id = ?", 
                       (data['nombre'], data.get('contacto', ''), id))
        conn.commit()
        return {"status": "ok"}

@app.delete("/api/proveedores/{proveedor_id}")
def eliminar_proveedor(proveedor_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM proveedor WHERE id = ?", (proveedor_id,))
        conn.commit()
        return {"mensaje": "Proveedor eliminado"}

# ==========================================
# CLIENTES (MAQUILA)
# ==========================================
@app.get("/api/clientes")
def listar_clientes():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cliente")
        data = [dict(row) for row in cursor.fetchall()]
        return data

@app.post("/api/clientes", status_code=201)
def crear_cliente(cliente: dict):
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO cliente (nombre, contacto) VALUES (?, ?)", 
                           (cliente['nombre'], cliente.get('contacto', '')))
            conn.commit()
            nuevo_id = cursor.lastrowid
            return {"id": nuevo_id, **cliente}
        except Exception as e:
            logger.error(f"Error creando cliente: {e}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.put("/api/clientes/{id}")
def editar_cliente(id: int, data: dict):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE cliente SET nombre = ?, contacto = ? WHERE id = ?", 
                       (data['nombre'], data.get('contacto', ''), id))
        conn.commit()
        return {"status": "ok"}

@app.delete("/api/clientes/{id}")
def eliminar_cliente(id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cliente WHERE id = ?", (id,))
        conn.commit()
        return {"mensaje": "Cliente eliminado"}

# ==========================================
# TIPOS DE FRUTA
# ==========================================
@app.get("/api/tipos-fruta")
def listar_tipos_fruta():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tipofruta")
        data = [dict(row) for row in cursor.fetchall()]
        return data

@app.post("/api/tipos-fruta", status_code=201)
def crear_tipo_fruta(fruta: dict):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO tipofruta (nombre, descripcion) VALUES (?, ?)",
                    (fruta['nombre'], fruta.get('descripcion')))
        conn.commit()
        nuevo_id = cursor.lastrowid
        return {"id": nuevo_id, **fruta}

@app.put("/api/tipos-fruta/{id}")
def editar_fruta(id: int, data: dict):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE tipofruta SET nombre = ?, descripcion = ? WHERE id = ?", 
                       (data['nombre'], data.get('descripcion', ''), id))
        conn.commit()
        return {"status": "ok"}

@app.delete("/api/tipos-fruta/{fruta_id}")
def eliminar_tipo_fruta(fruta_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM tipofruta WHERE id = ?", (fruta_id,))
        conn.commit()
        return {"mensaje": "Tipo de fruta eliminado"}

# ==========================================
# NOTAS DE PROVEEDOR Y CONCILIACIÓN
# ==========================================
@app.get("/api/notas")
def listar_notas():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT n.*, p.nombre as proveedor_nombre, t.nombre as fruta_nombre 
            FROM notaproveedor n
            JOIN proveedor p ON n.proveedor_id = p.id
            JOIN tipofruta t ON n.tipo_fruta_id = t.id
            ORDER BY n.id DESC
        """)
        data = [dict(row) for row in cursor.fetchall()]
        return data

@app.post("/api/notas", status_code=201)
def crear_nota(nota: dict):
    with get_db() as conn:
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
            logger.error(f"Error creando nota: {e}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.put("/api/notas/{id}")
def editar_nota(id: int, nota: dict):
    with get_db() as conn:
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
                UPDATE notaproveedor 
                SET folio = ?, proveedor_id = ?, tipo_fruta_id = ?, 
                    cantidad_cajas = ?, tara_tarima = ?, tara_caja = ?, 
                    peso_bruto = ?, peso_neto = ?, precio_kg = ?, total_monetario = ?, fecha = ?
                WHERE id = ?
            """, (nota['folio'], nota['proveedor_id'], nota['tipo_fruta_id'], 
                cajas, t_tarima, t_caja, p_bruto, peso_neto, precio, total_monetario, 
                nota.get('fecha', datetime.now().isoformat()), id))
            conn.commit()
            return {"status": "ok"}
        except Exception as e:
            logger.error(f"Error editando nota {id}: {e}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.delete("/api/notas/{nota_id}")
def eliminar_nota(nota_id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM notaproveedor WHERE id = ?", (nota_id,))
        conn.commit()
        return {"mensaje": "Nota eliminada"}

@app.post("/api/viajes/{viaje_id}/conciliar")
def conciliar_viaje(viaje_id: int, data: ConciliacionData):
    with get_db() as conn:
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
            logger.error(f"Error conciliando viaje {viaje_id}: {e}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")

# ==========================================
# REGISTRO DE BÁSCULA (PESADAS) - Histórico
# ==========================================
@app.get("/api/registros-bascula")
def listar_tarimas():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT r.*, t.nombre as fruta_nombre 
            FROM registrobascula r
            LEFT JOIN tipofruta t ON r.tipo_fruta_id = t.id
            ORDER BY r.id DESC
        """)
        data = [dict(row) for row in cursor.fetchall()]
        return data

@app.post("/api/registros-bascula")
def registrar_pesada(tarima: dict):
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            # Insertar en Báscula (Histórico)
            cursor.execute("""
                INSERT INTO registrobascula (
                    viaje_id, tipo_fruta_id, numero_tarima, cantidad_cajas, 
                    peso_neto, peso_bruto, tara_total, tara_caja, tara_tarima,
                    fecha_hora, estado_ubicacion
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), 'EN_BODEGA')
            """, (
                tarima['viaje_id'], tarima['tipo_fruta_id'], tarima['numero_tarima'], 
                tarima['cantidad_cajas'], tarima['peso_neto'], tarima.get('peso_bruto', 0),
                tarima.get('tara_total', 0), tarima.get('tara_caja', 0), tarima.get('tara_tarima', 0)
            ))
            
            registro_id = cursor.lastrowid

            # Crear entrada en Inventario Frío
            numero_display = f"T-{tarima['numero_tarima']}"
            cursor.execute("""
                INSERT INTO inventario_frio (
                    viaje_id, tipo_fruta_id, numero_tarima_display, 
                    cantidad_cajas, peso_neto, fecha_ingreso, notas_referencia, 
                    origen, origen_id, activo
                )
                VALUES (?, ?, ?, ?, ?, datetime('now'), ?, 'PESADA', ?, 1)
            """, (
                tarima['viaje_id'], tarima['tipo_fruta_id'], numero_display,
                tarima['cantidad_cajas'], tarima['peso_neto'],
                f"Registro de pesada #{registro_id}", registro_id
            ))
            
            inventario_id = cursor.lastrowid
            
            conn.commit()
            return {"status": "ok", "registro_id": registro_id, "inventario_id": inventario_id}
        except Exception as e:
            conn.rollback()
            logger.error(f"Error registrando pesada: {e}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.put("/api/registros-bascula/{id}")
def editar_tarima(id: int, data: dict):
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            # Verificar si el viaje está conciliado
            cursor.execute("""
                SELECT v.estado FROM registrobascula r 
                JOIN viaje v ON r.viaje_id = v.id 
                WHERE r.id = ?
            """, (id,))
            v_row = cursor.fetchone()
            if v_row and v_row['estado'] == 'CONCILIADO':
                raise HTTPException(status_code=400, detail="Bloqueado: Esta pesada pertenece a un viaje ya consolidado contablemente.")

            cursor.execute("SELECT * FROM registrobascula WHERE id = ?", (id,))
            actual = dict(cursor.fetchone())
            
            tipo_fruta_id = data.get('tipo_fruta_id', actual['tipo_fruta_id'])
            cantidad_cajas = data.get('cantidad_cajas', actual['cantidad_cajas'])
            peso_neto = data.get('peso_neto', actual['peso_neto'])

            cursor.execute("""
                UPDATE registrobascula 
                SET peso_neto = ?, tipo_fruta_id = ?, cantidad_cajas = ?
                WHERE id = ?
            """, (peso_neto, tipo_fruta_id, cantidad_cajas, id))
            
            # También actualizar en inventario_frio si existe
            cursor.execute("""
                UPDATE inventario_frio 
                SET peso_neto = ?, cantidad_cajas = ?, tipo_fruta_id = ?
                WHERE origen_id = ? AND origen = 'PESADA'
            """, (peso_neto, cantidad_cajas, tipo_fruta_id, id))
            
            conn.commit()
            return {"status": "ok", "mensaje": "Tarima actualizada"}
        except HTTPException as he:
            raise he
        except Exception as e:
            conn.rollback()
            logger.error(f"Error editando tarima {id}: {e}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.delete("/api/registros-bascula/{id}")
def eliminar_tarima(id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT v.estado FROM registrobascula r 
                JOIN viaje v ON r.viaje_id = v.id 
                WHERE r.id = ?
            """, (id,))
            v_row = cursor.fetchone()
            if v_row and v_row['estado'] == 'CONCILIADO':
                raise HTTPException(status_code=400, detail="Bloqueado: No se puede eliminar pesadas de viajes consolidados.")

            # Eliminar del inventario frío si existe y no está mezclado
            cursor.execute("""
                DELETE FROM cuartofrio 
                WHERE inventario_frio_id IN (
                    SELECT id FROM inventario_frio WHERE origen_id = ? AND origen = 'PESADA'
                )
            """, (id,))
            cursor.execute("DELETE FROM inventario_frio WHERE origen_id = ? AND origen = 'PESADA'", (id,))
            cursor.execute("DELETE FROM registrobascula WHERE id = ?", (id,))
            conn.commit()
            return {"status": "ok", "mensaje": "Pesada eliminada correctamente"}
        except HTTPException as he:
            raise he
        except Exception as e:
            conn.rollback()
            logger.error(f"Error eliminando tarima {id}: {e}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")

# ==========================================
# INVENTARIO FRÍO (Gestión Independiente)
# ==========================================
@app.get("/api/inventario-frio")
def listar_inventario_frio():
    """Lista todas las tarimas en el inventario frío (activas)"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT i.*, v.tipo_operacion, 
                   a.nombre as acopiador_nombre,
                   c.nombre as cliente_nombre,
                   t.nombre as fruta_nombre
            FROM inventario_frio i
            LEFT JOIN viaje v ON i.viaje_id = v.id
            LEFT JOIN acopiador a ON v.acopiador_id = a.id
            LEFT JOIN cliente c ON v.cliente_id = c.id
            LEFT JOIN tipofruta t ON i.tipo_fruta_id = t.id
            WHERE i.activo = 1
            ORDER BY i.id DESC
        """)
        data = [dict(row) for row in cursor.fetchall()]
        return data

@app.post("/api/inventario-frio")
def crear_tarima_frio(tarima: dict):
    """Crear una tarima manualmente en el inventario frío (sin pasar por báscula)"""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            # viaje_id puede ser None
            viaje_id = tarima.get('viaje_id')
            if viaje_id:
                viaje_id = int(viaje_id)
            
            cursor.execute("""
                INSERT INTO inventario_frio (
                    viaje_id, tipo_fruta_id, numero_tarima_display, 
                    cantidad_cajas, peso_neto, fecha_ingreso, notas_referencia, 
                    origen, activo
                )
                VALUES (?, ?, ?, ?, ?, datetime('now'), ?, ?, 1)
            """, (
                viaje_id,  # Puede ser None
                tarima['tipo_fruta_id'], 
                tarima['numero_tarima_display'],
                tarima['cantidad_cajas'], 
                tarima['peso_neto'], 
                tarima.get('notas_referencia', "Creación manual en cuarto frío"),
                tarima.get('origen', 'MANUAL')
            ))
            conn.commit()
            nuevo_id = cursor.lastrowid
            return {"id": nuevo_id, "mensaje": "Tarima creada exitosamente"}
        except Exception as e:
            conn.rollback()
            logger.error(f"Error creando tarima frío: {e}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.put("/api/inventario-frio/{id}")
def editar_tarima_frio(id: int, data: dict):
    """Editar una tarima en el inventario frío"""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            # viaje_id puede ser None
            viaje_id = data.get('viaje_id')
            if viaje_id:
                viaje_id = int(viaje_id)
                
            cursor.execute("""
                UPDATE inventario_frio 
                SET viaje_id = ?, numero_tarima_display = ?, cantidad_cajas = ?, peso_neto = ?, tipo_fruta_id = ?
                WHERE id = ? AND activo = 1
            """, (
                viaje_id,
                data.get('numero_tarima_display'),
                data.get('cantidad_cajas'),
                data.get('peso_neto'),
                data.get('tipo_fruta_id'),
                id
            ))
            conn.commit()
            return {"status": "ok", "mensaje": "Tarima actualizada"}
        except Exception as e:
            conn.rollback()
            logger.error(f"Error editando tarima frío {id}: {e}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.delete("/api/inventario-frio/{id}")
def eliminar_tarima_frio(id: int):
    """Eliminar (desactivar) una tarima del inventario frío"""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            # Primero eliminar del cuarto frío
            cursor.execute("DELETE FROM cuartofrio WHERE inventario_frio_id = ?", (id,))
            # Desactivar en inventario
            cursor.execute("UPDATE inventario_frio SET activo = 0 WHERE id = ?", (id,))
            conn.commit()
            return {"mensaje": "Tarima eliminada del inventario"}
        except Exception as e:
            conn.rollback()
            logger.error(f"Error eliminando tarima frío {id}: {e}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")

# Agrega o actualiza este endpoint en main.py
class UnirTarimasRequest(BaseModel):
    id_inventario_1: int
    id_inventario_2: int
    nueva_fila_x: int
    nueva_columna_y: int
    nuevo_numero_tarima: str

@app.post("/api/inventario-frio/unir")
def unir_tarimas_frio(req: UnirTarimasRequest):
    """Unir dos tarimas en una sola (suma de cantidades)"""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            # Obtener las tarimas originales
            cursor.execute("SELECT * FROM inventario_frio WHERE id = ? AND activo = 1", (req.id_inventario_1,))
            t1 = cursor.fetchone()
            cursor.execute("SELECT * FROM inventario_frio WHERE id = ? AND activo = 1", (req.id_inventario_2,))
            t2 = cursor.fetchone()
            
            if not t1 or not t2:
                raise HTTPException(400, "No se encontraron las dos tarimas especificadas")
            
            t1 = dict(t1)
            t2 = dict(t2)
            
            # Calcular sumatorias
            nuevo_peso = t1['peso_neto'] + t2['peso_neto']
            nuevas_cajas = t1['cantidad_cajas'] + t2['cantidad_cajas']
            
            # Usar el viaje más antiguo para respetar PEPS
            fecha1 = datetime.fromisoformat(t1['fecha_ingreso'].replace('Z', '+00:00') if t1['fecha_ingreso'] else datetime.now().isoformat())
            fecha2 = datetime.fromisoformat(t2['fecha_ingreso'].replace('Z', '+00:00') if t2['fecha_ingreso'] else datetime.now().isoformat())
            viaje_principal = t1['viaje_id'] if fecha1 < fecha2 else t2['viaje_id']
            
            # Crear la nueva tarima combinada
            notas_referencia = f"Unión de {t1['numero_tarima_display']} ({t1['peso_neto']}kg) + {t2['numero_tarima_display']} ({t2['peso_neto']}kg)"
            
            cursor.execute("""
                INSERT INTO inventario_frio (
                    viaje_id, tipo_fruta_id, numero_tarima_display, 
                    cantidad_cajas, peso_neto, fecha_ingreso, notas_referencia, 
                    origen, activo
                )
                VALUES (?, ?, ?, ?, ?, datetime('now'), ?, 'UNION', 1)
            """, (viaje_principal, t1['tipo_fruta_id'], req.nuevo_numero_tarima, nuevas_cajas, nuevo_peso, notas_referencia))
            
            nueva_id = cursor.lastrowid
        
            # Liberar espacios en cuarto frío de las tarimas originales
            cursor.execute("DELETE FROM cuartofrio WHERE inventario_frio_id IN (?, ?)", (req.id_inventario_1, req.id_inventario_2))
            
            # Desactivar tarimas originales
            cursor.execute("UPDATE inventario_frio SET activo = 0 WHERE id IN (?, ?)", (req.id_inventario_1, req.id_inventario_2))
            
            # Posicionar la nueva tarima en la ubicación solicitada
            # Verificar que la ubicación no esté ocupada
            cursor.execute("SELECT id FROM cuartofrio WHERE fila_x = ? AND columna_y = ?", (req.nueva_fila_x, req.nueva_columna_y))
            if cursor.fetchone():
                # Si está ocupada, buscar una ubicación disponible
                cursor.execute("SELECT fila_x, columna_y FROM cuartofrio")
                ocupadas = cursor.fetchall()
                ocupadas_set = {(r['fila_x'], r['columna_y']) for r in ocupadas}
                
                for y in range(1, 6):
                    for x in range(1, 11):
                        if (x, y) not in ocupadas_set:
                            req.nueva_fila_x = x
                            req.nueva_columna_y = y
                            break
                    else:
                        continue
                    break
            
            cursor.execute("""
                INSERT INTO cuartofrio (fila_x, columna_y, inventario_frio_id) 
                VALUES (?, ?, ?)
            """, (req.nueva_fila_x, req.nueva_columna_y, nueva_id))

            conn.commit()
            return {
                "status": "ok", 
                "mensaje": "Tarimas unidas con éxito",
                "nueva_tarima_id": nueva_id,
                "nuevo_peso": nuevo_peso,
                "nuevas_cajas": nuevas_cajas
            }
        except Exception as e:
            conn.rollback()
            logger.error(f"Error uniendo tarimas: {e}")
            raise HTTPException(500, detail="Error interno del servidor")

@app.post("/api/inventario-frio/{id}/reasignar-viaje")
def reasignar_viaje_tarima(id: int, req: ReasignarViajeRequest):
    """Reasignar una tarima a otro viaje (cambia el dueño)"""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE inventario_frio 
                SET viaje_id = ?, notas_referencia = notas_referencia || ' | Reasignado a viaje #' || ?
                WHERE id = ? AND activo = 1
            """, (req.viaje_id, req.viaje_id, id))
            conn.commit()
            return {"status": "ok", "mensaje": "Tarima reasignada exitosamente"}
        except Exception as e:
            conn.rollback()
            logger.error(f"Error reasignando viaje tarima {id}: {e}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")

# ==========================================
# CUARTO FRÍO (Ubicaciones)
# ==========================================
@app.get("/api/cuarto-frio")
def listar_cuarto_frio():
    """Obtener todas las ubicaciones del cuarto frío con sus tarimas asociadas"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.id, c.fila_x, c.columna_y, c.inventario_frio_id,
                   i.numero_tarima_display, i.cantidad_cajas, i.peso_neto, i.viaje_id,
                   i.tipo_fruta_id, i.origen, i.notas_referencia,
                   v.tipo_operacion,
                   a.nombre as acopiador_nombre,
                   cl.nombre as cliente_nombre,
                   t.nombre as fruta_nombre
            FROM cuartofrio c
            LEFT JOIN inventario_frio i ON c.inventario_frio_id = i.id AND i.activo = 1
            LEFT JOIN viaje v ON i.viaje_id = v.id
            LEFT JOIN acopiador a ON v.acopiador_id = a.id
            LEFT JOIN cliente cl ON v.cliente_id = cl.id
            LEFT JOIN tipofruta t ON i.tipo_fruta_id = t.id
            ORDER BY c.columna_y, c.fila_x
        """)
        data = [dict(row) for row in cursor.fetchall()]
        return data

@app.post("/api/cuarto-frio")
def asignar_ubicacion(datos: dict):
    """Asignar una tarima a una ubicación en el cuarto frío"""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            # Verificar si la ubicación ya está ocupada
            cursor.execute("SELECT id FROM cuartofrio WHERE fila_x = ? AND columna_y = ?", 
                           (datos['fila_x'], datos['columna_y']))
            if cursor.fetchone():
                raise HTTPException(400, "Esa ubicación en el cuarto frío ya está ocupada.")
            
            # Verificar que la tarima existe y está activa
            cursor.execute("SELECT id FROM inventario_frio WHERE id = ? AND activo = 1", 
                           (datos['inventario_frio_id'],))
            if not cursor.fetchone():
                raise HTTPException(400, "La tarima no existe o ya no está activa")
            
            cursor.execute("""
                INSERT INTO cuartofrio (fila_x, columna_y, inventario_frio_id)
                VALUES (?, ?, ?)
            """, (datos['fila_x'], datos['columna_y'], datos['inventario_frio_id']))
            conn.commit()
            return {"mensaje": "Ubicación asignada correctamente"}
        except HTTPException as he:
            raise he
        except Exception as e:
            conn.rollback()
            logger.error(f"Error asignando ubicación: {e}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.put("/api/cuarto-frio/{inventario_frio_id}/mover")
def mover_tarima(inventario_frio_id: int, datos: MoverTarimaRequest):
    """Mover una tarima a otra ubicación"""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            # Verificar si la ubicación destino ya está ocupada
            cursor.execute("SELECT id FROM cuartofrio WHERE fila_x = ? AND columna_y = ? AND inventario_frio_id != ?", 
                           (datos.fila_x, datos.columna_y, inventario_frio_id))
            if cursor.fetchone():
                raise HTTPException(400, "La ubicación destino ya está ocupada.")
            
            # Actualizar ubicación
            cursor.execute("""
                UPDATE cuartofrio 
                SET fila_x = ?, columna_y = ? 
                WHERE inventario_frio_id = ?
            """, (datos.fila_x, datos.columna_y, inventario_frio_id))
            conn.commit()
            return {"mensaje": "Movimiento exitoso"}
        except HTTPException as he:
            raise he
        except Exception as e:
            conn.rollback()
            logger.error(f"Error moviendo tarima {inventario_frio_id}: {e}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.delete("/api/cuarto-frio/{inventario_frio_id}")
def sacar_tarima_frio(inventario_frio_id: int):
    """Retirar una tarima del cuarto frío (sin eliminarla, solo sacarla de la ubicación)"""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM cuartofrio WHERE inventario_frio_id = ?", (inventario_frio_id,))
            conn.commit()
            return {"mensaje": "Tarima retirada del cuarto frío"}
        except Exception as e:
            conn.rollback()
            logger.error(f"Error sacando tarima frío {inventario_frio_id}: {e}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.get("/api/cuarto-frio/ubicaciones-disponibles")
def ubicaciones_disponibles():
    """Obtener lista de ubicaciones libres en el cuarto frío"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT fila_x, columna_y FROM cuartofrio")
        ocupadas = cursor.fetchall()
        ocupadas_set = {(r['fila_x'], r['columna_y']) for r in ocupadas}
        
        disponibles = []
        for x in range(1, 11):  # 10 columnas
            for y in range(1, 6):  # 5 filas
                if (x, y) not in ocupadas_set:
                    disponibles.append({"fila_x": x, "columna_y": y})
        
        return disponibles

# ==========================================
# PAGOS (LIQUIDACIÓN A PROVEEDORES)
# ==========================================
@app.get("/api/pagos")
def listar_pagos():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.*, pr.nombre as proveedor_nombre 
            FROM pago p
            JOIN proveedor pr ON p.proveedor_id = pr.id
            ORDER BY p.id DESC
        """)
        data = [dict(row) for row in cursor.fetchall()]
        return data

@app.post("/api/pagos", status_code=201)
def registrar_pago(pago: PagoData):
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO pago (proveedor_id, folio_pago, fecha_pago, monto_total, metodo_pago)
                VALUES (?, ?, datetime('now'), ?, ?)
            """, (pago.proveedor_id, pago.folio_pago, pago.monto_total, pago.metodo_pago))
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
            conn.rollback()
            logger.error(f"Error registrando pago: {e}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.put("/api/pagos/{id}")
def editar_pago(id: int, data: dict):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE pago SET folio_pago = ?, fecha_pago = ?, metodo_pago = ? WHERE id = ?", 
                       (data['folio_pago'], data['fecha_pago'], data['metodo_pago'], id))
        conn.commit()
        return {"status": "ok"}

@app.delete("/api/pagos/{id}")
def anular_pago(id: int):
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE notaproveedor SET estado_pago = 'PENDIENTE', pago_id = NULL WHERE pago_id = ?", (id,))
            cursor.execute("DELETE FROM pago WHERE id = ?", (id,))
            conn.commit()
            return {"status": "ok", "mensaje": "Pago anulado y notas liberadas"}
        except Exception as e:
            conn.rollback()
            logger.error(f"Error anulando pago {id}: {e}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")

# ==========================================
# BÁSCULA ESP32 - Thread-safe usando tabla temporal
# ==========================================
@app.post("/api/bascula/leer")
def recibir_peso_esp32(datos: dict):
    """Recibe peso del ESP32 y lo almacena en base de datos"""
    peso = float(datos.get("peso", 0.0))
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            # Crear tabla temporal si no existe para estado de báscula
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bascula_estado (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    peso_actual REAL DEFAULT 0.0,
                    ultima_actualizacion DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insertar o actualizar el estado (solo una fila con id=1)
            cursor.execute("""
                INSERT OR REPLACE INTO bascula_estado (id, peso_actual, ultima_actualizacion)
                VALUES (1, ?, datetime('now'))
            """, (peso,))
            
            conn.commit()
            logger.debug(f"Peso recibido de ESP32: {peso}kg")
            return {"mensaje": "Peso recibido", "peso": peso}
        except Exception as e:
            logger.error(f"Error guardando peso de báscula: {e}")
            raise HTTPException(status_code=500, detail="Error interno del servidor")

@app.get("/api/bascula/peso-actual")
def obtener_peso_actual():
    """Obtiene el peso actual de la báscula desde base de datos"""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT peso_actual FROM bascula_estado WHERE id = 1")
            row = cursor.fetchone()
            if row:
                peso = row['peso_actual']
            else:
                peso = 0.0
            return {"peso": peso}
        except Exception as e:
            logger.error(f"Error obteniendo peso actual: {e}")
            return {"peso": 0.0}

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
    
    # Agrega estos endpoints después de los existentes en main.py

# ==========================================
# ELIMINAR TARIMA DEL FRÍO (MARCAR COMO ENVIADA/DESCARGADA)
# ==========================================
@app.delete("/api/inventario-frio/{id}/enviar")
def marcar_tarima_enviada(id: int, notas: Optional[str] = None):
    """Marcar una tarima como enviada/descargada (no eliminar, solo desactivar)"""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            # Verificar si existe
            cursor.execute("SELECT id FROM inventario_frio WHERE id = ? AND activo = 1", (id,))
            if not cursor.fetchone():
                raise HTTPException(404, "Tarima no encontrada o ya fue procesada")
            
            # Eliminar del cuarto frío si estaba ubicada
            cursor.execute("DELETE FROM cuartofrio WHERE inventario_frio_id = ?", (id,))
            
            # Marcar como enviada (desactivar)
            nota_extra = f" | Enviada: {notas}" if notas else ""
            cursor.execute("""
                UPDATE inventario_frio 
                SET activo = 0, 
                    notas_referencia = notas_referencia || ? || datetime('now')
                WHERE id = ?
            """, (nota_extra, id))
            
            conn.commit()
            return {"mensaje": "Tarima marcada como enviada exitosamente"}
        except HTTPException as he:
            raise he
        except Exception as e:
            conn.rollback()
            logger.error(f"Error marcando tarima enviada {id}: {e}")
            raise HTTPException(500, detail="Error interno del servidor")

# ==========================================
# OBTENER TARIMAS ENVIADAS (HISTÓRICO)
# ==========================================
@app.get("/api/inventario-frio/enviadas")
def listar_tarimas_enviadas():
    """Listar tarimas que ya fueron enviadas/descargadas"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT i.*, v.tipo_operacion, 
                   a.nombre as acopiador_nombre,
                   c.nombre as cliente_nombre,
                   t.nombre as fruta_nombre
            FROM inventario_frio i
            LEFT JOIN viaje v ON i.viaje_id = v.id
            LEFT JOIN acopiador a ON v.acopiador_id = a.id
            LEFT JOIN cliente c ON v.cliente_id = c.id
            LEFT JOIN tipofruta t ON i.tipo_fruta_id = t.id
            WHERE i.activo = 0
            ORDER BY i.id DESC
            LIMIT 100
        """)
        data = [dict(row) for row in cursor.fetchall()]
        return data

# ==========================================
# REACTIVAR TARIMA (SI SE NECESITA)
# ==========================================
@app.post("/api/inventario-frio/{id}/reactivar")
def reactivar_tarima(id: int):
    """Reactivar una tarima que fue marcada como enviada"""
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE inventario_frio 
                SET activo = 1, 
                    notas_referencia = notas_referencia || ' | Reactivada: ' || datetime('now')
                WHERE id = ? AND activo = 0
            """, (id,))
            conn.commit()
            return {"mensaje": "Tarima reactivada exitosamente"}
        except Exception as e:
            conn.rollback()
            logger.error(f"Error reactivando tarima {id}: {e}")
            raise HTTPException(500, detail="Error interno del servidor")