"""VaciaT: tiempo de vaciado del horno (EAF) a la olla y de la olla al distribuidor. Preliminar.

    python vaciado.py                      abre la ventana
    python vaciado.py escenario.json       abre la ventana con ese escenario
    python vaciado.py --tiempo [a.json]    cálculo directo de los dos escenarios, en texto
    python vaciado.py --consola [...]      horno con cavidad 3D, sin ventana: CSV y figura (ver --consola --help)
    python vaciado.py --curvas PLANTA      toneladas límite por ángulo del horno, en texto
    python vaciado.py --colada [a.json]    secuencia olla → distribuidor → moldes (etapa posterior), en texto
    python vaciado.py --probar-ventana     abre la ventana, calcula, exporta y la cierra (comprueba Qt y las gráficas)
    python vaciado.py --version
"""

import sys

if __name__ == "__main__":
    from modelo_vaciado.texto import consola_utf8

    consola_utf8()
    args = sys.argv[1:]
    if args[:1] == ["--version"]:
        from modelo_vaciado import VERSION_MODELO

        print(f"VaciaT {VERSION_MODELO}")
        sys.exit(0)
    if args[:1] == ["--probar-ventana"]:
        from modelo_vaciado.ventana import probar_ventana

        sys.exit(probar_ventana())
    if args[:1] in (["--consola"], ["--curvas"], ["--colada"], ["--tiempo"], ["-h"], ["--help"]):
        if args[0] in ("-h", "--help"):
            print(__doc__)
            sys.exit(0)
        from modelo_vaciado.__main__ import main as consola

        sys.exit(consola(args[1:] if args[0] == "--consola" else args))
    from modelo_vaciado.ventana import main

    sys.exit(main(args[0] if args else None))
