"""Piezas de interfaz comunes a las páginas de VaciaT, sobre los componentes Qt de LWD-EAF."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFormLayout, QGridLayout, QScrollArea, QVBoxLayout, QWidget

from .interfaz.widgets import boton, tarjeta

# Lo que hace cada botón de la barra de las gráficas, en español (Matplotlib los trae en inglés).
_BARRA = {"Home": "Vista inicial", "Back": "Vista anterior", "Forward": "Vista siguiente",
          "Pan": "Desplazar (botón izquierdo) y ampliar un eje (botón derecho)", "Zoom": "Ampliar un rectángulo",
          "Save": "Guardar la gráfica como imagen"}
_ICONOS = {"Home": "home", "Back": "back", "Forward": "forward", "Pan": "move", "Zoom": "zoom_to_rect", "Save": "filesave"}


def formulario(capa, titulo: str) -> QFormLayout:
    """Una tarjeta con su título y un formulario etiqueta · campo dentro."""
    _, cuerpo = tarjeta(capa, titulo)
    f = QFormLayout()
    f.setContentsMargins(0, 0, 0, 0)
    f.setVerticalSpacing(6)
    f.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    cuerpo.addLayout(f)
    return f


def escala(px: int) -> int:
    """Un ancho fijo en píxeles, crecido con la letra de la aplicación (la base es la letra de 10 puntos)."""
    return int(px * max(QApplication.font().pointSizeF(), 10.0) / 10.0)


def _tenido(nombre: str):
    """El icono de Matplotlib (sus PNG) en el color del texto del diseño: Matplotlib lo pinta blanco o negro según el fondo que
    deduce, y en esta ventana lo deducía mal."""
    from pathlib import Path

    import matplotlib
    from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap

    from .interfaz import tema

    carpeta = Path(matplotlib.get_data_path()) / "images"
    nuevo = QIcon()
    for archivo in (f"{nombre}.png", f"{nombre}_large.png"):
        if not (carpeta / archivo).is_file():
            continue
        imagen = QPixmap(str(carpeta / archivo))
        pincel = QPainter(imagen)
        pincel.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
        pincel.fillRect(imagen.rect(), QColor(tema.PALETA["TEXTO_2"]))
        pincel.end()
        nuevo.addPixmap(imagen)
    return nuevo


def con_barra(lienzo) -> QWidget:
    """El lienzo de Matplotlib con su barra de herramientas (vista inicial, desplazar, ampliar, guardar la imagen)."""
    from matplotlib.backends.backend_qtagg import NavigationToolbar2QT

    caja = QWidget()
    v = QVBoxLayout(caja)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(0)
    barra = NavigationToolbar2QT(lienzo, caja, coordinates=True)
    for accion in barra.actions():
        texto = accion.text()
        if texto in ("Subplots", "Customize"):
            accion.setVisible(False)
        elif texto in _BARRA:
            accion.setToolTip(_BARRA[texto])
            accion.setIcon(_tenido(_ICONOS[texto]))
    lienzo.barra = barra
    v.addWidget(barra)
    v.addWidget(lienzo, 1)
    return caja


def botonera(filas) -> QWidget:
    """Botones en filas: ((texto, ayuda, acción), …) por fila; los de una fila se reparten el ancho."""
    caja = QWidget()
    g = QGridLayout(caja)
    g.setContentsMargins(0, 0, 0, 0)
    g.setSpacing(5)
    for i, fila in enumerate(filas):
        for j, (texto, ayuda, accion) in enumerate(fila):
            b = boton(texto, accion)
            b.setToolTip(ayuda)
            g.addWidget(b, i, j * 6 // len(fila), 1, 6 // len(fila))
    return caja


def columna_derecha(contenido: QWidget, ancho: int = 290) -> QScrollArea:
    """La columna del resultado, con desplazamiento vertical si la pantalla es baja (1 280 × 720)."""
    barra = QScrollArea()
    barra.setObjectName("Columna")
    contenido.setObjectName("ColumnaInterior")
    barra.setWidget(contenido)
    barra.setWidgetResizable(True)
    barra.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    barra.setFixedWidth(escala(ancho) + 12)
    return barra
