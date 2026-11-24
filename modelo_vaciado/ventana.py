"""La ventana de la aplicación de vaciado por la piquera (PySide6). El cálculo vive en ``simulacion`` y ``escenario``, sin Qt.

Izquierda: el escenario (planta, cargas, desgaste, piquera, hidráulica, basculado). Centro: pestañas «Colada» (las cuatro series
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
from .ventana_formulario import formulario
from .rutas import raiz
from . import FORMATO_ESCENARIO, VERSION_MODELO
from .datos import cargar, plantas_con_datos
from .escenario import abrir, correr, planta_de
from .reporte import AVISO, escribir_csv, escribir_excel, escribir_pdf, filas_de_resultado

NOMBRE_APP = "Vaciado-EAF"      # provisional (decisión W de docs/pendientes.md)
RAIZ = raiz()
RECURSOS = RAIZ / "modelo_vaciado" / "interfaz" / "recursos"
P = tema.PALETA
COLORES = [P["TINTA"], "#1F55D0", "#C8601A", P["CORRECTO"], "#7A3AA8", P["AVISO"], P["ALARMA"]]


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

        self.boton_calcular = boton("Calcular", self.calcular, "primario")
        col.addWidget(self.boton_calcular)
        col.addStretch(1)
        barra = QScrollArea()
        barra.setWidget(panel)
        barra.setWidgetResizable(True)
        barra.setFixedWidth(440)
        barra.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        fila.addWidget(barra)

        # centro: pestañas
        self.pestanas = QTabWidget()
        self.lienzo_colada = Lienzo(2, 2)
        self.pestanas.addTab(self.lienzo_colada, "Colada")
        corte = QWidget()
        cv = QVBoxLayout(corte)
        self.lienzo_corte = Lienzo()
        self.instante = QSlider(Qt.Orientation.Horizontal)
        self.instante.setRange(0, 1000)
        self.instante.valueChanged.connect(self._dibujar_corte)
        self.rotulo_instante = QLabel()
        cv.addWidget(self.lienzo_corte, 1)
        cv.addWidget(self.rotulo_instante)
        cv.addWidget(self.instante)
        self.pestanas.addTab(corte, "Corte")
        self.lienzo_limites = Lienzo()
        self.pestanas.addTab(self.lienzo_limites, "Límites")
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
        kv.addWidget(self.lienzo_comparar, 1)
        self.pestanas.addTab(comparar, "Comparar")
        self.pestanas.addTab(self._armar_mapas(), "Mapas")
        fila.addWidget(self.pestanas, 1)

        # derecha: resultado
        der = QWidget()
        dv = QVBoxLayout(der)
        self.titular = QLabel("—")
        self.titular.setStyleSheet(f"font-size: 30px; font-weight: 600; color: {P['TEXTO']};")
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
        dv.addWidget(QLabel("Tiempo de vaciado"))
        dv.addWidget(self.titular)
        dv.addWidget(self.subtitular)
        dv.addWidget(self.tabla)
        dv.addWidget(self.avisos)
        dv.addStretch(1)
        for texto, accion in (("Abrir escenario…", self.abrir), ("Guardar escenario…", self.guardar),
                              ("Exportar a Excel…", lambda: self.exportar("xlsx")), ("Exportar a PDF…", lambda: self.exportar("pdf")),
                              ("Exportar la serie (CSV)…", lambda: self.exportar("csv"))):
            dv.addWidget(boton(texto, accion))
        dv.addWidget(pie)
        der.setFixedWidth(300)
        fila.addWidget(der)

        self.planta.currentIndexChanged.connect(self._valores_de_la_planta)
        for w in (self.modo, self.tipo):
            w.currentIndexChanged.connect(self._habilitar)
        self.instantaneo.toggled.connect(self._habilitar)
        self._habilitar()

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
        fila.addWidget(boton("Calcular los mapas", self.calcular_mapas, "primario"))
        fila.addStretch(1)
        v.addLayout(fila)
        nota = QLabel("El crecimiento del canal por colada no tiene dato de planta: el valor es un supuesto para ver la tendencia.")
        nota.setStyleSheet(f"color: {P['AVISO']}; font-size: 11px;")
        v.addWidget(nota)
        self.lienzo_mapas = Lienzo(1, 2)
        v.addWidget(self.lienzo_mapas, 1)
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
            return False
        self.resultado, self.escenario_corrido = r, e
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
        return True

    def _dibujar_series(self, lienzo: Lienzo, lista):
        with matplotlib.rc_context(tema.estilo_matplotlib()):
            lienzo.limpiar()
            paneles = (("masa", "acero en el horno, t"), ("angulo", "ángulo de basculado, grados"),
                       ("altura", "acero sobre la boca, mm"), ("caudal", "caudal, t/s"))
            for ax, (campo, rotulo) in zip(lienzo.ejes, paneles):
                for i, (nombre, r) in enumerate(lista):
                    ax.plot(r.t, getattr(r, campo), color=COLORES[i % len(COLORES)], lw=1.8, label=f"{nombre} ({r.tiempo:.0f} s)")
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
                ax.set_xlabel("tiempo, s")
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
        ruta, _ = QFileDialog.getOpenFileName(self, "Abrir escenario de vaciado", str(RAIZ / "ejemplos" / "vaciado"), "Escenario (*.json)")
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


class Ventana(QMainWindow):
    """La aplicación: una página por etapa del vaciado."""

    def __init__(self, ruta_escenario: Path | str | None = None):
        super().__init__()
        self.setWindowTitle(f"{NOMBRE_APP} {VERSION_MODELO} — tiempos de vaciado del horno, la olla y el tundish")
        icono = QIcon(str(RECURSOS / "icono.png"))
        self.icono_cargado = not icono.isNull()
        self.setWindowIcon(icono)
        from .ventana_colada import PaginaColada

        es_colada = False
        if ruta_escenario:
            try:
                es_colada = json.loads(Path(ruta_escenario).read_text(encoding="utf-8")).get("formato") == "lwd_eaf.vaciado.colada/1"
            except (OSError, ValueError):
                es_colada = False
        self.paginas = QTabWidget()
        self.horno = PaginaHorno(None if es_colada else ruta_escenario)
        self.colada = PaginaColada(Lienzo, ruta_escenario if es_colada else None)
        self.paginas.addTab(self.horno, "Horno (EAF) → olla")
        self.paginas.addTab(self.colada, "Olla → tundish → moldes")
        if es_colada:
            self.paginas.setCurrentIndex(1)
        self.setCentralWidget(self.paginas)
        self.resize(1440, 860)


def probar_ventana() -> int:
    """Abre la ventana, calcula, recorre las pestañas, exporta a una carpeta temporal y cierra. 0 si todo funcionó."""
    import tempfile

    try:
        qapp = aplicacion_qt()
        hoja = tema_qt.aplicar(qapp)
        v = Ventana()
        v.setStyleSheet(hoja)
        v.show()
        qapp.processEvents()
        for i in range(v.horno.pestanas.count()):
            v.horno.pestanas.setCurrentIndex(i)
            qapp.processEvents()
        h = v.horno
        h.instante.setValue(600)
        h.anadir_a_comparacion()
        v.paginas.setCurrentIndex(1)
        for i in range(v.colada.pestanas.count()):
            v.colada.pestanas.setCurrentIndex(i)
            qapp.processEvents()
        with tempfile.TemporaryDirectory() as carpeta:
            for ext in ("xlsx", "pdf", "csv"):
                h.exportar_en(Path(carpeta) / f"p.{ext}")
                v.colada.exportar_en(Path(carpeta) / f"c.{ext}")
        tiempo, icono = h.resultado.tiempo, v.icono_cargado
        olla = v.colada.resultado.ollas[-1].duracion
        v.close()
        qapp.processEvents()
    except Exception as error:  # noqa: BLE001
        print(f"  NO: la ventana falló: {type(error).__name__}: {error}")
        return 1
    if not icono:
        print("  NO: el icono de la ventana no se pudo cargar")
        return 1
    print(f"  ok  ventana abierta, calculada (horno {tiempo:.0f} s; olla {olla / 60:.0f} min), exportada y cerrada")
    return 0


def main(ruta_escenario: str | None = None) -> int:
    qapp = aplicacion_qt()
    hoja = tema_qt.aplicar(qapp)
    v = Ventana(ruta_escenario)
    v.setStyleSheet(hoja)
    v.show()
    return qapp.exec()
