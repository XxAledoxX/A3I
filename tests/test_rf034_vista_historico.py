"""RF-034: vista del histórico con tabla y gráfica.

No usan BD: la vista recibe filas inventadas con las columnas de
historico_lecturas y el controlador se prueba con el repositorio simulado.

    python -m unittest -v tests.test_rf034_vista_historico
"""

import os
import unittest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.controller import controlador_historico
from app.controller.controlador_historico import ControladorHistorico
from app.model.repositorio import ErrorBaseDatos
from app.view.vista_historico import MENSAJE_FECHAS, MENSAJE_VACIO, VistaHistorico
from app.view.ventana_principal import VentanaPrincipal

app = QApplication.instance() or QApplication([])

VARIABLES = [
    {"variable": "caudal", "unidad": "L/min",
     "minimo_normal": Decimal(8), "maximo_normal": Decimal(15)},
    {"variable": "llama", "unidad": "", "minimo_normal": None, "maximo_normal": None},
]
INICIO = datetime(2026, 11, 20, 10, 0)


def filas(n: int = 3, maximo: str = "12.5") -> list[dict]:
    return [{
        "fecha_hora": INICIO + timedelta(hours=i), "valor_medio": Decimal("11.20"),
        "valor_minimo": Decimal("10.00"), "valor_maximo": Decimal(maximo), "lecturas": 12,
    } for i in range(n)]


class PruebasVista(unittest.TestCase):
    def setUp(self):
        self.vista = VistaHistorico("Histórico")
        self.pedidas = []
        self.vista.consulta_pedida.connect(lambda *datos: self.pedidas.append(datos))

    def _consultar(self, variable: str, resultado: list[dict]):
        self.vista.selector_variable.setCurrentIndex(
            self.vista.selector_variable.findData(variable))
        self.vista.pedir_consulta()
        self.vista.mostrar_historico(resultado)

    def test_desplegable_con_las_variables(self):
        self.vista.poner_variables(VARIABLES)
        textos = [self.vista.selector_variable.itemText(i)
                  for i in range(self.vista.selector_variable.count())]
        self.assertEqual(textos, ["Caudal de agua", "Detector de llama"])

    def test_la_primera_vez_consulta_las_ultimas_24_h(self):
        self.vista.poner_variables(VARIABLES)
        self.assertEqual(len(self.pedidas), 1)
        variable, desde, hasta = self.pedidas[0]
        self.assertEqual(variable, "caudal")
        self.assertEqual(hasta - desde, timedelta(days=1))

    def test_no_repite_la_consulta_si_las_variables_no_cambian(self):
        self.vista.poner_variables(VARIABLES)
        self.vista.poner_variables(VARIABLES)
        self.assertEqual(len(self.pedidas), 1)

    def test_periodos(self):
        self.vista.poner_variables(VARIABLES)
        self.vista.elegir_periodo(timedelta(days=30))
        _, desde, hasta = self.pedidas[-1]
        self.assertEqual(hasta - desde, timedelta(days=30))

    def test_fechas_al_reves(self):
        self.vista.poner_variables(VARIABLES)
        self.vista.desde.setDateTime(self.vista.hasta.dateTime().addDays(1))
        self.vista.pedir_consulta()
        self.assertEqual(len(self.pedidas), 1)
        self.assertEqual(self.vista.mensaje.text(), MENSAJE_FECHAS)
        self.assertEqual(self.vista.mensaje.property("tipo"), "error")

    def test_tabla(self):
        self.vista.poner_variables(VARIABLES)
        self._consultar("caudal", filas())
        tabla = self.vista.tabla
        self.assertEqual(tabla.rowCount(), 3)
        self.assertEqual(tabla.item(0, 0).text(), "20/11/2026 10:00")
        self.assertEqual(tabla.item(0, 1).text(), "11,2 L/min")
        self.assertEqual(tabla.item(0, 4).text(), "12")
        self.assertIn("36 lecturas", self.vista.mensaje.text())

    def test_tabla_de_la_llama(self):
        self.vista.poner_variables(VARIABLES)
        self._consultar("llama", filas(maximo="1"))
        self.assertEqual(self.vista.tabla.columnCount(), 3)
        self.assertEqual(self.vista.tabla.item(0, 1).text(), "Sí")

    def test_sin_lecturas(self):
        self.vista.poner_variables(VARIABLES)
        self._consultar("caudal", [])
        self.assertEqual(self.vista.tabla.rowCount(), 0)
        self.assertEqual(self.vista.mensaje.text(), MENSAJE_VACIO)

    def test_grafica(self):
        self.vista.poner_variables(VARIABLES)
        self._consultar("caudal", filas())
        nombres = [s.name() for s in self.vista.grafica.chart().series()]
        # Banda, media y las dos líneas del rango normal
        self.assertEqual(nombres, ["Mínimo y máximo", "Media", "Rango normal", "Rango normal"])

    def test_grafica_de_la_llama(self):
        self.vista.poner_variables(VARIABLES)
        self._consultar("llama", filas(maximo="1"))
        nombres = [s.name() for s in self.vista.grafica.chart().series()]
        self.assertEqual(nombres, ["Fuego detectado"])


class PruebasControlador(unittest.TestCase):
    def setUp(self):
        self.vista = VistaHistorico("Histórico")
        self.repositorio = mock.patch.object(controlador_historico, "repositorio").start()
        self.addCleanup(mock.patch.stopall)
        self.repositorio.ultimas_lecturas.return_value = VARIABLES
        self.repositorio.historico_lecturas.return_value = filas()
        self.controlador = ControladorHistorico(self.vista, 7)

    def test_al_abrir_carga_variables_y_consulta(self):
        self.vista.abierta.emit()
        self.repositorio.ultimas_lecturas.assert_called_once_with(7)
        args = self.repositorio.historico_lecturas.call_args.args
        self.assertEqual(args[:2], (7, "caudal"))
        self.assertEqual(self.vista.tabla.rowCount(), 3)

    def test_sin_conexion(self):
        self.repositorio.ultimas_lecturas.side_effect = ErrorBaseDatos()
        self.vista.abierta.emit()
        self.assertEqual(self.vista.mensaje.text(), controlador_historico.MENSAJE_SIN_CONEXION)

    def test_falla_la_consulta(self):
        self.repositorio.historico_lecturas.side_effect = ErrorBaseDatos()
        self.vista.abierta.emit()
        self.assertEqual(self.vista.mensaje.text(), controlador_historico.MENSAJE_SIN_CONEXION)
        self.assertEqual(self.vista.tabla.rowCount(), 0)


class PruebasVentana(unittest.TestCase):
    def test_solo_cientificos_tienen_historico(self):
        self.assertIsInstance(VentanaPrincipal("cientificos", "empleado").historico,
                              VistaHistorico)
        self.assertIsNone(VentanaPrincipal("seguridad", "jefe_perfil").historico)
        self.assertIsNone(VentanaPrincipal("tech", "empleado").historico)


if __name__ == "__main__":
    unittest.main()
