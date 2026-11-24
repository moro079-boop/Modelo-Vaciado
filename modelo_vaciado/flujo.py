"""Cálculo directo del tiempo de vaciado de un recipiente por un orificio, con los datos que da el usuario.

Es el núcleo común a los dos escenarios del programa (horno → olla y olla → distribuidor). No conoce la planta: recibe un
recipiente (cómo sube el nivel con la masa), un área de paso, un modelo de pérdidas y una condición aguas abajo, e integra en
el tiempo el balance de masa

    dM/dt = −Q,    Q = ρ · f_A · a · v(H),    H = h(M) + caída − contrapresión

con h(M) la altura del acero sobre el orificio, la caída el tramo vertical que el chorro recorre lleno por debajo del orificio
(canal de la piquera o tubo largo) y la contrapresión lo que el nivel del recipiente de destino queda sobre la salida.

La velocidad sale de la ecuación de energía entre la superficie libre y la salida (Bernoulli):

- ``cd``        v = C_d · √(2·g·H): un coeficiente agrupa todas las pérdidas (Torricelli con coeficiente de descarga).
- ``perdidas``  v = √(2·g·H / (1 + K + f·L/D)): pérdida de entrada K y fricción de Darcy f (Swamee–Jain) en un canal de largo L.

Con un recipiente prismático, el modelo ``cd`` y una contrapresión constante, la integral tiene solución cerrada (``torricelli``),
que sirve de comprobación del integrador. Unidades: mm, m², t, t/m³, s.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .hidraulica import G, factor_de_friccion

# ---------------------------------------------------------------------------
# Área de paso
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AreaDePaso:
    """Orificio circular equivalente. Se define por el diámetro o por el área (``de_area``)."""

    diametro: float          # mm

    @classmethod
    def de_area(cls, area_mm2: float) -> "AreaDePaso":
        if area_mm2 <= 0:
            raise ValueError("El área de paso debe ser mayor que cero.")
        return cls(math.sqrt(4.0 * area_mm2 / math.pi))

    @property
    def area_mm2(self) -> float:
        return math.pi * self.diametro ** 2 / 4.0

    @property
    def area_m2(self) -> float:
        return self.area_mm2 * 1e-6


# ---------------------------------------------------------------------------
# Pérdidas
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Perdidas:
    modo: str = "cd"                 # "cd" o "perdidas"
    cd: float = 0.75                 # modo cd
    k_entrada: float = 0.5           # modo perdidas: entrada de arista viva (valor de manual; supuesto)
    largo: float = 0.0               # mm del canal o tubo (modo perdidas)
    rugosidad: float = 1.0           # mm (supuesto)
    viscosidad: float = 0.006        # Pa·s del acero líquido (bibliografía; supuesto)

    def __post_init__(self):
        if self.modo not in ("cd", "perdidas"):
            raise ValueError(f"modelo de pérdidas desconocido: {self.modo!r}")
        if self.modo == "cd" and not 0.0 < self.cd <= 1.5:
            raise ValueError("El coeficiente de descarga debe estar entre 0 y 1.5.")

    def velocidad(self, carga_mm: float, diametro: float, densidad: float) -> float:
        """m/s en el orificio para una carga en mm de acero."""
        if carga_mm <= 0.0:
            return 0.0
        H = carga_mm / 1000.0
        if self.modo == "cd":
            return self.cd * math.sqrt(2.0 * G * H)
        d, L = diametro / 1000.0, self.largo / 1000.0
        v = math.sqrt(2.0 * G * H / (1.0 + self.k_entrada))
        for _ in range(8):                  # f depende de v por el número de Reynolds
            f = factor_de_friccion(densidad * 1000.0 * v * d / self.viscosidad, self.rugosidad / diametro)
            v = math.sqrt(2.0 * G * H / (1.0 + self.k_entrada + f * L / d))
        return v

    def cd_equivalente(self, carga_mm: float, diametro: float, densidad: float) -> float:
        """El C_d que daría el mismo caudal con la misma carga."""
        if carga_mm <= 0.0:
            return 0.0
        return self.velocidad(carga_mm, diametro, densidad) / math.sqrt(2.0 * G * carga_mm / 1000.0)


# ---------------------------------------------------------------------------
# Recipientes: altura del acero sobre el orificio en función de la masa drenable
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RecipientePrismatico:
    """Área de la superficie libre constante. Se dimensiona con el tonelaje y la altura metalostática (``de_tonelaje``)."""

    area: float              # m²
    densidad: float          # t/m³
    forma: str = "prismatica"

    @classmethod
    def de_tonelaje(cls, masa_t: float, altura_mm: float, densidad: float) -> "RecipientePrismatico":
        if masa_t <= 0 or altura_mm <= 0:
            raise ValueError("El tonelaje sobre el orificio y la altura metalostática deben ser mayores que cero.")
        return cls(masa_t / (densidad * altura_mm / 1000.0), densidad)

    def altura(self, masa_t: float) -> float:
        return max(masa_t, 0.0) / (self.densidad * self.area) * 1000.0

    def area_superficie(self, masa_t: float) -> float:
        return self.area


@dataclass(frozen=True)
class RecipienteTroncoconico:
    """Tronco de cono con el orificio en el fondo: diámetro ``d_fondo`` en el orificio y ``d_ref`` a la altura ``h_ref``.

    ``de_tonelaje`` lo dimensiona con el tonelaje, la altura metalostática y la relación ``d_fondo / d_superficie`` (1 =
    cilindro; < 1, se ensancha hacia arriba, como una olla o el baño de un horno)."""

    d_fondo: float           # mm
    d_ref: float             # mm
    h_ref: float             # mm
    densidad: float          # t/m³
    forma: str = "troncoconica"

    @classmethod
    def de_tonelaje(cls, masa_t: float, altura_mm: float, relacion: float, densidad: float) -> "RecipienteTroncoconico":
        if masa_t <= 0 or altura_mm <= 0:
            raise ValueError("El tonelaje sobre el orificio y la altura metalostática deben ser mayores que cero.")
        if not 0.05 <= relacion <= 20.0:
            raise ValueError("La relación de diámetros fondo / superficie debe estar entre 0.05 y 20.")
        v = masa_t / densidad * 1e9                                         # mm³
        d_sup = math.sqrt(12.0 * v / (math.pi * altura_mm * (relacion ** 2 + relacion + 1.0)))
        return cls(relacion * d_sup, d_sup, altura_mm, densidad)

    def _diametro(self, h: float) -> float:
        return max(self.d_fondo + (self.d_ref - self.d_fondo) * h / self.h_ref, 0.0)

    def _volumen(self, h: float) -> float:
        """mm³ hasta la altura h."""
        d0, d1 = self.d_fondo, self._diametro(h)
        return math.pi * h / 12.0 * (d0 * d0 + d0 * d1 + d1 * d1)

    def altura(self, masa_t: float) -> float:
        v = max(masa_t, 0.0) / self.densidad * 1e9
        if v <= 0.0:
            return 0.0
        bajo, alto = 0.0, self.h_ref
        while self._volumen(alto) < v:
            alto *= 2.0
            if alto > 1e7:
                return alto
        for _ in range(60):
            medio = 0.5 * (bajo + alto)
            if self._volumen(medio) < v:
                bajo = medio
            else:
                alto = medio
        return 0.5 * (bajo + alto)

    def area_superficie(self, masa_t: float) -> float:
        return math.pi * (self._diametro(self.altura(masa_t)) / 1000.0) ** 2 / 4.0


@dataclass(frozen=True)
class RecipienteTabulado:
    """Altura (mm) contra masa (t) dada por una tabla; por ejemplo, la olla de una planta con la regla del LWD."""

    masas: np.ndarray        # t, creciente
    alturas: np.ndarray      # mm
    densidad: float
    forma: str = "tabulada"
    descripcion: str = ""

    def altura(self, masa_t: float) -> float:
        return float(np.interp(masa_t, self.masas, self.alturas))

    def area_superficie(self, masa_t: float, dm: float = 0.5) -> float:
        h1, h2 = self.altura(max(masa_t - dm, 0.0)), self.altura(masa_t + dm)
        return (2 * dm if masa_t > dm else masa_t + dm) / self.densidad / max((h2 - h1) / 1000.0, 1e-9)

    @property
    def capacidad(self) -> float:
        return float(self.masas[-1])


# ---------------------------------------------------------------------------
# Condición aguas abajo
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SalidaLibre:
    """El chorro sale a la atmósfera (horno → olla; olla con el tubo sobre el baño del distribuidor)."""

    tipo: str = "libre"

    def inicial(self) -> float:
        return 0.0

    def contrapresion(self, estado: float) -> float:
        return 0.0

    def nivel(self, estado: float) -> float:
        return math.nan


@dataclass(frozen=True)
class NivelConstante:
    """El distribuidor mantiene su nivel (mm sobre su fondo); la salida del tubo, a ``altura_salida`` mm del fondo, queda sumergida
    la diferencia."""

    nivel_mm: float
    altura_salida: float = 0.0
    tipo: str = "nivel_constante"

    def inicial(self) -> float:
        return 0.0

    def contrapresion(self, estado: float) -> float:
        return max(self.nivel_mm - self.altura_salida, 0.0)

    def nivel(self, estado: float) -> float:
        return self.nivel_mm


@dataclass(frozen=True)
class DistribuidorQueSeLlena:
    """El distribuidor recibe el acero y no entrega (llenado antes de abrir las buzas): su nivel sube y empuja contra la olla.

    ``tundish`` es un ``artesa.Tundish``; ``masa_inicial`` las toneladas que ya tiene; ``altura_salida`` la altura de la salida
    del tubo largo sobre el fondo del distribuidor."""

    tundish: object
    masa_inicial: float
    altura_salida: float
    tipo: str = "llenado"

    def inicial(self) -> float:
        return self.masa_inicial

    def nivel(self, estado: float) -> float:
        return self.tundish.nivel(estado)

    def contrapresion(self, estado: float) -> float:
        return max(self.nivel(estado) - self.altura_salida, 0.0)


# ---------------------------------------------------------------------------
# Configuración, integración y solución cerrada
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConfigVaciado:
    recipiente: object                  # RecipientePrismatico, RecipienteTroncoconico o RecipienteTabulado
    paso: AreaDePaso
    perdidas: Perdidas
    acero_inicial: float                # t en el recipiente
    acero_final: float                  # t en el recipiente al terminar
    densidad: float                     # t/m³
    talon: float = 0.0                  # t que quedan por debajo del orificio (no salen)
    caida: float = 0.0                  # mm de tramo vertical lleno bajo el orificio
    fraccion_abierta: float = 1.0       # f_A de la válvula (1 = sin válvula o abierta del todo)
    aguas_abajo: object = field(default_factory=SalidaLibre)

    def __post_init__(self):
        if self.acero_final >= self.acero_inicial:
            raise ValueError("El acero al final debe ser menor que el acero al inicio.")
        if self.acero_final < self.talon - 1e-9:
            raise ValueError("El acero al final no puede ser menor que el talón: ese acero queda bajo el orificio.")
        if not 0.0 < self.fraccion_abierta <= 1.0:
            raise ValueError("La fracción abierta de la válvula debe estar entre 0 y 1.")

    def altura(self, masa: float) -> float:
        """mm de acero sobre el orificio."""
        return self.recipiente.altura(masa - self.talon)

    def carga(self, masa: float, estado: float) -> float:
        """mm de carga motriz: altura sobre el orificio + caída − contrapresión."""
        if masa - self.talon <= 0.0:
            return 0.0
        return max(self.altura(masa) + self.caida - self.aguas_abajo.contrapresion(estado), 0.0)

    def caudal(self, masa: float, estado: float) -> float:
        """t/s."""
        v = self.perdidas.velocidad(self.carga(masa, estado), self.paso.diametro, self.densidad)
        return self.densidad * self.fraccion_abierta * self.paso.area_m2 * v


@dataclass
class ResultadoVaciado:
    t: np.ndarray                # s
    masa: np.ndarray             # t en el recipiente
    altura: np.ndarray           # mm de acero sobre el orificio
    carga: np.ndarray            # mm de carga motriz
    caudal: np.ndarray           # t/s
    nivel_destino: np.ndarray    # mm (nan con salida libre)
    motivo_fin: str
    eventos: list = field(default_factory=list)
    config: ConfigVaciado | None = None
    nombre: str = ""

    @property
    def tiempo(self) -> float:
        return float(self.t[-1])

    @property
    def colado(self) -> float:
        return float(self.masa[0] - self.masa[-1])

    @property
    def caudal_medio(self) -> float:
        return self.colado / self.tiempo if self.tiempo > 0 else 0.0

    @property
    def terminado(self) -> bool:
        return self.motivo_fin.startswith("se alcanzó")

    def instante(self, masa: float) -> float:
        return float(np.interp(-masa, -self.masa, self.t))


def simular(c: ConfigVaciado, dt: float = 0.25, t_max: float = 6 * 3600.0, nombre: str = "",
            nivel_maximo_destino: float | None = None) -> ResultadoVaciado:
    """Integra con el método de Heun (predictor y corrector) a paso fijo; el último paso termina justo en el acero final."""
    t, m, s = 0.0, float(c.acero_inicial), float(c.aguas_abajo.inicial())
    llena = isinstance(c.aguas_abajo, DistribuidorQueSeLlena)
    T, M, Hs, Cs, Q, N, eventos = [], [], [], [], [], [], []
    avisado = False
    motivo = "tiempo máximo"
    while True:
        q1 = c.caudal(m, s)
        T.append(t); M.append(m); Hs.append(c.altura(m)); Cs.append(c.carga(m, s)); Q.append(q1)  # noqa: E702
        N.append(c.aguas_abajo.nivel(s))
        if nivel_maximo_destino is not None and not avisado and N[-1] > nivel_maximo_destino:
            avisado = True
            eventos.append((t, f"el distribuidor pasa de su nivel máximo ({nivel_maximo_destino:.0f} mm) con {m:.1f} t en la olla"))
        if m <= c.acero_final + 1e-9:
            motivo = "se alcanzó el acero objetivo"
            break
        if q1 <= 1e-9:
            if llena and c.aguas_abajo.contrapresion(s) > 0:
                motivo = f"los niveles se igualan: quedan {m:.1f} t que no salen"
            else:
                motivo = f"sin carga sobre el orificio: quedan {m:.1f} t"
            eventos.append((t, motivo))
            break
        if t >= t_max:
            break
        paso = dt
        m2 = max(m - q1 * paso, 0.0)
        q2 = c.caudal(m2, s + q1 * paso if llena else s)
        qm = 0.5 * (q1 + q2)
        if qm > 0.0 and m - qm * paso < c.acero_final:
            paso = (m - c.acero_final) / qm
        m = max(m - qm * paso, c.acero_final) if qm > 0 else m
        if llena:
            s += qm * paso
        t += paso
    return ResultadoVaciado(np.array(T), np.array(M), np.array(Hs), np.array(Cs), np.array(Q), np.array(N), motivo, eventos, c,
                            nombre)


def torricelli(c: ConfigVaciado) -> float | None:
    """Tiempo (s) de la solución cerrada, o None si no aplica (recipiente no prismático, pérdidas explícitas o un destino que se
    llena). t = A_s / (C_d·f_A·a) · √(2/g) · (√H₀ − √H_f), con H en m."""
    if not isinstance(c.recipiente, RecipientePrismatico) or c.perdidas.modo != "cd" \
            or isinstance(c.aguas_abajo, DistribuidorQueSeLlena):
        return None
    h0, hf = c.carga(c.acero_inicial, 0.0) / 1000.0, c.carga(c.acero_final, 0.0) / 1000.0
    if hf <= 0.0 and c.acero_final - c.talon > 1e-9:
        return None                     # la carga se anula antes de llegar al acero final: el vaciado no termina
    k = c.perdidas.cd * c.fraccion_abierta * c.paso.area_m2
    return c.recipiente.area / k * math.sqrt(2.0 / G) * (math.sqrt(h0) - math.sqrt(max(hf, 0.0)))
