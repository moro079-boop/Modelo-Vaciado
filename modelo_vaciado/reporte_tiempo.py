"""Reportes del cálculo directo (los dos escenarios con datos del usuario): texto, CSV, Excel con gráficas nativas y PDF."""

from __future__ import annotations

import csv
import math
from pathlib import Path

from . import VERSION_MODELO
from .escenarios import ESTADOS, TIPOS, completar, resumen
from .flujo import ResultadoVaciado

AVISO = "PRELIMINAR: sin validar con tiempos de vaciado medidos en planta."
FORMAS = {"prismatica": "prismática (área constante)", "troncoconica": "troncocónica"}
DESTINOS = {"libre": "chorro libre", "nivel_constante": "distribuidor a nivel constante", "llenado": "distribuidor que se llena"}


def _estado(e: dict, clave: str, valor_por_omision=None, valor=None) -> str:
    """Estado del dato: el de ``ESTADOS`` si el valor es el de omisión; «dato del usuario» si se cambió."""
    if valor is not None and valor_por_omision is not None and abs(float(valor) - float(valor_por_omision)) > 1e-9:
        return "dato del usuario"
    estado = ESTADOS.get(e["tipo"], {}).get(clave)
    return "dato del usuario" if estado is None else estado[0].replace("_", " ")


def filas_de_datos(e: dict) -> list[tuple[str, str, str]]:
    """(dato, valor, estado) de lo que entró al cálculo."""
    from .escenarios import nuevo

    e = completar(e)
    base = nuevo(e["tipo"])
    r, p, h = e["recipiente"], e["paso"], e["hidraulica"]
    br, bh = base["recipiente"], base["hidraulica"]
    filas = [("Escenario", TIPOS[e["tipo"]], ""),
             ("Acero al inicio, t", f"{e['acero_inicial_t']:g}", _estado(e, "acero_inicial_t", base["acero_inicial_t"], e["acero_inicial_t"])),
             ("Acero al final, t", f"{e['acero_final_t']:g}", _estado(e, "acero_final_t", base["acero_final_t"], e["acero_final_t"]))]
    if r.get("geometria") == "olla_de_planta":
        filas += [("Recipiente", f"olla de la planta «{r['planta']}» (regla del LWD)", _estado(e, "planta")),
                  ("Desgaste de pared / piso, mm", f"{r.get('pared_gastada_mm', 0):g} / {r.get('piso_gastado_mm', 0):g}", "dato del usuario")]
    else:
        filas += [("Recipiente", f"definido por el usuario, {FORMAS.get(r.get('forma'), r.get('forma'))}", "dato del usuario"),
                  ("Altura metalostática inicial sobre el orificio, mm", f"{r['altura_metalostatica_mm']:g}",
                   _estado(e, "altura_metalostatica_mm", br.get("altura_metalostatica_mm"), r["altura_metalostatica_mm"])),
                  ("Talón bajo el orificio, t", f"{r.get('talon_t', 0):g}", _estado(e, "talon_t", br.get("talon_t"), r.get("talon_t", 0)))]
        if r.get("forma") == "troncoconica":
            filas.append(("Relación de diámetros fondo / superficie", f"{r.get('relacion_diametros', 1):g}", "dato del usuario"))
        filas.append(("Densidad del acero líquido, t/m³", f"{e.get('densidad', 7.0):g}", _estado(e, "densidad", base.get("densidad"), e.get("densidad"))))
    if p.get("area_cm2") or p.get("area_mm2"):
        area = p.get("area_cm2") or p["area_mm2"] / 100.0
        filas.append(("Área de paso, cm²", f"{area:g}", "dato del usuario"))
    else:
        filas.append(("Diámetro del orificio, mm", f"{p['diametro_mm']:g}", _estado(e, "diametro_mm", base["paso"].get("diametro_mm"), p["diametro_mm"])))
    if h.get("modo", "cd") == "cd":
        filas.append(("Coeficiente de descarga", f"{h['cd']:g}", _estado(e, "cd", bh["cd"], h["cd"])))
    else:
        filas += [("Pérdida de entrada K", f"{h['k_entrada']:g}", _estado(e, "k_entrada", bh["k_entrada"], h["k_entrada"])),
                  ("Largo del canal, mm", f"{h['largo_mm']:g}", _estado(e, "largo_mm", bh["largo_mm"], h["largo_mm"])),
                  ("Rugosidad, mm", f"{h['rugosidad_mm']:g}", _estado(e, "rugosidad_mm", bh["rugosidad_mm"], h["rugosidad_mm"])),
                  ("Viscosidad del acero, Pa·s", f"{h['viscosidad']:g}", _estado(e, "viscosidad", bh["viscosidad"], h["viscosidad"]))]
    filas.append(("Caída bajo el orificio, mm", f"{h.get('caida_mm', 0):g}", _estado(e, "caida_mm", bh.get("caida_mm"), h.get("caida_mm", 0))))
    if e["tipo"] == "olla_distribuidor":
        v, d = e["valvula"], e["destino"]
        filas.append(("Abertura de la válvula, % de la carrera", f"{v.get('abertura_pct', 100):g}", "dato del usuario"))
        filas.append(("Destino", DESTINOS.get(d.get("tipo"), d.get("tipo")), "dato del usuario"))
        if d.get("tipo") == "nivel_constante":
            filas += [("Nivel del distribuidor, mm", f"{d['nivel_mm']:g}", _estado(e, "destino_nivel_mm", base["destino"]["nivel_mm"], d["nivel_mm"])),
                      ("Salida del tubo sobre el fondo del distribuidor, mm", f"{d['altura_salida_mm']:g}",
                       _estado(e, "destino_altura_salida_mm", base["destino"]["altura_salida_mm"], d["altura_salida_mm"]))]
        if d.get("tipo") == "llenado":
            filas += [("Fondo del distribuidor, mm", f"{d['largo_mm']:g} × {d['ancho_mm']:g}", "ejemplo"),
                      ("Talud de las paredes, °", f"{d.get('talud_grados', 0):g}", "ejemplo"),
                      ("Acero inicial en el distribuidor, t", f"{d.get('masa_inicial_t', 0):g}", "dato del usuario"),
                      ("Salida del tubo sobre el fondo del distribuidor, mm", f"{d['altura_salida_mm']:g}", "ejemplo")]
    return filas


def filas_de_resultado(r: ResultadoVaciado) -> list[tuple[str, str]]:
    s = resumen(r)
    filas = [("Tiempo de vaciado, s", f"{s['tiempo_s']:.0f}"), ("Tiempo de vaciado, min", f"{s['tiempo_min']:.2f}"),
             ("Acero vaciado, t", f"{s['acero_vaciado_t']:.1f}"), ("Caudal medio, t/min", f"{s['caudal_medio_t_min']:.1f}"),
             ("Caudal inicial / final, t/min", f"{s['caudal_inicial_t_min']:.1f} / {s['caudal_final_t_min']:.1f}"),
             ("Carga inicial / final, mm", f"{s['carga_inicial_mm']:.0f} / {s['carga_final_mm']:.0f}"),
             ("Velocidad inicial del chorro, m/s", f"{s['velocidad_inicial_m_s']:.2f}"),
             ("Área de paso, cm²", f"{s['area_de_paso_cm2']:.1f} (Ø{s['diametro_mm']:.1f} mm)"),
             ("Superficie libre inicial, m²", f"{s['area_superficie_m2']:.2f}")]
    if s["fraccion_abierta"] < 1.0:
        filas.append(("Fracción de área abierta de la válvula", f"{s['fraccion_abierta']:.3f}"))
    if s["tiempo_torricelli_s"] is not None:
        dif = (r.tiempo - s["tiempo_torricelli_s"]) / s["tiempo_torricelli_s"] * 100 if s["tiempo_torricelli_s"] else math.nan
        filas.append(("Solución cerrada de Torricelli, s", f"{s['tiempo_torricelli_s']:.0f} ({dif:+.2f} %)"))
    if r.config is not None and not math.isnan(float(r.nivel_destino[-1])):
        filas.append(("Nivel final del distribuidor sobre su fondo, mm", f"{float(r.nivel_destino[-1]):.0f}"))
    filas.append(("Fin", r.motivo_fin))
    return filas


def texto(e: dict, r: ResultadoVaciado) -> str:
    L = [f"{r.nombre or TIPOS[completar(e)['tipo']]}"] + [f"  {a}: {b}" for a, b in filas_de_resultado(r)]
    L += [f"  aviso a los {t:.0f} s: {x}" for t, x in r.eventos if x != r.motivo_fin]
    return "\n".join(L)


def _serie(r: ResultadoVaciado, cada: float):
    siguiente = 0.0
    for i in range(len(r.t)):
        if r.t[i] + 1e-9 >= siguiente or i == len(r.t) - 1:
            yield i
            siguiente = r.t[i] + cada


COLUMNAS = ["tiempo, s", "acero en el recipiente, t", "acero sobre el orificio, mm", "carga, mm", "caudal, t/min",
            "nivel del distribuidor, mm"]


def _fila(r: ResultadoVaciado, i: int) -> list:
    n = float(r.nivel_destino[i])
    return [round(float(r.t[i]), 2), round(float(r.masa[i]), 2), round(float(r.altura[i]), 1), round(float(r.carga[i]), 1),
            round(float(r.caudal[i]) * 60, 3), None if math.isnan(n) else round(n, 1)]


def escribir_csv(r: ResultadoVaciado, ruta: Path, cada: float = 1.0) -> None:
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["# " + AVISO + f" Modelo {VERSION_MODELO}. {r.nombre}"])
        w.writerow(COLUMNAS)
        for i in _serie(r, cada):
            w.writerow(["" if v is None else v for v in _fila(r, i)])


def escribir_excel(e: dict, r: ResultadoVaciado, ruta: Path) -> None:
    from openpyxl import Workbook
    from openpyxl.chart import LineChart, Reference
    from openpyxl.styles import Font

    libro = Workbook()
    h = libro.active
    h.title = "Resumen"
    h.append([r.nombre or "Escenario de vaciado"])
    h.append([f"{AVISO} Modelo {VERSION_MODELO}."])
    h.append([])
    for fila in filas_de_resultado(r):
        h.append(list(fila))
    h.column_dimensions["A"].width, h.column_dimensions["B"].width = 44, 48
    d = libro.create_sheet("Datos")
    d.append(["Dato", "Valor", "Estado"])
    for fila in filas_de_datos(e):
        d.append(list(fila))
    for col, ancho in zip("ABC", (50, 44, 26)):
        d.column_dimensions[col].width = ancho
    s = libro.create_sheet("Serie")
    s.append(COLUMNAS)
    for i in _serie(r, 1.0 if r.tiempo < 1800 else 10.0):
        s.append(_fila(r, i))
    n = s.max_row
    for k, (col, titulo) in enumerate(((2, "Acero en el recipiente, t"), (5, "Caudal, t/min"))):
        g = LineChart()
        g.title, g.height, g.width = titulo, 7.5, 15
        g.add_data(Reference(s, min_col=col, min_row=1, max_row=n), titles_from_data=True)
        g.set_categories(Reference(s, min_col=1, min_row=2, max_row=n))
        g.x_axis.title, g.legend = "tiempo, s", None
        g.x_axis.tickLblSkip = max(1, n // 10)
        s.add_chart(g, f"H{2 + 16 * k}")
    for hoja in (h, d, s):
        for celda in hoja[1]:
            celda.font = Font(bold=True, size=13 if hoja is h else 11)
    libro.save(ruta)


def figura(r: ResultadoVaciado, fig) -> None:
    """Las cuatro series en el tiempo sobre una figura de Matplotlib (2 × 2)."""
    ejes = fig.subplots(2, 2, sharex=True) if not fig.axes else fig.axes
    ejes = list(getattr(ejes, "flat", ejes))
    tmin = r.t / 60.0
    datos = ((r.masa, "acero en el recipiente, t"), (r.caudal * 60, "caudal, t/min"), (r.altura, "acero sobre el orificio, mm"),
             (r.carga, "carga motriz, mm"))
    for ax, (y, rotulo) in zip(ejes, datos):
        ax.plot(tmin, y, lw=1.8)
        ax.set_ylabel(rotulo)
        ax.set_ylim(bottom=0)
    for ax in ejes[2:]:
        ax.set_xlabel("tiempo, min")


def escribir_pdf(e: dict, r: ResultadoVaciado, ruta: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    with PdfPages(ruta) as pdf:
        fig = plt.figure(figsize=(8.27, 11.69))
        fig.text(0.08, 0.95, f"Tiempo de vaciado: {TIPOS[completar(e)['tipo']]}", fontsize=16, weight="bold")
        fig.text(0.08, 0.925, r.nombre or "Escenario", fontsize=11)
        fig.text(0.08, 0.905, f"{AVISO} Modelo {VERSION_MODELO}.", fontsize=8, color="#8A5D00")
        y = 0.87
        for titulo, filas in (("Resultado", [(a, b, "") for a, b in filas_de_resultado(r)]), ("Datos del cálculo", filas_de_datos(e))):
            fig.text(0.08, y, titulo, fontsize=12, weight="bold")
            for a, b, est in filas:
                y -= 0.019
                fig.text(0.08, y, a, fontsize=9)
                fig.text(0.55, y, str(b)[:40], fontsize=9)
                fig.text(0.83, y, est, fontsize=7.5, color="#5F6164")
            y -= 0.035
        pdf.savefig(fig)
        plt.close(fig)
        fig = plt.figure(figsize=(11.69, 8.27))
        figura(r, fig)
        fig.suptitle(r.nombre or "Escenario", fontsize=11)
        fig.tight_layout(rect=(0.02, 0.03, 0.98, 0.96))
        pdf.savefig(fig)
        plt.close(fig)
