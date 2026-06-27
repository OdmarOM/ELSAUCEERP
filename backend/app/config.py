import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class Settings:
    """Configuración centralizada de la aplicación"""
    
    # Servidor
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        origin.strip() 
        for origin in os.getenv("ALLOWED_ORIGINS", "*").split(",")
    ]
    
    # Base de Datos
    DB_PATH: Path = Path(os.getenv("DB_PATH", "./data/sauce_erp.db"))
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "./logs/erp.log")
    
    # ESP32
    ESP32_API_URL: str = os.getenv("ESP32_API_URL", "http://192.168.50.101:8000/api/bascula/leer")
    
    # JWT Authentication
    JWT_SECRET: str = os.getenv("JWT_SECRET", "tu_clave_secreta_muy_segura_cambiar_en_produccion")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 horas

settings = Settings()
