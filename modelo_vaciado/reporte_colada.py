"""Salidas del vaciado en la colada continua: filas de resumen y de datos, Excel, PDF y CSV."""

from __future__ import annotations

import csv
import math
from pathlib import Path

import numpy as np

from . import VERSION_MODELO
from .colada_continua import CAMPOS, ResultadoColada, parametros_de_planta, resumen

AVISO = ("PRELIMINAR: la olla es la del plano (heredada del LWD); la válvula, el tundish y la máquina son supuestos o ejemplos, "
         "sin validar con datos de planta.")


def _s(x: float) -> str:
    return f"{x:.0f} s ({x / 60:.1f} min)" if math.isfinite(x) else "—"


def filas_de_resultado(r: ResultadoColada) -> list[tuple[str, str]]:
    s = resumen(r)
    c = r.config
    vm = s["velocidad_maxima"]
    filas = [("Duración de la secuencia", _s(s["tiempo_total_s"])),
             ("Acero colado", f"{s['acero_colado_t']:.0f} t"),
             ("Demanda de la máquina", f"{s['demanda_t_min']:.2f} t/min ({c.moldes.velocidad:g} m/min)"),
             ("Colado de una olla en régimen", _s(s["colado_por_olla_regimen_s"])),
             ("Vaciado de una olla con la válvula abierta", _s(s["vaciado_libre_olla_s"]))]
    for o in r.ollas:
        filas.append((f"Olla {o.numero}: colado", f"{_s(o.duracion)}, f_A media {o.fraccion_media:.2f}"))
    m = s["margen_en_cambio"]
    filas += [("Tundish sin olla, del nivel de operación al mínimo", f"{_s(m['tiempo_s'])} para {m['cambio_s']:.0f} s de cambio"),
              ("Nivel mínimo del tundish en los cambios", ", ".join(f"{h:.0f}" for h in s["nivel_minimo_en_cambio_mm"]) + " mm"
               if s["nivel_minimo_en_cambio_mm"] else "—"),
              ("Velocidad máxima por la válvula de la olla (al final)", f"{vm['por_la_olla']:.2f} m/min"),
              ("Velocidad máxima por las buzas", f"{vm['por_las_buzas']:.2f} m/min")]
    return filas


TEXTOS_ESTADO = {"heredado_sin_verificar": "heredado del LWD, sin verificar", "tomado_del_sgw": "tomado del SGW (otra olla)",
                 "supuesto": "supuesto", "ejemplo": "ejemplo", "dato del usuario": "dato del usuario"}


def texto_estado(estado: str) -> str:
    return TEXTOS_ESTADO.get(estado, estado.replace("_", " "))


def filas_de_datos(planta: str, cambios: dict) -> list[tuple[str, str, str]]:
    base = parametros_de_planta(planta)
    filas = []
    for clave, etiqueta, unidad, _ in CAMPOS:
        valor, estado = base[clave]
        if clave in cambios and float(cambios[clave]) != valor:
            valor, estado = float(cambios[clave]), "dato del usuario"
        filas.append((etiqueta + (f", {unidad}" if unidad else ""), f"{valor:g}", texto_estado(estado)))
    return filas


def escribir_csv(r: ResultadoColada, ruta: Path) -> None:
    ab = r.abertura
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([f"# {AVISO} Modelo {VERSION_MODELO}. {r.nombre}"])
        w.writerow(["tiempo_s", "acero_en_la_olla_t", "acero_en_el_tundish_t", "nivel_del_tundish_mm", "caudal_de_la_olla_t_s",
                    "caudal_a_los_moldes_t_s", "abertura_de_la_valvula_pct", "velocidad_de_colada_m_min"])
        for i in range(len(r.t)):
            w.writerow([f"{r.t[i]:.1f}", f"{r.masa_olla[i]:.2f}", f"{r.masa_tundish[i]:.2f}", f"{r.nivel_tundish[i]:.1f}",
                        f"{r.caudal_olla[i]:.4f}", f"{r.caudal_molde[i]:.4f}", "" if np.isnan(ab[i]) else f"{ab[i]:.1f}",
                        f"{r.velocidad[i]:.3f}"])


def escribir_excel(e: dict, r: ResultadoColada, ruta: Path) -> None:
    from openpyxl import Workbook
    from openpyxl.chart import LineChart, Reference
    from openpyxl.styles import Font

    libro = Workbook()
    h = libro.active
    h.title = "Resumen"
    h.append([r.nombre or "Secuencia de colada continua"])
    h.append([f"{AVISO} Modelo {VERSION_MODELO}."])
    h.append([])
    for fila in filas_de_resultado(r):
        h.append(list(fila))
    h.append([])
    h.append(["Avisos"])
    for t, texto in r.eventos or [(None, "Ninguno")]:
        h.append(["" if t is None else f"{t:.0f} s", texto])
    h.column_dimensions["A"].width, h.column_dimensions["B"].width = 52, 60
    h["A1"].font = Font(bold=True, size=13)
    d = libro.create_sheet("Datos")
    d.append(["Dato", "Valor", "Estado"])
    for fila in filas_de_datos(e["planta"], e.get("cambios", {})):
        d.append(list(fila))
    for col, ancho in zip("ABC", (58, 14, 28)):
        d.column_dimensions[col].width = ancho
    o = libro.create_sheet("Ollas")
    o.append(["Olla", "Apertura, s", "Cierre, s", "Colado, s", "Acero colado, t", "f_A media", "Nivel mínimo del tundish en el cambio siguiente, mm"])
    for x in r.ollas:
        o.append([x.numero, round(x.apertura, 1), round(x.cierre, 1), round(x.duracion, 1), round(x.colado, 2),
                  None if math.isnan(x.fraccion_media) else round(x.fraccion_media, 3),
                  None if math.isnan(x.nivel_minimo_en_cambio) else round(x.nivel_minimo_en_cambio, 0)])
    s = libro.create_sheet("Serie")
    s.append(["tiempo, s", "acero en la olla, t", "nivel del tundish, mm", "abertura de la válvula, %", "velocidad de colada, m/min"])
    ab = r.abertura
    for i in range(0, len(r.t), 2):
        s.append([round(float(r.t[i]), 1), round(float(r.masa_olla[i]), 2), round(float(r.nivel_tundish[i]), 1),
                  None if np.isnan(ab[i]) else round(float(ab[i]), 1), round(float(r.velocidad[i]), 3)])
    n = s.max_row
    for k, col in enumerate((2, 3, 4, 5)):
        g = LineChart()
        g.title, g.height, g.width = s.cell(1, col).value, 7.5, 15
        g.add_data(Reference(s, min_col=col, min_row=1, max_row=n), titles_from_data=True)
        g.set_categories(Reference(s, min_col=1, min_row=2, max_row=n))
        g.x_axis.title, g.legend = "tiempo, s", None
        g.x_axis.tickLblSkip = max(1, n // 10)
        s.add_chart(g, f"{'G' if k % 2 == 0 else 'Q'}{2 + 16 * (k // 2)}")
    for hoja in (d, o, s):
        for celda in hoja[1]:
            celda.font = Font(bold=True)
    libro.save(ruta)


def figura_secuencia(r: ResultadoColada, fig) -> None:
    """Las cuatro series de la secuencia en una figura de matplotlib con 4 ejes (2 × 2)."""
    c = r.config
    ejes = fig.axes
    ejes[0].plot(r.t / 60, r.masa_olla, lw=1.6, color="#25272A")
    ejes[0].set_ylabel("acero en la olla, t")
    ejes[1].plot(r.t / 60, r.nivel_tundish, lw=1.6, color="#25272A")
    for valor, texto, color in ((c.tundish.nivel_operacion, "operación", "#3F6A24"), (c.tundish.nivel_minimo, "mínimo", "#A93526"),
                                (c.tundish.nivel_maximo, "máximo", "#8A5D00")):
        ejes[1].axhline(valor, color=color, lw=0.9, ls="--")
        ejes[1].annotate(texto, (0, valor), xytext=(3, 2), textcoords="offset points", fontsize=7, color=color)
    ejes[1].set_ylabel("nivel del tundish, mm")
    ejes[2].plot(r.t / 60, r.abertura, lw=1.4, color="#25272A")
    ejes[2].set_ylabel("abertura de la válvula de la olla, %")
    ejes[2].set_ylim(0, 105)
    ejes[3].plot(r.t / 60, r.caudal_olla * 60, lw=1.2, color="#1F55D0", label="olla → tundish")
    ejes[3].plot(r.t / 60, r.caudal_molde * 60, lw=1.6, color="#C8601A", label="tundish → moldes")
    ejes[3].set_ylabel("caudal, t/min")
    ejes[3].legend(fontsize=7.5, loc="upper right")
    for ax in ejes:
        ax.set_ylim(bottom=0)
        for o in r.ollas:
            ax.axvspan(o.cierre / 60, (o.cierre + (c.cambio if o.numero < len(r.ollas) else 0)) / 60, color="#9A8F78", alpha=0.18, lw=0)
    for ax in ejes[2:]:
        ax.set_xlabel("tiempo, min")


def escribir_pdf(e: dict, r: ResultadoColada, ruta: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    with PdfPages(ruta) as pdf:
        fig = plt.figure(figsize=(8.27, 11.69))
        fig.text(0.08, 0.95, "Vaciado en la colada continua", fontsize=17, weight="bold")
        fig.text(0.08, 0.925, r.nombre or "Secuencia", fontsize=11)
        fig.text(0.08, 0.895, AVISO, fontsize=7.5, color="#8A5D00", wrap=True)
        y = 0.85
        fig.text(0.08, y, "Resultado", fontsize=12, weight="bold")
        for a, b in filas_de_resultado(r):
            y -= 0.017
            fig.text(0.08, y, a, fontsize=8.5)
            fig.text(0.56, y, b, fontsize=8.5)
        y -= 0.03
        fig.text(0.08, y, "Datos del cálculo", fontsize=12, weight="bold")
        for a, b, est in filas_de_datos(e["planta"], e.get("cambios", {})):
            y -= 0.0155
            fig.text(0.08, y, a, fontsize=7.5)
            fig.text(0.68, y, b, fontsize=7.5)
            fig.text(0.78, y, est, fontsize=6.5, color="#5F6164")
        y -= 0.03
        fig.text(0.08, y, "Avisos", fontsize=12, weight="bold")
        for t, texto in r.eventos or [(None, "Ninguno.")]:
            y -= 0.017
            fig.text(0.08, y, (f"A los {t:.0f} s: " if t is not None else "") + texto, fontsize=7.5)
        pdf.savefig(fig)
        plt.close(fig)
        fig, _ = plt.subplots(2, 2, figsize=(11.69, 8.27), sharex=True)
        figura_secuencia(r, fig)
        fig.suptitle(r.nombre or "Secuencia", fontsize=11)
        fig.tight_layout(rect=(0.02, 0.02, 0.98, 0.96))
        pdf.savefig(fig)
        plt.close(fig)
