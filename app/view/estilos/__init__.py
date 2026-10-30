"""Estilos comunes de la aplicación.

Las vistas no ponen colores: marcan el widget con una propiedad, por ejemplo
boton.setProperty("tipo", "primario"), y a3i.qss le da el estilo.
"""

from pathlib import Path

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication

# Qt no carga las fuentes con rutas relativas
_CARPETA = Path(__file__).resolve().parent

# Colores de Assets/Images/ColorPalette.png
PALETA = {
    "azul_marino": "#0F172A",
    "grafito": "#111827",
    "pizarra": "#334155",
    "turquesa": "#14B8A6",
    "fondo": "#F8FAFC",
    "borde": "#CBD5E1",
    "verde": "#16A34A",
    "ambar": "#D97706",
    "rojo": "#DC2626",
    "blanco": "#FFFFFF",
}


def _mezclar(color: str, otro: str, proporcion: float) -> str:
    a = [int(color[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(otro[i:i + 2], 16) for i in (1, 3, 5)]
    mezcla = [round(x + (y - x) * proporcion) for x, y in zip(a, b)]
    return "#{:02X}{:02X}{:02X}".format(*mezcla)


# Tonos más claros y más oscuros para fondos, textos y hover
for _color in ("verde", "ambar", "rojo"):
    PALETA[f"{_color}_suave"] = _mezclar(PALETA[_color], PALETA["blanco"], 0.85)
    PALETA[f"{_color}_texto"] = _mezclar(PALETA[_color], "#000000", 0.35)
PALETA["neutro_suave"] = _mezclar(PALETA["pizarra"], PALETA["blanco"], 0.88)
PALETA["turquesa_hover"] = _mezclar(PALETA["turquesa"], "#000000", 0.12)
PALETA["rojo_hover"] = _mezclar(PALETA["rojo"], "#000000", 0.12)
PALETA["deshabilitado"] = _mezclar(PALETA["borde"], PALETA["blanco"], 0.55)


def aplicar_estilos(app: QApplication) -> None:
    """Carga las fuentes y aplica a3i.qss a toda la aplicación."""
    for fuente in sorted((_CARPETA / "fuentes").glob("*.ttf")):
        QFontDatabase.addApplicationFont(str(fuente))

    hoja = (_CARPETA / "a3i.qss").read_text(encoding="utf-8")
    # Primero los nombres largos para que @verde no cambie parte de @verde_suave
    for nombre in sorted(PALETA, key=len, reverse=True):
        hoja = hoja.replace(f"@{nombre}", PALETA[nombre])
    app.setStyleSheet(hoja)
