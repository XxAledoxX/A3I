"""Controlador del login: une la ventana de login con la autenticación."""

from functools import partial

from PySide6.QtCore import QEvent, QObject, QTimer
from PySide6.QtWidgets import QApplication

from app import config
from app.controller.controlador_historico import ControladorHistorico
from app.controller.controlador_panel import ControladorPanel
from app.controller.controlador_solicitudes import ControladorSolicitudes
from app.model import autenticacion, repositorio
from app.model.repositorio import ErrorBaseDatos
from app.model.usuario import Usuario
from app.view.ventana_login import VentanaLogin
from app.view.ventana_principal import VentanaPrincipal

# Mismo mensaje sea cual sea el fallo, para no dar pistas
MENSAJE_ERROR = "Usuario o contraseña incorrectos."
MENSAJE_SIN_CONEXION = "No se ha podido conectar. Inténtalo más tarde."
MENSAJE_INACTIVIDAD = "La sesión se ha cerrado por inactividad."

# Eventos que cuentan como que el usuario sigue usando la aplicación
EVENTOS_ACTIVIDAD = {QEvent.KeyPress, QEvent.MouseButtonPress, QEvent.Wheel}


class DetectorActividad(QObject):
    """Reinicia el temporizador cada vez que el usuario pulsa algo."""

    def __init__(self, temporizador: QTimer) -> None:
        super().__init__()
        self.temporizador = temporizador

    def eventFilter(self, objeto: QObject, evento: QEvent) -> bool:
        if evento.type() in EVENTOS_ACTIVIDAD:
            self.temporizador.start()
        return False


class ControladorLogin:
    def __init__(self) -> None:
        self.ventana_login = VentanaLogin()
        self.ventana_principal: VentanaPrincipal | None = None
        self.controlador_panel: ControladorPanel | None = None
        self.controlador_historico: ControladorHistorico | None = None
        self.controlador_solicitudes: ControladorSolicitudes | None = None
        self.ventana_login.login_pedido.connect(self.iniciar_sesion)

        self.temporizador = QTimer()
        self.temporizador.setSingleShot(True)
        self.temporizador.timeout.connect(self.sesion_caducada)
        self.detector = DetectorActividad(self.temporizador)

    def mostrar(self) -> None:
        self.ventana_login.show()

    def iniciar_sesion(self, login: str, contrasena: str) -> None:
        try:
            usuario = autenticacion.autenticar(login, contrasena)
        except ErrorBaseDatos:
            self.ventana_login.mostrar_error(MENSAJE_SIN_CONEXION)
            return

        if usuario is None:
            self.ventana_login.mostrar_error(MENSAJE_ERROR)
            return
        self.abrir_ventana_principal(usuario)

    def abrir_ventana_principal(self, usuario: Usuario) -> None:
        """Abre la ventana con el menú del perfil del usuario."""
        self.ventana_principal = VentanaPrincipal(usuario.perfil, usuario.rango)
        self.ventana_principal.mostrar_usuario(
            usuario.nombre, usuario.perfil, usuario.nivel, usuario.rango
        )
        self.ventana_principal.cerrar_sesion_pedido.connect(self.cerrar_sesion)
        self.ventana_principal.show()
        self.ventana_login.limpiar()
        self.ventana_login.close()

        self.temporizador.setInterval(int(config.MINUTOS_INACTIVIDAD * 60 * 1000))
        self.temporizador.start()
        QApplication.instance().installEventFilter(self.detector)
        self.iniciar_refresco(usuario)
        if self.ventana_principal.historico is not None:
            self.controlador_historico = ControladorHistorico(
                self.ventana_principal.historico, usuario.id_usuario
            )
        if self.ventana_principal.solicitudes is not None:
            self.controlador_solicitudes = ControladorSolicitudes(
                self.ventana_principal.solicitudes, usuario.id_usuario
            )

    def iniciar_refresco(self, usuario: Usuario) -> None:
        """Pide los datos del panel cada pocos segundos (RF-017) con su usuario."""
        ventana = self.ventana_principal
        if ventana.panel is None:
            return
        self.controlador_panel = ControladorPanel(
            ventana.panel, partial(repositorio.datos_panel, usuario.id_usuario)
        )
        self.controlador_panel.error_conexion.connect(
            partial(ventana.mostrar_sin_conexion, True)
        )
        self.controlador_panel.datos_recibidos.connect(
            partial(ventana.mostrar_sin_conexion, False)
        )
        self.controlador_panel.iniciar()

    def _terminar_sesion(self) -> None:
        """Para el temporizador y el hilo del refresco y cierra la sesión."""
        self.temporizador.stop()
        QApplication.instance().removeEventFilter(self.detector)
        if self.controlador_panel is not None:
            self.controlador_panel.parar()
            self.controlador_panel = None
        self.controlador_historico = None
        self.controlador_solicitudes = None
        autenticacion.cerrar_sesion()

    def cerrar_sesion(self) -> None:
        """Cierra la ventana principal y vuelve al login."""
        self._terminar_sesion()
        self.ventana_login.limpiar()
        self.ventana_login.show()
        self.ventana_principal.close()
        self.ventana_principal.deleteLater()
        self.ventana_principal = None

    def salir(self) -> None:
        """Al cerrar la app (también con la X): si el hilo sigue vivo, Qt aborta."""
        self._terminar_sesion()

    def sesion_caducada(self) -> None:
        self.cerrar_sesion()
        self.ventana_login.mostrar_error(MENSAJE_INACTIVIDAD)
