"""RF-033: histórico de una variable entre dos fechas.

Usa la BD con el histórico de db/006 (se salta sin .env o sin lecturas).
Las fechas cubren 60 días porque el histórico acaba en el último reset.

    python -m unittest -v tests.test_rf033_historico
"""

import unittest
from datetime import datetime, timedelta

import pymysql

from app import config
from app.model import autenticacion, repositorio
from app.model.repositorio import ErrorBaseDatos
from tests.test_rf020_permisos import ESPERADO

TODAS = {"temperatura_interior", "humedad_interior", "temperatura_ambiente",
         "humedad_ambiente", "calidad_aire", "caudal", "llama"}


def _hay_bd() -> bool:
    try:
        usuario = autenticacion.autenticar("cientifico1", "Cientifico1.Prueba")
        if usuario is None:
            return False
        hay = bool(repositorio.ultimas_lecturas(usuario.id_usuario))
        autenticacion.cerrar_sesion()
        return hay
    except ErrorBaseDatos:
        return False


@unittest.skipUnless(_hay_bd(), "Sin BD, sin .env o sin lecturas")
class PruebasHistorico(unittest.TestCase):
    def setUp(self):
        self.usuario = autenticacion.autenticar("cientifico1", "Cientifico1.Prueba")
        self.hasta = datetime.now()
        self.desde = self.hasta - timedelta(days=60)

    def tearDown(self):
        autenticacion.cerrar_sesion()

    def _historico(self, variable: str, **opciones) -> list[dict]:
        return repositorio.historico_lecturas(
            self.usuario.id_usuario, variable,
            opciones.get("desde", self.desde), opciones.get("hasta", self.hasta),
            opciones.get("puntos", config.PUNTOS_HISTORICO),
        )

    def test_columnas(self):
        fila = self._historico("caudal")[0]
        self.assertEqual(set(fila), {"fecha_hora", "valor_medio", "valor_minimo",
                                     "valor_maximo", "lecturas"})

    def test_no_pasa_del_maximo_de_puntos(self):
        filas = self._historico("caudal", puntos=100)
        self.assertLessEqual(len(filas), 100)
        # Los 30 días del histórico, una lectura cada 15 min, más las del simulador
        self.assertGreaterEqual(sum(f["lecturas"] for f in filas), 2879)

    def test_ordenado_y_dentro_de_las_fechas(self):
        fechas = [f["fecha_hora"] for f in self._historico("caudal")]
        self.assertEqual(fechas, sorted(fechas))
        self.assertGreaterEqual(fechas[0], self.desde.replace(microsecond=0))
        self.assertLessEqual(fechas[-1], self.hasta)

    def test_minimo_medio_y_maximo(self):
        for fila in self._historico("calidad_aire"):
            self.assertLessEqual(fila["valor_minimo"], fila["valor_medio"])
            self.assertLessEqual(fila["valor_medio"], fila["valor_maximo"])

    def test_el_pico_no_se_pierde_en_la_media(self):
        # El histórico tiene fuegos hace 12 y 4 días
        filas = self._historico("llama", puntos=10)
        self.assertEqual(max(f["valor_maximo"] for f in filas), 1)

    def test_fechas_al_reves(self):
        self.assertEqual(self._historico("caudal", desde=self.hasta, hasta=self.desde), [])

    def test_variable_que_no_existe(self):
        self.assertEqual(self._historico("radiacion"), [])

    def test_sin_sesion(self):
        autenticacion.cerrar_sesion()
        with self.assertRaises(ErrorBaseDatos):
            self._historico("caudal")


def _hay_usuarios_bd() -> bool:
    try:
        for usuario, contrasena in config.USUARIOS_PERFIL.values():
            repositorio._conectar(usuario, contrasena).close()
        return _hay_bd()
    except (pymysql.Error, ErrorBaseDatos):
        return False


@unittest.skipUnless(_hay_usuarios_bd(), "Sin BD, sin .env o sin lecturas")
class PruebasPermisos(unittest.TestCase):
    """Cada usuario solo ve el histórico de las variables de ultimas_lecturas."""

    def _filas(self, login: str, variable: str, perfil: str) -> list[dict]:
        id_usuario = repositorio.buscar_por_login(login)["id_usuario"]
        hasta = datetime.now()
        return repositorio._consultar_todos(
            "CALL historico_lecturas(%s, %s, %s, %s, %s)",
            (id_usuario, variable, hasta - timedelta(days=60), hasta, 10),
            config.USUARIOS_PERFIL[perfil],
        )

    def test_regla_de_acceso(self):
        for login, (perfil, variables, _, _) in ESPERADO.items():
            for variable in TODAS:
                with self.subTest(login=login, variable=variable):
                    filas = self._filas(login, variable, perfil)
                    self.assertEqual(bool(filas), variable in variables)

    def test_con_el_usuario_de_bd_de_otro_perfil(self):
        self.assertEqual(self._filas("cientifico1", "caudal", "tech"), [])


if __name__ == "__main__":
    unittest.main()
