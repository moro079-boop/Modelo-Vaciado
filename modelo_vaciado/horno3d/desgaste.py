"""Estado de desgaste manual (fase 3).

Decisiones del usuario del 2026-10-07 (pendientes 1, 5 y 6):
- Pared: un % del espesor de trabajo consumido, igual en todo el contorno y en toda la
  altura; se aplica al espesor de trabajo de cada zona del desarrollo y de A-A.
- Piso: un % del espesor de trabajo del fondo (el apisonado), con retroceso normal a la
  superficie: el casquete crece de radio y los taludes y la rampa se desplazan según su
  normal.

0 % reproduce el plano; 100 % deja la cara caliente en la capa de seguridad.

Fase 5: además del % uniforme, el estado puede ser un **perfil por línea** (``PerfilDesgaste``):
los milímetros de capa de trabajo perdidos en cada línea de 10 mm de altura, por separado en
el lado puerta (y el cuerpo) y en el lado nariz, más el retroceso del piso. Es lo que produce
el motor por colada (``lwd_eaf.campana``). Las líneas de 10 mm son las del LWD (10 líneas por
hilada de 100 mm) y las filas de la malla de la cavidad.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property

import numpy as np

PASO_LINEA = 10.0  # mm; altura de una línea de cálculo (la del LWD y la de la malla 3D)
N_LINEAS = 400  # líneas de 0 a 4 000 mm de altura (Y): Norte
N_LINEAS_NIVELES = 450  # las plantas de solo niveles (EAF-029): hasta Y = 4 500; Danieli llega a 4 265 y Fuchs a 4 389
# La malla de líneas, la cavidad y el motor de campaña suponen esta pared: 21 hiladas de 100 mm desde Y = 750 mm. Salen del plano
# de Largos Norte (A-A: «2100 = 21 hiladas»); ``planta.validar_planta`` exige que el archivo de planta diga lo mismo, de modo que
# una planta con otra pared falle con un mensaje y no calcule en silencio con la de Largos Norte.
N_HILADAS = 21
ALTURA_HILADA = 100.0  # mm
Y_BASE_HILADA_1 = 750.0  # mm


def hiladas_de(planta: dict) -> tuple[int, float, float]:
    """(cantidad de hiladas, Y de la base de la hilada 1, altura de hilada en mm) de la pared de la planta.

    Norte: las constantes de arriba (``planta.validar_planta`` exige que el archivo diga lo mismo). Plantas de solo niveles
    (EAF-027): el bloque ``desgaste.hiladas`` de su archivo.
    """
    if "pared" in planta:
        pared = planta["pared"]
        return N_HILADAS, float(pared["y_base_hilada_1"]["valor"]), float(pared["altura_de_hilada"]["valor"])
    h = planta["desgaste"]["hiladas"]
    return int(h["cantidad"]), float(h["y_base_hilada_1"]), float(h["altura_de_hilada"])


@dataclass(frozen=True)
class PerfilDesgaste:
    """mm de capa de trabajo perdidos por línea de 10 mm (índice j: Y de 10·j a 10·(j+1))."""

    puerta: tuple[float, ...]  # lado puerta de A-A y, por supuesto, todo el cuerpo
    nariz: tuple[float, ...]  # lado nariz de A-A y las columnas de la nariz
    piso: float = 0.0  # mm de retroceso normal del piso

    def __post_init__(self):
        for nombre in ("puerta", "nariz"):
            valores = getattr(self, nombre)
            if len(valores) not in (N_LINEAS, N_LINEAS_NIVELES):
                raise ValueError(f"el perfil «{nombre}» necesita {N_LINEAS} líneas (Norte) o {N_LINEAS_NIVELES} (plantas de solo "
                                 f"niveles), tiene {len(valores)}")
            if min(valores) < 0.0:
                raise ValueError(f"el perfil «{nombre}» tiene pérdidas negativas")
        if len(self.puerta) != len(self.nariz):
            raise ValueError("los dos lados del perfil necesitan el mismo número de líneas")
        if self.piso < 0.0:
            raise ValueError("el retroceso del piso no puede ser negativo")

    @classmethod
    def desde_arrays(cls, puerta, nariz, piso: float = 0.0) -> "PerfilDesgaste":
        return cls(tuple(float(v) for v in puerta), tuple(float(v) for v in nariz), float(piso))

    @cached_property
    def arrays(self) -> tuple[np.ndarray, np.ndarray]:
        return np.array(self.puerta), np.array(self.nariz)

    @property
    def es_nulo(self) -> bool:
        return self.piso == 0.0 and not any(self.puerta) and not any(self.nariz)

    def perdida(self, lado: str) -> np.ndarray:
        """Pérdida por línea de un lado de A-A. Los lados de la sección B-B (flancos del cuerpo)
        usan el perfil de la puerta."""
        return self.arrays[1] if lado == "nariz" else self.arrays[0]


@dataclass(frozen=True)
class Desgaste:
    pared: float = 0.0  # % del espesor de trabajo de la pared consumido
    piso: float = 0.0  # % del espesor de trabajo del piso consumido
    perfil: PerfilDesgaste | None = None  # con perfil, manda sobre los dos %, que quedan de referencia

    def __post_init__(self):
        for nombre in ("pared", "piso"):
            valor = getattr(self, nombre)
            if not 0.0 <= valor <= 100.0:
                raise ValueError(f"desgaste de {nombre} fuera de 0–100 %: {valor}")

    @property
    def fraccion_pared(self) -> float:
        return self.pared / 100.0

    @property
    def fraccion_piso(self) -> float:
        return self.piso / 100.0

    @property
    def es_nuevo(self) -> bool:
        if self.perfil is not None:
            return self.perfil.es_nulo
        return self.pared == 0.0 and self.piso == 0.0

    def __str__(self) -> str:
        if self.perfil is not None:
            return f"perfil por línea (pared hasta {self.pared:.1f} %, piso {self.piso:.1f} %)"
        return f"pared {self.pared:g} %, piso {self.piso:g} %"


NUEVO = Desgaste()


def espesor_trabajo_piso(planta: dict) -> float:
    """Espesor de la capa de trabajo del fondo (mm), del archivo de planta."""
    capas = planta["fondo"]["capas"]["lista"]
    return float(next(c["espesor"] for c in capas if c.get("funcion") == "trabajo"))


def retroceso_piso(planta: dict, desgaste: Desgaste | None) -> float:
    """Retroceso normal del piso en mm."""
    if desgaste is None:
        return 0.0
    if desgaste.perfil is not None:
        return desgaste.perfil.piso
    return desgaste.fraccion_piso * espesor_trabajo_piso(planta)
