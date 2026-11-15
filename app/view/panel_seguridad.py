"""Panel de Seguridad: detector de llama, barrera y cámara."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from app.view.panel_planta import ETIQUETAS_SECTOR, TarjetaVariable, poner_estado

# Estado del equipo: (estado de la etiqueta, texto)
ESTADOS_EQUIPO = {
    "operativo": ("ok", "Operativo"),
    "a_revisar": ("aviso", "A revisar"),
    "mantenimiento": ("neutro", "En mantenimiento"),
    "sin_conexion": ("neutro", "Sin conexión"),
}


def texto_barrera(actuador: dict) -> str:
    """Abierta o cerrada según la posición (la barrera solo usa 0 o 100)."""
    if actuador["movimiento"] == "en_movimiento":
        return "En movimiento"
    return "Abierta" if actuador["posicion"] == 100 else "Cerrada"


def estado_equipo(actuador: dict | None) -> tuple[str, str]:
    if actuador is None:
        return "neutro", "Sin datos"
    return ESTADOS_EQUIPO.get(actuador["estado"], ("neutro", actuador["estado"]))


class TarjetaActuador(QFrame):
    """Tarjeta con el nombre, el sector y el estado del equipo."""

    def __init__(self, nombre: str) -> None:
        super().__init__()
        self.setProperty("tipo", "tarjeta")
        self.nombre = nombre
        self.layout_tarjeta = QVBoxLayout(self)
        self.layout_tarjeta.setContentsMargins(18, 16, 18, 16)
        self.layout_tarjeta.setSpacing(8)

        self.titulo = QLabel(nombre)
        self.titulo.setProperty("tipo", "etiqueta")
        self.estado = QLabel()
        fila_estado = QHBoxLayout()
        fila_estado.addWidget(self.estado)
        fila_estado.addStretch()

        self.layout_tarjeta.addWidget(self.titulo)
        self.layout_tarjeta.addLayout(fila_estado)

    def actualizar(self, actuador: dict | None) -> None:
        if actuador is not None:
            sector = ETIQUETAS_SECTOR.get(actuador["sector"], actuador["sector"])
            self.titulo.setText(f"{self.nombre} · {sector}")
        poner_estado(self.estado, *estado_equipo(actuador))


class TarjetaBarrera(TarjetaActuador):
    def __init__(self) -> None:
        super().__init__("Barrera")
        self.posicion = QLabel("—")
        self.posicion.setProperty("tipo", "valor")
        # Abrir y cerrar llegan con los actuadores; de momento no hace nada
        self.boton = QPushButton("Abrir barrera")
        self.boton.setProperty("tipo", "primario")
        self.boton.setEnabled(False)
        self.boton.setToolTip("Disponible más adelante")
        self.layout_tarjeta.insertWidget(1, self.posicion)
        self.layout_tarjeta.addStretch()
        self.layout_tarjeta.addWidget(self.boton)
        self.actualizar(None)

    def actualizar(self, actuador: dict | None) -> None:
        super().actualizar(actuador)
        if actuador is None:
            return
        texto = texto_barrera(actuador)
        self.posicion.setText(texto)
        self.boton.setText("Cerrar barrera" if texto == "Abierta" else "Abrir barrera")


class TarjetaCamara(TarjetaActuador):
    def __init__(self) -> None:
        super().__init__("Cámara")
        # Aquí irá el vídeo cuando se conecte la cámara
        self.video = QLabel("Sin señal")
        self.video.setProperty("tipo", "video")
        self.video.setAlignment(Qt.AlignCenter)
        self.video.setMinimumSize(384, 216)
        self.layout_tarjeta.insertWidget(1, self.video, 1)
        self.actualizar(None)


class PanelSeguridad(QWidget):
    """Recibe los datos del controlador con mostrar_lecturas() y mostrar_actuadores()."""

    def __init__(self, titulo: str) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        cabecera = QHBoxLayout()
        etiqueta = QLabel(titulo)
        etiqueta.setProperty("tipo", "titulo")
        self.actualizado = QLabel()
        self.actualizado.setProperty("tipo", "nota")
        cabecera.addWidget(etiqueta)
        cabecera.addStretch()
        cabecera.addWidget(self.actualizado)
        layout.addLayout(cabecera)

        self.llama = TarjetaVariable("llama")
        self.barrera = TarjetaBarrera()
        self.camara = TarjetaCamara()

        izquierda = QVBoxLayout()
        izquierda.setSpacing(16)
        izquierda.addWidget(self.llama)
        izquierda.addWidget(self.barrera, 1)

        fila = QHBoxLayout()
        fila.setSpacing(16)
        fila.addLayout(izquierda, 1)
        fila.addWidget(self.camara, 2)
        layout.addLayout(fila)
        layout.addStretch()

    def mostrar_lecturas(self, lecturas: list[dict], hora: str = "") -> None:
        """De las lecturas solo usa la llama."""
        llama = next((x for x in lecturas if x["variable"] == "llama"), None)
        self.llama.actualizar(llama)
        if hora:
            self.actualizado.setText(f"Última actualización {hora}")

    def mostrar_actuadores(self, actuadores: list[dict]) -> None:
        por_nombre = {a["nombre"]: a for a in actuadores}
        self.barrera.actualizar(por_nombre.get("barrera"))
        self.camara.actualizar(por_nombre.get("camara"))


if __name__ == "__main__":
    # Demo con datos inventados: python -m app.view.panel_seguridad
    import sys
    from datetime import datetime

    from PySide6.QtWidgets import QApplication

    from app.view.estilos import aplicar_estilos

    ahora = datetime.now()
    app = QApplication(sys.argv)
    aplicar_estilos(app)
    panel = PanelSeguridad("Cámaras")
    panel.mostrar_lecturas([{"variable": "llama", "unidad": "", "valor": 0,
                             "fecha_hora": ahora, "minimo_normal": None,
                             "maximo_normal": None, "sector": "critico"}],
                           ahora.strftime("%H:%M:%S"))
    panel.mostrar_actuadores([
        {"nombre": "barrera", "sector": "general", "posicion": 0,
         "movimiento": "inmovil", "estado": "operativo"},
        {"nombre": "camara", "sector": "general", "posicion": 0,
         "movimiento": "inmovil", "estado": "operativo"},
    ])
    panel.resize(1134, 700)
    panel.show()
    sys.exit(app.exec())
