"""RF-030: la BD rechaza las lecturas físicamente imposibles.

Inserta con a3i_simulador (RF-029), que es quien mete las lecturas, y se
salta si no está su contraseña (DB_SIMULADOR_PASSWORD) en el .env. Cada
inserción va en una transacción que se deshace, así que la BD no cambia.

    python -m unittest -v tests.test_rf030_validacion_lecturas
"""

import os
import unittest

import pymysql

from app import config  # noqa: F401 (carga el .env)
from app.model import repositorio

USUARIO_SIMULADOR = "a3i_simulador"
CONTRASENA_SIMULADOR = os.getenv("DB_SIMULADOR_PASSWORD", "")

# Error de MariaDB cuando un trigger hace SIGNAL
ERROR_SIGNAL = 1644

# Valores en el límite (se aceptan) y justo fuera (se rechazan)
ACEPTADOS = {
    "humedad_interior": (0, 100, 45),
    "humedad_ambiente": (0, 100, 55),
    "temperatura_interior": (-40, 150, 55),
    "temperatura_ambiente": (-40, 150, 22),
    "calidad_aire": (0, 10000, 600),
    "caudal": (0, 100, 11),
    "llama": (0, 1),
}
RECHAZADOS = {
    "humedad_interior": (-0.01, 100.01),
    "humedad_ambiente": (-1, 150),
    "temperatura_interior": (-40.01, 150.01),
    "temperatura_ambiente": (-273, 1000),
    "calidad_aire": (-1, 10000.01),
    "caudal": (-0.01, 100.01),
    "llama": (-1, 0.5, 2),
}
# Fuera del rango normal pero posibles: son alertas, no errores
FUERA_DE_RANGO_NORMAL = {
    "temperatura_interior": 95,
    "humedad_ambiente": 85,
    "calidad_aire": 2500,
    "caudal": 2,
}


def _conectar_simulador() -> pymysql.connections.Connection:
    conexion = repositorio._conectar(USUARIO_SIMULADOR, CONTRASENA_SIMULADOR)
    conexion.autocommit(False)
    return conexion


def _hay_simulador() -> bool:
    if not CONTRASENA_SIMULADOR:
        return False
    try:
        _conectar_simulador().close()
        return True
    except pymysql.Error:
        return False


@unittest.skipUnless(_hay_simulador(), "Falta a3i_simulador (RF-029) o MariaDB")
class PruebasValidacionLecturas(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with _conectar_simulador() as conexion, conexion.cursor() as cursor:
            cursor.execute("SELECT id_variable, nombre FROM a3i.variable")
            cls.ids = {fila["nombre"]: fila["id_variable"] for fila in cursor.fetchall()}

    def _insertar(self, variable: str, valor: float) -> None:
        """Inserta la lectura y la deshace. Lanza pymysql.Error si se rechaza."""
        with _conectar_simulador() as conexion, conexion.cursor() as cursor:
            try:
                cursor.execute(
                    "INSERT INTO a3i_lecturas.lectura (id_variable, valor) VALUES (%s, %s)",
                    (self.ids[variable], valor),
                )
            finally:
                conexion.rollback()

    def test_estan_todas_las_variables(self):
        self.assertEqual(set(self.ids), set(ACEPTADOS))

    def test_acepta_valores_posibles(self):
        for variable, valores in ACEPTADOS.items():
            for valor in valores:
                with self.subTest(variable=variable, valor=valor):
                    self._insertar(variable, valor)

    def test_acepta_valores_fuera_del_rango_normal(self):
        for variable, valor in FUERA_DE_RANGO_NORMAL.items():
            with self.subTest(variable=variable, valor=valor):
                self._insertar(variable, valor)

    def test_rechaza_valores_imposibles(self):
        for variable, valores in RECHAZADOS.items():
            for valor in valores:
                with self.subTest(variable=variable, valor=valor):
                    with self.assertRaises(pymysql.Error) as error:
                        self._insertar(variable, valor)
                    self.assertEqual(error.exception.args[0], ERROR_SIGNAL)
                    self.assertIn(variable, error.exception.args[1])


if __name__ == "__main__":
    unittest.main()
