"""Modelo de vaciado por la piquera (EAF-065, ``modelo_vaciado``). Preliminar: las pruebas comprueban el integrador contra una
solución analítica y contra el cálculo teórico de Magnesita; no hay tiempos de vaciado medidos."""

import json
import math
from pathlib import Path

import numpy as np
import pytest

from modelo_vaciado.horno3d import niveles
from modelo_vaciado import datos as vd
from modelo_vaciado import escenario as ve
from modelo_vaciado.basculado import AnguloFijo, Escalones
from modelo_vaciado.hidraulica import G, Hidraulica, factor_de_friccion
from modelo_vaciado.simulacion import Contexto, simular
from modelo_vaciado.tabla import NivelAnalitico

RAIZ = Path(__file__).resolve().parent.parent
EJEMPLOS = RAIZ / "ejemplos" / "vaciado"
PIQUERA = vd.Piquera("EBT", 0.0, 0.0, -1000.0, 200.0)


def _prisma(area=40.0, rho=7.0, d=200.0):
    return Contexto(NivelAnalitico(area, rho), PIQUERA, rho, d)


def test_recipiente_prismatico_contra_torricelli():
    c, cd, m0, m1 = _prisma(), 0.7, 300.0, 50.0
    r = simular(c, Hidraulica("cd", "boca", cd), AnguloFijo(0.0), m0, m1, dt=0.25)
    h = lambda m: m / (c.densidad * 40.0)  # noqa: E731  (m)
    a = math.pi * 0.2 ** 2 / 4
    exacto = 2 * 40.0 * (math.sqrt(h(m0)) - math.sqrt(h(m1))) / (cd * a * math.sqrt(2 * G))
    assert r.tiempo == pytest.approx(exacto, rel=1e-5)
    assert r.masa[-1] == pytest.approx(m1) and r.motivo_fin.startswith("se alcanzó")
    assert np.all(np.diff(r.masa) <= 1e-12)


def test_el_paso_de_tiempo_no_cambia_el_resultado():
    c = _prisma()
    t = [simular(c, Hidraulica(), AnguloFijo(0.0), 300.0, 20.0, dt=dt).tiempo for dt in (2.0, 0.5, 0.1)]
    assert t[0] == pytest.approx(t[2], rel=1e-3) and t[1] == pytest.approx(t[2], rel=1e-4)


def test_vaciar_del_todo_termina_cuando_el_bano_no_llega_a_la_boca():
    r = simular(_prisma(), Hidraulica(), AnguloFijo(0.0), 50.0, 0.0, dt=0.5, t_max=20000)
    assert r.masa[-1] < 0.05 and r.tiempo < 20000


def test_hidraulica():
    assert factor_de_friccion(1000.0, 0.005) == pytest.approx(0.064)
    assert 0.02 < factor_de_friccion(1e6, 0.005) < 0.04
    cd, per = Hidraulica("cd", "boca", 0.731), Hidraulica("perdidas", "salida")
    q = cd.caudal(1031.0, 2.0, PIQUERA, 200.0, 6.9)
    assert q == pytest.approx(0.713, abs=1e-3)                                 # primer renglón de la tabla de Magnesita
    assert cd.caudal(-5.0, 0.0, PIQUERA, 200.0, 6.9) == 0.0
    assert Hidraulica("cd", "salida", 0.731).caudal(1031.0, 2.0, PIQUERA, 200.0, 6.9) > q    # el canal lleno suma carga
    assert cd.caudal(1031.0, 2.0, PIQUERA, 240.0, 6.9) == pytest.approx(q * 1.44)             # con el cuadrado del diámetro
    assert 0.6 < per.cd_equivalente(1000.0, 0.0, PIQUERA, 200.0, 6.9) / math.sqrt(2.0) < 0.9  # (1 + K + fL/D)^-½ con H = 2 m
    with pytest.raises(ValueError):
        Hidraulica(modo="otro")


def test_la_escoria_suma_carga():
    c = _prisma()
    sin = simular(c, Hidraulica(), AnguloFijo(0.0), 300.0, 100.0)
    con = simular(c, Hidraulica(), AnguloFijo(0.0), 300.0, 100.0, escoria_t=30.0)
    assert con.tiempo < sin.tiempo


def test_la_tabla_de_niveles_coincide_con_la_cavidad():
    d = vd.cargar("pesqueria")
    tabla = ve.tabla_de("pesqueria", d)
    cav = niveles.cavidad_de(ve.planta_de("pesqueria"))
    for ang, t in ((0.0, 450.0), (3.3, 400.0), (7.7, 260.0), (15.0, 150.0), (11.2, 20.0)):
        assert tabla.y_eje(t, ang) == pytest.approx(niveles.y_eje_para_volumen(cav, t / 6.9, ang), abs=1.5)
    assert tabla.masa_a_distancia(tabla.nivel_boca(300.0, 6.0), 6.0) == pytest.approx(300.0, abs=0.3)


def test_reproduce_el_estudio_de_magnesita():
    estudio = json.loads((RAIZ / "datos" / "estudios" / "vaciado_ebt_pesqueria.json").read_text(encoding="utf-8"))
    for archivo, estado, tol in (("01_magnesita_escalones.json", "nuevo", 0.01), ("06_revestimiento_gastado.json", "gastado", 0.02)):
        r = ve.correr(ve.abrir(EJEMPLOS / archivo))
        ref = estudio["escenarios"][estado]
        assert r.tiempo == pytest.approx(ref["tiempo_total_s"], rel=tol)
        cortes = [ref["pasos"][0]["t_inicio"]] + [p["t_fin"] for p in ref["pasos"]]
        for tramo, p in zip(r.tramos(cortes), ref["pasos"]):
            assert tramo["tiempo_s"] == pytest.approx(p["tiempo_s"], rel=0.04, abs=0.5)


def test_curvas_de_carga_y_drenado():
    c, d = ve.contexto_de({"planta": "pesqueria"})
    curvas = json.loads((RAIZ / "datos" / "estudios" / "vaciado_ebt_pesqueria.json").read_text(encoding="utf-8"))["curvas"]
    for a, seg, mini in zip(curvas["angulos"], curvas["nuevo"]["carga_segura_t"], curvas["nuevo"]["carga_minima_t"]):
        assert c.carga_segura(a) == pytest.approx(seg, abs=12.0)      # con la cavidad del programa (calibrada), no el barrido
        assert c.carga_minima(a) == pytest.approx(mini, abs=12.0)
    assert c.no_drenable(0.0) > 50.0 and c.no_drenable(12.0) < 1.0
    assert c.angulo_seguro(600.0, 15.0) == 0.0 and c.angulo_seguro(100.0, 15.0) == 15.0
    a = c.angulo_seguro(300.0, 15.0)
    assert c.carga_segura(a) == pytest.approx(300.0, abs=1.0)


def test_los_ejemplos_corren_y_respetan_el_panel():
    tiempos = {}
    for ruta in sorted(EJEMPLOS.glob("*.json")):
        r = ve.correr(ve.abrir(ruta), dt=0.5)
        assert r.motivo_fin.startswith("se alcanzó"), ruta.name
        assert r.colado == pytest.approx(300.0)
        tiempos[ruta.stem[:2]] = r.tiempo
    assert tiempos["03"] < tiempos["02"]            # bascular en continuo cuela antes que por escalones
    assert tiempos["04"] == pytest.approx(tiempos["03"] / 1.44, rel=0.01)
    r = ve.correr(ve.abrir(EJEMPLOS / "03_seguir_carga_segura.json"), dt=0.5)
    c = r.contexto
    assert all(m <= c.carga_segura(a) + 1.0 for m, a in zip(r.masa[5:], r.angulo[5:]))
    assert not any("panel" in texto for _, texto in r.eventos)


def test_escalones_y_avisos():
    c, _ = ve.contexto_de({"planta": "pesqueria"})
    r = simular(c, Hidraulica(), Escalones(((15.0, 0.0),)), 450.0, 30.0, dt=0.5)
    textos = " ".join(t for _, t in r.eventos)
    assert "panel" in textos and "arrastre" in textos       # 450 t a 15° invade el panel; con 30 t ya hay arrastre


def test_planta_sin_datos():
    with pytest.raises(FileNotFoundError):
        vd.cargar("largos_norte")


def test_excel_y_pdf(tmp_path):
    from modelo_vaciado import reporte as vr

    e = ve.abrir(EJEMPLOS / "05_perdidas_explicitas.json")
    r = ve.correr(e, dt=0.5)
    vr.escribir_excel(e, r, tmp_path / "v.xlsx")
    vr.escribir_pdf(e, r, tmp_path / "v.pdf")
    from openpyxl import load_workbook

    libro = load_workbook(tmp_path / "v.xlsx")
    assert libro.sheetnames == ["Resumen", "Datos", "Serie"] and libro["Serie"].max_row > 100
    assert "PRELIMINAR" in libro["Resumen"]["A2"].value
    assert any("supuesto" in str(f[2].value) for f in libro["Datos"].iter_rows(min_row=2))
    assert (tmp_path / "v.pdf").read_bytes()[:4] == b"%PDF"


def test_ventana(tmp_path):
    pytest.importorskip("PySide6")
    from modelo_vaciado.interfaz import tema_qt
    from modelo_vaciado.ventana import Ventana, aplicacion_qt

    qapp = aplicacion_qt()
    tema_qt.aplicar(qapp)
    v = Ventana(EJEMPLOS / "01_magnesita_escalones.json")
    h = v.horno
    assert h.resultado.tiempo == pytest.approx(413.4, abs=1.0)
    assert h.escenario()["basculado"]["pasos"][0] == [2.0, 380.0]
    h.tipo.setCurrentIndex(h.tipo.findData("carga_segura"))
    h.instantaneo.setChecked(False)
    h.diametro.setValue(240)
    assert h.calcular() and h.resultado.tiempo < 300
    for i in range(h.pestanas.count()):
        h.pestanas.setCurrentIndex(i)
        qapp.processEvents()
    h.instante.setValue(400)
    h.anadir_a_comparacion()
    h.mapa_coladas.setValue(40)
    assert h.calcular_mapas() and len(h.mapa_resultado[0]) == 16
    h.guardar_en(tmp_path / "e.json")
    assert ve.correr(ve.abrir(tmp_path / "e.json")).tiempo == pytest.approx(h.resultado.tiempo)
    for ext in ("xlsx", "pdf", "csv"):
        h.exportar_en(tmp_path / f"s.{ext}")
        assert (tmp_path / f"s.{ext}").stat().st_size > 500
    h.acero_final.setValue(500)                      # entrada no válida: avisa y no revienta
    assert not h.calcular() and "No se pudo calcular" in h.avisos.text()
    h.pasos.setText("esto no")
    h.tipo.setCurrentIndex(h.tipo.findData("escalones"))
    assert not h.calcular()
    # la página de la colada continua
    c = v.colada
    assert c.resultado is not None and len(c.resultado.ollas) == 4
    c.campos["valvula_diametro_mm"].setValue(100.0)
    assert c.estados["valvula_diametro_mm"].text().endswith("dato del usuario")      # la marca del estado va delante
    assert c.calcular() and "Sin avisos" in c.avisos.text()
    c.guardar_en(tmp_path / "c.json")
    from modelo_vaciado import colada_continua as cc
    assert cc.abrir(tmp_path / "c.json")["cambios"] == {"valvula_diametro_mm": 100.0}
    for ext in ("xlsx", "pdf", "csv"):
        c.exportar_en(tmp_path / f"c.{ext}")
        assert (tmp_path / f"c.{ext}").stat().st_size > 500
    c.campos["nivel_minimo_mm"].setValue(1200.0)
    assert not c.calcular() and "No se pudo calcular" in c.avisos.text()
    v.close()
    w = Ventana(EJEMPLOS / "colada_continua" / "03_mas_velocidad.json")   # un escenario de colada abre en su página
    assert w.paginas.currentIndex() == 1 and w.colada.campos["velocidad_m_min"].value() == 1.6
    w.close()
