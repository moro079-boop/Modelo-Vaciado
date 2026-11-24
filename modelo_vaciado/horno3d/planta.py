"""Lectura y validación del archivo de planta (formato lwd_eaf.planta/1, JSON)."""

from __future__ import annotations

import json
from pathlib import Path

from ..rutas import carpeta_plantas

FORMATO = "lwd_eaf.planta/1"
CARPETA_PLANTAS = carpeta_plantas()


class PlantaInvalida(ValueError):
    """El archivo de planta no cumple el formato."""


def ruta_planta(nombre: str) -> Path:
    """Ruta del archivo de una planta por su nombre de archivo sin extensión."""
    return CARPETA_PLANTAS / f"{nombre}.json"


def cargar_planta(nombre_o_ruta: str | Path) -> dict:
    """Lee y valida una planta. Acepta el nombre (``"largos_norte"``) o una ruta."""
    ruta = Path(nombre_o_ruta)
    if ruta.suffix != ".json":
        ruta = ruta_planta(str(nombre_o_ruta))
    with open(ruta, encoding="utf-8") as archivo:
        planta = json.load(archivo)
    problemas = validar_planta(planta)
    if problemas:
        raise PlantaInvalida(f"{ruta}:\n  " + "\n  ".join(problemas))
    return planta


def es_completa(planta: dict) -> bool:
    """La planta trae todo lo que necesitan la ventana, el desgaste y el motor por colada.

    Las de ``"alcance": "niveles"`` (Danieli, Puebla y Fuchs, EAF-023) solo traen la cavidad para los libros
    volumen–altura (``lwd_eaf.cavidad_general``): en la ventana se abren en «modo niveles» (sin desgaste ni campaña).
    """
    return planta.get("alcance", "completo") == "completo"


def plantas_abribles(carpeta: Path | None = None) -> dict[str, str]:
    """Nombre de archivo (sin extensión) → nombre de la planta, de todas las que abre la ventana (completas y de niveles)."""
    plantas = {}
    for archivo in sorted((carpeta or CARPETA_PLANTAS).glob("*.json")):
        try:
            plantas[archivo.stem] = cargar_planta(archivo)["planta"]
        except Exception:                                        # noqa: BLE001
            continue
    return plantas


def plantas_completas(carpeta: Path | None = None) -> dict[str, str]:
    """Nombre de archivo (sin extensión) → nombre de la planta, de las que se pueden abrir en la ventana."""
    plantas = {}
    for archivo in sorted((carpeta or CARPETA_PLANTAS).glob("*.json")):
        try:
            planta = cargar_planta(archivo)
        except Exception:                                        # noqa: BLE001
            continue
        if es_completa(planta):
            plantas[archivo.stem] = planta["planta"]
    return plantas


def validar_planta(planta: dict) -> list[str]:
    """Lista de problemas del archivo; vacía si es válido.

    Reglas:
    - ``formato`` es el esperado.
    - Todo número vive en un objeto con ``estado``, propio o de un objeto que lo contiene.
    - Todo ``estado`` es uno de los declarados en ``estados``.
    """
    problemas: list[str] = []
    if planta.get("formato") != FORMATO:
        problemas.append(f"formato {planta.get('formato')!r}; se esperaba {FORMATO!r}")
    estados = set(planta.get("estados", {}))
    if not estados:
        problemas.append("falta la tabla 'estados'")

    def recorrer(nodo, ruta: str, con_estado: bool) -> None:
        if isinstance(nodo, dict):
            if "estado" in nodo:
                if nodo["estado"] not in estados:
                    problemas.append(f"{ruta}: estado desconocido {nodo['estado']!r}")
                con_estado = True
            for clave, valor in nodo.items():
                if clave != "estados":
                    recorrer(valor, f"{ruta}.{clave}", con_estado)
        elif isinstance(nodo, list):
            for i, valor in enumerate(nodo):
                recorrer(valor, f"{ruta}[{i}]", con_estado)
        elif isinstance(nodo, (int, float)) and not isinstance(nodo, bool):
            if not con_estado:
                problemas.append(f"{ruta}: número sin estado")

    recorrer(planta, "planta", False)
    problemas.extend(_supuestos_del_motor(planta))
    return problemas


def _supuestos_del_motor(planta: dict) -> list[str]:
    """El motor de desgaste supone 21 hiladas de 100 mm desde Y = 750 mm (``desgaste.N_HILADAS`` y compañía). Una planta con otra
    pared tiene que decirlo aquí, con un mensaje, y no calcular en silencio con la de Largos Norte."""
    from .desgaste import ALTURA_HILADA, N_HILADAS, Y_BASE_HILADA_1

    problemas: list[str] = []
    pared = planta.get("pared")
    if not isinstance(pared, dict):
        return problemas
    try:
        if float(pared["y_base_hilada_1"]["valor"]) != Y_BASE_HILADA_1:
            problemas.append(f"pared.y_base_hilada_1 = {pared['y_base_hilada_1']['valor']}; el motor supone {Y_BASE_HILADA_1:g} mm")
        if float(pared["altura_de_hilada"]["valor"]) != ALTURA_HILADA:
            problemas.append(f"pared.altura_de_hilada = {pared['altura_de_hilada']['valor']}; el motor supone {ALTURA_HILADA:g} mm")
        ultima = max(t["hiladas"][1] for lado in pared["lados"].values() for t in lado["tramos"])
        if ultima != N_HILADAS:
            problemas.append(f"las hiladas llegan a la {ultima}; el motor supone {N_HILADAS}")
    except (KeyError, TypeError, ValueError) as error:
        problemas.append(f"pared: no se pudo comprobar lo que supone el motor ({type(error).__name__}: {error})")
    return problemas
