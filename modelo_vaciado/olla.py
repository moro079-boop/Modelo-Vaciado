"""La olla de colada: geometría de revolución con la regla del Ladle Wear Diagnosis (LWD) y nivel del acero por masa.

La coraza es un tronco de cono cuyo radio varía linealmente entre la base y el tope; la cara caliente es la coraza menos el
aislante, la capa de seguridad y el espesor de trabajo de cada hilada. El acero ocupa el volumen por encima del piso. Es la misma
regla que el LWD (``calculo._inicializar``), en líneas de 10 mm, para que los niveles de los dos programas coincidan.

El desgaste se aplica como pérdida uniforme de la capa de trabajo de la pared (mm) y del piso (mm).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class GeometriaOlla:
    radio_coraza_superior: float     # mm
    radio_coraza_inferior: float     # mm
    espesor_aislante: float          # mm
    espesor_seguridad: float         # mm
    espesor_piso: float              # mm
    altura_de_hilada: float          # mm
    hiladas: tuple                   # ((desde, hasta, espesor_mm), ...)
    densidad: float                  # t/m³
    capacidad_nominal: float         # t

    @classmethod
    def de_datos(cls, d: dict) -> "GeometriaOlla":
        return cls(float(d["radio_coraza_superior_mm"]), float(d["radio_coraza_inferior_mm"]), float(d["espesor_aislante_mm"]),
                   float(d["espesor_seguridad_mm"]), float(d["espesor_piso_mm"]), float(d["altura_de_hilada_mm"]),
                   tuple((int(h["desde"]), int(h["hasta"]), float(h["espesor_mm"])) for h in d["hiladas"]),
                   float(d["densidad_acero"]["valor"]), float(d.get("capacidad_nominal_t") or 0.0))

    @property
    def n_hiladas(self) -> int:
        return max(h[1] for h in self.hiladas)

    @property
    def altura(self) -> float:
        return self.n_hiladas * self.altura_de_hilada

    def espesor_trabajo(self, z: np.ndarray) -> np.ndarray:
        """Espesor de la capa de trabajo a la altura z (mm), por hilada."""
        hilada = np.clip(np.floor(z / self.altura_de_hilada).astype(int) + 1, 1, self.n_hiladas)
        e = np.zeros_like(z, dtype=float)
        for desde, hasta, espesor in self.hiladas:
            e = np.where((hilada >= desde) & (hilada <= hasta), espesor, e)
        return e

    def radio_cara_caliente(self, z: np.ndarray, pared_gastada: float = 0.0) -> np.ndarray:
        z = np.asarray(z, dtype=float)
        coraza = self.radio_coraza_inferior + (self.radio_coraza_superior - self.radio_coraza_inferior) * z / self.altura
        trabajo = np.maximum(self.espesor_trabajo(z) - pared_gastada, 0.0)
        return coraza - self.espesor_aislante - self.espesor_seguridad - trabajo


@dataclass(frozen=True)
class TablaOlla:
    """Masa de acero (t) contra la altura del acero sobre el piso (mm), en pasos de 10 mm."""

    geometria: GeometriaOlla
    z_piso: float            # cota del piso (mm sobre la base de la coraza)
    alturas: np.ndarray      # mm sobre el piso
    masa: np.ndarray         # t

    @classmethod
    def de_geometria(cls, g: GeometriaOlla, pared_gastada: float = 0.0, piso_gastado: float = 0.0, paso: float = 10.0) -> "TablaOlla":
        z_piso = max(g.espesor_piso - piso_gastado, 0.0)
        z = np.arange(z_piso, g.altura + paso / 2, paso)
        area = math.pi * g.radio_cara_caliente(z + paso / 2, pared_gastada) ** 2         # mm², en el centro de cada capa
        vol = np.concatenate([[0.0], np.cumsum(area[:-1] * paso)]) * 1e-9                # m³ desde el piso
        return cls(g, z_piso, z - z_piso, vol * g.densidad)

    def altura(self, masa: float) -> float:
        """mm de acero sobre el piso."""
        return float(np.interp(masa, self.masa, self.alturas))

    def cota(self, masa: float) -> float:
        """Cota de la superficie, mm sobre la base de la coraza (la de las marcas del plano)."""
        return self.z_piso + self.altura(masa)

    def masa_a_cota(self, z: float) -> float:
        return float(np.interp(z - self.z_piso, self.alturas, self.masa))

    def area(self, masa: float, pared_gastada: float = 0.0) -> float:
        """m² de la superficie libre."""
        return math.pi * (float(self.geometria.radio_cara_caliente(np.array([self.cota(masa)]), pared_gastada)[0]) / 1000.0) ** 2

    @property
    def capacidad(self) -> float:
        return float(self.masa[-1])
