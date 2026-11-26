"""Pruebas que cambian la BD: cada una va en una transacción que se deshace al acabar."""

import unittest
from unittest import mock

import pymysql

from app.model import repositorio

# Cuentas de db/003_datos_prueba.sql
LOGINS_PRUEBA = (
    "cientifico1", "seguridad1", "tech1", "cientifico2", "jefesector_cien",
    "subjefe_cien", "jefe_cien", "jefesector_seg", "subjefe_seg", "jefe_seg",
    "tech2", "subjefe_tech", "jefe_tech",
)

# Empiezan así en db/003_datos_prueba.sql
CUENTA_BLOQUEADA = ("tech_bloqueado", "Tech_bloqueado.Prueba")
CUENTA_DESACTIVADA = ("tech_desactivado", "Tech_desactivado.Prueba")


def hay_bd() -> bool:
    try:
        repositorio._conectar(*repositorio._credenciales_login()).close()
        return True
    except (pymysql.Error, repositorio.ErrorBaseDatos):
        return False


def estado_cuentas() -> dict[str, tuple]:
    """Intentos fallidos y estado de cada cuenta de prueba."""
    cuentas = {}
    for login in LOGINS_PRUEBA:
        fila = repositorio.buscar_por_login(login)
        cuentas[login] = (fila["intentos_fallidos"], fila["estado"])
    return cuentas


class _SinCerrar:
    """Deja abierta la conexión al salir del with, para seguir en la transacción."""

    def __init__(self, conexion) -> None:
        self.conexion = conexion

    def __enter__(self):
        return self.conexion

    def __exit__(self, *_) -> bool:
        return False

    def close(self) -> None:
        pass


class PruebaConTransaccion(unittest.TestCase):
    """Una conexión por usuario de BD durante la prueba y ROLLBACK al final."""

    def setUp(self):
        self.conexiones = {}
        conectar = repositorio._conectar

        def conectar_sin_guardar(usuario: str, contrasena: str) -> _SinCerrar:
            if usuario not in self.conexiones:
                conexion = conectar(usuario, contrasena)
                conexion.autocommit(False)
                self.conexiones[usuario] = conexion
            return _SinCerrar(self.conexiones[usuario])

        parche = mock.patch.object(repositorio, "_conectar", conectar_sin_guardar)
        parche.start()
        # Se ejecutan al revés: primero se quita el parche y luego se deshace todo
        self.addCleanup(self._deshacer)
        self.addCleanup(parche.stop)

    def _deshacer(self) -> None:
        for conexion in self.conexiones.values():
            conexion.rollback()
            conexion.close()
