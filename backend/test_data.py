import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'data', 'sauce_erp.db')
conn = sqlite3.connect(db_path)
c = conn.cursor()
c.execute("INSERT INTO acopiador (nombre) VALUES ('Juan Acopiador')")
c.execute("INSERT INTO cliente (nombre) VALUES ('Supermercados XYZ')")
c.execute("INSERT INTO tipofruta (nombre) VALUES ('Aguacate Hass')")
conn.commit()
conn.close()
print("Datos de prueba insertados.")
