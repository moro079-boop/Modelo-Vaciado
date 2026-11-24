"""Piezas de interfaz comunes a las páginas de Vaciado-EAF, sobre los componentes Qt de LWD-EAF."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFormLayout

from .interfaz.widgets import tarjeta


def formulario(capa, titulo: str) -> QFormLayout:
    """Una tarjeta de LWD-EAF con su título y un formulario etiqueta · campo dentro."""
    _, cuerpo = tarjeta(capa, titulo)
    f = QFormLayout()
    f.setContentsMargins(0, 0, 0, 0)
    f.setVerticalSpacing(6)
    f.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    cuerpo.addLayout(f)
    return f
