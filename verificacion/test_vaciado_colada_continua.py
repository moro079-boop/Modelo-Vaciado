"""Vaciado en la colada continua (EAF-069): olla, válvula deslizante, tundish y moldes, y los mapas del horno.

Preliminar: se comprueba la física contra soluciones analíticas y la geometría de la olla contra las marcas de su plano (heredadas
del LWD). Los datos del tundish y de la máquina son ejemplos."""

import math

import numpy as np
import pytest

from modelo_vaciado import colada_continua as cc
from modelo_vaciado import mapa
from modelo_vaciado.artesa import Tundish
from modelo_vaciado.olla import GeometriaOlla, TablaOlla
from modelo_vaciado.valvula import Orificio, abertura_para, fraccion_abierta
from modelo_vaciado import escenario as ve
from pathlib import Path

EJEMPLOS = Path(__file__).resolve().parent.parent / "ejemplos" / "horno_cavidad_3d"


@pytest.fixture(scope="module")
def config():
    return cc.configurar("pesqueria")


def test_valvula_fraccion_y_su_inversa():
    assert fraccion_abierta(100, 55) == pytest.approx(1.0)
    assert fraccion_abierta(0, 55) == pytest.approx(0.0, abs=1e-12)
    assert fraccion_abierta(50, 55) == pytest.approx(2 / math.pi * (math.acos(0.5) - 0.5 * math.sqrt(0.75)))
    for f in (0.05, 0.3, 0.8):
        assert fraccion_abierta(abertura_para(f, 55), 55) == pytest.approx(f, abs=1e-9)
    o = Orificio(55.0, 0.75)
    q = o.caudal(2000.0, 7.0)
    assert o.carga_para(q, 7.0) == pytest.approx(2000.0)


def test_olla_de_pesqueria_contra_las_marcas_del_plano(config):
    """Las marcas del plano CS129722: el LWD acepta 5 %; aquí quedan a 1.4 % (igual que el LWD)."""
    planta = cc.cargar_planta("pesqueria")
    t = config.olla
    for m in planta["olla"]["marcas"]["lista"]:
        assert t.masa_a_cota(m["z_mm"]) == pytest.approx(m["toneladas"], rel=0.02)
    g = GeometriaOlla.de_datos(planta["olla"])
    gastada = TablaOlla.de_geometria(g, pared_gastada=76.2, piso_gastado=200.0)
    assert gastada.capacidad > t.capacidad and gastada.cota(300.0) < t.cota(300.0)


def test_tundish_volumen_cerrado():
    tu = Tundish(7000, 1000, 10, 7.0, 1100, 500, 1300)
    h = np.linspace(0, 1300, 1301)
    numerico = np.trapezoid([tu.area(x) for x in h], h / 1000.0)
    assert tu.volumen(1300) == pytest.approx(numerico, rel=1e-6)
    assert tu.nivel(tu.masa(812.3)) == pytest.approx(812.3, abs=1e-6)


def test_vaciado_libre_contra_torricelli():
    """Olla cilíndrica de prueba: el tiempo de vaciado con la válvula abierta es el de Torricelli."""
    g = GeometriaOlla(2000.0, 2000.0, 0.0, 0.0, 0.0, 100.0, ((1, 40, 0.0),), 7.0, 0.0)
    c = cc.configurar("pesqueria")
    from dataclasses import replace
    c2 = replace(c, olla=TablaOlla.de_geometria(g, paso=5.0), caida=0.0, altura_salida_tubo=1e9, remanente=10.0, acero_por_olla=200.0)
    t, m = cc.vaciado_libre_olla(c2, dt=0.25)
    area = math.pi * 2.0 ** 2
    h = lambda masa: masa / (7.0 * area)  # noqa: E731
    a = c2.valvula.cd * c2.valvula.area
    exacto = 2 * area * (math.sqrt(h(200.0)) - math.sqrt(h(10.0))) / (a * math.sqrt(2 * 9.81))
    assert t[-1] == pytest.approx(exacto, rel=2e-3)


def test_secuencia_conserva_la_masa_y_controla_el_nivel(config):
    r = cc.simular_secuencia(config)
    assert len(r.ollas) == config.ollas
    for o in r.ollas:
        assert o.colado == pytest.approx(config.acero_por_olla - config.remanente, abs=0.01)
    salido = np.sum(0.5 * (r.caudal_molde[1:] + r.caudal_molde[:-1]) * np.diff(r.t))
    entrada_total = r.colado_total + config.tundish.masa(config.nivel_inicial) - r.masa_tundish[-1]
    assert salido == pytest.approx(entrada_total, rel=0.01)                 # el muestreo cada 5 s integra a 1 %
    assert r.nivel_tundish[-1] == pytest.approx(config.tundish.nivel_minimo, abs=1.0)
    s = cc.resumen(r)
    assert s["margen_en_cambio"]["tiempo_s"] > config.cambio
    assert all(h > config.tundish.nivel_minimo for h in s["nivel_minimo_en_cambio_mm"])
    # con la válvula de 55 mm la olla no alcanza la demanda al final de cada olla: el programa lo avisa
    assert s["velocidad_maxima"]["por_la_olla"] < config.moldes.velocidad
    assert any("abierta del todo" in texto for _, texto in r.eventos)


def test_una_valvula_mas_grande_sigue_la_demanda():
    c = cc.configurar("pesqueria", {"valvula_diametro_mm": 100.0})
    assert cc.velocidad_maxima(c)["por_la_olla"] > c.moldes.velocidad
    r = cc.simular_secuencia(c)
    regimen = cc.tiempo_de_colado_de_una_olla(c)
    for o in r.ollas[1:]:            # cada olla repone primero lo que el tundish perdió en el cambio
        assert o.duracion == pytest.approx(regimen - c.cambio, rel=0.01)
    assert not any("abierta del todo" in texto for _, texto in r.eventos)
    assert np.nanmedian(r.fraccion) < 0.5 and np.nanmin(r.abertura) > 0     # abierta del todo sólo al reponer tras el cambio


def test_buzas_limitan_la_velocidad():
    c = cc.configurar("pesqueria", {"valvula_diametro_mm": 80.0, "buza_diametro_mm": 30.0})
    r = cc.simular_secuencia(c)
    assert r.velocidad.max() < c.moldes.velocidad
    assert any("buzas" in texto for _, texto in r.eventos)


def test_mapa_por_angulo_y_por_colada():
    e = ve.abrir(EJEMPLOS / "03_seguir_carga_segura.json")
    filas = mapa.por_angulo(e, angulos=[0.0, 8.0, 15.0], dt=1.0)
    assert [f.llega for f in filas] == [True, True, True]
    assert filas[0].tiempo > filas[1].tiempo > filas[2].tiempo        # más ángulo, más carga, menos tiempo
    assert not filas[0].invade_panel and filas[2].invade_panel        # 450 t a 15° invaden el panel
    col = mapa.por_colada(e, 61, 0.5, cada=30, dt=1.0)
    assert [c["diametro"] for c in col] == [200.0, 215.0, 230.0]
    exacto = ve.correr(dict(e, piquera={"diametro": 215.0}), dt=1.0).tiempo
    assert col[1]["tiempo_s"] == pytest.approx(exacto, rel=2e-3)
    o = mapa.angulo_optimo(ve.abrir(EJEMPLOS / "01_magnesita_escalones.json"))
    assert o["ahorro_s"] > 0
