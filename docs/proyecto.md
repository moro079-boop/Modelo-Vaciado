# Vaciado-EAF: tiempos de vaciado del horno, la olla y el tundish

Documento de proyecto. Estado al 2026-11-20: versión del modelo 0.1.0-preliminar, con las etapas de horno, olla, tundish y moldes.

**Aviso general:** ningún parámetro hidráulico está validado con tiempos de vaciado medidos en planta. La geometría del horno y la de la olla proceden de planos; la válvula de la olla, el tundish y la máquina de colada continua se describen con valores supuestos o de ejemplo. Los resultados son escenarios, no pronósticos.

## 1. Objetivo y alcance

El proyecto persigue un programa que estime el tiempo de vaciado del acero líquido en las tres etapas de la acería:

- **Horno:** del horno de arco eléctrico (EAF) a la olla, por la piquera excéntrica de fondo (EBT) o por un canal de vaciado (OBT), según el ángulo de inclinación.
- **Olla:** de la olla al tundish de la máquina de colada continua (MCC), por la válvula deslizante.
- **Tundish:** del tundish a los moldes, por las buzas sumergidas, con la demanda que fija la velocidad de colada.

El programa debe servir para cualquier horno y máquina cuya geometría se describa en un archivo de datos, y debe permitir estudiar el efecto de la inclinación, del desgaste del revestimiento, del diámetro de los orificios, de la velocidad de colada y del cambio de olla.

El origen del proyecto es el estudio de vaciado por el EBT que el proveedor de refractarios dibujó en el plano AV00025170 del horno de Pesquería; su análisis y reproducción se describen en [../vaciado-ebt.md](vaciado-ebt.md).

## 2. Plan por fases

El plan ordena el trabajo de modo que cada fase entregue algo utilizable. Las fases 0 a 4 no dependen de datos de planta; las fases 5 a 7 sí.

| Fase | Contenido | Estado |
|---|---|---|
| 0 | Análisis del estudio del proveedor y reproducción de su cálculo | Hecha |
| 1 | Modelo del horno: nivel por masa y ángulo, hidráulica del canal, basculado e integración en el tiempo | Hecha |
| 2 | Aplicación propia con ventana, exportación a Excel, PDF y CSV, y ejecutable | Hecha |
| 3 | Mapas del horno (tiempo por ángulo fijo y por vida de la piquera), olla con válvula deslizante, tundish con control de nivel, moldes y secuencia de ollas | Hecha, con datos supuestos fuera del horno y de la olla |
| 4 | Interfaz Qt con los componentes de LWD-EAF: tarjetas, etiquetas de estado de cada dato, selectores y botones con la hoja de estilo Magnesita | En curso: las dos páginas usan tarjetas, estados y selectores; faltan los indicadores, la barra de herramientas de las gráficas, el escalado de pantalla y la prueba en un escritorio de Windows |
| 5 | Datos de planta: tiempos de vaciado medidos, diámetros de piquera y de válvula, geometría del tundish y de la máquina | Pendiente de datos |
| 6 | Calibración: coeficiente de descarga del horno y de la válvula con tiempos medidos; ley de crecimiento de la piquera | Pendiente de la fase 5 |
| 7 | Otras plantas y un horno con canal de vaciado (OBT) | Pendiente de datos |
| 8 | Extensiones: vórtice y arrastre de escoria con un criterio medido, temperatura del acero, plan de basculado óptimo con restricciones de proceso | Propuesta |

## 3. Fundamentos del modelo

Las tres etapas comparten el mismo principio: un recipiente que se vacía por un orificio. El caudal se obtiene de la ecuación de energía entre la superficie libre del recipiente y la salida del orificio, y la masa se integra en el tiempo.

### Balance de masa

Para un recipiente de masa M que recibe un caudal Q_ent y entrega un caudal Q_sal:

dM/dt = Q_ent − Q_sal

El horno y la olla sólo entregan; el tundish recibe de la olla y entrega a los moldes.

### Caudal por un orificio

Q = ρ · C_d · f_A · A · √(2 · g · H)

donde ρ es la densidad del acero líquido, C_d el coeficiente de descarga, f_A la fracción de área abierta (1 sin válvula), A el área del orificio y H la carga de acero, es decir, la diferencia de altura entre la superficie libre y la salida, descontada la contrapresión del recipiente de destino.

Cuando se conocen las pérdidas por separado, la velocidad se escribe como v = √(2·g·H / (1 + K + f·L/D)), con K la pérdida de entrada y f el factor de fricción de Darcy del canal de largo L y diámetro D. Ambas formas son equivalentes; la primera agrupa todas las pérdidas en C_d.

### Horno

- **Nivel:** la altura del acero sobre la boca de la piquera se obtiene de la cavidad tridimensional del horno, cortada por el plano inclinado de la superficie libre, para cada masa y cada ángulo.
- **Carga:** se mide desde la boca de la piquera, como en el estudio del proveedor, o desde la salida del canal, sumando su caída vertical con el canal lleno.
- **Basculado:** el ángulo sigue una de tres formas: escalones fijos, ángulo fijo o el mayor ángulo que deja 300 mm entre el baño y el panel refrigerado. Esta última es la más rápida posible con esa restricción, porque a mayor ángulo hay más acero sobre la piquera.
- **Límites:** a cada ángulo se calculan la carga segura (baño a 300 mm del panel), la carga mínima (altura mínima de acero sobre la boca, por debajo de la cual se arrastra escoria) y el acero que no puede salir.

### Olla

- **Geometría:** la coraza es un tronco de cono; la cara caliente es la coraza menos el aislante, la capa de seguridad y el espesor de trabajo de cada hilada. Es la misma regla del Ladle Wear Diagnosis (LWD), de modo que los niveles de los dos programas coinciden.
- **Carga:** altura del acero en la olla más la caída desde el piso de la olla hasta la salida del tubo largo, menos la altura del acero del tundish sobre esa salida.
- **Válvula deslizante:** dos orificios circulares de diámetro D desplazados una distancia e dejan abierta la fracción f_A = (2/π)·[arccos(x) − x·√(1 − x²)], con x = e/D. Es la relación que usa el modelo de desgaste de la válvula deslizante (SGW).

### Tundish y moldes

- **Geometría del tundish:** prisma de fondo rectangular con paredes en talud; el volumen hasta un nivel tiene forma cerrada.
- **Demanda de los moldes:** Q = n · ρ_s · a · e · v, con n líneas, ρ_s la densidad del acero sólido, a y e el ancho y el espesor del producto y v la velocidad de colada.
- **Buzas sumergidas:** cada una deja pasar como máximo Q = ρ·C_d·A·√(2·g·H), con H = nivel del tundish + largo de la buza bajo el fondo − inmersión en el molde. Si la demanda supera esa capacidad, la velocidad de colada baja.
- **Control de nivel:** la válvula de la olla deja pasar la demanda de los moldes más una corrección proporcional al error de nivel, Q = Q_moldes + ρ·A_tundish·(h_operación − h)/τ, sin exceder la válvula abierta del todo.

### Secuencia de ollas

Cada olla se abre con su acero y se cierra al quedar el remanente. Durante el cambio de olla el tundish sólo entrega; la olla siguiente repone primero lo perdido. Tras la última olla, el tundish se vacía hasta su nivel mínimo. Se avisa cuando la válvula de la olla, abierta del todo, ya no alcanza la demanda; cuando el tundish baja del mínimo en un cambio; cuando sobrepasa el máximo, y cuando las buzas limitan la velocidad.

### Integración

El sistema se integra con el método de Heun (predictor y corrector, de segundo orden) con paso fijo: 0,25 s en el horno y 1 s en la máquina. El último paso se acorta para terminar exactamente en la masa objetivo.

## 4. Datos y su procedencia

| Dato | Pesquería | Estado |
|---|---|---|
| Cavidad del horno | Plano CS128936 | Medido a escala, calibrado con las marcas del plano |
| Piquera del horno | Boca en X −5 000, Y 1 699 mm; Ø200 mm; largo 1 359 mm | Cota y medido a escala (plano AV00025170) |
| Coeficiente de descarga del horno | 0,731 | Implícito en el cálculo del proveedor; sin validar |
| Geometría de la olla | Plano CS129722 (300 t) | Heredado del LWD, sin verificar en este proyecto |
| Diámetro de la válvula de la olla | 55 mm | Tomado del SGW (válvula LG22L de otra olla): supuesto para Pesquería |
| Coeficiente de descarga de la válvula | 0,75 | Tomado del SGW, donde está por calibrar |
| Caída del piso de la olla a la salida del tubo | 900 mm | Supuesto |
| Acero remanente en la olla | 3 t | Supuesto |
| Tundish | 7 000 × 1 000 mm de fondo, talud 10°, niveles 500, 1 100 y 1 300 mm | Ejemplo |
| Moldes | Una línea de 1 600 × 250 mm a 1,2 m/min; buza de Ø80 mm | Ejemplo |
| Secuencia | Cuatro ollas de 300 t; cambio de 180 s | Ejemplo |

Cada valor lleva su estado en el archivo de datos, en la ventana (con una marca y un color por estado) y en los reportes.

## 5. Verificación

| Comprobación | Resultado |
|---|---|
| Recipiente prismático contra la solución de Torricelli | Igual a una parte en 100 000 |
| Paso de tiempo de 2 s contra 0,1 s | Menos de 0,1 % |
| Estudio del proveedor, horno nuevo (300 t) | 413,4 s contra 411,5 s (+0,5 %) |
| Estudio del proveedor, horno gastado | 408,0 s contra 413,8 s (−1,4 %) |
| Olla de Pesquería contra las marcas de su plano | 304,1 t a la cota de 300 t; 257,6 t a la de 255 t (criterio del LWD: 5 %) |
| Olla cilíndrica con la válvula abierta contra Torricelli | A 0,2 % |
| Volumen del tundish, forma cerrada contra integración numérica | A una parte en un millón |
| Conservación de masa en la secuencia de ollas | A 1 % (por el muestreo de la serie) |
| Mapa por vida de la piquera contra el cálculo directo | A 0,2 % |

Reproducir el estudio del proveedor comprueba que el modelo hace bien la misma cuenta, pero no que la cuenta sea cierta.

## 6. Resultados de ejemplo

### Horno de Pesquería (450 → 150 t, revestimiento nuevo)

| Escenario | Tiempo | Caudal medio |
|---|---|---|
| Escalones del proveedor, basculado instantáneo | 413 s | 43,5 t/min |
| Mismos escalones, basculando a 1 °/s | 414 s | 43,5 t/min |
| Basculado continuo hasta lo que permite el panel | 386 s | 46,6 t/min |
| Igual, con el canal en Ø240 mm | 268 s | 67,1 t/min |
| Igual, con pérdidas explícitas y carga hasta la salida | 255 s | 70,6 t/min |
| Escalones del proveedor, revestimiento gastado | 408 s | 44,1 t/min |

A ángulo fijo el tiempo baja de 614 s a 0° a 335 s a 15°, pero desde 3° el baño inicial de 450 t queda a menos de 300 mm del panel. Con el canal creciendo 0,3 mm por colada (valor supuesto), el tiempo baja de 386 s en la colada 1 a 292 s en la colada 101.

### Máquina de colada continua (datos de ejemplo)

| Escenario | Colado de una olla | Observación |
|---|---|---|
| Válvula de 55 mm, 1,2 m/min | 78 min | La válvula abierta no alcanza la demanda desde que quedan 90 t |
| Válvula de 80 mm, 1,2 m/min | 78 min | Sólo al final (14 t) la válvula no alcanza la demanda |
| Válvula de 80 mm, 1,6 m/min | 58 min | La válvula no alcanza la demanda desde que quedan 31 t |
| Válvula de 80 mm, cambio de olla de 10 min | 71 min | El tundish baja a 509 mm en cada cambio, a 9 mm del mínimo |

Con la máquina a velocidad constante, el colado de una olla lo fija la demanda de los moldes y no la válvula, salvo al final de la olla, cuando la carga ya no alcanza. El vaciado con la válvula abierta del todo es la cota inferior: 78 min con 55 mm y 37 min con 80 mm.

## 7. Límites

- **Validación:** ninguna cifra se ha contrastado con tiempos medidos.
- **Flujo:** el canal se supone lleno y el chorro libre; no se modelan el vórtice ni la entrada de aire.
- **Escoria:** el arrastre sólo se señala; no se calcula cuánta escoria pasa. En la olla y el tundish no se modela la escoria.
- **Desgaste de los orificios:** el diámetro es constante dentro de una colada; su crecimiento entre coladas sólo se estudia con una tasa supuesta.
- **Control:** el control de nivel del tundish es proporcional e ideal; el control real de la válvula, con su retardo y su banda muerta, no se modela.
- **Térmica:** no se considera la temperatura del acero ni la solidificación en los orificios.

## 8. Datos que hacen falta

| Dato | Para qué |
|---|---|
| Tiempos de vaciado medidos por colada en el horno, con el peso vaciado y la edad de la piquera | Fijar la hidráulica del horno |
| Diámetro de la piquera nueva y al cambiarla, o su tasa de crecimiento | Ley de desgaste de la piquera |
| Secuencia real de basculado y velocidad mecánica de basculado del horno | Forma de bascular y su límite |
| Diámetro de las placas de la válvula de la olla de Pesquería, carrera y caída hasta la salida del tubo | Válvula de la olla |
| Serie de peso de la olla durante la colada (ya la usa el SGW) | Coeficiente de descarga de la válvula |
| Geometría del tundish: planta, talud, niveles de operación, mínimo y máximo | Tundish |
| Formato, número de líneas, velocidades, buzas sumergidas e inmersión | Moldes |
| Tiempo de cambio de olla y acero remanente | Secuencia |

## 9. Software

### Organización

| Módulo | Contenido |
|---|---|
| `tabla.py` | Nivel del baño del horno por masa y ángulo, tabulado desde la cavidad tridimensional |
| `hidraulica.py` | Velocidad y caudal por el canal del horno |
| `basculado.py` | Formas de bascular el horno |
| `simulacion.py` | Integración del vaciado del horno, límites por ángulo y avisos |
| `mapa.py` | Tiempo a ángulo fijo, por diámetro y por vida de la piquera; comparación con el basculado óptimo |
| `olla.py` | Geometría de la olla con la regla del LWD y nivel por masa |
| `valvula.py` | Fracción abierta de la válvula deslizante y caudal por un orificio |
| `artesa.py` | Tundish y moldes |
| `colada_continua.py` | Configuración, secuencia acoplada olla–tundish–moldes y cálculos de una sola pieza |
| `escenario.py`, `reporte.py`, `reporte_colada.py` | Escenarios en JSON y reportes en texto, CSV, Excel y PDF |
| `ventana.py`, `ventana_colada.py`, `ventana_formulario.py` | Ventana de PySide6 con las páginas del horno y de la colada continua |

Los datos viven en `datos/vaciado/<planta>.json` (horno) y `datos/vaciado/colada_continua/<planta>.json` (olla, válvula, tundish y moldes); los escenarios de ejemplo, en `ejemplos/vaciado/` y `ejemplos/vaciado/colada_continua/`.

### Uso

```text
python vaciado.py                          ventana
python vaciado.py escenario.json           ventana con ese escenario (de horno o de colada continua)
python vaciado.py --consola [a.json ...]   horno, sin ventana: CSV y figura en reportes/vaciado/
python vaciado.py --colada [a.json ...]    colada continua, sin ventana
python vaciado.py --curvas pesqueria       límites del horno por ángulo
python vaciado.py --probar-ventana         comprobación de la ventana y las exportaciones
python empaquetado/construir_vaciado.py    ejecutable sin Python
```

La ventana tiene dos páginas. «Horno (EAF) → olla» contiene el escenario del horno y las pestañas Colada, Corte, Límites, Comparar y Mapas. «Olla → tundish → moldes» contiene los datos de la máquina, cada uno con su estado, y las pestañas Secuencia, Olla y Tundish y moldes. En las dos, la columna derecha muestra el resultado, los avisos y los botones para abrir, guardar y exportar.

### Agregar una planta

1. La geometría del horno debe existir en `datos/plantas/`.
2. Los datos de vaciado del horno se agregan en `datos/vaciado/<planta>.json`. En un horno con canal de vaciado, el tipo es `OBT` y la inclinación del canal es distinta de cero.
3. La olla, la válvula, el tundish y los moldes se agregan en `datos/vaciado/colada_continua/<planta>.json`. La geometría de la olla tiene el formato del LWD.

### Pruebas

`verificacion/test_vaciado_ebt.py`, `verificacion/test_vaciado_modelo.py` y `verificacion/test_vaciado_colada_continua.py` (30 pruebas en total).

## 10. Bitácora del proyecto

| Fecha | Entrada |
|---|---|
| 2026-11-15 | EAF-064: estudio del proveedor transcrito y reproducido |
| 2026-11-15 | EAF-065: primera versión del modelo del horno |
| 2026-11-16 | EAF-066: aplicación propia, con ventana y ejecutable |
| 2026-11-20 | EAF-069: mapas del horno, olla, válvula deslizante, tundish, moldes y secuencia de ollas; página de colada continua; primera parte de la interfaz Qt con los componentes de LWD-EAF; documento de integración del proyecto |
