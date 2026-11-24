"""Dónde están los archivos del programa: los datos de planta y los ejemplos.

Con el código fuente, a la altura del repositorio; en el ejecutable que hace ``empaquetado/construir.py``
(PyInstaller), dentro de la carpeta de recursos del ejecutable. Un solo lugar para que ninguno de los dos
casos se escriba a mano en otro sitio.
"""

from __future__ import annotations

import sys
from pathlib import Path


def raiz() -> Path:
    """La carpeta que contiene ``datos/`` y ``ejemplos/``."""
    if getattr(sys, "frozen", False):                      # ejecutable de PyInstaller
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def carpeta_plantas() -> Path:
    return raiz() / "datos" / "plantas"


def carpeta_ejemplos(que: str) -> Path:
    """``escenarios`` o ``campanas``."""
    return raiz() / "ejemplos" / que


def recurso(nombre: str) -> Path:
    """Un archivo de ``modelo_vaciado/interfaz/recursos`` (el icono)."""
    return raiz() / "modelo_vaciado" / "interfaz" / "recursos" / nombre
