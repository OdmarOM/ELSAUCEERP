# init_admin.py - Script para crear usuario admin inicial
import sys
from pathlib import Path

# Agregar el directorio app al path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import get_db
from app.auth import get_password_hash

def create_admin_user():
    """Crea un usuario admin inicial si no existe"""
    username = "admin"
    password = "admin"
    role = "admin"
    
    with get_db() as conn:
        cursor = conn.cursor()
        try:
            # Crear tabla de usuarios si no existe (primero)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT DEFAULT 'user',
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            
            # Verificar si el usuario ya existe
            cursor.execute("SELECT id FROM usuarios WHERE username = ?", (username,))
            if cursor.fetchone():
                print(f"El usuario '{username}' ya existe. No se creará un nuevo usuario.")
                return
            
            # Hashear contraseña y crear usuario
            password_hash = get_password_hash(password)
            cursor.execute(
                "INSERT INTO usuarios (username, password_hash, role) VALUES (?, ?, ?)",
                (username, password_hash, role)
            )
            conn.commit()
            
            print(f"Usuario admin creado exitosamente:")
            print(f"  Username: {username}")
            print(f"  Password: {password}")
            print(f"  Role: {role}")
            print(f"\nIMPORTANTE: Cambia la contraseña del usuario admin después del primer login.")
        except Exception as e:
            conn.rollback()
            print(f"Error creando usuario admin: {e}")
            sys.exit(1)

if __name__ == "__main__":
    create_admin_user()
