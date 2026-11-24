"""Piezas de la ventana (PySide6), en el diseño Magnesita (``tema.py`` y ``tema_qt.py``).

Filas etiqueta · campo · unidad, rótulos en versalitas y, junto a cada dato, la marca de su estado (supuesto, tomado del LWD,
modificado…): la forma de la marca lo distingue aunque el color no se vea.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QFrame, QGridLayout, QHeaderView, QLabel, QLineEdit, QPushButton,
                               QScrollArea, QSizePolicy, QSlider, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from . import tema
from .formato import fmt, fmt_g, grados, numero, numero_estricto  # noqa: F401  (se reexportan: la ventana los importa de aquí)

_ANCLA = {"w": Qt.AlignmentFlag.AlignLeft, "e": Qt.AlignmentFlag.AlignRight, "center": Qt.AlignmentFlag.AlignHCenter}


def poner_clase(widget, clase: str) -> None:
    """Cambia el papel de un widget en la hoja de estilo (``clase``) y lo repinta."""
    if widget.property("clase") != clase:
        widget.setProperty("clase", clase)
        widget.style().unpolish(widget)
        widget.style().polish(widget)


def etiqueta(texto: str = "", clase: str | None = None, envolver: bool = False) -> QLabel:
    e = QLabel(texto)
    if clase:
        e.setProperty("clase", clase)
    if envolver:
        e.setWordWrap(True)
        e.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Minimum)
    return e


def boton(texto: str, accion=None, clase: str | None = None) -> QPushButton:
    b = QPushButton(texto)
    if clase:
        b.setProperty("clase", clase)
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    if accion is not None:
        b.clicked.connect(lambda _=False: accion())
    return b


def linea(vertical: bool = False) -> QFrame:
    f = QFrame()
    f.setObjectName("Linea")
    if vertical:
        f.setFixedWidth(1)
    else:
        f.setFixedHeight(1)
    return f


def tarjeta(capa, titulo: str | None, rejilla: bool = False, expandir: bool = False):
    """Tarjeta redondeada con el título en una franja resaltada (sin franja si ``titulo`` es None).

    La agrega a la capa ``capa`` y devuelve (tarjeta, capa del cuerpo): vertical, o una rejilla con ``rejilla``.
    """
    marco = QFrame()
    marco.setObjectName("Tarjeta")
    v = QVBoxLayout(marco)
    v.setContentsMargins(1, 1, 1, 1)
    v.setSpacing(0)
    if titulo is not None:
        encabezado = QLabel(titulo.upper())
        encabezado.setObjectName("Encabezado")
        v.addWidget(encabezado)
    cuerpo = QWidget()
    capa_cuerpo = QGridLayout(cuerpo) if rejilla else QVBoxLayout(cuerpo)
    capa_cuerpo.setContentsMargins(13, 10, 13, 12)
    if rejilla:
        capa_cuerpo.setHorizontalSpacing(6)
        capa_cuerpo.setVerticalSpacing(6)
        capa_cuerpo.setColumnStretch(0, 1)
    else:
        capa_cuerpo.setSpacing(6)
    v.addWidget(cuerpo, 1)
    capa.addWidget(marco, 1 if expandir else 0)
    return marco, capa_cuerpo


tarjeta_lateral = tarjeta


def rejilla(capa=None) -> QGridLayout:
    """Una rejilla de filas etiqueta · campo · unidad · estado, para meter en una tarjeta vertical."""
    g = QGridLayout()
    g.setContentsMargins(0, 0, 0, 0)
    g.setHorizontalSpacing(6)
    g.setVerticalSpacing(6)
    g.setColumnStretch(0, 1)
    if capa is not None:
        capa.addLayout(g)
    return g


class Indicador(QWidget):
    """Rótulo en versalitas y cifra debajo."""

    def __init__(self, rotulo: str, valor: str = "—", acento: bool = False):
        super().__init__()
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 4)
        v.setSpacing(0)
        v.addWidget(etiqueta(rotulo.upper(), "rotulo"))
        self._valor = etiqueta(valor, "cifraAcento" if acento else "cifra")
        v.addWidget(self._valor)

    def set(self, texto: str, clase: str | None = None) -> None:
        self._valor.setText(texto)
        if clase:
            poner_clase(self._valor, clase)

    def texto(self) -> str:
        return self._valor.text()

    def clase(self) -> str:
        return self._valor.property("clase")


def nota(texto: str, clase: str = "tenue3") -> QLabel:
    return etiqueta(texto, clase, envolver=True)


class EtiquetaEstado(QLabel):
    """Estado de un dato: la marca (● ◆ ■ ▼ ○) y su nombre, en el color del estado."""

    def __init__(self, rol: str = "dato_del_usuario", texto: str | None = None, compacto: bool = False):
        super().__init__()
        self._rol, self._compacto = rol, compacto
        self.poner(rol, texto)

    def poner(self, rol: str, texto: str | None = None) -> None:
        """``compacto``: solo la marca; el nombre del estado queda en la ayuda emergente."""
        self._rol = rol
        nombre = texto or tema.texto_estado(rol)
        self.setText(tema.marca(rol) if self._compacto else f"{tema.marca(rol)} {nombre}")
        self.setToolTip(nombre if self._compacto else "")
        self.setStyleSheet(f"color: {tema.color_estado(rol)}; font-size: 8.5pt;")

    @property
    def rol(self) -> str:
        return self._rol


class Selector(QComboBox):
    """Lista desplegable que no cambia con la rueda del ratón al pasar por encima (va dentro de columnas que se desplazan)."""

    def __init__(self):
        super().__init__()
        # el ancho lo da la tarjeta, no el texto más largo de la lista (si no, la columna se ensancha y se recorta)
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.setMinimumContentsLength(8)

    def wheelEvent(self, evento):
        evento.ignore()


class Deslizador(QSlider):
    def __init__(self, nombre: str | None = None):
        super().__init__(Qt.Orientation.Horizontal)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if nombre:
            self.setObjectName(nombre)

    def wheelEvent(self, evento):
        evento.ignore()


class Variable:
    """Un texto que puede estar en un campo (``QLineEdit``) o todavía no: ``get``/``set`` y un aviso al cambiar."""

    def __init__(self, valor="", al_cambiar=None):
        self._texto = str(valor)
        self._al_cambiar = al_cambiar
        self.entrada: QLineEdit | None = None

    def enlazar(self, entrada: QLineEdit) -> QLineEdit:
        self.entrada = entrada
        entrada.setText(self._texto)
        entrada.textChanged.connect(self._cambio)
        return entrada

    def _cambio(self, texto: str) -> None:
        self._texto = texto
        if self._al_cambiar:
            self._al_cambiar()

    def get(self) -> str:
        return self._texto

    def set(self, valor) -> None:
        if self.entrada is not None:
            self.entrada.setText(str(valor))          # avisa por ``textChanged``
        elif str(valor) != self._texto:
            self._cambio(str(valor))


def campo_de_texto(ancho: int = 9, alinear: str = "e", variable: Variable | None = None) -> QLineEdit:
    """Un campo del ancho de ``ancho`` caracteres."""
    e = QLineEdit()
    e.setAlignment(_ANCLA[alinear] | Qt.AlignmentFlag.AlignVCenter)
    e.setFixedWidth(ancho * 7 + 22)
    if variable is not None:
        variable.enlazar(e)
    return e


class Campo:
    """Un número editable: etiqueta, campo, unidad y, al lado, el estado del dato.

    Con ``vincular_escala`` un deslizador queda enlazado: mover uno escribe en el otro, y el campo admite valores fuera del
    rango del deslizador. ``al_cambiar`` se llama con cada cambio; la aplicación lo difiere.
    """

    def __init__(self, valor: float | None = None, decimales: int = 1, al_cambiar=None,
                 rol: str = "dato_del_usuario", texto_estado: str | None = None):
        self.decimales = decimales
        self._al_cambiar = al_cambiar
        self._ocupado = False
        self.escala: Deslizador | None = None
        self.paso = None
        self.var = Variable(self._texto(valor), self._desde_campo)
        self.rol, self.texto_estado = rol, texto_estado
        self.estado: EtiquetaEstado | None = None
        self.entrada: QLineEdit | None = None
        self.piezas: list[QWidget] = []

    # --- construcción de los widgets ------------------------------------------------
    def poner_en(self, capa: QGridLayout, fila: int, rotulo: str, unidad: str = "", ancho: int = 9,
                 compacto: bool = False) -> "Campo":
        """Etiqueta, campo, unidad y estado en una fila de la rejilla ``capa`` (``compacto``: solo la marca)."""
        self.entrada = campo_de_texto(ancho, variable=self.var)
        self.estado = EtiquetaEstado(self.rol, self.texto_estado, compacto=compacto)
        self.piezas = [etiqueta(rotulo, "tenue"), self.entrada, etiqueta(unidad, "tenue3"), self.estado]
        for columna, pieza in enumerate(self.piezas):
            capa.addWidget(pieza, fila, columna)
        return self

    def tomar_entrada(self, entrada: QLineEdit) -> None:
        """Usa un campo ya hecho (el de la inclinación, que va entre sus dos botones)."""
        self.entrada = self.var.enlazar(entrada)

    def vincular_escala(self, escala: Deslizador, paso: float | None = None) -> None:
        self.escala, self.paso = escala, paso or 1.0
        self._a_la_escala(self.get() or 0.0)
        escala.valueChanged.connect(self._desde_escala)

    def poner_rango(self, minimo: float, maximo: float) -> None:
        if self.escala is not None:
            previo = self.escala.blockSignals(True)
            self.escala.setRange(int(round(minimo / self.paso)), int(round(maximo / self.paso)))
            self.escala.blockSignals(previo)
            self._a_la_escala(self.get() or 0.0)

    def _a_la_escala(self, v: float) -> None:
        previo = self.escala.blockSignals(True)
        self.escala.setValue(int(round(v / self.paso)))
        self.escala.blockSignals(previo)

    # --- valor ----------------------------------------------------------------------
    def _texto(self, v):
        return "" if v is None else "%.*f" % (self.decimales, v)

    def _texto_fiel(self, v):
        """El valor tal cual está en el archivo: con los decimales del campo si no pierde nada y con todos los suyos si no
        (abrir un archivo no debe redondear en silencio un 2.5° ni un criterio de 12.5 mm)."""
        if v is None or isinstance(v, str):
            return self._texto(v) if v is None else v
        if self.decimales > 2 or abs(round(v, self.decimales) - v) > 1e-9 * max(1.0, abs(v)):
            return fmt_g(v)
        return self._texto(v)

    def _desde_escala(self, pasos: int):
        if self._ocupado:
            return
        self._ocupado = True
        self.var.set(self._texto(pasos * self.paso))
        self._ocupado = False
        if self._al_cambiar:
            self._al_cambiar()

    def _desde_campo(self):
        if self._ocupado:
            return
        v = numero(self.var.get())
        if v is not None and self.escala is not None:
            self._a_la_escala(v)
        if self._al_cambiar:
            self._al_cambiar()

    def get(self):
        return numero(self.var.get())

    def get_estricto(self, nombre: str):
        """El valor, ``None`` si el campo está vacío y un ``ValueError`` si tiene un texto que no es un número."""
        return numero_estricto(self.var.get(), nombre)

    def set(self, v, avisar: bool = False):
        self._ocupado = True
        self.var.set(self._texto_fiel(v))
        if v is not None and self.escala is not None:
            self._a_la_escala(v)
        self._ocupado = False
        if avisar and self._al_cambiar:
            self._al_cambiar()


class ColumnaScroll(QScrollArea):
    """Una columna que se desplaza si su contenido no cabe (columnas laterales y supuestos)."""

    def __init__(self, ancho: int | None = None):
        super().__init__()
        self.setObjectName("Columna")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QFrame.Shape.NoFrame)
        if ancho:
            self.setFixedWidth(ancho)
        self.interior = QWidget()
        self.interior.setObjectName("ColumnaInterior")
        self.capa = QVBoxLayout(self.interior)
        self.capa.setContentsMargins(12, 12, 8, 12)
        self.capa.setSpacing(10)
        self.setWidget(self.interior)

    def cerrar(self) -> None:
        """Empuja las tarjetas hacia arriba: se llama cuando la columna ya tiene todo."""
        self.capa.addStretch(1)


class Tabla(QTableWidget):
    """Tabla de solo lectura: columnas (título, ancho, ancla), filas de textos y, si se quiere, un identificador por fila."""

    def __init__(self, columnas, filas_visibles: int | None = None, seleccion: bool = True, estirar: str | bool = True):
        super().__init__(0, len(columnas))
        self._anclas = [_ANCLA[c[2]] | Qt.AlignmentFlag.AlignVCenter for c in columnas]
        self.ids: list[str] = []
        self.setHorizontalHeaderLabels([c[0] for c in columnas])
        self.verticalHeader().setVisible(False)
        self.verticalHeader().setDefaultSectionSize(27)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection if seleccion
                              else QAbstractItemView.SelectionMode.NoSelection)
        self.setAlternatingRowColors(True)
        self.setShowGrid(False)
        self.setWordWrap(False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        cabecera = self.horizontalHeader()
        cabecera.setHighlightSections(False)
        cabecera.setMinimumSectionSize(40)
        for k, (_titulo, ancho, ancla) in enumerate(columnas):
            self.setColumnWidth(k, ancho)
            self.horizontalHeaderItem(k).setTextAlignment(_ANCLA[ancla] | Qt.AlignmentFlag.AlignVCenter)
        self._pesos = [c[1] for c in columnas] if estirar is True else None      # reparto proporcional a los anchos dados
        if estirar is True:
            cabecera.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        elif isinstance(estirar, int) and estirar is not False:
            cabecera.setSectionResizeMode(estirar, QHeaderView.ResizeMode.Stretch)
        if filas_visibles:
            self.setFixedHeight(34 + 27 * filas_visibles + 4)

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        if self._pesos:
            ancho, total, usado = self.viewport().width(), sum(self._pesos), 0
            for k, peso in enumerate(self._pesos):
                w = ancho - usado if k == len(self._pesos) - 1 else int(ancho * peso / total)
                self.setColumnWidth(k, max(w, 30))
                usado += w

    def poner(self, filas, ids=None, colores=None) -> None:
        """Sustituye las filas; ``colores`` es el color del texto de cada fila (o None)."""
        previo = self.blockSignals(True)
        self.setRowCount(0)
        self.setRowCount(len(filas))
        self.ids = [str(i) for i in ids] if ids is not None else [str(k) for k in range(len(filas))]
        for f, valores in enumerate(filas):
            for c, valor in enumerate(valores):
                celda = QTableWidgetItem(str(valor))
                celda.setTextAlignment(self._anclas[c])
                celda.setToolTip(str(valor))          # una celda recortada («DERRAMA y…») se lee completa al pasar el puntero
                if colores is not None and colores[f]:
                    celda.setForeground(QColor(colores[f]))
                self.setItem(f, c, celda)
        self.blockSignals(previo)

    def valores(self) -> list[tuple]:
        return [tuple(self.item(f, c).text() for c in range(self.columnCount())) for f in range(self.rowCount())]

    def indice_elegido(self) -> int | None:
        filas = self.selectionModel().selectedRows()
        return filas[0].row() if filas else None

    def id_elegido(self) -> str | None:
        i = self.indice_elegido()
        return None if i is None else self.ids[i]

    def elegir(self, identificador: str, avisar: bool = False) -> bool:
        if str(identificador) not in self.ids:
            return False
        fila = self.ids.index(str(identificador))
        previo = self.blockSignals(not avisar)
        self.selectRow(fila)
        self.scrollToItem(self.item(fila, 0))
        self.blockSignals(previo)
        return True
