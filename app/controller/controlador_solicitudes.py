"""Controlador de mis solicitudes: crea, lista y cancela con lo que pide la vista."""

from app.model import repositorio
from app.model.repositorio import ErrorBaseDatos, ErrorRegla
from app.view.vista_solicitudes import VistaSolicitudes

MENSAJE_SIN_CONEXION = "No se ha podido conectar. Inténtalo más tarde."


class ControladorSolicitudes:
    def __init__(self, vista: VistaSolicitudes, id_usuario: int) -> None:
        self.vista = vista
        self.id_usuario = id_usuario
        vista.abierta.connect(self.cargar)
        vista.actualizar_pedido.connect(self.cargar_solicitudes)
        vista.sector_elegido.connect(self.cargar_dispositivos)
        vista.envio_pedido.connect(self.crear)
        vista.cancelacion_pedida.connect(self.cancelar)

    def cargar(self) -> None:
        """Al abrir la sección: sectores del formulario y lista de solicitudes."""
        try:
            sectores = repositorio.sectores(self.id_usuario)
        except ErrorBaseDatos:
            self.vista.mostrar_error(MENSAJE_SIN_CONEXION)
            return
        self.vista.poner_sectores(sectores)
        self.cargar_solicitudes()

    def cargar_solicitudes(self) -> None:
        try:
            filas = repositorio.mis_solicitudes(self.id_usuario)
        except ErrorBaseDatos:
            self.vista.mostrar_error(MENSAJE_SIN_CONEXION)
            return
        self.vista.mostrar_solicitudes(filas)

    def cargar_dispositivos(self, id_sector: int) -> None:
        try:
            filas = repositorio.dispositivos_sector(self.id_usuario, id_sector)
        except ErrorBaseDatos:
            self.vista.mostrar_error(MENSAJE_SIN_CONEXION)
            return
        self.vista.poner_dispositivos(filas)

    def crear(self, tipo: str, prioridad: str, motivo: str, id_sector: int,
              duracion_min: int, id_dispositivo: int | None) -> None:
        try:
            repositorio.crear_solicitud(self.id_usuario, tipo, prioridad, motivo,
                                        id_sector, duracion_min, id_dispositivo)
        except ErrorRegla as error:
            self.vista.mostrar_error(str(error))
            return
        except ErrorBaseDatos:
            self.vista.mostrar_error(MENSAJE_SIN_CONEXION)
            return
        self.vista.solicitud_creada()
        self.cargar_solicitudes()

    def cancelar(self, id_solicitud: int) -> None:
        try:
            repositorio.cancelar_solicitud(self.id_usuario, id_solicitud)
        except ErrorRegla as error:
            self.vista.mostrar_error(str(error))
            return
        except ErrorBaseDatos:
            self.vista.mostrar_error(MENSAJE_SIN_CONEXION)
            return
        self.cargar_solicitudes()
