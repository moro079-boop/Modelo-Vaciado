"""Escritura segura de las cachés por planta, que comparten el hilo de la campaña y el de la ventana.

Cada caché es un diccionario del módulo que guarda lo calculado para una planta (``id(planta)``) con un tope de entradas.
La lectura (``dict.get``) es atómica; lo que no lo es es insertar y expulsar la más antigua mientras otro hilo hace lo mismo
(``next(iter(d))`` sobre un diccionario que cambia da ``RuntimeError``). Aquí se hace todo bajo un cerrojo
(auditoría de la interfaz, «posible carrera», EAF-019).
"""

from __future__ import annotations

import threading

CERROJO = threading.RLock()


def guardar(cache: dict, clave, valor, maximo: int) -> None:
    """Inserta y deja a lo más ``maximo`` entradas, expulsando las más antiguas."""
    with CERROJO:
        cache[clave] = valor
        while len(cache) > maximo:
            cache.pop(next(iter(cache)), None)
