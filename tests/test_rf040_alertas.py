"""RF-040: listado de las alertas que ve cada usuario.

Usan la BD de prueba con las alertas del histórico (db/011_alertas.sql) y van
en una transacción que se deshace al acabar.

    python -m unittest -v tests.test_rf040_alertas
"""

import unittest
from unittest import mock

from app.model import repositorio
from tests.bd import LOGINS_PRUEBA, PruebaConTransaccion, hay_bd
from tests.test_rf020_permisos import ESPERADO

# Las resueltas del histórico tienen menos de 60 días
HORAS_TODAS = 24 * 60
COLUMNAS = {
    "id_alerta", "variable", "unidad", "sector", "tipo", "estado", "valor", "fecha_hora",
    "valor_alarma", "fecha_alarma", "minimo_normal", "maximo_normal", "encargado",
    "fecha_asignacion", "fecha_terminada", "motivo_devolucion", "revisor", "fecha_resolucion",
}
ORDEN_ESTADOS = ["pendiente", "en_curso", "por_revisar", "resuelta"]


@unittest.skipUnless(hay_bd(), "MariaDB no disponible")
class PruebasListado(PruebaConTransaccion):

    def setUp(self):
        super().setUp()
        self.cuentas = {login: repositorio.buscar_por_login(login) for login in LOGINS_PRUEBA}
        self.ids = {v["nombre"]: v["id_variable"] for v in repositorio.variables_simulador()}

    def _alertas(self, login: str, horas: int = HORAS_TODAS,
                 perfil: str | None = None) -> list[dict]:
        cuenta = self.cuentas[login]
        with mock.patch.object(repositorio, "_perfil_conectado", perfil or cuenta["perfil"]):
            return repositorio.alertas_usuario(cuenta["id_usuario"], horas)

    def test_columnas(self):
        self.assertEqual(set(self._alertas("jefe_cien")[0]), COLUMNAS)

    def test_alertas_del_historico(self):
        alertas = self._alertas("jefe_cien")
        self.assertTrue(alertas)
        for alerta in alertas:
            with self.subTest(id_alerta=alerta["id_alerta"]):
                self.assertEqual(alerta["estado"], "resuelta")
                self.assertIsNotNone(alerta["fecha_resolucion"])
        variables = {a["variable"] for a in alertas if a["tipo"] == "alarma"}
        self.assertTrue({"llama", "temperatura_interior", "caudal"} <= variables)

    def test_quien_las_resuelve(self):
        revisores = {(a["sector"], a["variable"] == "llama"): a["revisor"]
                     for a in self._alertas("jefe_cien")}
        nombre = {login: cuenta["nombre"] for login, cuenta in self.cuentas.items()}
        self.assertEqual(revisores[("critico", True)], nombre["jefe_seg"])
        self.assertEqual(revisores[("critico", False)], nombre["jefe_cien"])
        self.assertEqual(revisores[("cientifico", False)], nombre["jefesector_cien"])

    def test_cada_uno_ve_las_de_sus_variables(self):
        for login, (perfil, variables, _, _) in ESPERADO.items():
            with self.subTest(login=login):
                vistas = {a["variable"] for a in self._alertas(login)}
                if perfil == "tech":
                    self.assertEqual(vistas, set())
                else:
                    self.assertTrue(vistas <= variables)
                    self.assertIn("llama", vistas)

    def test_con_el_usuario_de_bd_de_otro_perfil(self):
        self.assertEqual(self._alertas("cientifico1", perfil="seguridad"), [])

    def test_resueltas_solo_de_las_ultimas_horas(self):
        self.assertEqual(self._alertas("jefe_cien", horas=24), [])

    def test_activas_salen_siempre_y_primero_las_alarmas(self):
        repositorio.insertar_lectura(self.ids["calidad_aire"], 860)
        repositorio.insertar_lectura(self.ids["caudal"], 5.0)
        alertas = self._alertas("jefe_cien", horas=24)
        self.assertEqual([(a["variable"], a["tipo"]) for a in alertas],
                         [("caudal", "alarma"), ("calidad_aire", "aviso")])

    def test_orden_por_estado(self):
        repositorio.insertar_lectura(self.ids["caudal"], 5.0)
        estados = [a["estado"] for a in self._alertas("jefe_cien")]
        self.assertEqual(estados, sorted(estados, key=ORDEN_ESTADOS.index))


if __name__ == "__main__":
    unittest.main()
