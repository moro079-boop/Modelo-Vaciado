"""Datos de vaciado de una planta: ``datos/vaciado/<planta>.json`` (formato ``lwd_eaf.vaciado.planta/1``)."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from pathlib import Path

from .rutas import raiz  # noqa: E402

CARPETA = raiz() / "datos" / "vaciado"
FORMATO = "lwd_eaf.vaciado.planta/1"


@dataclass(frozen=True)
class Piquera:
    """La piquera en el marco del horno (mm). El canal es recto, de ``y_boca`` a ``y_salida`` sobre X = ``x``, con la inclinación
    ``inclinacion_canal`` respecto de la vertical del horno (0 en un EBT; un OBT la trae distinta de cero)."""

    tipo: str               # "EBT" u "OBT"
    x: float                # X del eje del canal en la boca
    y_boca: float           # cota de la boca (la entrada): la referencia de los niveles
    y_salida: float         # cota de la salida del canal
    diametro: float         # diámetro interior del canal nuevo
    inclinacion_canal: float = 0.0   # grados; + si la salida queda hacia la piquera (−X) respecto de la boca

    @property
    def largo(self) -> float:
        """Largo del canal en mm, de la boca a la salida."""
        import math

        return (self.y_boca - self.y_salida) / math.cos(math.radians(self.inclinacion_canal))

    def acortada(self, mm: float) -> "Piquera":
        """La piquera con la boca ``mm`` más abajo (el bloque se gasta o se corta con el fondo)."""
        return replace(self, y_boca=self.y_boca - mm) if mm else self


@dataclass(frozen=True)
class DatosVaciado:
    planta: str
    piquera: Piquera
    panel: tuple[float, float] | None       # punto (X, Y) del que se mide la distancia del baño al panel refrigerado
    distancia_panel: float                  # mm que el baño debe dejar al panel (carga segura)
    factor_altura_minima: float             # altura mínima de acero sobre la boca, en diámetros (arrastre de escoria)
    cd: float                               # coeficiente de descarga por omisión (referido a la boca)
    velocidad_basculado: float              # grados por segundo
    angulo_maximo: float                    # grados
    crudo: dict                             # el archivo completo, con los estados de cada dato

    def estado(self, clave: str) -> str:
        return str(self.crudo.get(clave, {}).get("estado", "sin estado"))


def ruta(planta: str) -> Path:
    return CARPETA / f"{planta}.json"


def plantas_con_datos() -> list[str]:
    return sorted(p.stem for p in CARPETA.glob("*.json"))


def cargar(planta: str) -> DatosVaciado:
    r = ruta(planta)
    if not r.exists():
        raise FileNotFoundError(f"la planta «{planta}» no tiene datos de vaciado ({r.name}); las que sí: {', '.join(plantas_con_datos())}")
    with open(r, encoding="utf-8") as f:
        d = json.load(f)
    if d.get("formato") != FORMATO:
        raise ValueError(f"{r.name}: formato {d.get('formato')!r}, se esperaba {FORMATO!r}")
    v = lambda clave: d[clave]["valor"]  # noqa: E731
    p = d["piquera"]
    piquera = Piquera(p["tipo"]["valor"], float(p["x"]["valor"]), float(p["y_boca"]["valor"]), float(p["y_salida"]["valor"]),
                      float(p["diametro"]["valor"]), float(p.get("inclinacion_canal", {}).get("valor", 0.0)))
    panel = d.get("panel")
    return DatosVaciado(d["planta"], piquera, (float(panel["x"]), float(panel["y"])) if panel else None,
                        float(v("distancia_panel")), float(v("factor_altura_minima")), float(v("coeficiente_de_descarga")),
                        float(v("velocidad_basculado")), float(v("angulo_maximo")), d)
