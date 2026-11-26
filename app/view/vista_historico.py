"""Histórico de una variable entre dos fechas, con gráfica y tabla."""

from datetime import datetime, timedelta

from PySide6.QtCharts import (
    QAreaSeries,
    QChart,
    QChartView,
    QDateTimeAxis,
    QLineSeries,
    QValueAxis,
)
from PySide6.QtCore import QDateTime, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateTimeEdit,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.view.estilos import PALETA
from app.view.panel_planta import ETIQUETAS_VARIABLE, formatear_numero

FORMATO_FECHA = "dd/MM/yyyy HH:mm"
# Botones para elegir rápido el periodo
PERIODOS = [("Últimas 24 h", timedelta(days=1)), ("7 días", timedelta(days=7)),
            ("30 días", timedelta(days=30))]

COLUMNAS = ["Fecha y hora", "Media", "Mínimo", "Máximo", "Lecturas"]
# La llama solo vale 0 o 1: basta con saber si hubo fuego en el tramo
COLUMNAS_LLAMA = ["Fecha y hora", "Fuego", "Lecturas"]

MENSAJE_FECHAS = "La fecha de inicio tiene que ser anterior a la de fin."
MENSAJE_VACIO = "No hay lecturas entre esas fechas."


def _ms(fecha: datetime) -> float:
    """Milisegundos desde 1970, que es lo que usa el eje de fechas."""
    return float(QDateTime(fecha).toMSecsSinceEpoch())


def _celda(texto: str, alineacion=Qt.AlignRight) -> QTableWidgetItem:
    celda = QTableWidgetItem(texto)
    celda.setTextAlignment(alineacion | Qt.AlignVCenter)
    return celda


class VistaHistorico(QWidget):
    """Emite abierta al mostrarse y consulta_pedida(variable, desde, hasta)."""

    abierta = Signal()
    consulta_pedida = Signal(str, object, object)

    def __init__(self, titulo: str) -> None:
        super().__init__()
        # Unidad y rango normal de cada variable, para la gráfica y la tabla
        self.variables: dict[str, dict] = {}
        self.variable_mostrada = ""
        # Líneas de la banda de la gráfica (ver _crear_grafica)
        self._lineas_banda: tuple = ()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        etiqueta = QLabel(titulo)
        etiqueta.setProperty("tipo", "titulo")
        layout.addWidget(etiqueta)
        layout.addWidget(self._filtros())

        self.mensaje = QLabel()
        self.mensaje.setProperty("tipo", "nota")
        layout.addWidget(self.mensaje)

        self.grafica = QChartView()
        self.grafica.setRenderHint(QPainter.Antialiasing)
        self.grafica.setMinimumHeight(320)
        layout.addWidget(self.grafica, 3)

        self.tabla = QTableWidget(0, len(COLUMNAS))
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.verticalHeader().hide()
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.tabla, 2)
        self.mostrar_historico([])

    def _filtros(self) -> QFrame:
        caja = QFrame()
        caja.setProperty("tipo", "tarjeta")
        fila = QHBoxLayout(caja)
        fila.setContentsMargins(18, 14, 18, 14)
        fila.setSpacing(10)

        self.selector_variable = QComboBox()
        self.selector_variable.setMinimumWidth(220)
        ahora = datetime.now().replace(second=0, microsecond=0)
        self.desde = self._selector_fecha(ahora - timedelta(days=1))
        self.hasta = self._selector_fecha(ahora)
        self.boton_consultar = QPushButton("Consultar")
        self.boton_consultar.setProperty("tipo", "primario")
        self.boton_consultar.clicked.connect(self.pedir_consulta)

        for texto, widget in (("Variable", self.selector_variable),
                              ("Desde", self.desde), ("Hasta", self.hasta)):
            nombre = QLabel(texto)
            nombre.setProperty("tipo", "etiqueta")
            fila.addWidget(nombre)
            fila.addWidget(widget)
        fila.addWidget(self.boton_consultar)
        fila.addStretch()

        for texto, periodo in PERIODOS:
            boton = QPushButton(texto)
            boton.setProperty("tipo", "secundario")
            boton.clicked.connect(lambda _=False, p=periodo: self.elegir_periodo(p))
            fila.addWidget(boton)
        return caja

    def _selector_fecha(self, fecha: datetime) -> QDateTimeEdit:
        selector = QDateTimeEdit(fecha)
        selector.setDisplayFormat(FORMATO_FECHA)
        selector.setCalendarPopup(True)
        return selector

    def showEvent(self, evento) -> None:
        super().showEvent(evento)
        # El controlador carga las variables al entrar en la sección
        self.abierta.emit()

    def poner_variables(self, lecturas: list[dict]) -> None:
        """Rellena el desplegable con las variables que ve el usuario."""
        nuevas = {lectura["variable"]: lectura for lectura in lecturas}
        if set(nuevas) == set(self.variables):
            return
        primera_vez = not self.variables
        self.variables = nuevas
        self.selector_variable.clear()
        for variable in nuevas:
            self.selector_variable.addItem(ETIQUETAS_VARIABLE.get(variable, variable), variable)
        # Al entrar por primera vez se enseñan ya las últimas 24 h
        if primera_vez and nuevas:
            self.pedir_consulta()

    def elegir_periodo(self, periodo: timedelta) -> None:
        ahora = datetime.now().replace(second=0, microsecond=0)
        self.desde.setDateTime(ahora - periodo)
        self.hasta.setDateTime(ahora)
        self.pedir_consulta()

    def pedir_consulta(self) -> None:
        variable = self.selector_variable.currentData()
        if variable is None:
            return
        desde = self.desde.dateTime().toPython()
        hasta = self.hasta.dateTime().toPython()
        if desde >= hasta:
            self.mostrar_error(MENSAJE_FECHAS)
            return
        self.variable_mostrada = variable
        self.consulta_pedida.emit(variable, desde, hasta)

    def mostrar_error(self, texto: str) -> None:
        self.mensaje.setProperty("tipo", "error")
        self.mensaje.setText(texto)
        self.mensaje.style().unpolish(self.mensaje)
        self.mensaje.style().polish(self.mensaje)

    def _mostrar_nota(self, texto: str) -> None:
        self.mensaje.setProperty("tipo", "nota")
        self.mensaje.setText(texto)
        self.mensaje.style().unpolish(self.mensaje)
        self.mensaje.style().polish(self.mensaje)

    def mostrar_historico(self, filas: list[dict]) -> None:
        """Pinta lo que devuelve historico_lecturas de la variable pedida."""
        info = self.variables.get(self.variable_mostrada, {})
        if self.variable_mostrada and not filas:
            self._mostrar_nota(MENSAJE_VACIO)
        elif filas:
            lecturas = sum(fila["lecturas"] for fila in filas)
            self._mostrar_nota(f"{lecturas} lecturas agrupadas en {len(filas)} tramos.")
        self._rellenar_tabla(filas, info)
        self.grafica.setChart(self._crear_grafica(filas, info))

    def _rellenar_tabla(self, filas: list[dict], info: dict) -> None:
        es_llama = self.variable_mostrada == "llama"
        columnas = COLUMNAS_LLAMA if es_llama else COLUMNAS
        unidad = info.get("unidad", "")
        self.tabla.setColumnCount(len(columnas))
        self.tabla.setHorizontalHeaderLabels(columnas)
        self.tabla.setRowCount(len(filas))
        for i, fila in enumerate(filas):
            fecha = fila["fecha_hora"].strftime("%d/%m/%Y %H:%M")
            if es_llama:
                textos = ["Sí" if fila["valor_maximo"] else "No"]
            else:
                textos = [f"{formatear_numero(fila[c])} {unidad}".strip()
                          for c in ("valor_medio", "valor_minimo", "valor_maximo")]
            self.tabla.setItem(i, 0, _celda(fecha, Qt.AlignLeft))
            # Sí o No se lee mejor centrado; los números, a la derecha
            alineacion = Qt.AlignCenter if es_llama else Qt.AlignRight
            for j, texto in enumerate(textos, start=1):
                self.tabla.setItem(i, j, _celda(texto, alineacion))
            self.tabla.setItem(i, len(textos) + 1, _celda(str(fila["lecturas"])))

    def _crear_grafica(self, filas: list[dict], info: dict) -> QChart:
        # QtCharts no lee a3i.qss: los colores se cogen de PALETA
        grafica = QChart()
        grafica.setBackgroundVisible(False)
        grafica.legend().setAlignment(Qt.AlignBottom)
        if not filas:
            grafica.legend().hide()
            return grafica

        es_llama = self.variable_mostrada == "llama"
        principal = QLineSeries()
        principal.setName("Fuego detectado" if es_llama else "Media")
        principal.setPen(QPen(QColor(PALETA["rojo" if es_llama else "azul_marino"]), 2))
        minimos, maximos = QLineSeries(), QLineSeries()
        for fila in filas:
            x = _ms(fila["fecha_hora"])
            valor = fila["valor_maximo"] if es_llama else fila["valor_medio"]
            principal.append(x, float(valor))
            minimos.append(x, float(fila["valor_minimo"]))
            maximos.append(x, float(fila["valor_maximo"]))

        series = [principal]
        if not es_llama:
            # Banda entre el mínimo y el máximo: los picos se ven aunque la media no los note
            banda = QAreaSeries(maximos, minimos)
            banda.setName("Mínimo y máximo")
            color = QColor(PALETA["turquesa"])
            color.setAlpha(60)
            banda.setBrush(color)
            banda.setPen(QPen(Qt.NoPen))
            series.insert(0, banda)
            # QAreaSeries no se queda con sus líneas: se guardan para que no se borren
            self._lineas_banda = (minimos, maximos)

        x_inicio, x_fin = _ms(filas[0]["fecha_hora"]), _ms(filas[-1]["fecha_hora"])
        limites = []
        for clave in ("minimo_normal", "maximo_normal"):
            if info.get(clave) is not None:
                limite = QLineSeries()
                limite.setName("Rango normal")
                pen = QPen(QColor(PALETA["verde"]), 1, Qt.DashLine)
                limite.setPen(pen)
                limite.append(x_inicio, float(info[clave]))
                limite.append(x_fin, float(info[clave]))
                limites.append(limite)
        series += limites

        eje_x = QDateTimeAxis()
        dias = (filas[-1]["fecha_hora"] - filas[0]["fecha_hora"]).days
        eje_x.setFormat("HH:mm" if dias < 1 else "dd/MM HH:mm")
        eje_x.setTickCount(7)
        eje_y = QValueAxis()
        eje_y.setLabelFormat("%.0f" if es_llama else "%.1f")
        if es_llama:
            eje_y.setRange(0, 1)
            eje_y.setTickCount(2)
        else:
            valores = [float(f[c]) for f in filas for c in ("valor_minimo", "valor_maximo")]
            valores += [float(info[c]) for c in ("minimo_normal", "maximo_normal")
                        if info.get(c) is not None]
            margen = (max(valores) - min(valores)) * 0.1 or 1
            eje_y.setRange(min(valores) - margen, max(valores) + margen)
            if info.get("unidad"):
                eje_y.setTitleText(info["unidad"])
        grafica.addAxis(eje_x, Qt.AlignBottom)
        grafica.addAxis(eje_y, Qt.AlignLeft)

        for serie in series:
            grafica.addSeries(serie)
            serie.attachAxis(eje_x)
            serie.attachAxis(eje_y)
        # El rango normal son dos líneas, pero en la leyenda sale una vez
        if len(limites) == 2:
            grafica.legend().markers(limites[1])[0].setVisible(False)
        return grafica


if __name__ == "__main__":
    # Demo con datos inventados: python -m app.view.vista_historico
    import math
    import random
    import sys
    from decimal import Decimal

    from PySide6.QtWidgets import QApplication

    from app.view.estilos import aplicar_estilos

    def historico_inventado(variable: str, desde: datetime, hasta: datetime) -> list[dict]:
        filas = []
        paso = (hasta - desde) / 100
        for i in range(100):
            fecha = desde + paso * i
            if variable == "llama":
                maximo = 1 if i in (40, 41) else 0
                filas.append({"fecha_hora": fecha, "valor_medio": Decimal(maximo),
                              "valor_minimo": Decimal(0), "valor_maximo": Decimal(maximo),
                              "lecturas": 12})
                continue
            media = 11.5 + 1.5 * math.sin(i / 8) + (3.5 if i in (60, 61) else 0)
            ruido = random.uniform(0.2, 0.8)
            filas.append({"fecha_hora": fecha, "valor_medio": Decimal(f"{media:.2f}"),
                          "valor_minimo": Decimal(f"{media - ruido:.2f}"),
                          "valor_maximo": Decimal(f"{media + ruido:.2f}"), "lecturas": 12})
        return filas

    app = QApplication(sys.argv)
    aplicar_estilos(app)
    vista = VistaHistorico("Histórico")
    vista.consulta_pedida.connect(
        lambda v, d, h: vista.mostrar_historico(historico_inventado(v, d, h)))
    vista.poner_variables([
        {"variable": "caudal", "unidad": "L/min",
         "minimo_normal": Decimal(8), "maximo_normal": Decimal(15)},
        {"variable": "llama", "unidad": "", "minimo_normal": None, "maximo_normal": None},
    ])
    vista.resize(1134, 760)
    vista.show()
    sys.exit(app.exec())
