"""Controlador de avisos y alarmas: refresca el tablero igual que el panel (RF-017)."""

from datetime import datetime

from app import config
from app.controller.controlador_panel import ControladorPanel
from app.model import repositorio
from app.view.vista_alertas import VistaAlertas


class ControladorAlertas(ControladorPanel):
    """Mismo temporizador, hilo y señales que el panel, pero pide las alertas."""

    def __init__(self, vista: VistaAlertas, id_usuario: int) -> None:
        self.id_usuario = id_usuario
        self.horas = config.HORAS_ALERTAS_RESUELTAS
        # El trabajador espera tres listas: las otras dos van vacías
        super().__init__(vista, lambda: (self._pedir_alertas(), [], []))
        vista.horas_cambiadas.connect(self.cambiar_horas)

    def _pedir_alertas(self) -> list[dict]:
        return repositorio.alertas_usuario(self.id_usuario, self.horas)

    def cambiar_horas(self, horas: int) -> None:
        self.horas = horas
        self.refrescar()

    def _mostrar(self, alertas: list[dict], *_) -> None:
        self.ocupado = False
        self.panel.mostrar_alertas(alertas, datetime.now().strftime("%H:%M:%S"))
        self.datos_recibidos.emit()
