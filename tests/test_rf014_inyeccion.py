"""RF-014: las consultas parametrizadas no dejan hacer inyección SQL.

Las pruebas con BD usan la de prueba (./db/reset_db.sh) y se saltan si
MariaDB no está disponible.

    python -m unittest -v
"""

import unittest

import pymysql

from app.model import repositorio

# Entradas típicas de inyección SQL
INYECCIONES = (
    "' OR '1'='1",
    "' OR 1=1 -- ",
    "cientifico1' -- ",
    "x'; UPDATE usuario SET estado = 'bloqueado'; -- ",
)


def _hay_bd() -> bool:
    try:
        repositorio._conectar().close()
        return True
    except pymysql.Error:
        return False


def _estado_cuentas() -> list[dict]:
    """Intentos fallidos y estado de todas las cuentas."""
    with repositorio._conectar() as conexion, conexion.cursor() as cursor:
        cursor.execute(
            "SELECT login, intentos_fallidos, estado FROM usuario ORDER BY login"
        )
        return cursor.fetchall()


class PruebasParametros(unittest.TestCase):
    """No necesitan BD: el error salta antes de conectar."""

    def test_consultar_sin_tupla_da_error(self):
        with self.assertRaises(TypeError):
            repositorio._consultar_uno("SELECT %s", "tech1")

    def test_ejecutar_sin_tupla_da_error(self):
        with self.assertRaises(TypeError):
            repositorio._ejecutar("SELECT %s", ["tech1"])


@unittest.skipUnless(_hay_bd(), "MariaDB no disponible")
class PruebasInyeccion(unittest.TestCase):

    def test_login_normal_funciona(self):
        # Control: si esto falla, las demás pruebas no demuestran nada
        fila = repositorio.buscar_por_login("cientifico1")
        self.assertIsNotNone(fila)
        self.assertEqual(fila["login"], "cientifico1")

    def test_inyeccion_en_busqueda_no_devuelve_nada(self):
        for entrada in INYECCIONES:
            with self.subTest(entrada=entrada):
                self.assertIsNone(repositorio.buscar_por_login(entrada))

    def test_inyeccion_en_busqueda_no_cambia_cuentas(self):
        antes = _estado_cuentas()
        for entrada in INYECCIONES:
            repositorio.buscar_por_login(entrada)
        self.assertEqual(_estado_cuentas(), antes)

    def test_inyeccion_en_registrar_fallo_no_cambia_cuentas(self):
        # Con el SQL concatenado sumaría un fallo a todas las cuentas activas
        antes = _estado_cuentas()
        for entrada in INYECCIONES:
            repositorio.registrar_fallo(entrada, 5)
        self.assertEqual(_estado_cuentas(), antes)

    def test_comilla_en_login_no_da_error(self):
        # Se escapa, no se rompe la consulta
        self.assertIsNone(repositorio.buscar_por_login("o'brien"))


if __name__ == "__main__":
    unittest.main()
