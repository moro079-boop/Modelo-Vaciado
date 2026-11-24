"""Página de cálculo directo del tiempo de vaciado (PySide6), común a los dos escenarios: horno → olla y olla → distribuidor.

El resultado se recalcula solo, 250 ms después del último cambio (el cálculo y el dibujo tardan unos 0,25 s), y sólo se dibuja
la pestaña visible; las demás se dibujan al elegirlas.

Izquierda: las variables que define el usuario (recipiente, tonelaje, altura metalostática, área de paso, hidráulica y, en la
olla, la válvula y el distribuidor), cada una con la marca de su estado. Centro: pestañas «Vaciado» (series en el tiempo),
«Esquema» (el recipiente equivalente con el nivel en el instante elegido), «Sensibilidad» (tiempo contra el diámetro y el
coeficiente de descarga) y «Comparar». Derecha: el tiempo de vaciado, la comprobación de Torricelli, los avisos y los archivos.
El cálculo vive en ``escenarios`` y ``flujo``, sin Qt.
"""

from __future__ import annotations

import copy
import math
from pathlib import Path

import matplotlib
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QDoubleSpinBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMessageBox,
                               QPushButton, QScrollArea, QSlider, QTabWidget, QVBoxLayout, QWidget)

from . import colada_continua as cc
from . import escenarios as es
from .interfaz import tema
from .interfaz.widgets import EtiquetaEstado, Selector, boton
from .reporte_tiempo import AVISO, escribir_csv, escribir_excel, escribir_pdf, filas_de_resultado
from .rutas import raiz
from .ventana_formulario import botonera, columna_derecha, con_barra, escala, formulario

P = tema.PALETA

# (ruta en el escenario, etiqueta, unidad, mínimo, máximo, decimales, paso, escenarios en que aparece)
CAMPOS = (
    (("acero_inicial_t",), "Acero al inicio (tonelaje)", "t", 0.1, 3000, 1, 5, ("horno_olla", "olla_distribuidor")),
    (("acero_final_t",), "Acero al final", "t", 0, 3000, 1, 5, ("horno_olla", "olla_distribuidor")),
    (("recipiente", "altura_metalostatica_mm"), "Altura metalostática inicial sobre el orificio", "mm", 1, 20000, 0, 10,
     ("horno_olla", "olla_distribuidor")),
    (("recipiente", "talon_t"), "Talón bajo el orificio (no sale)", "t", 0, 3000, 1, 1, ("horno_olla", "olla_distribuidor")),
    (("recipiente", "relacion_diametros"), "Relación de diámetros fondo / superficie", "", 0.05, 20, 2, 0.05,
     ("horno_olla", "olla_distribuidor")),
    (("densidad",), "Densidad del acero líquido", "t/m³", 5, 8.5, 2, 0.05, ("horno_olla", "olla_distribuidor")),
    (("recipiente", "pared_gastada_mm"), "Desgaste de la pared de la olla", "mm", 0, 300, 1, 5, ("olla_distribuidor",)),
    (("recipiente", "piso_gastado_mm"), "Desgaste del piso de la olla", "mm", 0, 600, 1, 5, ("olla_distribuidor",)),
    (("paso", "diametro_mm"), "Diámetro del orificio", "mm", 5, 800, 1, 5, ("horno_olla", "olla_distribuidor")),
    (("paso", "area_cm2"), "Área de paso", "cm²", 0.1, 5000, 1, 5, ("horno_olla", "olla_distribuidor")),
    (("hidraulica", "cd"), "Coeficiente de descarga C_d", "", 0.05, 1.5, 3, 0.005, ("horno_olla", "olla_distribuidor")),
    (("hidraulica", "k_entrada"), "Pérdida de entrada K", "", 0, 10, 2, 0.05, ("horno_olla", "olla_distribuidor")),
    (("hidraulica", "largo_mm"), "Largo del canal o tubo", "mm", 0, 10000, 0, 10, ("horno_olla", "olla_distribuidor")),
    (("hidraulica", "rugosidad_mm"), "Rugosidad", "mm", 0.01, 20, 2, 0.1, ("horno_olla", "olla_distribuidor")),
    (("hidraulica", "viscosidad"), "Viscosidad del acero", "Pa·s", 0.001, 0.05, 4, 0.0005, ("horno_olla", "olla_distribuidor")),
    (("hidraulica", "caida_mm"), "Caída bajo el orificio (canal o tubo lleno)", "mm", 0, 10000, 0, 10, ("horno_olla", "olla_distribuidor")),
    (("valvula", "abertura_pct"), "Abertura de la válvula", "%", 1, 100, 0, 5, ("olla_distribuidor",)),
    (("valvula", "carrera_mm"), "Carrera efectiva (0 = el diámetro)", "mm", 0, 500, 0, 5, ("olla_distribuidor",)),
    (("destino", "nivel_mm"), "Nivel del distribuidor", "mm", 0, 3000, 0, 10, ("olla_distribuidor",)),
    (("destino", "altura_salida_mm"), "Salida del tubo sobre el fondo del distribuidor", "mm", 0, 3000, 0, 10, ("olla_distribuidor",)),
    (("destino", "masa_inicial_t"), "Acero inicial en el distribuidor", "t", 0, 200, 1, 1, ("olla_distribuidor",)),
    (("destino", "largo_mm"), "Largo del fondo del distribuidor", "mm", 100, 30000, 0, 100, ("olla_distribuidor",)),
    (("destino", "ancho_mm"), "Ancho del fondo del distribuidor", "mm", 100, 10000, 0, 50, ("olla_distribuidor",)),
    (("destino", "talud_grados"), "Talud de las paredes", "°", 0, 45, 1, 1, ("olla_distribuidor",)),
    (("destino", "nivel_maximo_mm"), "Nivel máximo del distribuidor", "mm", 0, 5000, 0, 10, ("olla_distribuidor",)),
)
GRUPOS = (
    ("Recipiente", ("acero_inicial_t", "acero_final_t", "altura_metalostatica_mm", "talon_t", "relacion_diametros", "densidad",
                    "pared_gastada_mm", "piso_gastado_mm")),
    ("Área de paso", ("diametro_mm", "area_cm2")),
    ("Hidráulica", ("cd", "k_entrada", "largo_mm", "rugosidad_mm", "viscosidad", "caida_mm")),
    ("Válvula deslizante", ("abertura_pct", "carrera_mm")),
    ("Distribuidor", ("destino_nivel_mm", "destino_altura_salida_mm", "destino_masa_inicial_t", "destino_largo_mm",
                      "destino_ancho_mm", "destino_talud_grados", "destino_nivel_maximo_mm")),
)
def clave(ruta) -> str:
    """Nombre del campo: la última parte de la ruta (con «destino_» delante en el distribuidor, para no repetir nombres)."""
    return f"destino_{ruta[-1]}" if ruta[0] == "destino" else ruta[-1]


ROL = {"calculo_del_proveedor": "calculo_del_proveedor", "derivado": "derivado", "ejemplo": "ejemplo"}


def colores() -> list[str]:
    return [P["TINTA"], P.get("SERIE_2", "#1F55D0"), P.get("SERIE_3", "#C8601A"), P["CORRECTO"], P.get("SERIE_5", "#7A3AA8"),
            P["AVISO"], P["ALARMA"]]


def _leer(e: dict, ruta):
    nodo = e
    for parte in ruta:
        nodo = nodo.get(parte) if isinstance(nodo, dict) else None
    return nodo


def _escribir(e: dict, ruta, valor):
    nodo = e
    for parte in ruta[:-1]:
        nodo = nodo.setdefault(parte, {})
    nodo[ruta[-1]] = valor


class PaginaTiempo(QWidget):
    """Cálculo directo del tiempo de vaciado para un escenario (``horno_olla`` u ``olla_distribuidor``)."""

    def __init__(self, tipo: str, lienzo_factory, escenario: dict | None = None):
        super().__init__()
        self.tipo = tipo
        self._lienzo = lienzo_factory
        self.resultado = None
        self.escenario_corrido: dict | None = None
        self.comparados: list = []
        self.observadores: list = []         # funciones que reciben la página tras cada cálculo (indicadores del diseño)
        self.campos: dict[str, QDoubleSpinBox] = {}
        self.estados: dict[str, EtiquetaEstado] = {}
        self.filas: dict[str, list[QWidget]] = {}
        self._rutas = {clave(c[0]): c[0] for c in CAMPOS if tipo in c[7]}
        self._base = es.nuevo(tipo)
        self._cargando = False
        self._sucias: set = set()             # pestañas por redibujar
        from PySide6.QtCore import QTimer

        self._reloj = QTimer(self)
        self._reloj.setSingleShot(True)
        self._reloj.setInterval(250)
        self._reloj.timeout.connect(self.calcular)
        self._armar()
        self.poner_escenario(escenario or es.nuevo(tipo))
        self.calcular()

    # -- construcción --------------------------------------------------------------------------------------------------------
    def _armar(self):
        fila = QHBoxLayout(self)
        panel = QWidget()
        col = QVBoxLayout(panel)
        col.setContentsMargins(8, 8, 22, 8)
        self.nombre = QLineEdit(es.TIPOS[self.tipo])
        f = formulario(col, "Escenario")
        f.addRow("Nombre", self.nombre)
        self.geometria = Selector()
        if self.tipo == "olla_distribuidor":
            self.geometria.addItem("Olla de la planta", "olla_de_planta")
        self.geometria.addItem("Definida por el usuario", "simple")
        self.planta = Selector()
        self.planta.addItems(cc.plantas_con_datos())
        self.forma = Selector()
        self.forma.addItem("Prismática", "prismatica")
        self.forma.addItem("Troncocónica", "troncoconica")
        self.definir_paso = Selector()
        self.definir_paso.addItem("el diámetro", "diametro")
        self.definir_paso.addItem("el área", "area")
        self.modo = Selector()
        self.modo.addItem("Coeficiente de descarga", "cd")
        self.modo.addItem("Pérdidas explícitas", "perdidas")
        self.destino = Selector()
        self.destino.addItem("A nivel constante", "nivel_constante")
        self.destino.addItem("Se llena durante el vaciado", "llenado")
        self.destino.addItem("Chorro libre", "libre")
        for w, ayuda in ((self.geometria, "La olla de un archivo de planta (regla del LWD) o un recipiente definido por tonelaje y altura"),
                         (self.forma, "Prismática: área de la superficie constante (Torricelli). Troncocónica: el diámetro cambia "
                                      "linealmente con la altura"),
                         (self.modo, "Coeficiente de descarga: v = C_d·√(2gH). Pérdidas explícitas: v = √(2gH / (1 + K + f·L/D))"),
                         (self.destino, "Contrapresión del distribuidor sobre la salida del tubo largo")):
            w.setToolTip(ayuda)
        extras = {"Recipiente": (("Geometría", self.geometria), ("Planta", self.planta), ("Forma", self.forma)),
                  "Área de paso": (("Se define por", self.definir_paso),),
                  "Hidráulica": (("Modelo", self.modo),),
                  "Distribuidor": (("Distribuidor", self.destino),)}
        for titulo, claves in GRUPOS:
            claves = [k for k in claves if k in self._rutas]
            if not claves:
                continue
            f = formulario(col, titulo)
            for rotulo, w in extras.get(titulo, ()):
                if self.tipo == "horno_olla" and w in (self.planta, self.geometria):
                    continue
                f.addRow(rotulo, w)
                self.filas[f"sel_{id(w)}"] = [f.labelForField(w), w]
            for k in claves:
                ruta = self._rutas[k]
                c = next(x for x in CAMPOS if x[0] == ruta)
                s = QDoubleSpinBox()
                s.setRange(c[3], c[4])
                s.setDecimals(c[5])
                s.setSingleStep(c[6])
                s.setSuffix(f" {c[2]}" if c[2] else "")
                s.setKeyboardTracking(False)
                s.setAlignment(Qt.AlignmentFlag.AlignRight)
                estado = EtiquetaEstado("supuesto")
                caja = QWidget()
                cv = QVBoxLayout(caja)
                cv.setContentsMargins(0, 0, 0, 0)
                cv.setSpacing(0)
                cv.addWidget(s)
                cv.addWidget(estado)
                lab = QLabel(c[1])
                lab.setWordWrap(True)
                f.addRow(lab, caja)
                self.campos[k], self.estados[k], self.filas[k] = s, estado, [lab, caja]
                s.valueChanged.connect(lambda _v, k=k: self._cambio(k))
        self.boton_calcular = boton("Calcular", self.calcular, "acento")
        col.addWidget(self.boton_calcular)
        col.addStretch(1)
        barra = QScrollArea()
        barra.setObjectName("Columna")
        barra.setWidget(panel)
        barra.setWidgetResizable(True)
        barra.setFixedWidth(escala(400))
        barra.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        fila.addWidget(barra)

        self.pestanas = QTabWidget()
        self.lienzo_series = self._lienzo(2, 2)
        self.pestanas.addTab(con_barra(self.lienzo_series), "Vaciado")
        esquema = QWidget()
        ev = QVBoxLayout(esquema)
        self.lienzo_esquema = self._lienzo()
        self.instante = QSlider(Qt.Orientation.Horizontal)
        self.instante.setRange(0, 1000)
        self.instante.valueChanged.connect(self._dibujar_esquema)
        self.rotulo_instante = QLabel()
        ev.addWidget(con_barra(self.lienzo_esquema), 1)
        ev.addWidget(self.rotulo_instante)
        ev.addWidget(self.instante)
        self.pestanas.addTab(esquema, "Esquema")
        sens = QWidget()
        sv = QVBoxLayout(sens)
        sb = QHBoxLayout()
        sb.addWidget(boton("Calcular la sensibilidad", self.calcular_sensibilidad, "acento"))
        sb.addWidget(QLabel("Tiempo de vaciado al variar el diámetro del orificio y el coeficiente de descarga, con lo demás igual."))
        sb.addStretch(1)
        sv.addLayout(sb)
        self.lienzo_sensibilidad = self._lienzo(1, 2)
        sv.addWidget(con_barra(self.lienzo_sensibilidad), 1)
        self.sensibilidad = None
        self.pestanas.addTab(sens, "Sensibilidad")
        comparar = QWidget()
        kv = QVBoxLayout(comparar)
        kb = QHBoxLayout()
        b1, b2 = QPushButton("Añadir el escenario actual"), QPushButton("Vaciar la comparación")
        b1.clicked.connect(self.anadir_a_comparacion)
        b2.clicked.connect(self.vaciar_comparacion)
        kb.addWidget(b1)
        kb.addWidget(b2)
        kb.addStretch(1)
        kv.addLayout(kb)
        self.lienzo_comparar = self._lienzo(1, 2)
        kv.addWidget(con_barra(self.lienzo_comparar), 1)
        self.pestanas.addTab(comparar, "Comparar")
        fila.addWidget(self.pestanas, 1)

        der = QWidget()
        der.setObjectName("Resultado")
        dv = QVBoxLayout(der)
        self.rotulo_titular = QLabel("Tiempo de vaciado")
        self.rotulo_titular.setProperty("clase", "rotulo")
        self.titular = QLabel("—")
        self.titular.setObjectName("Titular")
        self.subtitular = QLabel("")
        self.subtitular.setWordWrap(True)
        self.tabla = QLabel("")
        self.tabla.setTextFormat(Qt.TextFormat.RichText)
        self.tabla.setWordWrap(True)
        self.avisos = QLabel("")
        self.avisos.setWordWrap(True)
        self.avisos.setTextFormat(Qt.TextFormat.RichText)
        pie = QLabel(AVISO)
        pie.setWordWrap(True)
        pie.setStyleSheet(f"color: {P['AVISO']}; font-size: 11px;")
        for w in (self.rotulo_titular, self.titular, self.subtitular, self.tabla, self.avisos):
            dv.addWidget(w)
        dv.addStretch(1)
        dv.addWidget(botonera(((("Abrir…", "Abrir un escenario (Ctrl+O)", self.abrir),
                                 ("Guardar…", "Guardar el escenario (Ctrl+S)", self.guardar)),
                                (("Restablecer los valores", "Volver a los valores con que abre el escenario", self.restablecer),),
                                (("Excel…", "Exportar a Excel (Ctrl+E)", lambda: self.exportar("xlsx")),
                                 ("PDF…", "Exportar a PDF (Ctrl+P)", lambda: self.exportar("pdf")),
                                 ("CSV…", "Exportar la serie en CSV", lambda: self.exportar("csv"))))))
        dv.addWidget(pie)
        fila.addWidget(columna_derecha(der))

        for w in (self.geometria, self.forma, self.definir_paso, self.modo, self.destino):
            w.currentIndexChanged.connect(self._habilitar)
            w.currentIndexChanged.connect(self._programar)
        self.planta.currentIndexChanged.connect(lambda _i: self._marcar_todo())
        self.planta.currentIndexChanged.connect(self._programar)
        self.nombre.editingFinished.connect(self._programar)
        self.pestanas.currentChanged.connect(lambda _i: self._dibujar_pendientes())

    def _programar(self, *_):
        """Recalcula 250 ms después del último cambio (si el usuario sigue escribiendo, espera)."""
        if not self._cargando:
            self._reloj.start()

    # -- escenario ↔ controles ---------------------------------------------------------------------------------------------
    def _mostrar(self, clave: str, visible: bool):
        for w in self.filas.get(clave, ()):
            if w is not None:
                w.setVisible(visible)

    def _habilitar(self):
        planta = self.geometria.currentData() == "olla_de_planta"
        for k in ("altura_metalostatica_mm", "talon_t", "densidad"):
            self._mostrar(k, not planta)
        self._mostrar("relacion_diametros", not planta and self.forma.currentData() == "troncoconica")
        self._mostrar(f"sel_{id(self.forma)}", not planta)
        self._mostrar(f"sel_{id(self.planta)}", planta)
        for k in ("pared_gastada_mm", "piso_gastado_mm"):
            self._mostrar(k, planta)
        por_area = self.definir_paso.currentData() == "area"
        self.campos["diametro_mm"].setEnabled(not por_area)
        self.campos["area_cm2"].setEnabled(por_area)
        cd = self.modo.currentData() == "cd"
        self._mostrar("cd", cd)
        for k in ("k_entrada", "largo_mm", "rugosidad_mm", "viscosidad"):
            self._mostrar(k, not cd)
        if self.tipo == "olla_distribuidor":
            d = self.destino.currentData()
            self._mostrar("destino_altura_salida_mm", d in ("nivel_constante", "llenado"))
            self._mostrar("destino_nivel_mm", d == "nivel_constante")
            for k in ("destino_masa_inicial_t", "destino_largo_mm", "destino_ancho_mm", "destino_talud_grados", "destino_nivel_maximo_mm"):
                self._mostrar(k, d == "llenado")

    def _cambio(self, k: str):
        if self._cargando:
            return
        if k in ("diametro_mm", "area_cm2"):          # el diámetro y el área se siguen el uno al otro
            self._cargando = True
            try:
                if k == "diametro_mm":
                    self.campos["area_cm2"].setValue(math.pi * self.campos["diametro_mm"].value() ** 2 / 4 / 100)
                else:
                    self.campos["diametro_mm"].setValue(math.sqrt(4 * self.campos["area_cm2"].value() * 100 / math.pi))
            finally:
                self._cargando = False
            self._marcar("diametro_mm")
            self._marcar("area_cm2")
        self._marcar(k)
        self._programar()

    def _marcar(self, k: str):
        ruta = self._rutas[k]
        base = _leer(self._base, ruta)
        if k == "area_cm2":
            base = math.pi * (self._base["paso"]["diametro_mm"]) ** 2 / 4 / 100
        actual = self.campos[k].value()
        estado = es.ESTADOS.get(self.tipo, {}).get(k)
        if base is not None and abs(actual - float(base)) > 10 ** -(self.campos[k].decimals()) / 2:
            self.estados[k].poner("modificado", "dato del usuario")
        elif estado:
            self.estados[k].poner(ROL.get(estado[0], estado[0]), tema.texto_estado(estado[0]))
            self.estados[k].setToolTip(estado[1])
        else:
            self.estados[k].poner("dato_del_usuario")

    def _marcar_todo(self):
        for k in self.campos:
            self._marcar(k)

    def escenario(self) -> dict:
        e = copy.deepcopy(self._base)
        e["nombre"] = self.nombre.text().strip() or es.TIPOS[self.tipo]
        for k, s in self.campos.items():
            if k != "area_cm2":
                _escribir(e, self._rutas[k], float(s.value()))
        e["recipiente"]["geometria"] = self.geometria.currentData()
        e["recipiente"]["forma"] = self.forma.currentData()
        if self.tipo == "olla_distribuidor":
            e["recipiente"]["planta"] = self.planta.currentText()
            e["destino"]["tipo"] = self.destino.currentData()
        if self.definir_paso.currentData() == "area":
            e["paso"] = {"area_cm2": float(self.campos["area_cm2"].value())}
        else:
            e["paso"] = {"diametro_mm": float(self.campos["diametro_mm"].value())}
        e["hidraulica"]["modo"] = self.modo.currentData()
        if e["acero_final_t"] >= e["acero_inicial_t"]:
            raise ValueError("El acero al final debe ser menor que el acero al inicio.")
        return e

    def poner_escenario(self, e: dict):
        e = es.completar(e)
        if e.get("tipo") != self.tipo:
            raise ValueError(f"el escenario es de «{es.TIPOS.get(e.get('tipo'), e.get('tipo'))}», no de «{es.TIPOS[self.tipo]}»")
        self._cargando = True
        try:
            self.nombre.setText(e.get("nombre", es.TIPOS[self.tipo]))
            for k, s in self.campos.items():
                v = _leer(e, self._rutas[k])
                if v is not None:
                    s.setValue(float(v))
            p = e["paso"]
            if p.get("area_cm2") or p.get("area_mm2"):
                area = float(p.get("area_cm2") or p["area_mm2"] / 100)
                self.campos["area_cm2"].setValue(area)
                self.campos["diametro_mm"].setValue(math.sqrt(4 * area * 100 / math.pi))
                self.definir_paso.setCurrentIndex(self.definir_paso.findData("area"))
            else:
                self.campos["area_cm2"].setValue(math.pi * float(p["diametro_mm"]) ** 2 / 4 / 100)
                self.definir_paso.setCurrentIndex(self.definir_paso.findData("diametro"))
            r = e["recipiente"]
            self.geometria.setCurrentIndex(max(self.geometria.findData(r.get("geometria", "simple")), 0))
            self.forma.setCurrentIndex(max(self.forma.findData(r.get("forma", "prismatica")), 0))
            if r.get("planta"):
                self.planta.setCurrentText(r["planta"])
            self.modo.setCurrentIndex(max(self.modo.findData(e["hidraulica"].get("modo", "cd")), 0))
            if self.tipo == "olla_distribuidor":
                self.destino.setCurrentIndex(max(self.destino.findData(e["destino"].get("tipo", "libre")), 0))
        finally:
            self._cargando = False
        self._marcar_todo()
        self._habilitar()

    def restablecer(self):
        self.poner_escenario(es.nuevo(self.tipo))
        self.calcular()

    # -- cálculo y dibujo ---------------------------------------------------------------------------------------------------
    def calcular(self) -> bool:
        self._reloj.stop()
        try:
            e = self.escenario()
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                r = es.correr(e)
            finally:
                QApplication.restoreOverrideCursor()
        except Exception as error:  # noqa: BLE001  (se muestra al usuario; la ventana sigue)
            self.titular.setText("—")
            self.subtitular.setText("")
            self.tabla.setText("")
            self.avisos.setText(f"<span style='color:{P['ALARMA']}'><b>No se pudo calcular.</b> {error}</span>")
            self._avisar()
            return False
        self.resultado, self.escenario_corrido = r, e
        s = es.resumen(r)
        self.titular.setText(self.tiempo_texto())
        self.subtitular.setText(f"{r.tiempo:.0f} s para {r.colado:.1f} t · caudal medio {s['caudal_medio_t_min']:.1f} t/min")
        self.tabla.setText("<table cellspacing='3'>" + "".join(
            f"<tr><td style='color:{P['TEXTO_2']}'>{a}</td><td align='right'><b>{b}</b></td></tr>"
            for a, b in filas_de_resultado(r)[3:] if not a.startswith("Fin")) + "</table>")
        avisos = [(t, x) for t, x in r.eventos]
        if not r.terminado and not any(x == r.motivo_fin for _, x in avisos):
            avisos.append((r.tiempo, r.motivo_fin))
        if avisos:
            self.avisos.setText("".join(f"<p style='color:{P['ALARMA']}'><b>Aviso a los {t:.0f} s.</b> {x}</p>" for t, x in avisos))
        else:
            self.avisos.setText(f"<span style='color:{P['CORRECTO']}'><b>Sin avisos.</b> El recipiente llega al acero final.</span>")
        self._sucias = {"series", "esquema"}
        self._dibujar_pendientes()
        self._avisar()
        return True

    def _dibujar_pendientes(self):
        """Dibuja la pestaña visible si quedó por redibujar."""
        visible = {0: "series", 1: "esquema"}.get(self.pestanas.currentIndex())
        if self.resultado is None or visible not in self._sucias:
            return
        self._sucias.discard(visible)
        if visible == "series":
            self._dibujar_series(self.lienzo_series, [(self.resultado.nombre, self.resultado)])
        else:
            self._dibujar_esquema()

    def tiempo_texto(self) -> str:
        if self.resultado is None:
            return "—"
        t = self.resultado.tiempo
        return f"{int(t // 60)} min {int(round(t % 60)):02d} s" if t >= 60 else f"{t:.0f} s"

    def _avisar(self):
        for f in self.observadores:
            f(self)

    def _dibujar_series(self, lienzo, lista):
        cols = colores()
        with matplotlib.rc_context(tema.estilo_matplotlib()):
            lienzo.limpiar()
            paneles = (("masa", 1, "acero en el recipiente, t"), ("caudal", 60, "caudal, t/min"),
                       ("altura", 1, "acero sobre el orificio, mm"), ("carga", 1, "carga motriz, mm"))
            for ax, (campo, factor, rotulo) in zip(lienzo.ejes, paneles):
                for i, (nombre, r) in enumerate(lista):
                    ax.plot(r.t / 60, getattr(r, campo) * factor, color=cols[i % len(cols)], lw=1.8,
                            label=f"{nombre} ({r.tiempo / 60:.1f} min)")
                ax.set_ylabel(rotulo)
                ax.set_ylim(bottom=0)
            if len(lista) > 1:
                lienzo.ejes[0].legend(loc="upper right", fontsize=7.5)
            for ax in lienzo.ejes[-2:]:
                ax.set_xlabel("tiempo, min")
        lienzo.draw_idle()

    def _dibujar_esquema(self):
        r = self.resultado
        if r is None:
            return
        c = r.config
        i = min(len(r.t) - 1, int(round(self.instante.value() / 1000 * (len(r.t) - 1))))
        sobre = c.acero_inicial - c.talon
        masas = np.linspace(0, sobre * 1.15, 80)
        h = np.array([c.recipiente.altura(m) for m in masas])
        radio = np.array([math.sqrt(c.recipiente.area_superficie(max(m, sobre * 0.01)) / math.pi) * 1000 for m in masas])
        nivel = float(r.altura[i])
        with matplotlib.rc_context(tema.estilo_matplotlib()):
            self.lienzo_esquema.limpiar()
            ax = self.lienzo_esquema.ejes[0]
            dentro = h <= nivel
            ax.fill_betweenx(h[dentro], -radio[dentro], radio[dentro], color=P["ACERO_LIQUIDO"], lw=0)
            if dentro.any() and nivel > 0:
                rn = float(np.interp(nivel, h, radio))
                ax.fill_betweenx([h[dentro][-1], nivel], [-radio[dentro][-1], -rn], [radio[dentro][-1], rn], color=P["ACERO_LIQUIDO"], lw=0)
            ax.plot(radio, h, color=P["CORAZA"], lw=2)
            ax.plot(-radio, h, color=P["CORAZA"], lw=2)
            ax.plot([-radio[0], radio[0]], [0, 0], color=P["CORAZA"], lw=2)
            d = c.paso.diametro
            caida = max(c.caida, 150.0)
            ax.plot([-d / 2, -d / 2], [0, -caida], color=P["TEXTO_3"], lw=1.4)
            ax.plot([d / 2, d / 2], [0, -caida], color=P["TEXTO_3"], lw=1.4)
            if r.caudal[i] > 0:
                ax.annotate("", (0, -caida - 400), (0, -caida), arrowprops=dict(arrowstyle="-|>", color=P["ACERO_TEXTO"], lw=2))
            ax.plot([radio.max() * 1.15] * 2, [-c.caida, nivel], color=P["ACERO_TEXTO"], lw=1.4)
            ax.annotate(f"carga {r.carga[i]:.0f} mm", (radio.max() * 1.15, 0.5 * (nivel - c.caida)), xytext=(6, 0),
                        textcoords="offset points", va="center", color=P["ACERO_TEXTO"], fontsize=9)
            nd = float(r.nivel_destino[i])
            if not math.isnan(nd) and nd > 0:
                cp = c.aguas_abajo.contrapresion(c.aguas_abajo.tundish.masa(nd) if hasattr(c.aguas_abajo, "tundish") else 0.0)
                ax.axhline(-c.caida + cp, color=P["AVISO"], lw=1, ls="--")
                ax.annotate(f"nivel del distribuidor: {cp:.0f} mm sobre la salida", (-radio.max(), -c.caida + cp), xytext=(0, 3),
                            textcoords="offset points", color=P["AVISO"], fontsize=8)
            ax.set_aspect("equal")
            ax.grid(False)
            ax.set_xticks([])
            ax.set_ylabel("altura sobre el orificio, mm")
            forma = {"prismatica": "prismático", "troncoconica": "troncocónico", "tabulada": "de la planta"}.get(c.recipiente.forma, "")
            ax.set_title(f"Recipiente equivalente ({forma}): {r.masa[i]:.1f} t a los {r.t[i] / 60:.1f} min", loc="left")
        self.rotulo_instante.setText(f"Instante: {r.t[i]:.0f} s de {r.tiempo:.0f} s  ·  caudal {r.caudal[i] * 60:.1f} t/min  ·  "
                                     f"acero sobre el orificio {r.altura[i]:.0f} mm")
        self.lienzo_esquema.draw_idle()

    def calcular_sensibilidad(self) -> bool:
        try:
            e = self.escenario()
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                d0 = es.paso_de(e).diametro
                diametros = np.linspace(0.6 * d0, 1.6 * d0, 11)
                t_d = []
                for d in diametros:
                    x = copy.deepcopy(e)
                    x["paso"] = {"diametro_mm": float(d)}
                    t_d.append(es.correr(x, dt=1.0).tiempo)
                cd0 = e["hidraulica"].get("cd", 0.75)
                cds = np.linspace(max(0.3, cd0 - 0.25), min(1.0, cd0 + 0.2), 10)
                t_c = []
                for cd in cds:
                    x = copy.deepcopy(e)
                    x["hidraulica"].update(modo="cd", cd=float(cd))
                    t_c.append(es.correr(x, dt=1.0).tiempo)
            finally:
                QApplication.restoreOverrideCursor()
        except Exception as error:  # noqa: BLE001
            QMessageBox.warning(self, "Modelo de vaciado", f"No se pudo calcular la sensibilidad.\n{error}")
            return False
        self.sensibilidad = (diametros, np.array(t_d), cds, np.array(t_c))
        with matplotlib.rc_context(tema.estilo_matplotlib()):
            self.lienzo_sensibilidad.limpiar()
            ax = self.lienzo_sensibilidad.ejes[0]
            ax.plot(diametros, np.array(t_d) / 60, "o-", color=P["TINTA"], lw=1.6)
            ax.axvline(d0, color=P["ACERO_TEXTO"], lw=1, ls="--")
            ax.set_xlabel("diámetro del orificio, mm")
            ax.set_ylabel("tiempo de vaciado, min")
            ax.set_title("Diámetro (t ∝ 1/D²)", loc="left")
            ax = self.lienzo_sensibilidad.ejes[1]
            ax.plot(cds, np.array(t_c) / 60, "o-", color=P["TINTA"], lw=1.6)
            if e["hidraulica"].get("modo", "cd") == "cd":
                ax.axvline(cd0, color=P["ACERO_TEXTO"], lw=1, ls="--")
            ax.set_xlabel("coeficiente de descarga")
            ax.set_ylabel("tiempo de vaciado, min")
            ax.set_title("Coeficiente de descarga (t ∝ 1/C_d)", loc="left")
        self.lienzo_sensibilidad.draw_idle()
        return True

    # -- comparación --------------------------------------------------------------------------------------------------------
    def anadir_a_comparacion(self):
        if self.resultado is not None:
            self.comparados.append((self.resultado.nombre, self.resultado))
            self._dibujar_comparacion()

    def vaciar_comparacion(self):
        self.comparados.clear()
        self._dibujar_comparacion()

    def _dibujar_comparacion(self):
        cols = colores()
        with matplotlib.rc_context(tema.estilo_matplotlib()):
            self.lienzo_comparar.limpiar()
            a, b = self.lienzo_comparar.ejes
            for i, (nombre, r) in enumerate(self.comparados):
                a.plot(r.t / 60, r.masa, color=cols[i % len(cols)], lw=1.8, label=f"{nombre} ({r.tiempo / 60:.1f} min)")
                b.barh(i, r.tiempo / 60, color=cols[i % len(cols)])
            a.set_xlabel("tiempo, min")
            a.set_ylabel("acero en el recipiente, t")
            a.set_ylim(bottom=0)
            if self.comparados:
                a.legend(loc="upper right", fontsize=7.5)
                b.set_yticks(range(len(self.comparados)), [n[:28] for n, _ in self.comparados], fontsize=7.5)
            b.set_xlabel("tiempo de vaciado, min")
            b.invert_yaxis()
        self.lienzo_comparar.draw_idle()

    # -- archivos -----------------------------------------------------------------------------------------------------------
    def abrir(self):
        ruta, _ = QFileDialog.getOpenFileName(self, "Abrir escenario", str(raiz() / "ejemplos" / self.tipo), "Escenario (*.json)")
        if ruta:
            self.abrir_ruta(ruta)

    def abrir_ruta(self, ruta) -> bool:
        try:
            self.poner_escenario(es.abrir(ruta))
        except Exception as error:  # noqa: BLE001
            QMessageBox.warning(self, "Modelo de vaciado", f"No se pudo abrir el escenario.\n{error}")
            return False
        return self.calcular()

    def guardar(self):
        ruta, _ = QFileDialog.getSaveFileName(self, "Guardar escenario", f"{self.tipo}.json", "Escenario (*.json)")
        if ruta:
            self.guardar_en(ruta)

    def guardar_en(self, ruta):
        es.guardar(self.escenario(), ruta)

    def exportar(self, tipo: str):
        if self.resultado is None:
            return
        filtro = {"xlsx": "Excel (*.xlsx)", "pdf": "PDF (*.pdf)", "csv": "CSV (*.csv)"}[tipo]
        ruta, _ = QFileDialog.getSaveFileName(self, "Exportar", f"vaciado_{self.tipo}.{tipo}", filtro)
        if ruta:
            try:
                self.exportar_en(ruta)
            except Exception as error:  # noqa: BLE001
                QMessageBox.warning(self, "Modelo de vaciado", f"No se pudo escribir el archivo.\n{error}")

    def exportar_en(self, ruta):
        ruta = Path(ruta)
        if ruta.suffix.lower() == ".xlsx":
            escribir_excel(self.escenario_corrido, self.resultado, ruta)
        elif ruta.suffix.lower() == ".pdf":
            escribir_pdf(self.escenario_corrido, self.resultado, ruta)
        else:
            escribir_csv(self.resultado, ruta)
