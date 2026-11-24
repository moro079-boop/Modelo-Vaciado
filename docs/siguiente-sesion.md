# Por dónde continuar

Estado al 2026-11-24 (MV-004, versión 0.2.0-preliminar). Este documento se actualiza al final de cada sesión.

**En corto:** TapFlow estima el tiempo de vaciado en dos escenarios, horno (EAF) → olla y olla → distribuidor, con un cálculo
directo a partir de las variables del usuario y, en el horno, el cálculo detallado con la cavidad 3D. Diseño, icono y nombre
están elegidos ([disenos.md](disenos.md)); la primera propuesta está archivada en la rama `archivo/disenos-iniciales`.

## Dónde estamos

- **Cálculo directo:** `modelo_vaciado/flujo.py` y `escenarios.py`; comprobado contra la solución cerrada de Torricelli, contra el
  vaciado de la olla del módulo heredado y contra la cavidad 3D del horno a ángulo fijo (+1,5 %).
- **Ventana:** `python vaciado.py`; abre en 0,7 s, recalcula en vivo, ajusta a 1 280 × 720. Probada sólo sin pantalla.
- **Ejecutable:** `python empaquetado/construir.py` (163 MB en Linux); la CI de Windows lo deja como artefacto.
- **Heredado sin cambios de cálculo:** horno con cavidad 3D y basculado, mapas, olla con la regla del LWD, válvula deslizante y
  secuencia olla → distribuidor → moldes (ésta, sólo por consola).

Última verificación (Linux, Python 3.13.18, PySide6 sin pantalla):

```text
python -m pytest verificacion -q -p no:cacheprovider
45 passed
```

## Lo siguiente

1. Abrir la ventana y el ejecutable en un escritorio de Windows (artefacto de la CI) y revisar el escalado a 125–200 %.
2. Conseguir tiempos de vaciado medidos del horno y de la olla, con el peso vaciado y el diámetro del orificio, para fijar los
   coeficientes de descarga (fases 5 y 6 de [proyecto.md](proyecto.md)).
3. Refinar el cálculo directo: tabla volumen–altura dada por el usuario (CSV), basculado simple en el horno, crecimiento del
   orificio durante el vaciado.
4. Más adelante: el distribuidor → moldes como tercer escenario (el modelo ya existe en `colada_continua.py`).
