"""Formato de números para la ventana y las gráficas (sin Qt, para poder probarlo sin pantalla)."""

from __future__ import annotations

import math


def numero(texto):
    """Texto de un campo a número; None si está vacío o no es un número finito («nan», «inf» y «1e999» no lo son)."""
    texto = (texto or "").strip().replace(",", ".")
    if not texto:
        return None
    try:
        valor = float(texto)
    except ValueError:
        return None
    return valor if math.isfinite(valor) else None


def numero_estricto(texto, nombre: str):
    """Como ``numero``, pero un texto que no está vacío y no es un número finito es un error y no un «vacío»."""
    valor = numero(texto)
    if valor is None and (texto or "").strip():
        raise ValueError(f"«{nombre}»: «{texto.strip()}» no es un número.")
    return valor


def fmt(x, dec=1, vacio="—"):
    """Número con separador de miles fino y decimales fijos."""
    if x is None:
        return vacio
    if isinstance(x, str):
        return x
    return f"{x:,.{dec}f}".replace(",", " ")


def grados(x) -> str:
    """Inclinación con signo (+3°, −3°) y sin signo en el cero (0°)."""
    return "0°" if round(float(x), 6) == 0 else f"{float(x):+g}°"


def fmt_g(x, vacio=""):
    """Formato corto de un valor dentro de un campo editable."""
    if x is None:
        return vacio
    if isinstance(x, str):
        return x
    if x == 0:
        return "0"
    return ("%.6f" % x).rstrip("0").rstrip(".")
