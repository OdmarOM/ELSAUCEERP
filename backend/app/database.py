# database.py
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "sauce_erp.db"

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

    # 6. Viaje (Flujo Interno - Actualizado con cliente_id)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS viaje (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        acopiador_id INTEGER,
        cliente_id INTEGER,
        placa TEXT NOT NULL,
        fecha_entrada DATETIME,
        estado TEXT DEFAULT 'ACTIVO',
        peso_total_fisico REAL DEFAULT 0.0,
        peso_total_teorico REAL DEFAULT 0.0,
        diferencia_peso REAL DEFAULT 0.0,
        tipo_operacion TEXT DEFAULT 'ACOPIO',
        FOREIGN KEY(acopiador_id) REFERENCES acopiador(id),
        FOREIGN KEY(cliente_id) REFERENCES cliente(id)
    )""")

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
        FOREIGN KEY(viaje_id) REFERENCES viaje(id),
        FOREIGN KEY(tipo_fruta_id) REFERENCES tipofruta(id)
    )""")

    # 11. Cuarto Frío - Ahora apunta a inventario_frio
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cuartofrio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fila_x INTEGER,
        columna_y INTEGER,
        inventario_frio_id INTEGER UNIQUE,
        FOREIGN KEY(inventario_frio_id) REFERENCES inventario_frio(id)
    )""")

    conn.commit()
    conn.close()
    print("Base de datos de El Sauce ERP inicializada/actualizada correctamente.")

if __name__ == "__main__":
    create_db_and_tables()