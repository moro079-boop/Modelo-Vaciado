"""El diseño Magnesita vestido con Qt: la paleta y los roles son los de ``tema.py``; aquí está la hoja de estilo.

Tarjetas con esquinas redondeadas, botones y campos con estados (sobre, foco, inhabilitado), deslizadores y barras de
desplazamiento finos, pestañas con subrayado y tablas con filas alternas. Qt escala solo en pantallas de 125 a 200 %.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette

from . import tema

# Letra de los controles: la del sistema en Windows 11/10 y, fuera de Windows, la primera que haya.
_LETRA = ("Segoe UI Variable Text", "Segoe UI", "Inter", "Noto Sans", "Ubuntu", "DejaVu Sans")


def _primera(candidatas, instaladas) -> str:
    return next((c for c in candidatas if c.lower() in instaladas), candidatas[-1])


def resolver_familias() -> str:
    """Elige las familias instaladas: las de las gráficas (``tema.FAMILIA_SANS``…, Trebuchet MS en Windows y DejaVu aquí) y,
    lo que devuelve, la de los controles."""
    instaladas = {f.lower() for f in QFontDatabase.families()}
    tema.FAMILIA_SANS = next((c for c in tema._SANS if c.lower() in instaladas), tema._SANS[0])
    tema.FAMILIA_CIFRA = tema.FAMILIA_MONO = next((c for c in tema._MONO if c.lower() in instaladas), tema._MONO[0])
    return _primera(_LETRA, instaladas)


def aplicar(aplicacion, tamano: float = 10.0) -> str:
    """Estilo Fusion (igual en Windows, Linux y macOS), paleta y letra; devuelve la hoja de estilo para la ventana."""
    P = tema.PALETA
    aplicacion.setStyle("Fusion")
    letra = resolver_familias()
    fuente = QFont(letra)
    fuente.setPointSizeF(tamano)
    aplicacion.setFont(fuente)
    paleta = QPalette()
    for rol, color in ((QPalette.ColorRole.Window, "FONDO"), (QPalette.ColorRole.WindowText, "TEXTO"),
                       (QPalette.ColorRole.Base, "PAPEL"), (QPalette.ColorRole.AlternateBase, "SUPERFICIE"),
                       (QPalette.ColorRole.Text, "TEXTO"), (QPalette.ColorRole.Button, "SUPERFICIE"),
                       (QPalette.ColorRole.ButtonText, "TEXTO"), (QPalette.ColorRole.Highlight, "ACENTO"),
                       (QPalette.ColorRole.HighlightedText, "SOBRE_ACENTO"), (QPalette.ColorRole.ToolTipBase, "PAPEL"),
                       (QPalette.ColorRole.ToolTipText, "TEXTO"), (QPalette.ColorRole.PlaceholderText, "TEXTO_3")):
        paleta.setColor(rol, QColor(P[color]))
    aplicacion.setPalette(paleta)
    return hoja_de_estilo()


def hoja_de_estilo() -> str:
    P = dict(ACENTO_OSCURO="#3B5019", PELIGRO_SUAVE="#F3DCD8", ENFOQUE="#FFFFFF")
    P.update(tema.PALETA, MONO=tema.FAMILIA_MONO, FLECHA=_flecha())
    return _HOJA % P


def _flecha() -> str:
    """La flecha de las listas desplegables, dibujada en el color de acento (una hoja de estilo de Qt solo acepta imágenes)."""
    import tempfile
    from pathlib import Path

    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QPainter, QPen, QPixmap, QPolygonF

    ruta = Path(tempfile.gettempdir()) / f"modelo_vaciado_flecha_{tema.PALETA['ACENTO'].lstrip('#')}.png"
    if not ruta.is_file():
        imagen = QPixmap(48, 48)
        imagen.fill(Qt.GlobalColor.transparent)
        pincel = QPainter(imagen)
        pincel.setRenderHint(QPainter.RenderHint.Antialiasing)
        pincel.setPen(QPen(QColor(tema.PALETA["ACENTO"]), 7, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        pincel.drawPolyline(QPolygonF([QPointF(8, 17), QPointF(24, 33), QPointF(40, 17)]))
        pincel.end()
        imagen.save(str(ruta))
    return ruta.as_posix()


_HOJA = """
QMainWindow, QWidget#Fondo, QScrollArea#Columna, QWidget#ColumnaInterior { background: %(FONDO)s; }
QScrollArea#Columna { border: none; }
QWidget#Barra, QWidget#Pie { background: %(SUPERFICIE)s; }
QFrame#Linea { background: %(BORDE)s; border: none; }
QLabel { color: %(TEXTO)s; background: transparent; }
QLabel#Marca { font-size: 15pt; font-weight: 700; color: %(TEXTO)s; }
QLabel#MarcaAcento { font-size: 13pt; font-weight: 700; color: %(ACENTO)s; }

/* tarjetas */
QFrame#Tarjeta { background: %(SUPERFICIE)s; border: 1px solid %(BORDE)s; border-radius: 10px; }
QFrame#Hoja { background: %(PAPEL)s; border: 1px solid %(BORDE)s; border-radius: 10px; }
QFrame#Tarjeta[tono="Ok"] { border-left: 5px solid %(CORRECTO)s; }
QFrame#Tarjeta[tono="Alarma"] { border-left: 5px solid %(ALARMA)s; }
QFrame#Tarjeta[tono="Aviso"] { border-left: 5px solid %(AVISO)s; }
QLabel#Encabezado { background: %(ACENTO_SUAVE)s; color: %(ACENTO)s; font-size: 8.5pt; font-weight: 700;
    padding: 7px 14px; border-top-left-radius: 9px; border-top-right-radius: 9px; }

/* textos por papel */
QLabel[clase="tenue"] { color: %(TEXTO_2)s; }
QLabel[clase="tenue3"] { color: %(TEXTO_3)s; font-size: 9pt; }
QLabel[clase="rotulo"] { color: %(TEXTO_3)s; font-size: 7.5pt; font-weight: 600; }
QLabel[clase="seccion"] { color: %(TEXTO_2)s; font-size: 9pt; font-weight: 700; }
QLabel[clase="cifra"] { font-weight: 600; color: %(TEXTO)s; font-size: 16pt; }
QLabel[clase="cifraAcento"] { font-weight: 600; color: %(ACENTO)s; font-size: 16pt; }
QLabel[clase="cifraAlarma"] { font-weight: 600; color: %(ALARMA)s; font-size: 16pt; }
QLabel[clase="mono"] { color: %(TEXTO_2)s; font-size: 9pt; }
QLabel[clase="error"] { color: %(ALARMA)s; font-size: 9pt; font-weight: 700; }
QLabel[clase="motivo"] { color: %(TEXTO)s; }
QLabel[clase="validez"] { color: %(TEXTO_3)s; font-size: 8pt; }
QLabel[clase="veredictoOk"] { color: %(CORRECTO)s; font-size: 18pt; font-weight: 700; }
QLabel[clase="veredictoAlarma"] { color: %(ALARMA)s; font-size: 18pt; font-weight: 700; }
QLabel[clase="veredictoAviso"] { color: %(AVISO)s; font-size: 18pt; font-weight: 700; }
QLabel[clase="estadoNeutro"] { color: %(TEXTO_2)s; font-size: 9pt; }
QLabel[clase="estadoOk"] { color: %(CORRECTO)s; font-size: 9pt; }
QLabel[clase="estadoAlarma"] { color: %(ALARMA)s; font-size: 9pt; }
QLabel[clase="estadoAviso"] { color: %(AVISO)s; font-size: 9pt; }
QLabel[clase="estadoActivo"] { color: %(ACENTO)s; font-size: 9pt; }

/* pestañas de la barra superior y de la campaña */
QPushButton#Pestana { background: transparent; border: none; border-bottom: 3px solid transparent; border-radius: 0;
    padding: 15px 14px 12px 14px; color: %(TEXTO_2)s; font-size: 10.5pt; font-weight: 400; }
QPushButton#Pestana:hover { color: %(TEXTO)s; background: %(SUPERFICIE_2)s; }
QPushButton#Pestana:focus { background: %(SUPERFICIE_2)s; }
QPushButton#Pestana:checked { color: %(ACENTO)s; border-bottom: 3px solid %(ACENTO)s; font-weight: 700; }
QPushButton#Subpestana { background: transparent; border: 1px solid transparent; border-radius: 14px; padding: 5px 12px;
    color: %(TEXTO_2)s; font-size: 10pt; font-weight: 400; }
QPushButton#Subpestana:hover, QPushButton#Subpestana:focus { background: %(SUPERFICIE)s; border: 1px solid %(BORDE)s; color: %(TEXTO)s; }
QPushButton#Subpestana:checked { background: %(ACENTO)s; border: 1px solid %(ACENTO)s; color: %(SOBRE_ACENTO)s; font-weight: 600; }

/* botones */
QPushButton { background: %(PAPEL)s; color: %(TEXTO)s; border: 1px solid %(BORDE)s; border-radius: 6px; padding: 5px 11px;
    font-size: 9pt; font-weight: 600; }
QPushButton:hover { background: %(SUPERFICIE_3)s; border-color: %(ACENTO)s; }
QPushButton:pressed { background: %(VERDE_TENUE)s; }
QPushButton:focus { border-color: %(ACENTO)s; }
QPushButton:disabled { background: %(SUPERFICIE_2)s; color: %(TEXTO_3)s; border-color: %(BORDE)s; }
QPushButton[clase="acento"] { background: %(ACENTO)s; color: %(SOBRE_ACENTO)s; border: 1px solid %(ACENTO)s; padding: 9px 14px;
    font-size: 9.5pt; }
QPushButton[clase="acento"]:hover, QPushButton[clase="acento"]:focus { background: %(ACENTO_OSCURO)s; border-color: %(ACENTO_OSCURO)s; }
QPushButton[clase="acento"]:pressed { background: %(TEXTO)s; }
QPushButton[clase="acento"]:disabled { background: %(BORDE)s; color: %(TEXTO_3)s; border-color: %(BORDE)s; }
QPushButton[clase="peligro"] { color: %(ALARMA)s; border-color: %(ALARMA)s; padding: 7px 12px; }
QPushButton[clase="peligro"]:hover { background: %(PELIGRO_SUAVE)s; border-color: %(ALARMA)s; }

/* campos, selectores y casillas */
QLineEdit { background: %(PAPEL)s; color: %(TEXTO)s; border: 1px solid %(BORDE)s; border-radius: 6px; padding: 4px 7px;
    selection-background-color: %(ACENTO)s; selection-color: %(SOBRE_ACENTO)s; }
QLineEdit:hover { border-color: %(TEXTO_3)s; }
QLineEdit:focus { border: 1px solid %(ACENTO)s; background: %(ENFOQUE)s; }
QLineEdit:disabled { background: %(SUPERFICIE_2)s; color: %(TEXTO_3)s; }
QLineEdit#Inclinacion { font-size: 14pt; font-weight: 600; padding: 3px 6px; }
QComboBox { background: %(PAPEL)s; color: %(TEXTO)s; border: 1px solid %(BORDE)s; border-radius: 6px; padding: 5px 9px; }
QComboBox:hover { border-color: %(TEXTO_3)s; }
QComboBox:focus, QComboBox:on { border-color: %(ACENTO)s; }
QComboBox::drop-down { border: none; width: 26px; }
QComboBox::down-arrow { image: url("%(FLECHA)s"); width: 12px; height: 12px; margin-right: 10px; }
QComboBox QAbstractItemView { background: %(PAPEL)s; color: %(TEXTO)s; border: 1px solid %(BORDE)s; outline: 0;
    selection-background-color: %(ACENTO)s; selection-color: %(SOBRE_ACENTO)s; padding: 3px; }
QCheckBox { color: %(TEXTO_2)s; font-size: 9pt; spacing: 7px; background: transparent; }
QDoubleSpinBox, QSpinBox { background: %(PAPEL)s; color: %(TEXTO)s; border: 1px solid %(BORDE)s; border-radius: 6px; padding: 3px 6px;
    selection-background-color: %(ACENTO)s; selection-color: %(SOBRE_ACENTO)s; }
QDoubleSpinBox:focus, QSpinBox:focus { border-color: %(ACENTO)s; background: %(ENFOQUE)s; }
QDoubleSpinBox:disabled { background: %(SUPERFICIE_2)s; color: %(TEXTO_3)s; }

/* pestañas de Qt */
QTabWidget::pane { border: 1px solid %(BORDE)s; border-radius: 8px; background: %(PAPEL)s; top: -1px; }
QTabBar::tab { background: transparent; color: %(TEXTO_2)s; padding: 8px 14px; border: none; border-bottom: 3px solid transparent; }
QTabBar::tab:hover { color: %(TEXTO)s; background: %(SUPERFICIE_2)s; }
QTabBar::tab:selected { color: %(ACENTO)s; border-bottom: 3px solid %(ACENTO)s; font-weight: 700; }
QMenuBar { background: %(SUPERFICIE)s; color: %(TEXTO)s; }
QMenuBar::item:selected { background: %(SUPERFICIE_2)s; }
QMenu { background: %(PAPEL)s; color: %(TEXTO)s; border: 1px solid %(BORDE)s; }
QMenu::item:selected { background: %(ACENTO)s; color: %(SOBRE_ACENTO)s; }

/* deslizadores */
QSlider::groove:horizontal { height: 6px; background: %(SUPERFICIE_2)s; border: 1px solid %(BORDE)s; border-radius: 4px; }
QSlider::handle:horizontal { background: %(ACENTO)s; border: 2px solid %(PAPEL)s; width: 14px; height: 14px; margin: -7px 0;
    border-radius: 9px; }
QSlider::handle:horizontal:hover, QSlider::handle:horizontal:pressed { background: %(TEXTO)s; }
QSlider#Inclinacion { min-height: 30px; }
QSlider#Inclinacion::groove:horizontal { height: 8px; background: %(ACENTO_SUAVE)s; border: 1px solid %(VERDE_TENUE)s;
    border-radius: 5px; }
QSlider#Inclinacion::handle:horizontal { width: 20px; height: 20px; margin: -9px 0; border-radius: 13px;
    border: 3px solid %(PAPEL)s; }
QSlider:focus { border: none; }

/* tablas */
QTableWidget { background: %(PAPEL)s; alternate-background-color: %(SUPERFICIE)s; color: %(TEXTO)s; border: 1px solid %(BORDE)s;
    border-radius: 8px; gridline-color: transparent; selection-background-color: %(ACENTO_SUAVE)s;
    selection-color: %(TEXTO)s; outline: 0; }
QTableWidget::item { padding: 2px 3px; border: none; }
QTableWidget::item:selected { background: %(ACENTO_SUAVE)s; }
QHeaderView { background: transparent; }
QHeaderView::section { background: %(SUPERFICIE_2)s; color: %(TEXTO_2)s; border: none; border-bottom: 1px solid %(BORDE)s;
    padding: 6px 3px; font-size: 8.5pt; font-weight: 700; }
QHeaderView::section:first { border-top-left-radius: 7px; }
QHeaderView::section:last { border-top-right-radius: 7px; }
QTableCornerButton::section { background: %(SUPERFICIE_2)s; border: none; }

/* desplazamiento y avance */
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px 1px; }
QScrollBar::handle:vertical { background: %(BORDE)s; border-radius: 4px; min-height: 32px; }
QScrollBar::handle:vertical:hover { background: %(TEXTO_3)s; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 1px 2px; }
QScrollBar::handle:horizontal { background: %(BORDE)s; border-radius: 4px; min-width: 32px; }
QScrollBar::handle:horizontal:hover { background: %(TEXTO_3)s; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QProgressBar { background: %(SUPERFICIE_2)s; border: none; border-radius: 4px; max-height: 8px; min-height: 8px; }
QProgressBar::chunk { background: %(ACENTO)s; border-radius: 4px; }

/* barra de la gráfica (Matplotlib) */
QToolBar { background: transparent; border: none; spacing: 2px; padding: 0; }
QToolBar QToolButton { background: transparent; border: 1px solid transparent; border-radius: 6px; padding: 4px; }
QToolBar QToolButton:hover { background: %(SUPERFICIE)s; border-color: %(BORDE)s; }
QToolBar QToolButton:checked { background: %(ACENTO_SUAVE)s; border-color: %(ACENTO)s; }
QToolBar QLabel { color: %(TEXTO_3)s; font-size: 9pt; }
QToolTip { background: %(PAPEL)s; color: %(TEXTO)s; border: 1px solid %(BORDE)s; padding: 4px 6px; }
"""
