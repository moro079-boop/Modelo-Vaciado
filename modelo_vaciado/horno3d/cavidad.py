"""Cavidad del horno en 3D, discretizada en celdas de 10 mm, a refractario nuevo.

La cavidad se construye con las reglas de ``modelo_3d`` del archivo de planta (supuestos
declarados) sobre lo que el plano define: contorno en planta, desarrollo (espesor de
pared por hilada en cada punto del contorno), perfiles del fondo en A-A y B-B y el lado
puerta de A-A.

Para cada capa horizontal de 10 mm se guarda el área de cavidad por columna de X
(``Cavidad.area``). El volumen bajo cualquier plano inclinado alrededor de un eje paralelo
a Z se obtiene sumando esa tabla (``lwd_eaf.niveles``).

Coordenadas: X (+ puerta), Z (+ hacia arriba en la vista C-C), Y altura; todo en mm.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .cache import guardar
from .desgaste import ALTURA_HILADA, N_HILADAS, PASO_LINEA, Y_BASE_HILADA_1, Desgaste, retroceso_piso
from .geometria import (
    _sectores_desarrollo,
    arcos_planta,
    perfil_fondo,
    posicion_en_planta,
    tramos_pared,
    zonas_desarrollo,
)


@dataclass
class Cavidad:
    paso: float  # mm
    x: np.ndarray  # centros de columna en X (nx)
    y_inferior: np.ndarray  # cota inferior de cada capa (ny)
    area: np.ndarray  # (ny, nx) área de cavidad en mm² por capa y columna de X
    y_fin_refractario: np.ndarray  # (n_contorno,) tope del refractario en cada punto del contorno
    x_cara_contorno: np.ndarray  # (n_contorno,) X de la cara caliente de la última hilada
    x_umbral: float
    y_umbral: float
    y_fondo: float = 679.0  # punto más bajo del piso; h = y_eje − y_fondo (Norte: 679; las plantas de solo niveles traen el suyo)
    # Canal con rebose (EAF-051, Colombia): en las columnas ``columnas_rebose`` la superficie no pasa del plano paralelo por el borde
    # ``rebose`` = (x, y) del extremo del canal; lo de arriba se va por el canal.
    rebose: tuple[float, float] | None = None
    columnas_rebose: np.ndarray | None = None
    # Área acumulada por columna: fila k = suma de las capas 0..k−1 (nuevo, para que el
    # volumen bajo un plano cueste un acceso por columna y no una suma de todas las capas).
    acumulado: np.ndarray = field(init=False, repr=False, compare=False)
    area_con_cero: np.ndarray = field(init=False, repr=False, compare=False)

    def __post_init__(self):
        n, nx = self.area.shape
        self.acumulado = np.zeros((n + 1, nx))
        np.cumsum(self.area, axis=0, out=self.acumulado[1:])
        self.area_con_cero = np.vstack([self.area, np.zeros((1, nx))])

    @property
    def y_superior(self) -> float:
        return float(self.y_inferior[-1] + self.paso)

    def volumen_total(self) -> float:
        """Volumen de toda la malla en m³ (hasta la última capa)."""
        return float(self.area.sum() * self.paso * 1e-9)


# ---------------------------------------------------------------------------
# Contorno en planta: distancia hacia dentro desde la coraza y posición s del desarrollo
# ---------------------------------------------------------------------------

def distancia_y_s(planta: dict, x: np.ndarray, z: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Distancia hacia dentro desde la cara interior de la coraza y posición s del desarrollo.

    Cada punto se asigna al arco del contorno cuya cuña angular (desde su centro) lo
    contiene y que está más cerca; fuera del contorno la distancia es negativa.
    """
    arcos = {a.nombre: a for a in arcos_planta(planta)}
    sectores = _sectores_desarrollo(planta)
    d = np.full(x.shape, -np.inf)
    s = np.full(x.shape, np.nan)
    dos_pi = 2 * math.pi
    for nombre, s0, s1, a0, a1 in sectores:
        arco = arcos[nombre]
        dx, dz = x - arco.centro[0], z - arco.centro[1]
        ang = np.arctan2(dz, dx)
        lo, hi = min(a0, a1), max(a0, a1)
        if hi > math.pi:  # cuñas que cruzan ±180°: trabajar en [0, 2π)
            ang = np.mod(ang, dos_pi)
        dentro = (ang >= lo - 1e-12) & (ang <= hi + 1e-12)
        dist = arco.radio - np.hypot(dx, dz)
        mejor = dentro & ((d == -np.inf) | (dist < d))
        d = np.where(mejor, dist, d)
        s = np.where(mejor, s0 + (ang - a0) / (a1 - a0) * (s1 - s0), s)
    return d, s


# ---------------------------------------------------------------------------
# Espesor de pared por hilada a lo largo del desarrollo
# ---------------------------------------------------------------------------

_CACHE_COMPONENTES: dict = {}


def _componentes(planta: dict, paso_s: float = 1.0):
    """(s, trabajo[21, ns], respaldo[21, ns], hay_celda[21, ns], es_columna_de_nariz[ns]) a refractario
    nuevo. No depende del desgaste, así que se guarda (el motor por colada lo pide en cada colada)."""
    clave = (id(planta), paso_s)
    hallado = _CACHE_COMPONENTES.get(clave)
    if hallado is not None and hallado[0] is planta:
        return hallado[1]
    reglas = planta["modelo_3d"]["pared"]["respaldo"]
    longitud = float(planta["pared"]["desarrollo"]["longitud"])
    s = np.arange(0.0, longitud + paso_s / 2, paso_s)
    trabajo = np.full((N_HILADAS, s.size), np.nan)
    respaldo = np.full((N_HILADAS, s.size), np.nan)
    nariz = np.zeros(s.size, dtype=bool)
    hay_celda = np.zeros((N_HILADAS, s.size), dtype=bool)
    for zona in zonas_desarrollo(planta):
        columna_nariz = zona.hiladas[1] >= 16
        for h, a, b in zona.celdas:
            m = (s >= a) & (s < b) if b < longitud else (s >= a) & (s <= b)
            hay_celda[h - 1, m] = True
            if zona.espesor_trabajo is not None:
                trabajo[h - 1, m] = zona.espesor_trabajo
            if columna_nariz:
                respaldo[h - 1, m] = reglas["columnas_de_nariz"]
                nariz |= m
            else:
                respaldo[h - 1, m] = reglas["hiladas_1_a_13"] if h <= 13 else reglas["hiladas_14_y_15"]
    # Piezas sin serie: el espesor de trabajo de la hilada de abajo en la misma posición.
    for h in range(1, N_HILADAS):
        falta = hay_celda[h] & np.isnan(trabajo[h])
        trabajo[h, falta] = trabajo[h - 1, falta]
    resultado = (s, trabajo, respaldo, hay_celda, nariz)
    guardar(_CACHE_COMPONENTES, clave, (planta, resultado), 4)
    return resultado


def perdida_media_por_hilada(perdida: np.ndarray) -> np.ndarray:
    """Pérdida media (mm) de cada una de las 21 hiladas a partir de las líneas de 10 mm."""
    return np.array([perdida[int(Y_BASE_HILADA_1 + ALTURA_HILADA * h) // int(PASO_LINEA):int(Y_BASE_HILADA_1 + ALTURA_HILADA * (h + 1)) // int(PASO_LINEA)].mean() for h in range(N_HILADAS)])


def espesores_por_hilada(planta: dict, paso_s: float = 1.0,
                         desgaste: Desgaste | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Espesor total de pared (desde la coraza) por hilada en una malla de s.

    Devuelve (s, espesor[21, ns], es_columna_de_nariz[ns]). Sin celda → NaN (hueco de la
    puerta o, en el cuerpo por encima de la hilada 15, paneles). Con ``desgaste`` la capa
    de trabajo pierde el % de pared indicado, igual en todo el contorno (decisión 6) o, con
    un perfil por línea (fase 5), los mm de cada hilada (media de sus diez líneas), por
    separado en las columnas de la nariz y en las demás.
    """
    s, trabajo, respaldo, hay_celda, nariz = _componentes(planta, paso_s)
    if desgaste is not None and desgaste.perfil is not None:
        puerta, nar = desgaste.perfil.arrays
        perdida = np.where(nariz[None, :], perdida_media_por_hilada(nar)[:, None],
                           perdida_media_por_hilada(puerta)[:, None])
        espesor = np.where(hay_celda, trabajo - np.minimum(perdida, trabajo) + respaldo, np.nan)
        return s, espesor, nariz
    f = desgaste.fraccion_pared if desgaste is not None else 0.0
    espesor = np.where(hay_celda, trabajo * (1.0 - f) + respaldo, np.nan)
    return s, espesor, nariz


# ---------------------------------------------------------------------------
# Fondo
# ---------------------------------------------------------------------------

def _piso(planta, x, z, d, espesor_h5, retroceso: float = 0.0):
    """Cota del piso. Con ``retroceso`` (mm) cada pieza retrocede según su normal (decisión 5).

    Casquete: el radio crece en ``retroceso``. Talud del cuerpo, rampa, plataforma y talud
    de la nariz son superficies regladas: bajan ``retroceso · √(1 + pendiente²)``. Las
    uniones se toman como el máximo (valles) o el mínimo (aristas) de las piezas
    desplazadas, sin redondear las aristas.
    """
    fondo = planta["fondo"]
    yc = float(fondo["y_centro_esfera"]["valor"])
    rc = float(fondo["radio_cara_caliente"]["valor"]) + retroceso
    perfil_b = perfil_fondo(planta, "B-B")
    (r_talud, y_talud), (r_pared, y_tope) = perfil_b[-2], perfil_b[-1]
    m_cono = (y_tope - y_talud) / (r_pared - r_talud)
    r = np.hypot(x, z)
    esfera = yc - np.sqrt(np.maximum(rc * rc - r * r, 0.0))
    cono = y_talud + (r - r_talud) * m_cono - retroceso * math.hypot(1.0, m_cono)
    tope = y_tope - retroceso
    piso = np.where(r <= r_talud, esfera, np.minimum(cono, tope))

    # Rampa y plataforma: el perfil de A-A para X < x del pie de la rampa, extruido en Z.
    # El tramo «rampa» del perfil de A-A da el pie y el tope; más allá del tope, plataforma.
    rampa_a = next(t for t in fondo["perfil_a_a"]["tramos"] if t.get("nombre") == "rampa")
    (x_tope, _), (x_pie, y_pie) = rampa_a["desde"], rampa_a["hasta"]
    m_rampa = (y_tope - y_pie) / (x_tope - x_pie)  # negativa: sube hacia −X
    linea = y_pie + (x - x_pie) * m_rampa - retroceso * math.hypot(1.0, m_rampa)
    rampa = np.where(x <= x_pie, np.minimum(linea, tope), -np.inf)
    piso = np.maximum(piso, rampa)

    # Talud junto a la pared en la zona de la plataforma.
    t = planta["modelo_3d"]["fondo"]["talud_nariz"]
    m_talud = t["alto"] / t["ancho"]
    a_cara = d - espesor_h5
    talud = y_tope + m_talud * (t["ancho"] - a_cara) - retroceso * math.hypot(1.0, m_talud)
    talud = np.minimum(talud, y_tope + t["alto"] - retroceso)
    talud = np.where((x < t["x_desde"]) & (a_cara < t["ancho"]), talud, -np.inf)
    return np.maximum(piso, talud)


def y_piso_a_a(planta: dict, x, desgaste: Desgaste | None = None) -> np.ndarray:
    """Cota del piso en la sección A-A (Z = 0), con la misma función que la cavidad 3D."""
    x = np.atleast_1d(np.asarray(x, dtype=np.float64))
    z = np.zeros_like(x)
    d, s = distancia_y_s(planta, x, z)
    s_malla, espesor, _ = espesores_por_hilada(planta)  # el talud se apoya en la pared nueva
    idx = np.clip(np.rint(np.nan_to_num(s, nan=0.0) / (s_malla[1] - s_malla[0])).astype(int), 0, s_malla.size - 1)
    return _piso(planta, x, z, d, np.nan_to_num(espesor[4][idx], nan=0.0), retroceso_piso(planta, desgaste))


# ---------------------------------------------------------------------------
# Puerta
# ---------------------------------------------------------------------------

def _cara_puerta(planta, desgaste: Desgaste | None = None) -> tuple[np.ndarray, np.ndarray]:
    """(cota inferior, X de la cara) por tramos del lado puerta de A-A, de abajo arriba."""
    tramos = sorted(tramos_pared(planta, "puerta", desgaste), key=lambda t: t.y_inferior)
    y0 = np.array([t.y_inferior for t in tramos])
    xc = np.array([t.x_cara for t in tramos])
    return y0, xc


# ---------------------------------------------------------------------------
# Construcción
# ---------------------------------------------------------------------------

@dataclass
class _Malla:
    """Lo que no depende del desgaste: rejilla, distancias, posición s y piezas de pared por hilada."""

    planta: dict
    paso: float
    x: np.ndarray
    X: np.ndarray
    Z: np.ndarray
    d: np.ndarray
    idx: np.ndarray
    en_puerta: np.ndarray
    nariz_celda: np.ndarray
    espesor_nuevo: np.ndarray  # (21, ns), a refractario nuevo
    _hiladas: dict = field(default_factory=dict)  # h → (M, trabajo) por celda, perezoso
    _anillos: dict = field(default_factory=dict)  # h → estructura de conteo por columna, perezoso

    def hilada(self, h: int):
        """(M, trabajo) de la hilada h (0..20) en cada celda: M = d − espesor nuevo total."""
        if h not in self._hiladas:
            _, trabajo, respaldo, hay, _ = _componentes(self.planta)
            e0 = np.where(hay[h], trabajo[h] + respaldo[h], 0.0)[self.idx]
            t = np.where(hay[h], np.nan_to_num(trabajo[h], nan=0.0), 0.0)[self.idx]
            self._hiladas[h] = (self.d - e0, t)
        return self._hiladas[h]

    def hilada_rapida(self, h: int):
        """(M del cuerpo, M de la nariz, celda de pared utilizable) de la hilada h: cada celda con el M
        de su categoría y −∞ en la otra, y ``utilizable`` = dentro de la capa de trabajo o más
        adentro y fuera de la puerta. Sirve para contar con dos comparaciones por capa."""
        if ("r", h) not in self._hiladas:
            M, t = self.hilada(h)
            mb = np.where(self.nariz_celda, -np.inf, M)
            mn = np.where(self.nariz_celda, M, -np.inf)
            self._hiladas[("r", h)] = (mb, mn, (M >= -t) & ~self.en_puerta)
        return self._hiladas[("r", h)]

    def anillos(self, h: int):
        """Conteo por columna de X para la hilada h con pérdida L (mm) por categoría de columna.

        Devuelve (base[nx], claves_cuerpo, claves_nariz): ``base`` son las celdas de pared que ya
        están dentro sin desgaste (M ≥ 0); las claves ordenadas permiten contar, con una
        búsqueda, las del «anillo» (−trabajo ≤ M < 0) que entran al perder L mm.
        """
        if h not in self._anillos:
            M, t = self.hilada(h)
            fuera = ~self.en_puerta
            nx = self.x.size
            ix = np.broadcast_to(np.arange(nx)[:, None], M.shape)
            base = ((M >= 0.0) & fuera).sum(axis=1).astype(float)
            anillo = fuera & (M < 0.0) & (M >= -t)
            claves = []
            for categoria in (False, True):
                m = anillo & (self.nariz_celda == categoria)
                claves.append(np.sort(ix[m] * _K + (M[m] + _K / 2)))
            self._anillos[h] = (base, claves[0], claves[1])
        return self._anillos[h]


_K = 20000.0  # separación entre columnas en las claves ordenadas (M ∈ [−10 000, 10 000))
_CACHE_MALLAS: dict = {}


def _malla(planta: dict, paso: float) -> _Malla:
    clave = (id(planta), paso)
    hallada = _CACHE_MALLAS.get(clave)
    if hallada is not None and hallada.planta is planta:
        return hallada
    c = planta["coraza_en_planta"]
    x_min = float(c["x_nariz_extremo"]["valor"])
    x_max = float(c["radio_cuerpo"]["valor"])
    z_max = float(c["radio_cuerpo"]["valor"])
    x = np.arange(x_min + paso / 2, x_max, paso)
    z = np.arange(-z_max + paso / 2, z_max, paso)
    X, Z = np.meshgrid(x, z, indexing="ij")  # (nx, nz)
    d, s = distancia_y_s(planta, X, Z)
    s_malla, espesor_nuevo, _ = espesores_por_hilada(planta)
    idx = np.clip(np.rint(np.nan_to_num(s, nan=0.0) / (s_malla[1] - s_malla[0])).astype(int), 0, s_malla.size - 1)
    puerta = planta["modelo_3d"]["puerta"]
    en_puerta = (np.abs(Z) < puerta["media_anchura"]) & (X > 0)
    _, _, _, _, nariz = _componentes(planta)
    malla = _Malla(planta, paso, x, X, Z, d, idx, en_puerta, nariz[idx], espesor_nuevo)
    guardar(_CACHE_MALLAS, clave, malla, 2)
    return malla


def construir_cavidad(planta: dict, paso: float | None = None, y_max: float = 4000.0,
                      desgaste: Desgaste | None = None, directo: bool = False) -> Cavidad:
    """Discretiza la cavidad. ``y_max`` limita la malla por arriba (paneles sin altura conocida).

    ``desgaste`` aplica el estado de desgaste a paredes, umbral y piso: el % uniforme de la
    fase 3 o el perfil por línea de la fase 5. Con perfil, el cálculo por capa usa conteos
    ordenados por columna (``directo=True`` fuerza el cálculo celda a celda, que es la
    referencia con la que se prueba el rápido).
    """
    paso = float(paso or planta["modelo_3d"]["paso_malla"]["valor"])
    malla = _malla(planta, paso)
    x, X, Z, d, idx, en_puerta = malla.x, malla.X, malla.Z, malla.d, malla.idx, malla.en_puerta
    espesor_nuevo = malla.espesor_nuevo
    con_perfil = desgaste is not None and desgaste.perfil is not None
    _, espesor, _ = espesores_por_hilada(planta, desgaste=desgaste)
    s_malla = _componentes(planta)[0]

    y0_puerta, xc_puerta = _cara_puerta(planta, desgaste)
    x_umbral, y_umbral = float(xc_puerta[-1]), float(planta["puerta"]["y_umbral"]["valor"])
    if con_perfil:
        tramos_nuevos = sorted(tramos_pared(planta, "puerta"), key=lambda t: t.y_inferior)
        y0_puerta = np.array([t.y_inferior for t in tramos_nuevos])
        x_nuevo_puerta = np.array([t.x_cara for t in tramos_nuevos])
        trabajo_puerta = np.array([t.capa_de_trabajo.espesor for t in tramos_nuevos])

    # El talud de la nariz se apoya en la cara nueva de la hilada 5 (el apisonado no se
    # mueve con la pared); el piso retrocede según el desgaste de piso.
    piso = _piso(planta, X, Z, d, np.nan_to_num(espesor_nuevo[4][idx], nan=0.0), retroceso_piso(planta, desgaste))
    fondo_min = float(np.nanmin(piso[d >= 0]))
    y_base = float(planta["pared"]["y_base_hilada_1"]["valor"])
    alto = float(planta["pared"]["altura_de_hilada"]["valor"])
    y_inf = np.arange(math.floor(fondo_min / paso) * paso, y_max, paso)
    area = np.zeros((y_inf.size, x.size))
    celda = paso * paso

    def fila_puerta(yc: float, perdida: float | None = None) -> float:
        i = np.searchsorted(y0_puerta, yc, side="right") - 1
        if yc >= y_umbral:
            return x_umbral
        if perdida is None:
            return float(xc_puerta[max(i, 0)])
        # Con perfil por línea la cara de la puerta retrocede lo que pierde su línea (sin pasar
        # del espesor de la capa de trabajo del tramo).
        j = max(i, 0)
        return float(x_nuevo_puerta[j] + min(perdida, trabajo_puerta[j]))

    if con_perfil and not directo:
        _area_con_perfil(area, malla, desgaste.perfil, piso, y_inf, paso, y_base, alto, fila_puerta)
    elif con_perfil:
        _area_con_perfil_directa(area, malla, desgaste.perfil, piso, y_inf, paso, y_base, alto, fila_puerta)
    else:
        # Máscaras de pared por hilada (fuera de la puerta).
        dentro_hilada = []
        for h in range(N_HILADAS):
            e = espesor[h][idx]
            e = np.where(np.isnan(e), 0.0, e)  # sin celda: paneles a paño de la coraza
            dentro_hilada.append((d >= e) & ~en_puerta)
        dentro_paneles = (d >= 0) & ~en_puerta
        for k, y0 in enumerate(y_inf):
            yc = y0 + paso / 2
            h = int((yc - y_base) // alto) + 1
            if h < 1:
                mascara = dentro_hilada[0]
            elif h <= N_HILADAS:
                mascara = dentro_hilada[h - 1]
            else:
                mascara = dentro_paneles
            mascara = (mascara | (en_puerta & (X <= fila_puerta(yc)))) & (piso <= yc)
            area[k] = mascara.sum(axis=1) * celda

    # Tope del refractario a lo largo del contorno (suceso «fin del refractario»). Donde la
    # última hilada es menor que la 15 está el hueco de la puerta: allí manda el umbral.
    fin = planta["modelo_3d"]["y_fin_refractario"]
    s_c = s_malla[::10]
    esp_c = espesor[:, ::10]
    hay = ~np.isnan(esp_c)
    ultima = np.where(hay.any(axis=0), 20 - np.argmax(hay[::-1], axis=0), -1)  # índice 0..20
    y_fin = np.where(ultima >= 15, fin["columnas_de_nariz"], np.where(ultima == 14, fin["cuerpo"], np.nan))
    x_cara_c = np.array([
        posicion_en_planta(planta, float(sv), float(esp_c[u, i]) if u >= 0 else 0.0)[0]
        for i, (sv, u) in enumerate(zip(s_c, ultima))
    ])
    return Cavidad(paso, x, y_inf, area, y_fin, x_cara_c, x_umbral, y_umbral)


def _linea(y0: float, paso: float, n: int) -> int:
    return min(max(int(round(y0 / paso)), 0), n - 1)


def _hilada_de(yc: float, y_base: float, alto: float) -> int:
    return int((yc - y_base) // alto) + 1


def _area_con_perfil_directa(area, malla: _Malla, perfil, piso, y_inf, paso, y_base, alto, fila_puerta):
    """Referencia: capa por capa, celda a celda. Una celda de pared está dentro si
    d ≥ espesor nuevo total − min(pérdida de su línea y lado, espesor de trabajo)."""
    X, en_puerta = malla.X, malla.en_puerta
    puerta, nariz = perfil.arrays
    celda = paso * paso
    for k, y0 in enumerate(y_inf):
        yc = y0 + paso / 2
        h = _hilada_de(yc, y_base, alto)
        j = _linea(y0, paso, puerta.size)
        if h <= N_HILADAS:
            M, t = malla.hilada(max(h, 1) - 1)
            perdida = np.where(malla.nariz_celda, nariz[j], puerta[j])
            mascara = (M >= -np.minimum(perdida, t)) & ~en_puerta
        else:
            mascara = (malla.d >= 0) & ~en_puerta
        mascara = (mascara | (en_puerta & (X <= fila_puerta(yc, puerta[j])))) & (piso <= yc)
        area[k] = mascara.sum(axis=1) * celda


def _area_con_perfil(area, malla: _Malla, perfil, piso, y_inf, paso, y_base, alto, fila_puerta):
    """Igual que la referencia, pero por encima del tope del piso cuenta con búsquedas ordenadas
    por columna en vez de recorrer las celdas."""
    X, en_puerta, d = malla.X, malla.en_puerta, malla.d
    puerta, nariz = perfil.arrays
    celda = paso * paso
    nx = malla.x.size
    columnas = np.arange(nx) * _K + _K / 2
    piso_tope = float(max(np.max(piso[d >= 0]), np.max(piso[en_puerta])))
    n_puerta_z = en_puerta.sum(axis=1).astype(float)
    base_paneles = ((d >= 0) & ~en_puerta).sum(axis=1).astype(float)
    # Celdas de la puerta: pocas; se cuentan aparte.
    puerta_ix = np.broadcast_to(np.arange(nx)[:, None], X.shape)[en_puerta]
    puerta_x = X[en_puerta]
    piso_puerta = piso[en_puerta]
    for k, y0 in enumerate(y_inf):
        yc = y0 + paso / 2
        h = _hilada_de(yc, y_base, alto)
        j = _linea(y0, paso, puerta.size)
        if yc < piso_tope:
            ok_piso = piso <= yc
            if h <= N_HILADAS:
                mb, mn, utilizable = malla.hilada_rapida(max(h, 1) - 1)
                mascara = ((mb >= -puerta[j]) | (mn >= -nariz[j])) & utilizable & ok_piso
            else:
                mascara = (d >= 0) & ~en_puerta & ok_piso
            area[k] = mascara.sum(axis=1) * celda
            m = (puerta_x <= fila_puerta(yc, puerta[j])) & (piso_puerta <= yc)
            if m.any():
                area[k] += np.bincount(puerta_ix[m], minlength=nx) * celda
            continue
        if h <= N_HILADAS:
            base, claves_cuerpo, claves_nariz = malla.anillos(max(h, 1) - 1)
            cuenta = base.copy()
            for claves, perdida in ((claves_cuerpo, puerta[j]), (claves_nariz, nariz[j])):
                if claves.size and perdida > 0.0:
                    cuenta += np.searchsorted(claves, columnas, side="left") \
                        - np.searchsorted(claves, columnas - perdida, side="left")
        else:
            cuenta = base_paneles.copy()
        cuenta += np.where(malla.x <= fila_puerta(yc, puerta[j]), n_puerta_z, 0.0)
        area[k] = cuenta * celda
