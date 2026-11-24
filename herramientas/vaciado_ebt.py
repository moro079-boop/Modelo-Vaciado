"""Reproduce el estudio de vaciado por el EBT de Magnesita para Pesquería (plano AV00025170, EAF-064).

Uso:  python -m herramientas.vaciado_ebt            (imprime las tablas y regenera las figuras de docs/figuras/)
      python -m herramientas.vaciado_ebt --sin-figuras
      python -m herramientas.vaciado_ebt --cad      (STL de la cavidad y DXF de las vistas inclinadas, en reportes/cad_vaciado_ebt/)

Qué hace, con ``datos/plantas/pesqueria.json`` (la geometría) y ``datos/estudios/vaciado_ebt_pesqueria.json`` (lo que
Magnesita escribió en el plano):

1. Construye el sólido de la cavidad, nuevo y gastado como lo rotula cada hoja.
2. Para cada vista inclinada del estudio calcula el nivel del baño sobre la boca del EBT que da el tonelaje rotulado y lo
   compara con la cota de Magnesita; lo mismo con las marcas de 150 y 450 t a 0° de las cinco hojas de desgaste.
3. Recalcula las curvas «carga segura» (baño a 300 mm del panel refrigerado) y «carga mínima» (arrastre de escoria).
4. Rehace la tabla de Magnesita (altura ferrostática media, flujo = k·√h, tiempo) con los niveles del sólido.

**El sólido de esta herramienta no es el del programa.** El plano solo dibuja el fondo en A-A y C-C; cómo sigue fuera de esos
dos cortes es un supuesto. El programa (``horno3d.cavidad_general``) mezcla por ángulo el casquete y la rampa en la mitad de
la piquera. Aquí se usa el **barrido**: el perfil transversal del casquete (C-C) trasladado a lo largo de la rampa de A-A. Se
eligió porque reproduce las marcas a 0° de las cinco hojas sin ninguna calibración; adoptarlo en el programa es decisión del
usuario (docs/pendientes.md). Nada de esto es una medición: es la reproducción de un cálculo teórico del proveedor.

Convenciones del proyecto: X + hacia la puerta, la piquera en X −; Y desde el fondo exterior de la coraza; inclinación +
hacia la piquera; mm y toneladas.
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from modelo_vaciado.horno3d import cavidad_general as cg
from modelo_vaciado.horno3d import niveles
from modelo_vaciado.horno3d.planta import cargar_planta

RAIZ = Path(__file__).resolve().parent.parent
ESTUDIO = RAIZ / "datos" / "estudios" / "vaciado_ebt_pesqueria.json"
CARPETA = RAIZ / "docs" / "figuras"
PASO = 20.0                 # mm; celda de la rejilla en planta (con 10 mm los niveles cambian menos de 1 mm)
FACTOR_NORMAL_MAX = 2.0     # como en el programa (EAF-039): el retroceso normal del piso se acota a 60° de pendiente
G = 9.81                    # m/s²


def cargar_estudio(ruta: Path | str = ESTUDIO) -> dict:
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# El sólido
# ---------------------------------------------------------------------------

def piso_barrido(planta: dict, X, Z) -> np.ndarray:
    """Cota del fondo nuevo en (X, Z). Hacia la puerta (X ≥ 0), el casquete de revolución de C-C. Hacia la piquera, el perfil
    transversal del casquete trasladado a lo largo de la rampa de A-A: rampa(|X|) + casquete(|Z|) − casquete(0). **Supuesto.**"""
    f = planta["cavidad_general"]["piso"]
    cr, cy = np.asarray(f["cuenco"]["r"], float), np.asarray(f["cuenco"]["y"], float)
    nx, ny = np.asarray(f["nariz"]["x_abs"], float), np.asarray(f["nariz"]["y"], float)
    X, Z = np.asarray(X, float), np.asarray(Z, float)
    puerta = cg._extrapolar(cr, cy, np.hypot(X, Z))
    piquera = cg._extrapolar(nx, ny, np.abs(X)) + cg._extrapolar(cr, cy, np.abs(Z)) - cy[0]
    return np.where(X >= 0.0, puerta, piquera)


def piso_gastado(planta: dict, X, Z, piso_mm: float) -> np.ndarray:
    """El fondo tras perder ``piso_mm`` perpendicular a su superficie (baja piso_mm / cos α, acotado como en el programa)."""
    F = piso_barrido(planta, X, Z)
    if piso_mm <= 0.0:
        return F
    d = 10.0
    gx = (piso_barrido(planta, X + d, Z) - piso_barrido(planta, X - d, Z)) / (2 * d)
    gz = (piso_barrido(planta, X, Z + d) - piso_barrido(planta, X, Z - d)) / (2 * d)
    return F - piso_mm * np.minimum(np.sqrt(1.0 + gx * gx + gz * gz), FACTOR_NORMAL_MAX)


@dataclass(frozen=True)
class Solido:
    """Cavidad como columnas verticales: el fondo de cada celda de la rejilla en planta (inf fuera de la cavidad)."""

    planta: dict
    paso: float
    X: np.ndarray       # (nx, nz) centro de cada celda
    fondo: np.ndarray   # (nx, nz) cota del fondo; inf fuera
    piso_mm: float
    pared_mm: float
    y_pared_desde: float

    def volumen(self, y_eje: float, angulo: float) -> float:
        """m³ bajo el plano Y = y_eje − tan(θ)·X."""
        sup = y_eje - math.tan(math.radians(angulo)) * self.X
        return float(np.clip(sup - self.fondo, 0.0, None).sum() * self.paso * self.paso * 1e-9)

    def y_eje(self, toneladas: float, angulo: float, densidad: float) -> float:
        """Cota en el eje del plano que contiene ``toneladas`` (bisección, 0.01 mm)."""
        v, bajo, alto = toneladas / densidad, -3000.0, 8000.0
        while alto - bajo > 0.01:
            medio = 0.5 * (bajo + alto)
            if self.volumen(medio, angulo) < v:
                bajo = medio
            else:
                alto = medio
        return 0.5 * (bajo + alto)


def construir_solido(planta: dict, piso_mm: float = 0.0, pared_mm: float = 0.0, y_pared_desde: float = 1590.0,
                     paso: float = PASO) -> Solido:
    """Paredes verticales sobre el contorno en planta del archivo; ``pared_mm`` ensancha el contorno desde ``y_pared_desde``
    hacia arriba (la base de la hilada 6: en la hoja 8 las hiladas 1 a 5 siguen con 450 mm)."""
    r_max = float(max(planta["cavidad_general"]["contorno"]["radios"])) + pared_mm + 2 * paso
    xs = np.arange(-math.ceil(r_max / paso) * paso, math.ceil(r_max / paso) * paso, paso) + paso / 2
    X, Z = np.meshgrid(xs, xs, indexing="ij")
    r = np.hypot(X, Z)
    R0 = cg.radio_contorno(planta, np.degrees(np.arctan2(Z, X)))
    fondo = np.where(r <= R0, piso_gastado(planta, X, Z, piso_mm), np.inf)
    if pared_mm > 0.0:
        fondo = np.where((r > R0) & (r <= R0 + pared_mm), y_pared_desde, fondo)
    return Solido(planta, paso, X, fondo, piso_mm, pared_mm, y_pared_desde)


def distancia_vertical(y_eje: float, angulo: float, punto) -> float:
    """mm que el plano del baño queda por encima de ``punto`` (X, Y), medidos en vertical con el horno inclinado."""
    t = math.radians(angulo)
    return (y_eje - math.tan(t) * punto[0] - punto[1]) * math.cos(t)


def y_eje_a_distancia(distancia: float, angulo: float, punto) -> float:
    t = math.radians(angulo)
    return punto[1] + math.tan(t) * punto[0] + distancia / math.cos(t)


# ---------------------------------------------------------------------------
# La reproducción
# ---------------------------------------------------------------------------

def boca(estudio: dict, estado: str) -> tuple[float, float]:
    """Centro de la boca del EBT: el punto desde el que Magnesita acota los niveles."""
    p = estudio["piquera"]
    y = p["y_boca"]["valor"] - (p["acortamiento_gastado"]["valor"] if estado == "gastado" else 0.0)
    return float(p["x_eje"]["valor"]), float(y)


def solido_de(planta: dict, estudio: dict, estado: str) -> Solido:
    d = estudio["desgaste"][estado]
    return construir_solido(planta, d["piso_mm"], d["pared_mm"], d.get("y_pared_desde", 1590.0))


def coeficiente(estudio: dict, estado: str) -> float:
    """k de Q = k·√h (t/s por √mm) que usa la tabla de Magnesita: mediana de toneladas / tiempo / √h de sus renglones."""
    ps = estudio["escenarios"][estado]["pasos"]
    return float(np.median([(p["t_inicio"] - p["t_fin"]) / p["tiempo_s"] / math.sqrt(p["altura_ferrostatica"]) for p in ps]))


def coeficiente_de_descarga(estudio: dict, estado: str) -> float:
    """Cd equivalente de ese k con Torricelli, la densidad y el diámetro de salida del plano."""
    rho, d = estudio["densidad_acero"]["valor"], estudio["piquera"]["diametro_salida"]["valor"] / 1000.0
    k = coeficiente(estudio, estado)                      # t/s por √mm
    return k / (rho * math.pi * d * d / 4.0 * math.sqrt(2.0 * G / 1000.0))


def reproducir_escenario(planta: dict, estudio: dict, estado: str, solido: Solido | None = None) -> list[dict]:
    """Un renglón por ángulo: niveles del sólido contra los de Magnesita, y la tabla rehecha con los niveles del sólido."""
    s = solido or solido_de(planta, estudio, estado)
    rho, punto, k = estudio["densidad_acero"]["valor"], boca(estudio, estado), coeficiente(estudio, estado)
    filas = []
    for p in estudio["escenarios"][estado]["pasos"]:
        y0, y1 = s.y_eje(p["t_inicio"], p["angulo"], rho), s.y_eje(p["t_fin"], p["angulo"], rho)
        n0, n1 = distancia_vertical(y0, p["angulo"], punto), distancia_vertical(y1, p["angulo"], punto)
        h = 0.5 * (n0 + n1)
        q = k * math.sqrt(h)
        filas.append({**p, "y_eje_inicio": y0, "y_eje_fin": y1, "nivel_inicio_modelo": n0, "nivel_fin_modelo": n1,
                      "altura_modelo": h, "flujo_modelo": q, "tiempo_modelo": (p["t_inicio"] - p["t_fin"]) / q})
    return filas


def reproducir_marcas(planta: dict, estudio: dict) -> list[dict]:
    """Las marcas de 150 y 450 t a 0° de las hojas 1 y 3 a 6 (cinco estados de desgaste)."""
    m, rho, filas = estudio["marcas_a_0_grados"], estudio["densidad_acero"]["valor"], []
    for h in m["lista"]:
        s = construir_solido(planta, h["piso_gastado"], 450.0 - h["pared_restante"])
        fila = dict(h)
        for t in (150, 450):
            fila[f"y_{t}"] = m["y_referencia"] - h[f"cota_{t}"]
            fila[f"y_{t}_modelo"] = s.y_eje(t, 0.0, rho)
        filas.append(fila)
    return filas


def reproducir_curvas(planta: dict, estudio: dict, estado: str, solido: Solido | None = None,
                      distancia_panel: float = 300.0, altura_minima: float = 700.0) -> list[dict]:
    """Por ángulo: la carga con el baño a ``distancia_panel`` del panel (amarilla) y la carga con ``altura_minima`` de acero
    sobre la boca del EBT (roja: el criterio no está escrito en el plano; 700 mm = 3.5 diámetros es lo que la reproduce)."""
    s = solido or solido_de(planta, estudio, estado)
    rho, c = estudio["densidad_acero"]["valor"], estudio["curvas"]
    panel, punto = (estudio["panel"]["x"], estudio["panel"]["y"]), boca(estudio, estado)
    filas = []
    for i, a in enumerate(c["angulos"]):
        y_min = s.y_eje(c[estado]["carga_minima_t"][i], a, rho)
        filas.append({
            "angulo": a,
            "segura": c[estado]["carga_segura_t"][i],
            "segura_modelo": s.volumen(y_eje_a_distancia(-distancia_panel, a, panel), a) * rho,
            "minima": c[estado]["carga_minima_t"][i],
            "minima_modelo": s.volumen(y_eje_a_distancia(altura_minima, a, punto), a) * rho,
            "altura_de_la_minima": distancia_vertical(y_min, a, punto),
        })
    return filas


def reproducir_talon(planta: dict, estudio: dict, estado: str, solido: Solido | None = None) -> dict:
    """Hoja 9: el talón a 15°. El nivel del sólido para esas toneladas y la altura media que le correspondería."""
    s = solido or solido_de(planta, estudio, estado)
    t = estudio["talon"][estado]
    nivel = distancia_vertical(s.y_eje(t["toneladas"], t["angulo"], estudio["densidad_acero"]["valor"]), t["angulo"],
                               boca(estudio, estado))
    k = coeficiente(estudio, estado)
    return {**t, "nivel_modelo": nivel, "altura_media_modelo": nivel / 2.0,
            "tiempo_con_altura_media": t["toneladas"] / (k * math.sqrt(nivel / 2.0)),
            "nivel_de_la_hoja": estudio["escenarios"][estado]["pasos"][-1]["nivel_fin"]}


def comparar_con_el_programa(planta: dict, estudio: dict) -> list[dict]:
    """Los niveles del escenario nuevo con la cavidad del programa (la de ``pesqueria.json``, calibrada, y la dibujada)."""
    rho, punto, filas = estudio["densidad_acero"]["valor"], boca(estudio, "nuevo"), []
    cavidades = {"calibrada": cg.construir_cavidad_general(planta),
                 "dibujada": cg.construir_cavidad_general(planta, ajuste=cg.Ajuste(0.0, 1.0))}
    for p in estudio["escenarios"]["nuevo"]["pasos"]:
        for t, n in ((p["t_inicio"], p["nivel_inicio"]), (p["t_fin"], p["nivel_fin"])):
            fila = {"angulo": p["angulo"], "toneladas": t, "nivel": n}
            for nombre, cav in cavidades.items():
                fila[nombre] = distancia_vertical(niveles.y_eje_para_volumen(cav, t / rho, p["angulo"]), p["angulo"], punto)
            filas.append(fila)
    return filas


# ---------------------------------------------------------------------------
# Texto
# ---------------------------------------------------------------------------

def informe(planta: dict, estudio: dict) -> str:
    L = []
    f = estudio["fuente"]
    L.append(f"Estudio de vaciado por el EBT — {f['proveedor']}, plano {f['plano']} rev. {f['revision']} ({f['fecha_del_cajetin']})")
    L.append("Reproducción con el sólido de barrido (supuesto). Cálculo teórico del proveedor, no medición de planta.\n")
    L.append("Marcas a 0° (cota Y de la superficie en el eje, mm)")
    L.append("  hoja  piso gastado  pared restante |   150 t: plano  sólido   dif |   450 t: plano  sólido   dif")
    for m in reproducir_marcas(planta, estudio):
        L.append(f"  {m['hoja']:>4}  {m['piso_gastado']:>12g}  {m['pared_restante']:>14g} |"
                 f"  {m['y_150']:>12.0f}  {m['y_150_modelo']:>6.0f}  {m['y_150_modelo'] - m['y_150']:>+4.0f} |"
                 f"  {m['y_450']:>12.0f}  {m['y_450_modelo']:>6.0f}  {m['y_450_modelo'] - m['y_450']:>+4.0f}")
    for estado in ("nuevo", "gastado"):
        s = solido_de(planta, estudio, estado)
        e = estudio["escenarios"][estado]
        L.append(f"\nEscenario {estado} (hoja {e['hoja']}): niveles sobre la boca del EBT (mm) y tabla de vaciado")
        L.append(f"  k = {coeficiente(estudio, estado):.6f} t/s por √mm  (Cd = {coeficiente_de_descarga(estudio, estado):.4f} con Ø200 y 6.9 t/m³)")
        L.append("  ángulo   t inicio → fin |  nivel inicio: plano sólido dif |  nivel fin: plano sólido dif |  tiempo: plano  sólido")
        filas = reproducir_escenario(planta, estudio, estado, s)
        for p in filas:
            L.append(f"  {p['angulo']:>5}°  {p['t_inicio']:>8g} → {p['t_fin']:<4g} |"
                     f"  {p['nivel_inicio']:>18g} {p['nivel_inicio_modelo']:>6.0f} {p['nivel_inicio_modelo'] - p['nivel_inicio']:>+4.0f} |"
                     f"  {p['nivel_fin']:>15g} {p['nivel_fin_modelo']:>6.0f} {p['nivel_fin_modelo'] - p['nivel_fin']:>+4.0f} |"
                     f"  {p['tiempo_s']:>13.2f} {p['tiempo_modelo']:>7.2f}")
        L.append(f"  total: plano {e['tiempo_total_s']:.2f} s, sólido {sum(p['tiempo_modelo'] for p in filas):.2f} s")
        L.append("  curvas:  ángulo | carga segura (300 mm del panel): gráfica  sólido | carga mínima: gráfica  sólido (700 mm sobre la boca) | altura de la mínima de la gráfica")
        for c in reproducir_curvas(planta, estudio, estado, s):
            L.append(f"           {c['angulo']:>5}° | {c['segura']:>39g} {c['segura_modelo']:>7.0f} | {c['minima']:>21g} {c['minima_modelo']:>7.0f}"
                     f" {'':>22}| {c['altura_de_la_minima']:>6.0f}")
        t = reproducir_talon(planta, estudio, estado, s)
        L.append(f"  talón (hoja 9): {t['toneladas']} t a {t['angulo']}°. La tabla usa h = {t['altura_ferrostatica']} mm ({t['tiempo_s']} s). "
                 f"El sólido da {t['nivel_modelo']:.0f} mm sobre la boca (la hoja {e['hoja']} acota {t['nivel_de_la_hoja']}); "
                 f"con su mitad, {t['altura_media_modelo']:.0f} mm, serían {t['tiempo_con_altura_media']:.0f} s.")
    L.append("\nEscenario nuevo con la cavidad del programa (nivel sobre la boca, mm; diferencia con el plano)")
    L.append("  ángulo  toneladas  plano | calibrada  dif | dibujada  dif")
    for c in comparar_con_el_programa(planta, estudio):
        L.append(f"  {c['angulo']:>5}°  {c['toneladas']:>9g}  {c['nivel']:>5g} | {c['calibrada']:>9.0f} {c['calibrada'] - c['nivel']:>+4.0f} |"
                 f" {c['dibujada']:>8.0f} {c['dibujada'] - c['nivel']:>+4.0f}")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# Figuras
# ---------------------------------------------------------------------------

AZUL, VERDE, GRIS, AMARILLO, ROJO = "#1f4fd8", "#1a9a32", "#8a8f98", "#e0a800", "#d62828"
ROTULO = "Reproducción del cálculo teórico de Magnesita (plano AV00025170). Sólido de barrido: supuesto. No es una medición."


def _girar(x, y, angulo: float):
    """Del marco del horno a la vista: inclinación + baja la piquera (X −)."""
    t = math.radians(angulo)
    x, y = np.asarray(x, float), np.asarray(y, float)
    return x * math.cos(t) - y * math.sin(t), x * math.sin(t) + y * math.cos(t)


def perfil_del_eje(s: Solido, estudio: dict, estado: str) -> tuple[np.ndarray, np.ndarray]:
    """Contorno de la cavidad en el plano del eje (Z = 0): pared de la nariz, fondo con el canal del EBT, y pared de la puerta."""
    pl = s.planta
    g = pl["cavidad_general"]
    xn, xp = -float(cg.radio_contorno(pl, 180.0)), float(cg.radio_contorno(pl, 0.0))
    x = np.arange(xn, xp + 1.0, 10.0)
    y = piso_gastado(pl, x, np.zeros_like(x), s.piso_mm)
    y_nariz, y_puerta = float(g["fin_refractario"]["nariz"]["valor"]), float(g["puerta"]["y_umbral"]["valor"])
    if s.pared_mm > 0.0:
        px = [xn - s.pared_mm, xn - s.pared_mm, xn, *x, xp, xp + s.pared_mm, xp + s.pared_mm]
        py = [y_nariz, s.y_pared_desde, s.y_pared_desde, *y, s.y_pared_desde, s.y_pared_desde, y_puerta]
    else:
        px, py = [xn, *x, xp], [y_nariz, *y, y_puerta]
    return np.asarray(px, float), np.asarray(py, float)


def _bano(px, py, y_eje: float, angulo: float):
    """Polígono del acero en el corte del eje: entre el contorno y el plano del baño."""
    xs = np.linspace(px.min(), px.max(), 1500)
    fondo = np.full_like(xs, np.inf)
    # el contorno de abajo: en cada x, la cota más baja del perfil (el fondo; las paredes son verticales)
    orden = np.argsort(px, kind="stable")
    fondo = np.interp(xs, px[orden], py[orden])
    sup = y_eje - math.tan(math.radians(angulo)) * xs
    moja = sup > fondo
    if not moja.any():
        return None
    i = np.nonzero(moja)[0]
    xa = xs[i[0]:i[-1] + 1]
    return np.concatenate([xa, xa[::-1]]), np.concatenate([sup[i[0]:i[-1] + 1], np.maximum(fondo, -1e9)[i[0]:i[-1] + 1][::-1]])


def _vista(ax, s: Solido, estudio: dict, estado: str, angulo: float, niveles_t: list, titulo: str, pie: str):
    px, py = perfil_del_eje(s, estudio, estado)
    rho, punto = estudio["densidad_acero"]["valor"], boca(estudio, estado)
    for (t, color) in niveles_t:
        y = s.y_eje(t, angulo, rho)
        pol = _bano(px, py, y, angulo)
        if pol is not None:
            gx, gy = _girar(*pol, angulo)
            ax.fill(gx, gy, color=color, alpha=0.22, lw=0)
            sx = np.array([pol[0][0], pol[0][len(pol[0]) // 2 - 1]])
            lx, ly = _girar(sx, y - math.tan(math.radians(angulo)) * sx, angulo)
            ax.plot(lx, ly, color=color, lw=1.6)
            abajo = color == VERDE
            ax.annotate(f"{t:g} t", (0.5 * (lx[0] + lx[1]) + (900 if abajo else -900), ly[1]), xytext=(0, -3 if abajo else 3),
                        textcoords="offset points", color=color, fontsize=8.5, ha="center", va="top" if abajo else "bottom")
    gx, gy = _girar(px, py, angulo)
    ax.plot(gx, gy, color="black", lw=1.6)
    # canal del EBT (esquema: Ø200 hasta el fondo de la coraza) y los dos puntos de referencia
    xb, yb = punto
    cx, cy = _girar([xb - 100, xb - 100, xb + 100, xb + 100], [yb, 340.0, 340.0, yb], angulo)
    ax.plot(cx, cy, color=GRIS, lw=1.0)
    bx, by = _girar([xb], [yb], angulo)
    ax.plot(bx, by, "o", color=ROJO, ms=4)
    ax.axhline(by[0], xmin=0.0, xmax=0.35, color=ROJO, lw=0.6, ls=":")
    qx, qy = _girar([estudio["panel"]["x"]], [estudio["panel"]["y"]], angulo)
    ax.plot(qx, qy, "s", color=AMARILLO, ms=4)
    ex, ey = _girar([0, 0], [800, 3900], angulo)
    ax.plot(ex, ey, color=GRIS, lw=0.6, ls="-.")
    ax.set_title(titulo, fontsize=9, loc="left")
    ax.text(0.5, -0.02, pie, transform=ax.transAxes, fontsize=7.5, ha="center", va="top")
    ax.set_aspect("equal")
    ax.set_xlim(-6500, 4700)
    ax.set_ylim(-700, 4500)
    ax.axis("off")


def figura_vistas(planta: dict, estudio: dict, estado: str, ruta: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    s = solido_de(planta, estudio, estado)
    filas = reproducir_escenario(planta, estudio, estado, s)
    fig, ejes = plt.subplots(2, 3, figsize=(16, 8.4))
    acumulado = 0.0
    for ax, p in zip(ejes.flat, filas):
        acumulado += p["tiempo_s"]
        _vista(ax, s, estudio, estado, p["angulo"], [(p["t_inicio"], AZUL), (p["t_fin"], VERDE)],
               f"{p['angulo']}°: de {p['t_inicio']:g} a {p['t_fin']:g} t en el horno ({p['tiempo_s']:.0f} s; acumulado {acumulado:.0f} s)",
               f"nivel sobre la boca del EBT, mm — plano: {p['nivel_inicio']:g} → {p['nivel_fin']:g};  "
               f"sólido: {p['nivel_inicio_modelo']:.0f} → {p['nivel_fin_modelo']:.0f}")
    t = reproducir_talon(planta, estudio, estado, s)
    _vista(ejes.flat[5], s, estudio, estado, t["angulo"], [(t["toneladas"], AZUL)],
           f"Hoja 9 — talón: {t['toneladas']} t a {t['angulo']}° hasta vaciar ({t['tiempo_s']:.0f} s en el plano)",
           f"la tabla usa h = {t['altura_ferrostatica']} mm; el sólido da {t['nivel_modelo']:.0f} mm sobre la boca "
           f"(media {t['altura_media_modelo']:.0f})")
    d = estudio["desgaste"][estado]
    fig.suptitle(f"Pesquería — vaciado por el EBT, revestimiento {estado} (hoja {estudio['escenarios'][estado]['hoja']}: "
                 f"fondo gastado {d['piso_mm']:g} mm, pared gastada {d['pared_mm']:g} mm).  Corte por el eje; la piquera a la izquierda.",
                 fontsize=11, x=0.01, ha="left")
    fig.text(0.01, 0.012, ROTULO + "   ● boca del EBT (referencia de los niveles)   ■ esquina del panel refrigerado   azul: inicio del ángulo; verde: final",
             fontsize=8, color="#444")
    fig.subplots_adjust(left=0.01, right=0.99, top=0.93, bottom=0.07, wspace=0.02, hspace=0.16)
    fig.savefig(ruta, dpi=110)
    plt.close(fig)


def figura_curvas(planta: dict, estudio: dict, ruta: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ejes = plt.subplots(2, 2, figsize=(15, 8.6), sharex="col")
    for col, estado in enumerate(("nuevo", "gastado")):
        s = solido_de(planta, estudio, estado)
        filas = reproducir_escenario(planta, estudio, estado, s)
        curvas = reproducir_curvas(planta, estudio, estado, s)
        t0 = np.concatenate([[0.0], np.cumsum([p["tiempo_s"] for p in filas])])
        ax = ejes[0, col]
        ax.plot(t0, [filas[0]["t_inicio"]] + [p["t_fin"] for p in filas], "-o", color="black", ms=4, label="acero en el horno (tabla del plano)")
        for clave, color, nombre in (("segura", AMARILLO, "carga segura: baño a 300 mm del panel"),
                                     ("minima", ROJO, "carga mínima: arrastre de escoria")):
            ax.step(t0, [c[clave + "_modelo"] for c in curvas] + [curvas[-1][clave + "_modelo"]], where="post", color=color, lw=1.8,
                    label=nombre + (" (sólido)" if clave == "segura" else " (sólido, 700 mm sobre la boca)"))
            ax.plot(0.5 * (t0[:-1] + t0[1:]), [c[clave] for c in curvas], "D", color=color, ms=6, mfc="white",
                    label="  leído de la gráfica del plano")
        for i, p in enumerate(filas):
            ax.text(0.5 * (t0[i] + t0[i + 1]), 8, f"{p['angulo']}°", ha="center", fontsize=9, color=GRIS)
        ax.set_ylabel("toneladas")
        ax.set_ylim(0, 900 if estado == "gastado" else 680)
        ax.grid(alpha=0.3)
        ax.set_title(f"Revestimiento {estado} (hoja {estudio['escenarios'][estado]['hoja']}) — «Tapping over time»", fontsize=10, loc="left")
        ax.legend(fontsize=7.5, loc="upper right", ncol=1)
        ax = ejes[1, col]
        tt, plano, modelo = [], [], []
        for i, p in enumerate(filas):
            tt += [t0[i], t0[i + 1]]
            plano += [p["nivel_inicio"], p["nivel_fin"]]
            modelo += [p["nivel_inicio_modelo"], p["nivel_fin_modelo"]]
        ax.plot(tt, plano, "-o", color="black", ms=4, label="cotas del plano")
        ax.plot(tt, modelo, "--s", color=AZUL, ms=4, mfc="white", label="sólido reproducido")
        for x, y in zip(tt, plano):
            ax.annotate(f"{y:g}", (x, y), xytext=(0, 6), textcoords="offset points", ha="center", fontsize=7.5)
        ax.set_ylabel("nivel del baño sobre la boca del EBT, mm")
        ax.set_xlabel("tiempo, s (el de la tabla del plano)")
        ax.set_ylim(0, 1400)
        ax.grid(alpha=0.3)
        ax.set_title("«Bath level over time»: cada salto es el basculado al ángulo siguiente", fontsize=10, loc="left")
        ax.legend(fontsize=8, loc="lower left")
    fig.text(0.01, 0.01, ROTULO, fontsize=8, color="#444")
    fig.tight_layout(rect=(0, 0.025, 1, 1))
    fig.savefig(ruta, dpi=110)
    plt.close(fig)


# ---------------------------------------------------------------------------
# CAD: el sólido en STL y las vistas inclinadas en DXF
# ---------------------------------------------------------------------------

Y_TOPE_CAD = 3290.0     # tope de la zona de escoria (hilada 22): hasta ahí se cierra el sólido exportado
PASO_CAD = 50.0


def malla_cavidad(s: Solido, y_tope: float = Y_TOPE_CAD) -> np.ndarray:
    """Triángulos (n, 3, 3) del volumen de la cavidad hasta ``y_tope``, cerrado, en mm y con Z hacia arriba:
    (x, y, z) del archivo = (X del horno, Z del horno, Y del horno). El fondo se suaviza con la cota en cada nodo de la rejilla."""
    pl, h = s.planta, s.paso
    dentro = np.isfinite(s.fondo)
    nx, nz = dentro.shape
    x0 = s.X[0, 0] - h / 2
    xn = x0 + h * np.arange(nx + 1)
    zn = x0 + h * np.arange(nz + 1)
    XN, ZN = np.meshgrid(xn, zn, indexing="ij")
    yn = piso_gastado(pl, XN, ZN, s.piso_mm)
    if s.pared_mm > 0.0:        # el anillo que deja la pared gastada: su fondo es la base de la hilada 6
        fuera = np.hypot(XN, ZN) > cg.radio_contorno(pl, np.degrees(np.arctan2(ZN, XN)))
        yn = np.where(fuera, s.y_pared_desde, yn)
    yn = np.minimum(yn, y_tope)

    def p(i, j, arriba):
        return (xn[i], zn[j], y_tope if arriba else yn[i, j])

    tri = []
    for i, j in zip(*np.nonzero(dentro)):
        a, b, c, d = (i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)
        tri += [(p(*a, 1), p(*b, 1), p(*c, 1)), (p(*a, 1), p(*c, 1), p(*d, 1))]          # tapa (normal +z)
        tri += [(p(*a, 0), p(*c, 0), p(*b, 0)), (p(*a, 0), p(*d, 0), p(*c, 0))]          # fondo (normal −z)
        for (u, v), (di, dj) in (((a, b), (0, -1)), ((b, c), (1, 0)), ((c, d), (0, 1)), ((d, a), (-1, 0))):
            ii, jj = i + di, j + dj
            if 0 <= ii < nx and 0 <= jj < nz and dentro[ii, jj]:
                continue
            tri += [(p(*u, 0), p(*v, 0), p(*v, 1)), (p(*u, 0), p(*v, 1), p(*u, 1))]      # pared del borde (normal hacia fuera)
    return np.asarray(tri, float)


def volumen_de_malla(tri: np.ndarray) -> float:
    """m³ encerrados por la malla (suma de tetraedros con signo): comprueba que está cerrada y bien orientada."""
    return float(np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum() / 6.0 * 1e-9)


def escribir_stl(tri: np.ndarray, ruta: Path, nombre: str) -> None:
    import struct

    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    with open(ruta, "wb") as f:
        f.write(nombre.encode("ascii", "replace")[:80].ljust(80, b" "))
        f.write(struct.pack("<I", len(tri)))
        for k in range(len(tri)):
            f.write(struct.pack("<12fH", *n[k], *tri[k].ravel(), 0))


class _Dxf:
    """DXF R12 en ASCII, lo mínimo: capas, polilíneas, líneas, círculos y textos. Unidades: mm reales."""

    CAPAS = {"CAVIDAD": 7, "NIVEL_INICIO": 5, "NIVEL_FIN": 3, "EBT": 1, "PANEL": 2, "EJE": 8, "TEXTO": 7}

    def __init__(self):
        self.e = []

    def polilinea(self, capa, x, y, cerrada=False):
        self.e += ["0", "POLYLINE", "8", capa, "66", "1", "70", "1" if cerrada else "0"]
        for a, b in zip(x, y):
            self.e += ["0", "VERTEX", "8", capa, "10", f"{a:.1f}", "20", f"{b:.1f}"]
        self.e += ["0", "SEQEND", "8", capa]

    def linea(self, capa, x0, y0, x1, y1):
        self.e += ["0", "LINE", "8", capa, "10", f"{x0:.1f}", "20", f"{y0:.1f}", "11", f"{x1:.1f}", "21", f"{y1:.1f}"]

    def circulo(self, capa, x, y, r):
        self.e += ["0", "CIRCLE", "8", capa, "10", f"{x:.1f}", "20", f"{y:.1f}", "40", f"{r:.1f}"]

    def texto(self, x, y, alto, t, capa="TEXTO"):
        t = t.translate(str.maketrans("áéíóúñ°→−—", "aeioun  --")).replace("  ", " ")
        self.e += ["0", "TEXT", "8", capa, "10", f"{x:.1f}", "20", f"{y:.1f}", "40", f"{alto:.0f}", "1", t]

    def escribir(self, ruta: Path):
        c = ["0", "SECTION", "2", "TABLES", "0", "TABLE", "2", "LAYER", "70", str(len(self.CAPAS))]
        for nombre, color in self.CAPAS.items():
            c += ["0", "LAYER", "2", nombre, "70", "0", "62", str(color), "6", "CONTINUOUS"]
        c += ["0", "ENDTAB", "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES", *self.e, "0", "ENDSEC", "0", "EOF"]
        ruta.write_text("\n".join(c) + "\n", encoding="ascii")


def escribir_dxf_vistas(planta: dict, estudio: dict, estado: str, ruta: Path) -> None:
    """Las cinco vistas inclinadas de la hoja y la del talón, en el corte por el eje, a escala real (mm), una junto a otra."""
    s = solido_de(planta, estudio, estado)
    rho, punto = estudio["densidad_acero"]["valor"], boca(estudio, estado)
    px, py = perfil_del_eje(s, estudio, estado)
    d = _Dxf()
    vistas = [(p["angulo"], [(p["t_inicio"], "NIVEL_INICIO", p["nivel_inicio"]), (p["t_fin"], "NIVEL_FIN", p["nivel_fin"])],
               f"{p['angulo']} grados: {p['t_inicio']:g} a {p['t_fin']:g} t ({p['tiempo_s']:.0f} s en el plano)")
              for p in estudio["escenarios"][estado]["pasos"]]
    t = estudio["talon"][estado]
    vistas.append((t["angulo"], [(t["toneladas"], "NIVEL_INICIO", None)], f"Hoja 9: talon de {t['toneladas']} t a {t['angulo']} grados"))
    for k, (ang, niv, titulo) in enumerate(vistas):
        ox, oy = (k % 3) * 13000.0, -(k // 3) * 8000.0
        gx, gy = _girar(px, py, ang)
        d.polilinea("CAVIDAD", gx + ox, gy + oy)
        xb, yb = punto
        cx, cy = _girar([xb - 100, xb - 100, xb + 100, xb + 100], [yb, 340.0, 340.0, yb], ang)
        d.polilinea("EBT", cx + ox, cy + oy)
        bx, by = _girar([xb], [yb], ang)
        d.circulo("EBT", bx[0] + ox, by[0] + oy, 40.0)
        qx, qy = _girar([estudio["panel"]["x"]], [estudio["panel"]["y"]], ang)
        d.circulo("PANEL", qx[0] + ox, qy[0] + oy, 40.0)
        ex, ey = _girar([0, 0], [800, 3900], ang)
        d.linea("EJE", ex[0] + ox, ey[0] + oy, ex[1] + ox, ey[1] + oy)
        d.texto(ox - 6000, oy + 4800, 180, f"Pesqueria, revestimiento {estado}. {titulo}")
        for i, (ton, capa, cota) in enumerate(niv):
            y = s.y_eje(ton, ang, rho)
            pol = _bano(px, py, y, ang)
            if pol is None:
                continue
            m = len(pol[0]) // 2
            lx, ly = _girar(np.array([pol[0][0], pol[0][m - 1]]), y - math.tan(math.radians(ang)) * np.array([pol[0][0], pol[0][m - 1]]), ang)
            d.linea(capa, lx[0] + ox, ly[0] + oy, lx[1] + ox, ly[1] + oy)
            nivel = distancia_vertical(y, ang, punto)
            d.linea(capa, ox - 6200 - 300 * i, by[0] + oy, ox - 6200 - 300 * i, ly[0] + oy)      # la cota: de la boca al baño
            d.texto(ox - 6000, oy + 4400 - 300 * i, 150,
                    f"{ton:g} t: {nivel:.0f} mm sobre la boca del EBT (solido)" + (f"; el plano acota {cota:g}" if cota else ""), capa)
    d.texto(-6000, 5400, 200, "Reproduccion del calculo teorico de Magnesita (plano AV00025170). Solido de barrido: supuesto. No es una medicion ni el CAD del proveedor.")
    d.escribir(ruta)


def exportar_cad(planta: dict, estudio: dict, carpeta: Path) -> list[Path]:
    """STL de la cavidad (nueva y gastada) y DXF de las vistas inclinadas. Se escriben fuera del control de versiones (reportes/)."""
    carpeta.mkdir(parents=True, exist_ok=True)
    rutas = []
    for estado in ("nuevo", "gastado"):
        d = estudio["desgaste"][estado]
        s = construir_solido(planta, d["piso_mm"], d["pared_mm"], d.get("y_pared_desde", 1590.0), paso=PASO_CAD)
        tri = malla_cavidad(s)
        r = carpeta / f"pesqueria_cavidad_{estado}.stl"
        escribir_stl(tri, r, f"Pesqueria cavidad {estado} hasta Y {Y_TOPE_CAD:g} mm (reproduccion, supuesto)")
        rutas.append(r)
        r = carpeta / f"pesqueria_vaciado_{estado}.dxf"
        escribir_dxf_vistas(planta, estudio, estado, r)
        rutas.append(r)
    (carpeta / "LEEME.txt").write_text(
        "CAD de la reproduccion del estudio de vaciado por el EBT (EAF-064). Generado con: python -m herramientas.vaciado_ebt --cad\n\n"
        "NO es el CAD de Magnesita: es un solido reconstruido de los planos, con el fondo del lado de la piquera supuesto (barrido).\n\n"
        "pesqueria_cavidad_<estado>.stl  volumen interior del horno (lo que puede ocupar el bano) hasta Y = 3 290 mm, cerrado.\n"
        "                                Unidades mm. x = eje puerta(+)/piquera(-), y = transversal, z = altura desde el fondo de la coraza.\n"
        "                                Rejilla de 50 mm; las paredes salen escalonadas en planta. Sin el canal del EBT ni el nicho de la puerta.\n"
        "pesqueria_vaciado_<estado>.dxf  corte por el eje en los cinco angulos de la hoja y el talon de la hoja 9, a escala real (mm),\n"
        "                                con los niveles de inicio y final de cada angulo. Capas: CAVIDAD, NIVEL_INICIO, NIVEL_FIN, EBT, PANEL, EJE, TEXTO.\n",
        encoding="utf-8")
    rutas.append(carpeta / "LEEME.txt")
    return rutas


def regenerar_figuras(planta: dict, estudio: dict, carpeta: Path = CARPETA) -> list[Path]:
    rutas = [carpeta / "vaciado_ebt_pesqueria_nuevo.png", carpeta / "vaciado_ebt_pesqueria_gastado.png",
             carpeta / "vaciado_ebt_pesqueria_curvas.png"]
    figura_vistas(planta, estudio, "nuevo", rutas[0])
    figura_vistas(planta, estudio, "gastado", rutas[1])
    figura_curvas(planta, estudio, rutas[2])
    return rutas


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    planta, estudio = cargar_planta("pesqueria"), cargar_estudio()
    print(informe(planta, estudio))
    if "--cad" in argv:
        for r in exportar_cad(planta, estudio, RAIZ / "reportes" / "cad_vaciado_ebt"):
            print("escrito", r.relative_to(RAIZ))
        return 0
    if "--sin-figuras" not in argv:
        for r in regenerar_figuras(planta, estudio):
            print("escrita", r.relative_to(RAIZ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
