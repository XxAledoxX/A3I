"""Controlador del panel: pide los datos cada pocos segundos sin congelar la ventana."""

from collections.abc import Callable
from datetime import datetime

from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot

from app import config
from app.model.repositorio import ErrorBaseDatos

# Función que devuelve (lecturas, actuadores, equipos). La de verdad llega con RF-031
ObtenerDatos = Callable[[], tuple[list[dict], list[dict], list[dict]]]


class Trabajador(QObject):
    """Hace la consulta en un hilo aparte y avisa con una señal."""

    datos_listos = Signal(list, list, list)
    fallo = Signal()

    def __init__(self, obtener_datos: ObtenerDatos) -> None:
        super().__init__()
        self.obtener_datos = obtener_datos

    @Slot()
    def cargar(self) -> None:
        try:
            lecturas, actuadores, equipos = self.obtener_datos()
        except ErrorBaseDatos:
            self.fallo.emit()
            return
        self.datos_listos.emit(lecturas, actuadores, equipos)


class ControladorPanel(QObject):
    """Refresca el panel cada config.SEGUNDOS_REFRESCO segundos.

    Emite error_conexion si falla la consulta; el panel se queda con los
    últimos datos.
    """

    pedir_datos = Signal()
    error_conexion = Signal()

    def __init__(self, panel, obtener_datos: ObtenerDatos) -> None:
        super().__init__()
        self.panel = panel
        # Si la consulta anterior no ha terminado, no se pide otra
        self.ocupado = False

        # El trabajador vive en otro hilo; solo este hilo toca la ventana
        self.hilo = QThread()
        self.trabajador = Trabajador(obtener_datos)
        self.trabajador.moveToThread(self.hilo)
        self.pedir_datos.connect(self.trabajador.cargar)
        self.trabajador.datos_listos.connect(self._mostrar)
        self.trabajador.fallo.connect(self._fallo)

        self.temporizador = QTimer(self)
        self.temporizador.setInterval(int(config.SEGUNDOS_REFRESCO * 1000))
        self.temporizador.timeout.connect(self.refrescar)

    def iniciar(self) -> None:
        """Carga los datos ya y luego cada pocos segundos."""
        self.hilo.start()
        self.refrescar()
        self.temporizador.start()

    def parar(self) -> None:
        """Para el temporizador y espera a que termine el hilo."""
        self.temporizador.stop()
        self.hilo.quit()
        self.hilo.wait()

    def refrescar(self) -> None:
        if self.ocupado:
            return
        self.ocupado = True
        self.pedir_datos.emit()

    def _mostrar(self, lecturas: list[dict], actuadores: list[dict],
                 equipos: list[dict]) -> None:
        self.ocupado = False
        self.panel.mostrar_lecturas(lecturas, datetime.now().strftime("%H:%M:%S"))
        # Seguridad muestra actuadores y Tech, el estado de los equipos
        if hasattr(self.panel, "mostrar_actuadores"):
            self.panel.mostrar_actuadores(actuadores)
        if hasattr(self.panel, "mostrar_equipos"):
            self.panel.mostrar_equipos(equipos)

    def _fallo(self) -> None:
        self.ocupado = False
        self.error_conexion.emit()


if __name__ == "__main__":
    # Demo con datos inventados que cambian cada 5 s:
    # python -m app.controller.controlador_panel
    import random
    import sys
    from decimal import Decimal

    from PySide6.QtWidgets import QApplication, QMainWindow

    from app.view.estilos import aplicar_estilos
    from app.view.panel_planta import PanelPlanta

    variables = [
        ("temperatura_interior", "°C", 40, 70, "critico"),
        ("humedad_interior", "%", 30, 50, "critico"),
        ("temperatura_ambiente", "°C", 18, 26, "cientifico"),
        ("humedad_ambiente", "%", 40, 60, "cientifico"),
        ("calidad_aire", "ppm", 400, 900, "cientifico"),
        ("caudal", "L/min", 8, 15, "cientifico"),
    ]

    def datos_inventados() -> tuple[list[dict], list[dict], list[dict]]:
        ahora = datetime.now()
        lecturas = []
        for nombre, unidad, minimo, maximo, sector in variables:
            # A veces se sale un poco del rango para ver el color rojo
            margen = (maximo - minimo) * 0.15
            valor = random.uniform(minimo - margen, maximo + margen)
            lecturas.append({
                "variable": nombre, "unidad": unidad,
                "valor": Decimal(f"{valor:.1f}"), "fecha_hora": ahora,
                "minimo_normal": Decimal(minimo), "maximo_normal": Decimal(maximo),
                "sector": sector,
            })
        lecturas.append({
            "variable": "llama", "unidad": "", "valor": Decimal(random.random() < 0.1),
            "fecha_hora": ahora, "minimo_normal": None, "maximo_normal": None,
            "sector": "critico",
        })
        return lecturas, [], []

    app = QApplication(sys.argv)
    aplicar_estilos(app)
    ventana = QMainWindow()
    panel = PanelPlanta("Panel de planta")
    ventana.setCentralWidget(panel)
    ventana.resize(1134, 700)

    controlador = ControladorPanel(panel, datos_inventados)
    app.aboutToQuit.connect(controlador.parar)
    controlador.iniciar()
    ventana.show()
    sys.exit(app.exec())
