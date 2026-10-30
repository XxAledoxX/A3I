"""Ventana de inicio de sesión."""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

LOGO = Path(__file__).resolve().parent / "estilos" / "logo_icono.png"


class VentanaLogin(QMainWindow):
    """Pide usuario y contraseña y emite login_pedido al pulsar el botón."""

    login_pedido = Signal(str, str)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("A3I · Iniciar sesión")
        self.resize(1200, 760)

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._panel_presentacion(), 1)
        layout.addWidget(self._panel_formulario(), 1)
        self.setCentralWidget(central)

    def _panel_presentacion(self) -> QFrame:
        panel = QFrame()
        panel.setProperty("zona", "oscura")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(56, 48, 56, 40)

        marca = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(QPixmap(str(LOGO)).scaled(
            48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        nombre = QLabel("A3I")
        nombre.setProperty("tipo", "etiqueta")
        marca.addWidget(logo)
        marca.addWidget(nombre)
        marca.addStretch()
        layout.addLayout(marca)
        layout.addStretch()

        acento = QFrame()
        acento.setProperty("tipo", "acento")
        acento.setFixedSize(56, 4)
        titulo = QLabel("Dashboard de la central nuclear")
        titulo.setProperty("tipo", "titulo")
        titulo.setWordWrap(True)
        texto = QLabel(
            "Monitorización y operación de la planta simulada. Cada perfil ve "
            "solo lo que le corresponde según su nivel y su sector, y cada "
            "acción relevante queda registrada."
        )
        texto.setProperty("tipo", "subtitulo")
        texto.setWordWrap(True)
        layout.addWidget(acento)
        layout.addSpacing(16)
        layout.addWidget(titulo)
        layout.addSpacing(8)
        layout.addWidget(texto)
        layout.addSpacing(16)

        perfiles = QHBoxLayout()
        for perfil in ("Científicos", "Seguridad", "Tech/Mantenimiento"):
            chip = QLabel(perfil)
            chip.setProperty("tipo", "chip")
            perfiles.addWidget(chip)
        perfiles.addStretch()
        layout.addLayout(perfiles)
        layout.addStretch()

        pie = QLabel("Entorno simulado · Proyecto de Ingeniería I · UEM 2026-2027")
        pie.setProperty("tipo", "dato")
        layout.addWidget(pie)
        return panel

    def _panel_formulario(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.addStretch()

        tarjeta = QFrame()
        tarjeta.setProperty("tipo", "tarjeta")
        tarjeta.setFixedWidth(420)
        campos = QVBoxLayout(tarjeta)
        campos.setContentsMargins(40, 36, 40, 36)
        campos.setSpacing(8)

        titulo = QLabel("Iniciar sesión")
        titulo.setProperty("tipo", "titulo")
        subtitulo = QLabel("Introduce las credenciales de tu cuenta.")
        subtitulo.setProperty("tipo", "subtitulo")
        campos.addWidget(titulo)
        campos.addWidget(subtitulo)
        campos.addSpacing(12)

        self.error = QLabel()
        self.error.setProperty("tipo", "error")
        self.error.setWordWrap(True)
        self.error.hide()
        campos.addWidget(self.error)

        etiqueta_usuario = QLabel("Usuario")
        etiqueta_usuario.setProperty("tipo", "etiqueta")
        self.usuario = QLineEdit()
        self.usuario.setPlaceholderText("Usuario")
        etiqueta_contrasena = QLabel("Contraseña")
        etiqueta_contrasena.setProperty("tipo", "etiqueta")
        self.contrasena = QLineEdit()
        self.contrasena.setPlaceholderText("Contraseña")
        self.contrasena.setEchoMode(QLineEdit.Password)
        campos.addWidget(etiqueta_usuario)
        campos.addWidget(self.usuario)
        campos.addSpacing(8)
        campos.addWidget(etiqueta_contrasena)
        campos.addWidget(self.contrasena)
        campos.addSpacing(16)

        self.boton = QPushButton("Iniciar sesión")
        self.boton.setProperty("tipo", "primario")
        campos.addWidget(self.boton)
        campos.addSpacing(16)

        separador = QFrame()
        separador.setProperty("tipo", "separador")
        separador.setFixedHeight(1)
        campos.addWidget(separador)
        campos.addSpacing(8)
        for nota in (
            "Tras varios intentos fallidos la cuenta se bloquea.",
            "No hay auto-registro: las cuentas nuevas se crean mediante una "
            "solicitud aprobada.",
        ):
            etiqueta = QLabel(nota)
            etiqueta.setProperty("tipo", "nota")
            etiqueta.setWordWrap(True)
            campos.addWidget(etiqueta)

        layout.addWidget(tarjeta, 0, Qt.AlignHCenter)
        layout.addStretch()

        self.boton.clicked.connect(self._enviar)
        self.usuario.returnPressed.connect(self.contrasena.setFocus)
        self.contrasena.returnPressed.connect(self._enviar)
        return panel

    def _enviar(self) -> None:
        self.login_pedido.emit(self.usuario.text(), self.contrasena.text())

    def mostrar_error(self, mensaje: str) -> None:
        self.error.setText(mensaje)
        self.error.show()
        self.contrasena.clear()
        self.contrasena.setFocus()

    def limpiar(self) -> None:
        self.error.hide()
        self.usuario.clear()
        self.contrasena.clear()
        self.usuario.setFocus()
