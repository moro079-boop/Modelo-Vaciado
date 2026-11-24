"""El tundish (artesa): volumen contra nivel y la salida al molde.

Geometría: prisma con el fondo rectangular (largo × ancho) y paredes en talud, de modo que a la altura h la sección es
(L + 2·h·tan α)·(W + 2·h·tan α). El volumen hasta h tiene forma cerrada.

Molde: la demanda de acero es Q = n · ρ_sólido · ancho · espesor · v_colada. La buza sumergida de cada línea tiene un caudal máximo
con el tapón abierto, Q_máx = ρ·C_d·A·√(2·g·H), con H = nivel del tundish + largo de la buza bajo el fondo − inmersión en el molde.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .valvula import Orificio


@dataclass(frozen=True)
class Tundish:
    largo: float             # mm, fondo
    ancho: float             # mm, fondo
    talud: float             # grados respecto de la vertical
    densidad: float          # t/m³ del acero líquido
    nivel_operacion: float   # mm
    nivel_minimo: float      # mm
    nivel_maximo: float      # mm

    def _t(self) -> float:
        return math.tan(math.radians(self.talud))

    def area(self, h: float) -> float:
        """m² de la superficie libre a la altura h (mm)."""
        t = self._t()
        return (self.largo + 2 * h * t) * (self.ancho + 2 * h * t) * 1e-6

    def volumen(self, h: float) -> float:
        """m³ hasta la altura h (mm)."""
        if h <= 0:
            return 0.0
        L, W, t = self.largo, self.ancho, self._t()
        v = L * W * h + (L + W) * t * h * h + 4.0 / 3.0 * t * t * h ** 3
        return v * 1e-9

    def masa(self, h: float) -> float:
        return self.volumen(h) * self.densidad

    def nivel(self, masa: float) -> float:
        """mm para una masa (t), por bisección."""
        if masa <= 0:
            return 0.0
        bajo, alto = 0.0, 10000.0
        for _ in range(60):
            medio = 0.5 * (bajo + alto)
            if self.masa(medio) < masa:
                bajo = medio
            else:
                alto = medio
        return 0.5 * (bajo + alto)


@dataclass(frozen=True)
class Moldes:
    lineas: int
    ancho: float             # mm
    espesor: float           # mm
    velocidad: float         # m/min
    densidad_solido: float   # t/m³
    buza: Orificio           # buza sumergida de cada línea
    largo_buza: float        # mm bajo el fondo del tundish
    inmersion: float         # mm de la salida de la buza bajo el menisco

    def demanda(self, velocidad: float | None = None) -> float:
        """t/s que pide la máquina a esa velocidad de colada."""
        v = self.velocidad if velocidad is None else velocidad
        return self.lineas * self.densidad_solido * (self.ancho / 1000.0) * (self.espesor / 1000.0) * v / 60.0

    def capacidad(self, nivel_tundish: float, densidad: float) -> float:
        """t/s que dejan pasar las buzas con el tapón abierto del todo."""
        return self.lineas * self.buza.caudal(nivel_tundish + self.largo_buza - self.inmersion, densidad)

    def velocidad_maxima(self, nivel_tundish: float, densidad: float) -> float:
        """m/min que admiten las buzas a ese nivel del tundish."""
        return self.capacidad(nivel_tundish, densidad) / self.demanda(1.0)
