"""Controlador del login: une la ventana de login con la autenticación."""

from app.model import autenticacion
from app.model.repositorio import ErrorBaseDatos
from app.model.usuario import Usuario
from app.view.ventana_login import VentanaLogin
from app.view.ventana_principal import VentanaPrincipal

# Mismo mensaje sea cual sea el fallo, para no dar pistas
MENSAJE_ERROR = "Usuario o contraseña incorrectos."
MENSAJE_SIN_CONEXION = "No se ha podido conectar. Inténtalo más tarde."


class ControladorLogin:
    def __init__(self) -> None:
        self.ventana_login = VentanaLogin()
        self.ventana_principal: VentanaPrincipal | None = None
        self.ventana_login.login_pedido.connect(self.iniciar_sesion)

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
        self.ventana_principal.show()
        self.ventana_login.limpiar()
        self.ventana_login.close()
