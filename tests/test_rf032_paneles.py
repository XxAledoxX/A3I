"""RF-032: pruebas de los paneles de planta y de Seguridad.

No usan BD: se les pasan lecturas inventadas con las mismas columnas que
devolverán los procedimientos. Van con Qt sin pantalla (offscreen).

    python -m unittest -v tests.test_rf032_paneles
"""

import os
import unittest
from datetime import datetime
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.view.panel_equipos import PanelEquipos
from app.view.panel_planta import PanelPlanta, estado_lectura, formatear_numero
from app.view.panel_seguridad import PanelSeguridad, estado_equipo, texto_barrera
from app.view.ventana_principal import VentanaPrincipal

app = QApplication.instance() or QApplication([])


def lectura(variable: str, valor, minimo=None, maximo=None,
            sector: str = "cientifico", unidad: str = "") -> dict:
    return {
        "variable": variable,
        "unidad": unidad,
        "valor": None if valor is None else Decimal(str(valor)),
        "fecha_hora": datetime(2026, 11, 11, 17, 42, 5),
        "minimo_normal": None if minimo is None else Decimal(str(minimo)),
        "maximo_normal": None if maximo is None else Decimal(str(maximo)),
        "sector": sector,
    }


def actuador(nombre: str, posicion: int = 0, movimiento: str = "inmovil",
             estado: str = "operativo") -> dict:
    return {"nombre": nombre, "sector": "general", "posicion": posicion,
            "movimiento": movimiento, "estado": estado}


class PruebasEstadoLectura(unittest.TestCase):
    def test_dentro_del_rango_es_normal(self):
        self.assertEqual(estado_lectura(lectura("caudal", 11, 8, 15)), ("ok", "Normal"))

    def test_en_el_limite_sigue_normal(self):
        self.assertEqual(estado_lectura(lectura("caudal", 15, 8, 15))[0], "ok")
        self.assertEqual(estado_lectura(lectura("caudal", 8, 8, 15))[0], "ok")

    def test_fuera_del_rango_es_alarma(self):
        self.assertEqual(estado_lectura(lectura("caudal", 15.1, 8, 15)),
                         ("alarma", "Fuera de rango"))
        self.assertEqual(estado_lectura(lectura("caudal", 7.9, 8, 15))[0], "alarma")

    def test_llama(self):
        self.assertEqual(estado_lectura(lectura("llama", 1)), ("alarma", "Fuego detectado"))
        self.assertEqual(estado_lectura(lectura("llama", 0)), ("ok", "Normal"))

    def test_sin_lectura(self):
        self.assertEqual(estado_lectura(None), ("neutro", "Sin datos"))
        self.assertEqual(estado_lectura(lectura("caudal", None, 8, 15))[0], "neutro")

    def test_formato_de_numeros(self):
        self.assertEqual(formatear_numero(Decimal("41.00")), "41")
        self.assertEqual(formatear_numero(Decimal("52.50")), "52,5")
        self.assertEqual(formatear_numero(Decimal("650")), "650")


class PruebasActuadores(unittest.TestCase):
    def test_barrera(self):
        self.assertEqual(texto_barrera(actuador("barrera", 0)), "Cerrada")
        self.assertEqual(texto_barrera(actuador("barrera", 100)), "Abierta")
        self.assertEqual(texto_barrera(actuador("barrera", 40, "en_movimiento")),
                         "En movimiento")

    def test_estado_del_equipo(self):
        self.assertEqual(estado_equipo(actuador("camara")), ("ok", "Operativo"))
        self.assertEqual(estado_equipo(actuador("camara", estado="a_revisar"))[0], "aviso")
        self.assertEqual(estado_equipo(actuador("camara", estado="sin_conexion"))[0],
                         "neutro")
        self.assertEqual(estado_equipo(None), ("neutro", "Sin datos"))


class PruebasPanelPlanta(unittest.TestCase):
    def setUp(self):
        self.panel = PanelPlanta("Panel de planta")
        self.lecturas = [
            lectura("temperatura_ambiente", 27.3, 18, 26, unidad="°C"),
            lectura("caudal", 11.2, 8, 15, unidad="L/min"),
            lectura("llama", 0, sector="critico"),
        ]

    def test_sin_lecturas_muestra_aviso(self):
        self.panel.mostrar_lecturas([])
        self.assertFalse(self.panel.sin_datos.isHidden())
        self.assertEqual(self.panel.tarjetas, {})

    def test_una_tarjeta_por_variable_recibida(self):
        self.panel.mostrar_lecturas(self.lecturas, "17:42:05")
        self.assertEqual(set(self.panel.tarjetas), {"temperatura_ambiente", "caudal", "llama"})
        self.assertTrue(self.panel.sin_datos.isHidden())
        self.assertIn("17:42:05", self.panel.actualizado.text())

    def test_no_muestra_lo_que_no_llega(self):
        # Un científico de nivel 2 no recibe el reactor, así que no sale su tarjeta
        self.panel.mostrar_lecturas(self.lecturas)
        self.assertNotIn("temperatura_interior", self.panel.tarjetas)

    def test_estado_y_valor_de_la_tarjeta(self):
        self.panel.mostrar_lecturas(self.lecturas)
        tarjeta = self.panel.tarjetas["temperatura_ambiente"]
        self.assertEqual(tarjeta.valor.text(), "27,3 °C")
        self.assertEqual(tarjeta.estado.property("estado"), "alarma")
        self.assertEqual(self.panel.tarjetas["caudal"].estado.property("estado"), "ok")

    def test_refresco_no_crea_tarjetas_nuevas(self):
        self.panel.mostrar_lecturas(self.lecturas)
        antes = self.panel.tarjetas["caudal"]
        self.lecturas[1] = lectura("caudal", 16, 8, 15, unidad="L/min")
        self.panel.mostrar_lecturas(self.lecturas)
        self.assertIs(self.panel.tarjetas["caudal"], antes)
        self.assertEqual(antes.estado.property("estado"), "alarma")


class PruebasPanelSeguridad(unittest.TestCase):
    def setUp(self):
        self.panel = PanelSeguridad("Cámaras")

    def test_llama(self):
        self.panel.mostrar_lecturas([lectura("llama", 1, sector="critico")])
        self.assertEqual(self.panel.llama.estado.text(), "Fuego detectado")

    def test_barrera_cerrada_y_abierta(self):
        self.panel.mostrar_actuadores([actuador("barrera", 0)])
        self.assertEqual(self.panel.barrera.posicion.text(), "Cerrada")
        self.assertEqual(self.panel.barrera.boton.text(), "Abrir barrera")

        self.panel.mostrar_actuadores([actuador("barrera", 100)])
        self.assertEqual(self.panel.barrera.posicion.text(), "Abierta")
        self.assertEqual(self.panel.barrera.boton.text(), "Cerrar barrera")

    def test_boton_de_la_barrera_desactivado(self):
        self.panel.mostrar_actuadores([actuador("barrera", 0)])
        self.assertFalse(self.panel.barrera.boton.isEnabled())

    def test_camara_sin_senal(self):
        self.panel.mostrar_actuadores([actuador("camara", estado="a_revisar")])
        self.assertEqual(self.panel.camara.video.text(), "Sin señal")
        self.assertEqual(self.panel.camara.estado.property("estado"), "aviso")

    def test_sin_actuadores(self):
        self.panel.mostrar_actuadores([])
        self.assertEqual(self.panel.barrera.estado.text(), "Sin datos")
        self.assertEqual(self.panel.camara.estado.text(), "Sin datos")


class PruebasVentanaPrincipal(unittest.TestCase):
    def test_cada_perfil_abre_en_su_panel(self):
        esperado = {
            "cientificos": PanelPlanta,
            "seguridad": PanelSeguridad,
            "tech": PanelEquipos,
        }
        for perfil, clase in esperado.items():
            with self.subTest(perfil=perfil):
                ventana = VentanaPrincipal(perfil, "empleado")
                self.assertIsInstance(ventana.panel, clase)
                self.assertIs(ventana.paginas.currentWidget(), ventana.panel)
                ventana.deleteLater()


if __name__ == "__main__":
    unittest.main()
