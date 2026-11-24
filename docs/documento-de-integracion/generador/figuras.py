"""Figuras del documento de integración de Vaciado-EAF. Uso, desde la raíz del repositorio:

    python docs/vaciado/documento-de-integracion/generador/figuras.py

Escribe en esta carpeta: mapas_horno.png, secuencia_colada.png y olla.png. Las capturas de la ventana se toman de docs/figuras/.
"""

import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parents[2]
sys.path.insert(0, str(RAIZ))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from modelo_vaciado import colada_continua as cc  # noqa: E402
from modelo_vaciado import escenario as ve  # noqa: E402
from modelo_vaciado import mapa  # noqa: E402
from modelo_vaciado.reporte_colada import figura_secuencia  # noqa: E402

plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": 0.35})


def mapas():
    e = ve.abrir(RAIZ / "ejemplos" / "vaciado" / "03_seguir_carga_segura.json")
    filas = mapa.por_angulo(e, dt=1.0)
    col = mapa.por_colada(e, 150, 0.3, diametro_maximo=260, cada=5, dt=1.0)
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.8))
    a.plot([f.angulo for f in filas], [f.tiempo for f in filas], color="#25272A", lw=1.4)
    for f in filas:
        a.plot(f.angulo, f.tiempo, "o", color="#A93526" if f.invade_panel else "#3F6A24", ms=5)
    a.plot([], [], "o", color="#3F6A24", label="el baño inicial respeta el panel")
    a.plot([], [], "o", color="#A93526", label="el baño inicial invade el panel")
    a.set_xlabel("ángulo fijo, grados")
    a.set_ylabel("tiempo de vaciado (450 → 150 t), s")
    a.legend(fontsize=8)
    b.plot([c["colada"] for c in col], [c["tiempo_s"] for c in col], color="#25272A", lw=1.6)
    b2 = b.twinx()
    b2.plot([c["colada"] for c in col], [c["diametro"] for c in col], color="#8A5D00", ls="--", lw=1)
    b2.set_ylabel("diámetro del canal, mm", color="#8A5D00")
    b2.grid(False)
    b.set_xlabel("colada de la piquera")
    b.set_ylabel("tiempo de vaciado, s")
    fig.tight_layout()
    fig.savefig(AQUI / "mapas_horno.png", dpi=150)
    plt.close(fig)


def secuencia():
    r = cc.correr(cc.abrir(RAIZ / "ejemplos" / "vaciado" / "colada_continua" / "02_valvula_de_80.json"))
    fig, _ = plt.subplots(2, 2, figsize=(10, 6), sharex=True)
    figura_secuencia(r, fig)
    fig.tight_layout()
    fig.savefig(AQUI / "secuencia_colada.png", dpi=150)
    plt.close(fig)


def olla():
    fig, (a, b) = plt.subplots(1, 2, figsize=(10, 4))
    c = cc.configurar("pesqueria")
    g = c.olla.geometria
    z = np.linspace(0, g.altura, 400)
    rc = g.radio_cara_caliente(z)
    a.plot(rc, z, color="#25272A")
    a.plot(-rc, z, color="#25272A")
    a.plot([-rc[0], rc[0]], [c.olla.z_piso] * 2, color="#25272A")
    planta = cc.cargar_planta("pesqueria")
    for m in planta["olla"]["marcas"]["lista"]:
        a.axhline(m["z_mm"], color="#8A5D00", ls="--", lw=0.9)
        a.annotate(f"plano: {m['toneladas']:g} t", (-rc.max(), m["z_mm"]), xytext=(2, 2), textcoords="offset points", fontsize=7.5, color="#8A5D00")
        a.axhline(c.olla.cota(m["toneladas"]), color="#1F55D0", lw=0.9)
    a.plot([], [], color="#8A5D00", ls="--", label="marca del plano")
    a.plot([], [], color="#1F55D0", label="modelo, mismas toneladas")
    a.set_aspect("equal")
    a.set_xlabel("mm")
    a.set_ylabel("altura sobre la base de la coraza, mm")
    a.legend(fontsize=7.5, loc="lower center")
    for d, color in ((55.0, "#A93526"), (80.0, "#25272A")):
        cd = cc.configurar("pesqueria", {"valvula_diametro_mm": d})
        t, m = cc.vaciado_libre_olla(cd)
        b.plot(t / 60, m, color=color, label=f"válvula de {d:g} mm abierta: {t[-1] / 60:.0f} min")
    b.axhline(c.remanente, color="#5F6164", lw=0.8, ls=":")
    b.set_xlabel("tiempo, min")
    b.set_ylabel("acero en la olla, t")
    b.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(AQUI / "olla.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    mapas()
    secuencia()
    olla()
    print("figuras escritas en", AQUI)
