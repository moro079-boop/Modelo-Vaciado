# Versiones

Este documento describe cómo se numeran las versiones de VaciaT y registra cada una.

## Esquema

La versión vive sólo en `modelo_vaciado/__init__.py` (`VERSION_MODELO`) y tiene la forma `MAYOR.MENOR.PARCHE-preliminar`.

- **Mayor:** cambia el significado de los resultados o se rompe la compatibilidad de los archivos de escenario.
- **Menor:** se agrega una capacidad (un escenario, un modelo, una vista) o cambia un resultado numérico.
- **Parche:** correcciones y mejoras que no mueven ningún resultado ni ningún formato.
- **Sufijo «preliminar»:** se mantiene mientras ningún parámetro hidráulico esté validado con tiempos de vaciado medidos.

La versión se sube con cada cambio que lo amerite según este esquema (decisión del usuario del 2026-11-24).

## Registro

| Versión | Cambio | Contenido |
|---|---|---|
| 0.1.0-preliminar | EAF-065 a EAF-069 (LWD-EAF), MV-001 | Modelo del horno con cavidad 3D, olla, válvula, distribuidor, moldes y secuencia; trasladado a este repositorio |
| 0.2.0-preliminar | MV-002 a MV-004 | Cálculo directo con las variables del usuario; dos escenarios (horno → olla y olla → distribuidor); formato de escenario `modelo_vaciado.escenario/1`; programa VaciaT con su diseño, icono y optimizaciones de la ventana |
