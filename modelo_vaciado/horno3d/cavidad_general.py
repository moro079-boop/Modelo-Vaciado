"""Cavidad de las plantas de «solo niveles» (``"alcance": "niveles"``), construida desde su archivo de planta.

Es la geometría con que se calculan los libros volumen–altura de Danieli, Puebla y Fuchs (EAF-023). Devuelve el
mismo objeto ``Cavidad`` que consume ``lwd_eaf.niveles`` (``volumen``, ``y_eje_para_volumen``); no sirve para el
desgaste ni para la ventana, que siguen atados a la geometría de Largos Norte.

Cómo se arma (bloque ``cavidad_general`` del archivo de planta; **todas las reglas son supuestos**, ver el
documento ``docs/plantas-nuevas.md``):

* **Planta.** Contorno de la cara caliente a la altura de la escoria, como radio ``R(θ)`` desde el eje del horno
  (θ = 0 hacia la puerta, 180° hacia la nariz; simétrico respecto de A-A). Las paredes son verticales hasta
  ``y_max``, la altura hasta donde se midió la cavidad.
* **Fondo.** Hacia la puerta y los costados (X ≥ 0), cuenco de revolución ``Y = cuenco(r)`` con el perfil medido en el
  plano (el lado puerta de A-A, que coincide con C-C). Si la planta tiene nariz EBT, en la mitad de la piquera (X < 0) el
  piso pasa, según el ángulo, del cuenco (a 90°, el costado) a la rampa y la plataforma de A-A del lado de la nariz
  (a 180°, el eje): ``Y = (1 − w)·cuenco(min(r, R_cuerpo)) + w·nariz(r)``, ``w = (θ − 90°)/90°`` (EAF-032). Así el
  eje puerta–piquera reproduce A-A a los dos lados y el costado reproduce C-C, sin el escalón que dejaba el cuenco
  girado del lado de la nariz (hasta 500 mm, EAF-032). Fuera de los ejes el plano no dibuja el fondo: es un supuesto.
* **Ajuste.** ``Δ`` (desplazamiento vertical del piso, mm) y ``f`` (estiramiento radial del cuenco) calibran contra las
  marcas de nivel del plano (``lwd_eaf.cavidad_general.calibrar``). Entre EAF-032 y EAF-049 no se usaban (manda la geometría
  dibujada, Δ = 0, f = 1); **desde EAF-050 (decisión del usuario, 2026-11-04) Puebla, Fuchs y Pesquería abren calibradas**
  (``herramientas/libros_plantas.CALIBRADAS``) y Danieli y Colombia, dibujadas. La profundidad h se sigue midiendo desde el
  piso dibujado en el eje, como las profundidades que escribe el plano (Puebla: 520 mm a la marca de 65 t).

* **Puerta.** Escalones del umbral medidos en A-A (o B-B en Fuchs): cada fila de pieza larga tiene su cara interior
  a cierta X y el nicho entre la pared y esa cara cuenta como cavidad, en el ancho de la puerta. El derrame es por la
  arista interior de la fila de arriba (``x_umbral``, ``y_umbral``), igual que en Norte. **Interpretación por
  confirmar** (ver ``docs/plantas-nuevas.md``).
* **Desgaste de la pared (EAF-026).** La cara caliente retrocede, en todo el contorno y a toda la altura, el % pedido del
  espesor de trabajo que rotula el plano (bloque ``desgaste``), también en el nicho y el umbral de la puerta (como en Norte).
  La capa de trabajo es el ladrillo pegado a la cavidad (decisión del usuario, 2026-10-22). El anillo ganado sigue horizontal
  desde donde el piso toca la pared original (EAF-034).
* **Desgaste del piso (EAF-035).** La capa de trabajo del piso la fijó el usuario (Danieli: la masa apisonada; Puebla: el
  apisonado, la masa de abajo y el banqueo de la unión piso–pared; Fuchs: solo el apisonado) y su espesor es el mínimo medido en
  las secciones, perpendicular a la superficie (``desgaste.espesor_trabajo_piso``, ``herramientas/espesor_piso_plantas.py``). El
  piso retrocede **perpendicular a su superficie** (EAF-039, como Norte con su casquete): baja ``u / cos α`` según la pendiente local
  (``factor_normal``, acotado a 60°), dentro del contorno original; el contacto con la pared no se mueve (el banqueo se repone).
* **Fin del refractario.** Tope de la pared por sector: ``nariz`` (fuera del círculo del cuerpo), ``cuerpo`` y, en la
  puerta, el umbral. Por encima de lo medido las paredes se suponen verticales hasta el tope más alto (``y_max``).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .cavidad import Cavidad
from .desgaste import Desgaste, hiladas_de


@dataclass(frozen=True)
class Ajuste:
    delta_y: float = 0.0       # mm, desplazamiento vertical del piso (+ lo sube)
    estiramiento: float = 1.0  # f: el perfil del cuenco se estira radialmente (f > 1: laderas más abajo)


def leer_ajuste(planta: dict) -> Ajuste:
    """El ajuste del piso guardado en el archivo de planta (Δ = 0, f = 1 desde EAF-032: la geometría dibujada)."""
    c = planta.get("calibracion")
    if not c or c.get("delta_y") is None:
        return Ajuste()
    return Ajuste(float(c["delta_y"]["valor"]), float(c["estiramiento_cuenco"]["valor"]))


def texto_ajuste(planta: dict) -> str | None:
    """«calibrada con las marcas del plano (piso Δ = −55 mm)» si la planta abre calibrada (EAF-050); ``None`` si va dibujada."""
    c = planta.get("calibracion") or {}
    if not c.get("parametros_ajustados"):
        return None
    a = leer_ajuste(planta)
    partes = [f"piso Δ = {a.delta_y:+g} mm"] + ([f"cuenco f = {a.estiramiento:g}"] if a.estiramiento != 1.0 else [])
    return f"calibrada con las marcas del plano ({', '.join(partes)})"


def _g(planta: dict) -> dict:
    if planta.get("alcance") != "niveles" or "cavidad_general" not in planta:
        raise ValueError("la planta no trae el bloque «cavidad_general» (alcance «niveles»)")
    return planta["cavidad_general"]


def radio_contorno(planta: dict, theta_grados) -> np.ndarray:
    """R(θ) del contorno. Simétrico respecto de A-A por omisión; con ``"simetrico_en_z": false`` la tabla da 0°–360°."""
    c = _g(planta)["contorno"]
    th = np.asarray(theta_grados, dtype=np.float64)
    if c.get("simetrico_en_z", True):
        return np.interp(np.abs(((th + 180.0) % 360.0) - 180.0), c["angulos_grados"], c["radios"])
    ang, rad = np.asarray(c["angulos_grados"], float), np.asarray(c["radios"], float)
    return np.interp(np.mod(th, 360.0), np.concatenate([ang - 360.0, ang, ang + 360.0]), np.tile(rad, 3))


def _extrapolar(perfil_r: np.ndarray, perfil_y: np.ndarray, r: np.ndarray) -> np.ndarray:
    """Interpola y, pasado el último punto, sigue con la pendiente del último tramo (al menos 1)."""
    y = np.interp(r, perfil_r, perfil_y)
    pend = max((perfil_y[-1] - perfil_y[-2]) / (perfil_r[-1] - perfil_r[-2]), 1.0)
    return y + np.where(r > perfil_r[-1], (r - perfil_r[-1]) * pend, 0.0)


def _piso_por_direcciones(direcciones: list, r: np.ndarray, theta_grados: np.ndarray, ajuste: Ajuste) -> np.ndarray:
    """Piso medido en varias direcciones (θ = 0° hacia la puerta, 180° hacia la piquera; simétrico respecto de X),
    mezclado linealmente en el ángulo entre direcciones vecinas."""
    angulos = np.array([d["theta_grados"] for d in direcciones], dtype=float)
    th = np.abs(((theta_grados + 180.0) % 360.0) - 180.0)
    y = np.zeros_like(r)
    for j, d in enumerate(direcciones):
        peso = np.interp(th, angulos, np.eye(len(angulos))[j])
        yj = _extrapolar(np.asarray(d["r"], float), np.asarray(d["y"], float), r / ajuste.estiramiento)
        y = y + peso * yj
    return y + ajuste.delta_y


def distancia_estadio(semilargo: float, X, Z) -> np.ndarray:
    """Distancia (mm) de (X, Z) al segmento central del estadio, de X = −semilargo a X = +semilargo sobre Z = 0."""
    return np.hypot(np.maximum(np.abs(np.asarray(X, float)) - semilargo, 0.0), np.asarray(Z, float))


def _piso_estadio(f: dict, X: np.ndarray, Z: np.ndarray, ajuste: Ajuste) -> np.ndarray:
    """Piso de un horno en forma de estadio (Colombia, EAF-040): dos semicírculos con centro en X = ±semilargo unidos por tramos
    rectos. La cota es un solo perfil medido en la sección transversal (B-B) en función de la distancia al segmento central, que
    en esa sección es |Z|; la sección longitudinal (A-A) lo confirma. ``frente_piquera`` (opcional): en la franja |Z| ≤ semiancho
    del lado X < 0 y desde el primer punto del perfil hacia afuera, el piso es el más alto entre el estadio y el perfil medido en A-A
    hacia la piquera (en función de |X|), que es donde el bloque de la piquera corta el talud."""
    e = f["estadio"]
    perfil = e["perfil"]
    d = distancia_estadio(float(e["semilargo"]["valor"]), X, Z)
    y = _extrapolar(np.asarray(perfil["d"], float), np.asarray(perfil["y"], float), d / ajuste.estiramiento)
    frente = f.get("frente_piquera")
    if frente is not None:
        g = frente["perfil"]
        yf = _extrapolar(np.asarray(g["x_abs"], float), np.asarray(g["y"], float), np.abs(X) / ajuste.estiramiento)
        desde = float(frente.get("desde", g["x_abs"][0]))      # el retrocedido (EAF-061) trae su perfil desde el eje
        en = (np.asarray(X) < 0.0) & (np.abs(Z) <= float(frente["semiancho"]["valor"])) & (np.abs(X) >= desde)
        y = np.where(en, np.maximum(y, yf), y)
    return y + ajuste.delta_y


def piso(planta: dict, X: np.ndarray, Z: np.ndarray, ajuste: Ajuste) -> np.ndarray:
    """Cota del piso en cada punto (X, Z) dentro del contorno original (el anillo de la pared gastada: ``piso_del_anillo``).
    Con ``piso.bancos`` (Siderca, EAF-058), por encima de eso, los bancos de apisonado contra la pared: ``_con_bancos``."""
    f = _g(planta)["piso"]
    y = _piso_base(f, X, Z, ajuste)
    return _con_bancos(f, X, Z, y, ajuste) if f.get("bancos") else y


def _con_bancos(f: dict, X, Z, y: np.ndarray, ajuste: Ajuste, u_banco: float = 0.0) -> np.ndarray:
    """Bancos de la masa apisonada pegados a la pared (Siderca, EAF-058): cada banco es una meseta horizontal a ``y_tope`` desde su
    cara (radio ``radios`` en función del ángulo, simétrico respecto de A-A) hasta la pared. El piso es el más alto entre el de abajo
    y los bancos que cubren el punto. Donde el banco no llega (la nariz), su radio es muy grande y no cubre nada. Se desplaza con Δ,
    como el resto del piso. ``u_banco`` (EAF-059): mm que retrocede el banco perpendicular a sus caras: el tope baja eso y la cara
    se aparta eso hacia la pared; cuando la cara llega a la pared, el banco ya no está."""
    X, Z = np.asarray(X, float), np.asarray(Z, float)
    r = np.hypot(X, Z)
    th = np.abs(np.degrees(np.arctan2(Z, X)))
    for b in f["bancos"]["lista"]:
        rb = np.interp(th, b["angulos_grados"], b["radios"]) + u_banco
        y = np.where(r >= rb, np.maximum(y, float(b["y_tope"]) + ajuste.delta_y - u_banco), y)
    return y


def multiplicador_bancos(planta: dict) -> float:
    """Cuántas veces más rápido que el piso se gastan los bancos del hogar (``piso.bancos.multiplicador_desgaste``; 1 si la planta
    no lo dice o no tiene bancos). Siderca: 5, dato del usuario (EAF-059)."""
    b = _g(planta)["piso"].get("bancos") or {}
    return float((b.get("multiplicador_desgaste") or {}).get("valor", 1.0))


def piso_gastado(planta: dict, X, Z, ajuste: Ajuste, u: float, h: float = 10.0) -> np.ndarray:
    """Cota del piso con ``u`` mm de retroceso perpendicular a su superficie (EAF-039), dentro del contorno original: el piso de
    abajo con sus perfiles retrocedidos ``u`` mm (``_piso_retrocedido``, EAF-061). Con bancos (EAF-059) cada banco retrocede
    ``multiplicador · u`` normal a sus propias caras (la pendiente del banco no entra en el piso de abajo). ``h`` no se usa
    (era el paso de la pendiente local hasta EAF-060); se conserva por compatibilidad."""
    X, Z = np.asarray(X, float), np.asarray(Z, float)
    if u <= 0.0:
        return piso(planta, X, Z, ajuste)
    f = _g(planta)["piso"]
    base = _base_gastada(planta, f, X, Z, ajuste, u)
    if not f.get("bancos"):
        return base
    return _con_bancos(f, X, Z, base, ajuste, multiplicador_bancos(planta) * u)


def _base_gastada(planta: dict, f: dict, X, Z, ajuste: Ajuste, u: float) -> np.ndarray:
    """El piso de abajo (sin bancos) retrocedido ``u`` mm perpendicular a su superficie (EAF-061), sin bajar en ningún punto más de
    ``FACTOR_NORMAL_MAX · u`` (la cota de 60° de EAF-039: las caras casi verticales del piso no retroceden de lado como si fueran
    pared). Las dos son continuas: el máximo de las dos no deja escalones."""
    retrocedido = _piso_base(_piso_retrocedido(planta, u, ajuste), X, Z, ajuste)
    return np.maximum(retrocedido, _piso_base(f, X, Z, ajuste) - FACTOR_NORMAL_MAX * u)


PASO_RETROCESO = 5.0     # mm: muestreo de los perfiles retrocedidos y de los desplazamientos de la envolvente (EAF-061)


def retroceder_perfil(r, y, u: float, r_hasta: float, escala: float = 1.0, paso: float = PASO_RETROCESO) -> tuple[np.ndarray, np.ndarray]:
    """Perfil del piso ``y(r)`` retrocedido ``u`` mm **perpendicular a su superficie** (EAF-061): la envolvente inferior de los
    círculos de radio ``u`` con centro en el perfil, ``min_s y(s) − √(u² − (s − r)²)`` con ``|s − r| ≤ u``. Es la cara del
    refractario que queda a ``u`` mm de la original, medidos en la normal; en lo plano baja ``u``, en una rampa de pendiente α
    baja ``u / cos α`` y en un quiebre (donde la rampa se encuentra con lo plano) sigue el arco, sin el escalón ni el valle que
    dejaba bajar cada punto según su pendiente local (``factor_normal``, EAF-039 a EAF-060).

    ``r`` y ``y``: el perfil como lo lee ``_extrapolar`` (pasado el último punto sigue su pendiente); ``escala``: el estiramiento
    radial con que se evalúa (la distancia real es ``escala · r``). El perfil se toma par (el otro lado del eje es el mismo) y se
    devuelve, en las mismas unidades de ``r``, muestreado cada ``paso`` mm reales de 0 a ``r_hasta``."""
    rp, yp = np.asarray(r, float), np.asarray(y, float)
    R = np.arange(0.0, float(r_hasta) + paso, paso)
    n = max(1, int(math.ceil(u / paso)))
    salida = np.full(R.size, np.inf)
    for d in np.linspace(-u, u, 2 * n + 1):
        salida = np.minimum(salida, _extrapolar(rp, yp, np.abs(R + d) / escala) - math.sqrt(max(u * u - d * d, 0.0)))
    return R / escala, salida


_CACHE_RETROCEDIDO: dict = {}


def _piso_retrocedido(planta: dict, u: float, ajuste: Ajuste) -> dict:
    """El bloque ``piso`` con cada perfil retrocedido ``u`` mm perpendicular a su superficie (``retroceder_perfil``, EAF-061): el
    cuenco y los perfiles por dirección (de revolución: su normal está en el plano del perfil, así que retroceder el perfil es
    retroceder la superficie), el estadio (función de la distancia al segmento central: igual), la rampa de la nariz y el frente
    de la piquera. Donde ``_piso_base`` mezcla dos perfiles (la mitad de la piquera) o toma el más alto (el frente de la piquera),
    mezcla los retrocedidos: la pendiente a lo largo del ángulo no entra (es pequeña frente a la radial). Se guarda por planta,
    ``u`` y ajuste."""
    clave = (id(planta), round(float(u), 6), ajuste)
    hallado = _CACHE_RETROCEDIDO.get(clave)
    if hallado is not None and hallado[0] is planta:
        return hallado[1]
    f = _g(planta)["piso"]
    hasta = float(max(_g(planta)["contorno"]["radios"])) + 2.0 * PASO_RETROCESO
    est = ajuste.estiramiento

    def perfil(bloque: dict, clave_r: str, escala: float) -> dict:
        r, y = retroceder_perfil(bloque[clave_r], bloque["y"], u, hasta, escala)
        return {**bloque, clave_r: r, "y": y}

    nuevo = dict(f)
    if "direcciones" in f:
        nuevo["direcciones"] = [perfil(d, "r", est) for d in f["direcciones"]]
    elif "estadio" in f:
        e = f["estadio"]
        nuevo["estadio"] = {**e, "perfil": perfil(e["perfil"], "d", est)}
        if f.get("frente_piquera") is not None:
            fr = f["frente_piquera"]
            nuevo["frente_piquera"] = {**fr, "perfil": perfil(fr["perfil"], "x_abs", est),
                                       "desde": float(fr["perfil"]["x_abs"][0])}
    else:
        nuevo["cuenco"] = perfil(f["cuenco"], "r", est)
        if f.get("nariz") is not None:
            nuevo["nariz"] = perfil(f["nariz"], "x_abs", 1.0)
    if len(_CACHE_RETROCEDIDO) >= 16:
        _CACHE_RETROCEDIDO.pop(next(iter(_CACHE_RETROCEDIDO)))
    _CACHE_RETROCEDIDO[clave] = (planta, nuevo)
    return nuevo


def _piso_base(f: dict, X: np.ndarray, Z: np.ndarray, ajuste: Ajuste) -> np.ndarray:
    r = np.hypot(X, Z)
    if "direcciones" in f:
        return _piso_por_direcciones(f["direcciones"], r, np.degrees(np.arctan2(Z, X)), ajuste)
    if "estadio" in f:
        return _piso_estadio(f, X, Z, ajuste)
    cuenco = f["cuenco"]
    cr, cy = np.asarray(cuenco["r"], float), np.asarray(cuenco["y"], float)
    y = _extrapolar(cr, cy, r / ajuste.estiramiento)
    nariz = f.get("nariz")
    if nariz is None:
        return y + ajuste.delta_y
    # mitad de la piquera: del cuenco (costado, 90°) a la rampa de A-A (eje, 180°), mezclados por el ángulo
    r_cuerpo = float(nariz["radio_cuerpo"])
    y_costado = _extrapolar(cr, cy, np.minimum(r, r_cuerpo) / ajuste.estiramiento)
    y_eje = _extrapolar(np.asarray(nariz["x_abs"], float), np.asarray(nariz["y"], float), r)
    w = np.clip((np.degrees(np.arctan2(np.abs(Z), X)) - 90.0) / 90.0, 0.0, 1.0)
    return np.where(X >= 0.0, y, (1.0 - w) * y_costado + w * y_eje) + ajuste.delta_y


def piso_del_anillo(planta: dict, X: np.ndarray, Z: np.ndarray, ajuste: Ajuste, u: float = 0.0) -> np.ndarray:
    """Piso del anillo que gana la pared al gastarse (fuera del contorno original): la cota donde el piso toca la pared original en
    ese mismo ángulo, horizontal hacia afuera (EAF-034). Es la regla del desgaste: la pared se expone desde ese contacto hacia
    arriba (``trabajo_por_linea``), y lo que queda por debajo lo cubre el piso, que no se gasta; así el anillo no excava un foso ni
    levanta una rampa. (Hasta EAF-033 seguía el cuenco extrapolado, que del lado de la piquera subía cientos de mm.) Con bancos
    (EAF-059) y ``u`` mm de piso perdido, el contacto es el del piso gastado: baja cuando baja el banco."""
    X, Z = np.asarray(X, float), np.asarray(Z, float)
    th = np.arctan2(Z, X)
    R0 = radio_contorno(planta, np.degrees(th))
    if u > 0.0 and _g(planta)["piso"].get("bancos"):   # el contacto baja con el banco gastado (EAF-059): justo dentro de la pared
        return piso_gastado(planta, (R0 - 1.0) * np.cos(th), (R0 - 1.0) * np.sin(th), ajuste, u)
    return piso(planta, R0 * np.cos(th), R0 * np.sin(th), ajuste)


_CACHE_COMPONENTES: dict = {}


def _componentes(planta: dict) -> dict:
    clave = id(planta)
    hallado = _CACHE_COMPONENTES.get(clave)
    if hallado is not None and hallado[0] is planta:
        return hallado[1]
    c = componentes_desarrollo(planta)
    if len(_CACHE_COMPONENTES) >= 8:
        _CACHE_COMPONENTES.pop(next(iter(_CACHE_COMPONENTES)))
    _CACHE_COMPONENTES[clave] = (planta, c)
    return c


def _por_hilada_mas_cercana(comp: dict, n: int) -> np.ndarray:
    """Vector (índice 0 = hilada 1) con el valor de la hilada; donde no hay, el de la hilada más cercana."""
    h = np.arange(1, n + 1)
    claves = np.array(sorted(comp))
    cerca = claves[np.abs(h[:, None] - claves[None, :]).argmin(axis=1)]
    return np.array([comp[int(k)] for k in cerca], dtype=object)


def espesor_trabajo_pared(planta: dict, y, lado: str | None = None) -> np.ndarray:
    """Espesor de la capa de trabajo de la pared (mm) a la altura ``y``.

    Con ``lado`` («a» puerta/cuerpo, «b» nariz) y la transcripción del ``desarrollo``: el **mínimo de las columnas** de ese lado en
    la hilada de ``y`` (como en Norte: la primera que se agota). Sin ``lado`` o sin desarrollo: la tabla ``desgaste.espesor_trabajo_pared``
    (el rótulo del plano en A-A). Fuera de las hiladas, el de la hilada más cercana."""
    y = np.asarray(y, dtype=np.float64)
    if lado is not None and "desarrollo" in planta:
        comp = _componentes(planta)["nariz" if lado in ("b", "nariz") else "puerta"]
        n, y_base, alto = hiladas_de(planta)
        espesores = np.array([v[1] for v in _por_hilada_mas_cercana(comp, n)], dtype=float)
        h = np.clip(np.floor((y - y_base) / alto).astype(int), 0, n - 1)
        return espesores[h]
    d = planta.get("desgaste", {}).get("espesor_trabajo_pared")
    if not d:
        raise ValueError("la planta no trae el espesor de trabajo de la pared (bloque «desgaste»)")
    tramos = sorted(d["lista"], key=lambda t: t["y_inferior"])
    e = np.full(y.shape, float(tramos[0]["espesor"]))
    for t in tramos[1:]:
        e = np.where(y >= float(t["y_inferior"]), float(t["espesor"]), e)
    return e


def material_por_linea(planta: dict, lado: str, n_lineas: int = 450, paso: float = 10.0) -> list:
    """Material de la capa de trabajo en cada línea de 10 mm de un lado («puerta» o «nariz»): el dominante de la hilada en el
    ``desarrollo`` si la planta lo trae; si no, los tramos de ``desgaste.materiales_pared`` (lo leído en A-A)."""
    n, y_base, alto = hiladas_de(planta)
    salida: list = [None] * n_lineas
    if "desarrollo" in planta:
        comp = _componentes(planta)[lado]
        for h, (material, _e) in comp.items():
            lo = int(round((y_base + alto * (h - 1)) / paso))
            hi = int(round((y_base + alto * h) / paso))
            for j in range(max(lo, 0), min(hi, n_lineas)):
                salida[j] = material
        return salida
    for tramo in planta["desgaste"]["materiales_pared"][lado]:
        h0, h1 = tramo["hiladas"]
        lo = int(round((y_base + alto * (h0 - 1)) / paso))
        hi = int(round((y_base + alto * h1) / paso))
        for j in range(max(lo, 0), min(hi, n_lineas)):
            salida[j] = tramo["material"]
    return salida


def _lado_b(planta: dict, X, R0):
    """Celdas (o puntos del contorno) del lado «nariz» de la ley de desgaste: el lóbulo de la nariz (fuera del círculo del cuerpo)
    si la planta tiene nariz; si no, la mitad X < 0, el lado de la piquera (supuesto, ``docs/plantas-nuevas.md`` §8)."""
    nariz = _g(planta)["piso"].get("nariz")
    if nariz is None:
        return np.asarray(X) < 0.0
    return (np.asarray(X) < 0.0) & (np.asarray(R0) > float(nariz["radio_cuerpo"]) + 5.0)


def trabajo_por_linea(planta: dict, n_lineas: int = 450, paso: float = 10.0) -> tuple[np.ndarray, np.ndarray]:
    """Capa de trabajo (mm) de cada línea de 10 mm, lado puerta/cuerpo y lado nariz: el espesor rotulado en el plano donde la
    pared está expuesta y 0 donde no hay pared o la cubre el piso. La pared queda expuesta desde donde el piso toca su
    cara (en la puerta para el lado puerta; en la nariz para el lado nariz) hasta el fin del refractario del sector; el piso se
    supone quieto (no hay dato de su desgaste), así que ese contacto no se mueve. El motor tiene ``n_lineas`` líneas de 10 mm
    (450: Y < 4 500; Danieli llega a 4 265 y Fuchs a 4 389)."""
    g = _g(planta)
    ajuste = leer_ajuste(planta)
    y = (np.arange(n_lineas) + 0.5) * paso
    e_a, e_b = espesor_trabajo_pared(planta, y, "a"), espesor_trabajo_pared(planta, y, "b")
    fin = g["fin_refractario"]
    tope_a = float(fin["cuerpo"]["valor"])
    tope_b = float(fin["nariz"]["valor"]) if "nariz" in fin else tope_a
    r_a, r_b = float(radio_contorno(planta, 0.0)), float(radio_contorno(planta, 180.0))
    contacto_a = float(piso(planta, np.array([r_a]), np.array([0.0]), ajuste)[0])
    tabla = contacto_por_piso(planta)
    if tabla is not None:                         # el contacto más bajo al que pueden llegar los bancos gastados con el piso (EAF-059)
        contacto_a = min(tabla[1])
    contacto_b = float(piso(planta, np.array([-r_b]), np.array([0.0]), ajuste)[0])
    n, y_base, alto = hiladas_de(planta)
    y_fin = y_base + n * alto
    a = np.where((y >= max(contacto_a, y_base)) & (y < min(tope_a, y_fin)), e_a, 0.0)
    b = np.where((y >= max(contacto_b, y_base)) & (y < min(tope_b, y_fin)), e_b, 0.0)
    return a, b


_CACHE_CONTACTO: dict = {}


def contacto_por_piso(planta: dict, paso_u: float = 1.0) -> tuple | None:
    """(piso perdido, altura del contacto piso–pared del lado puerta/cuerpo) en tablas, para la ley (EAF-059): solo si la planta
    tiene bancos que se gastan con el piso; el contacto baja con ellos y deja la pared al descubierto. ``None`` sin bancos. Es
    ``piso_gastado`` justo dentro de la pared a 0°, para cada pérdida de 0 al espesor de trabajo del piso."""
    clave = (id(planta), paso_u)
    hallado = _CACHE_CONTACTO.get(clave)
    if hallado is not None and hallado[0] is planta:
        return hallado[1]
    f = _g(planta)["piso"]
    if not f.get("bancos") or not tiene_desgaste_de_piso(planta):
        salida = None
    else:
        ajuste = leer_ajuste(planta)
        X, Z = np.array([float(radio_contorno(planta, 0.0)) - 1.0]), np.array([0.0])
        u = np.arange(0.0, espesor_trabajo_piso(planta) + paso_u, paso_u)
        y = np.array([float(_base_gastada(planta, f, X, Z, ajuste, float(v))[0]) if v > 0.0
                      else float(_piso_base(f, X, Z, ajuste)[0]) for v in u])      # perpendicular a la superficie (EAF-061)
        m = multiplicador_bancos(planta)
        for b in f["bancos"]["lista"]:            # como _con_bancos, en el punto fijo y para todas las pérdidas a la vez
            rb = float(np.interp(0.0, b["angulos_grados"], b["radios"])) + m * u
            y = np.where(X[0] >= rb, np.maximum(y, float(b["y_tope"]) + ajuste.delta_y - m * u), y)
        salida = (tuple(float(v) for v in u), tuple(float(v) for v in y))
    if len(_CACHE_CONTACTO) >= 8:
        _CACHE_CONTACTO.pop(next(iter(_CACHE_CONTACTO)))
    _CACHE_CONTACTO[clave] = (planta, salida)
    return salida


def _es_marco(z: dict) -> bool:
    """Zona del marco de la puerta (piezas «70/0», P7, P9, V3L-100) o bloque de jamba «35/0» junto a ella (Puebla; supuesto): no
    es pared del cuerpo ni de la nariz, y no entra en el mínimo del espesor ni en el material dominante."""
    return (z.get("serie") is None or "marco" in z.get("lugar", "") or "puerta, extremo" in z.get("lugar", "")
            or "35/0" in z.get("rotulos", []))


def componentes_desarrollo(planta: dict) -> dict:
    """De ``desarrollo`` (la transcripción del plano): por hilada y lado, el **material dominante** y el **espesor mínimo** de la
    capa de trabajo. Mismo criterio que Norte: el lado «nariz» son las columnas del sector de la nariz y el lado «puerta» todo lo
    demás (el cuerpo y las uniones); el espesor es el mínimo de las columnas (el primero que se agota) y el material, el que
    cubre más ancho del desarrollo. Las zonas del marco de la puerta no cuentan. Después se aplican las ``excepciones`` de
    ``desgaste.espesor_trabajo_pared`` (Fuchs: 500 mm en las hiladas 24–28 del lado puerta, decisión del usuario, EAF-036). Devuelve
    ``{lado: {hilada: (material, espesor_mm)}}``; una hilada sin columnas en ese lado no aparece (Puebla: la hilada 1 de la nariz).
    """
    des = planta["desarrollo"]
    series = {k: float(v) for k, v in des["series"].items() if k not in ("estado", "nota")}
    sectores = [(float(s["s"][0]), float(s["s"][1]), str(s.get("arco", "")).startswith("nariz")) for s in des["sectores"]]
    ancho: dict = {}
    minimo: dict = {}
    for z in des["zonas"]:
        if _es_marco(z):
            continue
        trabajo = series[str(z["serie"])]
        for h, s0, s1 in z["celdas"]:
            for a, b, es_nariz in sectores:
                largo = min(s1, b) - max(s0, a)
                if largo <= 0:
                    continue
                lado = "nariz" if es_nariz else "puerta"
                ancho[(lado, int(h), z["material"])] = ancho.get((lado, int(h), z["material"]), 0.0) + largo
                minimo[(lado, int(h))] = min(minimo.get((lado, int(h)), trabajo), trabajo)
    salida: dict = {"puerta": {}, "nariz": {}}
    for (lado, h, material), largo in ancho.items():
        actual = salida[lado].get(h)
        if actual is None or largo > ancho[(lado, h, actual[0])]:
            salida[lado][h] = (material, minimo[(lado, h)])
    if not salida["nariz"]:                   # Fuchs: el plano no distingue una nariz; los dos lados tienen las mismas columnas
        salida["nariz"] = dict(salida["puerta"])
    # excepciones declaradas en el archivo (decisión del usuario): un espesor de trabajo distinto en unas hiladas de un lado
    for ex in planta.get("desgaste", {}).get("espesor_trabajo_pared", {}).get("excepciones", []):
        lado = "nariz" if ex["lado"] in ("b", "nariz") else "puerta"
        h0, h1 = ex["hiladas"]
        for h in range(int(h0), int(h1) + 1):
            if h in salida[lado]:
                salida[lado][h] = (salida[lado][h][0], float(ex["espesor"]))
    return salida


def topes_en_el_eje(planta: dict) -> tuple[float, float]:
    """(Y del tope de la pared del lado puerta, del lado piquera) en el eje: el umbral en la puerta (si la planta lo trae) y el fin
    del refractario de la nariz (o del cuerpo si no hay nariz) en la piquera. Por encima, en el eje, no hay pared dibujada."""
    g = _g(planta)
    fin = g["fin_refractario"]
    cuerpo = float(fin["cuerpo"]["valor"])
    puerta = float(g["puerta"]["y_umbral"]["valor"]) if g.get("puerta") else cuerpo
    return puerta, float(fin["nariz"]["valor"]) if "nariz" in fin else cuerpo


def contorno_en_el_eje(planta: dict, desgaste: Desgaste | None = None, paso: float = 10.0) -> np.ndarray:
    """Contorno de la cavidad del modelo en el plano del eje puerta–piquera (Z = 0): del tope de la cara de la nariz, por el piso, al
    tope de la cara de la puerta (el umbral; ``topes_en_el_eje``). Con ``desgaste`` (solo pared), las caras retroceden. Puntos (X, Y) en mm; para las figuras."""
    g = _g(planta)
    aj = leer_ajuste(planta)
    y0, y_max = float(g["y_fondo_medido"]["valor"]), float(g["y_max"]["valor"])
    ys = np.arange(y0, y_max + paso, paso)
    r_a, r_b = float(radio_contorno(planta, 0.0)), float(radio_contorno(planta, 180.0))
    xa = r_a + retroceso_pared(planta, desgaste, ys, "a")
    xb = -(r_b + retroceso_pared(planta, desgaste, ys, "b"))
    x = np.arange(xb[0], xa[0] + paso, paso)
    piso_x = piso(planta, x, np.zeros_like(x), aj)
    tope_a, tope_b = topes_en_el_eje(planta)
    ka = (ys >= piso_x[-1]) & (ys <= tope_a)                         # las paredes, desde donde las toca el piso hasta su tope
    kb = (ys >= piso_x[0]) & (ys <= tope_b)
    return np.vstack([np.column_stack([xb[kb][::-1], ys[kb][::-1]]), np.column_stack([x, piso_x]),
                      np.column_stack([xa[ka], ys[ka]])])


def retroceso_pared(planta: dict, desgaste: Desgaste | None, y, lado: str = "a") -> np.ndarray:
    """mm que retrocede la cara caliente de la pared a la altura ``y`` en el lado ``a`` (puerta/cuerpo) o ``b`` (nariz).

    ``Desgaste`` por %: ese % del espesor de trabajo de cada tramo, igual en los dos lados. Con ``perfil`` (la campaña): los mm que
    perdió la línea, sin pasar de su capa de trabajo (la de seguridad no se erosiona en la cavidad, como en Norte). El piso va
    aparte (``retroceso_piso``).
    """
    y = np.asarray(y, dtype=np.float64)
    if desgaste is None:
        return np.zeros_like(y)
    if desgaste.perfil is not None:
        es_a = lado in ("a", "puerta")
        perdida = desgaste.perfil.perdida("puerta" if es_a else "nariz")
        trabajo = trabajo_por_linea(planta, perdida.size)[0 if es_a else 1]
        j = np.clip(np.floor(y / 10.0).astype(int), 0, perdida.size - 1)
        arriba = y >= perdida.size * 10.0
        return np.where(arriba, 0.0, np.minimum(perdida[j], trabajo[j]))
    if desgaste.es_nuevo:
        return np.zeros_like(y)
    return desgaste.fraccion_pared * espesor_trabajo_pared(planta, y, "a" if lado in ("a", "puerta") else "b")


def espesor_trabajo_piso(planta: dict) -> float:
    """Espesor vertical (mm) de la capa de trabajo del piso: el mínimo medido en las secciones (EAF-035,
    ``herramientas/espesor_piso_plantas.py``). ``ValueError`` si la planta no lo trae (el piso no se puede desgastar)."""
    d = planta.get("desgaste", {}).get("espesor_trabajo_piso") or {}
    if d.get("valor") is None:
        raise ValueError("esta planta no tiene el espesor de trabajo del piso: el piso no se puede desgastar")
    return float(d["valor"])


def tiene_desgaste_de_piso(planta: dict) -> bool:
    """Si la planta de solo niveles trae el espesor de trabajo del piso (las tres desde EAF-035)."""
    return (planta.get("desgaste", {}).get("espesor_trabajo_piso") or {}).get("valor") is not None


def retroceso_piso(planta: dict, desgaste: Desgaste | None) -> float:
    """mm que retrocede el piso **perpendicular a su superficie**, igual en todo el fondo dentro del contorno original (EAF-039; como
    en Norte, que lo hace normal al casquete): en cada punto el piso baja este valor por ``factor_normal``. Por %: ese % del espesor
    de trabajo; con ``perfil`` (la campaña): lo perdido, sin pasar de la capa de trabajo."""
    if desgaste is None:
        return 0.0
    perdido = desgaste.perfil.piso if desgaste.perfil is not None else desgaste.fraccion_piso * (espesor_trabajo_piso(planta) if desgaste.piso else 0.0)
    return min(float(perdido), espesor_trabajo_piso(planta)) if perdido > 0.0 else 0.0


FACTOR_NORMAL_MAX = 2.0     # el retroceso normal baja el piso u / cos α; se acota a 60° (en las caras casi verticales no es un piso)


def factor_normal(planta: dict, X, Z, ajuste: Ajuste, h: float = 10.0) -> np.ndarray:
    """Cuánto baja el piso por cada mm de retroceso **perpendicular a su superficie** (EAF-039): 1 / cos α = √(1 + |∇Y|²), con la
    pendiente α de la cara caliente del piso en (X, Z) por diferencias centradas de ``h`` mm; acotado a ``FACTOR_NORMAL_MAX``.
    En lo plano vale 1; en una rampa de 40°, 1.31; de 50°, 1.56."""
    return _factor_normal_de(lambda a, b: piso(planta, a, b, ajuste), X, Z, h)


def _factor_normal_de(cota, X, Z, h: float) -> np.ndarray:
    X, Z = np.asarray(X, float), np.asarray(Z, float)
    gx = (cota(X + h, Z) - cota(X - h, Z)) / (2.0 * h)
    gz = (cota(X, Z + h) - cota(X, Z - h)) / (2.0 * h)
    return np.minimum(np.sqrt(1.0 + gx * gx + gz * gz), FACTOR_NORMAL_MAX)


def _areas_de_piso(F: np.ndarray, columnas: np.ndarray, y0: float, n_capas: int, n_columnas: int, paso: float) -> np.ndarray:
    """Área (mm²) por capa [y0 + k·paso, + paso] y por columna X de las celdas cuyo piso ``F`` queda por debajo, en una pasada: una celda
    llena entera las capas de arriba de su capa y en la suya la fracción que queda sobre el piso. Es lo mismo que recorrer las capas
    con ``clip((y + paso − F) / paso, 0, 1)``, pero en O(celdas)."""
    t = (F - y0) / paso
    j = np.floor(t).astype(int)
    parte = 1.0 - (t - j)
    debajo = j < 0                               # piso bajo la primera capa: llena todas
    j = np.where(debajo, 0, j)
    parte = np.where(debajo, 1.0, parte)
    usar = j < n_capas
    cuenta = np.zeros((n_capas + 1, n_columnas))
    fraccion = np.zeros((n_capas, n_columnas))
    np.add.at(cuenta, (j[usar] + 1, columnas[usar]), 1.0)
    np.add.at(fraccion, (j[usar], columnas[usar]), parte[usar])
    llenas = np.cumsum(cuenta, axis=0)[:n_capas]
    return (llenas + fraccion) * paso * paso


def _rejilla(planta: dict, paso: float):
    c = _g(planta)["contorno"]
    r_max = float(max(c["radios"]))
    n = math.ceil(r_max / paso) + 1
    x = (np.arange(-n, n) + 0.5) * paso
    X, Z = np.meshgrid(x, x, indexing="ij")
    theta = np.degrees(np.arctan2(Z, X))
    dentro = np.hypot(X, Z) <= radio_contorno(planta, theta)
    return x, X, Z, dentro


def volumen_directo(planta: dict, y: float, ajuste: Ajuste | None = None, paso: float = 10.0) -> float:
    """Volumen (m³) bajo el nivel horizontal ``y``, con el canal si la planta lo trae; es lo que se compara con las marcas al calibrar."""
    ajuste = ajuste or leer_ajuste(planta)
    _, X, Z, dentro = _rejilla(planta, paso)
    prof = np.clip(y - piso(planta, X, Z, ajuste), 0.0, None)
    return float((prof * dentro).sum() * paso * paso * 1e-9) + volumen_canal(planta, y, paso)


# ---------------------------------------------------------------------------
# Agujero de la piquera y canal de colada (EAF-051, Colombia)
# ---------------------------------------------------------------------------
#
# Cuentan como cavidad (pedido del usuario: A-A dibuja las líneas de nivel hasta el canal). Se suman como columnas de X más allá de
# la cara del lado de la piquera, con el mismo paso que la rejilla: el agujero, un cilindro inclinado por el eje medido en A-A; el
# canal, el perfil en U de E-E sobre el fondo de A-A, con el ancho escalado por la planta. Arriba de la pared del canal no cuenta
# (el metal se va). No se gastan ni se calibran.

def _canal(planta: dict) -> dict | None:
    return planta.get("cavidad_general", {}).get("canal")


def retroceso_canal(planta: dict, desgaste: Desgaste | None) -> float:
    """mm que retrocede el revestimiento del canal (EAF-052): la fracción consumida de la pared del lado de la piquera a la altura
    media del fondo del canal, por el espesor de trabajo del canal (el ANKOFORM bajo el fondo en E-E). El fondo baja eso y cada
    pared se abre eso (supuesto). Sirve con el % (escenario) y con el perfil por línea (campaña)."""
    c = _canal(planta)
    if not c or desgaste is None or desgaste.es_nuevo:
        return 0.0
    y_ref = np.array([float(np.mean(c["fondo"]["y"]))])
    e_pared = float(espesor_trabajo_pared(planta, y_ref, "b")[0])
    fraccion = float(retroceso_pared(planta, desgaste, y_ref, "b")[0]) / e_pared if e_pared > 0 else 0.0
    return float(np.clip(fraccion, 0.0, 1.0)) * float(c["espesor_trabajo"]["valor"])


def _ancho_en_canal(c: dict, x: np.ndarray, y: np.ndarray, u: float = 0.0) -> np.ndarray:
    """Ancho en Z (mm) del hueco del agujero o del canal en la columna ``x`` a la altura ``y`` (arreglos de la misma forma), con el
    revestimiento del canal gastado ``u`` mm (el fondo baja ``u`` y cada pared se abre ``u``)."""
    x, y = np.broadcast_arrays(np.asarray(x, float), np.asarray(y, float))
    p = c["piquera"]
    r = 0.5 * float(p["diametro"]["valor"])
    b = r / math.cos(math.radians(float(p["angulo_grados"])))           # semieje vertical del corte del cilindro inclinado
    yc = (x - float(p["origen_x"])) / float(p["pendiente_x_por_y"])
    agujero = (x > float(p["x_coraza"])) & (x <= float(p["x_cara"]))
    w_agujero = 2.0 * r * np.sqrt(np.clip(1.0 - ((y - yc) / b) ** 2, 0.0, None))
    f, ee, pl = c["fondo"], c["seccion_ee"], c["ancho_planta"]
    yb = np.interp(x, f["x"], f["y"]) - u
    h = y - yb
    escala = np.interp(x, pl["x"], pl["ancho"]) / float(np.interp(ee["x"], pl["x"], pl["ancho"]))
    en_canal = (x <= float(p["x_coraza"])) & (x >= float(f["x"][0])) & (h >= 0.0) & (h <= float(c["alto"]["valor"]) + u)
    w_canal = escala * np.interp(np.maximum(h - u, 0.0), ee["h"], ee["ancho"]) + 2.0 * u
    return np.where(agujero, w_agujero, np.where(en_canal, w_canal, 0.0))


def columnas_canal(planta: dict, paso: float = 10.0) -> np.ndarray:
    """Centros de X de las columnas del agujero y el canal, alineados con la rejilla (``(k + ½)·paso``)."""
    c = _canal(planta)
    if not c:
        return np.zeros(0)
    x0 = float(c["fondo"]["x"][0])
    x1 = min(float(c["piquera"]["x_cara"]), -float(radio_contorno(planta, 180.0)))   # lo de adentro del contorno ya es cavidad
    return (np.arange(math.floor(x0 / paso), math.floor(x1 / paso)) + 0.5) * paso


def areas_canal(planta: dict, y_inf: np.ndarray, paso: float = 10.0, sub: int = 5, u: float = 0.0) -> np.ndarray:
    """Área horizontal (mm², ancho en Z × paso en X; como ``Cavidad.area``) del agujero y el canal por capa (``y_inf``) y columna
    (``columnas_canal``), promediada en ``sub`` alturas de la capa."""
    c = _canal(planta)
    xc = columnas_canal(planta, paso)
    if not c or xc.size == 0:
        return np.zeros((len(y_inf), 0))
    ys = np.asarray(y_inf, float)[:, None] + (np.arange(sub) + 0.5) * paso / sub
    w = _ancho_en_canal(c, xc[None, None, :], ys[:, :, None], u)        # (capas, sub, columnas)
    return w.mean(axis=1) * paso


def volumen_canal(planta: dict, y: float, paso: float = 10.0) -> float:
    """Volumen (m³) del agujero y el canal bajo el nivel horizontal ``y``; 0 si la planta no trae canal."""
    c = _canal(planta)
    if not c:
        return 0.0
    ys = np.arange(800.0, min(float(y), rebose_canal(planta)[1]), 1.0) + 0.5     # lo de arriba del borde se va por el canal
    if ys.size == 0:
        return 0.0
    xc = columnas_canal(planta, paso)
    return float(_ancho_en_canal(c, xc[None, :], ys[:, None]).sum() * paso * 1e-9)


def rebose_canal(planta: dict, u: float = 0.0) -> tuple[float, float] | None:
    """(x, y) del borde del extremo del canal, por donde se va el metal (el fondo de A-A en su extremo, gastado ``u``); None si no
    hay canal."""
    c = _canal(planta)
    return (float(c["fondo"]["x"][0]), float(c["fondo"]["y"][0]) - u) if c else None


def _con_canal(planta: dict, x: np.ndarray, y_inf: np.ndarray, area: np.ndarray, paso: float,
               u: float = 0.0) -> tuple[np.ndarray, np.ndarray]:
    """Las columnas del agujero y el canal, aparte y delante de las de la cavidad: comparten X con el estadio del lado de la piquera
    (que llega a X ≈ −1 979 fuera del sector del bloque THB), pero solo a ellas les toca el rebose (``_rebose``)."""
    xc = columnas_canal(planta, paso)
    if xc.size == 0:
        return x, area
    return np.concatenate([xc, x]), np.hstack([areas_canal(planta, y_inf, paso, u=u), area])


def _rebose(planta: dict, x: np.ndarray, paso: float, u: float = 0.0) -> dict:
    """Los argumentos de ``Cavidad`` para el rebose del canal: el borde y las columnas del canal (todas fuera del contorno)."""
    borde = rebose_canal(planta, u)
    if borde is None:
        return {}
    mascara = np.zeros(x.size, bool)
    mascara[:columnas_canal(planta, paso).size] = True                  # las primeras: las del canal (``_con_canal``)
    return {"rebose": borde, "columnas_rebose": mascara}


def contorno_canal(planta: dict, u: float = 0.0) -> np.ndarray | None:
    """El hueco del agujero y el canal en el eje (Z = 0) como polígono (x, y) cerrado, para el dibujo, con el fondo del canal gastado
    ``u``; None si no hay canal."""
    c = _canal(planta)
    if not c:
        return None
    p, f = c["piquera"], c["fondo"]
    r = 0.5 * float(p["diametro"]["valor"])
    b = r / math.cos(math.radians(float(p["angulo_grados"])))
    xa, xk = float(p["x_cara"]), float(p["x_coraza"])
    yc = lambda x: (x - float(p["origen_x"])) / float(p["pendiente_x_por_y"])            # noqa: E731
    fx, fy = np.asarray(f["x"], float), np.asarray(f["y"], float) - u
    alto = float(c["alto"]["valor"]) + u
    fondo = [(x, y) for x, y in zip(fx[::-1], fy[::-1])]                 # de la coraza al extremo
    tope = [(x, y + alto) for x, y in zip(fx, fy)]                       # del extremo a la coraza
    return np.array([(xa, yc(xa) - b), (xk, yc(xk) - b), *fondo, *tope, (xk, yc(xk) + b), (xa, yc(xa) + b)])


def _puerta(g: dict):
    """(ancho, escalones [(y_inf, y_sup, x_cara)], y_umbral, x_umbral) o None si la planta no trae puerta medida."""
    p = g.get("puerta")
    if not p:
        return None
    esc = [(float(e["y_inferior"]), float(e["y_superior"]), float(e["x_cara"])) for e in p["escalones"]["lista"]]
    return float(p["ancho"]["valor"]), esc, float(p["y_umbral"]["valor"]), float(p["x_umbral"]["valor"])


def _x_cara_puerta(esc: list, yk: float) -> float | None:
    """X de la cara interior de la fila de pieza a la altura ``yk`` (las juntas entre filas cuentan como la fila de abajo)."""
    for i, (y0, y1, x) in enumerate(esc):
        y_hasta = esc[i + 1][0] if i + 1 < len(esc) else y1
        if y0 <= yk < y_hasta:
            return x
    return None


def fin_del_refractario(planta: dict, paso_angulo: float = 2.0, desgaste: Desgaste | None = None) -> tuple[np.ndarray, np.ndarray]:
    """(Y del tope, X de la cara) a lo largo del contorno. NaN en la puerta, donde manda el umbral."""
    g = _g(planta)
    f = g["fin_refractario"]
    th = np.arange(0.0, 360.0, paso_angulo)
    R = radio_contorno(planta, th)
    x = R * np.cos(np.radians(th))
    z = R * np.sin(np.radians(th))
    y = np.full(th.shape, float(f["cuerpo"]["valor"]))
    nariz = g["piso"].get("nariz")
    if nariz is not None and "nariz" in f:
        y = np.where(R > float(nariz["radio_cuerpo"]) + 5.0, float(f["nariz"]["valor"]), y)
    puerta = _puerta(g)
    if puerta is not None:
        y = np.where((x > 0) & (np.abs(z) <= puerta[0] / 2.0), np.nan, y)
    if desgaste is not None and not (desgaste.es_nuevo and desgaste.perfil is None):
        yy = np.nan_to_num(y, nan=float(f["cuerpo"]["valor"]))
        retro = np.where(_lado_b(planta, x, R), retroceso_pared(planta, desgaste, yy, "b"), retroceso_pared(planta, desgaste, yy, "a"))
        x = x + retro * np.cos(np.radians(th))
    return y, x


class _Estatica:
    """Lo que no cambia de una colada a otra: la rejilla, el piso, el área de las celdas que siempre están dentro (dentro del
    contorno original) y las celdas que el desgaste puede sumar (el anillo de hasta el espesor de trabajo más grande y la
    ventana del nicho de la puerta). Con ella, una cavidad gastada cuesta una pasada por el anillo en vez de por toda la rejilla."""

    def __init__(self, planta: dict, paso: float, ajuste: Ajuste):
        g = _g(planta)
        self.paso = paso
        x, X, Z, dentro = _rejilla(planta, paso)
        self.x = x
        r = np.hypot(X, Z)
        R0 = radio_contorno(planta, np.degrees(np.arctan2(Z, X)))
        F = piso(planta, X, Z, ajuste)
        self.y_piso = float(F[dentro].min())
        y_max = float(g["y_max"]["valor"])
        self.y_inf = np.arange(math.floor(self.y_piso / paso) * paso, y_max, paso)
        # El anillo que gana la pared al gastarse sigue horizontal desde donde el piso toca la pared original (EAF-034).
        Fw = np.where(r <= R0 + 1e-6, F, piso_del_anillo(planta, X, Z, ajuste))
        self.puerta = _puerta(g)
        rho_max = float(max(t["espesor"] for t in planta["desgaste"]["espesor_trabajo_pared"]["lista"]))
        if "desarrollo" in planta:                     # el anillo posible es el espesor de trabajo más grande de cualquier lado
            rho_max = max(rho_max, *(v[1] for lado in _componentes(planta).values() for v in lado.values()))
        adentro = dentro
        ventana = np.zeros_like(dentro)
        if self.puerta is not None and self.puerta[1]:
            x_max = max(e[2] for e in self.puerta[1]) + rho_max
            ventana = (np.abs(Z) <= self.puerta[0] / 2.0) & (X > 0) & (X <= x_max)
        opcional = ~adentro & ((R0 - r >= -(rho_max + paso)) | ventana)
        # área fija: celdas dentro del contorno original, capa por capa
        celda = paso * paso
        self.area_fija = np.zeros((self.y_inf.size, x.size))
        Fa = np.where(adentro, F, np.inf)
        idx_adentro = np.nonzero(adentro)
        self.piso_adentro = F[idx_adentro]                 # para el piso gastado (EAF-039): celdas dentro del contorno original
        self.columnas_adentro = idx_adentro[0]
        self._bancos = bool(g["piso"].get("bancos"))
        self._planta, self._ajuste = planta, ajuste
        self._X_adentro, self._Z_adentro = X[idx_adentro], Z[idx_adentro]
        for k, yk in enumerate(self.y_inf):
            self.area_fija[k] = np.clip((yk + paso - Fa) / paso, 0.0, 1.0).sum(axis=1) * celda
        idx = np.nonzero(opcional)
        self.col = idx[0]                                  # índice de columna X de cada celda opcional
        self.F = Fw[idx]
        self.X, self.Z = X[idx], Z[idx]
        self._anillo = ~(r <= R0 + 1e-6)[idx]              # celdas del anillo (fuera del contorno original)
        self.margen = (R0 - r)[idx]                        # < 0: fuera del contorno original
        self.lado_b = _lado_b(planta, self.X, R0[idx])
        self.nicho = None if self.puerta is None else (np.abs(self.Z) <= self.puerta[0] / 2.0) & (self.X > 0)
        self.celda = celda

    def areas_con_piso(self, u: float) -> tuple[np.ndarray, np.ndarray]:
        """(capas, área por capa y columna) con el piso gastado ``u`` mm perpendicular a su superficie (EAF-039; los perfiles
        retrocedidos, EAF-061)."""
        if u <= 0.0:
            return self.y_inf, self.area_fija
        F = piso_gastado(self._planta, self._X_adentro, self._Z_adentro, self._ajuste, u)
        y0 = math.floor(min(self.y_piso, float(F.min())) / self.paso) * self.paso
        y_inf = np.arange(y0, self.y_inf[-1] + self.paso / 2.0, self.paso)
        return y_inf, _areas_de_piso(F, self.columnas_adentro, y0, y_inf.size, self.x.size, self.paso)


_CACHE_ESTATICA: dict = {}


def _estatica(planta: dict, paso: float, ajuste: Ajuste) -> _Estatica:
    clave = (id(planta), paso, ajuste)
    hallado = _CACHE_ESTATICA.get(clave)
    if hallado is not None and hallado[0] is planta:
        return hallado[1]
    e = _Estatica(planta, paso, ajuste)
    if len(_CACHE_ESTATICA) >= 4:
        _CACHE_ESTATICA.pop(next(iter(_CACHE_ESTATICA)))
    _CACHE_ESTATICA[clave] = (planta, e)
    return e


def construir_cavidad_general(planta: dict, paso: float = 10.0, ajuste: Ajuste | None = None,
                              desgaste: Desgaste | None = None) -> Cavidad:
    """La cavidad discretizada, con el contrato de ``lwd_eaf.cavidad.Cavidad``.

    ``desgaste`` (solo pared) ensancha el contorno y el nicho de la puerta: por % del espesor de trabajo (escenario, EAF-026) o
    con un ``perfil`` por línea (la campaña, EAF-027). ``ValueError`` si pide piso.
    """
    g = _g(planta)
    ajuste = ajuste or leer_ajuste(planta)
    e = _estatica(planta, paso, ajuste)
    y_fondo = float(g["y_fondo_medido"]["valor"])      # el piso dibujado, no el calibrado: h se mide desde ahí (como las cotas del plano)
    u_piso = retroceso_piso(planta, desgaste)
    y_inf, area = e.areas_con_piso(u_piso)      # el piso gastado, perpendicular a su superficie
    area = area.copy()
    F_opc = e.F
    if u_piso > 0.0 and e._bancos and e._anillo.any():   # el anillo sigue al contacto gastado del banco (EAF-059)
        F_opc = e.F.copy()
        F_opc[e._anillo] = piso_del_anillo(planta, e.X[e._anillo], e.Z[e._anillo], ajuste, u_piso)
    centros = y_inf + 0.5 * paso
    ra = retroceso_pared(planta, desgaste, centros, "a")
    rb = retroceso_pared(planta, desgaste, centros, "b")
    for k, yk in enumerate(y_inf):
        rho = np.where(e.lado_b, rb[k], ra[k])
        dentro = e.margen >= -rho
        if e.puerta is not None:
            xc = _x_cara_puerta(e.puerta[1], yk + 0.5 * paso)
            if xc is not None:                          # el nicho de la puerta: entre la pared y la cara de la fila
                dentro = dentro | (e.nicho & (e.X <= xc + ra[k]))
        if not dentro.any():
            continue
        frac = np.clip((yk + paso - np.where(dentro, F_opc, np.inf)) / paso, 0.0, 1.0)
        area[k] += np.bincount(e.col, weights=frac, minlength=e.x.size) * e.celda
    y_fin, x_cara = fin_del_refractario(planta, desgaste=desgaste)
    puerta = e.puerta
    x_um, y_um = (puerta[3], puerta[2]) if puerta is not None else (math.nan, math.nan)
    if puerta is not None:
        x_um += float(retroceso_pared(planta, desgaste, y_um - 1.0, "a"))   # la arista es la cara de la fila de abajo del tope
    u = retroceso_canal(planta, desgaste)                               # el agujero de la piquera y el canal (EAF-051, gastado EAF-052)
    x, area = _con_canal(planta, e.x, y_inf, area, paso, u)
    return Cavidad(paso, x, y_inf, area, y_fin, x_cara, x_um, y_um, y_fondo=y_fondo, **_rebose(planta, x, paso, u))


def _construir_lento(planta: dict, paso: float = 10.0, ajuste: Ajuste | None = None,
                              desgaste: Desgaste | None = None) -> Cavidad:
    """Referencia lenta (una pasada completa de la rejilla por capa) de ``construir_cavidad_general``, solo para las
    pruebas (desgaste por % y por perfil); la versión rápida da lo mismo (EAF-027)."""
    g = _g(planta)
    ajuste = ajuste or leer_ajuste(planta)
    y_max = float(g["y_max"]["valor"])
    x, X, Z, dentro = _rejilla(planta, paso)
    F = piso(planta, X, Z, ajuste)
    u_piso = retroceso_piso(planta, desgaste)
    if u_piso > 0.0:                                     # el piso gastado, perpendicular a su superficie (EAF-039; bancos, EAF-059)
        F = piso_gastado(planta, X, Z, ajuste, u_piso, paso)
    y_piso = float(F[dentro].min())
    y_fondo = float(g["y_fondo_medido"]["valor"])      # el piso dibujado, no el calibrado: h se mide desde ahí (como las cotas del plano)
    y0 = math.floor(y_piso / paso) * paso
    y_inf = np.arange(y0, y_max, paso)
    area = np.zeros((y_inf.size, x.size))
    celda = paso * paso
    puerta = _puerta(g)
    desgastada = desgaste is not None and not (desgaste.es_nuevo and desgaste.perfil is None)
    if desgastada:
        r_celda, R_celda = np.hypot(X, Z), radio_contorno(planta, np.degrees(np.arctan2(Z, X)))
        lado_b = _lado_b(planta, X, R_celda)
        # El anillo que gana la pared al gastarse sigue horizontal desde donde el piso toca la pared original (EAF-034).
        F = np.where(r_celda <= R_celda + 1e-6, F, piso_del_anillo(planta, X, Z, ajuste, u_piso))
    for k, yk in enumerate(y_inf):
        dentro_k = dentro
        ra = float(retroceso_pared(planta, desgaste, yk + 0.5 * paso, "a")) if desgastada else 0.0
        rb = float(retroceso_pared(planta, desgaste, yk + 0.5 * paso, "b")) if desgastada else 0.0
        if desgastada:                                  # la cara caliente retrocede en todo el contorno
            dentro_k = r_celda <= R_celda + np.where(lado_b, rb, ra)
        if puerta is not None:
            xc = _x_cara_puerta(puerta[1], yk + 0.5 * paso)
            if xc is not None:                          # el nicho de la puerta: entre la pared y la cara de la fila
                dentro_k = dentro_k | ((np.abs(Z) <= puerta[0] / 2.0) & (X > 0) & (X <= xc + ra))
        Fd = np.where(dentro_k, F, np.inf)
        frac = np.clip((yk + paso - Fd) / paso, 0.0, 1.0)
        area[k] = frac.sum(axis=1) * celda
    y_fin, x_cara = fin_del_refractario(planta, desgaste=desgaste)
    x_um, y_um = (puerta[3], puerta[2]) if puerta is not None else (math.nan, math.nan)
    if desgastada and puerta is not None:
        x_um += float(retroceso_pared(planta, desgaste, y_um - 1.0, "a"))   # la arista es la cara de la fila de abajo del tope
    u = retroceso_canal(planta, desgaste)
    x, area = _con_canal(planta, x, y_inf, area, paso, u)
    return Cavidad(paso, x, y_inf, area, y_fin, x_cara, x_um, y_um, y_fondo=y_fondo, **_rebose(planta, x, paso, u))


# ---------------------------------------------------------------------------
# Marcas de nivel del plano y calibración
# ---------------------------------------------------------------------------

def marcas(planta: dict) -> list[dict]:
    """Marcas de nivel del plano: ``y`` (mm), ``toneladas`` y ``volumen_m3`` (= toneladas / densidad, o el escrito)."""
    rho = float(planta["densidades"]["acero_liquido"]["valor"])
    salida = []
    for m in planta["marcas_del_plano"]["lista"]:
        v = m.get("volumen_m3")
        v = float(v["valor"]) if isinstance(v, dict) else m["toneladas"]["valor"] / rho
        salida.append({"nombre": m["nombre"], "y": float(m["y"]["valor"]), "toneladas": float(m["toneladas"]["valor"]),
                       "volumen_m3": float(v)})
    return salida


def residuos(planta: dict, ajuste: Ajuste | None = None, paso: float = 10.0) -> list[dict]:
    """Volumen calculado (con el agujero de la piquera y el canal, si los hay) contra volumen de cada marca, con la diferencia relativa."""
    ajuste = ajuste or leer_ajuste(planta)
    _, X, Z, dentro = _rejilla(planta, paso)
    F = piso(planta, X, Z, ajuste)
    salida = []
    for m in marcas(planta):
        v = float((np.clip(m["y"] - F, 0.0, None) * dentro).sum() * paso * paso * 1e-9) + volumen_canal(planta, m["y"], paso)
        salida.append(dict(m, calculado_m3=v, diferencia=v / m["volumen_m3"] - 1.0))
    return salida


def calibrar(planta: dict, paso: float = 10.0, parametros: int = 2) -> tuple[Ajuste, list[dict]]:
    """Ajusta ``Δ`` (y ``f`` si ``parametros`` = 2) para que el volumen reproduzca las marcas (mínimos cuadrados
    de la diferencia relativa; Nelder–Mead, solo NumPy). Devuelve el ajuste y los residuos."""
    ms = marcas(planta)
    _, X, Z, dentro = _rejilla(planta, paso)
    canal = [volumen_canal(planta, m["y"], paso) for m in ms]          # el canal no se ajusta

    def costo(p) -> float:
        a = Ajuste(float(p[0]), float(p[1]) if parametros == 2 else 1.0)
        F = piso(planta, X, Z, a)
        e = [(float((np.clip(m["y"] - F, 0.0, None) * dentro).sum() * paso * paso * 1e-9) + vc) / m["volumen_m3"] - 1.0
             for m, vc in zip(ms, canal)]
        return float(np.sum(np.square(e)))

    inicio = np.array([0.0, 1.0][:parametros])
    paso_ini = np.array([60.0, 0.05][:parametros])
    p = _nelder_mead(costo, inicio, paso_ini)
    a = Ajuste(float(p[0]), float(p[1]) if parametros == 2 else 1.0)
    return a, residuos(planta, a, paso)


def _nelder_mead(f, x0: np.ndarray, paso: np.ndarray, iteraciones: int = 120, tolerancia: float = 1e-12) -> np.ndarray:
    n = len(x0)
    simplex = [x0.copy()] + [x0 + np.eye(n)[i] * paso[i] for i in range(n)]
    valores = [f(p) for p in simplex]
    for _ in range(iteraciones):
        orden = np.argsort(valores)
        simplex = [simplex[i] for i in orden]
        valores = [valores[i] for i in orden]
        if abs(valores[-1] - valores[0]) < tolerancia:
            break
        centro = np.mean(simplex[:-1], axis=0)
        refl = centro + (centro - simplex[-1])
        fr = f(refl)
        if fr < valores[0]:
            exp = centro + 2.0 * (centro - simplex[-1])
            fe = f(exp)
            simplex[-1], valores[-1] = (exp, fe) if fe < fr else (refl, fr)
        elif fr < valores[-2]:
            simplex[-1], valores[-1] = refl, fr
        else:
            con = centro + 0.5 * (simplex[-1] - centro)
            fc = f(con)
            if fc < valores[-1]:
                simplex[-1], valores[-1] = con, fc
            else:
                simplex = [simplex[0]] + [simplex[0] + 0.5 * (p - simplex[0]) for p in simplex[1:]]
                valores = [valores[0]] + [f(p) for p in simplex[1:]]
    return simplex[int(np.argmin(valores))]
