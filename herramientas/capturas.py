"""Capturas de la ventana sin pantalla: ``python -m herramientas.capturas``.

Escribe en ``docs/figuras/ventana/`` una captura de cada escenario a 1 440 × 880 (el tamaño con que abre la ventana) y a
1 280 × 720 (la pantalla más pequeña que se considera), y una de la vista del horno con la cavidad 3D.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_SCALE_FACTOR", "1")

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
CARPETA = RAIZ / "docs" / "figuras" / "ventana"


def main() -> int:
    import warnings

    from modelo_vaciado.ventana import Ventana, aplicacion_qt, preparar

    warnings.filterwarnings("ignore")
    qapp = aplicacion_qt()
    CARPETA.mkdir(parents=True, exist_ok=True)
    hoja = preparar(qapp)
    v = Ventana()
    v.setStyleSheet(hoja)
    v.show()

    def foto(nombre: str):
        for _ in range(5):
            qapp.processEvents()
        ruta = CARPETA / f"{nombre}.png"
        v.grab().save(str(ruta))
        print(ruta.relative_to(RAIZ))

    for ancho, alto in ((1440, 880), (1280, 720)):
        v.resize(ancho, alto)
        for i, sufijo in enumerate(("horno", "olla")):
            v._elegir(i)
            foto(f"{sufijo}_{ancho}x{alto}")
    v.resize(1440, 880)
    v._elegir(0)
    v.horno.elegir(1)
    foto("horno_cavidad_3d_1440x880")
    v.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
