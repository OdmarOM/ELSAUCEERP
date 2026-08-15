# database.py
import sqlite3
from pathlib import Path
from contextlib import contextmanager
import threading
from .config import settings

DB_PATH = settings.DB_PATH

# Lock para thread-safety en SQLite
db_lock = threading.Lock()

@contextmanager
def get_db():
    """Context manager para conexiones a base de datos con thread-safety"""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # Habilitar WAL mode para mejor concurrencia
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    
    try:
        with db_lock:
            yield conn
    finally:
        conn.close()

def create_db_and_tables():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Acopiador
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS acopiador (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        telefono TEXT
    )""")

    # 2. Proveedor
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS proveedor (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        contacto TEXT
    )""")

    # 3. Cliente (Catálogo nuevo para Maquila)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cliente (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        contacto TEXT
    )""")

    # 4. Tipo de Fruta
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tipofruta (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT NOT NULL,
        descripcion TEXT
    )""")

    # 5. Maquila (Flujo Externo)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS maquila (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER,
        fecha_entrada DATETIME,
        estado TEXT DEFAULT 'ACTIVO',
        peso_total_procesado REAL DEFAULT 0.0,
        FOREIGN KEY(cliente_id) REFERENCES cliente(id)
    )""")

    # 6. Viaje (Flujo Interno - Actualizado con cliente_id y fecha_salida)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS viaje (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        acopiador_id INTEGER,
        cliente_id INTEGER,
        placa TEXT NOT NULL,
        fecha_entrada DATETIME,
        fecha_salida DATETIME,
        estado TEXT DEFAULT 'ACTIVO',
        peso_total_fisico REAL DEFAULT 0.0,
        peso_total_teorico REAL DEFAULT 0.0,
        diferencia_peso REAL DEFAULT 0.0,
        tipo_operacion TEXT DEFAULT 'ACOPIO',
        tipo TEXT DEFAULT 'ENTRADA',
        FOREIGN KEY(acopiador_id) REFERENCES acopiador(id),
        FOREIGN KEY(cliente_id) REFERENCES cliente(id)
    )""")

    # Agregar columnas si no existen (para tablas existentes)
    try:
        cursor.execute("ALTER TABLE viaje ADD COLUMN fecha_salida DATETIME")
    except sqlite3.OperationalError:
        # La columna ya existe
        pass

    try:
        cursor.execute("ALTER TABLE viaje ADD COLUMN tipo TEXT DEFAULT 'ENTRADA'")
    except sqlite3.OperationalError:
        # La columna ya existe
        pass

    try:
        cursor.execute("ALTER TABLE viaje ADD COLUMN precio_kg_venta REAL DEFAULT 0.0")
    except sqlite3.OperationalError:
        pass

    # 7. Pagos (módulo financiero)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pago (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        proveedor_id INTEGER,
        folio_pago TEXT,
        fecha_pago DATETIME,
        monto_total REAL,
        metodo_pago TEXT,
        FOREIGN KEY(proveedor_id) REFERENCES proveedor(id)
    )""")

    # 8. Notas de Proveedor (con campo folio, pago_id y fecha explícita)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS notaproveedor (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        viaje_id INTEGER,
        proveedor_id INTEGER,
        tipo_fruta_id INTEGER,
        pago_id INTEGER,
        fecha DATETIME,
        cantidad_cajas INTEGER,
        tara_tarima REAL,
        tara_caja REAL,
        peso_bruto REAL,
        peso_neto REAL,
        precio_kg REAL,
        total_monetario REAL,
        estado_pago TEXT DEFAULT 'PENDIENTE',
        folio TEXT DEFAULT 'S/F',
        FOREIGN KEY(viaje_id) REFERENCES viaje(id),
        FOREIGN KEY(proveedor_id) REFERENCES proveedor(id),
        FOREIGN KEY(tipo_fruta_id) REFERENCES tipofruta(id),
        FOREIGN KEY(pago_id) REFERENCES pago(id)
    )""")

    # 9. Registro de Báscula (Pesadas / Tarimas) - Se mantiene como histórico
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS registrobascula (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        viaje_id INTEGER,
        maquila_id INTEGER,
        tipo_fruta_id INTEGER,
        numero_tarima INTEGER,
        fecha_hora DATETIME,
        estado_ubicacion TEXT DEFAULT 'EN_BODEGA',
        cantidad_cajas INTEGER,
        tara_tarima REAL,
        tara_caja REAL,
        tara_total REAL,
        peso_bruto REAL,
        peso_neto REAL,
        promedio_peso_caja REAL,
        FOREIGN KEY(viaje_id) REFERENCES viaje(id),
        FOREIGN KEY(maquila_id) REFERENCES maquila(id),
        FOREIGN KEY(tipo_fruta_id) REFERENCES tipofruta(id)
    )""")

    # 10. INVENTARIO FRÍO - Tabla independiente para gestión del cuarto frío
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventario_frio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        viaje_id INTEGER,
        tipo_fruta_id INTEGER,
        numero_tarima_display TEXT,
        cantidad_cajas INTEGER,
        peso_neto REAL,
        fecha_ingreso DATETIME,
        notas_referencia TEXT,
        origen TEXT DEFAULT 'PESADA',
        origen_id INTEGER,
        activo INTEGER DEFAULT 1,
        fecha_salida DATETIME,
        viaje_salida_id INTEGER,
        peso_salida REAL,
        FOREIGN KEY(viaje_id) REFERENCES viaje(id),
        FOREIGN KEY(tipo_fruta_id) REFERENCES tipofruta(id),
        FOREIGN KEY(viaje_salida_id) REFERENCES viaje(id)
    )""")

    # Agregar columnas de seguimiento de salida si no existen
    try:
        cursor.execute("ALTER TABLE inventario_frio ADD COLUMN fecha_salida DATETIME")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE inventario_frio ADD COLUMN viaje_salida_id INTEGER")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE inventario_frio ADD COLUMN peso_salida REAL")
    except sqlite3.OperationalError:
        pass

    # 11. Cuarto Frío - Ahora apunta a inventario_frio
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cuartofrio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fila_x INTEGER,
        columna_y INTEGER,
        inventario_frio_id INTEGER UNIQUE,
        FOREIGN KEY(inventario_frio_id) REFERENCES inventario_frio(id)
    )""")

    # 12. Viaje Salida Tarima - Trazabilidad de tarimas en salidas
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS viaje_salida_tarima (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        viaje_id INTEGER NOT NULL,
        inventario_frio_id INTEGER NOT NULL,
        fecha_salida DATETIME DEFAULT CURRENT_TIMESTAMP,
        peso_salida REAL,
        observaciones TEXT,
        FOREIGN KEY(viaje_id) REFERENCES viaje(id),
        FOREIGN KEY(inventario_frio_id) REFERENCES inventario_frio(id)
    )""")

    # 13. Cuentas por Cobrar (Clientes)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cuenta_cobrar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id INTEGER NOT NULL,
        viaje_salida_id INTEGER,
        maquila_id INTEGER,
        fecha_emision DATETIME DEFAULT CURRENT_TIMESTAMP,
        monto_total REAL NOT NULL DEFAULT 0.0,
        saldo_pendiente REAL NOT NULL DEFAULT 0.0,
        estado TEXT DEFAULT 'PENDIENTE',
        FOREIGN KEY(cliente_id) REFERENCES cliente(id),
        FOREIGN KEY(viaje_salida_id) REFERENCES viaje(id),
        FOREIGN KEY(maquila_id) REFERENCES maquila(id)
    )""")

    # 14. Cobros a Clientes (Pagos recibidos)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cobro_cliente (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cuenta_cobrar_id INTEGER NOT NULL,
        monto_cobrado REAL NOT NULL,
        fecha_cobro DATETIME DEFAULT CURRENT_TIMESTAMP,
        metodo_pago TEXT,
        referencia TEXT,
        FOREIGN KEY(cuenta_cobrar_id) REFERENCES cuenta_cobrar(id)
    )""")

    # ================= ÍNDICES PARA OPTIMIZACIÓN =================
    # Índices para consultas frecuentes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_viaje_estado ON viaje(estado)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_viaje_tipo ON viaje(tipo_operacion)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_viaje_fecha ON viaje(fecha_entrada)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_viaje_fecha_salida ON viaje(fecha_salida)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notaproveedor_viaje ON notaproveedor(viaje_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notaproveedor_proveedor ON notaproveedor(proveedor_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notaproveedor_pago ON notaproveedor(pago_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notaproveedor_estado ON notaproveedor(estado_pago)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_registrobascula_viaje ON registrobascula(viaje_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventario_frio_viaje ON inventario_frio(viaje_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventario_frio_activo ON inventario_frio(activo)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_inventario_frio_tipo ON inventario_frio(tipo_fruta_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pago_proveedor ON pago(proveedor_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cuartofrio_ubicacion ON cuartofrio(fila_x, columna_y)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_viaje_salida_tarima_viaje ON viaje_salida_tarima(viaje_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_viaje_salida_tarima_inventario ON viaje_salida_tarima(inventario_frio_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cuenta_cobrar_cliente ON cuenta_cobrar(cliente_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cuenta_cobrar_estado ON cuenta_cobrar(estado)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cobro_cliente_cuenta ON cobro_cliente(cuenta_cobrar_id)")

    conn.commit()
    conn.close()
    print("Base de datos de El Sauce ERP inicializada/actualizada correctamente.")

if __name__ == "__main__":
    create_db_and_tables()