"""Capturas de la ventana con cada diseño, sin pantalla: ``python -m herramientas.capturas``.

Escribe en ``docs/figuras/disenos/`` una captura por diseño y por escenario (``<diseño>_horno.png`` y ``<diseño>_olla.png``),
con la ventana a 1 480 × 900 y escala de pantalla 1.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_SCALE_FACTOR", "1")

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
CARPETA = RAIZ / "docs" / "figuras" / "disenos"


def main(argv: list[str] | None = None) -> int:
    import warnings

    from modelo_vaciado.interfaz import disenos
    from modelo_vaciado.ventana import Ventana, aplicacion_qt, preparar

    warnings.filterwarnings("ignore")
    nombres = [a for a in (argv if argv is not None else sys.argv[1:])] or list(disenos.DISENOS)
    qapp = aplicacion_qt()
    CARPETA.mkdir(parents=True, exist_ok=True)
    for nombre in nombres:
        hoja = preparar(qapp, nombre)
        v = Ventana(diseno=nombre)
        v.setStyleSheet(hoja)
        v.resize(1480, 900)
        v.show()
        for i, sufijo in enumerate(("horno", "olla")):
            v._elegir(i)
            for _ in range(5):
                qapp.processEvents()
            pagina = v.horno.directo if i == 0 else v.olla
            pagina.lienzo_series.draw()
            qapp.processEvents()
            ruta = CARPETA / f"{nombre}_{sufijo}.png"
            v.grab().save(str(ruta))
            print(ruta.relative_to(RAIZ))
        v.close()
        qapp.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
