"""Políticas de basculado: a qué ángulo quiere estar el horno en cada instante de la colada.

Cada política da un ángulo objetivo; el integrador lo sigue con la velocidad de basculado (infinita = salto instantáneo).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AnguloFijo:
    angulo: float

    def objetivo(self, masa: float, angulo: float, contexto) -> float:
        return self.angulo

    @property
    def angulo_inicial(self) -> float:
        return self.angulo


@dataclass(frozen=True)
class Escalones:
    """Como el estudio de Magnesita: el horno se queda en un ángulo hasta que el acero baja a ``hasta_t`` y pasa al siguiente.
    ``pasos`` = ((ángulo, hasta_t), ...), con hasta_t decreciente."""

    pasos: tuple[tuple[float, float], ...]

    def objetivo(self, masa: float, angulo: float, contexto) -> float:
        for a, hasta in self.pasos:
            if masa > hasta + 1e-9:
                return a
        return self.pasos[-1][0]

    @property
    def angulo_inicial(self) -> float:
        return self.pasos[0][0]


@dataclass(frozen=True)
class SeguirCargaSegura:
    """Inclina todo lo que el panel permite: el mayor ángulo con el que el baño deja ``distancia`` mm al panel refrigerado, más
    un ``margen_t`` de toneladas. Más inclinación = más acero sobre la piquera = más caudal y menos riesgo de arrastre."""

    angulo_maximo: float = 15.0
    margen_t: float = 0.0
    angulo_arranque: float = 0.0

    def objetivo(self, masa: float, angulo: float, contexto) -> float:
        return contexto.angulo_seguro(masa + self.margen_t, self.angulo_maximo)

    @property
    def angulo_inicial(self) -> float:
        return self.angulo_arranque
