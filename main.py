"""Arranca la aplicación."""

import sys

from PySide6.QtWidgets import QApplication

from app.controller.controlador_login import ControladorLogin
from app.view.estilos import aplicar_estilos


def main() -> None:
    app = QApplication(sys.argv)
    aplicar_estilos(app)
    controlador = ControladorLogin()
    controlador.mostrar()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
