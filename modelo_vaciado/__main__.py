"""El modelo de vaciado por consola.

    python -m modelo_vaciado --tiempo [a.json ...]   cálculo directo de los dos escenarios (por omisión, ejemplos/horno_olla/ y
                                                     ejemplos/olla_distribuidor/)
    python -m modelo_vaciado                         horno con cavidad 3D: corre ejemplos/horno_cavidad_3d/ y escribe en reportes/vaciado/
    python -m modelo_vaciado a.json b.json           corre esos escenarios
    python -m modelo_vaciado --curvas pesqueria      carga segura, carga mínima y acero no drenable por ángulo
    python -m modelo_vaciado --colada [a.json ...]   secuencia olla → distribuidor → moldes (etapa posterior al alcance actual;
                                                     por omisión, ejemplos/distribuidor_moldes/)
    python -m modelo_vaciado --salida CARPETA ...    otra carpeta de salida
    python -m modelo_vaciado --sin-archivos ...      solo el texto

(``python vaciado.py --consola ...`` en la raíz del repositorio hace lo mismo; sin argumentos, ``vaciado.py`` abre la ventana.)
"""

from __future__ import annotations

import sys
from pathlib import Path

from .rutas import raiz
from .texto import consola_utf8
from . import VERSION_MODELO
from .datos import cargar
from .escenario import abrir, contexto_de, correr
from .reporte import AVISO, escribir_csv, figura, resumen

RAIZ = raiz()


def curvas(planta: str) -> str:
    c, datos = contexto_de({"planta": planta})
    L = [f"{planta}: toneladas límite por ángulo (revestimiento nuevo, canal Ø{c.diametro:g} mm)",
         "  ángulo | carga segura (panel) | carga mínima (arrastre) | no drenable"]
    a = 0.0
    while a <= datos.angulo_maximo + 1e-9:
        L.append(f"  {a:>5.1f}° | {c.carga_segura(a):>20.0f} | {c.carga_minima(a):>23.0f} | {c.no_drenable(a):>11.1f}")
        a += 1.0
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    consola_utf8()
    argv = list(sys.argv[1:] if argv is None else argv)
    if "-h" in argv or "--help" in argv:
        print(__doc__)
        return 0
    print(f"Modelo de vaciado {VERSION_MODELO}. {AVISO}\n")
    if "--tiempo" in argv:
        from . import escenarios as es
        from .reporte_tiempo import texto

        rutas = [Path(a) for a in argv if not a.startswith("--")] or (
            sorted((RAIZ / "ejemplos" / "horno_olla").glob("*.json")) + sorted((RAIZ / "ejemplos" / "olla_distribuidor").glob("*.json")))
        for ruta in rutas:
            e = es.abrir(ruta)
            if e.get("formato") != es.FORMATO:
                print(f"{ruta.name}: es un escenario del horno con cavidad 3D o de la secuencia; se corre sin --tiempo o con --colada\n")
                continue
            print(texto(e, es.correr(e)) + "\n")
        return 0
    if "--colada" in argv:
        from . import colada_continua as cc
        from .reporte_colada import filas_de_resultado

        rutas = [Path(a) for a in argv if not a.startswith("--")] or sorted((RAIZ / "ejemplos" / "distribuidor_moldes").glob("*.json"))
        for ruta in rutas:
            r = cc.correr(cc.abrir(ruta))
            print(r.nombre)
            for a, b in filas_de_resultado(r):
                print(f"  {a}: {b}")
            for t, texto in r.eventos:
                print(f"  aviso a los {t / 60:.0f} min: {texto}")
            print()
        return 0
    if "--curvas" in argv:
        print(curvas(argv[argv.index("--curvas") + 1]))
        return 0
    salida = Path.cwd() / "reportes" / "vaciado"
    if "--salida" in argv:
        i = argv.index("--salida")
        salida = Path(argv[i + 1])
        del argv[i:i + 2]
    archivos = "--sin-archivos" not in argv
    rutas = [Path(a) for a in argv if not a.startswith("--")] or sorted((RAIZ / "ejemplos" / "horno_cavidad_3d").glob("*.json"))
    resultados = []
    for ruta in rutas:
        e = abrir(ruta)
        cargar(e["planta"])
        r = correr(e)
        resultados.append(r)
        print(resumen(r) + "\n")
        if archivos:
            salida.mkdir(parents=True, exist_ok=True)
            escribir_csv(r, salida / (ruta.stem + ".csv"))
    if archivos and resultados:
        figura(resultados, salida / "comparacion.png", "Vaciado por la piquera: escenarios")
        print(f"Series (CSV) y comparacion.png en {salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
