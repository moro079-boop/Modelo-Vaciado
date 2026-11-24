"""Caudal por el canal de la piquera.

Dos modos, los dos sobre la misma ecuación de energía entre la superficie del baño y la salida del canal:

- ``cd``        v = Cd·√(2·g·H). Un solo coeficiente que absorbe todas las pérdidas (y, si la carga se refiere a la boca, también
                el largo del canal). Es lo que hace el estudio de Magnesita: Cd = 0.731 con H medida hasta la boca.
- ``perdidas``  v = √(2·g·H / (1 + K + f·L/D)), con K la pérdida de entrada y f el factor de fricción de Darcy del canal
                (Swamee–Jain, con el número de Reynolds del propio flujo). Aquí H se refiere a la salida.

``referencia`` dice hasta dónde se mide la carga: ``boca`` (la entrada del canal, como Magnesita) o ``salida`` (la boca más la
caída vertical del canal lleno, L·cos(θ + inclinación)). Unidades de entrada: mm, grados, t/m³. Salida: t/s.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .datos import Piquera

G = 9.81  # m/s²


def factor_de_friccion(reynolds: float, rugosidad_relativa: float) -> float:
    """Darcy. Laminar: 64/Re; turbulento: Swamee–Jain (explícita, a ±1 % de Colebrook)."""
    if reynolds <= 0.0:
        return 0.0
    if reynolds < 2300.0:
        return 64.0 / reynolds
    return 0.25 / math.log10(rugosidad_relativa / 3.7 + 5.74 / reynolds ** 0.9) ** 2


@dataclass(frozen=True)
class Hidraulica:
    modo: str = "cd"                    # "cd" o "perdidas"
    referencia: str = "boca"            # "boca" o "salida"
    cd: float = 0.731                   # modo cd
    k_entrada: float = 0.5              # modo perdidas: entrada de arista viva (valor de manual; supuesto)
    rugosidad: float = 1.0              # mm; refractario del canal (supuesto)
    viscosidad: float = 0.006           # Pa·s; acero líquido (valor de bibliografía; supuesto)

    def __post_init__(self):
        if self.modo not in ("cd", "perdidas"):
            raise ValueError(f"modo hidráulico desconocido: {self.modo!r}")
        if self.referencia not in ("boca", "salida"):
            raise ValueError(f"referencia de la carga desconocida: {self.referencia!r}")

    def carga(self, altura_boca: float, angulo: float, piquera: Piquera) -> float:
        """Carga motriz en m de acero. ``altura_boca`` (mm) ya incluye el equivalente de la escoria."""
        if altura_boca <= 0.0:
            return 0.0
        h = altura_boca / 1000.0
        if self.referencia == "salida":
            h += piquera.largo / 1000.0 * math.cos(math.radians(angulo + piquera.inclinacion_canal))
        return max(h, 0.0)

    def velocidad(self, altura_boca: float, angulo: float, piquera: Piquera, diametro: float, densidad: float) -> float:
        """m/s en el canal."""
        H = self.carga(altura_boca, angulo, piquera)
        if H <= 0.0:
            return 0.0
        if self.modo == "cd":
            return self.cd * math.sqrt(2.0 * G * H)
        d, largo = diametro / 1000.0, piquera.largo / 1000.0
        v = math.sqrt(2.0 * G * H / (1.0 + self.k_entrada))
        for _ in range(8):                      # f depende de v por el Reynolds: converge en tres o cuatro vueltas
            f = factor_de_friccion(densidad * 1000.0 * v * d / self.viscosidad, self.rugosidad / diametro)
            v = math.sqrt(2.0 * G * H / (1.0 + self.k_entrada + f * largo / d))
        return v

    def caudal(self, altura_boca: float, angulo: float, piquera: Piquera, diametro: float, densidad: float) -> float:
        """t/s."""
        return densidad * math.pi * (diametro / 1000.0) ** 2 / 4.0 * self.velocidad(altura_boca, angulo, piquera, diametro, densidad)

    def cd_equivalente(self, altura_boca: float, angulo: float, piquera: Piquera, diametro: float, densidad: float) -> float:
        """El Cd referido a la boca que daría el mismo caudal (para comparar con el del proveedor)."""
        if altura_boca <= 0.0:
            return 0.0
        return self.velocidad(altura_boca, angulo, piquera, diametro, densidad) / math.sqrt(2.0 * G * altura_boca / 1000.0)
