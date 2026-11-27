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
  en su script de db/ (como los de 007_control_acceso.sql).
"""

from datetime import datetime

import pymysql
from pymysql.cursors import DictCursor

from app import config

# Usuario y contraseña de BD con los que conectarse
Credenciales = tuple[str, str]

# Perfil con el que se inició sesión; None si no hay sesión
_perfil_conectado: str | None = None


class ErrorBaseDatos(Exception):
    pass


class ErrorRegla(ErrorBaseDatos):
    """La BD ha rechazado la operación por una regla; el mensaje es el de la BD."""


# Error de MariaDB cuando un procedimiento hace SIGNAL
ERROR_SIGNAL = 1644


def _error(error: pymysql.Error, mensaje: str) -> ErrorBaseDatos:
    """ErrorRegla con el mensaje de la BD si fue un SIGNAL; si no, ErrorBaseDatos."""
    if error.args and error.args[0] == ERROR_SIGNAL:
        return ErrorRegla(error.args[1])
    return ErrorBaseDatos(mensaje)


def _conectar(usuario: str, contrasena: str) -> pymysql.connections.Connection:
    try:
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
            # Siempre cifrado: se comprueba que el certificado del servidor lo firma
            # nuestra CA y que es para el host al que nos conectamos
            ssl_ca=config.DB_SSL_CA,
            ssl_verify_cert=True,
            ssl_verify_identity=True,
        )
    except OSError as error:
        # Sin el archivo de la CA (o con uno roto) no se puede conectar
        raise ErrorBaseDatos("Error al conectar con la base de datos") from error


def _comprobar_parametros(parametros: tuple) -> None:
    if not isinstance(parametros, tuple):
        raise TypeError("Los parámetros de la consulta deben ser una tupla")


def _consultar_uno(sql: str, parametros: tuple,
                   credenciales: Credenciales) -> dict | None:
    _comprobar_parametros(parametros)
    try:
        with _conectar(*credenciales) as conexion, conexion.cursor() as cursor:
            cursor.execute(sql, parametros)
            return cursor.fetchone()
    except pymysql.Error as error:
        raise _error(error, "Error al consultar la base de datos") from error


def _consultar_todos(sql: str, parametros: tuple,
                     credenciales: Credenciales) -> list[dict]:
    _comprobar_parametros(parametros)
    try:
        with _conectar(*credenciales) as conexion, conexion.cursor() as cursor:
            cursor.execute(sql, parametros)
            return list(cursor.fetchall())
    except pymysql.Error as error:
        raise _error(error, "Error al consultar la base de datos") from error


def _ejecutar(sql: str, parametros: tuple,
              credenciales: Credenciales) -> None:
    _comprobar_parametros(parametros)
    try:
        with _conectar(*credenciales) as conexion, conexion.cursor() as cursor:
            cursor.execute(sql, parametros)
    except pymysql.Error as error:
        raise _error(error, "Error al modificar la base de datos") from error


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


# Datos del panel, con el usuario de BD del perfil

def ultimas_lecturas(id_usuario: int) -> list[dict]:
    return _consultar_todos(
        "CALL ultimas_lecturas(%s)", (id_usuario,), _credenciales_perfil()
    )


def estado_actuadores(id_usuario: int) -> list[dict]:
    return _consultar_todos(
        "CALL estado_actuadores(%s)", (id_usuario,), _credenciales_perfil()
    )


def estado_equipos(id_usuario: int) -> list[dict]:
    return _consultar_todos(
        "CALL estado_equipos(%s)", (id_usuario,), _credenciales_perfil()
    )


def datos_panel(id_usuario: int) -> tuple[list[dict], list[dict], list[dict]]:
    """Lo que pide el panel en cada refresco: lecturas, actuadores y equipos."""
    return (
        ultimas_lecturas(id_usuario),
        estado_actuadores(id_usuario),
        estado_equipos(id_usuario),
    )


def historico_lecturas(id_usuario: int, variable: str, desde: datetime,
                       hasta: datetime,
                       puntos: int = config.PUNTOS_HISTORICO) -> list[dict]:
    """Lecturas de una variable entre dos fechas, agrupadas en tramos."""
    return _consultar_todos(
        "CALL historico_lecturas(%s, %s, %s, %s, %s)",
        (id_usuario, variable, desde, hasta, puntos),
        _credenciales_perfil(),
    )


# Avisos (RF-006), con el usuario de BD del perfil

def mis_notificaciones(id_usuario: int) -> list[dict]:
    """Avisos sin leer del usuario, el más reciente primero."""
    return _consultar_todos(
        "CALL mis_notificaciones(%s)", (id_usuario,), _credenciales_perfil()
    )


def marcar_notificacion_leida(id_usuario: int, id_notificacion: int) -> None:
    _ejecutar(
        "CALL marcar_notificacion_leida(%s, %s)",
        (id_usuario, id_notificacion),
        _credenciales_perfil(),
    )


# Solicitudes, con el usuario de BD del perfil. Las reglas las comprueba la BD
# y, si no se cumplen, llegan como ErrorRegla

def crear_solicitud(id_usuario: int, tipo: str, prioridad: str, motivo: str,
                    id_sector: int, duracion_min: int,
                    id_dispositivo: int | None) -> int:
    """Crea una solicitud pendiente y devuelve su id."""
    fila = _consultar_uno(
        "CALL crear_solicitud(%s, %s, %s, %s, %s, %s, %s)",
        (id_usuario, tipo, prioridad, motivo, id_sector, duracion_min, id_dispositivo),
        _credenciales_perfil(),
    )
    return fila["id_solicitud"]


def mis_solicitudes(id_usuario: int) -> list[dict]:
    """Solicitudes del usuario, la más nueva primero."""
    return _consultar_todos(
        "CALL mis_solicitudes(%s)", (id_usuario,), _credenciales_perfil()
    )


def cancelar_solicitud(id_usuario: int, id_solicitud: int) -> None:
    _ejecutar(
        "CALL cancelar_solicitud(%s, %s)", (id_usuario, id_solicitud), _credenciales_perfil()
    )


def sectores(id_usuario: int) -> list[dict]:
    return _consultar_todos("CALL sectores(%s)", (id_usuario,), _credenciales_perfil())


def dispositivos_sector(id_usuario: int, id_sector: int) -> list[dict]:
    return _consultar_todos(
        "CALL dispositivos_sector(%s, %s)", (id_usuario, id_sector), _credenciales_perfil()
    )


# Aprobaciones (RF-076), con el usuario de BD del perfil

def por_aprobar(id_usuario: int) -> list[dict]:
    """Solicitudes pendientes que el usuario puede aprobar o rechazar."""
    return _consultar_todos("CALL por_aprobar(%s)", (id_usuario,), _credenciales_perfil())


def _decidir(id_usuario: int, id_solicitud: int, decision: str, comentario: str) -> None:
    _ejecutar(
        "CALL decidir_solicitud(%s, %s, %s, %s)",
        (id_usuario, id_solicitud, decision, comentario),
        _credenciales_perfil(),
    )


def aprobar_solicitud(id_usuario: int, id_solicitud: int, comentario: str = "") -> None:
    _decidir(id_usuario, id_solicitud, "aceptada", comentario)


def rechazar_solicitud(id_usuario: int, id_solicitud: int, comentario: str = "") -> None:
    _decidir(id_usuario, id_solicitud, "rechazada", comentario)


# Simulador de lecturas (RF-029), con a3i_simulador

def _credenciales_simulador() -> Credenciales:
    return config.DB_USUARIO_SIMULADOR, config.DB_PASSWORD_SIMULADOR


def variables_simulador() -> list[dict]:
    """Variables con su rango normal, para inventar las lecturas."""
    return _consultar_todos(
        "SELECT id_variable, nombre, minimo_normal, maximo_normal FROM variable",
        (),
        _credenciales_simulador(),
    )


def insertar_lectura(id_variable: int, valor: float) -> None:
    """La fecha y hora la pone MariaDB."""
    _ejecutar(
        "INSERT INTO a3i_lecturas.lectura (id_variable, valor) VALUES (%s, %s)",
        (id_variable, valor),
        _credenciales_simulador(),
    )
