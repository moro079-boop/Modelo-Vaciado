"""La ventana del programa (PySide6) y la página del horno con su cavidad 3D. El cálculo vive en ``simulacion``, ``escenario``,
``escenarios`` y ``flujo``, sin Qt.

Dos escenarios, uno por página: «Horno (EAF) → olla» (cálculo directo con los datos del usuario, o la cavidad 3D de la planta con
basculado) y «Olla → distribuidor» (``ventana_tiempo.PaginaTiempo``). El aspecto y el acomodo los fija el diseño
(``interfaz/tema.py`` y ``tema_qt.py``).

Página del horno con la cavidad 3D. Izquierda: el escenario (planta, cargas, desgaste, piquera, hidráulica, basculado). Centro: pestañas «Colada» (las cuatro series
en el tiempo), «Corte» (el horno inclinado en el instante elegido), «Límites» (toneladas límite por ángulo) y «Comparar» (los
escenarios guardados en la sesión). Derecha: resultado y avisos. Abajo: abrir, guardar y exportar.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import matplotlib
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.patches import Polygon, Rectangle
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtWidgets import (QApplication, QCheckBox, QDoubleSpinBox, QFileDialog, QHBoxLayout,
                               QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QScrollArea, QSlider, QTabWidget,
                               QVBoxLayout, QWidget)

from .horno3d import cavidad_general as cg
from .horno3d.desgaste import Desgaste
from .interfaz import tema, tema_qt
from .interfaz.widgets import Selector, boton
from .ventana_formulario import botonera, columna_derecha, con_barra, escala, formulario
from .rutas import raiz
from . import FORMATO_ESCENARIO, VERSION_MODELO
from .datos import cargar, plantas_con_datos
from .escenario import abrir, correr, planta_de
from .reporte import AVISO, escribir_csv, escribir_excel, escribir_pdf, filas_de_resultado
from .ventana_tiempo import PaginaTiempo, colores

NOMBRE_APP = "TapFlow"          # nombre del programa (decisión del usuario del 2026-11-24)
RAIZ = raiz()
RECURSOS = RAIZ / "modelo_vaciado" / "interfaz" / "recursos"
P = tema.PALETA


def aplicacion_qt() -> QApplication:
    qapp = QApplication.instance()
    if qapp is None:
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
        qapp = QApplication(sys.argv[:1])
        qapp.setApplicationName(NOMBRE_APP)
        qapp.setApplicationVersion(VERSION_MODELO)
    return qapp


def _numero(minimo, maximo, valor, paso=1.0, decimales=0, sufijo="") -> QDoubleSpinBox:
    s = QDoubleSpinBox()
    s.setRange(minimo, maximo)
    s.setDecimals(decimales)
    s.setSingleStep(paso)
    s.setValue(valor)
    s.setSuffix(sufijo)
    s.setKeyboardTracking(False)
    s.setAlignment(Qt.AlignmentFlag.AlignRight)
    return s


class Lienzo(FigureCanvasQTAgg):
    def __init__(self, filas=1, columnas=1):
        with matplotlib.rc_context(tema.estilo_matplotlib()):
            self.figura = Figure(figsize=(8, 5), layout="constrained")
            self.ejes = np.atleast_1d(self.figura.subplots(filas, columnas, sharex=filas > 1)).ravel()
        super().__init__(self.figura)

    def limpiar(self):
        for ax in self.ejes:
            ax.clear()


class PaginaHorno(QWidget):
    """Vaciado del horno por la piquera."""

    def __init__(self, ruta_escenario: Path | str | None = None):
        super().__init__()
        self.resultado = None
        self.escenario_corrido: dict | None = None
        self.comparados: list = []          # (nombre, Resultado)
        self.observadores: list = []        # funciones que reciben la página tras cada cálculo (indicadores de la cabecera)
        self.esta_obsoleto = False
        self._cargando = False
        self._armar()
        if ruta_escenario:
            self.poner_escenario(abrir(ruta_escenario))
        else:
            self._valores_de_la_planta()
        self.calcular()

    # -- construcción --------------------------------------------------------------------------------------------------------
    def _armar(self):
        fila = QHBoxLayout(self)

        # izquierda: el escenario
        panel = QWidget()
        col = QVBoxLayout(panel)
        col.setContentsMargins(8, 8, 22, 8)
        self.nombre = QLineEdit("Escenario")
        self.planta = Selector()
        self.planta.addItems(plantas_con_datos())
        self.acero_inicial = _numero(1, 2000, 450, 5, 0, " t")
        self.acero_final = _numero(0, 2000, 150, 5, 0, " t")
        self.escoria = _numero(0, 200, 0, 1, 0, " t")
        f = formulario(col, "Colada")
        f.addRow("Nombre", self.nombre)
        f.addRow("Planta", self.planta)
        f.addRow("Acero al inicio", self.acero_inicial)
        f.addRow("Acero al final (talón)", self.acero_final)
        f.addRow("Escoria", self.escoria)

        self.pared = _numero(0, 100, 0, 5, 1, " %")
        self.piso = _numero(0, 100, 0, 5, 1, " %")
        f = formulario(col, "Desgaste del revestimiento (capa de trabajo)")
        f.addRow("Pared", self.pared)
        f.addRow("Piso", self.piso)

        self.diametro = _numero(50, 500, 200, 5, 0, " mm")
        self.acortamiento = _numero(0, 1000, 0, 10, 0, " mm")
        f = formulario(col, "Piquera")
        f.addRow("Diámetro del canal", self.diametro)
        f.addRow("Boca más abajo (bloque gastado)", self.acortamiento)

        self.modo = Selector()
        self.modo.addItem("Coeficiente de descarga", "cd")
        self.modo.addItem("Pérdidas explícitas", "perdidas")
        self.referencia = Selector()
        self.referencia.addItem("la boca del canal", "boca")
        self.referencia.addItem("la salida del canal", "salida")
        self.cd = _numero(0.1, 1.5, 0.731, 0.005, 3)
        self.k_entrada = _numero(0, 5, 0.5, 0.05, 2)
        self.rugosidad = _numero(0.01, 20, 1.0, 0.1, 2, " mm")
        self.viscosidad = _numero(0.001, 0.05, 0.006, 0.0005, 4, " Pa·s")
        f = formulario(col, "Hidráulica del canal")
        f.addRow("Modelo", self.modo)
        f.addRow("Carga medida hasta", self.referencia)
        f.addRow("Coeficiente de descarga", self.cd)
        f.addRow("Pérdida de entrada K", self.k_entrada)
        f.addRow("Rugosidad", self.rugosidad)
        f.addRow("Viscosidad del acero", self.viscosidad)

        self.tipo = Selector()
        self.tipo.addItem("Continuo: lo que permite el panel", "carga_segura")
        self.tipo.addItem("Por escalones", "escalones")
        self.tipo.addItem("Ángulo fijo", "fijo")
        self.pasos = QLineEdit("2:380, 5:292, 8:222, 11:173, 15:150")
        self.pasos.setToolTip("ángulo:toneladas hasta las que el horno se queda en ese ángulo, separados por comas")
        self.angulo_fijo = _numero(0, 45, 8, 0.5, 1, "°")
        self.velocidad = _numero(0.05, 20, 1.0, 0.1, 2, " °/s")
        self.instantaneo = QCheckBox("Basculado instantáneo")
        f = formulario(col, "Basculado")
        f.addRow("Forma", self.tipo)
        f.addRow("Escalones (ángulo:t)", self.pasos)
        f.addRow("Ángulo", self.angulo_fijo)
        f.addRow("Velocidad", self.velocidad)
        f.addRow("", self.instantaneo)

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

        # centro: pestañas
        self.pestanas = QTabWidget()
        self.lienzo_colada = Lienzo(2, 2)
        self.pestanas.addTab(con_barra(self.lienzo_colada), "Colada")
        corte = QWidget()
        cv = QVBoxLayout(corte)
        self.lienzo_corte = Lienzo()
        self.instante = QSlider(Qt.Orientation.Horizontal)
        self.instante.setRange(0, 1000)
        self.instante.valueChanged.connect(self._dibujar_corte)
        self.rotulo_instante = QLabel()
        cv.addWidget(con_barra(self.lienzo_corte), 1)
        cv.addWidget(self.rotulo_instante)
        cv.addWidget(self.instante)
        self.pestanas.addTab(corte, "Corte")
        self.lienzo_limites = Lienzo()
        self.pestanas.addTab(con_barra(self.lienzo_limites), "Límites")
        comparar = QWidget()
        kv = QVBoxLayout(comparar)
        self.lienzo_comparar = Lienzo(2, 2)
        kb = QHBoxLayout()
        b1, b2 = QPushButton("Añadir el escenario actual"), QPushButton("Vaciar la comparación")
        b1.clicked.connect(self.anadir_a_comparacion)
        b2.clicked.connect(self.vaciar_comparacion)
        kb.addWidget(b1)
        kb.addWidget(b2)
        kb.addStretch(1)
        kv.addLayout(kb)
        kv.addWidget(con_barra(self.lienzo_comparar), 1)
        self.pestanas.addTab(comparar, "Comparar")
        self.pestanas.addTab(self._armar_mapas(), "Mapas")
        fila.addWidget(self.pestanas, 1)

        # derecha: resultado
        der = QWidget()
        dv = QVBoxLayout(der)
        self.titular = QLabel("—")
        self.titular.setObjectName("Titular")
        self.obsoleto = QLabel("Datos cambiados: pulse «Calcular» (F5) para actualizar el resultado.")
        self.obsoleto.setObjectName("Obsoleto")
        self.obsoleto.setWordWrap(True)
        self.obsoleto.hide()
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
        self.rotulo_titular = QLabel("Tiempo de vaciado")
        dv.addWidget(self.rotulo_titular)
        dv.addWidget(self.titular)
        dv.addWidget(self.obsoleto)
        dv.addWidget(self.subtitular)
        dv.addWidget(self.tabla)
        dv.addWidget(self.avisos)
        dv.addStretch(1)
        dv.addWidget(botonera(((("Abrir…", "Abrir un escenario (Ctrl+O)", self.abrir),
                                 ("Guardar…", "Guardar el escenario (Ctrl+S)", self.guardar)),
                                (("Excel…", "Exportar a Excel (Ctrl+E)", lambda: self.exportar("xlsx")),
                                 ("PDF…", "Exportar a PDF (Ctrl+P)", lambda: self.exportar("pdf")),
                                 ("CSV…", "Exportar la serie en CSV", lambda: self.exportar("csv"))))))
        dv.addWidget(pie)
        fila.addWidget(columna_derecha(der))

        self.planta.currentIndexChanged.connect(self._valores_de_la_planta)
        for w in (self.modo, self.tipo):
            w.currentIndexChanged.connect(self._habilitar)
        self.instantaneo.toggled.connect(self._habilitar)
        self._habilitar()
        # un resultado que ya no corresponde a los datos en pantalla se marca (el cálculo con la cavidad tarda ~0,6 s: no se
        # recalcula en cada cambio, como sí la página del cálculo directo)
        for w in (self.acero_inicial, self.acero_final, self.escoria, self.pared, self.piso, self.diametro, self.acortamiento,
                  self.cd, self.k_entrada, self.rugosidad, self.viscosidad, self.angulo_fijo, self.velocidad):
            w.valueChanged.connect(self._marcar_obsoleto)
        for w in (self.planta, self.modo, self.referencia, self.tipo):
            w.currentIndexChanged.connect(self._marcar_obsoleto)
        self.pasos.textChanged.connect(self._marcar_obsoleto)
        self.instantaneo.toggled.connect(self._marcar_obsoleto)

    def _marcar_obsoleto(self, *_):
        if self._cargando or self.resultado is None:
            return
        self.obsoleto.show()
        self.esta_obsoleto = True
        for f in self.observadores:
            f(self)

    def _armar_mapas(self) -> QWidget:
        """Pestaña «Mapas»: tiempo a ángulo fijo y tiempo por colada con el canal creciendo."""
        hoja = QWidget()
        v = QVBoxLayout(hoja)
        fila = QHBoxLayout()
        self.mapa_coladas = _numero(10, 2000, 150, 10, 0)
        self.mapa_crecimiento = _numero(0, 5, 0.3, 0.05, 2, " mm/colada")
        self.mapa_dmax = _numero(50, 500, 260, 5, 0, " mm")
        for texto, w in (("Coladas", self.mapa_coladas), ("Crecimiento del canal", self.mapa_crecimiento), ("Diámetro de cambio", self.mapa_dmax)):
            fila.addWidget(QLabel(texto))
            fila.addWidget(w)
        fila.addWidget(boton("Calcular los mapas", self.calcular_mapas, "acento"))
        fila.addStretch(1)
        v.addLayout(fila)
        nota = QLabel("El crecimiento del canal por colada no tiene dato de planta: el valor es un supuesto para ver la tendencia.")
        nota.setStyleSheet(f"color: {P['AVISO']}; font-size: 11px;")
        v.addWidget(nota)
        self.lienzo_mapas = Lienzo(1, 2)
        v.addWidget(con_barra(self.lienzo_mapas), 1)
        self.mapa_resultado = None
        return hoja

    def calcular_mapas(self) -> bool:
        from . import mapa

        try:
            e = self.escenario()
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                angulos = mapa.por_angulo(e, dt=1.0)
                coladas = mapa.por_colada(e, int(self.mapa_coladas.value()), self.mapa_crecimiento.value(),
                                          diametro_maximo=self.mapa_dmax.value(), cada=max(1, int(self.mapa_coladas.value()) // 60), dt=1.0)
            finally:
                QApplication.restoreOverrideCursor()
        except Exception as error:  # noqa: BLE001
            QMessageBox.warning(self, NOMBRE_APP, f"No se pudieron calcular los mapas.\n{error}")
            return False
        self.mapa_resultado = (angulos, coladas)
        with matplotlib.rc_context(tema.estilo_matplotlib()):
            self.lienzo_mapas.limpiar()
            ax = self.lienzo_mapas.ejes[0]
            ok = [f for f in angulos if f.llega and not f.invade_panel]
            mal = [f for f in angulos if f.llega and f.invade_panel]
            ax.plot([f.angulo for f in angulos if f.llega], [f.tiempo for f in angulos if f.llega], color=P["TINTA"], lw=1.5)
            ax.plot([f.angulo for f in ok], [f.tiempo for f in ok], "o", color=P["CORRECTO"], label="respeta el panel")
            ax.plot([f.angulo for f in mal], [f.tiempo for f in mal], "o", color=P["ALARMA"], label="el baño inicial invade el panel")
            for f in angulos:
                if not f.llega:
                    ax.annotate(f"quedan {f.queda:.0f} t", (f.angulo, f.tiempo), fontsize=7, color=P["ALARMA"])
            if self.resultado is not None:
                ax.axhline(self.resultado.tiempo, color="#1F55D0", ls="--", lw=1)
                ax.annotate(f"escenario: {self.resultado.tiempo:.0f} s", (0, self.resultado.tiempo), xytext=(4, 3),
                            textcoords="offset points", color="#1F55D0", fontsize=8)
            ax.set_xlabel("ángulo fijo, grados")
            ax.set_ylabel("tiempo de vaciado, s")
            ax.set_title("Tiempo a ángulo fijo", loc="left")
            ax.legend(loc="upper right")
            ax = self.lienzo_mapas.ejes[1]
            ax.plot([c["colada"] for c in coladas], [c["tiempo_s"] for c in coladas], color=P["TINTA"], lw=1.8)
            ax2 = ax.twinx()
            ax2.plot([c["colada"] for c in coladas], [c["diametro"] for c in coladas], color=P["AVISO"], lw=1, ls="--")
            ax2.set_ylabel("diámetro del canal, mm", color=P["AVISO"])
            ax2.grid(False)
            ax.set_xlabel("colada de la piquera")
            ax.set_ylabel("tiempo de vaciado, s")
            ax.set_title("Vida de la piquera (escenario)", loc="left")
        self.lienzo_mapas.draw_idle()
        return True

    def _habilitar(self):
        cd = self.modo.currentData() == "cd"
        self.cd.setEnabled(cd)
        for w in (self.k_entrada, self.rugosidad, self.viscosidad):
            w.setEnabled(not cd)
        tipo = self.tipo.currentData()
        self.pasos.setEnabled(tipo == "escalones")
        self.angulo_fijo.setEnabled(tipo == "fijo")
        self.velocidad.setEnabled(not self.instantaneo.isChecked())

    def _valores_de_la_planta(self):
        """Al elegir planta: su piquera, su Cd, su velocidad y su colada nominal."""
        if self._cargando:
            return
        d = cargar(self.planta.currentText())
        self.diametro.setValue(d.piquera.diametro)
        self.cd.setValue(d.cd)
        self.velocidad.setValue(d.velocidad_basculado)
        self.angulo_fijo.setMaximum(d.angulo_maximo)

    # -- escenario ↔ controles ---------------------------------------------------------------------------------------------
    def escenario(self) -> dict:
        h = {"modo": self.modo.currentData(), "referencia": self.referencia.currentData()}
        if h["modo"] == "cd":
            h["cd"] = self.cd.value()
        else:
            h.update(k_entrada=self.k_entrada.value(), rugosidad=self.rugosidad.value(), viscosidad=self.viscosidad.value())
        b = {"tipo": self.tipo.currentData(), "velocidad": "instantaneo" if self.instantaneo.isChecked() else self.velocidad.value()}
        if b["tipo"] == "escalones":
            try:
                b["pasos"] = [[float(a), float(m)] for a, m in (par.split(":") for par in self.pasos.text().split(",") if par.strip())]
            except ValueError as error:
                raise ValueError("Los escalones se escriben como ángulo:toneladas separados por comas, por ejemplo 2:380, 5:292.") from error
            if not b["pasos"]:
                raise ValueError("Falta al menos un escalón.")
        if b["tipo"] == "fijo":
            b["angulo"] = self.angulo_fijo.value()
        if self.acero_final.value() >= self.acero_inicial.value():
            raise ValueError("El acero al final debe ser menor que el acero al inicio.")
        return {"formato": FORMATO_ESCENARIO, "nombre": self.nombre.text().strip() or "Escenario", "planta": self.planta.currentText(),
                "desgaste": {"pared": self.pared.value(), "piso": self.piso.value()},
                "acero_inicial_t": self.acero_inicial.value(), "acero_final_t": self.acero_final.value(), "escoria_t": self.escoria.value(),
                "piquera": {"diametro": self.diametro.value(), "acortamiento": self.acortamiento.value()},
                "hidraulica": h, "basculado": b}

    def poner_escenario(self, e: dict):
        self._cargando = True
        try:
            d = cargar(e["planta"])
            self.nombre.setText(e.get("nombre", "Escenario"))
            self.planta.setCurrentText(e["planta"])
            self.acero_inicial.setValue(e["acero_inicial_t"])
            self.acero_final.setValue(e["acero_final_t"])
            self.escoria.setValue(e.get("escoria_t", 0.0))
            self.pared.setValue(e.get("desgaste", {}).get("pared", 0.0))
            self.piso.setValue(e.get("desgaste", {}).get("piso", 0.0))
            p = e.get("piquera", {})
            self.diametro.setValue(p.get("diametro") or d.piquera.diametro)
            self.acortamiento.setValue(p.get("acortamiento", 0.0))
            h = e.get("hidraulica", {})
            self.modo.setCurrentIndex(self.modo.findData(h.get("modo", "cd")))
            self.referencia.setCurrentIndex(self.referencia.findData(h.get("referencia", "boca")))
            self.cd.setValue(h.get("cd", d.cd))
            self.k_entrada.setValue(h.get("k_entrada", 0.5))
            self.rugosidad.setValue(h.get("rugosidad", 1.0))
            self.viscosidad.setValue(h.get("viscosidad", 0.006))
            b = e.get("basculado", {})
            self.tipo.setCurrentIndex(self.tipo.findData(b.get("tipo", "carga_segura")))
            if "pasos" in b:
                self.pasos.setText(", ".join(f"{a:g}:{m:g}" for a, m in b["pasos"]))
            self.angulo_fijo.setValue(b.get("angulo", 8.0))
            v = b.get("velocidad", d.velocidad_basculado)
            self.instantaneo.setChecked(v in ("instantaneo", None))
            if v not in ("instantaneo", None):
                self.velocidad.setValue(float(v))
        finally:
            self._cargando = False
        self._habilitar()

    # -- cálculo y dibujo ---------------------------------------------------------------------------------------------------
    def calcular(self) -> bool:
        try:
            e = self.escenario()
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                r = correr(e)
            finally:
                QApplication.restoreOverrideCursor()
        except Exception as error:  # noqa: BLE001  (se muestra al usuario; la ventana sigue)
            self.titular.setText("—")
            self.subtitular.setText("")
            self.tabla.setText("")
            self.avisos.setText(f"<span style='color:{P['ALARMA']}'><b>No se pudo calcular.</b> {error}</span>")
            for f in self.observadores:
                f(self)
            return False
        self.resultado, self.escenario_corrido = r, e
        self.obsoleto.hide()
        self.esta_obsoleto = False
        self.titular.setText(f"{r.tiempo:.0f} s")
        self.subtitular.setText(f"{r.tiempo / 60:.2f} min para {r.colado:.0f} t · caudal medio {r.caudal_medio * 60:.1f} t/min")
        self.tabla.setText("<table cellspacing='3'>" + "".join(
            f"<tr><td style='color:{P['TEXTO_2']}'>{a}</td><td align='right'><b>{b}</b></td></tr>" for a, b in filas_de_resultado(r)[4:10]) + "</table>")
        if r.eventos:
            self.avisos.setText("".join(f"<p style='color:{P['ALARMA']}'><b>Aviso a los {t:.0f} s.</b> {texto}</p>" for t, texto in r.eventos))
        else:
            self.avisos.setText(f"<span style='color:{P['CORRECTO']}'><b>Sin avisos.</b> El baño respeta el panel y la altura mínima sobre la boca.</span>"
                                if r.motivo_fin.startswith("se alcanzó") else f"<span style='color:{P['ALARMA']}'><b>{r.motivo_fin}.</b></span>")
        self._dibujar_series(self.lienzo_colada, [(r.nombre, r)])
        self._dibujar_limites()
        self._dibujar_corte()
        for f in self.observadores:
            f(self)
        return True

    def tiempo_texto(self) -> str:
        if self.resultado is None:
            return "—"
        t = self.resultado.tiempo
        return f"{int(t // 60)} min {int(round(t % 60)):02d} s"

    def _dibujar_series(self, lienzo: Lienzo, lista):
        with matplotlib.rc_context(tema.estilo_matplotlib()):
            lienzo.limpiar()
            paneles = (("masa", 1, "acero en el horno, t"), ("angulo", 1, "ángulo de basculado, grados"),
                       ("altura", 1, "acero sobre la boca, mm"), ("caudal", 60, "caudal, t/min"))
            for ax, (campo, factor, rotulo) in zip(lienzo.ejes, paneles):
                for i, (nombre, r) in enumerate(lista):
                    ax.plot(r.t / 60, getattr(r, campo) * factor, color=colores()[i % len(colores())], lw=1.8,
                            label=f"{nombre} ({r.tiempo / 60:.1f} min)")
                ax.set_ylabel(rotulo)
                ax.set_ylim(bottom=0)
            if lista:
                c = lista[0][1].contexto
                lienzo.ejes[2].axhline(c.altura_minima, color=P["ALARMA"], lw=1, ls="--")
                lienzo.ejes[2].annotate(f"altura mínima {c.altura_minima:.0f} mm", (0, c.altura_minima), xytext=(4, 3),
                                        textcoords="offset points", color=P["ALARMA"], fontsize=8)
                if len(lista) > 1:
                    lienzo.ejes[0].legend(loc="lower left", fontsize=7.5)
            for ax in lienzo.ejes[2:]:
                ax.set_xlabel("tiempo, min")
        lienzo.draw_idle()

    def _dibujar_limites(self):
        r = self.resultado
        c = r.contexto
        angulos = np.arange(0.0, cargar(self.escenario_corrido["planta"]).angulo_maximo + 0.01, 0.5)
        with matplotlib.rc_context(tema.estilo_matplotlib()):
            self.lienzo_limites.limpiar()
            ax = self.lienzo_limites.ejes[0]
            if c.panel is not None:
                ax.plot(angulos, [c.carga_segura(a) for a in angulos], color=P["AVISO"], lw=2, label=f"carga segura: baño a {c.distancia_panel:g} mm del panel")
            ax.plot(angulos, [c.carga_minima(a) for a in angulos], color=P["ALARMA"], lw=2, label=f"carga mínima: {c.altura_minima:.0f} mm de acero sobre la boca")
            ax.plot(angulos, [c.no_drenable(a) for a in angulos], color=P["TEXTO_3"], lw=1.5, ls="--", label="acero que no puede salir")
            ax.plot(r.angulo, r.masa, color=P["TINTA"], lw=2.2, label="esta colada")
            ax.set_xlabel("ángulo de basculado, grados")
            ax.set_ylabel("toneladas de acero en el horno")
            ax.set_ylim(bottom=0)
            ax.legend(loc="upper right")
            ax.set_title("La colada debe quedar entre la carga segura y la carga mínima", loc="left")
        self.lienzo_limites.draw_idle()

    def _dibujar_corte(self):
        r, e = self.resultado, self.escenario_corrido
        if r is None:
            return
        i = min(len(r.t) - 1, int(round(self.instante.value() / 1000 * (len(r.t) - 1))))
        ang, c = float(r.angulo[i]), r.contexto
        planta = planta_de(e["planta"])
        g = e.get("desgaste", {})
        contorno = cg.contorno_en_el_eje(planta, Desgaste(g.get("pared", 0.0), 0.0))
        if g.get("piso", 0.0) > 0.0:        # el fondo gastado, perpendicular a su superficie (como la cavidad)
            u = cg.retroceso_piso(planta, Desgaste(0.0, g["piso"]))
            x = contorno[:, 0]
            dentro = (x > x.min() + 1) & (x < x.max() - 1) & (np.abs(np.gradient(contorno[:, 1], np.maximum(np.gradient(x), 1e-6))) < 5)
            contorno[dentro, 1] = cg.piso_gastado(planta, x[dentro], np.zeros(dentro.sum()), cg.leer_ajuste(planta), u)
        t = math.radians(ang)
        giro = lambda x, y: (x * math.cos(t) - y * math.sin(t), x * math.sin(t) + y * math.cos(t))  # noqa: E731
        gx, gy = giro(contorno[:, 0], contorno[:, 1])
        xb, yb = c.piquera.x, c.piquera.y_boca
        bx, by = giro(xb, yb)
        nivel = by + float(r.altura[i])
        with matplotlib.rc_context(tema.estilo_matplotlib()):
            self.lienzo_corte.limpiar()
            ax = self.lienzo_corte.ejes[0]
            cavidad = Polygon(np.column_stack([gx, gy]), closed=True, fc="none", ec="none")
            ax.add_patch(cavidad)
            acero = Rectangle((gx.min() - 500, gy.min() - 3000), np.ptp(gx) + 1000, nivel - gy.min() + 3000, fc=P["ACERO_LIQUIDO"], ec="none")
            ax.add_patch(acero)
            acero.set_clip_path(cavidad)
            ax.plot(gx, gy, color=P["CORAZA"], lw=2)
            cx, cy = giro(np.array([xb - c.diametro / 2, xb - c.diametro / 2, xb + c.diametro / 2, xb + c.diametro / 2]),
                          np.array([yb, c.piquera.y_salida, c.piquera.y_salida, yb]))
            ax.plot(cx, cy, color=P["TEXTO_3"], lw=1.2)
            ax.plot([bx], [by], "o", color=P["ALARMA"], ms=6)
            ax.plot([gx.min() - 700, bx], [by, by], color=P["ALARMA"], lw=0.8, ls=":")
            ax.plot([gx.min() - 500, gx.min() - 500], [by, nivel], color=P["ACERO_TEXTO"], lw=1.5)
            ax.annotate(f"{r.altura[i]:.0f} mm", (gx.min() - 500, 0.5 * (by + nivel)), xytext=(-10, 0), textcoords="offset points",
                        ha="right", va="center", color=P["ACERO_TEXTO"], fontsize=10)
            if c.panel is not None:
                px, py = giro(*c.panel)
                ax.plot([px], [py], "s", color=P["AVISO"], ms=6)
            ax.set_aspect("equal")
            ax.set_xlim(gx.min() - 1800, gx.max() + 600)
            ax.set_ylim(min(cy.min(), gy.min()) - 300, gy.max() + 300)
            ax.grid(False)
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_title(f"Corte por el eje, la piquera a la izquierda — {ang:.1f}°, {r.masa[i]:.0f} t en el horno", loc="left")
        self.rotulo_instante.setText(f"Instante: {r.t[i]:.0f} s de {r.tiempo:.0f} s  ·  caudal {r.caudal[i] * 60:.1f} t/min  ·  "
                                     "● boca de la piquera   ■ esquina del panel refrigerado")
        self.lienzo_corte.draw_idle()

    # -- comparación --------------------------------------------------------------------------------------------------------
    def anadir_a_comparacion(self):
        if self.resultado is not None:
            self.comparados.append((self.resultado.nombre, self.resultado))
            self._dibujar_series(self.lienzo_comparar, self.comparados)

    def vaciar_comparacion(self):
        self.comparados.clear()
        self._dibujar_series(self.lienzo_comparar, [])

    # -- archivos -----------------------------------------------------------------------------------------------------------
    def abrir(self):
        ruta, _ = QFileDialog.getOpenFileName(self, "Abrir escenario de vaciado", str(RAIZ / "ejemplos" / "horno_cavidad_3d"), "Escenario (*.json)")
        if ruta:
            self.abrir_ruta(ruta)

    def abrir_ruta(self, ruta) -> bool:
        try:
            self.poner_escenario(abrir(ruta))
        except Exception as error:  # noqa: BLE001
            QMessageBox.warning(self, NOMBRE_APP, f"No se pudo abrir el escenario.\n{error}")
            return False
        return self.calcular()

    def guardar(self):
        ruta, _ = QFileDialog.getSaveFileName(self, "Guardar escenario de vaciado", "escenario_vaciado.json", "Escenario (*.json)")
        if ruta:
            self.guardar_en(ruta)

    def guardar_en(self, ruta):
        Path(ruta).write_text(json.dumps(self.escenario(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    def exportar(self, tipo: str):
        if self.resultado is None:
            return
        filtro = {"xlsx": "Excel (*.xlsx)", "pdf": "PDF (*.pdf)", "csv": "CSV (*.csv)"}[tipo]
        ruta, _ = QFileDialog.getSaveFileName(self, "Exportar", f"vaciado.{tipo}", filtro)
        if ruta:
            try:
                self.exportar_en(ruta)
            except Exception as error:  # noqa: BLE001
                QMessageBox.warning(self, NOMBRE_APP, f"No se pudo escribir el archivo.\n{error}")

    def exportar_en(self, ruta):
        """Exporta el último escenario calculado según la extensión (.xlsx, .pdf o .csv)."""
        ruta = Path(ruta)
        if ruta.suffix.lower() == ".xlsx":
            escribir_excel(self.escenario_corrido, self.resultado, ruta)
        elif ruta.suffix.lower() == ".pdf":
            escribir_pdf(self.escenario_corrido, self.resultado, ruta)
        else:
            escribir_csv(self.resultado, ruta)


class PaginaHornoOlla(QWidget):
    """Escenario «Horno (EAF) → olla»: cálculo directo con los datos del usuario o la cavidad 3D de la planta con basculado.

    La vista con la cavidad 3D se arma la primera vez que se elige (armar la cavidad tarda unos segundos; ``precalentar`` la
    adelanta en segundo plano al abrir la ventana)."""

    def __init__(self, ruta_escenario: Path | str | None = None):
        from PySide6.QtWidgets import QStackedWidget

        from . import escenarios as es

        super().__init__()
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        fila = QHBoxLayout()
        fila.setContentsMargins(10, 8, 10, 0)
        fila.addWidget(QLabel("Modelo del horno:"))
        self.botones = []
        for i, (texto, ayuda) in enumerate((
                ("Cálculo directo (datos del usuario)", "Tonelaje, altura metalostática y área de paso: el horno como recipiente simple"),
                ("Cavidad 3D de la planta y basculado", "La cavidad del horno de la planta, el ángulo de basculado y los límites del panel"))):
            b = QPushButton(texto)
            b.setObjectName("Subpestana")
            b.setCheckable(True)
            b.setToolTip(ayuda)
            b.clicked.connect(lambda _=False, i=i: self.elegir(i))
            fila.addWidget(b)
            self.botones.append(b)
        fila.addStretch(1)
        v.addLayout(fila)
        self.pila = QStackedWidget()
        self.observadores: list = []
        e = es.abrir(ruta_escenario) if ruta_escenario else None
        detallado = e is not None and e.get("formato") == FORMATO_ESCENARIO
        self.directo = PaginaTiempo("horno_olla", Lienzo, None if detallado else e)
        self.directo.observadores.append(lambda _p: self._avisar())
        self.pila.addWidget(self.directo)
        self._detallado: PaginaHorno | None = None
        self._ruta_detallado = ruta_escenario if detallado else None
        v.addWidget(self.pila, 1)
        self.elegir(1 if detallado else 0)

    @property
    def detallado(self) -> PaginaHorno:
        """La página con la cavidad 3D (se arma al primer uso)."""
        if self._detallado is None:
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                self._detallado = PaginaHorno(self._ruta_detallado)
            finally:
                QApplication.restoreOverrideCursor()
            self._detallado.observadores.append(lambda _p: self._avisar())
            self._detallado.titular.hide()          # el tiempo ya está en los indicadores de la cabecera
            self._detallado.rotulo_titular.hide()
            self.pila.addWidget(self._detallado)
        return self._detallado

    @property
    def actual(self):
        return self.pila.currentWidget()

    def elegir(self, i: int):
        self.pila.setCurrentWidget(self.directo if i == 0 else self.detallado)
        for k, b in enumerate(self.botones):
            b.setChecked(k == i)
        self._avisar()

    def _avisar(self):
        for f in self.observadores:
            f(self)


def indicadores_de(pagina) -> tuple[list[tuple[str, str]], str]:
    """((rótulo, valor) × 4, estado) de lo que la cabecera muestra de la página activa. Estado: «ok», «obsoleto» o «error»."""
    p = pagina.actual if isinstance(pagina, PaginaHornoOlla) else pagina
    r = p.resultado
    vacio = [("Tiempo de vaciado", "—"), ("Caudal medio", "—"), ("Acero vaciado", "—"), ("Comprobación", "—")]
    if r is None:
        return vacio, "error"
    estado = "obsoleto" if getattr(p, "esta_obsoleto", False) else ("error" if "No se pudo" in p.avisos.text() else "ok")
    if isinstance(p, PaginaHorno):
        return [("Tiempo de vaciado", p.tiempo_texto()), ("Caudal medio", f"{r.caudal_medio * 60:.1f} t/min"),
                ("Acero vaciado", f"{r.colado:.0f} t"), ("Ángulo final", f"{r.angulo[-1]:.1f}°")], estado
    from .flujo import torricelli

    t = torricelli(r.config)
    return [("Tiempo de vaciado", p.tiempo_texto()), ("Caudal medio", f"{r.caudal_medio * 60:.1f} t/min"),
            ("Acero vaciado", f"{r.colado:.1f} t"), ("Solución de Torricelli", f"{t / 60:.1f} min" if t else "no aplica")], estado


class _Kpi(QWidget):
    def __init__(self, acento: bool = False):
        from PySide6.QtWidgets import QFrame

        super().__init__()
        self.marco = QFrame(self)
        self.marco.setObjectName("Kpi")
        v = QVBoxLayout(self.marco)
        v.setContentsMargins(14, 6, 14, 6)
        v.setSpacing(0)
        self.rotulo = QLabel("—")
        self.rotulo.setObjectName("KpiRotulo")
        self.valor = QLabel("—")
        self.valor.setObjectName("KpiValorAcento" if acento else "KpiValor")
        v.addWidget(self.rotulo)
        v.addWidget(self.valor)
        capa = QVBoxLayout(self)
        capa.setContentsMargins(0, 0, 0, 0)
        capa.addWidget(self.marco)

    def poner(self, rotulo: str, valor: str, estado: str = "ok"):
        self.rotulo.setText(rotulo.upper())
        self.valor.setText(valor)
        if self.marco.property("estado") != estado:
            self.marco.setProperty("estado", estado)
            self.marco.style().unpolish(self.marco)
            self.marco.style().polish(self.marco)
        self.setToolTip({"obsoleto": "Los datos cambiaron: el resultado no está actualizado (F5 para calcular).",
                         "error": "No se pudo calcular con los datos en pantalla."}.get(estado, ""))


_HILO_PRECALENTADO = None


def precalentar() -> None:
    """Arma en segundo plano, una sola vez por proceso, la tabla de niveles del horno de cada planta con datos de vaciado (lo
    que hace lenta la primera visita a la vista con la cavidad 3D)."""
    global _HILO_PRECALENTADO
    if _HILO_PRECALENTADO is not None:
        return
    import threading

    def trabajo():
        from .escenario import tabla_de

        for planta in plantas_con_datos():
            try:
                tabla_de(planta, cargar(planta))
            except Exception:  # noqa: BLE001  (si falla aquí, fallará con su mensaje al abrir la vista)
                pass

    _HILO_PRECALENTADO = threading.Thread(target=trabajo, name="precalentado", daemon=True)
    _HILO_PRECALENTADO.start()


class Ventana(QMainWindow):
    """El programa: cabecera oscura con la marca y los dos escenarios como pasos, indicadores grandes de la página activa y,
    debajo, la página del escenario."""

    def __init__(self, ruta_escenario: Path | str | None = None):
        from PySide6.QtCore import QTimer
        from PySide6.QtGui import QKeySequence, QShortcut
        from PySide6.QtWidgets import QButtonGroup, QFrame, QStackedWidget

        from . import escenarios as es

        super().__init__()
        self.setWindowTitle(f"{NOMBRE_APP} {VERSION_MODELO}: tiempo de vaciado del horno a la olla y de la olla al distribuidor")
        icono = QIcon(str(RECURSOS / "icono.png"))
        self.icono_cargado = not icono.isNull()
        self.setWindowIcon(icono)

        tipo = None
        if ruta_escenario:
            e = es.abrir(ruta_escenario)
            if e.get("formato") == "lwd_eaf.vaciado.colada/1":
                raise ValueError("Los escenarios de la secuencia olla → distribuidor → moldes quedan fuera del alcance actual de la "
                                 "ventana; se corren con «python vaciado.py --colada».")
            tipo = "horno_olla" if e.get("formato") == FORMATO_ESCENARIO else e.get("tipo")
        self.horno = PaginaHornoOlla(ruta_escenario if tipo == "horno_olla" else None)
        self.olla = PaginaTiempo("olla_distribuidor", Lienzo, es.abrir(ruta_escenario) if tipo == "olla_distribuidor" else None)
        self.paginas_lista = [(self.horno, "Horno (EAF) → olla"), (self.olla, "Olla → distribuidor")]
        self.kpis: list[_Kpi] = []
        for p, _ in self.paginas_lista:
            p.observadores.append(lambda _p: self._actualizar_indicadores())
        self.horno.directo.titular.hide()           # el tiempo ya está en los indicadores de la cabecera
        self.horno.directo.rotulo_titular.hide()
        self.olla.titular.hide()
        self.olla.rotulo_titular.hide()

        central = QWidget()
        central.setObjectName("Fondo")
        capa = QVBoxLayout(central)
        capa.setContentsMargins(0, 0, 0, 0)
        capa.setSpacing(0)
        cab = QFrame()
        cab.setObjectName("Cabecera")
        ch = QHBoxLayout(cab)
        ch.setContentsMargins(16, 10, 16, 10)
        logo = QLabel()
        logo.setPixmap(icono.pixmap(42, 42))
        ch.addWidget(logo)
        marcas = QVBoxLayout()
        marcas.setSpacing(0)
        marca = QLabel(NOMBRE_APP)
        marca.setObjectName("MarcaBarra")
        lema = QLabel("Tiempo de vaciado · balance de masa, Bernoulli y Torricelli")
        lema.setObjectName("LemaBarra")
        marcas.addWidget(marca)
        marcas.addWidget(lema)
        ch.addLayout(marcas)
        ch.addSpacing(28)
        self.pila = QStackedWidget()
        grupo = QButtonGroup(self)
        self.botones_nav = []
        for i, (p, texto) in enumerate(self.paginas_lista):
            self.pila.addWidget(p)
            b = QPushButton(f"{i + 1}  {texto}")
            b.setObjectName("Paso")
            b.setCheckable(True)
            b.setToolTip(f"{texto} (Ctrl+{i + 1})")
            grupo.addButton(b, i)
            ch.addWidget(b)
            self.botones_nav.append(b)
        ch.addStretch(1)
        grupo.idClicked.connect(self._elegir)
        capa.addWidget(cab)
        franja = QFrame()
        franja.setObjectName("Indicadores")
        fh = QHBoxLayout(franja)
        fh.setContentsMargins(12, 8, 12, 4)
        for i in range(4):
            k = _Kpi(acento=i == 0)
            self.kpis.append(k)
            fh.addWidget(k, 1)
        capa.addWidget(franja)
        capa.addWidget(self.pila, 1)
        self.setCentralWidget(central)
        self.statusBar().showMessage("F5 calcula · Ctrl+1 / Ctrl+2 cambian de escenario · Ctrl+O abre · Ctrl+S guarda · "
                                     "Ctrl+E exporta a Excel · Ctrl+P exporta a PDF")
        self._menu()
        for tecla, accion in (("F5", lambda: self.pagina_activa().calcular()), ("Ctrl+1", lambda: self._elegir(0)),
                              ("Ctrl+2", lambda: self._elegir(1))):
            QShortcut(QKeySequence(tecla), self, activated=accion)
        self._elegir(1 if tipo == "olla_distribuidor" else 0)
        self.setMinimumSize(1180, 680)
        self.resize(1440, 880)
        if not ruta_escenario or tipo != "horno_olla":
            QTimer.singleShot(1500, precalentar)

    def _elegir(self, i: int):
        self.pila.setCurrentIndex(i)
        for k, b in enumerate(self.botones_nav):
            b.setChecked(k == i)
        self._actualizar_indicadores()

    def _actual(self) -> int:
        return self.pila.currentIndex()

    def pagina_actual(self):
        return self.paginas_lista[self._actual()][0]

    def pagina_activa(self):
        """La página de cálculo visible (en el horno, la vista elegida)."""
        p = self.pagina_actual()
        return p.actual if isinstance(p, PaginaHornoOlla) else p

    def _actualizar_indicadores(self):
        if not self.kpis or not hasattr(self, "pila"):
            return
        filas, estado = indicadores_de(self.pagina_actual())
        for k, (rotulo, valor) in zip(self.kpis, filas):
            k.poner(rotulo, valor, estado)

    def _menu(self):
        from PySide6.QtGui import QAction, QKeySequence

        archivo = self.menuBar().addMenu("&Archivo")
        for texto, tecla, accion in (("Abrir escenario…", QKeySequence.StandardKey.Open, lambda: self.pagina_activa().abrir()),
                                     ("Guardar escenario…", QKeySequence.StandardKey.Save, lambda: self.pagina_activa().guardar()),
                                     ("Exportar a Excel…", "Ctrl+E", lambda: self.pagina_activa().exportar("xlsx")),
                                     ("Exportar a PDF…", "Ctrl+P", lambda: self.pagina_activa().exportar("pdf")),
                                     ("Exportar la serie (CSV)…", None, lambda: self.pagina_activa().exportar("csv"))):
            a = QAction(texto, self)
            if tecla is not None:
                a.setShortcut(QKeySequence(tecla))
            a.triggered.connect(accion)
            archivo.addAction(a)
        archivo.addSeparator()
        copiar = QAction("Copiar el resumen del resultado", self)
        copiar.setShortcut(QKeySequence("Ctrl+Shift+C"))
        copiar.triggered.connect(self.copiar_resumen)
        archivo.addAction(copiar)
        archivo.addSeparator()
        salir = QAction("Salir", self)
        salir.setShortcut(QKeySequence.StandardKey.Quit)
        salir.triggered.connect(self.close)
        archivo.addAction(salir)
        ayuda = self.menuBar().addMenu("A&yuda")
        acerca = QAction(f"Acerca de {NOMBRE_APP}", self)
        acerca.triggered.connect(lambda: QMessageBox.about(
            self, NOMBRE_APP, f"<b>{NOMBRE_APP} {VERSION_MODELO}</b><br>Tiempo de vaciado del horno (EAF) a la olla y de la olla al "
            f"distribuidor con las ecuaciones de flujo (balance de masa, Bernoulli y Torricelli).<br><br>{AVISO}"))
        ayuda.addAction(acerca)


    def resumen_texto(self) -> str:
        """El resultado de la página activa en texto (para pegarlo en un correo o un informe)."""
        p = self.pagina_activa()
        if p.resultado is None:
            return ""
        if isinstance(p, PaginaHorno):
            from .reporte import resumen

            return resumen(p.resultado)
        from .reporte_tiempo import texto

        return texto(p.escenario_corrido, p.resultado)

    def copiar_resumen(self):
        texto = self.resumen_texto()
        if texto:
            QApplication.clipboard().setText(f"{NOMBRE_APP} {VERSION_MODELO}. {AVISO}\n{texto}")
            self.statusBar().showMessage("Resumen copiado al portapapeles.", 4000)

    # -- tamaño, posición y escenario activo, recordados entre sesiones (sólo con ``main``) ------------------------------------
    def recordar(self, ajustes) -> None:
        ajustes.setValue("geometria", self.saveGeometry())
        ajustes.setValue("pagina", self._actual())

    def restaurar(self, ajustes) -> None:
        geometria = ajustes.value("geometria")
        if geometria is not None:
            self.restoreGeometry(geometria)
        try:
            self._elegir(int(ajustes.value("pagina", 0)))
        except (TypeError, ValueError):
            pass


_VENTANAS: list = []          # ventanas abiertas por ``main`` (para que no las recoja el recolector)


def preparar(qapp) -> str:
    """Aplica el diseño (paleta, letra y hoja de estilo) a la aplicación y devuelve la hoja para la ventana."""
    return tema_qt.aplicar(qapp)


def probar_ventana() -> int:
    """Abre la ventana, calcula, recorre las páginas y pestañas, exporta a una carpeta temporal y cierra. 0 si todo funcionó."""
    import tempfile
    import time

    try:
        qapp = aplicacion_qt()
        hoja = preparar(qapp)
        inicio = time.perf_counter()
        v = Ventana()
        v.setStyleSheet(hoja)
        v.show()
        qapp.processEvents()
        apertura = time.perf_counter() - inicio
        h = v.horno
        h.elegir(1)
        for i in range(h.detallado.pestanas.count()):
            h.detallado.pestanas.setCurrentIndex(i)
            qapp.processEvents()
        h.detallado.instante.setValue(600)
        h.elegir(0)
        for pagina in (h.directo, v.olla):
            for i in range(pagina.pestanas.count()):
                pagina.pestanas.setCurrentIndex(i)
                qapp.processEvents()
            pagina.instante.setValue(500)
            pagina.anadir_a_comparacion()
        v._elegir(1)
        qapp.processEvents()
        with tempfile.TemporaryDirectory() as carpeta:
            for ext in ("xlsx", "pdf", "csv"):
                h.detallado.exportar_en(Path(carpeta) / f"h3d.{ext}")
                h.directo.exportar_en(Path(carpeta) / f"h.{ext}")
                v.olla.exportar_en(Path(carpeta) / f"o.{ext}")
        tiempos = (h.directo.resultado.tiempo, h.detallado.resultado.tiempo, v.olla.resultado.tiempo)
        icono = v.icono_cargado
        v.close()
        qapp.processEvents()
    except Exception as error:  # noqa: BLE001
        print(f"  NO: la ventana falló: {type(error).__name__}: {error}")
        return 1
    if not icono:
        print("  NO: el icono de la ventana no se pudo cargar")
        return 1
    print(f"  ok  ventana abierta en {apertura:.1f} s, calculada (horno directo {tiempos[0]:.0f} s; horno con cavidad 3D "
          f"{tiempos[1]:.0f} s; olla {tiempos[2] / 60:.0f} min), exportada y cerrada")
    return 0


def main(ruta_escenario: str | None = None) -> int:
    from PySide6.QtCore import QSettings

    qapp = aplicacion_qt()
    hoja = preparar(qapp)
    try:
        v = Ventana(ruta_escenario)
    except ValueError as error:
        QMessageBox.warning(None, NOMBRE_APP, str(error))
        v = Ventana()
    ajustes = QSettings(NOMBRE_APP, NOMBRE_APP)
    v.restaurar(ajustes)
    if ruta_escenario:                      # un escenario abierto manda sobre la última página vista
        v._elegir(1 if v.olla.escenario_corrido and es_de_olla(ruta_escenario) else 0)
    v.setStyleSheet(hoja)
    v.show()
    _VENTANAS.append(v)
    qapp.aboutToQuit.connect(lambda: v.recordar(ajustes))
    return qapp.exec()


def es_de_olla(ruta) -> bool:
    from . import escenarios as es

    try:
        return es.abrir(ruta).get("tipo") == "olla_distribuidor"
    except (OSError, ValueError):
        return False
