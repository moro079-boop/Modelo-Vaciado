"""Lectura de archivos de texto de planta (CSV) que vienen de Excel en español.

Excel de Windows guarda «CSV (delimitado por comas)» en **ANSI (cp1252)**, no en UTF-8: un «sintético» o una
«ñ» rompen la lectura en UTF-8. Se prueba UTF-8 (con o sin marca BOM) y, si no es válido, cp1252. No se
adivina nada más: un archivo que no sea ninguno de los dos da un error claro.
"""

from __future__ import annotations

import sys
from pathlib import Path


def leer_texto(ruta: Path | str) -> str:
    datos = Path(ruta).read_bytes()
    try:
        return datos.decode("utf-8-sig")
    except UnicodeDecodeError:
        pass
    try:
        return datos.decode("cp1252")
    except UnicodeDecodeError:
        raise ValueError(f"No se pudo leer «{Path(ruta).name}» como texto (ni UTF-8 ni ANSI de Windows). "
                         "Guárdalo como CSV desde Excel.") from None


def consola_utf8() -> None:
    """La consola de Windows usa cp1252 y no sabe escribir «−» ni «≥»: los mensajes del programa lo llevan. Se pasa
    la salida a UTF-8 y, si la consola aun así no puede, se sustituye el carácter en vez de abortar. Sin consola
    (ejecutable de ventana) ``sys.stdout`` es ``None`` y no hay nada que hacer."""
    for flujo in (sys.stdout, sys.stderr):
        if flujo is not None and hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")
