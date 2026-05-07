from typing import Optional
from sqlmodel import Field, SQLModel
from datetime import datetime
from enum import Enum

# ==========================================
# 1. ENUMS (Estados Fijos para validación)
# ==========================================
class EstadoUbicacion(str, Enum):
    EN_BODEGA = "EN_BODEGA"
    EN_CUARTO_FRIO = "EN_CUARTO_FRIO"
    ENVIADA = "ENVIADA"

class EstadoViaje(str, Enum):
    ACTIVO = "ACTIVO"
    CERRADO = "CERRADO"
    CONCILIADO = "CONCILIADO"

class EstadoPago(str, Enum):
    PENDIENTE = "PENDIENTE"
    PAGADO = "PAGADO"

class EstadoMaquila(str, Enum):
    ACTIVO = "ACTIVO"
    FINALIZADO = "FINALIZADO"

# ==========================================
# 2. CATÁLOGOS BASE
# ==========================================
class Acopiador(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    telefono: Optional[str] = None

class Proveedor(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    contacto: Optional[str] = None

class Cliente(SQLModel, table=True):  # Para el flujo de Maquilas
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    contacto: Optional[str] = None

class TipoFruta(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    descripcion: Optional[str] = None

# ==========================================
# 3. FLUJO DE MAQUILA (Servicio Externo)
# ==========================================
class Maquila(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    cliente_id: int = Field(foreign_key="cliente.id")
    fecha_entrada: datetime = Field(default_factory=datetime.now)
    estado: str = Field(default=EstadoMaquila.ACTIVO.value)
    peso_total_procesado: float = 0.0

# ==========================================
# 4. FLUJO DE ACOPIO INTERNO (Viajes y Pagos)
# ==========================================
class Viaje(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    acopiador_id: int = Field(foreign_key="acopiador.id")
    placa: str
    fecha_entrada: datetime = Field(default_factory=datetime.now)
    estado: str = Field(default=EstadoViaje.ACTIVO.value)
    
    # Campo nuevo para definir el flujo: 'MAQUILA' o 'ACOPIO'
    tipo_operacion: str = Field(default="MAQUILA") 
    
    # Datos de conciliación crítica
    peso_total_fisico: float = 0.0
    peso_total_teorico: float = 0.0
    diferencia_peso: float = 0.0

class Pago(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    proveedor_id: int = Field(foreign_key="proveedor.id")
    folio_pago: str = Field(unique=True, index=True)
    fecha_pago: datetime = Field(default_factory=datetime.now)
    monto_total: float
    metodo_pago: str

class NotaProveedor(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    viaje_id: int = Field(foreign_key="viaje.id")
    proveedor_id: int = Field(foreign_key="proveedor.id")
    tipo_fruta_id: int = Field(foreign_key="tipofruta.id")
    pago_id: Optional[int] = Field(default=None, foreign_key="pago.id") # Nulo si no está pagada
    
    # Datos documentales
    fecha: datetime = Field(default_factory=datetime.now)
    cantidad_cajas: int
    tara_tarima: float
    tara_caja: float
    peso_bruto: float
    peso_neto: float
    precio_kg: float
    total_monetario: float
    estado_pago: str = Field(default=EstadoPago.PENDIENTE.value)

# ==========================================
# 5. EL CORAZÓN DE LA BÁSCULA (Registro Físico)
# ==========================================
class RegistroBascula(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    # Puede pertenecer a un Viaje (Interno) o a una Maquila (Externo)
    viaje_id: Optional[int] = Field(default=None, foreign_key="viaje.id")
    maquila_id: Optional[int] = Field(default=None, foreign_key="maquila.id")
    tipo_fruta_id: int = Field(foreign_key="tipofruta.id")
    
    numero_tarima: int
    fecha_hora: datetime = Field(default_factory=datetime.now)
    estado_ubicacion: str = Field(default=EstadoUbicacion.EN_BODEGA.value)
    
    # Datos de pesaje exactos
    cantidad_cajas: int
    tara_tarima: float
    tara_caja: float
    tara_total: float
    peso_bruto: float
    peso_neto: float
    promedio_peso_caja: float

# ==========================================
# 6. ALMACENAMIENTO VISUAL (Cuarto Frío)
# ==========================================
class CuartoFrio(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    fila_x: int
    columna_y: int
    # Si es Nulo, la interfaz entenderá que este espacio está "Disponible"
    tarima_id: Optional[int] = Field(default=None, foreign_key="registrobascula.id", unique=True)