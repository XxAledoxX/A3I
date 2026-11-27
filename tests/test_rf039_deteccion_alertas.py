"""RF-039: el trigger crea los avisos y las alarmas al llegar cada lectura.

Usan la BD de prueba y van en una transacción que se deshace al acabar. Las
lecturas las mete a3i_simulador y las alertas se leen con alertas_usuario.
Lo de los equipos en mantenimiento no se puede preparar desde la app: se
prueba a mano cambiando el estado del dispositivo.

    python -m unittest -v tests.test_rf039_deteccion_alertas
"""

import unittest
from unittest import mock

from app.model import repositorio
from tests.bd import PruebaConTransaccion, hay_bd


@unittest.skipUnless(hay_bd(), "MariaDB no disponible")
class PruebasDeteccion(PruebaConTransaccion):

    def setUp(self):
        super().setUp()
        self.ids = {v["nombre"]: v["id_variable"] for v in repositorio.variables_simulador()}
        self.cuentas = {login: repositorio.buscar_por_login(login)
                        for login in ("jefe_cien", "seguridad1")}

    def _leer(self, variable: str, valor: float) -> None:
        repositorio.insertar_lectura(self.ids[variable], valor)

    def _activas(self, variable: str, login: str = "jefe_cien") -> list[dict]:
        cuenta = self.cuentas[login]
        with mock.patch.object(repositorio, "_perfil_conectado", cuenta["perfil"]):
            alertas = repositorio.alertas_usuario(cuenta["id_usuario"])
        return [a for a in alertas if a["variable"] == variable and a["estado"] != "resuelta"]

    def test_valor_normal_no_crea_alerta(self):
        # Caudal 8-15: el aviso empieza a menos de 0,7 de un límite
        self._leer("caudal", 11.5)
        self._leer("caudal", 8.8)
        self.assertEqual(self._activas("caudal"), [])

    def test_aviso_cerca_del_limite(self):
        self._leer("caudal", 8.5)
        alertas = self._activas("caudal")
        self.assertEqual(len(alertas), 1)
        self.assertEqual((alertas[0]["tipo"], alertas[0]["estado"]), ("aviso", "pendiente"))
        self.assertEqual(float(alertas[0]["valor"]), 8.5)

    def test_aviso_por_arriba(self):
        self._leer("calidad_aire", 860)
        self.assertEqual(self._activas("calidad_aire")[0]["tipo"], "aviso")

    def test_alarma_fuera_de_rango(self):
        self._leer("temperatura_interior", 75)
        alertas = self._activas("temperatura_interior")
        self.assertEqual(alertas[0]["tipo"], "alarma")
        self.assertIsNone(alertas[0]["valor_alarma"])

    def test_una_sola_alerta_activa_por_variable(self):
        for valor in (5.5, 5.0, 6.0):
            self._leer("caudal", valor)
        alertas = self._activas("caudal")
        self.assertEqual(len(alertas), 1)
        self.assertEqual(float(alertas[0]["valor"]), 5.5)

    def test_aviso_que_sube_a_alarma(self):
        self._leer("caudal", 8.5)
        self._leer("caudal", 5.0)
        alertas = self._activas("caudal")
        self.assertEqual(len(alertas), 1)
        self.assertEqual(alertas[0]["tipo"], "alarma")
        self.assertEqual(float(alertas[0]["valor"]), 8.5)
        self.assertEqual(float(alertas[0]["valor_alarma"]), 5.0)

    def test_alarma_no_baja_a_aviso(self):
        self._leer("caudal", 5.0)
        self._leer("caudal", 8.5)
        self._leer("caudal", 11.5)
        self.assertEqual(self._activas("caudal")[0]["tipo"], "alarma")

    def test_fuego(self):
        self._leer("llama", 0)
        self.assertEqual(self._activas("llama", "seguridad1"), [])
        self._leer("llama", 1)
        alertas = self._activas("llama", "seguridad1")
        self.assertEqual([a["tipo"] for a in alertas], ["alarma"])


if __name__ == "__main__":
    unittest.main()
