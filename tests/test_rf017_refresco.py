"""RF-017: pruebas del refresco del panel en segundo plano.

No usan BD: el controlador recibe una función de datos falsa. El refresco
se pone a 0,05 s para que las pruebas vayan rápido. Van con Qt sin
pantalla (offscreen).

    python -m unittest -v tests.test_rf017_refresco
"""

import os
import threading
import time
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app import config
from app.controller.controlador_panel import ControladorPanel
from app.model.repositorio import ErrorBaseDatos

app = QApplication.instance() or QApplication([])

LECTURAS = [{"variable": "caudal", "valor": 11}]
ACTUADORES = [{"nombre": "barrera", "posicion": 0}]


def esperar(segundos: float) -> None:
    """Deja que Qt procese señales y temporizadores durante un rato."""
    fin = time.monotonic() + segundos
    while time.monotonic() < fin:
        app.processEvents()
        time.sleep(0.005)


class PanelFalso:
    """Apunta lo que le pasa el controlador."""

    def __init__(self) -> None:
        self.lecturas = []
        self.actuadores = []

    def mostrar_lecturas(self, lecturas: list[dict], hora: str = "") -> None:
        self.lecturas.append(lecturas)

    def mostrar_actuadores(self, actuadores: list[dict]) -> None:
        self.actuadores.append(actuadores)


class PanelSinActuadores:
    def __init__(self) -> None:
        self.lecturas = []

    def mostrar_lecturas(self, lecturas: list[dict], hora: str = "") -> None:
        self.lecturas.append(lecturas)


@mock.patch.object(config, "SEGUNDOS_REFRESCO", 0.05)
class PruebasRefresco(unittest.TestCase):
    def setUp(self):
        self.llamadas = 0
        self.hilos = set()
        self.controladores = []

    def tearDown(self):
        for controlador in self.controladores:
            controlador.parar()

    def datos(self):
        self.llamadas += 1
        self.hilos.add(threading.get_ident())
        return LECTURAS, ACTUADORES

    def crear(self, panel, obtener_datos=None) -> ControladorPanel:
        controlador = ControladorPanel(panel, obtener_datos or self.datos)
        self.controladores.append(controlador)
        return controlador

    def test_primera_carga_inmediata(self):
        panel = PanelFalso()
        self.crear(panel).iniciar()
        esperar(0.02)
        self.assertEqual(panel.lecturas, [LECTURAS])
        self.assertEqual(panel.actuadores, [ACTUADORES])

    def test_refresca_periodicamente(self):
        panel = PanelFalso()
        self.crear(panel).iniciar()
        esperar(0.3)
        self.assertGreaterEqual(len(panel.lecturas), 3)

    def test_consulta_en_otro_hilo(self):
        self.crear(PanelFalso()).iniciar()
        esperar(0.1)
        self.assertTrue(self.hilos)
        self.assertNotIn(threading.get_ident(), self.hilos)

    def test_panel_sin_actuadores(self):
        panel = PanelSinActuadores()
        self.crear(panel).iniciar()
        esperar(0.02)
        self.assertEqual(panel.lecturas, [LECTURAS])

    def test_no_se_solapan_consultas(self):
        en_curso = 0
        maximo = 0

        def lenta():
            nonlocal en_curso, maximo
            en_curso += 1
            maximo = max(maximo, en_curso)
            time.sleep(0.2)
            en_curso -= 1
            return LECTURAS, ACTUADORES

        panel = PanelFalso()
        self.crear(panel, lenta).iniciar()
        esperar(0.5)
        self.assertEqual(maximo, 1)
        # En 0,5 s caben como mucho 3 consultas de 0,2 s
        self.assertLessEqual(len(panel.lecturas), 3)

    def test_error_avisa_y_no_pinta(self):
        def falla():
            raise ErrorBaseDatos("Error al consultar la base de datos")

        panel = PanelFalso()
        controlador = self.crear(panel, falla)
        errores = []
        controlador.error_conexion.connect(lambda: errores.append(1))
        controlador.iniciar()
        esperar(0.2)
        self.assertGreaterEqual(len(errores), 2)
        self.assertEqual(panel.lecturas, [])

    def test_sigue_tras_un_error(self):
        respuestas = [ErrorBaseDatos("caída"), None]

        def falla_una_vez():
            if respuestas and respuestas.pop(0):
                raise ErrorBaseDatos("caída")
            return LECTURAS, ACTUADORES

        panel = PanelFalso()
        self.crear(panel, falla_una_vez).iniciar()
        esperar(0.2)
        self.assertTrue(panel.lecturas)

    def test_parar(self):
        panel = PanelFalso()
        controlador = self.crear(panel)
        controlador.iniciar()
        esperar(0.15)
        controlador.parar()
        llamadas = self.llamadas
        esperar(0.2)
        self.assertEqual(self.llamadas, llamadas)
        self.assertFalse(controlador.hilo.isRunning())


if __name__ == "__main__":
    unittest.main()
