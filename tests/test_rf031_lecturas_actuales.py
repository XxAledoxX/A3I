"""RF-031: el panel muestra las lecturas actuales desde que se inicia sesión.

PruebasRepositorio usa la BD (se salta sin .env o sin lecturas).
PruebasRefresco simula autenticar y datos_panel, así que no la necesita.

    python -m unittest -v tests.test_rf031_lecturas_actuales
"""

import os
import time
import unittest
from datetime import datetime
from decimal import Decimal
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.controller import controlador_login
from app.controller.controlador_login import ControladorLogin
from app.model import autenticacion, repositorio
from app.model.repositorio import ErrorBaseDatos
from app.model.usuario import Usuario

app = QApplication.instance() or QApplication([])

CIENTIFICO = Usuario(id_usuario=1, nombre="Lucía Herrera", login="cientifico1",
                     perfil="cientificos", nivel=2, rango="empleado")
LECTURAS = [{
    "variable": "caudal", "unidad": "L/min", "valor": Decimal("11.20"),
    "fecha_hora": datetime(2026, 11, 15, 10, 0), "minimo_normal": Decimal("8"),
    "maximo_normal": Decimal("15"), "sector": "cientifico",
}]


def _hay_bd() -> bool:
    try:
        return autenticacion.autenticar("cientifico1", "Cientifico1.Prueba") is not None
    except ErrorBaseDatos:
        return False


@unittest.skipUnless(_hay_bd(), "Sin BD o sin .env")
class PruebasRepositorio(unittest.TestCase):
    def tearDown(self):
        autenticacion.cerrar_sesion()

    def _datos(self, login: str, contrasena: str):
        usuario = autenticacion.autenticar(login, contrasena)
        return repositorio.datos_panel(usuario.id_usuario)

    def test_cientifico_ve_su_sector_y_la_llama(self):
        lecturas, actuadores, equipos = self._datos("cientifico1", "Cientifico1.Prueba")
        self.assertEqual({x["sector"] for x in lecturas}, {"cientifico", "critico"})
        self.assertIn("llama", {x["variable"] for x in lecturas})
        self.assertEqual({x["nombre"] for x in actuadores}, {"bomba_agua", "humidificador"})
        self.assertEqual(equipos, [])

    def test_seguridad_ve_la_barrera_y_la_camara(self):
        lecturas, actuadores, _ = self._datos("seguridad1", "Seguridad1.Prueba")
        self.assertEqual({x["variable"] for x in lecturas}, {"llama"})
        self.assertEqual({x["nombre"] for x in actuadores}, {"barrera", "camara"})

    def test_tech_ve_el_estado_de_sus_equipos(self):
        _, _, equipos = self._datos("tech1", "Tech1.Prueba")
        self.assertEqual({x["nombre"] for x in equipos}, {"barrera", "camara"})

    def test_sin_sesion_no_hay_datos(self):
        usuario = autenticacion.autenticar("cientifico1", "Cientifico1.Prueba")
        autenticacion.cerrar_sesion()
        with self.assertRaises(ErrorBaseDatos):
            repositorio.datos_panel(usuario.id_usuario)


def _esperar(condicion, segundos: float = 2) -> bool:
    """Procesa eventos de Qt hasta que se cumpla la condición."""
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        app.processEvents()
        if condicion():
            return True
        time.sleep(0.01)
    return condicion()


class PruebasRefresco(unittest.TestCase):
    def setUp(self):
        self.datos = mock.patch.object(controlador_login.repositorio, "datos_panel",
                                       return_value=(LECTURAS, [], []))
        self.datos_panel = self.datos.start()
        self.controlador = ControladorLogin()
        with mock.patch.object(controlador_login.autenticacion, "autenticar",
                               return_value=CIENTIFICO):
            self.controlador.iniciar_sesion("cientifico1", "Cientifico1.Prueba")
        self.ventana = self.controlador.ventana_principal

    def tearDown(self):
        if self.controlador.ventana_principal is not None:
            self.controlador.cerrar_sesion()
        self.datos.stop()
        self.controlador.ventana_login.close()
        self.controlador.ventana_login.deleteLater()
        app.processEvents()

    def test_al_iniciar_sesion_se_muestran_los_datos(self):
        self.assertTrue(_esperar(lambda: "caudal" in self.ventana.panel.tarjetas))
        self.datos_panel.assert_called_with(CIENTIFICO.id_usuario)

    def test_sin_conexion_y_vuelta(self):
        self.assertTrue(_esperar(lambda: "caudal" in self.ventana.panel.tarjetas))
        panel = self.controlador.controlador_panel

        self.datos_panel.side_effect = ErrorBaseDatos("sin conexión")
        panel.refrescar()
        self.assertTrue(_esperar(lambda: self.ventana.aviso_conexion.isVisibleTo(self.ventana)))

        self.datos_panel.side_effect = None
        _esperar(lambda: not panel.ocupado)
        panel.refrescar()
        self.assertTrue(_esperar(lambda: not self.ventana.aviso_conexion.isVisibleTo(self.ventana)))

    def test_cerrar_sesion_para_el_refresco(self):
        hilo = self.controlador.controlador_panel.hilo
        self.controlador.cerrar_sesion()
        self.assertIsNone(self.controlador.controlador_panel)
        self.assertFalse(hilo.isRunning())


if __name__ == "__main__":
    unittest.main()
