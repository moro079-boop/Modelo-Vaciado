"""Geometría del horno a partir del archivo de planta, a refractario nuevo.

Coordenadas de la sección: X horizontal (en A-A, + hacia la puerta y − hacia la nariz),
Y altura desde el fondo de la coraza. Coordenadas en planta: X igual que en A-A, Z
perpendicular. Todo en mm.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .cache import guardar

LADOS_A_A = ("nariz", "puerta")
LADOS_B_B = ("b_izquierdo", "b_derecho")


# ---------------------------------------------------------------------------
# Paredes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Capa:
    material: str
    espesor: float
    funcion: str | None
    x_exterior: float  # lado de la capa hacia la coraza
    x_cara: float  # lado de la capa hacia el interior
    y_superior: float | None = None  # si la capa termina antes que el tramo


@dataclass(frozen=True)
class TramoPared:
    lado: str
    hiladas: tuple[int, int] | None  # None en las filas del umbral
    y_inferior: float
    y_superior: float
    capas: tuple[Capa, ...]
    estado: str

    @property
    def x_cara(self) -> float:
        """Cara caliente del tramo."""
        return self.capas[-1].x_cara

    @property
    def espesor_total(self) -> float:
        return sum(c.espesor for c in self.capas)

    @property
    def capa_de_trabajo(self) -> Capa:
        return next(c for c in self.capas if c.funcion == "trabajo")


def _sentido(datos_lado: dict) -> int:
    """+1 si el lado está en X positivas; la cara caliente avanza hacia −X."""
    return 1 if datos_lado["lado_de_x"] == "positivo" else -1


def y_hilada(planta: dict, hilada: int) -> tuple[float, float]:
    """Y inferior y superior de una hilada."""
    pared = planta["pared"]
    alto = float(pared["altura_de_hilada"]["valor"])
    base = float(pared["y_base_hilada_1"]["valor"]) + alto * (hilada - 1)
    return base, base + alto


def _capas(lista: list[dict], x_exterior: float, sentido: int, fraccion_desgaste: float = 0.0,
           perdida_mm: float | None = None) -> tuple[Capa, ...]:
    """Capas desde la coraza hacia dentro; la de trabajo pierde ``fraccion_desgaste`` de su espesor
    o, si se da, ``perdida_mm`` (sin pasar de su espesor)."""
    capas = []
    x = x_exterior
    for capa in lista:
        espesor = float(capa["espesor"])
        if capa.get("funcion") == "trabajo":
            espesor = max(espesor - perdida_mm, 0.0) if perdida_mm is not None else espesor * (1.0 - fraccion_desgaste)
        x_siguiente = x - sentido * espesor
        y_sup = capa.get("y_superior")
        capas.append(Capa(capa["material"], espesor, capa.get("funcion"), x, x_siguiente,
                          None if y_sup is None else float(y_sup)))
        x = x_siguiente
    return tuple(capas)


def tramos_pared(planta: dict, lado: str, desgaste=None) -> list[TramoPared]:
    """Tramos de pared de un lado, de abajo hacia arriba.

    En el lado puerta se añaden las filas del umbral como tramos sin hiladas, con una sola
    capa de trabajo cuyo espesor es el largo de la pieza. Con ``desgaste``
    (``lwd_eaf.desgaste.Desgaste``) la capa de trabajo pierde el % de pared indicado; la
    cara caliente retrocede hacia la coraza.

    Si el desgaste trae un **perfil por línea** (fase 5), cada hilada es un tramo propio y la
    capa de trabajo pierde la media de las diez líneas de la hilada; las filas del umbral
    pierden la media de las líneas que ocupan (supuesto: el umbral se desgasta como la pared
    del lado puerta a su altura).
    """
    perfil = desgaste.perfil if desgaste is not None else None
    f = desgaste.fraccion_pared if desgaste is not None else 0.0
    datos = planta["pared"]["lados"][lado]
    sentido = _sentido(datos)
    x_exterior = float(datos["x_exterior"]["valor"])
    perdida = perfil.perdida(lado) if perfil is not None else None
    tramos = []
    for tramo in datos["tramos"]:
        h0, h1 = tramo["hiladas"]
        if perfil is None:
            y0 = y_hilada(planta, h0)[0]
            y1 = y_hilada(planta, h1)[1]
            tramos.append(TramoPared(lado, (h0, h1), y0, y1,
                                     _capas(tramo["capas"], x_exterior, sentido, f), tramo["estado"]))
            continue
        for h in range(h0, h1 + 1):
            y0, y1 = y_hilada(planta, h)
            tramos.append(TramoPared(lado, (h, h), y0, y1,
                                     _capas(tramo["capas"], x_exterior, sentido,
                                            perdida_mm=_perdida_media(perdida, y0, y1)), tramo["estado"]))
    umbral = datos.get("umbral")
    if umbral:
        largo = float(umbral["largo_de_pieza"])
        for fila in umbral["filas"]:
            x_ext = float(fila["x_cara"]) + sentido * largo
            if perfil is None:
                restante = largo * (1.0 - f)
            else:
                restante = max(largo - _perdida_media(perdida, float(fila["y_inferior"]), float(fila["y_superior"])), 0.0)
            capa = Capa(umbral["material"], restante, "trabajo", x_ext, x_ext - sentido * restante)
            tramos.append(TramoPared(lado, None, float(fila["y_inferior"]),
                                     float(fila["y_superior"]), (capa,), umbral["estado"]))
    return tramos


def _perdida_media(perdida: np.ndarray, y_inferior: float, y_superior: float) -> float:
    """Pérdida media (mm) de las líneas de 10 mm entre dos alturas."""
    a = max(int(round(y_inferior / 10.0)), 0)
    b = min(max(int(round(y_superior / 10.0)), a + 1), perdida.size)
    return float(perdida[a:b].mean())


def escalera_cara(tramos: list[TramoPared], y_desde: float, y_hasta: float) -> np.ndarray:
    """Polilínea de la cara caliente entre dos alturas, en el sentido de y_desde a y_hasta."""
    sube = y_hasta >= y_desde
    lo, hi = sorted((y_desde, y_hasta))
    tramos = sorted((t for t in tramos if t.y_superior > lo and t.y_inferior < hi),
                    key=lambda t: t.y_inferior, reverse=not sube)
    puntos: list[tuple[float, float]] = []
    for t in tramos:
        a, b = max(t.y_inferior, lo), min(t.y_superior, hi)
        if not sube:
            a, b = b, a
        puntos += [(t.x_cara, a), (t.x_cara, b)]
    return np.array(puntos, dtype=np.float64)


# ---------------------------------------------------------------------------
# Fondo
# ---------------------------------------------------------------------------

def _esfera(planta: dict, radio: float, x) -> np.ndarray:
    yc = float(planta["fondo"]["y_centro_esfera"]["valor"])
    x = np.asarray(x, dtype=np.float64)
    return yc - np.sqrt(radio * radio - x * x)


def y_cara_caliente_casquete(planta: dict, x) -> np.ndarray:
    """Y de la esfera de la cara caliente del fondo."""
    return _esfera(planta, float(planta["fondo"]["radio_cara_caliente"]["valor"]), x)


def y_esfera_capa(planta: dict, n_capas: int, x) -> np.ndarray:
    """Y de la esfera que limita por arriba las ``n_capas`` primeras capas del fondo.

    ``n_capas = 0`` es la coraza.
    """
    fondo = planta["fondo"]
    radio = float(fondo["radio_coraza"]["valor"])
    radio -= sum(float(c["espesor"]) for c in fondo["capas"]["lista"][:n_capas])
    return _esfera(planta, radio, x)


def perfil_fondo(planta: dict, seccion: str = "A-A", paso: float = 10.0) -> np.ndarray:
    """Polilínea de la cara caliente del fondo, de X menor a X mayor."""
    clave = {"A-A": "perfil_a_a", "B-B": "perfil_b_b"}[seccion]
    puntos: list[tuple[float, float]] = []
    for tramo in planta["fondo"][clave]["tramos"]:
        if tramo["tipo"] == "recta":
            nuevos = [tuple(tramo["desde"]), tuple(tramo["hasta"])]
        elif tramo["tipo"] == "poligonal":
            nuevos = [tuple(p) for p in tramo["puntos"]]
        elif tramo["tipo"] == "arco":
            x0, x1 = float(tramo["x_desde"]), float(tramo["x_hasta"])
            n = max(2, math.ceil((x1 - x0) / paso) + 1)
            xs = np.linspace(x0, x1, n)
            nuevos = list(zip(xs, y_cara_caliente_casquete(planta, xs)))
        else:
            raise ValueError(f"tramo de fondo desconocido: {tramo['tipo']!r}")
        for p in nuevos:
            p = (float(p[0]), float(p[1]))
            # Las uniones de tramos coinciden a menos de 0.1 mm (redondeo de las cotas).
            if not puntos or math.dist(puntos[-1], p) > 0.1:
                puntos.append(p)
    return np.array(puntos, dtype=np.float64)


def y_fondo(planta: dict, x, seccion: str = "A-A") -> np.ndarray:
    """Y de la cara caliente del fondo en X, interpolando sobre la polilínea fina."""
    perfil = perfil_fondo(planta, seccion, paso=1.0)
    return np.interp(np.asarray(x, dtype=np.float64), perfil[:, 0], perfil[:, 1],
                     left=np.nan, right=np.nan)


# ---------------------------------------------------------------------------
# Sección A-A completa
# ---------------------------------------------------------------------------

def cara_caliente_a_a(planta: dict, paso: float = 10.0, desgaste=None) -> np.ndarray:
    """Cara caliente en A-A: de lo alto de la nariz al final del umbral.

    Sin desgaste es el perfil exacto del plano. Con desgaste, las paredes salen de
    ``tramos_pared(..., desgaste)`` y el piso se muestrea en Z = 0 de la misma función que
    usa la cavidad 3D (``lwd_eaf.cavidad.y_piso_a_a``).
    """
    if desgaste is not None and not desgaste.es_nuevo:
        return _cara_caliente_a_a_desgastada(planta, paso, desgaste)
    fondo = perfil_fondo(planta, "A-A", paso)
    nariz = tramos_pared(planta, "nariz")
    puerta = tramos_pared(planta, "puerta")
    y_tope_nariz = max(t.y_superior for t in nariz)
    lado_nariz = escalera_cara(nariz, y_tope_nariz, fondo[0, 1])
    lado_puerta = escalera_cara(puerta, fondo[-1, 1], max(t.y_superior for t in puerta))
    umbral = planta["pared"]["lados"]["puerta"]["umbral"]
    fin = np.array([[float(umbral["x_fin_ladrillo_superior"]), lado_puerta[-1, 1]]])
    partes = [lado_nariz, fondo, lado_puerta, fin]
    puntos = np.vstack(partes)
    # Quitar puntos repetidos en las uniones.
    keep = np.r_[True, np.any(np.abs(np.diff(puntos, axis=0)) > 1e-6, axis=1)]
    return puntos[keep]


def _cara_en(tramos: list[TramoPared], y: float) -> float:
    for t in tramos:
        if t.y_inferior <= y < t.y_superior:
            return t.x_cara
    return tramos[0].x_cara if y < tramos[0].y_inferior else tramos[-1].x_cara


def _encuentro_con_piso(tramos, y_piso, x_inicial: float) -> tuple[float, float]:
    """Punto donde la cara de la pared toca el piso (iteración entre cara y piso)."""
    x = x_inicial
    for _ in range(10):
        y = float(y_piso(np.array([x]))[0])
        x_nuevo = _cara_en(tramos, y)
        if abs(x_nuevo - x) < 1e-9:
            break
        x = x_nuevo
    return x, float(y_piso(np.array([x]))[0])


def _cara_caliente_a_a_desgastada(planta: dict, paso: float, desgaste) -> np.ndarray:
    from .cavidad import y_piso_a_a

    nariz = sorted(tramos_pared(planta, "nariz", desgaste), key=lambda t: t.y_inferior)
    puerta = sorted(tramos_pared(planta, "puerta", desgaste), key=lambda t: t.y_inferior)

    def y_piso(x):
        return y_piso_a_a(planta, x, desgaste)

    x_n, y_n = _encuentro_con_piso(nariz, y_piso, _cara_en(nariz, 1350.0))
    x_p, y_p = _encuentro_con_piso(puerta, y_piso, _cara_en(puerta, 1150.0))
    xs = np.arange(x_n, x_p, paso)
    fondo = np.column_stack([np.r_[xs, x_p], y_piso(np.r_[xs, x_p])])
    fondo[0] = (x_n, y_n)
    y_tope_nariz = max(t.y_superior for t in nariz)
    lado_nariz = escalera_cara(nariz, y_tope_nariz, y_n)
    lado_puerta = escalera_cara(puerta, y_p, max(t.y_superior for t in puerta))
    umbral = planta["pared"]["lados"]["puerta"]["umbral"]
    x_fin = max(float(umbral["x_fin_ladrillo_superior"]), float(lado_puerta[-1, 0]))
    fin = np.array([[x_fin, lado_puerta[-1, 1]]])
    puntos = np.vstack([lado_nariz, fondo, lado_puerta, fin])
    keep = np.r_[True, np.any(np.abs(np.diff(puntos, axis=0)) > 1e-6, axis=1)]
    return puntos[keep]


# ---------------------------------------------------------------------------
# Planta
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Arco:
    nombre: str
    centro: tuple[float, float]
    radio: float  # radio de la coraza; el desplazamiento se aplica aparte
    angulo_desde: float  # radianes, sentido antihorario
    angulo_hasta: float

    @property
    def amplitud_grados(self) -> float:
        return math.degrees(self.angulo_hasta - self.angulo_desde)


def arcos_planta(planta: dict) -> list[Arco]:
    """Los cinco arcos del contorno de la coraza, en sentido antihorario desde +X.

    Cuerpo (radio Rs, centro en el eje), arco de unión superior (Ra), nariz (Rn, centro en
    x_n) y arco de unión inferior. Los arcos de unión son tangentes interiores al cuerpo y a
    la nariz: |C − O| = Ra − Rs y |C − N| = Ra − Rn.
    """
    c = planta["coraza_en_planta"]
    rs = float(c["radio_cuerpo"]["valor"])
    rn = float(c["radio_nariz"]["valor"])
    ra = float(c["radio_arcos_de_union"]["valor"])
    xn = float(c["x_centro_nariz"]["valor"])
    cx = ((ra - rn) ** 2 - (ra - rs) ** 2 - xn ** 2) / (-2.0 * xn)
    cz = math.sqrt((ra - rs) ** 2 - cx ** 2)

    centro_sup = (cx, -cz)  # el arco de arriba (Z > 0) tiene el centro abajo
    centro_inf = (cx, cz)
    # La dirección del centro del arco de unión hacia el centro del cuerpo (o de la nariz)
    # es también la del punto de tangencia visto desde el cuerpo (o desde la nariz).
    t_cuerpo = math.atan2(-centro_sup[1], -centro_sup[0])
    t_nariz = math.atan2(-centro_sup[1], xn - centro_sup[0])
    return [
        Arco("cuerpo", (0.0, 0.0), rs, -t_cuerpo, t_cuerpo),
        Arco("union_superior", centro_sup, ra, t_cuerpo, t_nariz),
        Arco("nariz", (xn, 0.0), rn, t_nariz, 2 * math.pi - t_nariz),
        Arco("union_inferior", centro_inf, ra, 2 * math.pi - t_nariz, 2 * math.pi - t_cuerpo),
    ]


def contorno_planta(planta: dict, desplazamiento: float = 0.0, paso: float = 10.0) -> np.ndarray:
    """Contorno cerrado en planta (X, Z), desplazado hacia dentro ``desplazamiento`` mm.

    Con 0 es la cara interior de la coraza. Como los cuatro arcos son convexos vistos desde
    dentro, el desplazado conserva los centros y resta el desplazamiento a cada radio.
    """
    puntos = []
    for arco in arcos_planta(planta):
        r = arco.radio - desplazamiento
        n = max(2, math.ceil(r * (arco.angulo_hasta - arco.angulo_desde) / paso) + 1)
        ang = np.linspace(arco.angulo_desde, arco.angulo_hasta, n)
        xs = arco.centro[0] + r * np.cos(ang)
        zs = arco.centro[1] + r * np.sin(ang)
        tramo = np.column_stack([xs, zs])
        puntos.append(tramo if not puntos else tramo[1:])
    return np.vstack(puntos)


# ---------------------------------------------------------------------------
# Desarrollo: material y espesor de trabajo por hilada a lo largo del contorno
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ZonaDesarrollo:
    id: str
    lugar: str
    hiladas: tuple[int, int]
    material: str
    serie: int | None
    espesor_trabajo: float | None  # de la serie de la pieza; None si no se conoce
    rotulos: tuple[str, ...]
    celdas: tuple[tuple[int, float, float], ...]  # (hilada, s_desde, s_hasta)


def zonas_desarrollo(planta: dict) -> list[ZonaDesarrollo]:
    """Zonas del desarrollo tal como las rotula el plano."""
    desarrollo = planta["pared"]["desarrollo"]
    series = {int(k): float(v) for k, v in desarrollo["series"].items() if k.isdigit()}
    zonas = []
    for z in desarrollo["zonas"]:
        serie = z["serie"]
        zonas.append(ZonaDesarrollo(
            z["id"], z["lugar"], tuple(z["hiladas"]), z["material"], serie,
            None if serie is None else series[int(serie)], tuple(z["rotulos"]),
            tuple((int(h), float(a), float(b)) for h, a, b in z["celdas"]),
        ))
    return zonas


def zona_en(planta: dict, hilada: int, s: float) -> ZonaDesarrollo | None:
    """Zona del desarrollo en la hilada y la posición s (mm del desarrollo); None si es hueco."""
    longitud = float(planta["pared"]["desarrollo"]["longitud"])
    for zona in zonas_desarrollo(planta):
        for h, a, b in zona.celdas:
            if h == hilada and (a <= s < b or (s == longitud and b == longitud)):
                return zona
    return None


def _sectores_desarrollo(planta: dict) -> list[tuple[str, float, float, float, float]]:
    """(arco, s_desde, s_hasta, ángulo_desde, ángulo_hasta) de cada sector del desarrollo.

    Los ángulos son los de ``arcos_planta`` (radianes, antihorario desde +X). El desarrollo
    recorre el contorno en sentido horario, así que el ángulo decrece con s.
    """
    arcos = {a.nombre: a for a in arcos_planta(planta)}
    t_c = arcos["cuerpo"].angulo_hasta
    t_n = arcos["union_superior"].angulo_hasta
    dos_pi = 2 * math.pi
    angulos = {
        ("cuerpo", "-Z"): (0.0, -t_c),
        ("union_inferior", "-Z"): (dos_pi - t_c, dos_pi - t_n),
        ("nariz", None): (dos_pi - t_n, t_n),
        ("union_superior", "+Z"): (t_n, t_c),
        ("cuerpo", "+Z"): (t_c, 0.0),
    }
    sectores = []
    for sector in planta["pared"]["desarrollo"]["sectores"]:
        a0, a1 = angulos[(sector["arco"], sector.get("lado"))]
        s0, s1 = (float(v) for v in sector["s"])
        sectores.append((sector["arco"], s0, s1, a0, a1))
    return sectores


_CACHE_CONTORNO: dict = {}


def _contorno_y_sectores(planta: dict):
    """Los arcos por nombre y los sectores del desarrollo de una planta, calculados una sola vez.

    ``posicion_en_planta`` se llama miles de veces por cavidad (una por columna del contorno) y la campaña
    reconstruye la cavidad en cada colada; recalcular los arcos en cada llamada era la cuarta parte del tiempo
    de una colada (EAF-017, medido). La planta no cambia durante la ejecución (misma regla que las demás cachés).
    """
    hallado = _CACHE_CONTORNO.get(id(planta))
    if hallado is not None and hallado[0] is planta:
        return hallado[1], hallado[2]
    arcos = {a.nombre: a for a in arcos_planta(planta)}
    sectores = _sectores_desarrollo(planta)
    guardar(_CACHE_CONTORNO, id(planta), (planta, arcos, sectores), 4)
    return arcos, sectores


def posicion_en_planta(planta: dict, s: float, desplazamiento: float = 0.0) -> tuple[float, float]:
    """Punto (X, Z) del contorno en planta que corresponde a la posición s del desarrollo.

    Dentro de cada sector, s es proporcional al ángulo del arco (así está dibujado el
    desarrollo). ``desplazamiento`` mide hacia dentro desde la coraza.
    """
    arcos, sectores = _contorno_y_sectores(planta)
    for nombre, s0, s1, a0, a1 in sectores:
        if s0 <= s <= s1:
            ang = a0 + (a1 - a0) * (s - s0) / (s1 - s0)
            arco = arcos[nombre]
            r = arco.radio - desplazamiento
            return arco.centro[0] + r * math.cos(ang), arco.centro[1] + r * math.sin(ang)
    raise ValueError(f"s = {s} fuera del desarrollo")


def s_de_angulo_cuerpo(planta: dict, grados: float) -> float:
    """Posición s del desarrollo para un ángulo del cuerpo (desde +X, + hacia +Z)."""
    ang = math.radians(grados)
    for nombre, s0, s1, a0, a1 in _sectores_desarrollo(planta):
        if nombre == "cuerpo" and min(a0, a1) <= ang <= max(a0, a1):
            return s0 + (s1 - s0) * (ang - a0) / (a1 - a0)
    raise ValueError(f"{grados}° no está en el arco del cuerpo")
