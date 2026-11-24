"""Válvula deslizante y buzas: área abierta y caudal por un orificio con carga.

Fracción de área abierta de dos orificios circulares iguales desplazados una distancia e (la misma que usa el modelo de desgaste de
la válvula deslizante, SGW):

    f_A = (2/π) · [arccos(x) − x·√(1 − x²)],   x = e / D,   e = (1 − abertura/100) · C

con D el diámetro del orificio y C la carrera efectiva (sin dato, C = D: la válvula cierra justo al recorrer un diámetro).
Caudal: Q = ρ · C_d · f_A · A · √(2·g·H), con H la carga en m de acero.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

G = 9.81


def fraccion_abierta(abertura: float, diametro: float, carrera: float | None = None) -> float:
    """f_A para una abertura en % de la carrera (100 = abierta del todo)."""
    c = carrera or diametro
    e = (1.0 - min(max(abertura, 0.0), 100.0) / 100.0) * c
    x = min(e / diametro, 1.0)
    return (2.0 / math.pi) * (math.acos(x) - x * math.sqrt(1.0 - x * x))


def abertura_para(fraccion: float, diametro: float, carrera: float | None = None) -> float:
    """La abertura (%) que da la fracción de área f_A (inversa por bisección)."""
    if fraccion >= 1.0:
        return 100.0
    if fraccion <= 0.0:
        return 100.0 * (1.0 - diametro / (carrera or diametro)) if carrera and carrera > diametro else 0.0
    bajo, alto = 0.0, 100.0
    for _ in range(50):
        medio = 0.5 * (bajo + alto)
        if fraccion_abierta(medio, diametro, carrera) < fraccion:
            bajo = medio
        else:
            alto = medio
    return 0.5 * (bajo + alto)


@dataclass(frozen=True)
class Orificio:
    diametro: float          # mm
    cd: float                # coeficiente de descarga

    @property
    def area(self) -> float:
        """m²."""
        return math.pi * (self.diametro / 1000.0) ** 2 / 4.0

    def caudal(self, carga_mm: float, densidad: float, fraccion: float = 1.0) -> float:
        """t/s con la carga en mm de acero."""
        if carga_mm <= 0.0 or fraccion <= 0.0:
            return 0.0
        return densidad * self.cd * fraccion * self.area * math.sqrt(2.0 * G * carga_mm / 1000.0)

    def carga_para(self, caudal: float, densidad: float, fraccion: float = 1.0) -> float:
        """mm de carga que hacen falta para un caudal (t/s)."""
        v = caudal / (densidad * self.cd * fraccion * self.area)
        return v * v / (2.0 * G) * 1000.0
