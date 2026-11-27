"""Avisos y alarmas: tablero To do / Doing / Done con el detalle de la alerta elegida."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.view.panel_planta import (
    ETIQUETAS_SECTOR,
    ETIQUETAS_VARIABLE,
    formatear_numero,
    poner_estado,
    texto_valor,
)

# Columnas del tablero y estados de la alerta que van en cada una
COLUMNAS = [
    ("To do", ("pendiente",)),
    ("Doing", ("en_curso", "por_revisar")),
    ("Done", ("resuelta",)),
]
ETIQUETAS_ESTADO = {
    "pendiente": "Pendiente",
    "en_curso": "En curso",
    "por_revisar": "Por revisar",
    "resuelta": "Resuelta",
}
ETIQUETAS_TIPO = {"aviso": "Aviso", "alarma": "Alarma"}

# Cuánto tiempo atrás se ven las resueltas
PERIODOS_DONE = [("Últimas 24 h", 24), ("Últimos 7 días", 24 * 7), ("Últimos 30 días", 24 * 30)]

# Botones de cada estado. Se gestionan en el Sprint 4
BOTONES = {
    "pendiente": ["Asignar", "Crear solicitud"],
    "en_curso": ["Terminada", "Crear solicitud"],
    "por_revisar": ["Resolver", "Devolver"],
    "resuelta": [],
}
AVISO_SPRINT4 = "Disponible en el Sprint 4"


def _fecha(fecha) -> str:
    return fecha.strftime("%d/%m/%Y %H:%M") if fecha else "—"


def texto_lectura(alerta: dict, columna_valor: str = "valor") -> str:
    """Valor con su unidad; en la llama, si hubo fuego."""
    return texto_valor({"variable": alerta["variable"], "valor": alerta[columna_valor],
                        "unidad": alerta["unidad"]})


def estado_etiqueta(alerta: dict) -> str:
    """Color de la etiqueta: las resueltas en gris, el resto según el tipo."""
    return "neutro" if alerta["estado"] == "resuelta" else alerta["tipo"]


class TarjetaAlerta(QFrame):
    """Una alerta del tablero. Al pulsarla emite pulsada con su id."""

    pulsada = Signal(int)

    def __init__(self, alerta: dict) -> None:
        super().__init__()
        self.id_alerta = alerta["id_alerta"]
        self.setProperty("tipo", "tarjeta")
        self.setCursor(Qt.PointingHandCursor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        fila = QHBoxLayout()
        tipo = QLabel()
        poner_estado(tipo, estado_etiqueta(alerta), ETIQUETAS_TIPO[alerta["tipo"]])
        fila.addWidget(tipo)
        if alerta["estado"] == "por_revisar":
            marca = QLabel("Por revisar")
            marca.setProperty("tipo", "nota")
            fila.addWidget(marca)
        fila.addStretch()
        layout.addLayout(fila)

        nombre = QLabel(ETIQUETAS_VARIABLE.get(alerta["variable"], alerta["variable"]))
        nombre.setProperty("tipo", "etiqueta")
        layout.addWidget(nombre)
        # Si un aviso subió a alarma, se enseña la lectura de la alarma
        if alerta["valor_alarma"] is not None:
            lectura = f"{texto_lectura(alerta, 'valor_alarma')} · {_fecha(alerta['fecha_alarma'])}"
        else:
            lectura = f"{texto_lectura(alerta)} · {_fecha(alerta['fecha_hora'])}"
        detalle = QLabel(lectura)
        detalle.setProperty("tipo", "nota")
        layout.addWidget(detalle)
        if alerta["encargado"]:
            encargado = QLabel(f"Encargado: {alerta['encargado']}")
            encargado.setProperty("tipo", "nota")
            layout.addWidget(encargado)

    def marcar(self, seleccionada: bool) -> None:
        self.setProperty("seleccionada", seleccionada)
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, evento) -> None:
        self.pulsada.emit(self.id_alerta)
        super().mousePressEvent(evento)


class VistaAlertas(QWidget):
    """Muestra lo que le pasa el controlador con mostrar_alertas().

    Emite horas_cambiadas cuando se elige otro periodo para Done.
    """

    horas_cambiadas = Signal(int)

    def __init__(self, titulo: str) -> None:
        super().__init__()
        self.alertas: list[dict] = []
        self.tarjetas: dict[int, TarjetaAlerta] = {}
        self.seleccionada: int | None = None

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

        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(16)
        tablero = QGridLayout()
        tablero.setHorizontalSpacing(16)
        self.cabeceras: list[QLabel] = []
        self.columnas: list[QVBoxLayout] = []
        for i, (nombre, _) in enumerate(COLUMNAS):
            fila_titulo = QHBoxLayout()
            titulo_columna = QLabel(nombre.upper())
            titulo_columna.setProperty("tipo", "seccion")
            fila_titulo.addWidget(titulo_columna)
            fila_titulo.addStretch()
            if nombre == "Done":
                self.periodo = QComboBox()
                for texto, horas in PERIODOS_DONE:
                    self.periodo.addItem(texto, horas)
                self.periodo.currentIndexChanged.connect(self._cambiar_periodo)
                fila_titulo.addWidget(self.periodo)
            self.cabeceras.append(titulo_columna)
            tablero.addLayout(fila_titulo, 0, i)

            scroll = QScrollArea()
            scroll.setProperty("tipo", "panel")
            scroll.setWidgetResizable(True)
            contenido = QWidget()
            columna = QVBoxLayout(contenido)
            columna.setContentsMargins(0, 0, 0, 0)
            columna.setSpacing(10)
            columna.addStretch()
            scroll.setWidget(contenido)
            tablero.addWidget(scroll, 1, i)
            tablero.setColumnStretch(i, 1)
            self.columnas.append(columna)
        tablero.setRowStretch(1, 1)
        cuerpo.addLayout(tablero, 1)
        cuerpo.addWidget(self._detalle())
        layout.addLayout(cuerpo, 1)
        self.mostrar_alertas([])

    def _detalle(self) -> QFrame:
        caja = QFrame()
        caja.setProperty("tipo", "tarjeta")
        caja.setFixedWidth(300)
        layout = QVBoxLayout(caja)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        titulo = QLabel("DETALLE")
        titulo.setProperty("tipo", "seccion")
        layout.addWidget(titulo)
        self.texto_detalle = QLabel("Pulsa una alerta para ver el detalle.")
        self.texto_detalle.setProperty("tipo", "nota")
        self.texto_detalle.setWordWrap(True)
        self.texto_detalle.setTextFormat(Qt.PlainText)
        layout.addWidget(self.texto_detalle)
        layout.addStretch()

        # Todos los botones existen; se enseñan los del estado de la alerta
        self.botones: dict[str, QPushButton] = {}
        for texto in ("Asignar", "Terminada", "Resolver", "Devolver", "Crear solicitud"):
            boton = QPushButton(texto)
            boton.setProperty("tipo", "secundario")
            boton.setEnabled(False)
            boton.setToolTip(AVISO_SPRINT4)
            boton.hide()
            layout.addWidget(boton)
            self.botones[texto] = boton
        return caja

    def _cambiar_periodo(self) -> None:
        self.horas_cambiadas.emit(self.periodo.currentData())

    def mostrar_alertas(self, alertas: list[dict], hora: str = "") -> None:
        """Pinta el tablero. Si no ha cambiado nada no lo rehace, para no perder el scroll."""
        if hora:
            self.actualizado.setText(f"Última actualización {hora}")
        if self.tarjetas and alertas == self.alertas:
            return
        self.alertas = alertas
        self.tarjetas.clear()
        for i, (nombre, estados) in enumerate(COLUMNAS):
            columna = self.columnas[i]
            # Deja solo el stretch del final
            while columna.count() > 1:
                item = columna.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            de_la_columna = [a for a in alertas if a["estado"] in estados]
            self.cabeceras[i].setText(f"{nombre.upper()} · {len(de_la_columna)}")
            for posicion, alerta in enumerate(de_la_columna):
                tarjeta = TarjetaAlerta(alerta)
                tarjeta.pulsada.connect(self.seleccionar)
                self.tarjetas[alerta["id_alerta"]] = tarjeta
                columna.insertWidget(posicion, tarjeta)
            if not de_la_columna:
                vacia = QLabel("Sin alertas.")
                vacia.setProperty("tipo", "nota")
                columna.insertWidget(0, vacia)

        # Si la elegida ya no está (p. ej. resuelta hace más del periodo), se limpia
        if self.seleccionada not in self.tarjetas:
            self.seleccionada = None
        self.seleccionar(self.seleccionada)

    def seleccionar(self, id_alerta: int | None) -> None:
        self.seleccionada = id_alerta
        for id_tarjeta, tarjeta in self.tarjetas.items():
            tarjeta.marcar(id_tarjeta == id_alerta)
        alerta = next((a for a in self.alertas if a["id_alerta"] == id_alerta), None)
        for boton in self.botones.values():
            boton.hide()
        if alerta is None:
            self.texto_detalle.setText("Pulsa una alerta para ver el detalle.")
            return
        self.texto_detalle.setText(self.texto_alerta(alerta))
        for texto in BOTONES[alerta["estado"]]:
            self.botones[texto].show()

    @staticmethod
    def texto_alerta(alerta: dict) -> str:
        lineas = [
            ETIQUETAS_VARIABLE.get(alerta["variable"], alerta["variable"]),
            ETIQUETAS_SECTOR.get(alerta["sector"], alerta["sector"]),
            "",
            f"Tipo: {ETIQUETAS_TIPO[alerta['tipo']]}",
            f"Estado: {ETIQUETAS_ESTADO[alerta['estado']]}",
            f"Valor: {texto_lectura(alerta)}",
            f"Fecha: {_fecha(alerta['fecha_hora'])}",
        ]
        if alerta["valor_alarma"] is not None:
            lineas.append(f"Subió a alarma: {texto_lectura(alerta, 'valor_alarma')} "
                          f"el {_fecha(alerta['fecha_alarma'])}")
        if alerta["minimo_normal"] is not None:
            lineas.append(f"Rango normal: {formatear_numero(alerta['minimo_normal'])}–"
                          f"{formatear_numero(alerta['maximo_normal'])} {alerta['unidad']}")
        lineas.append(f"Encargado: {alerta['encargado'] or 'sin asignar'}")
        if alerta["motivo_devolucion"]:
            lineas.append(f"Devuelta: {alerta['motivo_devolucion']}")
        if alerta["estado"] == "resuelta":
            lineas.append(f"Resuelta por {alerta['revisor'] or '—'} "
                          f"el {_fecha(alerta['fecha_resolucion'])}")
        return "\n".join(lineas)


if __name__ == "__main__":
    # Demo con datos inventados: python -m app.view.vista_alertas
    import sys
    from datetime import datetime, timedelta
    from decimal import Decimal

    from PySide6.QtWidgets import QApplication

    from app.view.estilos import aplicar_estilos

    ahora = datetime.now()

    def alerta(id_alerta, variable, unidad, tipo, estado, valor, horas, **extra) -> dict:
        datos = {
            "id_alerta": id_alerta, "variable": variable, "unidad": unidad,
            "sector": "critico" if variable == "llama" else "cientifico",
            "tipo": tipo, "estado": estado, "valor": Decimal(valor),
            "fecha_hora": ahora - timedelta(hours=horas), "valor_alarma": None,
            "fecha_alarma": None, "minimo_normal": Decimal(8), "maximo_normal": Decimal(15),
            "encargado": None, "fecha_asignacion": None, "fecha_terminada": None,
            "motivo_devolucion": None, "revisor": None, "fecha_resolucion": None,
        }
        datos.update(extra)
        return datos

    app = QApplication(sys.argv)
    aplicar_estilos(app)
    vista = VistaAlertas("Avisos y alarmas")
    vista.mostrar_alertas([
        alerta(1, "caudal", "L/min", "alarma", "pendiente", "5.5", 1,
               valor_alarma=Decimal("5.5"), fecha_alarma=ahora),
        alerta(2, "calidad_aire", "ppm", "aviso", "pendiente", "860", 2,
               minimo_normal=Decimal(400), maximo_normal=Decimal(900)),
        alerta(3, "humedad_ambiente", "%", "aviso", "por_revisar", "41.5", 5,
               encargado="Lucía Herrera", minimo_normal=Decimal(40), maximo_normal=Decimal(60)),
        alerta(4, "llama", "", "alarma", "resuelta", "1", 20, minimo_normal=None,
               maximo_normal=None, revisor="Andrés Romero",
               fecha_resolucion=ahora - timedelta(hours=19)),
    ], ahora.strftime("%H:%M:%S"))
    vista.resize(1134, 700)
    vista.show()
    sys.exit(app.exec())
