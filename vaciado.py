"""Vaciado-EAF: modelo de vaciado del acero por la piquera (EBT / OBT). Proyecto paralelo a LWD-EAF; preliminar.

    python vaciado.py                      abre la ventana
    python vaciado.py escenario.json       abre la ventana con ese escenario
    python vaciado.py --consola [...]      sin ventana: corre escenarios y escribe CSV y figura (ver --consola --help)
    python vaciado.py --curvas PLANTA      toneladas límite por ángulo, en texto
    python vaciado.py --colada [a.json]    olla → tundish → moldes, en texto
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

        print(f"Vaciado-EAF {VERSION_MODELO}")
        sys.exit(0)
    if args[:1] == ["--probar-ventana"]:
        from modelo_vaciado.ventana import probar_ventana

        sys.exit(probar_ventana())
    if args[:1] in (["--consola"], ["--curvas"], ["--colada"], ["-h"], ["--help"]):
        if args[0] in ("-h", "--help"):
            print(__doc__)
            sys.exit(0)
        from modelo_vaciado.__main__ import main as consola

        sys.exit(consola(args[1:] if args[0] == "--consola" else args))
    from modelo_vaciado.ventana import main

    sys.exit(main(args[0] if args else None))
