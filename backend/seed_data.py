# seed_data.py - Script para generar datos de prueba
import sys
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import random

# Agregar el directorio app al path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import get_db

# Datos de prueba
ACOPIADORES = [
    "Juan Pérez", "María García", "Carlos López", "Ana Rodríguez", 
    "Pedro Sánchez", "Laura Martínez", "Miguel González", "Carmen Hernández",
    "Roberto Díaz", "Francisco Ruiz", "Elena Morales", "José Torres"
]

PROVEEDORES = [
    "AgroExport S.A.", "Frutas del Valle", "Cosecha Fresca", 
    "Productores Unidos", "Campo Verde", "Harvest Ltd.",
    "Frutícola del Norte", "Agrícola del Sur", "Exportadora Central"
]

CLIENTES = [
    "Supermercados El Grande", "Tiendas Express", "Distribuidora Nacional",
    "Mercado Central", "Exportadora Internacional", "Fruterías Don Juan"
]

TIPOS_FRUTA = [
    ("Manzana", "Manzana roja deliciosa"),
    ("Naranja", "Naranja valencia"),
    ("Limón", "Limón persa"),
    ("Pera", "Pera europea"),
    ("Uva", "Uva verde sin semilla"),
    ("Mango", "Mango Tommy Atkins"),
    ("Papaya", "Papaya maradol"),
    ("Piña", "Piña golden"),
    ("Plátano", "Plátano macho"),
    ("Aguacate", "Aguacate hass")
]

def generar_fecha_aleatoria(dias_atras=30):
    """Genera una fecha aleatoria en los últimos N días"""
    hoy = datetime.now()
    delta = timedelta(days=random.randint(0, dias_atras))
    return (hoy - delta).isoformat()

def generar_placa():
    """Genera una placa de vehículo aleatoria"""
    letras = ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=3))
    numeros = ''.join(random.choices('0123456789', k=3))
    return f"{letras}-{numeros}"

def generar_folio():
    """Genera un folio aleatorio"""
    prefijos = ['A', 'B', 'C', 'F', 'N', 'P']
    prefijo = random.choice(prefijos)
    numero = random.randint(1000, 9999)
    return f"{prefijo}-{numero}"

def seed_database():
    """Poblar la base de datos con datos de prueba"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        print("🌱 Iniciando generación de datos de prueba...")
        
        # 1. Insertar acopiadores
        print("📝 Insertando acopiadores...")
        acopiador_ids = {}
        for nombre in ACOPIADORES:
            cursor.execute(
                "INSERT INTO acopiador (nombre, telefono) VALUES (?, ?)",
                (nombre, f"555-{random.randint(1000, 9999)}")
            )
            acopiador_ids[nombre] = cursor.lastrowid
        
        # 2. Insertar proveedores
        print("📝 Insertando proveedores...")
        proveedor_ids = {}
        for nombre in PROVEEDORES:
            cursor.execute(
                "INSERT INTO proveedor (nombre, contacto) VALUES (?, ?)",
                (nombre, f"contacto@{nombre.lower().replace(' ', '').replace('.', '')}.com")
            )
            proveedor_ids[nombre] = cursor.lastrowid
        
        # 3. Insertar clientes
        print("📝 Insertando clientes...")
        cliente_ids = {}
        for nombre in CLIENTES:
            cursor.execute(
                "INSERT INTO cliente (nombre, contacto) VALUES (?, ?)",
                (nombre, f"ventas@{nombre.lower().replace(' ', '').replace('.', '')}.com")
            )
            cliente_ids[nombre] = cursor.lastrowid
        
        # 4. Insertar tipos de fruta
        print("📝 Insertando tipos de fruta...")
        fruta_ids = {}
        for nombre, descripcion in TIPOS_FRUTA:
            cursor.execute(
                "INSERT INTO tipofruta (nombre, descripcion) VALUES (?, ?)",
                (nombre, descripcion)
            )
            fruta_ids[nombre] = cursor.lastrowid
        
        # 5. Insertar viajes (ACOPIO y MAQUILA)
        print("📝 Insertando viajes...")
        viaje_ids = []
        
        # Generar viajes de ACOPIO
        for i in range(25):
            acopiador = random.choice(list(acopiador_ids.keys()))
            cursor.execute(
                """INSERT INTO viaje 
                (acopiador_id, cliente_id, placa, fecha_entrada, estado, tipo_operacion) 
                VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    acopiador_ids[acopiador],
                    None,
                    generar_placa(),
                    generar_fecha_aleatoria(30),
                    random.choice(['ACTIVO', 'CERRADO', 'CONCILIADO']),
                    'ACOPIO'
                )
            )
            viaje_ids.append(cursor.lastrowid)
        
        # Generar viajes de MAQUILA
        for i in range(10):
            cliente = random.choice(list(cliente_ids.keys()))
            cursor.execute(
                """INSERT INTO viaje 
                (acopiador_id, cliente_id, placa, fecha_entrada, estado, tipo_operacion) 
                VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    None,
                    cliente_ids[cliente],
                    'N/A',
                    generar_fecha_aleatoria(30),
                    random.choice(['ACTIVO', 'CERRADO', 'CONCILIADO']),
                    'MAQUILA'
                )
            )
            viaje_ids.append(cursor.lastrowid)
        
        # 6. Insertar registros de báscula (pesadas)
        print("📝 Insertando registros de báscula...")
        registro_ids = []
        
        for viaje_id in viaje_ids:
            # Cada viaje tiene entre 3 y 8 tarimas
            num_tarimas = random.randint(3, 8)
            
            for i in range(num_tarimas):
                fruta = random.choice(list(fruta_ids.keys()))
                cantidad_cajas = random.randint(30, 50)
                tara_caja = round(random.uniform(1.5, 2.0), 2)
                tara_tarima = round(random.uniform(20.0, 22.0), 2)
                peso_bruto = round(random.uniform(800.0, 1200.0), 2)
                tara_total = (cantidad_cajas * tara_caja) + tara_tarima
                peso_neto = round(peso_bruto - tara_total, 2)
                promedio_peso_caja = round(peso_neto / cantidad_cajas, 2)
                
                cursor.execute(
                    """INSERT INTO registrobascula 
                    (viaje_id, maquila_id, numero_tarima, tipo_fruta_id, cantidad_cajas, 
                     tara_caja, tara_tarima, peso_bruto, tara_total, 
                     peso_neto, promedio_peso_caja) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        viaje_id,
                        None,
                        i + 1,
                        fruta_ids[fruta],
                        cantidad_cajas,
                        tara_caja,
                        tara_tarima,
                        peso_bruto,
                        tara_total,
                        peso_neto,
                        promedio_peso_caja
                    )
                )
                registro_ids.append(cursor.lastrowid)
        
        # 7. Insertar notas de proveedores
        print("📝 Insertando notas de proveedores...")
        nota_ids = []
        
        for i in range(40):
            proveedor = random.choice(list(proveedor_ids.keys()))
            fruta = random.choice(list(fruta_ids.keys()))
            cantidad_cajas = random.randint(20, 60)
            tara_tarima = round(random.uniform(20.0, 22.0), 2)
            tara_caja = round(random.uniform(1.5, 2.0), 2)
            peso_bruto = round(random.uniform(500.0, 1500.0), 2)
            tara_total = tara_tarima + (cantidad_cajas * tara_caja)
            peso_neto = round(peso_bruto - tara_total, 2)
            precio_kg = round(random.uniform(8.0, 15.0), 2)
            total_monetario = round(peso_neto * precio_kg, 2)
            
            cursor.execute(
                """INSERT INTO notaproveedor 
                (proveedor_id, viaje_id, folio, fecha, tipo_fruta_id, cantidad_cajas, 
                 tara_tarima, tara_caja, peso_bruto, peso_neto, precio_kg, total_monetario, estado_pago) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    proveedor_ids[proveedor],
                    None,  # Inicialmente sin viaje
                    generar_folio(),
                    generar_fecha_aleatoria(30),
                    fruta_ids[fruta],
                    cantidad_cajas,
                    tara_tarima,
                    tara_caja,
                    peso_bruto,
                    peso_neto,
                    precio_kg,
                    total_monetario,
                    random.choice(['PENDIENTE', 'PAGADO'])
                )
            )
            nota_ids.append(cursor.lastrowid)
        
        # 8. Conciliar algunas notas con viajes
        print("📝 Conciliando notas con viajes...")
        notas_libres = nota_ids[:20]
        viajes_cerrados = [v for v in viaje_ids if random.random() > 0.5][:15]
        
        for i, (nota_id, viaje_id) in enumerate(zip(notas_libres, viajes_cerrados)):
            # Asignar nota al viaje
            cursor.execute(
                "UPDATE notaproveedor SET viaje_id = ? WHERE id = ?",
                (viaje_id, nota_id)
            )
            
            # Actualizar estado del viaje a CONCILIADO
            cursor.execute(
                "UPDATE viaje SET estado = 'CONCILIADO' WHERE id = ?",
                (viaje_id,)
            )
        
        # 9. Insertar pagos
        print("📝 Insertando pagos...")
        notas_pendientes = nota_ids[20:]
        
        for i in range(15):
            proveedor = random.choice(list(proveedor_ids.keys()))
            # Seleccionar 2-4 notas para este pago
            notas_pago = random.sample(notas_pendientes, random.randint(2, 4))
            monto_total = sum(random.uniform(5000, 15000) for _ in notas_pago)
            
            cursor.execute(
                """INSERT INTO pago 
                (proveedor_id, folio_pago, fecha_pago, metodo_pago, monto_total) 
                VALUES (?, ?, ?, ?, ?)""",
                (
                    proveedor_ids[proveedor],
                    generar_folio(),
                    generar_fecha_aleatoria(30),
                    random.choice(['TRANSFERENCIA', 'EFECTIVO', 'CHEQUE']),
                    round(monto_total, 2)
                )
            )
            pago_id = cursor.lastrowid
            
            # Asociar notas al pago
            for nota_id in notas_pago:
                cursor.execute(
                    "UPDATE notaproveedor SET pago_id = ?, estado_pago = 'PAGADO' WHERE id = ?",
                    (pago_id, nota_id)
                )
        
        # 10. Insertar inventario frío (tarimas)
        print("📝 Insertando inventario frío...")
        inventario_ids = []
        
        # Crear tarimas a partir de registros de báscula
        for registro_id in registro_ids[:50]:
            cursor.execute("SELECT * FROM registrobascula WHERE id = ?", (registro_id,))
            registro = cursor.fetchone()
            
            if registro:
                fruta = random.choice(list(fruta_ids.keys()))
                cursor.execute(
                    """INSERT INTO inventario_frio 
                    (viaje_id, tipo_fruta_id, numero_tarima_display, cantidad_cajas, 
                     peso_neto, notas_referencia, origen, activo) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        registro['viaje_id'],
                        fruta_ids[fruta],
                        f"T-{random.randint(1000, 9999)}",
                        registro['cantidad_cajas'],
                        registro['peso_neto'],
                        "Generado desde báscula",
                        "BASCULA",
                        1
                    )
                )
                inventario_ids.append(cursor.lastrowid)
        
        # Crear algunas tarimas manuales
        for i in range(10):
            fruta = random.choice(list(fruta_ids.keys()))
            cursor.execute(
                """INSERT INTO inventario_frio 
                (viaje_id, tipo_fruta_id, numero_tarima_display, cantidad_cajas, 
                 peso_neto, notas_referencia, origen, activo) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    None,
                    fruta_ids[fruta],
                    f"MAN-{random.randint(1000, 9999)}",
                    random.randint(30, 50),
                    round(random.uniform(700.0, 1100.0), 2),
                    "Tarima manual",
                    "MANUAL",
                    1
                )
            )
            inventario_ids.append(cursor.lastrowid)
        
        # 11. Insertar ubicaciones en cuarto frío
        print("📝 Insertando ubicaciones en cuarto frío...")
        # Ubicar algunas tarimas en el cuarto frío (matriz 10x5)
        tarimas_en_frio = random.sample(inventario_ids, min(35, len(inventario_ids)))
        
        for i, inventario_id in enumerate(tarimas_en_frio):
            fila = (i % 5) + 1
            columna = (i // 5) + 1
            
            cursor.execute(
                """INSERT INTO cuartofrio 
                (inventario_frio_id, fila_x, columna_y) 
                VALUES (?, ?, ?)""",
                (inventario_id, columna, fila)
            )
        
        conn.commit()
        
        print("✅ Datos de prueba generados exitosamente!")
        print(f"📊 Resumen:")
        print(f"   - Acopiadores: {len(acopiador_ids)}")
        print(f"   - Proveedores: {len(proveedor_ids)}")
        print(f"   - Clientes: {len(cliente_ids)}")
        print(f"   - Tipos de fruta: {len(fruta_ids)}")
        print(f"   - Viajes: {len(viaje_ids)}")
        print(f"   - Registros de báscula: {len(registro_ids)}")
        print(f"   - Notas: {len(nota_ids)}")
        print(f"   - Pagos: 15")
        print(f"   - Inventario frío: {len(inventario_ids)}")
        print(f"   - Ubicaciones en frío: {len(tarimas_en_frio)}")

if __name__ == "__main__":
    try:
        seed_database()
    except Exception as e:
        print(f"❌ Error generando datos de prueba: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
