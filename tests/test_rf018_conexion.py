"""RF-018: pruebas del aviso de pérdida de conexión.

No usan BD: el controlador recibe una función de datos que falla cuando
se le dice. El refresco se pone a 0,05 s. Van con Qt sin pantalla.

    python -m unittest -v tests.test_rf018_conexion
"""

import os
import time
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app import config
from app.controller.controlador_panel import ControladorPanel
from app.model.repositorio import ErrorBaseDatos
from app.view import ventana_principal
from app.view.ventana_principal import VentanaPrincipal

app = QApplication.instance() or QApplication([])

LECTURAS = [{"variable": "caudal", "valor": 11}]


def esperar(segundos: float) -> None:
    fin = time.monotonic() + segundos
    while time.monotonic() < fin:
        app.processEvents()
        time.sleep(0.005)


class PanelFalso:
    def __init__(self) -> None:
        self.lecturas = []

    def mostrar_lecturas(self, lecturas: list[dict], hora: str = "") -> None:
        self.lecturas.append(lecturas)


class PruebasAviso(unittest.TestCase):
    def setUp(self):
        self.ventana = VentanaPrincipal("cientificos", "empleado")

    def tearDown(self):
        self.ventana.close()
        self.ventana.deleteLater()

    def test_empieza_oculto(self):
        self.assertTrue(self.ventana.aviso_conexion.isHidden())

    def test_mostrar_y_ocultar(self):
        self.ventana.mostrar_sin_conexion(True)
        self.assertFalse(self.ventana.aviso_conexion.isHidden())
        self.ventana.mostrar_sin_conexion(False)
        self.assertTrue(self.ventana.aviso_conexion.isHidden())

    def test_texto_y_estilo_de_alarma(self):
        aviso = self.ventana.aviso_conexion
        self.assertEqual(aviso.text(), ventana_principal.MENSAJE_SIN_CONEXION)
        self.assertIn("Sin conexión", aviso.text())
        self.assertEqual(aviso.property("estado"), "alarma")

    def test_en_todos_los_perfiles(self):
        for perfil in ("cientificos", "seguridad", "tech"):
            with self.subTest(perfil=perfil):
                ventana = VentanaPrincipal(perfil, "empleado")
                ventana.mostrar_sin_conexion(True)
                self.assertFalse(ventana.aviso_conexion.isHidden())
                ventana.deleteLater()


class PruebasConControlador(unittest.TestCase):
    """El aviso conectado al controlador como lo hará RF-031."""

    def setUp(self):
        # El intervalo se lee al crear el controlador
        parche = mock.patch.object(config, "SEGUNDOS_REFRESCO", 0.05)
        parche.start()
        self.addCleanup(parche.stop)
        self.falla = False
        self.ventana = VentanaPrincipal("cientificos", "empleado")
        self.panel = PanelFalso()
        self.controlador = ControladorPanel(self.panel, self.datos)
        self.controlador.error_conexion.connect(
            lambda: self.ventana.mostrar_sin_conexion(True))
        self.controlador.datos_recibidos.connect(
            lambda: self.ventana.mostrar_sin_conexion(False))

    def tearDown(self):
        self.controlador.parar()
        self.ventana.deleteLater()

    def datos(self):
        if self.falla:
            raise ErrorBaseDatos("Error al consultar la base de datos")
        return LECTURAS, [], []

    def test_datos_recibidos_en_cada_refresco(self):
        recibidos = []
        self.controlador.datos_recibidos.connect(lambda: recibidos.append(1))
        self.controlador.iniciar()
        esperar(0.3)
        self.assertGreaterEqual(len(recibidos), 3)

    def test_sin_datos_recibidos_si_falla(self):
        self.falla = True
        recibidos = []
        self.controlador.datos_recibidos.connect(lambda: recibidos.append(1))
        self.controlador.iniciar()
        esperar(0.2)
        self.assertEqual(recibidos, [])

    def test_aviso_al_perder_la_conexion(self):
        self.controlador.iniciar()
        esperar(0.1)
        self.assertTrue(self.ventana.aviso_conexion.isHidden())
        self.falla = True
        esperar(0.2)
        self.assertFalse(self.ventana.aviso_conexion.isHidden())

    def test_el_panel_se_queda_con_los_ultimos_datos(self):
        self.controlador.iniciar()
        esperar(0.1)
        self.falla = True
        # Deja llegar una consulta que ya estuviera en marcha
        esperar(0.1)
        pintados = len(self.panel.lecturas)
        self.assertGreater(pintados, 0)
        esperar(0.2)
        self.assertEqual(len(self.panel.lecturas), pintados)

    def test_el_aviso_se_quita_al_volver_la_conexion(self):
        self.falla = True
        self.controlador.iniciar()
        esperar(0.2)
        self.assertFalse(self.ventana.aviso_conexion.isHidden())
        # El reintento es automático: el temporizador sigue pidiendo
        self.falla = False
        esperar(0.2)
        self.assertTrue(self.ventana.aviso_conexion.isHidden())


if __name__ == "__main__":
    unittest.main()
