"""Escenarios de vaciado guardados en JSON (formato ``lwd_eaf.vaciado/1``) y cómo se corren."""

from __future__ import annotations

import json
import math
from pathlib import Path

from .horno3d import niveles
from .horno3d.desgaste import Desgaste
from .horno3d.planta import cargar_planta
from . import FORMATO_ESCENARIO
from .basculado import AnguloFijo, Escalones, SeguirCargaSegura
from .datos import DatosVaciado, cargar
from .hidraulica import Hidraulica
from .simulacion import Contexto, Resultado, simular
from .tabla import TablaNiveles

_TABLAS: dict = {}
_PLANTAS: dict = {}


def planta_de(nombre: str) -> dict:
    if nombre not in _PLANTAS:
        _PLANTAS[nombre] = cargar_planta(nombre)
    return _PLANTAS[nombre]


def tabla_de(nombre: str, datos: DatosVaciado, pared: float = 0.0, piso: float = 0.0) -> TablaNiveles:
    """La tabla de niveles de la planta con ese desgaste (% de la capa de trabajo, como en el programa). Se guarda en memoria."""
    clave = (nombre, float(pared), float(piso), datos.angulo_maximo)
    if clave not in _TABLAS:
        planta = planta_de(nombre)
        cav = niveles.cavidad_de(planta, Desgaste(pared, piso))
        _TABLAS[clave] = TablaNiveles.de_cavidad(cav, (datos.piquera.x, datos.piquera.y_boca),
                                                 float(planta["densidades"]["acero_liquido"]["valor"]), datos.angulo_maximo)
    return _TABLAS[clave]


def abrir(ruta: Path | str) -> dict:
    with open(ruta, encoding="utf-8") as f:
        e = json.load(f)
    if e.get("formato") != FORMATO_ESCENARIO:
        raise ValueError(f"{Path(ruta).name}: formato {e.get('formato')!r}, se esperaba {FORMATO_ESCENARIO!r}")
    return e


def _politica(b: dict, datos: DatosVaciado):
    tipo = b.get("tipo", "carga_segura")
    if tipo == "escalones":
        return Escalones(tuple((float(a), float(m)) for a, m in b["pasos"]))
    if tipo == "fijo":
        return AnguloFijo(float(b["angulo"]))
    if tipo == "carga_segura":
        return SeguirCargaSegura(float(b.get("angulo_maximo", datos.angulo_maximo)), float(b.get("margen_t", 0.0)),
                                 float(b.get("angulo_arranque", 0.0)))
    raise ValueError(f"tipo de basculado desconocido: {tipo!r}")


def contexto_de(e: dict) -> tuple[Contexto, DatosVaciado]:
    datos = cargar(e["planta"])
    planta = planta_de(e["planta"])
    d = e.get("desgaste", {})
    p = e.get("piquera", {})
    piquera = datos.piquera.acortada(float(p.get("acortamiento", 0.0)))
    tabla = tabla_de(e["planta"], datos, d.get("pared", 0.0), d.get("piso", 0.0)).con_boca((piquera.x, piquera.y_boca))
    diametro = float(p.get("diametro") or datos.piquera.diametro)
    return Contexto(tabla, piquera, tabla.densidad, diametro, datos.panel, datos.distancia_panel,
                    float(e.get("factor_altura_minima", datos.factor_altura_minima)),
                    float(planta["densidades"]["escoria"]["valor"])), datos


def correr(e: dict, dt: float = 0.25) -> Resultado:
    c, datos = contexto_de(e)
    h = dict(e.get("hidraulica", {}))
    h.setdefault("cd", datos.cd)
    b = e.get("basculado", {})
    vel = b.get("velocidad", datos.velocidad_basculado)
    vel = math.inf if vel in ("instantaneo", "instantáneo", None) else float(vel)
    return simular(c, Hidraulica(**h), _politica(b, datos), float(e["acero_inicial_t"]), float(e["acero_final_t"]),
                   float(e.get("escoria_t", 0.0)), vel, dt, nombre=e.get("nombre", ""))
