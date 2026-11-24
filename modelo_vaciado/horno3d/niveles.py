"""Niveles del baño: volumen bajo un plano inclinado, búsqueda inversa y sucesos.

Convenciones (AGENTS.md): inclinación positiva hacia la piquera (la nariz baja). En el
marco del horno la superficie libre es el plano Y = y_eje − tan(θ)·X, donde y_eje es su
cota sobre el eje del horno; h = y_eje − 679 es la profundidad en el eje. El pivote de
basculeo no cambia el volumen.

Sucesos:
- derrame: la superficie pasa por encima de la arista del umbral (X = 2 772, Y = 1 850).
- fin del refractario: la superficie alcanza el tope del ladrillo en algún punto del
  contorno (Y = 2 250 en el cuerpo, 2 850 en la nariz y los arcos de unión). Por encima el
  volumen sigue con los paneles a paño de la coraza (supuesto, pared.por_encima).
"""

from __future__ import annotations

import math
from collections import OrderedDict

from .cache import CERROJO
from dataclasses import dataclass

import numpy as np

from .cavidad import Cavidad, construir_cavidad
from .cavidad_general import construir_cavidad_general
from .planta import es_completa

Y_FONDO = 679.0  # punto más bajo del fondo (cota del plano); h = y_eje − 679


def _superficie(cav: Cavidad, y_eje: float, inclinacion: float) -> np.ndarray:
    """Cota de la superficie en cada columna; en las del canal (EAF-051), sin pasar del plano paralelo por su borde de rebose."""
    tg = math.tan(math.radians(inclinacion))
    y_sup = y_eje - tg * cav.x
    if cav.rebose is not None and cav.columnas_rebose is not None:
        x_r, y_r = cav.rebose
        y_sup = np.where(cav.columnas_rebose, np.minimum(y_sup, y_r - tg * (cav.x - x_r)), y_sup)
    return y_sup


def volumen(cav: Cavidad, y_eje: float, inclinacion: float) -> float:
    """Volumen en m³ bajo la superficie libre, para la inclinación dada en grados.

    Por columna de X: capas completas por debajo de la superficie (suma acumulada) más la
    fracción de la capa que la superficie corta. Es lo mismo que sumar todas las capas con
    su fracción mojada (``volumen_directo``), con un acceso por columna.
    """
    y_sup = _superficie(cav, y_eje, inclinacion)  # (nx,)
    t = (y_sup - cav.y_inferior[0]) / cav.paso  # altura de la superficie en capas
    n = cav.area.shape[0]
    k = np.clip(np.floor(t), 0, n).astype(np.intp)
    frac = np.clip(t - k, 0.0, 1.0)
    cols = np.arange(k.size)
    por_columna = cav.acumulado[k, cols] + cav.area_con_cero[k, cols] * frac
    return float(por_columna.sum() * cav.paso * 1e-9)


def volumen_directo(cav: Cavidad, y_eje: float, inclinacion: float) -> float:
    """Referencia lenta: suma todas las capas con su fracción mojada. Solo para verificar."""
    y_sup = _superficie(cav, y_eje, inclinacion)
    fraccion = np.clip((y_sup[None, :] - cav.y_inferior[:, None]) / cav.paso, 0.0, 1.0)
    return float((cav.area * fraccion).sum() * cav.paso * 1e-9)


def y_eje_para_volumen(cav: Cavidad, volumen_m3: float, inclinacion: float, tolerancia: float = 0.01) -> float:
    """Cota de la superficie en el eje que contiene ``volumen_m3`` (bisección, ±0.01 mm)."""
    # Límites: con «bajo» el plano queda por debajo de toda la malla; con «alto», por encima de toda ella (a cualquier
    # inclinación). Antes «alto» era y_superior − margen y dejaba fuera la parte alta de la malla: a 15° solo veía 49 m³
    # de 82 y lanzaba «no caben» aunque cupieran (auditoría EAF-018, hallazgo 9; corregido en EAF-024).
    margen = abs(math.tan(math.radians(inclinacion))) * float(np.abs(cav.x).max())
    bajo = float(cav.y_inferior[0]) - margen - 1.0
    alto = cav.y_superior + margen
    if volumen(cav, alto, inclinacion) < volumen_m3:
        raise ValueError(f"{volumen_m3:.3f} m³ no caben en la malla a {inclinacion}°")
    while alto - bajo > tolerancia:
        medio = (bajo + alto) / 2
        if volumen(cav, medio, inclinacion) < volumen_m3:
            bajo = medio
        else:
            alto = medio
    return (bajo + alto) / 2


@dataclass(frozen=True)
class Sucesos:
    derrama: bool
    margen_umbral: float  # mm, positivo = por debajo de la arista del umbral
    sobre_refractario: bool
    margen_refractario: float  # mm, positivo = por debajo del tope del ladrillo


def y_eje_umbral(cav: Cavidad, inclinacion: float) -> float:
    """y_eje del plano que pasa por la arista del umbral."""
    return cav.y_umbral + math.tan(math.radians(inclinacion)) * cav.x_umbral


def y_eje_fin_refractario(cav: Cavidad, inclinacion: float) -> float:
    """y_eje del plano que toca primero el tope del ladrillo en algún punto del contorno."""
    m = ~np.isnan(cav.y_fin_refractario)
    return float(np.min(cav.y_fin_refractario[m] + math.tan(math.radians(inclinacion)) * cav.x_cara_contorno[m]))


def sucesos(cav: Cavidad, y_eje: float, inclinacion: float) -> Sucesos:
    m_u = y_eje_umbral(cav, inclinacion) - y_eje
    m_r = y_eje_fin_refractario(cav, inclinacion) - y_eje
    return Sucesos(m_u < 0, m_u, m_r < 0, m_r)


@dataclass(frozen=True)
class Nivel:
    inclinacion: float
    toneladas: float
    densidad: float
    volumen: float  # m³
    y_eje: float  # mm
    sucesos: Sucesos
    y_fondo: float = Y_FONDO  # piso de la cavidad (Norte: 679; las plantas de solo niveles traen el suyo)

    @property
    def h(self) -> float:
        return self.y_eje - self.y_fondo


def nivel(cav: Cavidad, toneladas: float, densidad: float, inclinacion: float) -> Nivel:
    v = toneladas / densidad
    y = y_eje_para_volumen(cav, v, inclinacion)
    return Nivel(inclinacion, toneladas, densidad, v, y, sucesos(cav, y, inclinacion), cav.y_fondo)


@dataclass(frozen=True)
class Capacidad:
    inclinacion: float
    volumen_umbral: float  # m³ hasta la arista del umbral
    volumen_refractario: float  # m³ hasta el tope del ladrillo
    y_eje_umbral: float
    y_eje_refractario: float

    @property
    def volumen_seguro(self) -> float:
        return min(self.volumen_umbral, self.volumen_refractario)

    @property
    def limita(self) -> str:
        return "umbral" if self.volumen_umbral <= self.volumen_refractario else "fin del refractario"


def capacidad(cav: Cavidad, inclinacion: float) -> Capacidad:
    yu = y_eje_umbral(cav, inclinacion)
    yr = y_eje_fin_refractario(cav, inclinacion)
    return Capacidad(inclinacion, volumen(cav, yu, inclinacion), volumen(cav, yr, inclinacion), yu, yr)


_CACHE: "OrderedDict[tuple, tuple[dict, Cavidad]]" = OrderedDict()
_CACHE_MAX = 14  # cada cavidad pesa unos 4 MB; las seis plantas nuevas (precalentado, EAF-053) y los estados de desgaste


def cavidad_de(planta: dict, desgaste=None) -> Cavidad:
    """Cavidad construida una vez por planta y estado de desgaste (cada una tarda ~0.5 s).

    Se conservan las ``_CACHE_MAX`` más recientes. La entrada guarda la propia planta y se
    comprueba su identidad: un ``id()`` puede reutilizarse cuando se recarga la planta.
    """
    from .desgaste import NUEVO

    desgaste = desgaste or NUEVO
    clave = (id(planta), desgaste)
    with CERROJO:
        entrada = _CACHE.get(clave)
        if entrada is not None and entrada[0] is planta:
            _CACHE.move_to_end(clave)
            return entrada[1]
    cav = construir_cavidad(planta, desgaste=desgaste) if es_completa(planta) else construir_cavidad_general(planta, desgaste=desgaste)
    with CERROJO:
        _CACHE[clave] = (planta, cav)
        while len(_CACHE) > _CACHE_MAX:
            _CACHE.popitem(last=False)
    return cav


def tabla_capacidad(cav: Cavidad, angulos, densidad: float, cargas=(109.0, 117.0)) -> list[dict]:
    """Una fila por ángulo: capacidad al umbral y al fin del refractario, y nivel de cada carga."""
    filas = []
    for th in angulos:
        c = capacidad(cav, th)
        fila = {
            "inclinacion": th,
            "h_umbral": c.y_eje_umbral - cav.y_fondo, "t_umbral": c.volumen_umbral * densidad,
            "h_refractario": c.y_eje_refractario - cav.y_fondo, "t_refractario": c.volumen_refractario * densidad,
            "t_segura": c.volumen_seguro * densidad, "limita": c.limita,
        }
        for carga in cargas:
            n = nivel(cav, carga, densidad, th)
            fila[f"h_{carga:g}"] = n.h
            fila[f"margen_umbral_{carga:g}"] = n.sucesos.margen_umbral
            fila[f"derrama_{carga:g}"] = n.sucesos.derrama
            fila[f"sobre_refractario_{carga:g}"] = n.sucesos.sobre_refractario
        filas.append(fila)
    return filas


def curva_volumen(cav: Cavidad, angulos, alturas) -> np.ndarray:
    """Volumen (m³) para cada altura h en el eje (filas) y cada ángulo (columnas)."""
    return np.array([[volumen(cav, cav.y_fondo + h, th) for th in angulos] for h in alturas])


# ---------------------------------------------------------------------------
# Escoria (regla tomada del LWD; factor de espumado propio)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ParametrosBano:
    densidad_acero: float  # t/m³ (supuesto del archivo de planta)
    densidad_escoria: float  # t/m³ (tomada del LWD)
    factor_espumado: float  # sobre el volumen de escoria (supuesto)


def parametros_bano(planta: dict) -> ParametrosBano:
    d = planta["densidades"]
    return ParametrosBano(float(d["acero_liquido"]["valor"]), float(d["escoria"]["valor"]),
                          float(d["factor_de_espumado"]["valor"]))


@dataclass(frozen=True)
class NivelBano:
    acero: Nivel
    escoria_t: float
    volumen_escoria: float  # m³, ya multiplicado por el factor de espumado
    y_eje_escoria: float  # mm, superficie de la escoria en el eje
    sucesos_escoria: Sucesos
    parametros: ParametrosBano

    @property
    def h_escoria(self) -> float:
        return self.y_eje_escoria - self.acero.y_fondo

    @property
    def espesor_escoria(self) -> float:
        """Espesor de la capa de escoria medido en el eje (mm)."""
        return self.y_eje_escoria - self.acero.y_eje


def nivel_con_escoria(cav: Cavidad, acero_t: float, escoria_t: float, inclinacion: float,
                      parametros: ParametrosBano) -> NivelBano:
    """Línea de acero y línea de escoria (el plano que contiene acero + escoria × factor)."""
    acero = nivel(cav, acero_t, parametros.densidad_acero, inclinacion)
    v_esc = escoria_t / parametros.densidad_escoria * parametros.factor_espumado
    if v_esc > 0:
        y_esc = y_eje_para_volumen(cav, acero.volumen + v_esc, inclinacion)
    else:
        y_esc = acero.y_eje
    return NivelBano(acero, escoria_t, v_esc, y_esc, sucesos(cav, y_esc, inclinacion), parametros)


# ---------------------------------------------------------------------------
# Desgaste manual (fase 3)
# ---------------------------------------------------------------------------

def tabla_desgaste(planta: dict, porcentajes=(0, 25, 50, 75, 100), angulos=(-3.0, 0.0, 3.0),
                   densidad: float = 7.0, carga: float = 109.0) -> list[dict]:
    """Capacidad y nivel de ``carga`` para cada combinación de % de pared y % de piso."""
    from .desgaste import Desgaste

    filas = []
    for pared in porcentajes:
        for piso in porcentajes:
            cav = cavidad_de(planta, Desgaste(pared, piso))
            fila = {"pared": pared, "piso": piso}
            for th in angulos:
                c = capacidad(cav, th)
                n = nivel(cav, carga, densidad, th)
                fila[f"t_segura_{th:+g}"] = c.volumen_seguro * densidad
                fila[f"limita_{th:+g}"] = c.limita
                fila[f"h_{th:+g}"] = n.h
                fila[f"margen_{th:+g}"] = n.sucesos.margen_umbral
                fila[f"derrama_{th:+g}"] = n.sucesos.derrama
            filas.append(fila)
    return filas
