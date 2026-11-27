"""RF-040: tablero de avisos y alarmas.

No usan BD: la vista recibe alertas inventadas con las columnas de
alertas_usuario y el controlador se prueba con el repositorio simulado.

    python -m unittest -v tests.test_rf040_vista_alertas
"""

import os
import time
import unittest
from datetime import datetime
from decimal import Decimal
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel

from app import config
from app.controller import controlador_alertas
from app.controller.controlador_alertas import ControladorAlertas
from app.model.repositorio import ErrorBaseDatos
from app.view.ventana_principal import VentanaPrincipal
from app.view.vista_alertas import AVISO_SPRINT4, VistaAlertas, estado_etiqueta

app = QApplication.instance() or QApplication([])


def alerta(id_alerta: int, tipo: str = "aviso", estado: str = "pendiente",
           variable: str = "caudal", **extra) -> dict:
    datos = {
        "id_alerta": id_alerta, "variable": variable, "unidad": "L/min",
        "sector": "cientifico", "tipo": tipo, "estado": estado,
        "valor": Decimal("8.5"), "fecha_hora": datetime(2026, 11, 27, 10, 0),
        "valor_alarma": None, "fecha_alarma": None,
        "minimo_normal": Decimal(8), "maximo_normal": Decimal(15),
        "encargado": None, "fecha_asignacion": None, "fecha_terminada": None,
        "motivo_devolucion": None, "revisor": None, "fecha_resolucion": None,
    }
    datos.update(extra)
    return datos


TABLERO = [
    alerta(1, "alarma"), alerta(2), alerta(3, estado="en_curso", encargado="Lucía Herrera"),
    alerta(4, estado="por_revisar", encargado="Lucía Herrera"),
    alerta(5, "alarma", "resuelta", revisor="Javier Morales",
           fecha_resolucion=datetime(2026, 11, 27, 11, 0)),
]


def _textos(widget) -> list[str]:
    return [etiqueta.text() for etiqueta in widget.findChildren(QLabel)]


class PruebasVista(unittest.TestCase):
    def setUp(self):
        self.vista = VistaAlertas("Avisos y alarmas")
        self.vista.mostrar_alertas(TABLERO)

    def _ids_columna(self, indice: int) -> list[int]:
        columna = self.vista.columnas[indice]
        tarjetas = [columna.itemAt(i).widget() for i in range(columna.count())]
        return [t.id_alerta for t in tarjetas if hasattr(t, "id_alerta")]

    def test_cada_estado_en_su_columna(self):
        self.assertEqual(self._ids_columna(0), [1, 2])
        self.assertEqual(self._ids_columna(1), [3, 4])
        self.assertEqual(self._ids_columna(2), [5])
        self.assertEqual([c.text() for c in self.vista.cabeceras],
                         ["TO DO · 2", "DOING · 2", "DONE · 1"])

    def test_colores(self):
        self.assertEqual(estado_etiqueta(alerta(1, "alarma")), "alarma")
        self.assertEqual(estado_etiqueta(alerta(1, "aviso")), "aviso")
        self.assertEqual(estado_etiqueta(alerta(1, "alarma", "resuelta")), "neutro")

    def test_marca_de_por_revisar(self):
        self.assertIn("Por revisar", _textos(self.vista.tarjetas[4]))
        self.assertNotIn("Por revisar", _textos(self.vista.tarjetas[3]))

    def test_aviso_que_subio_a_alarma(self):
        subida = alerta(6, "alarma", valor_alarma=Decimal("5"),
                        fecha_alarma=datetime(2026, 11, 27, 10, 15))
        self.vista.mostrar_alertas([subida])
        self.assertIn("5 L/min · 27/11/2026 10:15", _textos(self.vista.tarjetas[6]))

    def test_columna_vacia(self):
        self.vista.mostrar_alertas([])
        self.assertEqual(self.vista.cabeceras[0].text(), "TO DO · 0")
        self.assertIn("Sin alertas.", _textos(self.vista))

    def test_detalle(self):
        self.vista.seleccionar(5)
        texto = self.vista.texto_detalle.text()
        self.assertIn("Caudal de agua", texto)
        self.assertIn("Rango normal: 8–15 L/min", texto)
        self.assertIn("Resuelta por Javier Morales", texto)

    def test_botones_desactivados_segun_el_estado(self):
        for id_alerta, botones in ((1, {"Asignar", "Crear solicitud"}),
                                   (3, {"Terminada", "Crear solicitud"}),
                                   (4, {"Resolver", "Devolver"}), (5, set())):
            with self.subTest(id_alerta=id_alerta):
                self.vista.seleccionar(id_alerta)
                visibles = {t for t, b in self.vista.botones.items() if not b.isHidden()}
                self.assertEqual(visibles, botones)
                for texto in visibles:
                    self.assertFalse(self.vista.botones[texto].isEnabled())
                    self.assertEqual(self.vista.botones[texto].toolTip(), AVISO_SPRINT4)

    def test_la_eleccion_sigue_tras_refrescar(self):
        self.vista.seleccionar(2)
        self.vista.mostrar_alertas(TABLERO + [alerta(7)])
        self.assertEqual(self.vista.seleccionada, 2)
        self.vista.mostrar_alertas([alerta(7)])
        self.assertIsNone(self.vista.seleccionada)

    def test_periodo_de_done(self):
        horas = []
        self.vista.horas_cambiadas.connect(horas.append)
        self.vista.periodo.setCurrentIndex(1)
        self.assertEqual(horas, [24 * 7])


def _esperar(condicion, segundos: float = 2) -> bool:
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        app.processEvents()
        if condicion():
            return True
    return False


class PruebasControlador(unittest.TestCase):
    def setUp(self):
        self.vista = VistaAlertas("Avisos y alarmas")
        self.repositorio = mock.patch.object(controlador_alertas, "repositorio").start()
        self.addCleanup(mock.patch.stopall)
        self.repositorio.alertas_usuario.return_value = TABLERO
        self.controlador = ControladorAlertas(self.vista, 7)
        self.addCleanup(self.controlador.parar)

    def test_pide_las_alertas_del_usuario(self):
        self.controlador.iniciar()
        self.assertTrue(_esperar(lambda: len(self.vista.tarjetas) == 5))
        self.repositorio.alertas_usuario.assert_called_with(
            7, config.HORAS_ALERTAS_RESUELTAS)

    def test_cambiar_el_periodo(self):
        self.controlador.iniciar()
        _esperar(lambda: self.vista.tarjetas)
        self.vista.periodo.setCurrentIndex(2)
        self.assertTrue(_esperar(
            lambda: self.repositorio.alertas_usuario.call_args.args == (7, 24 * 30)))

    def test_sin_conexion(self):
        errores = []
        self.controlador.error_conexion.connect(lambda: errores.append(True))
        self.repositorio.alertas_usuario.side_effect = ErrorBaseDatos()
        self.controlador.iniciar()
        self.assertTrue(_esperar(lambda: errores))


class PruebasVentana(unittest.TestCase):
    def test_quien_tiene_avisos_y_alarmas(self):
        self.assertIsInstance(VentanaPrincipal("cientificos", "empleado").alertas, VistaAlertas)
        self.assertIsInstance(VentanaPrincipal("seguridad", "empleado").alertas, VistaAlertas)
        self.assertIsNone(VentanaPrincipal("tech", "jefe_perfil").alertas)


if __name__ == "__main__":
    unittest.main()
