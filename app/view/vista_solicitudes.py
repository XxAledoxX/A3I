"""Mis solicitudes: formulario para pedir una nueva y lista de las propias."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.view.panel_equipos import ETIQUETAS_DISPOSITIVO
from app.view.panel_planta import ETIQUETAS_SECTOR, poner_estado

# Texto que se muestra para cada tipo de la BD
ETIQUETAS_TIPO = {
    "cambio_equipo": "Cambio en un equipo",
    "mantenimiento": "Mantenimiento",
    "revision": "Revisión",
    "accion_restringida": "Acción restringida",
    "alta_usuario": "Alta de usuario",
    "baja_usuario": "Baja de usuario",
    "modificacion_usuario": "Modificación de usuario",
    "cambio_nivel": "Cambio de nivel",
    "acceso_sector": "Acceso a un sector",
}
# Tipos que cada perfil puede pedir desde esta pantalla
TIPOS_PERFIL = {
    "tech": ["cambio_equipo", "mantenimiento", "revision", "acceso_sector"],
    "cientificos": ["revision", "acceso_sector"],
    "seguridad": ["revision", "acceso_sector"],
}
PRIORIDADES = [("baja", "Baja"), ("normal", "Normal"), ("alta", "Alta")]

ETIQUETAS_ESTADO = {
    "pendiente": "Pendiente",
    "aceptada": "Aceptada",
    "rechazada": "Rechazada",
    "cancelada": "Cancelada",
    "caducada": "Caducada",
}
COLORES_ESTADO = {"aceptada": "ok", "rechazada": "alarma"}

COLUMNAS = ["Fecha", "Tipo", "Dispositivo", "Sector", "Estado", "Aprobaciones", ""]
APROBACIONES_NECESARIAS = 2
DURACION_POR_DEFECTO = 60

# Primera opción de los desplegables: obliga a elegir
SIN_ELEGIR = "---"

MENSAJE_ENVIADA = "Solicitud enviada."
MENSAJE_TIPO = "Elige el tipo"
MENSAJE_SECTOR = "Elige el sector"
MENSAJE_DISPOSITIVO = "Elige el dispositivo"
MENSAJE_VACIA = "Todavía no has hecho ninguna solicitud."
PREGUNTA_CANCELAR = "¿Cancelar la solicitud?"


def _celda(texto: str) -> QTableWidgetItem:
    celda = QTableWidgetItem(texto)
    celda.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    return celda


class VistaSolicitudes(QWidget):
    """Emite abierta, actualizar_pedido, sector_elegido(id), envio_pedido y
    cancelacion_pedida(id). El controlador le pasa los datos con poner_* y mostrar_*."""

    abierta = Signal()
    actualizar_pedido = Signal()
    sector_elegido = Signal(int)
    # tipo, prioridad, motivo, id_sector, duración, id_dispositivo (o None)
    envio_pedido = Signal(str, str, str, int, int, object)
    cancelacion_pedida = Signal(int)

    def __init__(self, titulo: str, perfil: str) -> None:
        super().__init__()
        self.perfil = perfil

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(16)

        etiqueta = QLabel(titulo)
        etiqueta.setProperty("tipo", "titulo")
        layout.addWidget(etiqueta)
        layout.addWidget(self._formulario())

        self.mensaje = QLabel()
        self.mensaje.setProperty("tipo", "nota")
        self.mensaje.setWordWrap(True)
        layout.addWidget(self.mensaje)

        layout.addWidget(self._lista(), 1)
        self._tipo_cambiado()

    def _formulario(self) -> QFrame:
        caja = QFrame()
        caja.setProperty("tipo", "tarjeta")
        rejilla = QGridLayout(caja)
        rejilla.setContentsMargins(18, 14, 18, 14)
        rejilla.setHorizontalSpacing(10)
        rejilla.setVerticalSpacing(10)

        seccion = QLabel("Nueva solicitud")
        seccion.setProperty("tipo", "seccion")
        rejilla.addWidget(seccion, 0, 0, 1, 6)

        self.selector_tipo = QComboBox()
        self.selector_tipo.addItem(SIN_ELEGIR, None)
        for tipo in TIPOS_PERFIL.get(self.perfil, []):
            self.selector_tipo.addItem(ETIQUETAS_TIPO[tipo], tipo)
        self.selector_tipo.currentIndexChanged.connect(self._tipo_cambiado)

        self.selector_sector = QComboBox()
        self.selector_sector.addItem(SIN_ELEGIR, None)
        self.selector_sector.currentIndexChanged.connect(self._sector_cambiado)
        self.selector_dispositivo = QComboBox()
        self.selector_dispositivo.setMinimumWidth(240)
        self.selector_dispositivo.addItem(SIN_ELEGIR, None)

        self.selector_prioridad = QComboBox()
        for prioridad, texto in PRIORIDADES:
            self.selector_prioridad.addItem(texto, prioridad)
        self.selector_prioridad.setCurrentIndex(1)

        # El máximo lo comprueba la BD (parametro duracion_max_min)
        self.duracion = QSpinBox()
        self.duracion.setRange(1, 9999)
        self.duracion.setValue(DURACION_POR_DEFECTO)
        self.duracion.setSuffix(" min")

        self.motivo = QLineEdit()
        self.motivo.setMaxLength(255)
        self.motivo.setPlaceholderText("Para qué hace falta")

        self.boton_enviar = QPushButton("Enviar")
        self.boton_enviar.setProperty("tipo", "primario")
        self.boton_enviar.clicked.connect(self.pedir_envio)

        campos = [("Tipo", self.selector_tipo), ("Sector", self.selector_sector),
                  ("Dispositivo", self.selector_dispositivo),
                  ("Prioridad", self.selector_prioridad),
                  ("Duración en minutos", self.duracion)]
        for i, (texto, widget) in enumerate(campos):
            fila, columna = 1 + i // 3, (i % 3) * 2
            nombre = QLabel(texto)
            nombre.setProperty("tipo", "etiqueta")
            rejilla.addWidget(nombre, fila, columna)
            rejilla.addWidget(widget, fila, columna + 1)

        nombre = QLabel("Motivo")
        nombre.setProperty("tipo", "etiqueta")
        rejilla.addWidget(nombre, 3, 0)
        rejilla.addWidget(self.motivo, 3, 1, 1, 4)
        rejilla.addWidget(self.boton_enviar, 3, 5)
        return caja

    def _lista(self) -> QFrame:
        caja = QFrame()
        caja.setProperty("tipo", "tarjeta")
        columna = QVBoxLayout(caja)
        columna.setContentsMargins(18, 14, 18, 14)
        columna.setSpacing(10)

        cabecera = QHBoxLayout()
        seccion = QLabel("Mis solicitudes")
        seccion.setProperty("tipo", "seccion")
        self.boton_actualizar = QPushButton("Actualizar")
        self.boton_actualizar.setProperty("tipo", "secundario")
        self.boton_actualizar.clicked.connect(self.actualizar_pedido.emit)
        cabecera.addWidget(seccion)
        cabecera.addStretch()
        cabecera.addWidget(self.boton_actualizar)
        columna.addLayout(cabecera)

        self.vacia = QLabel(MENSAJE_VACIA)
        self.vacia.setProperty("tipo", "nota")
        columna.addWidget(self.vacia)

        self.tabla = QTableWidget(0, len(COLUMNAS))
        self.tabla.setHorizontalHeaderLabels(COLUMNAS)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setSelectionMode(QAbstractItemView.NoSelection)
        self.tabla.verticalHeader().hide()
        # Una línea por fila y cada columna al ancho de su contenido; si no cabe, scroll
        self.tabla.setWordWrap(False)
        self.tabla.setTextElideMode(Qt.ElideNone)
        self.tabla.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        columna.addWidget(self.tabla, 1)
        return caja

    def showEvent(self, evento) -> None:
        super().showEvent(evento)
        # El controlador carga sectores y solicitudes al entrar en la sección
        self.abierta.emit()

    def _tipo_cambiado(self) -> None:
        # El acceso a un sector no lleva dispositivo
        con_dispositivo = self.selector_tipo.currentData() != "acceso_sector"
        if not con_dispositivo:
            self.selector_dispositivo.setCurrentIndex(0)
        self.selector_dispositivo.setEnabled(con_dispositivo)

    def _sector_cambiado(self) -> None:
        self._vaciar_dispositivos()
        id_sector = self.selector_sector.currentData()
        if id_sector is not None:
            self.sector_elegido.emit(id_sector)

    def poner_sectores(self, filas: list[dict]) -> None:
        """Rellena el desplegable de sectores; si no han cambiado, no lo toca."""
        actuales = [self.selector_sector.itemData(i)
                    for i in range(1, self.selector_sector.count())]
        if actuales == [fila["id_sector"] for fila in filas]:
            return
        self.selector_sector.clear()
        self.selector_sector.addItem(SIN_ELEGIR, None)
        for fila in filas:
            texto = ETIQUETAS_SECTOR.get(fila["nombre"], fila["nombre"])
            self.selector_sector.addItem(texto, fila["id_sector"])

    def _vaciar_dispositivos(self) -> None:
        self.selector_dispositivo.clear()
        self.selector_dispositivo.addItem(SIN_ELEGIR, None)

    def poner_dispositivos(self, filas: list[dict]) -> None:
        self._vaciar_dispositivos()
        for fila in filas:
            texto = ETIQUETAS_DISPOSITIVO.get(fila["nombre"], fila["nombre"])
            self.selector_dispositivo.addItem(texto, fila["id_dispositivo"])

    def pedir_envio(self) -> None:
        """Si falta algo por elegir, avisa sin llamar a la BD."""
        tipo = self.selector_tipo.currentData()
        id_sector = self.selector_sector.currentData()
        id_dispositivo = self.selector_dispositivo.currentData()
        if tipo is None:
            self.mostrar_error(MENSAJE_TIPO)
            return
        if id_sector is None:
            self.mostrar_error(MENSAJE_SECTOR)
            return
        if tipo != "acceso_sector" and id_dispositivo is None:
            self.mostrar_error(MENSAJE_DISPOSITIVO)
            return
        if tipo == "acceso_sector":
            id_dispositivo = None
        self.envio_pedido.emit(tipo, self.selector_prioridad.currentData(),
                               self.motivo.text(), id_sector, self.duracion.value(),
                               id_dispositivo)

    def solicitud_creada(self) -> None:
        self.motivo.clear()
        self._poner_mensaje("nota", MENSAJE_ENVIADA)

    def mostrar_error(self, texto: str) -> None:
        self._poner_mensaje("error", texto)

    def _poner_mensaje(self, tipo: str, texto: str) -> None:
        self.mensaje.setProperty("tipo", tipo)
        self.mensaje.setText(texto)
        self.mensaje.style().unpolish(self.mensaje)
        self.mensaje.style().polish(self.mensaje)

    def mostrar_solicitudes(self, filas: list[dict]) -> None:
        """Pinta lo que devuelve mis_solicitudes."""
        self.vacia.setVisible(not filas)
        self.tabla.setRowCount(len(filas))
        for i, fila in enumerate(filas):
            dispositivo = fila["dispositivo"]
            textos = [
                fila["fecha_creacion"].strftime("%d/%m/%Y %H:%M"),
                ETIQUETAS_TIPO.get(fila["tipo"], fila["tipo"]),
                ETIQUETAS_DISPOSITIVO.get(dispositivo, dispositivo) if dispositivo else "—",
                ETIQUETAS_SECTOR.get(fila["sector"], fila["sector"]),
            ]
            for j, texto in enumerate(textos):
                self.tabla.setItem(i, j, _celda(texto))

            estado = QLabel()
            poner_estado(estado, COLORES_ESTADO.get(fila["estado"], "neutro"),
                         ETIQUETAS_ESTADO.get(fila["estado"], fila["estado"]))
            self.tabla.setCellWidget(i, 4, self._centrado(estado))
            self.tabla.setItem(
                i, 5, _celda(f"{fila['aprobaciones']} de {APROBACIONES_NECESARIAS}"))

            if fila["estado"] == "pendiente":
                boton = QPushButton("Cancelar")
                boton.setProperty("tipo", "peligro")
                boton.clicked.connect(
                    lambda _=False, s=fila["id_solicitud"]: self.pedir_cancelacion(s))
                self.tabla.setCellWidget(i, 6, self._centrado(boton))
            else:
                self.tabla.removeCellWidget(i, 6)
        self.tabla.resizeRowsToContents()

    def _centrado(self, widget: QWidget) -> QWidget:
        caja = QWidget()
        fila = QHBoxLayout(caja)
        fila.setContentsMargins(4, 2, 4, 2)
        fila.addWidget(widget)
        fila.addStretch()
        return caja

    def pedir_cancelacion(self, id_solicitud: int) -> None:
        if self.confirmar(PREGUNTA_CANCELAR):
            self.cancelacion_pedida.emit(id_solicitud)

    def confirmar(self, pregunta: str) -> bool:
        respuesta = QMessageBox.question(self, "Cancelar solicitud", pregunta)
        return respuesta == QMessageBox.Yes
