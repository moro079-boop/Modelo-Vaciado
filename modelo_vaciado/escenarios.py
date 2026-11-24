"""Los dos escenarios del programa, con las variables que define el usuario, y su archivo (formato ``modelo_vaciado.escenario/1``).

- ``horno_olla``         el horno (EAF) se vacía por la piquera hacia la olla, con el chorro libre.
- ``olla_distribuidor``  la olla se vacía por la válvula deslizante hacia el distribuidor (tundish), que puede estar a nivel
                         constante, llenarse durante el vaciado o no oponer contrapresión.

Cada escenario se arma con:

- **Recipiente:** ``simple`` (tonelaje, altura metalostática sobre el orificio, talón y forma: prismática o troncocónica) o, en
  la olla, ``olla_de_planta`` (la geometría de ``datos/vaciado/colada_continua/<planta>.json``, con la regla del LWD).
- **Área de paso:** diámetro o área del orificio.
- **Hidráulica:** coeficiente de descarga o pérdidas explícitas; caída bajo el orificio (canal o tubo lleno).
- **Válvula** (olla): abertura en % de la carrera.
- **Destino** (olla): libre, nivel constante o distribuidor que se llena.

El horno con su cavidad 3D, el basculado y los límites del panel es el escenario detallado de ``escenario.py`` (formato
``lwd_eaf.vaciado/1``); ``abrir`` reconoce los dos formatos.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

from .artesa import Tundish
from .flujo import (AreaDePaso, ConfigVaciado, DistribuidorQueSeLlena, NivelConstante, Perdidas, RecipientePrismatico,
                    RecipienteTabulado, RecipienteTroncoconico, ResultadoVaciado, SalidaLibre, simular, torricelli)
from .valvula import fraccion_abierta

FORMATO = "modelo_vaciado.escenario/1"
TIPOS = {"horno_olla": "Horno (EAF) → olla", "olla_distribuidor": "Olla → distribuidor"}
DENSIDAD_ACERO = 7.0     # t/m³; valor de bibliografía del acero líquido a temperatura de colada (supuesto)

# Valores con los que abre cada escenario. Cada uno lleva su estado en ``ESTADOS``.
POR_OMISION = {
    "horno_olla": {
        "formato": FORMATO, "tipo": "horno_olla", "nombre": "Horno → olla",
        "recipiente": {"geometria": "simple", "forma": "prismatica", "altura_metalostatica_mm": 969.0, "talon_t": 94.5,
                       "relacion_diametros": 1.0},
        "acero_inicial_t": 450.0, "acero_final_t": 150.0, "densidad": 6.9,
        "paso": {"diametro_mm": 200.0},
        "hidraulica": {"modo": "cd", "cd": 0.731, "caida_mm": 0.0, "largo_mm": 1359.0, "k_entrada": 0.5, "rugosidad_mm": 1.0,
                       "viscosidad": 0.006},
    },
    "olla_distribuidor": {
        "formato": FORMATO, "tipo": "olla_distribuidor", "nombre": "Olla → distribuidor",
        "recipiente": {"geometria": "olla_de_planta", "planta": "pesqueria", "pared_gastada_mm": 0.0, "piso_gastado_mm": 0.0,
                       "forma": "troncoconica", "altura_metalostatica_mm": 3600.0, "talon_t": 0.0, "relacion_diametros": 0.95},
        "acero_inicial_t": 300.0, "acero_final_t": 3.0, "densidad": 6.9,
        "paso": {"diametro_mm": 55.0},
        "hidraulica": {"modo": "cd", "cd": 0.75, "caida_mm": 900.0, "largo_mm": 900.0, "k_entrada": 0.5, "rugosidad_mm": 1.0,
                       "viscosidad": 0.006},
        "valvula": {"abertura_pct": 100.0, "carrera_mm": 0.0},
        "destino": {"tipo": "nivel_constante", "nivel_mm": 1100.0, "altura_salida_mm": 300.0, "masa_inicial_t": 0.0,
                    "largo_mm": 7000.0, "ancho_mm": 1000.0, "talud_grados": 10.0, "nivel_maximo_mm": 1300.0},
    },
}

# Procedencia de los valores por omisión (lo que la ventana y los reportes muestran junto a cada dato).
ESTADOS = {
    "horno_olla": {
        "altura_metalostatica_mm": ("derivado", "nivel sobre la boca de la piquera con 450 t a 0° en la cavidad de Pesquería"),
        "talon_t": ("derivado", "acero bajo la boca de la piquera a 0° en la cavidad de Pesquería"),
        "acero_inicial_t": ("calculo_del_proveedor", "estudio de vaciado de Pesquería (plano AV00025170)"),
        "acero_final_t": ("calculo_del_proveedor", "estudio de vaciado de Pesquería (plano AV00025170)"),
        "densidad": ("cota_del_plano", "ρ = 6,9 t/m³ del plano del horno de Pesquería"),
        "diametro_mm": ("cota_del_plano", "Ø200 del detalle de la piquera (plano AV00025170)"),
        "cd": ("calculo_del_proveedor", "implícito en el estudio de Magnesita; sin validar con tiempos medidos"),
        "largo_mm": ("medido_a_escala", "largo del canal de la piquera de Pesquería"),
        "k_entrada": ("supuesto", "entrada de arista viva, valor de manual"),
        "rugosidad_mm": ("supuesto", "sin dato del refractario del canal"),
        "viscosidad": ("supuesto", "valor de bibliografía del acero líquido"),
    },
    "olla_distribuidor": {
        "planta": ("heredado_sin_verificar", "olla de Pesquería del LWD (plano CS129722)"),
        "acero_inicial_t": ("heredado_sin_verificar", "capacidad nominal de la olla de Pesquería"),
        "acero_final_t": ("supuesto", "remanente al cerrar la olla"),
        "densidad": ("heredado_sin_verificar", "densidad impresa en el plano de la olla"),
        "diametro_mm": ("supuesto", "D0 de las placas LG22L del SGW (otra olla)"),
        "cd": ("supuesto", "C_d del SGW, por calibrar"),
        "caida_mm": ("supuesto", "del piso de la olla a la salida del tubo largo"),
        "destino_nivel_mm": ("ejemplo", "nivel de operación del distribuidor de ejemplo"),
        "destino_altura_salida_mm": ("ejemplo", "salida del tubo largo sobre el fondo del distribuidor"),
        "destino_largo_mm": ("ejemplo", "fondo del distribuidor de ejemplo"),
        "destino_ancho_mm": ("ejemplo", "fondo del distribuidor de ejemplo"),
        "destino_talud_grados": ("ejemplo", "distribuidor de ejemplo"),
        "destino_nivel_maximo_mm": ("ejemplo", "distribuidor de ejemplo"),
        "largo_mm": ("supuesto", "largo del tramo de la válvula al tubo largo (igual a la caída)"),
        "k_entrada": ("supuesto", "entrada de arista viva, valor de manual"),
        "rugosidad_mm": ("supuesto", "sin dato"),
        "viscosidad": ("supuesto", "valor de bibliografía del acero líquido"),
    },
}


def nuevo(tipo: str) -> dict:
    if tipo not in TIPOS:
        raise ValueError(f"escenario desconocido: {tipo!r}; los posibles: {', '.join(TIPOS)}")
    return copy.deepcopy(POR_OMISION[tipo])


def completar(e: dict) -> dict:
    """El escenario con los valores por omisión de su tipo donde no trae nada."""
    base = nuevo(e.get("tipo", "horno_olla"))
    for clave, valor in e.items():
        if isinstance(valor, dict) and isinstance(base.get(clave), dict):
            base[clave].update(valor)
        else:
            base[clave] = valor
    return base


def abrir(ruta: Path | str) -> dict:
    """Lee un escenario de cualquiera de los formatos del programa (el simple o el del horno con cavidad 3D)."""
    e = json.loads(Path(ruta).read_text(encoding="utf-8"))
    formatos = (FORMATO, "lwd_eaf.vaciado/1", "lwd_eaf.vaciado.colada/1")
    if e.get("formato") not in formatos:
        raise ValueError(f"{Path(ruta).name}: formato {e.get('formato')!r}; se esperaba uno de {', '.join(formatos)}")
    return completar(e) if e["formato"] == FORMATO else e


def guardar(e: dict, ruta: Path | str) -> None:
    Path(ruta).write_text(json.dumps(e, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Del escenario a la configuración del cálculo
# ---------------------------------------------------------------------------

def _olla_de_planta(r: dict):
    from . import colada_continua as cc
    from .olla import GeometriaOlla, TablaOlla

    d = cc.cargar_planta(r["planta"])
    g = GeometriaOlla.de_datos(d["olla"])
    tabla = TablaOlla.de_geometria(g, float(r.get("pared_gastada_mm", 0.0)), float(r.get("piso_gastado_mm", 0.0)))
    return RecipienteTabulado(tabla.masa, tabla.alturas, g.densidad, descripcion=d["olla"].get("nombre", r["planta"])), g.densidad


def recipiente_de(e: dict):
    """(recipiente, densidad, talón) del escenario."""
    r = e["recipiente"]
    if r.get("geometria") == "olla_de_planta":
        if e["tipo"] != "olla_distribuidor":
            raise ValueError("La olla de una planta sólo es recipiente en el escenario olla → distribuidor.")
        rec, densidad = _olla_de_planta(r)
        return rec, densidad, 0.0
    densidad = float(e.get("densidad", DENSIDAD_ACERO))
    talon = float(r.get("talon_t", 0.0))
    sobre = float(e["acero_inicial_t"]) - talon
    if sobre <= 0:
        raise ValueError("El acero al inicio debe ser mayor que el talón.")
    h = float(r["altura_metalostatica_mm"])
    if r.get("forma", "prismatica") == "prismatica":
        return RecipientePrismatico.de_tonelaje(sobre, h, densidad), densidad, talon
    return RecipienteTroncoconico.de_tonelaje(sobre, h, float(r.get("relacion_diametros", 1.0)), densidad), densidad, talon


def paso_de(e: dict) -> AreaDePaso:
    p = e["paso"]
    if p.get("area_mm2"):
        return AreaDePaso.de_area(float(p["area_mm2"]))
    if p.get("area_cm2"):
        return AreaDePaso.de_area(float(p["area_cm2"]) * 100.0)
    d = float(p.get("diametro_mm", 0.0))
    if d <= 0:
        raise ValueError("El diámetro del orificio debe ser mayor que cero.")
    return AreaDePaso(d)


def configurar(e: dict) -> ConfigVaciado:
    e = completar(e)
    rec, densidad, talon = recipiente_de(e)
    paso = paso_de(e)
    h = e["hidraulica"]
    perdidas = Perdidas(h.get("modo", "cd"), float(h.get("cd", 0.75)), float(h.get("k_entrada", 0.5)), float(h.get("largo_mm", 0.0)),
                        float(h.get("rugosidad_mm", 1.0)), float(h.get("viscosidad", 0.006)))
    fa, destino = 1.0, SalidaLibre()
    if e["tipo"] == "olla_distribuidor":
        v = e.get("valvula", {})
        fa = fraccion_abierta(float(v.get("abertura_pct", 100.0)), paso.diametro, float(v.get("carrera_mm") or 0.0) or None)
        if fa <= 0:
            raise ValueError("Con esa abertura la válvula queda cerrada.")
        d = e.get("destino", {})
        tipo = d.get("tipo", "libre")
        if tipo == "nivel_constante":
            destino = NivelConstante(float(d["nivel_mm"]), float(d.get("altura_salida_mm", 0.0)))
        elif tipo == "llenado":
            tundish = Tundish(float(d["largo_mm"]), float(d["ancho_mm"]), float(d.get("talud_grados", 0.0)), densidad,
                              float(d.get("nivel_mm", 0.0)), 0.0, float(d.get("nivel_maximo_mm", 1e9)))
            destino = DistribuidorQueSeLlena(tundish, float(d.get("masa_inicial_t", 0.0)), float(d.get("altura_salida_mm", 0.0)))
        elif tipo != "libre":
            raise ValueError(f"destino desconocido: {tipo!r}")
    if isinstance(rec, RecipienteTabulado) and float(e["acero_inicial_t"]) > rec.capacidad + 1e-6:
        raise ValueError(f"La olla no admite {e['acero_inicial_t']:g} t: su capacidad hasta el tope es {rec.capacidad:.0f} t.")
    return ConfigVaciado(rec, paso, perdidas, float(e["acero_inicial_t"]), float(e["acero_final_t"]), densidad, talon,
                         float(h.get("caida_mm", 0.0)), fa, destino)


def correr(e: dict, dt: float | None = None) -> ResultadoVaciado:
    e = completar(e)
    c = configurar(e)
    if dt is None:
        dt = 0.25 if e["tipo"] == "horno_olla" else 1.0
    maximo = e.get("destino", {}).get("nivel_maximo_mm") if e.get("destino", {}).get("tipo") == "llenado" else None
    return simular(c, dt=dt, nombre=e.get("nombre", ""), nivel_maximo_destino=maximo)


def resumen(r: ResultadoVaciado) -> dict:
    """Las cifras del resultado que se muestran y se exportan."""
    c = r.config
    t_cerrado = torricelli(c)
    return {
        "tiempo_s": r.tiempo, "tiempo_min": r.tiempo / 60.0, "acero_vaciado_t": r.colado, "caudal_medio_t_min": r.caudal_medio * 60.0,
        "caudal_inicial_t_min": float(r.caudal[0]) * 60.0, "caudal_final_t_min": float(r.caudal[-1]) * 60.0,
        "carga_inicial_mm": float(r.carga[0]), "carga_final_mm": float(r.carga[-1]),
        "velocidad_inicial_m_s": c.perdidas.velocidad(float(r.carga[0]), c.paso.diametro, c.densidad),
        "area_de_paso_cm2": c.paso.area_mm2 / 100.0, "diametro_mm": c.paso.diametro, "fraccion_abierta": c.fraccion_abierta,
        "area_superficie_m2": c.recipiente.area_superficie(c.acero_inicial - c.talon),
        "tiempo_torricelli_s": t_cerrado, "motivo_fin": r.motivo_fin,
    }
