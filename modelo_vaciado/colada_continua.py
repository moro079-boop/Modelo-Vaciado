"""Vaciado en la máquina de colada continua: olla → tundish → moldes, acoplados en el tiempo.

Balances de masa (t, s):

    dM_olla/dt    = −Q_olla
    dM_tundish/dt =  Q_olla − Q_molde

- **Q_olla**, por la válvula deslizante: Q = ρ·C_d·f_A·A·√(2·g·H_olla), con H_olla = altura del acero en la olla + caída del piso de
  la olla a la salida del tubo largo − contrapresión del tundish (lo que el nivel del tundish queda sobre la salida del tubo).
- **f_A** la fija el control de nivel del tundish: la válvula deja pasar lo que piden los moldes más una corrección proporcional
  al error de nivel, Q_pedido = Q_molde + ρ·A_tundish·(h_objetivo − h)/τ, sin pasar de la válvula abierta del todo.
- **Q_molde** = la demanda de la máquina (n·ρ_sólido·ancho·espesor·v), sin pasar de lo que dejan las buzas sumergidas con el
  tapón abierto; si no alcanza, la velocidad baja y se avisa.

La secuencia: cada olla se abre con su acero y se cierra al quedar el remanente (o si deja de tener carga); sigue el cambio de olla,
en el que el tundish sólo se vacía; tras la última olla el tundish se vacía hasta su nivel mínimo y termina la secuencia.

**Preliminar:** sin datos de planta de la válvula, del tundish ni de la máquina; los valores por omisión son supuestos o ejemplos.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .rutas import raiz
from .artesa import Moldes, Tundish
from .olla import GeometriaOlla, TablaOlla
from .valvula import Orificio, abertura_para

CARPETA = raiz() / "datos" / "vaciado" / "colada_continua"
FORMATO_PLANTA = "lwd_eaf.vaciado.colada_continua/1"
FORMATO_ESCENARIO = "lwd_eaf.vaciado.colada/1"

# (clave, etiqueta, unidad, ruta en el archivo de planta). La ruta lleva al valor o a un {"valor", "estado"}.
CAMPOS = (
    ("acero_por_olla_t", "Acero por olla", "t", ("secuencia", "acero_por_olla_t")),
    ("ollas", "Ollas en la secuencia", "", ("secuencia", "ollas")),
    ("cambio_de_olla_s", "Cambio de olla", "s", ("secuencia", "cambio_de_olla_s")),
    ("olla_pared_gastada_mm", "Desgaste de la pared de la olla", "mm", None),
    ("olla_piso_gastado_mm", "Desgaste del piso de la olla", "mm", None),
    ("valvula_diametro_mm", "Diámetro del orificio de la válvula", "mm", ("valvula", "diametro_mm")),
    ("valvula_cd", "Coeficiente de descarga de la válvula", "", ("valvula", "coeficiente_de_descarga")),
    ("valvula_carrera_mm", "Carrera efectiva de la válvula (0 = el diámetro)", "mm", ("valvula", "carrera_mm")),
    ("caida_bajo_el_piso_mm", "Caída del piso de la olla a la salida del tubo", "mm", ("valvula", "caida_bajo_el_piso_mm")),
    ("acero_remanente_t", "Acero remanente al cerrar la olla", "t", ("valvula", "acero_remanente_t")),
    ("tundish_largo_mm", "Largo del fondo del tundish", "mm", ("tundish", "largo_fondo_mm")),
    ("tundish_ancho_mm", "Ancho del fondo del tundish", "mm", ("tundish", "ancho_fondo_mm")),
    ("tundish_talud_grados", "Talud de las paredes del tundish", "°", ("tundish", "talud_grados")),
    ("nivel_operacion_mm", "Nivel de operación del tundish", "mm", ("tundish", "nivel_operacion_mm")),
    ("nivel_minimo_mm", "Nivel mínimo del tundish", "mm", ("tundish", "nivel_minimo_mm")),
    ("nivel_maximo_mm", "Nivel máximo del tundish", "mm", ("tundish", "nivel_maximo_mm")),
    ("nivel_inicial_mm", "Nivel del tundish al abrir la primera olla", "mm", ("tundish", "nivel_inicial_mm")),
    ("altura_salida_tubo_mm", "Altura de la salida del tubo largo sobre el fondo del tundish", "mm", ("tundish", "altura_salida_tubo_mm")),
    ("constante_de_control_s", "Constante del control de nivel", "s", ("tundish", "constante_de_control_s")),
    ("lineas", "Líneas de colada", "", ("moldes", "lineas")),
    ("ancho_mm", "Ancho del producto", "mm", ("moldes", "ancho_mm")),
    ("espesor_mm", "Espesor del producto", "mm", ("moldes", "espesor_mm")),
    ("velocidad_m_min", "Velocidad de colada", "m/min", ("moldes", "velocidad_m_min")),
    ("densidad_solido", "Densidad del acero sólido", "t/m³", ("moldes", "densidad_solido")),
    ("buza_diametro_mm", "Diámetro de la buza sumergida", "mm", ("moldes", "buza_sumergida", "diametro_mm")),
    ("buza_cd", "Coeficiente de descarga de la buza", "", ("moldes", "buza_sumergida", "coeficiente_de_descarga")),
    ("buza_largo_mm", "Largo de la buza bajo el fondo del tundish", "mm", ("moldes", "buza_sumergida", "largo_bajo_el_fondo_mm")),
    ("buza_inmersion_mm", "Inmersión de la buza en el molde", "mm", ("moldes", "buza_sumergida", "inmersion_mm")),
)
ETIQUETAS = {c[0]: (c[1], c[2]) for c in CAMPOS}


def plantas_con_datos() -> list[str]:
    return sorted(p.stem for p in CARPETA.glob("*.json"))


def cargar_planta(planta: str) -> dict:
    r = CARPETA / f"{planta}.json"
    if not r.exists():
        raise FileNotFoundError(f"la planta «{planta}» no tiene datos de colada continua; las que sí: {', '.join(plantas_con_datos())}")
    d = json.loads(r.read_text(encoding="utf-8"))
    if d.get("formato") != FORMATO_PLANTA:
        raise ValueError(f"{r.name}: formato {d.get('formato')!r}, se esperaba {FORMATO_PLANTA!r}")
    return d


def parametros_de_planta(planta: str) -> dict[str, tuple[float, str]]:
    """{clave: (valor, estado)} con los valores del archivo de la planta."""
    d = cargar_planta(planta)
    salida = {}
    for clave, _, _, ruta in CAMPOS:
        if ruta is None:
            salida[clave] = (0.0, "dato del usuario")
            continue
        nodo, estado = d, None
        for parte in ruta:
            estado = nodo.get("estado", estado) if isinstance(nodo, dict) else estado
            nodo = nodo[parte]
        if isinstance(nodo, dict):
            estado, nodo = nodo.get("estado", estado), nodo.get("valor")
        salida[clave] = (float(nodo or 0.0), str(estado or "sin estado"))
    return salida


@dataclass(frozen=True)
class ConfigColada:
    planta: str
    olla: TablaOlla
    valvula: Orificio
    carrera: float | None
    caida: float
    remanente: float
    tundish: Tundish
    nivel_inicial: float
    altura_salida_tubo: float
    tau: float
    moldes: Moldes
    acero_por_olla: float
    ollas: int
    cambio: float
    parametros: dict

    @property
    def densidad(self) -> float:
        return self.olla.geometria.densidad


def configurar(planta: str, cambios: dict | None = None) -> ConfigColada:
    """La configuración de la planta con los cambios del escenario ({clave: valor})."""
    d = cargar_planta(planta)
    p = {k: v for k, (v, _) in parametros_de_planta(planta).items()}
    p.update({k: float(v) for k, v in (cambios or {}).items() if k in ETIQUETAS})
    g = GeometriaOlla.de_datos(d["olla"])
    tabla = TablaOlla.de_geometria(g, p["olla_pared_gastada_mm"], p["olla_piso_gastado_mm"])
    tundish = Tundish(p["tundish_largo_mm"], p["tundish_ancho_mm"], p["tundish_talud_grados"], g.densidad,
                      p["nivel_operacion_mm"], p["nivel_minimo_mm"], p["nivel_maximo_mm"])
    moldes = Moldes(int(p["lineas"]), p["ancho_mm"], p["espesor_mm"], p["velocidad_m_min"], p["densidad_solido"],
                    Orificio(p["buza_diametro_mm"], p["buza_cd"]), p["buza_largo_mm"], p["buza_inmersion_mm"])
    return ConfigColada(planta, tabla, Orificio(p["valvula_diametro_mm"], p["valvula_cd"]), p["valvula_carrera_mm"] or None,
                        p["caida_bajo_el_piso_mm"], p["acero_remanente_t"], tundish, p["nivel_inicial_mm"],
                        p["altura_salida_tubo_mm"], p["constante_de_control_s"], moldes, p["acero_por_olla_t"],
                        max(int(p["ollas"]), 1), p["cambio_de_olla_s"], p)


# ---------------------------------------------------------------------------
# Piezas del cálculo
# ---------------------------------------------------------------------------

def carga_olla(c: ConfigColada, masa_olla: float, nivel_tundish: float) -> float:
    """mm de acero que empujan por la válvula: altura en la olla + caída − contrapresión del tundish."""
    if masa_olla <= 0.0:
        return 0.0
    return c.olla.altura(masa_olla) + c.caida - max(nivel_tundish - c.altura_salida_tubo, 0.0)


def caudal_olla_abierta(c: ConfigColada, masa_olla: float, nivel_tundish: float) -> float:
    return c.valvula.caudal(carga_olla(c, masa_olla, nivel_tundish), c.densidad)


class _NivelTundish:
    """Nivel del tundish por interpolación (la inversa del volumen, tabulada cada mm)."""

    def __init__(self, t: Tundish):
        self.h = np.arange(0.0, max(t.nivel_maximo * 2.0, 3000.0), 1.0)
        self.m = np.array([t.masa(x) for x in self.h])

    def __call__(self, masa: float) -> float:
        return float(np.interp(masa, self.m, self.h))


@dataclass
class Olla:
    numero: int
    apertura: float
    cierre: float = math.nan
    colado: float = 0.0
    fraccion_media: float = math.nan
    nivel_minimo_en_cambio: float = math.nan
    motivo_cierre: str = ""

    @property
    def duracion(self) -> float:
        return self.cierre - self.apertura


@dataclass
class ResultadoColada:
    t: np.ndarray
    masa_olla: np.ndarray
    masa_tundish: np.ndarray
    nivel_tundish: np.ndarray
    caudal_olla: np.ndarray
    caudal_molde: np.ndarray
    fraccion: np.ndarray          # f_A de la válvula de la olla (nan sin olla)
    velocidad: np.ndarray         # m/min efectiva
    ollas: list
    eventos: list = field(default_factory=list)
    config: ConfigColada | None = None
    nombre: str = ""

    @property
    def tiempo(self) -> float:
        return float(self.t[-1])

    @property
    def abertura(self) -> np.ndarray:
        """% de carrera de la válvula de la olla (a partir de f_A)."""
        c = self.config
        return np.array([abertura_para(f, c.valvula.diametro, c.carrera) if np.isfinite(f) else np.nan for f in self.fraccion])

    @property
    def colado_total(self) -> float:
        return sum(o.colado for o in self.ollas)


def simular_secuencia(c: ConfigColada, dt: float = 1.0, muestreo: float = 5.0, t_max: float = 24 * 3600.0,
                      nombre: str = "") -> ResultadoColada:
    nivel = _NivelTundish(c.tundish)
    rho = c.densidad
    m_t = c.tundish.masa(c.nivel_inicial)
    t = 0.0
    T, MO, MT, HT, QO, QM, FA, V = [], [], [], [], [], [], [], []
    eventos, ollas = [], []
    avisos = set()

    def salida(mt: float) -> tuple[float, float]:
        h = nivel(mt)
        demanda = c.moldes.demanda()
        cap = c.moldes.capacidad(h, rho) if h > 0 else 0.0
        q = min(demanda, cap)
        return q, (q / c.moldes.demanda(1.0) if demanda > 0 else 0.0)

    def control(mo: float, mt: float, qm: float) -> tuple[float, float]:
        if mo <= c.remanente:
            return 0.0, math.nan
        h = nivel(mt)
        q_abierta = caudal_olla_abierta(c, mo, h)
        if q_abierta <= 0.0:
            return 0.0, 0.0
        pedido = qm + rho * c.tundish.area(h) * (c.tundish.nivel_operacion - h) / 1000.0 / c.tau
        f = min(max(pedido / q_abierta, 0.0), 1.0)
        return f * q_abierta, f

    def anotar(mo, mt, qo, qm, f, vel):
        T.append(t); MO.append(mo); MT.append(mt); HT.append(nivel(mt)); QO.append(qo); QM.append(qm); FA.append(f); V.append(vel)  # noqa: E702

    proximo = 0.0
    for k in range(c.ollas):
        if k > 0:                                                   # cambio de olla: el tundish sólo se vacía
            fin_cambio, h_min = t + c.cambio, math.inf
            while t < fin_cambio - 1e-9:
                paso = min(dt, fin_cambio - t)
                qm, vel = salida(m_t)
                m_t = max(m_t - qm * paso, 0.0)
                t += paso
                h_min = min(h_min, nivel(m_t))
                if t + 1e-9 >= proximo:
                    anotar(0.0, m_t, 0.0, qm, math.nan, vel)
                    proximo = t + muestreo
            ollas[-1].nivel_minimo_en_cambio = h_min
            if h_min < c.tundish.nivel_minimo and "cambio" not in avisos:
                avisos.add("cambio")
                eventos.append((t, f"en el cambio de olla el tundish baja a {h_min:.0f} mm, debajo del mínimo de {c.tundish.nivel_minimo:.0f} mm"))
        m_o = c.acero_por_olla
        o = Olla(k + 1, t)
        suma_f = tiempo_f = 0.0
        while t < t_max:
            qm, vel = salida(m_t)
            qo, f = control(m_o, m_t, qm)
            if qo <= 0.0 and m_o <= c.remanente + 1e-9:
                o.motivo_cierre = "remanente"
                break
            if qo <= 0.0 and f == 0.0 and nivel(m_t) < c.tundish.nivel_operacion:
                o.motivo_cierre = "sin carga sobre la válvula"
                eventos.append((t, f"la olla {k + 1} se queda sin carga con {m_o:.1f} t dentro"))
                break
            # Heun sobre las dos masas
            mo2, mt2 = m_o - qo * dt, m_t + (qo - qm) * dt
            qm2, _ = salida(mt2)
            qo2, _ = control(mo2, mt2, qm2)
            qo_m, qm_m = 0.5 * (qo + qo2), 0.5 * (qm + qm2)
            paso = dt
            if qo_m > 0 and m_o - qo_m * paso < c.remanente:
                paso = (m_o - c.remanente) / qo_m
            m_o -= qo_m * paso
            m_t = max(m_t + (qo_m - qm_m) * paso, 0.0)
            o.colado += qo_m * paso
            if math.isfinite(f):
                suma_f += f * paso
                tiempo_f += paso
            t += paso
            if f >= 0.999 and qo_m < qm_m and "abierta" not in avisos:
                avisos.add("abierta")
                eventos.append((t, f"la válvula de la olla {k + 1} queda abierta del todo con {m_o:.0f} t dentro y aun así entra menos de lo que sale: la olla ya no alcanza la demanda"))
            if vel < c.moldes.velocidad - 1e-6 and "buza" not in avisos:
                avisos.add("buza")
                eventos.append((t, f"las buzas no alcanzan la velocidad de colada: {vel:.2f} m/min en lugar de {c.moldes.velocidad:.2f}"))
            if nivel(m_t) > c.tundish.nivel_maximo and "maximo" not in avisos:
                avisos.add("maximo")
                eventos.append((t, f"el tundish pasa de su nivel máximo ({c.tundish.nivel_maximo:.0f} mm)"))
            if t + 1e-9 >= proximo:
                anotar(m_o, m_t, qo_m, qm_m, f, vel)
                proximo = t + muestreo
            if m_o <= c.remanente + 1e-9:
                o.motivo_cierre = "remanente"
                break
        o.cierre = t
        o.fraccion_media = suma_f / tiempo_f if tiempo_f > 0 else math.nan
        ollas.append(o)
        anotar(m_o, m_t, 0.0, salida(m_t)[0], math.nan, salida(m_t)[1])
    # vaciado final del tundish hasta su mínimo
    m_min = c.tundish.masa(c.tundish.nivel_minimo)
    while m_t > m_min + 1e-9 and t < t_max:
        qm, vel = salida(m_t)
        if qm <= 0:
            break
        paso = min(dt, (m_t - m_min) / qm)
        m_t -= qm * paso
        t += paso
        if t + 1e-9 >= proximo or m_t <= m_min + 1e-9:
            anotar(0.0, m_t, 0.0, qm, math.nan, vel)
            proximo = t + muestreo
    return ResultadoColada(np.array(T), np.array(MO), np.array(MT), np.array(HT), np.array(QO), np.array(QM), np.array(FA),
                           np.array(V), ollas, eventos, c, nombre)


# ---------------------------------------------------------------------------
# Cálculos de una sola pieza
# ---------------------------------------------------------------------------

def vaciado_libre_olla(c: ConfigColada, acero: float | None = None, nivel_tundish: float | None = None,
                       dt: float = 0.5) -> tuple[np.ndarray, np.ndarray]:
    """La olla con la válvula abierta del todo y el tundish quieto en su nivel de operación: el menor tiempo en que puede vaciarse.
    Devuelve (t, masa)."""
    m = c.acero_por_olla if acero is None else acero
    h = c.tundish.nivel_operacion if nivel_tundish is None else nivel_tundish
    T, M, t = [0.0], [m], 0.0
    while m > c.remanente + 1e-9:
        q1 = caudal_olla_abierta(c, m, h)
        if q1 <= 0:
            break
        q2 = caudal_olla_abierta(c, max(m - q1 * dt, 0.0), h)
        q = 0.5 * (q1 + q2)
        paso = min(dt, (m - c.remanente) / q)
        m -= q * paso
        t += paso
        T.append(t)
        M.append(m)
    return np.array(T), np.array(M)


def tiempo_de_colado_de_una_olla(c: ConfigColada) -> float:
    """Con la máquina a su velocidad, lo que dura una olla en régimen: (acero − remanente) / demanda."""
    return (c.acero_por_olla - c.remanente) / c.moldes.demanda()


def margen_en_cambio(c: ConfigColada) -> dict:
    """Tiempo que el tundish aguanta sin olla, del nivel de operación al mínimo, a la velocidad de colada."""
    m = c.tundish.masa(c.tundish.nivel_operacion) - c.tundish.masa(c.tundish.nivel_minimo)
    q = c.moldes.demanda()
    return {"masa_util_t": m, "tiempo_s": m / q if q > 0 else math.inf, "cambio_s": c.cambio}


def velocidad_maxima(c: ConfigColada) -> dict:
    """m/min que permiten la válvula de la olla (abierta del todo, con el remanente encima y el tundish en operación) y las buzas
    (con el tundish en operación)."""
    q_olla = caudal_olla_abierta(c, c.remanente + 1e-6, c.tundish.nivel_operacion)
    return {"por_la_olla": q_olla / c.moldes.demanda(1.0),
            "por_las_buzas": c.moldes.velocidad_maxima(c.tundish.nivel_operacion, c.densidad)}


def resumen(r: ResultadoColada) -> dict:
    c = r.config
    t_libre, _ = vaciado_libre_olla(c)
    return {
        "tiempo_total_s": r.tiempo,
        "acero_colado_t": r.colado_total,
        "colado_por_olla_s": [o.duracion for o in r.ollas],
        "colado_por_olla_regimen_s": tiempo_de_colado_de_una_olla(c),
        "vaciado_libre_olla_s": float(t_libre[-1]) if len(t_libre) else math.nan,
        "fraccion_media": [o.fraccion_media for o in r.ollas],
        "nivel_minimo_en_cambio_mm": [o.nivel_minimo_en_cambio for o in r.ollas[:-1]],
        "margen_en_cambio": margen_en_cambio(c),
        "velocidad_maxima": velocidad_maxima(c),
        "demanda_t_min": c.moldes.demanda() * 60.0,
    }


# ---------------------------------------------------------------------------
# Escenarios
# ---------------------------------------------------------------------------

def escenario_vacio(planta: str = "pesqueria", nombre: str = "Secuencia") -> dict:
    return {"formato": FORMATO_ESCENARIO, "nombre": nombre, "planta": planta, "cambios": {}}


def abrir(ruta: Path | str) -> dict:
    e = json.loads(Path(ruta).read_text(encoding="utf-8"))
    if e.get("formato") != FORMATO_ESCENARIO:
        raise ValueError(f"{Path(ruta).name}: formato {e.get('formato')!r}, se esperaba {FORMATO_ESCENARIO!r}")
    return e


def correr(e: dict, dt: float = 1.0) -> ResultadoColada:
    return simular_secuencia(configurar(e["planta"], e.get("cambios")), dt=dt, nombre=e.get("nombre", ""))
