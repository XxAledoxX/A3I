"""Consultas a la base de datos. Todo el SQL de la aplicación va aquí."""

import pymysql
from pymysql.cursors import DictCursor

from app import config


class ErrorBaseDatos(Exception):
    pass


def _conectar() -> pymysql.connections.Connection:
    return pymysql.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=True,
        connect_timeout=5,
    )


def _consultar_uno(sql: str, parametros: tuple) -> dict | None:
    try:
        with _conectar() as conexion, conexion.cursor() as cursor:
            cursor.execute(sql, parametros)
            return cursor.fetchone()
    except pymysql.Error as error:
        raise ErrorBaseDatos("Error al consultar la base de datos") from error


def _ejecutar(sql: str, parametros: tuple) -> None:
    try:
        with _conectar() as conexion, conexion.cursor() as cursor:
            cursor.execute(sql, parametros)
    except pymysql.Error as error:
        raise ErrorBaseDatos("Error al modificar la base de datos") from error


def buscar_por_login(login: str) -> dict | None:
    sql = """
        SELECT u.id_usuario, u.nombre, u.login, u.hash_contrasena,
               u.intentos_fallidos, u.estado, u.rango, u.nivel,
               p.nombre AS perfil
        FROM usuario u
        JOIN perfil p ON p.id_perfil = u.id_perfil
        WHERE u.login = %s
    """
    return _consultar_uno(sql, (login,))


def actualizar_intentos(id_usuario: int, intentos: int) -> None:
    _ejecutar(
        "UPDATE usuario SET intentos_fallidos = %s WHERE id_usuario = %s",
        (intentos, id_usuario),
    )


def registrar_fallo(login: str, max_intentos: int) -> None:
    """Suma un intento fallido y bloquea la cuenta al llegar al máximo."""
    # En una sola consulta para no perder fallos si llegan dos a la vez.
    # estado va primero porque MariaDB asigna de izquierda a derecha
    _ejecutar(
        """
        UPDATE usuario
        SET estado = IF(intentos_fallidos + 1 >= %s, 'bloqueado', estado),
            intentos_fallidos = intentos_fallidos + 1
        WHERE login = %s AND estado = 'activo'
        """,
        (max_intentos, login),
    )


def actualizar_hash(id_usuario: int, nuevo_hash: str) -> None:
    _ejecutar(
        "UPDATE usuario SET hash_contrasena = %s WHERE id_usuario = %s",
        (nuevo_hash, id_usuario),
    )
