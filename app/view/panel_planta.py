"""Panel con la última lectura de cada variable, agrupadas por sector."""

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

# Texto que se muestra para cada valor de la BD
ETIQUETAS_VARIABLE = {
    "temperatura_interior": "Temperatura interior",
    "humedad_interior": "Humedad interior",
    "temperatura_ambiente": "Temperatura ambiente",
    "humedad_ambiente": "Humedad ambiente",
    "calidad_aire": "Calidad del aire",
    "caudal": "Caudal de agua",
    "llama": "Detector de llama",
}
ETIQUETAS_SECTOR = {
    "general": "Sector 1 · General",
    "cientifico": "Sector 2 · Científico",
    "critico": "Sector 3 · Crítico",
}
ORDEN_SECTORES = ["general", "cientifico", "critico"]
COLUMNAS = 4


def estado_lectura(lectura: dict | None) -> tuple[str, str]:
    """Devuelve el estado de la etiqueta (ok, alarma, neutro) y su texto."""
    if lectura is None or lectura.get("valor") is None:
        return "neutro", "Sin datos"
    valor = lectura["valor"]
    if lectura["variable"] == "llama":
        return ("alarma", "Fuego detectado") if valor else ("ok", "Normal")

    minimo, maximo = lectura.get("minimo_normal"), lectura.get("maximo_normal")
    if (minimo is not None and valor < minimo) or (maximo is not None and valor > maximo):
        return "alarma", "Fuera de rango"
    return "ok", "Normal"


def poner_estado(etiqueta: QLabel, estado: str, texto: str) -> None:
    """Cambia el texto y el color de una etiqueta de estado."""
    etiqueta.setText(texto)
    etiqueta.setProperty("estado", estado)
    # Qt no vuelve a aplicar el estilo solo al cambiar una propiedad
    etiqueta.style().unpolish(etiqueta)
    etiqueta.style().polish(etiqueta)


def formatear_numero(valor) -> str:
    """Número con coma decimal y sin decimales si es entero (650 ppm, 41,5 %)."""
    if valor == int(valor):
        return str(int(valor))
    return f"{valor:.1f}".replace(".", ",")


def texto_valor(lectura: dict) -> str:
    if lectura["variable"] == "llama":
        return "Fuego" if lectura["valor"] else "Sin fuego"
    return f"{formatear_numero(lectura['valor'])} {lectura['unidad']}"


def texto_detalle(lectura: dict) -> str:
    partes = []
    if lectura.get("minimo_normal") is not None:
        minimo = formatear_numero(lectura["minimo_normal"])
        maximo = formatear_numero(lectura["maximo_normal"])
        partes.append(f"Normal {minimo}–{maximo}")
    if lectura.get("fecha_hora") is not None:
        partes.append(lectura["fecha_hora"].strftime("%H:%M:%S"))
    return " · ".join(partes)


class TarjetaVariable(QFrame):
    """Tarjeta con el nombre, el valor y el estado de una variable."""

    def __init__(self, variable: str) -> None:
        super().__init__()
        self.setProperty("tipo", "tarjeta")
        self.setMinimumWidth(220)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(6)

        nombre = QLabel(ETIQUETAS_VARIABLE.get(variable, variable))
        nombre.setProperty("tipo", "etiqueta")
        self.valor = QLabel("—")
        self.valor.setProperty("tipo", "valor")
        self.detalle = QLabel()
        self.detalle.setProperty("tipo", "nota")
        self.estado = QLabel()

        fila_estado = QHBoxLayout()
        fila_estado.addWidget(self.estado)
        fila_estado.addStretch()

        layout.addWidget(nombre)
        layout.addWidget(self.valor)
        layout.addWidget(self.detalle)
        layout.addLayout(fila_estado)
        self.actualizar(None)

    def actualizar(self, lectura: dict | None) -> None:
        poner_estado(self.estado, *estado_lectura(lectura))
        if lectura is not None and lectura.get("valor") is not None:
            self.valor.setText(texto_valor(lectura))
            self.detalle.setText(texto_detalle(lectura))


class PanelPlanta(QWidget):
    """Muestra las lecturas que le pasa el controlador con mostrar_lecturas()."""

    def __init__(self, titulo: str) -> None:
        super().__init__()
        self.tarjetas: dict[str, TarjetaVariable] = {}

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

        scroll = QScrollArea()
        scroll.setProperty("tipo", "panel")
        scroll.setWidgetResizable(True)
        self.contenido = QWidget()
        self.secciones = QVBoxLayout(self.contenido)
        self.secciones.setContentsMargins(0, 0, 0, 0)
        self.secciones.setSpacing(12)
        scroll.setWidget(self.contenido)
        layout.addWidget(scroll, 1)

        self.sin_datos = QLabel("Todavía no hay lecturas.")
        self.sin_datos.setProperty("tipo", "subtitulo")
        self.secciones.addWidget(self.sin_datos)
        self.secciones.addStretch()

    def mostrar_lecturas(self, lecturas: list[dict], hora: str = "") -> None:
        """Pinta las lecturas. Solo crea tarjetas nuevas si cambian las variables."""
        variables = {lectura["variable"] for lectura in lecturas}
        if variables != set(self.tarjetas):
            self._crear_tarjetas(lecturas)
        for lectura in lecturas:
            self.tarjetas[lectura["variable"]].actualizar(lectura)
        self.sin_datos.setVisible(not lecturas)
        if hora:
            self.actualizado.setText(f"Última actualización {hora}")

    def _crear_tarjetas(self, lecturas: list[dict]) -> None:
        # Borra todo menos el aviso de sin datos y el stretch del final
        while self.secciones.count() > 2:
            item = self.secciones.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
        self.tarjetas.clear()

        por_sector: dict[str, list[str]] = {}
        for lectura in lecturas:
            por_sector.setdefault(lectura["sector"], []).append(lectura["variable"])

        posicion = 1
        for sector in sorted(por_sector, key=lambda s: ORDEN_SECTORES.index(s)
                             if s in ORDEN_SECTORES else len(ORDEN_SECTORES)):
            titulo = QLabel(ETIQUETAS_SECTOR.get(sector, sector).upper())
            titulo.setProperty("tipo", "seccion")
            self.secciones.insertWidget(posicion, titulo)

            rejilla = QWidget()
            grid = QGridLayout(rejilla)
            grid.setContentsMargins(0, 0, 0, 12)
            grid.setSpacing(16)
            for i, variable in enumerate(por_sector[sector]):
                tarjeta = TarjetaVariable(variable)
                self.tarjetas[variable] = tarjeta
                grid.addWidget(tarjeta, i // COLUMNAS, i % COLUMNAS)
            for columna in range(COLUMNAS):
                grid.setColumnStretch(columna, 1)
            self.secciones.insertWidget(posicion + 1, rejilla)
            posicion += 2


if __name__ == "__main__":
    # Demo con datos inventados: python -m app.view.panel_planta
    import sys
    from datetime import datetime
    from decimal import Decimal

    from PySide6.QtWidgets import QApplication

    from app.view.estilos import aplicar_estilos

    ahora = datetime.now()
    ejemplo = [
        ("temperatura_interior", "°C", "58.4", 40, 70, "critico"),
        ("humedad_interior", "%", "41.0", 30, 50, "critico"),
        ("llama", "", "0", None, None, "critico"),
        ("temperatura_ambiente", "°C", "27.3", 18, 26, "cientifico"),
        ("humedad_ambiente", "%", "52.5", 40, 60, "cientifico"),
        ("calidad_aire", "ppm", "650", 400, 900, "cientifico"),
        ("caudal", "L/min", "11.2", 8, 15, "cientifico"),
    ]
    lecturas = [
        {"variable": v, "unidad": u, "valor": Decimal(valor), "fecha_hora": ahora,
         "minimo_normal": mn, "maximo_normal": mx, "sector": s}
        for v, u, valor, mn, mx, s in ejemplo
    ]

    app = QApplication(sys.argv)
    aplicar_estilos(app)
    panel = PanelPlanta("Panel de planta")
    panel.mostrar_lecturas(lecturas, ahora.strftime("%H:%M:%S"))
    panel.resize(1134, 700)
    panel.show()
    sys.exit(app.exec())
