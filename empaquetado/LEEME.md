# Ejecutable

`python empaquetado/construir.py` hace el ejecutable de TapFlow (con su icono) con PyInstaller (`pip install -r requirements.txt pyinstaller`). Corre en la
máquina donde se va a usar: un ejecutable de Windows se hace en Windows. Sale en `dist/<nombre>/` y en
`dist/<nombre>-<versión>-<sistema>.zip`; al terminar corre `--probar-ventana` con el ejecutable recién hecho. La CI de Windows lo
deja como artefacto.

En el equipo de planta, un `.exe` recién construido puede quedar bloqueado por la regla ASR de Windows Defender que impide abrir
ejecutables que la nube de Microsoft aún no conoce (visto con LWD-EAF; detalle en el documento
`docs/ejecutable-bloqueado-por-defender.md` de ese repositorio). Conviene construir con antelación y entregar sólo lo que ya abre.

El ejecutable deja fuera los módulos que el programa no usa y que otras bibliotecas arrastran si están instalados (SciPy, pandas,
lxml, Qt Quick, QML, red y PDF de Qt). En Linux el `.zip` bajó de 226 MB a 163 MB.
