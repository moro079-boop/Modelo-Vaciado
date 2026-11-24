"""Salidas del modelo de vaciado: resumen en texto, serie en CSV y figura comparativa."""

from __future__ import annotations

import csv
from pathlib import Path

from . import VERSION_MODELO
from .simulacion import Resultado

AVISO = "PRELIMINAR: sin validar con tiempos de vaciado medidos en planta."


def resumen(r: Resultado) -> str:
    c = r.contexto
    L = [f"{r.nombre or 'Escenario'}",
         f"  acero: {r.masa[0]:.0f} → {r.masa[-1]:.1f} t ({r.colado:.1f} t coladas) en {r.tiempo:.1f} s ({r.tiempo / 60:.2f} min); "
         f"caudal medio {r.caudal_medio:.3f} t/s ({r.caudal_medio * 60:.1f} t/min)",
         f"  ángulo: {r.angulo[0]:.1f}° → {r.angulo[-1]:.1f}° (máximo {r.angulo.max():.1f}°); "
         f"acero sobre la boca: {r.altura[0]:.0f} → {r.altura[-1]:.0f} mm (mínimo {r.altura.min():.0f}, máximo {r.altura.max():.0f})",
         f"  fin: {r.motivo_fin}"]
    if c is not None:
        L.append(f"  canal Ø{c.diametro:g} mm, largo {c.piquera.largo:.0f} mm; altura mínima {c.altura_minima:.0f} mm; "
                 f"al final: carga mínima {c.carga_minima(float(r.angulo[-1])):.0f} t, no drenable {c.no_drenable(float(r.angulo[-1])):.1f} t")
    for t, texto in r.eventos:
        L.append(f"  aviso a los {t:.0f} s: {texto}")
    return "\n".join(L)


def escribir_csv(r: Resultado, ruta: Path, cada: float = 1.0) -> None:
    """La serie, una fila cada ``cada`` segundos (y la última)."""
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["# " + AVISO + f" Modelo {VERSION_MODELO}. {r.nombre}"])
        w.writerow(["tiempo_s", "acero_en_el_horno_t", "angulo_grados", "acero_sobre_la_boca_mm", "caudal_t_s"])
        siguiente = 0.0
        for i in range(len(r.t)):
            if r.t[i] + 1e-9 >= siguiente or i == len(r.t) - 1:
                w.writerow([f"{r.t[i]:.2f}", f"{r.masa[i]:.2f}", f"{r.angulo[i]:.2f}", f"{r.altura[i]:.1f}", f"{r.caudal[i]:.4f}"])
                siguiente = r.t[i] + cada


def figura(resultados: list[Resultado], ruta: Path, titulo: str = "") -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    colores = ["#18212b", "#1f55d0", "#e2681c", "#168a3a", "#8a3ab9", "#b98500", "#c8302b"]
    fig, ejes = plt.subplots(2, 2, figsize=(14, 8), sharex=True)
    paneles = (("masa", "acero en el horno, t"), ("angulo", "ángulo de basculado, grados"),
               ("altura", "acero sobre la boca de la piquera, mm"), ("caudal", "caudal, t/s"))
    for ax, (campo, rotulo) in zip(ejes.flat, paneles):
        for i, r in enumerate(resultados):
            ax.plot(r.t, getattr(r, campo), color=colores[i % len(colores)], lw=1.8,
                    label=f"{r.nombre} ({r.tiempo:.0f} s)" if campo == "masa" else None)
        ax.set_ylabel(rotulo)
        ax.grid(alpha=0.3)
        ax.set_ylim(bottom=0)
    c = resultados[0].contexto
    if c is not None:
        ejes[1, 0].axhline(c.altura_minima, color="#c8302b", lw=1, ls="--")
        ejes[1, 0].text(0, c.altura_minima, f" altura mínima {c.altura_minima:.0f} mm (arrastre de escoria)", color="#c8302b",
                        fontsize=8, va="bottom")
    ejes[0, 0].legend(fontsize=7.5, loc="lower left")
    for ax in ejes[1]:
        ax.set_xlabel("tiempo, s")
    fig.suptitle(titulo or "Modelo de vaciado por la piquera", fontsize=12, x=0.01, ha="left")
    fig.text(0.01, 0.01, f"{AVISO} Modelo {VERSION_MODELO}.", fontsize=8, color="#444")
    fig.tight_layout(rect=(0, 0.025, 1, 0.97))
    fig.savefig(ruta, dpi=110)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Excel y PDF (la aplicación de vaciado)
# ---------------------------------------------------------------------------

def filas_de_datos(escenario: dict, r: Resultado) -> list[tuple[str, str, str]]:
    """(dato, valor, estado) de lo que entró al cálculo, para la hoja «Datos» y la página de datos del PDF."""
    from .datos import cargar

    d, c = cargar(escenario["planta"]), r.contexto
    h, b, g = escenario.get("hidraulica", {}), escenario.get("basculado", {}), escenario.get("desgaste", {})
    cr = d.crudo
    modo = h.get("modo", "cd")
    filas = [
        ("Planta", escenario["planta"], ""),
        ("Acero inicial / final, t", f"{escenario['acero_inicial_t']:g} / {escenario['acero_final_t']:g}", "dato del usuario"),
        ("Escoria, t", f"{escenario.get('escoria_t', 0):g}", "dato del usuario"),
        ("Desgaste de pared / piso, % de la capa de trabajo", f"{g.get('pared', 0):g} / {g.get('piso', 0):g}", "dato del usuario"),
        ("Piquera: X, Y de la boca, mm", f"{c.piquera.x:g}, {c.piquera.y_boca:g}", cr["piquera"]["y_boca"]["estado"]),
        ("Piquera: largo del canal, mm", f"{c.piquera.largo:.0f}", cr["piquera"]["y_salida"]["estado"]),
        ("Piquera: diámetro del canal, mm", f"{c.diametro:g}",
         cr["piquera"]["diametro"]["estado"] if c.diametro == d.piquera.diametro else "dato del usuario"),
        ("Hidráulica", "coeficiente de descarga" if modo == "cd" else "pérdidas explícitas", ""),
        ("Carga medida hasta", "la boca del canal" if h.get("referencia", "boca") == "boca" else "la salida del canal", ""),
    ]
    if modo == "cd":
        cd = h.get("cd", d.cd)
        filas.append(("Coeficiente de descarga", f"{cd:g}", cr["coeficiente_de_descarga"]["estado"] if cd == d.cd else "dato del usuario"))
    else:
        filas += [("Pérdida de entrada K", f"{h.get('k_entrada', 0.5):g}", "supuesto"), ("Rugosidad del canal, mm", f"{h.get('rugosidad', 1.0):g}", "supuesto"),
                  ("Viscosidad del acero, Pa·s", f"{h.get('viscosidad', 0.006):g}", "supuesto")]
    tipo = b.get("tipo", "carga_segura")
    filas.append(("Basculado", {"escalones": "por escalones", "carga_segura": "continuo, todo lo que permite el panel", "fijo": "ángulo fijo"}[tipo], ""))
    if tipo == "escalones":
        filas.append(("Escalones (ángulo: hasta t)", ", ".join(f"{a:g}°: {m:g}" for a, m in b["pasos"]), "dato del usuario"))
    if tipo == "fijo":
        filas.append(("Ángulo, grados", f"{b['angulo']:g}", "dato del usuario"))
    v = b.get("velocidad", d.velocidad_basculado)
    filas += [("Velocidad de basculado, °/s", "instantáneo" if v in ("instantaneo", None) else f"{v:g}",
               cr["velocidad_basculado"]["estado"] if v == d.velocidad_basculado else "dato del usuario"),
              ("Distancia al panel refrigerado, mm", f"{c.distancia_panel:g}", cr["distancia_panel"]["estado"]),
              ("Altura mínima de acero sobre la boca, mm", f"{c.altura_minima:.0f}", cr["factor_altura_minima"]["estado"]),
              ("Densidad del acero / escoria, t/m³", f"{c.densidad:g} / {c.densidad_escoria:g}", "archivo de planta")]
    return [(a, b_, e.replace("_", " ")) for a, b_, e in filas]


def filas_de_resultado(r: Resultado) -> list[tuple[str, str]]:
    c = r.contexto
    a = float(r.angulo[-1])
    return [("Acero colado, t", f"{r.colado:.1f}"), ("Tiempo de vaciado, s", f"{r.tiempo:.1f}"), ("Tiempo de vaciado, min", f"{r.tiempo / 60:.2f}"),
            ("Caudal medio, t/min", f"{r.caudal_medio * 60:.1f}"), ("Caudal máximo, t/min", f"{r.caudal.max() * 60:.1f}"),
            ("Ángulo final, grados", f"{a:.1f}"), ("Acero sobre la boca: mínimo / máximo, mm", f"{r.altura.min():.0f} / {r.altura.max():.0f}"),
            ("Carga segura al ángulo final, t", f"{c.carga_segura(a):.0f}"), ("Carga mínima al ángulo final, t", f"{c.carga_minima(a):.0f}"),
            ("Acero no drenable al ángulo final, t", f"{c.no_drenable(a):.1f}"), ("Fin de la colada", r.motivo_fin)]


def escribir_excel(escenario: dict, r: Resultado, ruta: Path) -> None:
    from openpyxl import Workbook
    from openpyxl.chart import LineChart, Reference
    from openpyxl.styles import Font

    libro = Workbook()
    h = libro.active
    h.title = "Resumen"
    h.append([r.nombre or "Escenario de vaciado"])
    h["A1"].font = Font(bold=True, size=13)
    h.append([f"{AVISO} Modelo {VERSION_MODELO}."])
    h.append([])
    for fila in filas_de_resultado(r):
        h.append(list(fila))
    h.append([])
    h.append(["Avisos"])
    for t, texto in r.eventos or [(0, "ninguno")]:
        h.append([f"{t:.0f} s" if r.eventos else "", texto])
    h.column_dimensions["A"].width = 44
    h.column_dimensions["B"].width = 60
    d = libro.create_sheet("Datos")
    d.append(["Dato", "Valor", "Estado"])
    for fila in filas_de_datos(escenario, r):
        d.append(list(fila))
    for col, ancho in zip("ABC", (48, 44, 26)):
        d.column_dimensions[col].width = ancho
    s = libro.create_sheet("Serie")
    s.append(["tiempo, s", "acero en el horno, t", "ángulo, grados", "acero sobre la boca, mm", "caudal, t/s"])
    siguiente = 0.0
    for i in range(len(r.t)):
        if r.t[i] + 1e-9 >= siguiente or i == len(r.t) - 1:
            s.append([round(float(r.t[i]), 2), round(float(r.masa[i]), 2), round(float(r.angulo[i]), 2), round(float(r.altura[i]), 1), round(float(r.caudal[i]), 4)])
            siguiente = r.t[i] + 1.0
    n = s.max_row
    for k, (col, titulo) in enumerate(((2, "Acero en el horno, t"), (3, "Ángulo, grados"), (4, "Acero sobre la boca, mm"), (5, "Caudal, t/s"))):
        g = LineChart()
        g.title, g.height, g.width = titulo, 7.5, 15
        g.add_data(Reference(s, min_col=col, min_row=1, max_row=n), titles_from_data=True)
        g.set_categories(Reference(s, min_col=1, min_row=2, max_row=n))
        g.x_axis.title, g.legend = "tiempo, s", None
        g.x_axis.tickLblSkip = max(1, n // 10)
        s.add_chart(g, f"{'G' if k % 2 == 0 else 'Q'}{2 + 16 * (k // 2)}")
    for hoja in (h, d, s):
        for celda in hoja[1]:
            celda.font = Font(bold=True, size=13 if hoja is h else 11)
    libro.save(ruta)


def escribir_pdf(escenario: dict, r: Resultado, ruta: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    with PdfPages(ruta) as pdf:
        fig = plt.figure(figsize=(8.27, 11.69))
        fig.text(0.08, 0.95, "Vaciado por la piquera", fontsize=17, weight="bold")
        fig.text(0.08, 0.925, r.nombre or "Escenario", fontsize=11)
        fig.text(0.08, 0.905, f"{AVISO} Modelo {VERSION_MODELO}.", fontsize=8, color="#8A5D00")
        y = 0.87
        fig.text(0.08, y, "Resultado", fontsize=12, weight="bold")
        for a, b in filas_de_resultado(r):
            y -= 0.019
            fig.text(0.08, y, a, fontsize=9)
            fig.text(0.50, y, b, fontsize=9)
        y -= 0.035
        fig.text(0.08, y, "Datos del cálculo", fontsize=12, weight="bold")
        for a, b, e in filas_de_datos(escenario, r):
            y -= 0.019
            fig.text(0.08, y, a, fontsize=9)
            fig.text(0.50, y, b[:44], fontsize=9)
            fig.text(0.80, y, e, fontsize=7.5, color="#5F6164")
        y -= 0.035
        fig.text(0.08, y, "Avisos", fontsize=12, weight="bold")
        for t, texto in r.eventos or [(None, "Ninguno.")]:
            y -= 0.019
            fig.text(0.08, y, (f"A los {t:.0f} s: " if t is not None else "") + texto, fontsize=8.5, wrap=True)
        pdf.savefig(fig)
        plt.close(fig)
        fig, ejes = plt.subplots(4, 1, figsize=(8.27, 11.69), sharex=True)
        for ax, (campo, rotulo) in zip(ejes, (("masa", "acero en el horno, t"), ("angulo", "ángulo, grados"),
                                              ("altura", "acero sobre la boca, mm"), ("caudal", "caudal, t/s"))):
            ax.plot(r.t, getattr(r, campo), color="#25272A", lw=1.6)
            ax.set_ylabel(rotulo)
            ax.set_ylim(bottom=0)
            ax.grid(alpha=0.3)
        ejes[2].axhline(r.contexto.altura_minima, color="#A93526", lw=1, ls="--")
        ejes[-1].set_xlabel("tiempo, s")
        fig.suptitle(r.nombre or "Escenario", fontsize=11)
        fig.tight_layout(rect=(0.03, 0.03, 0.97, 0.97))
        pdf.savefig(fig)
        plt.close(fig)
