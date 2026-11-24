"""Reproducción del estudio de vaciado por el EBT de Magnesita para Pesquería (EAF-064, herramientas/vaciado_ebt.py).

Las tolerancias son las diferencias observadas más un margen; no validan nada del horno: comparan un sólido supuesto con el
cálculo teórico del proveedor.
"""

import math

import pytest

from herramientas import vaciado_ebt as ve
from modelo_vaciado.horno3d.planta import cargar_planta


@pytest.fixture(scope="module")
def datos():
    return cargar_planta("pesqueria"), ve.cargar_estudio()


def test_la_tabla_de_magnesita_es_torricelli_con_altura_media(datos):
    _, estudio = datos
    for estado, cd in (("nuevo", 0.731), ("gastado", 0.741)):
        k = ve.coeficiente(estudio, estado)
        for p in estudio["escenarios"][estado]["pasos"]:
            assert p["altura_ferrostatica"] == pytest.approx(0.5 * (p["nivel_inicio"] + p["nivel_fin"]))
            q = (p["t_inicio"] - p["t_fin"]) / p["tiempo_s"]
            assert q == pytest.approx(k * math.sqrt(p["altura_ferrostatica"]), rel=2e-4)
            assert q == pytest.approx(p["flujo_t_s"], abs=6e-4)
        assert ve.coeficiente_de_descarga(estudio, estado) == pytest.approx(cd, abs=1e-3)
        assert sum(p["tiempo_s"] for p in estudio["escenarios"][estado]["pasos"]) == pytest.approx(
            estudio["escenarios"][estado]["tiempo_total_s"], abs=0.02)


def test_marcas_a_cero_grados_de_los_cinco_desgastes(datos):
    planta, estudio = datos
    filas = ve.reproducir_marcas(planta, estudio)
    assert len(filas) == 5
    for m in filas:
        for t in (150, 450):
            tolerancia = 16.0 if (m["hoja"], t) == (6, 450) else 6.0      # la hoja 6 (400 mm de fondo) queda +14 mm a 450 t
            assert abs(m[f"y_{t}_modelo"] - m[f"y_{t}"]) <= tolerancia, (m["hoja"], t)


@pytest.mark.parametrize("estado, tolerancia", [("nuevo", 25.0), ("gastado", 15.0)])
def test_niveles_inclinados(datos, estado, tolerancia):
    planta, estudio = datos
    filas = ve.reproducir_escenario(planta, estudio, estado)
    for p in filas:
        assert abs(p["nivel_inicio_modelo"] - p["nivel_inicio"]) <= tolerancia
        assert abs(p["nivel_fin_modelo"] - p["nivel_fin"]) <= tolerancia
    total = sum(p["tiempo_modelo"] for p in filas)
    assert total == pytest.approx(estudio["escenarios"][estado]["tiempo_total_s"], rel=0.01)


@pytest.mark.parametrize("estado", ["nuevo", "gastado"])
def test_curvas_de_carga(datos, estado):
    planta, estudio = datos
    for c in ve.reproducir_curvas(planta, estudio, estado):
        assert abs(c["segura_modelo"] - c["segura"]) <= 8.0          # leídas de la gráfica a ±5 t
        assert abs(c["minima_modelo"] - c["minima"]) <= 8.0
        assert 670.0 <= c["altura_de_la_minima"] <= 715.0             # la roja: unos 700 mm de acero sobre la boca


def test_el_talon_de_la_hoja_9_no_cuadra_con_las_hojas_7_y_8(datos):
    planta, estudio = datos
    for estado in ("nuevo", "gastado"):
        t = ve.reproducir_talon(planta, estudio, estado)
        # la tabla usa la mitad del nivel final del paso de 2°, no la mitad del nivel de 150 t a 15°
        assert t["altura_ferrostatica"] == estudio["escenarios"][estado]["pasos"][0]["nivel_fin"] / 2
        assert t["nivel_modelo"] / 2 > t["altura_ferrostatica"] + 60


def test_distancia_vertical_y_su_inversa():
    y = ve.y_eje_a_distancia(300.0, 11.0, (-5000.0, 1699.0))
    assert ve.distancia_vertical(y, 11.0, (-5000.0, 1699.0)) == pytest.approx(300.0)


def test_el_stl_de_la_cavidad_esta_cerrado_y_el_dxf_se_escribe(datos, tmp_path):
    planta, estudio = datos
    s = ve.construir_solido(planta, 348.0, 225.0, paso=100.0)
    malla = ve.malla_cavidad(s)
    assert ve.volumen_de_malla(malla) == pytest.approx(s.volumen(ve.Y_TOPE_CAD, 0.0), rel=2e-3)   # cerrada y bien orientada
    ve.escribir_stl(malla, tmp_path / "c.stl", "prueba")
    assert (tmp_path / "c.stl").stat().st_size == 84 + 50 * len(malla)
    ve.escribir_dxf_vistas(planta, estudio, "nuevo", tmp_path / "v.dxf")
    texto = (tmp_path / "v.dxf").read_text(encoding="ascii")
    assert texto.rstrip().endswith("EOF") and texto.count("POLYLINE") == 12 and "NIVEL_FIN" in texto
