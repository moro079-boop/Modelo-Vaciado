"""Cálculo directo del tiempo de vaciado (``flujo``, ``escenarios``, ``reporte_tiempo``) y su ventana.

Las referencias son independientes del integrador: la solución cerrada de Torricelli, el vaciado de la olla del módulo de la
colada continua (otro integrador sobre la misma olla) y el horno con su cavidad 3D a ángulo fijo.
"""

import math
from pathlib import Path

import pytest

from modelo_vaciado import colada_continua as cc
from modelo_vaciado import escenarios as es
from modelo_vaciado.flujo import (AreaDePaso, ConfigVaciado, NivelConstante, Perdidas, RecipientePrismatico,
                                  RecipienteTroncoconico, simular, torricelli)

RAIZ = Path(__file__).resolve().parent.parent


def _config(**cambios):
    base = dict(recipiente=RecipientePrismatico(10.0, 7.0), paso=AreaDePaso(100.0), perdidas=Perdidas(cd=0.8),
                acero_inicial=140.0, acero_final=14.0, densidad=7.0)
    base.update(cambios)
    return ConfigVaciado(**base)


def test_torricelli_contra_el_integrador():
    for c in (_config(), _config(caida=500.0), _config(aguas_abajo=NivelConstante(300.0, 100.0), caida=400.0),
              _config(fraccion_abierta=0.6)):
        r = simular(c, dt=0.5)
        assert r.terminado
        assert r.tiempo == pytest.approx(torricelli(c), rel=1e-4)


def test_area_y_diametro_equivalentes():
    a = AreaDePaso.de_area(math.pi * 100.0 ** 2 / 4)
    assert a.diametro == pytest.approx(100.0)
    assert simular(_config(paso=a)).tiempo == pytest.approx(simular(_config()).tiempo)


def test_troncoconico_conserva_el_tonelaje_y_cilindro_igual_a_prisma():
    t = RecipienteTroncoconico.de_tonelaje(200.0, 1500.0, 0.7, 7.0)
    assert t.altura(200.0) == pytest.approx(1500.0, rel=1e-6)
    cil = RecipienteTroncoconico.de_tonelaje(200.0, 1500.0, 1.0, 7.0)
    pri = RecipientePrismatico.de_tonelaje(200.0, 1500.0, 7.0)
    assert cil.altura(80.0) == pytest.approx(pri.altura(80.0), rel=1e-6)


def test_el_tiempo_escala_con_el_area_y_el_cd():
    t0 = simular(_config()).tiempo
    assert simular(_config(paso=AreaDePaso(200.0))).tiempo == pytest.approx(t0 / 4, rel=1e-3)
    assert simular(_config(perdidas=Perdidas(cd=0.4))).tiempo == pytest.approx(2 * t0, rel=1e-3)


def test_perdidas_explicitas_mas_lentas_que_sin_perdidas():
    sin = simular(_config(perdidas=Perdidas(cd=1.0))).tiempo
    con = simular(_config(perdidas=Perdidas("perdidas", largo=1000.0, k_entrada=0.5))).tiempo
    assert con > sin * math.sqrt(1.5) * 0.999


def test_contrapresion_que_iguala_los_niveles_detiene_el_vaciado():
    c = _config(aguas_abajo=NivelConstante(2000.0, 0.0), acero_final=1.0)   # el destino queda por encima del baño final
    r = simular(c)
    assert not r.terminado and "sin carga" in r.motivo_fin
    assert c.altura(float(r.masa[-1])) == pytest.approx(2000.0, abs=5.0)


def test_olla_igual_al_modulo_de_colada_continua():
    """La olla de Pesquería con el distribuidor a nivel constante: el mismo vaciado que ``colada_continua.vaciado_libre_olla``."""
    r = es.correr(es.nuevo("olla_distribuidor"))
    t, _ = cc.vaciado_libre_olla(cc.configurar("pesqueria"))
    assert r.tiempo == pytest.approx(float(t[-1]), rel=2e-3)


def test_horno_simple_cerca_de_la_cavidad_3d_a_angulo_fijo():
    """El horno como prisma (tonelaje, altura y talón de la cavidad a 0°) contra la cavidad 3D a 0°: 622 s contra 613,5 s."""
    from modelo_vaciado import escenario as ve
    from modelo_vaciado.basculado import AnguloFijo
    from modelo_vaciado.hidraulica import Hidraulica
    from modelo_vaciado.simulacion import simular as simular_3d

    r = es.correr(es.abrir(RAIZ / "ejemplos" / "horno_olla" / "01_prismatico_pesqueria.json"))
    c, _ = ve.contexto_de({"planta": "pesqueria"})
    r3d = simular_3d(c, Hidraulica(cd=0.731), AnguloFijo(0.0), 450.0, 150.0)
    assert r.tiempo == pytest.approx(r3d.tiempo, rel=0.03)
    assert r.tiempo == pytest.approx(es.resumen(r)["tiempo_torricelli_s"], rel=1e-4)


def test_los_ejemplos_corren_y_se_guardan(tmp_path):
    for carpeta in ("horno_olla", "olla_distribuidor"):
        rutas = sorted((RAIZ / "ejemplos" / carpeta).glob("*.json"))
        assert len(rutas) >= 5
        for ruta in rutas:
            e = es.abrir(ruta)
            r = es.correr(e)
            assert r.terminado, (ruta.name, r.motivo_fin)
            es.guardar(e, tmp_path / ruta.name)
            assert es.correr(es.abrir(tmp_path / ruta.name)).tiempo == pytest.approx(r.tiempo)


def test_llenado_del_distribuidor_conserva_la_masa():
    e = es.abrir(RAIZ / "ejemplos" / "olla_distribuidor" / "04_llenado_distribuidor.json")
    r = es.correr(e)
    c = r.config
    masa_destino = c.aguas_abajo.tundish.masa(float(r.nivel_destino[-1]))
    assert masa_destino == pytest.approx(c.aguas_abajo.masa_inicial + r.colado, rel=2e-3)


def test_entradas_no_validas():
    e = es.nuevo("horno_olla")
    e["acero_final_t"] = 500.0
    with pytest.raises(ValueError):
        es.correr(e)
    e = es.nuevo("olla_distribuidor")
    e["acero_inicial_t"] = 900.0
    with pytest.raises(ValueError, match="capacidad"):
        es.correr(e)
    with pytest.raises(ValueError):
        es.nuevo("distribuidor_moldes")


def test_reportes(tmp_path):
    from openpyxl import load_workbook

    from modelo_vaciado import reporte_tiempo as rt

    for tipo in es.TIPOS:
        e = es.nuevo(tipo)
        r = es.correr(e)
        rt.escribir_csv(r, tmp_path / f"{tipo}.csv")
        rt.escribir_excel(e, r, tmp_path / f"{tipo}.xlsx")
        rt.escribir_pdf(e, r, tmp_path / f"{tipo}.pdf")
        libro = load_workbook(tmp_path / f"{tipo}.xlsx")
        assert libro.sheetnames == ["Resumen", "Datos", "Serie"]
        assert "PRELIMINAR" in libro["Resumen"]["A2"].value
        assert (tmp_path / f"{tipo}.pdf").read_bytes()[:4] == b"%PDF"
        assert "Tiempo de vaciado" in rt.texto(e, r)


def test_ventana_y_disenos(tmp_path):
    pytest.importorskip("PySide6")
    from modelo_vaciado.interfaz import disenos, tema
    from modelo_vaciado.ventana import Ventana, aplicacion_qt, cambiar_diseno, indicadores_de, preparar

    qapp = aplicacion_qt()
    for nombre in disenos.DISENOS:
        preparar(qapp, nombre)
        assert tema.DISENO == nombre
        v = Ventana(diseno=nombre)
        assert v.icono_cargado
        o = v.olla
        assert o.resultado.tiempo == pytest.approx(es.correr(es.nuevo("olla_distribuidor")).tiempo)
        o.campos["diametro_mm"].setValue(80.0)
        assert o.campos["area_cm2"].value() == pytest.approx(math.pi * 64 / 4 * 100 / 100, rel=1e-3)
        assert "dato del usuario" in o.estados["diametro_mm"].text()
        assert o.calcular() and o.resultado.tiempo / 60 == pytest.approx(36.7, abs=0.2)
        o.destino.setCurrentIndex(o.destino.findData("llenado"))
        assert o.calcular()
        v._elegir(1)
        assert indicadores_de(v.pagina_actual())[0][1] == o.tiempo_texto()
        v.close()
    preparar(qapp, "magnesita")
    v = Ventana(RAIZ / "ejemplos" / "olla_distribuidor" / "03_abertura_60.json", diseno="magnesita")
    assert v._actual() == 1 and v.olla.campos["abertura_pct"].value() == 60.0
    h = v.horno.directo
    h.definir_paso.setCurrentIndex(h.definir_paso.findData("area"))
    h.campos["area_cm2"].setValue(400.0)
    assert h.calcular() and h.escenario()["paso"] == {"area_cm2": 400.0}
    assert h.calcular_sensibilidad() and len(h.sensibilidad[0]) == 11
    h.guardar_en(tmp_path / "h.json")
    assert es.correr(es.abrir(tmp_path / "h.json")).tiempo == pytest.approx(h.resultado.tiempo)
    for ext in ("xlsx", "pdf", "csv"):
        h.exportar_en(tmp_path / f"h.{ext}")
        assert (tmp_path / f"h.{ext}").stat().st_size > 500
    h.campos["acero_final_t"].setValue(600.0)
    assert not h.calcular() and "No se pudo calcular" in h.avisos.text()
    h.campos["acero_final_t"].setValue(150.0)
    w = cambiar_diseno(v, "colada")                         # el escenario en pantalla pasa al diseño nuevo
    assert w.diseno.nombre == "colada" and w.horno.directo.escenario()["paso"] == {"area_cm2": 400.0}
    w.close()
    preparar(qapp, "magnesita")
