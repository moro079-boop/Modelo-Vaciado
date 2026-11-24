# Por dónde continuar

Estado al 2026-11-24 (MV-003). Este documento se actualiza al final de cada sesión.

**En corto:** el modelo de vaciado se trasladó desde LWD-EAF (MV-001) y se redefinió hacia la estimación de tiempos de vaciado
(MV-002): dos escenarios, horno (EAF) → olla y olla → distribuidor, con un cálculo directo a partir de las variables del usuario
y, en el horno, el cálculo detallado con la cavidad 3D que ya existía. La ventana tiene cuatro diseños para elegir (MV-003).

## Dónde estamos

- **Cálculo directo:** `modelo_vaciado/flujo.py` y `escenarios.py`; comprobado contra la solución cerrada de Torricelli, contra el
  vaciado de la olla del módulo heredado y contra la cavidad 3D del horno a ángulo fijo (+1,5 %).
- **Ventana:** `python vaciado.py`; dos páginas y cuatro diseños (`--diseno`). Probada sólo sin pantalla.
- **Heredado sin cambios de cálculo:** horno con cavidad 3D y basculado, mapas, olla con la regla del LWD, válvula deslizante y
  secuencia olla → distribuidor → moldes (ésta, sólo por consola).

Última verificación (Linux, Python 3.13.18, PySide6 sin pantalla):

```text
python -m pytest verificacion -q -p no:cacheprovider
43 passed
```

## Lo siguiente

1. Que el usuario elija diseño, icono y nombre (decisiones N1 a N3 de [pendientes.md](pendientes.md)) y vea la ventana en
   Windows (la CI deja el ejecutable como artefacto).
2. Conseguir tiempos de vaciado medidos del horno y de la olla, con el peso vaciado y el diámetro del orificio, para fijar los
   coeficientes de descarga (fases 5 y 6 de [proyecto.md](proyecto.md)).
3. Refinar el cálculo directo: tabla volumen–altura dada por el usuario (CSV), basculado simple en el horno, crecimiento del
   orificio durante el vaciado.
4. Más adelante: el distribuidor → moldes como tercer escenario (el modelo ya existe en `colada_continua.py`).
