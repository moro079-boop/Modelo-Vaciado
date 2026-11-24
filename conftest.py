"""Hace importable la raíz del repositorio durante las pruebas y abre Qt sin pantalla."""

import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

# La ventana es de PySide6: sin pantalla, las pruebas de la ventana corren en cualquier máquina y en paralelo (pytest -n).
# Para verlas en una pantalla real: QT_QPA_PLATFORM= (vacío) o el de la plataforma.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
