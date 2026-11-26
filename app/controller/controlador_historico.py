"""Controlador del histórico: pide a la BD lo que elige el usuario en la vista."""

from datetime import datetime

from app.model import repositorio
from app.model.repositorio import ErrorBaseDatos
from app.view.vista_historico import VistaHistorico

MENSAJE_SIN_CONEXION = "No se ha podido conectar. Inténtalo más tarde."


class ControladorHistorico:
    def __init__(self, vista: VistaHistorico, id_usuario: int) -> None:
        self.vista = vista
        self.id_usuario = id_usuario
        vista.abierta.connect(self.cargar_variables)
        vista.consulta_pedida.connect(self.consultar)

    def cargar_variables(self) -> None:
        """Las variables del desplegable son las que el usuario ve en el panel."""
        try:
            lecturas = repositorio.ultimas_lecturas(self.id_usuario)
        except ErrorBaseDatos:
            self.vista.mostrar_error(MENSAJE_SIN_CONEXION)
            return
        self.vista.poner_variables(lecturas)

    def consultar(self, variable: str, desde: datetime, hasta: datetime) -> None:
        try:
            filas = repositorio.historico_lecturas(self.id_usuario, variable, desde, hasta)
        except ErrorBaseDatos:
            self.vista.mostrar_error(MENSAJE_SIN_CONEXION)
            return
        self.vista.mostrar_historico(filas)
