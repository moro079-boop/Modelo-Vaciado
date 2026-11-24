"""Vaciado-EAF: tiempos de vaciado del horno por la piquera (EBT u OBT), de la olla al tundish y del tundish a los moldes — proyecto paralelo a LWD-EAF (EAF-065, preliminar).

Integra en el tiempo dM/dt = −ρ·A·v, con la velocidad v dada por la carga de acero sobre la piquera y las pérdidas del canal, y con
el nivel del baño tomado de la cavidad 3D del programa para cada masa y cada ángulo de basculado. Documento: ``docs/vaciado/``.

Capas (separadas, como en el resto del programa):

- ``datos``       lo que la planta aporta: piquera, panel y valores por omisión (``datos/vaciado/<planta>.json``)
- ``tabla``       nivel del baño sobre la boca de la piquera en función de la masa y el ángulo (de la cavidad del programa)
- ``hidraulica``  velocidad y caudal por el canal (coeficiente de descarga o pérdidas explícitas)
- ``basculado``   cómo se inclina el horno durante la colada (escalones, seguir la carga segura, ángulo fijo)
- ``simulacion``  el integrador y su resultado
- ``escenario``   leer y correr un escenario guardado en JSON
- ``reporte``     texto, CSV y figura
- ``mapa``        tiempo del horno a ángulo fijo, por diámetro y por vida de la piquera
- ``olla``, ``valvula``, ``artesa``  olla (regla del LWD), válvula deslizante (regla del SGW), tundish y moldes
- ``colada_continua``  secuencia acoplada olla → tundish → moldes, con control de nivel y cambio de olla
- ``reporte_colada``   reportes de la colada continua
- ``ventana*``    la aplicación Vaciado-EAF (PySide6), con una página por etapa

**Preliminar:** ningún parámetro hidráulico está validado con tiempos de vaciado medidos en planta.
"""

VERSION_MODELO = "0.1.0-preliminar"
FORMATO_ESCENARIO = "lwd_eaf.vaciado/1"
