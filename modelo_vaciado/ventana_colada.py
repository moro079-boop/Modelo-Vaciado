"""Página «Colada continua» de Vaciado-EAF: la olla en la máquina, el tundish y los moldes (PySide6)."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QDoubleSpinBox, QFileDialog, QHBoxLayout, QLabel,
                               QLineEdit, QMessageBox, QScrollArea, QTabWidget, QVBoxLayout, QWidget)

from .interfaz import tema
from .interfaz.widgets import EtiquetaEstado, Selector, boton
from .ventana_formulario import formulario
from . import colada_continua as cc
from .reporte_colada import AVISO, escribir_csv, escribir_excel, escribir_pdf, figura_secuencia, filas_de_resultado, texto_estado

P = tema.PALETA
# el estado del dato en este proyecto → el papel visual de los estados de LWD-EAF (marca y color)
ROL_ESTADO = {"ejemplo": "supuesto", "tomado_del_sgw": "heredado_sin_verificar", "dato del usuario": "dato_del_usuario"}
GRUPOS = (
    ("Secuencia", ("acero_por_olla_t", "ollas", "cambio_de_olla_s")),
    ("Olla y válvula deslizante", ("olla_pared_gastada_mm", "olla_piso_gastado_mm", "valvula_diametro_mm", "valvula_cd",
                                   "valvula_carrera_mm", "caida_bajo_el_piso_mm", "acero_remanente_t")),
    ("Tundish", ("tundish_largo_mm", "tundish_ancho_mm", "tundish_talud_grados", "nivel_operacion_mm", "nivel_minimo_mm",
                 "nivel_maximo_mm", "nivel_inicial_mm", "altura_salida_tubo_mm", "constante_de_control_s")),
    ("Moldes", ("lineas", "ancho_mm", "espesor_mm", "velocidad_m_min", "densidad_solido", "buza_diametro_mm", "buza_cd",
                "buza_largo_mm", "buza_inmersion_mm")),
)
DECIMALES = {"valvula_cd": 3, "buza_cd": 3, "velocidad_m_min": 2, "densidad_solido": 2, "tundish_talud_grados": 1}
ENTEROS = {"ollas", "lineas"}


class PaginaColada(QWidget):
    def __init__(self, lienzo_factory, ruta_escenario: Path | str | None = None):
        super().__init__()
        self._lienzo = lienzo_factory
        self.resultado = None
        self.escenario_corrido = None
        self.campos: dict[str, QDoubleSpinBox] = {}
        self.estados: dict[str, QLabel] = {}
        self._base: dict = {}
        self._armar()
        if ruta_escenario:
            self.poner_escenario(cc.abrir(ruta_escenario))
        else:
            self._valores_de_la_planta()
        self.calcular()

    def _armar(self):
        fila = QHBoxLayout(self)
        panel = QWidget()
        col = QVBoxLayout(panel)
        col.setContentsMargins(8, 8, 22, 8)
        self.nombre = QLineEdit("Secuencia de colada")
        self.planta = Selector()
        self.planta.addItems(cc.plantas_con_datos())
        f = formulario(col, "Escenario")
        f.addRow("Nombre", self.nombre)
        f.addRow("Planta", self.planta)
        for titulo, claves in GRUPOS:
            f = formulario(col, titulo)
            for k in claves:
                etiqueta, unidad = cc.ETIQUETAS[k]
                s = QDoubleSpinBox()
                s.setRange(0, 100000)
                s.setDecimals(0 if k in ENTEROS else DECIMALES.get(k, 1))
                s.setSingleStep(1 if k in ENTEROS else (0.05 if DECIMALES.get(k, 1) >= 2 else 10))
                s.setSuffix(f" {unidad}" if unidad else "")
                s.setKeyboardTracking(False)
                s.setAlignment(Qt.AlignmentFlag.AlignRight)
                estado = EtiquetaEstado("supuesto")
                caja = QWidget()
                cv = QVBoxLayout(caja)
                cv.setContentsMargins(0, 0, 0, 0)
                cv.setSpacing(0)
                cv.addWidget(s)
                cv.addWidget(estado)
                lab = QLabel(etiqueta)
                lab.setWordWrap(True)
                f.addRow(lab, caja)
                self.campos[k], self.estados[k] = s, estado
                s.valueChanged.connect(lambda _v, k=k: self._marcar(k))
        col.addWidget(boton("Calcular", self.calcular, "primario"))
        col.addStretch(1)
        barra = QScrollArea()
        barra.setWidget(panel)
        barra.setWidgetResizable(True)
        barra.setFixedWidth(470)
        barra.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        fila.addWidget(barra)

        self.pestanas = QTabWidget()
        self.lienzo_secuencia = self._lienzo(2, 2)
        self.pestanas.addTab(self.lienzo_secuencia, "Secuencia")
        self.lienzo_olla = self._lienzo(1, 2)
        self.pestanas.addTab(self.lienzo_olla, "Olla")
        self.lienzo_tundish = self._lienzo(1, 2)
        self.pestanas.addTab(self.lienzo_tundish, "Tundish y moldes")
        fila.addWidget(self.pestanas, 1)

        der = QWidget()
        dv = QVBoxLayout(der)
        self.titular = QLabel("—")
        self.titular.setStyleSheet(f"font-size: 28px; font-weight: 600; color: {P['TEXTO']};")
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
        dv.addWidget(QLabel("Colado de una olla"))
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
        der.setFixedWidth(320)
        fila.addWidget(der)
        self.planta.currentIndexChanged.connect(self._valores_de_la_planta)

    # -- datos ↔ controles ---------------------------------------------------------------------------------------------------
    def _valores_de_la_planta(self):
        self._base = cc.parametros_de_planta(self.planta.currentText())
        for k, (valor, _) in self._base.items():
            self.campos[k].blockSignals(True)
            self.campos[k].setValue(valor)
            self.campos[k].blockSignals(False)
            self._marcar(k)

    def _marcar(self, k: str):
        valor, estado = self._base.get(k, (None, ""))
        actual = self.campos[k].value()
        if valor is not None and abs(actual - valor) > 1e-9:
            self.estados[k].poner("modificado", "dato del usuario")
        else:
            self.estados[k].poner(ROL_ESTADO.get(estado, estado), texto_estado(estado))

    def escenario(self) -> dict:
        cambios = {k: s.value() for k, s in self.campos.items() if abs(s.value() - self._base[k][0]) > 1e-9}
        return {"formato": cc.FORMATO_ESCENARIO, "nombre": self.nombre.text().strip() or "Secuencia", "planta": self.planta.currentText(),
                "cambios": cambios}

    def poner_escenario(self, e: dict):
        self.nombre.setText(e.get("nombre", "Secuencia"))
        self.planta.setCurrentText(e["planta"])
        self._valores_de_la_planta()
        for k, v in e.get("cambios", {}).items():
            if k in self.campos:
                self.campos[k].setValue(float(v))

    # -- cálculo y dibujo ---------------------------------------------------------------------------------------------------
    def calcular(self) -> bool:
        try:
            e = self.escenario()
            c = cc.configurar(e["planta"], e["cambios"])
            if c.acero_por_olla <= c.remanente:
                raise ValueError("El acero por olla debe ser mayor que el remanente.")
            if not c.tundish.nivel_minimo < c.tundish.nivel_operacion <= c.tundish.nivel_maximo:
                raise ValueError("Los niveles del tundish deben cumplir mínimo < operación ≤ máximo.")
            if c.acero_por_olla > c.olla.capacidad:
                raise ValueError(f"La olla no admite {c.acero_por_olla:g} t: su capacidad hasta el tope es {c.olla.capacidad:.0f} t.")
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                r = cc.simular_secuencia(c, nombre=e["nombre"])
            finally:
                QApplication.restoreOverrideCursor()
        except Exception as error:  # noqa: BLE001
            self.titular.setText("—")
            self.subtitular.setText("")
            self.tabla.setText("")
            self.avisos.setText(f"<span style='color:{P['ALARMA']}'><b>No se pudo calcular.</b> {error}</span>")
            return False
        self.resultado, self.escenario_corrido = r, e
        s = cc.resumen(r)
        dur = [o.duracion for o in r.ollas[1:]] or [r.ollas[0].duracion]
        self.titular.setText(f"{np.mean(dur) / 60:.0f} min")
        self.subtitular.setText(f"{len(r.ollas)} ollas en {r.tiempo / 3600:.2f} h · {s['demanda_t_min']:.2f} t/min · "
                                f"con la válvula abierta, una olla se vaciaría en {s['vaciado_libre_olla_s'] / 60:.0f} min")
        self.tabla.setText("<table cellspacing='3'>" + "".join(
            f"<tr><td style='color:{P['TEXTO_2']}'>{a}</td><td align='right'><b>{b}</b></td></tr>"
            for a, b in filas_de_resultado(r) if not a.startswith("Olla ")) + "</table>")
        if r.eventos:
            self.avisos.setText("".join(f"<p style='color:{P['ALARMA']}'><b>Aviso a los {t / 60:.0f} min.</b> {x}</p>" for t, x in r.eventos))
        else:
            self.avisos.setText(f"<span style='color:{P['CORRECTO']}'><b>Sin avisos.</b> La olla sigue la demanda y el tundish "
                                "se mantiene entre sus niveles.</span>")
        self._dibujar()
        return True

    def _dibujar(self):
        r, c = self.resultado, self.resultado.config
        with matplotlib.rc_context(tema.estilo_matplotlib()):
            self.lienzo_secuencia.limpiar()
            figura_secuencia(r, self.lienzo_secuencia.figura)
            # olla: perfil y vaciado libre contra controlado
            self.lienzo_olla.limpiar()
            ax = self.lienzo_olla.ejes[0]
            g = c.olla.geometria
            z = np.linspace(0, g.altura, 400)
            rc = g.radio_cara_caliente(z, c.parametros["olla_pared_gastada_mm"])
            ax.plot(rc, z, color=P["CORAZA"], lw=1.8)
            ax.plot(-rc, z, color=P["CORAZA"], lw=1.8)
            ax.plot([-rc[0], rc[0]], [c.olla.z_piso] * 2, color=P["CORAZA"], lw=1.8)
            zl = c.olla.cota(c.acero_por_olla)
            dentro = z <= zl
            ax.fill_betweenx(z[dentro & (z >= c.olla.z_piso)], -rc[dentro & (z >= c.olla.z_piso)], rc[dentro & (z >= c.olla.z_piso)],
                             color=P["ACERO_LIQUIDO"])
            ax.plot([0, 0], [c.olla.z_piso, c.olla.z_piso - c.caida], color=P["TEXTO_3"], lw=3)
            ax.annotate(f"{c.acero_por_olla:g} t: {zl - c.olla.z_piso:.0f} mm de acero", (0, zl), xytext=(0, 6),
                        textcoords="offset points", ha="center", fontsize=8)
            ax.set_aspect("equal")
            ax.set_title("Olla (cara caliente)", loc="left")
            ax.set_xlabel("mm")
            ax.set_ylabel("altura sobre la base de la coraza, mm")
            ax = self.lienzo_olla.ejes[1]
            tl, ml = cc.vaciado_libre_olla(c)
            ax.plot(tl / 60, ml, color=P["ALARMA"], lw=1.6, label=f"válvula abierta: {tl[-1] / 60:.0f} min")
            o = r.ollas[-1]
            en = (r.t > o.apertura) & (r.t <= o.cierre + 1) & (r.masa_olla > 0)
            ax.plot((r.t[en] - o.apertura) / 60, r.masa_olla[en], color=P["TINTA"], lw=1.8,
                    label=f"con el control del tundish: {o.duracion / 60:.0f} min")
            ax.set_xlabel("tiempo desde la apertura, min")
            ax.set_ylabel("acero en la olla, t")
            ax.set_ylim(bottom=0)
            ax.legend(loc="upper right")
            ax.set_title("Vaciado de una olla", loc="left")
            # tundish: volumen-nivel y capacidad de las buzas
            self.lienzo_tundish.limpiar()
            ax = self.lienzo_tundish.ejes[0]
            h = np.linspace(0, c.tundish.nivel_maximo * 1.1, 200)
            ax.plot([c.tundish.masa(x) for x in h], h, color=P["TINTA"], lw=1.8)
            for valor, texto, color in ((c.tundish.nivel_operacion, "operación", P["CORRECTO"]), (c.tundish.nivel_minimo, "mínimo", P["ALARMA"]),
                                        (c.tundish.nivel_maximo, "máximo", P["AVISO"])):
                ax.axhline(valor, color=color, lw=0.9, ls="--")
                ax.annotate(f"{texto}: {c.tundish.masa(valor):.1f} t", (0, valor), xytext=(3, 2), textcoords="offset points",
                            fontsize=7.5, color=color)
            ax.set_xlabel("acero en el tundish, t")
            ax.set_ylabel("nivel, mm")
            ax.set_title("Tundish: masa contra nivel", loc="left")
            ax = self.lienzo_tundish.ejes[1]
            ax.plot(h, [c.moldes.velocidad_maxima(x, c.densidad) for x in h], color=P["TINTA"], lw=1.8, label="máxima por las buzas")
            ax.axhline(c.moldes.velocidad, color=P["ACERO_TEXTO"], lw=1.2, ls="--", label=f"de colada: {c.moldes.velocidad:g} m/min")
            vo = [cc.caudal_olla_abierta(c, m, c.tundish.nivel_operacion) / c.moldes.demanda(1.0)
                  for m in np.linspace(c.remanente, c.acero_por_olla, 5)]
            ax.axhspan(min(vo), max(vo), color=P["ALARMA"], alpha=0.12, label="máxima por la válvula de la olla (llena → remanente)")
            ax.set_xlabel("nivel del tundish, mm")
            ax.set_ylabel("velocidad de colada, m/min")
            ax.set_ylim(bottom=0)
            ax.legend(loc="lower right", fontsize=7.5)
            ax.set_title("Velocidad máxima de colada", loc="left")
        for lz in (self.lienzo_secuencia, self.lienzo_olla, self.lienzo_tundish):
            lz.draw_idle()

    # -- archivos -----------------------------------------------------------------------------------------------------------
    def abrir(self):
        ruta, _ = QFileDialog.getOpenFileName(self, "Abrir escenario de colada continua", "", "Escenario (*.json)")
        if ruta:
            self.abrir_ruta(ruta)

    def abrir_ruta(self, ruta) -> bool:
        try:
            self.poner_escenario(cc.abrir(ruta))
        except Exception as error:  # noqa: BLE001
            QMessageBox.warning(self, "Vaciado-EAF", f"No se pudo abrir el escenario.\n{error}")
            return False
        return self.calcular()

    def guardar(self):
        ruta, _ = QFileDialog.getSaveFileName(self, "Guardar escenario de colada continua", "colada.json", "Escenario (*.json)")
        if ruta:
            self.guardar_en(ruta)

    def guardar_en(self, ruta):
        Path(ruta).write_text(json.dumps(self.escenario(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    def exportar(self, tipo: str):
        if self.resultado is None:
            return
        filtro = {"xlsx": "Excel (*.xlsx)", "pdf": "PDF (*.pdf)", "csv": "CSV (*.csv)"}[tipo]
        ruta, _ = QFileDialog.getSaveFileName(self, "Exportar", f"colada.{tipo}", filtro)
        if ruta:
            try:
                self.exportar_en(ruta)
            except Exception as error:  # noqa: BLE001
                QMessageBox.warning(self, "Vaciado-EAF", f"No se pudo escribir el archivo.\n{error}")

    def exportar_en(self, ruta):
        ruta = Path(ruta)
        if ruta.suffix.lower() == ".xlsx":
            escribir_excel(self.escenario_corrido, self.resultado, ruta)
        elif ruta.suffix.lower() == ".pdf":
            escribir_pdf(self.escenario_corrido, self.resultado, ruta)
        else:
            escribir_csv(self.resultado, ruta)


__all__ = ["PaginaColada"]
