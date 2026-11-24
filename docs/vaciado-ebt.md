# Vaciado por el EBT: el estudio de Magnesita para Pesquería y su reproducción (EAF-064)

Estado al 2026-11-15. **Todo lo de este documento reproduce un cálculo teórico del proveedor; no hay ninguna medición de planta.**

- Fuente: plano AV00025170 rev. A de Magnesita Refratários (antes AV00014279_F, CRM 73899, cajetín del 22.09.2026, «for approval»), 9 hojas. El PDF no está en el repositorio.
- Transcripción: [`datos/estudios/vaciado_ebt_pesqueria.json`](../datos/estudios/vaciado_ebt_pesqueria.json), con el estado de cada dato.
- Reproducción: `python -m herramientas.vaciado_ebt` (tablas en pantalla y las tres figuras de `docs/figuras/vaciado_ebt_pesqueria_*.png`).
- CAD: `python -m herramientas.vaciado_ebt --cad` escribe en `reportes/cad_vaciado_ebt/` el sólido en STL (nuevo y gastado) y las vistas inclinadas en DXF. No es el CAD de Magnesita.
- Pruebas: `verificacion/test_vaciado_ebt.py`.

## 1. Qué trae el plano

| Hojas | Contenido |
|---|---|
| 1–2 | Revestimiento nuevo: secciones, planta, desarrollo, detalle del EBT (Ø200 a la salida) y marcas de 150 t y 150+300 t con ρ = 6,9 t/m³. |
| 3–6 | Cuatro desgastes del fondo (246, 50, 200 y 400 mm gastados de 696) con las marcas de 150 y 450 t a 0°. Sin cálculo de vaciado. |
| 7 | Vaciado de 300 t (450 → 150 t) con revestimiento nuevo, en cinco ángulos: 2°, 5°, 8°, 11° y 15°. |
| 8 | Lo mismo con el fondo en 348 mm (la mitad) y las paredes en 225 mm desde la hilada 6. |
| 9 | Drenado del talón de 150 t a 15°, para los dos estados. |

## 2. Cómo calculó Magnesita cada tabla

Es Torricelli cuasi-estático por escalones de ángulo:

1. **Toneladas por ángulo.** En cada vista inclinada el CAD da dos superficies de baño (inicio y final) y su tonelaje es volumen × 6,9 t/m³.
2. **Altura ferrostática.** El promedio de los dos niveles de la vista. Los niveles son cotas verticales desde el **centro de la boca del EBT** (la entrada del canal) hasta la superficie.
3. **Flujo.** Q = k·√h. Con Ø200 y 6,9 t/m³ equivale a Q = Cd·A·ρ·√(2·g·h) con **Cd = 0,731** (nuevo) y **0,741** (gastado). El plano lo llama «ajustado» y no explica el coeficiente ni por qué cambia entre estados.
4. **Tiempo.** Toneladas / Q; el total es la suma: 411,5 s (nuevo) y 413,8 s (gastado).

Los diez renglones se reproducen con cuatro cifras (`test_la_tabla_de_magnesita_es_torricelli_con_altura_media`).

Las gráficas:

- **«Bath level over time»**: el nivel sobre la boca del EBT; baja durante cada ángulo y salta al bascular (el basculado se supone instantáneo).
- **«Tapping over time»**: el acero que queda (negra); la carga con la que el baño queda a 300 mm del panel refrigerado a ese ángulo (amarilla); y la carga mínima antes del arrastre de escoria (roja).

## 3. El sólido reproducido

La geometría sale de `datos/plantas/pesqueria.json` (plano CS128936, el mismo horno): contorno en planta por sus cotas, casquete de C-C y rampa de A-A. El plano no dibuja el fondo fuera de esos dos cortes, así que la forma en 3D es un supuesto. Se compararon dos:

- **El del programa** (`lwd_eaf.cavidad_general`): en la mitad de la piquera mezcla por ángulo el casquete y la rampa. Necesita subir el piso 32,9 mm para dar las marcas a 0° (la calibración de EAF-050).
- **Barrido** (`herramientas/vaciado_ebt.py`): hacia la piquera, el perfil transversal del casquete trasladado a lo largo de la rampa. **Da las marcas a 0° sin calibrar.**

El desgaste se aplica como lo rotula cada hoja: el fondo retrocede perpendicular a su superficie y la pared ensancha el contorno desde la base de la hilada 6 (Y = 1 590).

Puntos de referencia, medidos sobre el trazo vectorial del PDF nuevo:

| Punto | X, Y (mm) | Cómo se obtuvo |
|---|---|---|
| Boca del EBT, nuevo | −5 000, 1 699 | Primera junta del canal en A-A de la hoja 1. La línea de referencia de los niveles pasa por su centro en las diez vistas (±2 mm). |
| Boca del EBT, gastado | −5 000, 1 447 | En la hoja 8 la boca está 252 mm más abajo (cinco vistas, ±1 mm). |
| Esquina del panel | −3 914, 3 089 | Arranque de la cota «304». Las cinco vistas de la hoja 7 dan el mismo punto. |

## 4. Resultados

**Marcas a 0°** (cota de la superficie en el eje; sólido − plano, mm):

| Hoja | Fondo gastado | Pared restante | 150 t | 450 t |
|---|---|---|---|---|
| 1 | 0 | 450 | −4 | +1 |
| 3 | 246 | 450 | +3 | +4 |
| 4 | 50 | 406 | 0 | −1 |
| 5 | 200 | 304,8 | 0 | −2 |
| 6 | 400 | 203,2 | +2 | +14 |

**Niveles inclinados** sobre la boca del EBT (sólido − plano, mm; inicio / final de cada ángulo):

| Ángulo | Nuevo (hoja 7) | Gastado (hoja 8) | Programa calibrado, nuevo | Programa dibujado, nuevo |
|---|---|---|---|---|
| 2° | +1 / −1 | +12 / +10 | +3 / +2 | −30 / −31 |
| 5° | −7 / −5 | +10 / +11 | −4 / −2 | −37 / −35 |
| 8° | −12 / −11 | +10 / +9 | −10 / −12 | −43 / −44 |
| 11° | −16 / −15 | +10 / +10 | −19 / −20 | −51 / −52 |
| 15° | −23 / −23 | +11 / +13 | −31 / −33 | −63 / −64 |

Con los niveles del sólido, la tabla de Magnesita da 413,1 s (nuevo) y 411,8 s (gastado): menos de 0,5 % de diferencia con el plano.

**Curvas de carga** (t; gráfica del plano, leída a ±5 t, y sólido):

| Ángulo | Segura, nuevo | Mínima, nuevo | Segura, gastado | Mínima, gastado |
|---|---|---|---|---|
| 2° | 453 / 451 | 290 / 291 | 638 / 632 | 353 / 350 |
| 5° | 385 / 383 | 202 / 205 | 560 / 556 | 257 / 254 |
| 8° | 316 / 314 | 132 / 136 | 484 / 479 | 178 / 176 |
| 11° | 255 / 253 | 83 / 87 | 408 / 404 | 122 / 119 |
| 15° | 192 / 190 | 43 / 47 | 323 / 320 | 72 / 70 |

- La amarilla es el baño a 300 mm, en vertical, por debajo de la esquina del panel.
- La roja sale con **700 mm de acero sobre la boca del EBT** (3,5 diámetros). El plano no escribe el criterio: es lo que la reproduce, no un dato del proveedor.

Figuras: [nuevo](figuras/vaciado_ebt_pesqueria_nuevo.png), [gastado](figuras/vaciado_ebt_pesqueria_gastado.png) y [curvas](figuras/vaciado_ebt_pesqueria_curvas.png).

## 5. Lo que no cuadra o queda abierto

- **El revestimiento nuevo se desvía con el ángulo**: de +1 mm a 2° hasta −23 mm a 15° (2 % de la altura, 1 % del flujo). El gastado no tiene esa tendencia (+10 mm constantes). El sólido tiene algo más de volumen hacia la piquera que el de Magnesita; no se encontró qué parte del fondo lo explica.
- **Hoja 9.** La tabla usa h = 469 y 449 mm, que son la mitad de 938 y 898: los niveles finales del paso de **2°** de las hojas 7 y 8. Con 150 t a 15° las mismas hojas acotan 1 200 y 1 021 mm; con su mitad el drenado daría unos 276 y 295 s, no 312 y 315. Puede ser una celda mal referenciada.
- **Nota 2 del plano, confirmada.** El sólido deja 0,2 t bajo la boca del EBT a 8° y nada desde 9° (revestimiento nuevo).
- **El coeficiente 0,731 / 0,741** no está explicado. Hipótesis sin confirmar: fricción en el canal, que se acorta con el desgaste.
- **El criterio de la curva roja** y **el reparto de toneladas entre ángulos** no están escritos.
- **Hoja 6, 450 t: +14 mm.** Con 400 mm de fondo gastado el retroceso perpendicular acotado deja de ser buena aproximación cerca de las paredes.

## 6. Límites del método de Magnesita, para el modelo de flujo

- La altura se mide a la entrada del canal. Con el canal lleno, la carga motriz llega a la salida; el Cd absorbe esa diferencia junto con las pérdidas.
- El promedio lineal de h vale para escalones cortos (0,1 % en los 300 t). En el drenado hasta cero deja de valer: siguiendo el nivel continuo del sólido, las 150 t a 15° salen en unos 253 s (nuevo), contra 276 s con la altura media y 312 s de la tabla, porque casi todo el acero está en la parte alta del baño.
- El basculado es instantáneo: no hay velocidad de inclinación.
- No hay escoria, vórtice ni crecimiento del diámetro del canal con las coladas.
- El plano da la relación tonelaje–nivel–ángulo solo en los pares dibujados. El sólido reproducido la da continua, que es lo que necesita integrar dM/dt = −ρ·Cd·A·√(2·g·H(M, θ)).
