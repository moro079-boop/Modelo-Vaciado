"""Modelo de vaciado: tiempo que tarda un recipiente de acero líquido en vaciarse, con las ecuaciones de flujo. Preliminar.

Escenarios del alcance actual: horno (EAF) → olla y olla → distribuidor. Documento: ``docs/proyecto.md``.

Capas (separadas: el cálculo no importa Qt):

- ``flujo``, ``escenarios``  cálculo directo con las variables del usuario (recipiente, área de paso, hidráulica, destino)
- ``datos``, ``tabla``, ``hidraulica``, ``basculado``, ``simulacion``, ``escenario``, ``mapa``  horno con su cavidad 3D
  (``horno3d``), basculado y límites del panel
- ``olla``, ``valvula``, ``artesa``  olla (regla del LWD), válvula deslizante (regla del SGW), distribuidor y moldes
- ``colada_continua``  secuencia olla → distribuidor → moldes (etapa posterior; sólo por consola)
- ``reporte``, ``reporte_tiempo``, ``reporte_colada``  texto, CSV, Excel y PDF
- ``ventana``, ``ventana_tiempo``, ``ventana_colada``, ``interfaz``  la ventana (PySide6) y sus diseños

**Preliminar:** ningún parámetro hidráulico está validado con tiempos de vaciado medidos en planta.
"""

VERSION_MODELO = "0.1.0-preliminar"
FORMATO_ESCENARIO = "lwd_eaf.vaciado/1"
