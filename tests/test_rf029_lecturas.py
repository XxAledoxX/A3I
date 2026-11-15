"""RF-029: histórico de lecturas y simulador.

Las de generar_lecturas no usan BD. Las demás se saltan si no hay
a3i_simulador (falta DB_SIMULADOR_PASSWORD en el .env o el reset).

    python -m unittest -v tests.test_rf029_lecturas
"""

import unittest
from decimal import Decimal

import pymysql

from app import config
from app.model import repositorio
from app.model.repositorio import ErrorBaseDatos
from simulador import generar_lecturas

VARIABLES = [
    {"id_variable": 1, "nombre": "temperatura_interior", "minimo_normal": Decimal("40"),
     "maximo_normal": Decimal("70")},
    {"id_variable": 5, "nombre": "calidad_aire", "minimo_normal": Decimal("400"),
     "maximo_normal": Decimal("900")},
    {"id_variable": 6, "nombre": "caudal", "minimo_normal": Decimal("8"),
     "maximo_normal": Decimal("15")},
    {"id_variable": 7, "nombre": "llama", "minimo_normal": None, "maximo_normal": None},
]
RANGOS = {v["nombre"]: (v["minimo_normal"], v["maximo_normal"]) for v in VARIABLES}


def _fuera(nombre: str, valor: float) -> bool:
    minimo, maximo = RANGOS[nombre]
    return not minimo <= valor <= maximo


class PruebasGenerarLecturas(unittest.TestCase):
    def test_una_lectura_por_variable(self):
        lecturas = generar_lecturas(VARIABLES)
        self.assertEqual([x[1] for x in lecturas], [1, 5, 6, 7])

    def test_valores_normales_dentro_del_rango(self):
        for _ in range(200):
            for nombre, _, valor in generar_lecturas(VARIABLES):
                if nombre != "llama":
                    self.assertFalse(_fuera(nombre, valor), (nombre, valor))

    def test_fuera_de_rango_solo_una_variable(self):
        for _ in range(200):
            lecturas = generar_lecturas(VARIABLES, fuera_de_rango=True)
            fuera = [n for n, _, v in lecturas if n != "llama" and _fuera(n, v)]
            self.assertEqual(len(fuera), 1)

    def test_llama(self):
        llama = {n: v for n, _, v in generar_lecturas(VARIABLES)}["llama"]
        self.assertEqual(llama, 0)
        llama = {n: v for n, _, v in generar_lecturas(VARIABLES, fuego=True)}["llama"]
        self.assertEqual(llama, 1)


def _hay_simulador() -> bool:
    if not config.DB_PASSWORD_SIMULADOR:
        return False
    try:
        repositorio.variables_simulador()
        return True
    except ErrorBaseDatos:
        return False


def _ultimas_lecturas(login: str) -> dict[str, dict]:
    """Últimas lecturas que ve el jefe de Científicos, que ve las siete."""
    id_usuario = repositorio.buscar_por_login(login)["id_usuario"]
    filas = repositorio._consultar_todos(
        "CALL ultimas_lecturas(%s)", (id_usuario,), config.USUARIOS_PERFIL["cientificos"]
    )
    return {fila["variable"]: fila for fila in filas}


@unittest.skipUnless(_hay_simulador(), "Falta a3i_simulador (DB_SIMULADOR_PASSWORD) o MariaDB")
class PruebasBD(unittest.TestCase):
    def test_hay_lecturas_de_las_siete_variables(self):
        self.assertEqual(len(_ultimas_lecturas("jefe_cien")), 7)

    def test_el_simulador_mete_una_lectura(self):
        variable = next(v for v in repositorio.variables_simulador()
                        if v["nombre"] == "caudal")
        repositorio.insertar_lectura(variable["id_variable"], 11.11)
        fila = _ultimas_lecturas("jefe_cien")["caudal"]
        self.assertEqual(fila["valor"], Decimal("11.11"))

    def test_el_simulador_no_lee_ni_borra_lecturas(self):
        conexion = repositorio._conectar(config.DB_USUARIO_SIMULADOR,
                                         config.DB_PASSWORD_SIMULADOR)
        with conexion, conexion.cursor() as cursor:
            for sql in ("SELECT * FROM a3i_lecturas.lectura LIMIT 1",
                        "DELETE FROM a3i_lecturas.lectura WHERE id_lectura = 1",
                        "SELECT * FROM a3i.usuario LIMIT 1"):
                with self.subTest(sql=sql), self.assertRaises(pymysql.err.OperationalError):
                    cursor.execute(sql)


if __name__ == "__main__":
    unittest.main()
