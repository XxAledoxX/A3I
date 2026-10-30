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

# Formato del login (RF-015): letras sin tilde, números, punto, guion y
# guion bajo. El máximo es el de la columna usuario.login, VARCHAR(30)
LONGITUD_MINIMA_LOGIN = 3
LONGITUD_MAXIMA_LOGIN = 30
PATRON_LOGIN = rf"[A-Za-z0-9._-]{{{LONGITUD_MINIMA_LOGIN},{LONGITUD_MAXIMA_LOGIN}}}"

# Minutos sin usar la aplicación antes de cerrar la sesión
MINUTOS_INACTIVIDAD = 10
