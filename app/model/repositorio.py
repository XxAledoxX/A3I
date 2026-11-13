"""Consultas a la base de datos. Todo el SQL de la aplicación va aquí.

Los valores nunca se introducen en el SQL: van con %s y se pasan aparte
en una tupla, y PyMySQL los escapa.

    _consultar_uno("SELECT ... WHERE login = %s", (login,))

- Nada de f-strings, +, % ni .format() para construir el SQL.
- Con un solo valor la tupla lleva coma: (login,).
- Un % que forme parte del SQL se escribe %%.
- LIKE: el comodín va en el valor, ("%" + texto + "%",).
- IN: un %s por valor, ", ".join(["%s"] * len(valores)).
- Los nombres de tabla o columna no se pueden pasar con %s. Si tienen que
  cambiar, se eligen de una lista fija escrita en el código.
- La app solo ejecuta procedimientos (CALL), con el usuario de BD del login
  o el del perfil (RF-013). Un procedimiento nuevo necesita su GRANT EXECUTE
  en db/007_control_acceso.sql.
"""

import pymysql
from pymysql.cursors import DictCursor

from app import config

# Usuario y contraseña de BD con los que conectarse
Credenciales = tuple[str, str]

# Perfil con el que se inició sesión; None si no hay sesión
_perfil_conectado: str | None = None


class ErrorBaseDatos(Exception):
    pass


def _conectar(usuario: str | None = None,
              contrasena: str | None = None) -> pymysql.connections.Connection:
    """Abre una conexión. Sin usuario, usa el de DB_USER del .env."""
    if usuario is None:
        usuario, contrasena = config.DB_USER, config.DB_PASSWORD
    return pymysql.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=usuario,
        password=contrasena,
        database=config.DB_NAME,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=True,
        connect_timeout=5,
    )


def _comprobar_parametros(parametros: tuple) -> None:
    if not isinstance(parametros, tuple):
        raise TypeError("Los parámetros de la consulta deben ser una tupla")


def _consultar_uno(sql: str, parametros: tuple,
                   credenciales: Credenciales | None = None) -> dict | None:
    _comprobar_parametros(parametros)
    try:
        with _conectar(*(credenciales or ())) as conexion, conexion.cursor() as cursor:
            cursor.execute(sql, parametros)
            return cursor.fetchone()
    except pymysql.Error as error:
        raise ErrorBaseDatos("Error al consultar la base de datos") from error


def _consultar_todos(sql: str, parametros: tuple,
                     credenciales: Credenciales | None = None) -> list[dict]:
    _comprobar_parametros(parametros)
    try:
        with _conectar(*(credenciales or ())) as conexion, conexion.cursor() as cursor:
            cursor.execute(sql, parametros)
            return list(cursor.fetchall())
    except pymysql.Error as error:
        raise ErrorBaseDatos("Error al consultar la base de datos") from error


def _ejecutar(sql: str, parametros: tuple,
              credenciales: Credenciales | None = None) -> None:
    _comprobar_parametros(parametros)
    try:
        with _conectar(*(credenciales or ())) as conexion, conexion.cursor() as cursor:
            cursor.execute(sql, parametros)
    except pymysql.Error as error:
        raise ErrorBaseDatos("Error al modificar la base de datos") from error


def _credenciales_login() -> Credenciales:
    return config.DB_USUARIO_LOGIN, config.DB_PASSWORD_LOGIN


def _credenciales_perfil() -> Credenciales:
    """Usuario de BD del perfil de la sesión, para las consultas de datos."""
    if _perfil_conectado is None:
        raise ErrorBaseDatos("No hay ninguna sesión iniciada")
    return config.USUARIOS_PERFIL[_perfil_conectado]


def conectar_perfil(perfil: str) -> None:
    """Tras el login, las consultas de datos pasan al usuario de BD del perfil."""
    global _perfil_conectado
    usuario, contrasena = config.USUARIOS_PERFIL[perfil]
    try:
        _conectar(usuario, contrasena).close()
    except pymysql.Error as error:
        raise ErrorBaseDatos("Error al conectar con la base de datos") from error
    _perfil_conectado = perfil


def desconectar_perfil() -> None:
    global _perfil_conectado
    _perfil_conectado = None


# Login, con a3i_login

def buscar_por_login(login: str) -> dict | None:
    return _consultar_uno("CALL buscar_usuario(%s)", (login,), _credenciales_login())


def actualizar_intentos(id_usuario: int, intentos: int) -> None:
    _ejecutar(
        "CALL actualizar_intentos(%s, %s)", (id_usuario, intentos), _credenciales_login()
    )


def registrar_fallo(login: str, max_intentos: int) -> None:
    """Suma un intento fallido y bloquea la cuenta al llegar al máximo."""
    _ejecutar("CALL registrar_fallo(%s, %s)", (login, max_intentos), _credenciales_login())


def actualizar_hash(id_usuario: int, nuevo_hash: str) -> None:
    _ejecutar(
        "CALL actualizar_hash(%s, %s)", (id_usuario, nuevo_hash), _credenciales_login()
    )
