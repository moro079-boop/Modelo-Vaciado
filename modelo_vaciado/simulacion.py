"""El integrador: dM/dt = −Q(M, θ), con θ(t) dado por la política de basculado.

Método de Heun (predictor–corrector, segundo orden) con paso fijo; el último paso se acorta para terminar justo en el acero
objetivo. El caudal depende de la masa a través del nivel sobre la boca (``TablaNiveles``) y de la hidráulica del canal.

Escoria: una capa de ``escoria_t`` flota sobre el acero. Su espesor sobre la boca sale de la misma cavidad (el volumen de
acero más el de escoria) y suma carga como ρ_escoria/ρ_acero de su espesor. El arrastre se señala cuando el acero sobre la boca
baja de la altura mínima (``factor_altura_minima`` diámetros); el modelo no calcula cuánta escoria pasa.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .datos import Piquera
from .hidraulica import Hidraulica


@dataclass(frozen=True)
class Contexto:
    """Lo que el integrador y las políticas necesitan saber del horno."""

    tabla: object                           # TablaNiveles o NivelAnalitico
    piquera: Piquera
    densidad: float                         # t/m³ del acero
    diametro: float                         # mm; el del canal en esta colada
    panel: tuple[float, float] | None = None
    distancia_panel: float = 300.0
    factor_altura_minima: float = 3.5
    densidad_escoria: float = 3.0

    @property
    def altura_minima(self) -> float:
        return self.factor_altura_minima * self.diametro

    def carga_segura(self, angulo: float) -> float:
        """Toneladas con el baño a ``distancia_panel`` del panel (inf si la planta no trae el punto del panel)."""
        if self.panel is None:
            return math.inf
        return self.tabla.masa_a_distancia(-self.distancia_panel, angulo, self.panel)

    def carga_minima(self, angulo: float) -> float:
        """Toneladas con la altura mínima de acero sobre la boca: por debajo empieza el arrastre de escoria."""
        return self.tabla.masa_a_distancia(self.altura_minima, angulo)

    def no_drenable(self, angulo: float) -> float:
        """Toneladas que quedan por debajo de la boca a ese ángulo."""
        return self.tabla.masa_a_distancia(0.0, angulo)

    def angulo_seguro(self, masa: float, angulo_maximo: float) -> float:
        """El mayor ángulo (hasta ``angulo_maximo``) cuya carga segura admite ``masa``. La carga segura baja al inclinar."""
        if self.carga_segura(angulo_maximo) >= masa:
            return angulo_maximo
        if self.carga_segura(0.0) < masa:
            return 0.0
        bajo, alto = 0.0, angulo_maximo
        for _ in range(30):
            medio = 0.5 * (bajo + alto)
            if self.carga_segura(medio) >= masa:
                bajo = medio
            else:
                alto = medio
        return bajo


@dataclass
class Resultado:
    t: np.ndarray               # s
    masa: np.ndarray            # t de acero en el horno
    angulo: np.ndarray          # grados
    altura: np.ndarray          # mm de acero sobre la boca
    caudal: np.ndarray          # t/s
    motivo_fin: str
    eventos: list = field(default_factory=list)      # (t, texto)
    contexto: Contexto | None = None
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

    def instante(self, masa: float) -> float:
        """Segundo en que el acero en el horno baja a ``masa``."""
        return float(np.interp(-masa, -self.masa, self.t))

    def tramos(self, cortes) -> list[dict]:
        """Resumen entre masas sucesivas (para comparar con una tabla por escalones)."""
        filas = []
        for m0, m1 in zip(cortes[:-1], cortes[1:]):
            t0, t1 = self.instante(m0), self.instante(m1)
            en = (self.t >= t0) & (self.t <= t1)
            filas.append({"de_t": m0, "a_t": m1, "tiempo_s": t1 - t0, "caudal_medio": (m0 - m1) / (t1 - t0) if t1 > t0 else 0.0,
                          "angulo_medio": float(self.angulo[en].mean()) if en.any() else float("nan"),
                          "altura_media": float(self.altura[en].mean()) if en.any() else float("nan")})
        return filas


def simular(contexto: Contexto, hidraulica: Hidraulica, politica, acero_inicial: float, acero_final: float,
            escoria_t: float = 0.0, velocidad_basculado: float = math.inf, dt: float = 0.25, t_max: float = 3600.0,
            nombre: str = "") -> Resultado:
    c, tabla = contexto, contexto.tabla
    equivalente_escoria = escoria_t * c.densidad / c.densidad_escoria       # t de acero con el volumen de la escoria

    def altura_y_caudal(m: float, ang: float) -> tuple[float, float]:
        h = tabla.nivel_boca(m, ang)
        carga = h
        if escoria_t > 0.0 and h > 0.0:
            carga = h + (tabla.nivel_boca(m + equivalente_escoria, ang) - h) * c.densidad_escoria / c.densidad
        return h, hidraulica.caudal(carga, ang, c.piquera, c.diametro, c.densidad)

    t, m, ang = 0.0, float(acero_inicial), float(politica.angulo_inicial)
    T, M, A, H, Q, eventos = [], [], [], [], [], []
    avisado = {"panel": False, "minima": False}
    motivo = "tiempo máximo"

    def anotar():
        h, q = altura_y_caudal(m, ang)
        T.append(t); M.append(m); A.append(ang); H.append(h); Q.append(q)  # noqa: E702
        if not avisado["panel"] and m > c.carga_segura(ang) + 0.5:
            avisado["panel"] = True
            eventos.append((t, f"el baño queda a menos de {c.distancia_panel:g} mm del panel ({m:.0f} t a {ang:.1f}°; carga segura {c.carga_segura(ang):.0f} t)"))
        if not avisado["minima"] and h < c.altura_minima and m > acero_final + 1e-6:
            avisado["minima"] = True
            eventos.append((t, f"el acero sobre la boca baja de {c.altura_minima:.0f} mm con {m:.0f} t en el horno: riesgo de arrastre de escoria"))
        return h, q

    while True:
        h, q1 = anotar()
        if m <= acero_final + 1e-9:
            motivo = "se alcanzó el acero objetivo"
            break
        if t >= t_max:
            break
        objetivo = politica.objetivo(m, ang, c)
        if q1 <= 0.0 and abs(objetivo - ang) < 1e-9:
            motivo = f"el baño no llega a la boca: quedan {m:.1f} t que no salen a {ang:.1f}°"
            break
        paso = dt
        ang2 = objetivo if math.isinf(velocidad_basculado) else ang + max(-velocidad_basculado * paso, min(velocidad_basculado * paso, objetivo - ang))
        _, q2 = altura_y_caudal(max(m - q1 * paso, 0.0), ang2)
        qm = 0.5 * (q1 + q2)
        if qm > 0.0 and m - qm * paso < acero_final:            # el último paso termina justo en el objetivo
            paso = (m - acero_final) / qm
            ang2 = objetivo if math.isinf(velocidad_basculado) else ang + max(-velocidad_basculado * paso, min(velocidad_basculado * paso, objetivo - ang))
        m, ang, t = max(m - qm * paso, acero_final if qm > 0 else m), ang2, t + paso
        nuevo = politica.objetivo(m, ang, c)                    # un salto instantáneo se anota en el mismo instante
        if math.isinf(velocidad_basculado) and abs(nuevo - ang) > 1e-9:
            anotar()
            ang = nuevo
    return Resultado(np.array(T), np.array(M), np.array(A), np.array(H), np.array(Q), motivo, eventos, c, nombre)
