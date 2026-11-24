"""Nivel del baño sobre la boca de la piquera en función de la masa de acero y del ángulo de basculado.

La tabla se llena una vez con la cavidad 3D del programa (``horno3d.niveles.volumen``: volumen bajo el plano inclinado) y después
se interpola; así el integrador no vuelve a tocar la cavidad. ``NivelAnalitico`` da lo mismo para un recipiente de fórmula
conocida y sirve para comprobar el integrador.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .horno3d import niveles
from .horno3d.cavidad import Cavidad


def distancia_vertical(y_eje: float, angulo: float, punto) -> float:
    """mm que el plano del baño (Y = y_eje − tan θ·X en el marco del horno) queda sobre ``punto``, en vertical real."""
    t = math.radians(angulo)
    return (y_eje - math.tan(t) * punto[0] - punto[1]) * math.cos(t)


def y_eje_a_distancia(distancia: float, angulo: float, punto) -> float:
    t = math.radians(angulo)
    return punto[1] + math.tan(t) * punto[0] + distancia / math.cos(t)


@dataclass(frozen=True)
class TablaNiveles:
    angulos: np.ndarray     # (na,) grados, creciente
    y: np.ndarray           # (ny,) cota del baño en el eje, mm, creciente
    masa: np.ndarray        # (na, ny) toneladas bajo el plano; no decreciente en y
    boca: tuple[float, float]
    densidad: float

    @classmethod
    def de_cavidad(cls, cav: Cavidad, boca, densidad: float, angulo_maximo: float = 15.0, paso_angulo: float = 0.5,
                   paso_y: float = 10.0, angulo_minimo: float = 0.0) -> "TablaNiveles":
        angulos = np.arange(angulo_minimo, angulo_maximo + 1e-9, paso_angulo)
        margen = math.tan(math.radians(max(abs(angulo_minimo), abs(angulo_maximo)))) * float(np.abs(cav.x).max())
        y = np.arange(float(cav.y_inferior[0]) - margen - paso_y, cav.y_superior + margen + paso_y, paso_y)
        masa = np.array([[niveles.volumen(cav, float(yk), float(a)) for yk in y] for a in angulos]) * densidad
        return cls(angulos, y, masa, (float(boca[0]), float(boca[1])), float(densidad))

    # -- interpolación ------------------------------------------------------------------------------------------------------
    def _fila(self, angulo: float) -> tuple[int, float]:
        a = float(np.clip(angulo, self.angulos[0], self.angulos[-1]))
        i = int(min(np.searchsorted(self.angulos, a, side="right") - 1, len(self.angulos) - 2))
        return i, (a - self.angulos[i]) / (self.angulos[i + 1] - self.angulos[i])

    def _y_en_fila(self, i: int, masa: float) -> float:
        m = self.masa[i]
        j = int(np.searchsorted(m, masa, side="right"))        # primer índice con más masa: el baño está entre j−1 y j
        if j <= 0:
            return float(self.y[0])
        if j >= m.size:
            return float(self.y[-1])
        d = m[j] - m[j - 1]
        return float(self.y[j - 1] + (self.y[j] - self.y[j - 1]) * ((masa - m[j - 1]) / d if d > 0 else 0.0))

    def y_eje(self, masa: float, angulo: float) -> float:
        i, f = self._fila(angulo)
        return (1.0 - f) * self._y_en_fila(i, masa) + f * self._y_en_fila(i + 1, masa)

    def nivel_boca(self, masa: float, angulo: float) -> float:
        """mm de acero sobre la boca de la piquera (negativo: el baño no llega a la boca)."""
        return distancia_vertical(self.y_eje(masa, angulo), angulo, self.boca)

    def masa_bajo(self, y_eje: float, angulo: float) -> float:
        i, f = self._fila(angulo)
        return float((1.0 - f) * np.interp(y_eje, self.y, self.masa[i]) + f * np.interp(y_eje, self.y, self.masa[i + 1]))

    def masa_a_distancia(self, distancia: float, angulo: float, punto=None) -> float:
        """Toneladas con el baño a ``distancia`` mm por encima de ``punto`` (por omisión, la boca); negativa = por debajo."""
        return self.masa_bajo(y_eje_a_distancia(distancia, angulo, punto or self.boca), angulo)

    def con_boca(self, boca) -> "TablaNiveles":
        return TablaNiveles(self.angulos, self.y, self.masa, (float(boca[0]), float(boca[1])), self.densidad)


@dataclass(frozen=True)
class NivelAnalitico:
    """Recipiente prismático de área ``area_m2`` con la piquera en el fondo: nivel = masa / (ρ·área). Para pruebas."""

    area_m2: float
    densidad: float
    boca: tuple[float, float] = (0.0, 0.0)

    def nivel_boca(self, masa: float, angulo: float) -> float:
        return masa / (self.densidad * self.area_m2) * 1000.0

    def masa_a_distancia(self, distancia: float, angulo: float, punto=None) -> float:
        return distancia / 1000.0 * self.densidad * self.area_m2
