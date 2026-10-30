"""Ventana principal: cabecera, menú lateral según el perfil y contenido."""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

LOGO = Path(__file__).resolve().parent / "estilos" / "logo_icono.png"

# Secciones del menú de cada perfil (sacadas de los mockups)
MENUS = {
    "cientificos": [
        ("Planta", ["Panel de planta", "Histórico", "Actuadores", "Avisos y alarmas"]),
        ("Gestión", ["Mis solicitudes", "Por aprobar", "Registro"]),
    ],
    "seguridad": [
        ("Instalación", ["Cámaras", "Puertas y accesos", "Cronología", "Niveles"]),
        ("Gestión", ["Mis solicitudes", "Por aprobar", "Registro"]),
    ],
    "tech": [
        ("Equipos y cuentas", ["Dispositivos", "Configuración", "Cuentas"]),
        ("Gestión", ["Solicitudes y permisos", "Registro"]),
    ],
}

# Niveles solo lo ven los jefes y subjefes de Seguridad
SOLO_JEFES = {"Niveles"}
RANGOS_JEFE = {"jefe_perfil", "subjefe_perfil"}


def secciones_menu(perfil: str, rango: str) -> list[tuple[str, list[str]]]:
    """Devuelve los grupos del menú que puede ver el usuario."""
    grupos = []
    for grupo, opciones in MENUS[perfil]:
        if rango not in RANGOS_JEFE:
            opciones = [o for o in opciones if o not in SOLO_JEFES]
        grupos.append((grupo, opciones))
    return grupos


class VentanaPrincipal(QMainWindow):
    """Ventana que se abre tras el login. Emite cerrar_sesion_pedido."""

    cerrar_sesion_pedido = Signal()

    def __init__(self, perfil: str, rango: str) -> None:
        super().__init__()
        self.setWindowTitle("A3I · Central nuclear")
        self.resize(1366, 768)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._cabecera())

        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(0)
        self.paginas = QStackedWidget()
        cuerpo.addWidget(self._menu(secciones_menu(perfil, rango)))
        cuerpo.addWidget(self.paginas, 1)
        layout.addLayout(cuerpo, 1)
        self.setCentralWidget(central)

    def _cabecera(self) -> QFrame:
        cabecera = QFrame()
        cabecera.setProperty("zona", "oscura")
        layout = QHBoxLayout(cabecera)
        layout.setContentsMargins(24, 12, 24, 12)

        logo = QLabel()
        logo.setPixmap(QPixmap(str(LOGO)).scaled(
            36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        titulo = QLabel("Central nuclear · Dashboard")
        titulo.setProperty("tipo", "etiqueta")
        layout.addWidget(logo)
        layout.addSpacing(8)
        layout.addWidget(titulo)
        layout.addStretch()

        # Datos del usuario (los rellena RF-008)
        self.caja_usuario = QFrame()
        self.caja_usuario.setProperty("tipo", "caja_usuario")
        datos = QVBoxLayout(self.caja_usuario)
        datos.setContentsMargins(12, 6, 12, 6)
        datos.setSpacing(2)
        self.nombre_usuario = QLabel()
        self.nombre_usuario.setProperty("tipo", "dato")
        self.detalle_usuario = QLabel()
        datos.addWidget(self.nombre_usuario)
        datos.addWidget(self.detalle_usuario)
        layout.addWidget(self.caja_usuario)
        layout.addSpacing(12)

        self.boton_cerrar = QPushButton("Cerrar sesión")
        self.boton_cerrar.setProperty("tipo", "secundario")
        self.boton_cerrar.clicked.connect(self.cerrar_sesion_pedido)
        layout.addWidget(self.boton_cerrar)
        return cabecera

    def _menu(self, grupos: list[tuple[str, list[str]]]) -> QFrame:
        menu = QFrame()
        menu.setProperty("zona", "oscura")
        menu.setFixedWidth(232)
        layout = QVBoxLayout(menu)
        layout.setContentsMargins(12, 24, 12, 24)
        layout.setSpacing(4)

        self.botones_menu = QButtonGroup(self)
        for grupo, opciones in grupos:
            seccion = QLabel(grupo.upper())
            seccion.setProperty("tipo", "seccion")
            layout.addSpacing(12)
            layout.addWidget(seccion)
            for opcion in opciones:
                boton = QPushButton(opcion)
                boton.setProperty("tipo", "menu")
                boton.setCheckable(True)
                indice = self.paginas.addWidget(self._pagina(opcion))
                self.botones_menu.addButton(boton, indice)
                layout.addWidget(boton)
        layout.addStretch()

        self.botones_menu.idClicked.connect(self.paginas.setCurrentIndex)
        self.botones_menu.button(0).setChecked(True)
        return menu

    def _pagina(self, titulo: str) -> QWidget:
        # De momento cada sección es una página vacía
        pagina = QWidget()
        layout = QVBoxLayout(pagina)
        layout.setContentsMargins(32, 28, 32, 28)
        etiqueta = QLabel(titulo)
        etiqueta.setProperty("tipo", "titulo")
        aviso = QLabel("Esta vista llegará en los próximos sprints.")
        aviso.setProperty("tipo", "subtitulo")
        layout.addWidget(etiqueta)
        layout.addWidget(aviso)
        layout.addStretch()
        return pagina
