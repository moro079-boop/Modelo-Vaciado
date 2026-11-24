"""Mapas del vaciado del horno: el tiempo según el ángulo, según el diámetro de la piquera y a lo largo de la vida de la piquera.

- ``por_angulo``: para cada ángulo fijo, cuánto tarda en salir el acero hasta el objetivo, cuánto no sale a ese ángulo y si el
  baño invade el panel. Es la respuesta directa a «¿cuánto tarda el horno a X grados?».
- ``por_diametro``: el tiempo de una misma colada con el canal en distintos diámetros.
- ``por_colada``: el tiempo de cada colada con el diámetro creciendo una cantidad fija por colada hasta el cambio de piquera.
  La tasa de crecimiento es un dato de planta que falta; se declara al usarla.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .basculado import AnguloFijo
from .escenario import contexto_de, correr
from .datos import cargar
from .hidraulica import Hidraulica
from .simulacion import simular


@dataclass(frozen=True)
class FilaAngulo:
    angulo: float
    tiempo: float           # s hasta el objetivo o hasta que deja de salir
    colado: float           # t
    queda: float            # t en el horno al terminar
    llega: bool             # si alcanzó el acero objetivo
    invade_panel: bool      # si el baño inicial queda a menos de la distancia al panel
    caudal_medio: float     # t/s


def _hidraulica(e: dict, datos) -> Hidraulica:
    h = dict(e.get("hidraulica", {}))
    h.setdefault("cd", datos.cd)
    return Hidraulica(**h)


def por_angulo(e: dict, angulos=None, dt: float = 0.5) -> list[FilaAngulo]:
    """El escenario ``e`` repetido a cada ángulo fijo (se ignora su forma de bascular)."""
    c, datos = contexto_de(e)
    h = _hidraulica(e, datos)
    angulos = np.arange(0.0, datos.angulo_maximo + 1e-9, 1.0) if angulos is None else angulos
    m0, m1 = float(e["acero_inicial_t"]), float(e["acero_final_t"])
    filas = []
    for a in angulos:
        r = simular(c, h, AnguloFijo(float(a)), m0, m1, float(e.get("escoria_t", 0.0)), dt=dt, t_max=4 * 3600.0)
        filas.append(FilaAngulo(float(a), r.tiempo, r.colado, float(r.masa[-1]), r.motivo_fin.startswith("se alcanzó"),
                                m0 > c.carga_segura(float(a)) + 0.5, r.caudal_medio))
    return filas


def por_diametro(e: dict, diametros, dt: float = 0.5) -> list[tuple[float, float]]:
    """(diámetro, tiempo) del escenario con el canal en cada diámetro."""
    salida = []
    for d in diametros:
        e2 = dict(e, piquera=dict(e.get("piquera", {}), diametro=float(d)))
        salida.append((float(d), correr(e2, dt=dt).tiempo))
    return salida


def por_colada(e: dict, coladas: int, crecimiento_mm_por_colada: float, diametro_inicial: float | None = None,
               diametro_maximo: float | None = None, cada: int = 1, dt: float = 0.5) -> list[dict]:
    """El escenario en las coladas 1, 1 + cada, ... con D = D0 + crecimiento·(colada − 1), hasta ``diametro_maximo``.

    El tiempo con un diámetro dado no depende del número de colada, así que se interpola sobre unos pocos diámetros
    calculados y el resultado es el de un cálculo por colada a menos de 0.1 %."""
    datos = cargar(e["planta"])
    d0 = float(diametro_inicial or e.get("piquera", {}).get("diametro") or datos.piquera.diametro)
    n = np.arange(1, coladas + 1, max(int(cada), 1))
    d = d0 + crecimiento_mm_por_colada * (n - 1)
    if diametro_maximo:
        d = np.minimum(d, diametro_maximo)
    nodos = np.unique(np.round(np.linspace(d.min(), d.max(), min(9, max(2, len(np.unique(d))))), 3))
    tiempos = dict(por_diametro(e, nodos, dt=dt)) if len(nodos) > 1 else {float(nodos[0]): correr(e, dt=dt).tiempo}
    xs = np.array(sorted(tiempos))
    ys = np.array([tiempos[x] for x in xs])
    # el tiempo va como 1/D²: se interpola t·D² para que la interpolación sea casi exacta
    t = np.interp(d, xs, ys * xs ** 2) / d ** 2 if len(xs) > 1 else np.full_like(d, ys[0])
    return [{"colada": int(k), "diametro": float(dd), "tiempo_s": float(tt)} for k, dd, tt in zip(n, d, t)]


def angulo_optimo(e: dict) -> dict:
    """Compara la forma de bascular del escenario con la de «todo lo que permite el panel», que es la más rápida posible con
    las restricciones del modelo: a mayor ángulo, más acero sobre la piquera; y el panel limita el ángulo por arriba."""
    datos = cargar(e["planta"])
    base = correr(e)
    optimo = correr(dict(e, basculado={"tipo": "carga_segura", "velocidad": e.get("basculado", {}).get("velocidad", datos.velocidad_basculado)}))
    return {"tiempo_escenario_s": base.tiempo, "tiempo_optimo_s": optimo.tiempo,
            "ahorro_s": base.tiempo - optimo.tiempo, "ahorro_pct": 100.0 * (1 - optimo.tiempo / base.tiempo) if base.tiempo else math.nan}


__all__ = ["FilaAngulo", "por_angulo", "por_diametro", "por_colada", "angulo_optimo"]
