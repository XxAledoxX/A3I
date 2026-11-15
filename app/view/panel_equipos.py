"""Panel de Tech: detector de llama y estado de los equipos de su sector."""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from app.view.panel_planta import (
    ETIQUETAS_SECTOR,
    ORDEN_SECTORES,
    TarjetaVariable,
    poner_estado,
)
from app.view.panel_seguridad import estado_equipo

# Texto que se muestra para cada dispositivo de la BD
ETIQUETAS_DISPOSITIVO = {
    "sensor_interior": "Sensor interior (temperatura y humedad)",
    "sensor_ambiente": "Sensor ambiente (temperatura y humedad)",
    "detector_llama": "Detector de llama",
    "sensor_aire": "Sensor de calidad del aire",
    "caudalimetro": "Caudalímetro",
    "barrera": "Barrera",
    "camara": "Cámara",
    "bomba_agua": "Bomba de agua",
    "turbina": "Turbina",
    "humidificador": "Humidificador",
}


class PanelEquipos(QWidget):
    """Recibe los datos del controlador con mostrar_lecturas() y mostrar_equipos()."""

    def __init__(self, titulo: str) -> None:
        super().__init__()
        self.estados: dict[str, QLabel] = {}

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
        fila_llama = QHBoxLayout()
        fila_llama.addWidget(self.llama, 1)
        fila_llama.addStretch(2)
        layout.addLayout(fila_llama)

        # Tarjeta con una fila por equipo, agrupados por sector
        self.tarjeta = QFrame()
        self.tarjeta.setProperty("tipo", "tarjeta")
        self.filas = QVBoxLayout(self.tarjeta)
        self.filas.setContentsMargins(18, 16, 18, 16)
        self.filas.setSpacing(8)
        titulo_equipos = QLabel("Estado de los equipos")
        titulo_equipos.setProperty("tipo", "etiqueta")
        self.sin_datos = QLabel("No hay equipos que mostrar.")
        self.sin_datos.setProperty("tipo", "nota")
        self.filas.addWidget(titulo_equipos)
        self.filas.addWidget(self.sin_datos)
        layout.addWidget(self.tarjeta)
        layout.addStretch()

    def mostrar_lecturas(self, lecturas: list[dict], hora: str = "") -> None:
        """De las lecturas solo usa la llama."""
        llama = next((x for x in lecturas if x["variable"] == "llama"), None)
        self.llama.actualizar(llama)
        if hora:
            self.actualizado.setText(f"Última actualización {hora}")

    def mostrar_equipos(self, equipos: list[dict]) -> None:
        """Solo crea filas nuevas si cambian los equipos."""
        if {e["nombre"] for e in equipos} != set(self.estados):
            self._crear_filas(equipos)
        for equipo in equipos:
            poner_estado(self.estados[equipo["nombre"]], *estado_equipo(equipo))
        self.sin_datos.setVisible(not equipos)

    def _crear_filas(self, equipos: list[dict]) -> None:
        # Borra todo menos el título y el aviso de sin datos
        while self.filas.count() > 2:
            item = self.filas.takeAt(2)
            if item.widget():
                item.widget().deleteLater()
        self.estados.clear()

        por_sector: dict[str, list[str]] = {}
        for equipo in equipos:
            por_sector.setdefault(equipo["sector"], []).append(equipo["nombre"])

        for sector in sorted(por_sector, key=lambda s: ORDEN_SECTORES.index(s)
                             if s in ORDEN_SECTORES else len(ORDEN_SECTORES)):
            titulo = QLabel(ETIQUETAS_SECTOR.get(sector, sector).upper())
            titulo.setProperty("tipo", "seccion")
            self.filas.addWidget(titulo)
            for nombre in por_sector[sector]:
                fila = QWidget()
                fila_layout = QHBoxLayout(fila)
                fila_layout.setContentsMargins(0, 2, 0, 2)
                fila_layout.addWidget(QLabel(ETIQUETAS_DISPOSITIVO.get(nombre, nombre)))
                fila_layout.addStretch()
                estado = QLabel()
                fila_layout.addWidget(estado)
                self.estados[nombre] = estado
                self.filas.addWidget(fila)


if __name__ == "__main__":
    # Demo con datos inventados: python -m app.view.panel_equipos
    import sys
    from datetime import datetime

    from PySide6.QtWidgets import QApplication

    from app.view.estilos import aplicar_estilos

    ahora = datetime.now()
    app = QApplication(sys.argv)
    aplicar_estilos(app)
    panel = PanelEquipos("Dispositivos")
    panel.mostrar_lecturas([{"variable": "llama", "unidad": "", "valor": 0,
                             "fecha_hora": ahora, "minimo_normal": None,
                             "maximo_normal": None, "sector": "critico"}],
                           ahora.strftime("%H:%M:%S"))
    panel.mostrar_equipos([
        {"nombre": "sensor_interior", "sector": "critico", "estado": "operativo"},
        {"nombre": "detector_llama", "sector": "critico", "estado": "a_revisar"},
        {"nombre": "turbina", "sector": "critico", "estado": "mantenimiento"},
    ])
    panel.resize(1134, 700)
    panel.show()
    sys.exit(app.exec())
