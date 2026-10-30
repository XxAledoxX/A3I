"""Configuración de la aplicación."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Lee el .env de la raíz del proyecto
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME", "a3i")
DB_USER = os.getenv("DB_USER", "a3i_app")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# Intentos fallidos antes de bloquear la cuenta
MAX_INTENTOS_FALLIDOS = 5

# Minutos sin usar la aplicación antes de cerrar la sesión
MINUTOS_INACTIVIDAD = 10
