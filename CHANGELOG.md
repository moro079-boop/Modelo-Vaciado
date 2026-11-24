# Bitácora de cambios

Cada modificación agrega una entrada (`MV-NNN`) con motivo, resultado, evidencia y pendientes. La entrada más reciente va arriba.

## 2026-11-24

### MV-004: VaciaT 0.2.0-preliminar: diseño, icono y nombre elegidos; optimizaciones de la ventana y del ejecutable

- Motivo: decisiones del usuario del 2026-11-24 sobre la primera propuesta (MV-003): diseño «Plano» con la estructura del diseño
  «Turno»; icono del reloj en la paleta de «Plano», con fondo oscuro; nombre VaciaT; archivar lo demás como historial; subir la
  versión (y, en adelante, subirla según los cambios); sumar este repositorio a la lista de `docs/estilo-de-documentos.md`; y
  aplicar las optimizaciones que hagan falta, con las de LWD-EAF como referencia.
- Diseño, icono y nombre:
  - Un solo diseño, VaciaT: la paleta de «Plano» pasa a `interfaz/tema.py` (los roles de LWD-EAF se conservan) y el acomodo de
    tablero de «Turno» (cabecera oscura con la marca y los pasos, cuatro indicadores grandes) a `ventana.py` y `tema_qt.py`.
    Se retiraron el selector de diseño, `interfaz/disenos.py` y la opción `--diseno`.
  - Icono: reloj de arena en la paleta VaciaT sobre la tinta oscura de la cabecera (`herramientas/iconos.py`); es el de la
    ventana y el del ejecutable.
  - Nombre: VaciaT en la ventana, el ejecutable (`dist/VaciaT/`) y los mensajes.
  - Historial: rama `archivo/disenos-iniciales` (commit `f78fadf`, con los cuatro diseños y el selector) y, en
    `docs/historial/disenos-iniciales/`, las capturas y la lámina de iconos.
- Optimizaciones (equivalentes a las de LWD-EAF, EAF-017 a EAF-053):
  - **Apertura de la ventana:** de 3,1 s a 0,7 s. La vista del horno con la cavidad 3D se arma al primer uso y un hilo, una sola
    vez por proceso, prepara su tabla de niveles 1,5 s después de abrir la ventana (como el precalentado de EAF-053).
  - **Recálculo en vivo** en las páginas del cálculo directo: 250 ms después del último cambio (cálculo y dibujo, unos 0,25 s
    medidos). La vista con la cavidad 3D (0,6 s por cálculo) no recalcula sola: marca el resultado como desactualizado y la
    franja del indicador pasa a gris hasta pulsar «Calcular» (equivalente a I1 de la auditoría de EAF-018). Un cálculo fallido
    pone la franja en rojo.
  - **Sólo se dibuja la pestaña visible;** las demás se dibujan al elegirlas.
  - **Barra de las gráficas** (vista inicial, desplazar, ampliar, guardar la imagen) con ayudas en español e iconos en el color
    del diseño (Matplotlib los pintaba blancos sobre el fondo claro).
  - **Teclado:** F5, Ctrl+1 / Ctrl+2, Ctrl+O, Ctrl+S, Ctrl+E, Ctrl+P y Ctrl+Shift+C (copia el resumen del resultado); la barra de
    estado los recuerda (como el pie de atajos de EAF-018).
  - **1 280 × 720** (como EAF-052): la columna del resultado se desplaza si no cabe, los botones de archivo van en una rejilla
    compacta, los selectores tienen textos cortos con la explicación en la ayuda emergente, el tiempo no se repite junto a los
    indicadores y la ventana no baja de 1 180 × 680.
  - **Unidades:** las series del horno con cavidad 3D pasan a minutos y t/min, como las del cálculo directo (sólo presentación).
  - **Sesión:** la ventana recuerda su tamaño, su posición y el escenario activo entre sesiones.
  - **Ejecutable:** deja fuera los módulos que no usa (SciPy, pandas, lxml, Qt Quick, QML, red y PDF de Qt); en Linux el `.zip`
    bajó de 226 MB a 163 MB y el ejecutable pasa su propia prueba de ventana.
- Versión 0.2.0-preliminar (`docs/versiones.md`, nuevo): capacidad nueva (cálculo directo), formato de escenario nuevo y alcance
  redefinido. Los resultados heredados no cambian.
- `docs/estilo-de-documentos.md`: Modelo-Vaciado se suma a la lista de proyectos («los cinco»).
- Impacto numérico: ninguno.
- Verificación (Linux, Python 3.13.18, PySide6 sin pantalla): `python -m pytest verificacion -q -p no:cacheprovider`:
  `45 passed`, sin advertencias; `ruff check .`: limpio; `python vaciado.py --probar-ventana`: «ok, ventana abierta en 0.7 s»;
  `python empaquetado/construir.py`: ejecutable de Linux construido y probado. Capturas a 1 440 × 880 y 1 280 × 720 revisadas.
  **No se ha abierto en un escritorio de Windows.**
- Pendientes: la lista de proyectos de `docs/estilo-de-documentos.md` debe cambiarse también en los otros cuatro repositorios
  (no se modifican desde aquí); ver la ventana y el ejecutable en Windows.

### MV-003: Tres diseños nuevos de la ventana, opciones de icono y de nombre

- Motivo: el usuario pidió tres diseños nuevos de interfaz con Qt como motor, y opciones de iconos y de nombres.
- Resultado:
  - `modelo_vaciado/interfaz/disenos.py`: diseños **Colada** (oscuro, navegación lateral e indicadores), **Plano** (técnico,
    barra de marca y pestañas planas) y **Turno** (alto contraste, letra grande, tablero con pasos e indicadores), además de
    **Magnesita** (el heredado). Un diseño es una paleta de roles, un tamaño de letra, una hoja de estilo adicional, un acomodo y
    un icono; se aplica antes de construir la ventana y lo siguen los widgets y las gráficas.
  - La ventana cambia de diseño desde «Ver → Diseño de la ventana» (el escenario en pantalla pasa al diseño nuevo) o con
    `python vaciado.py --diseno <nombre>`.
  - `herramientas/iconos.py`: cuatro opciones de icono dibujadas con Qt (Chorro, Torricelli, Reloj, Piquera), en PNG e ICO.
  - `herramientas/capturas.py`: capturas de cada diseño en `docs/figuras/disenos/`.
  - `docs/disenos.md`: diseños, iconos y seis opciones de nombre. Nada está elegido (decisiones N1 a N3).
  - `tema.estilo_matplotlib` fija 100 ppp en las figuras: un `matplotlibrc` del sistema con otra resolución duplicaba la letra de
    las gráficas en la ventana.
- Verificación: ver MV-002 (las mismas corridas cubren los cuatro diseños: `test_ventana_y_disenos` y
  `python vaciado.py --probar-ventana --diseno <nombre>` con los cuatro, «ok»). Las capturas se tomaron sin pantalla
  (plataforma `offscreen`): **nadie ha visto los diseños en un escritorio de Windows**.
- Pendientes: elegir diseño, icono y nombre (N1 a N3).

### MV-002: Cálculo directo del tiempo de vaciado con las variables del usuario; alcance de dos escenarios

- Motivo: el usuario pidió que el fin principal del programa sea estimar tiempos de vaciado, con variables definidas por el
  usuario (área de paso, altura metalostática, tonelaje…), y que los escenarios posibles sean sólo horno (EAF) → olla y olla →
  distribuidor, sin quitar nada fundamental.
- Resultado:
  - `modelo_vaciado/flujo.py` (nuevo): recipiente prismático (dimensionado con el tonelaje y la altura metalostática),
    troncocónico (con la relación de diámetros) o tabulado (la olla de una planta); área de paso por diámetro o por área;
    coeficiente de descarga o pérdidas explícitas (entrada y fricción de Darcy); caída bajo el orificio; fracción abierta de la
    válvula; destino libre, a nivel constante o que se llena. Integración de Heun y solución cerrada de Torricelli.
  - `modelo_vaciado/escenarios.py` (nuevo): los dos escenarios, formato `modelo_vaciado.escenario/1`, valores por omisión con su
    estado y procedencia. `abrir` reconoce también los formatos heredados.
  - `modelo_vaciado/reporte_tiempo.py` (nuevo): texto, CSV, Excel con gráficas nativas y PDF.
  - `modelo_vaciado/ventana_tiempo.py` (nuevo): página del cálculo directo con las pestañas Vaciado, Esquema, Sensibilidad
    (diámetro y C_d) y Comparar, y el estado de cada dato.
  - `modelo_vaciado/ventana.py`: dos páginas, «Horno (EAF) → olla» (conmutador entre el cálculo directo y la cavidad 3D con
    basculado, que se conserva entera) y «Olla → distribuidor». La secuencia olla → distribuidor → moldes sale de la ventana pero
    se conserva en el código, en sus pruebas y por consola (`--colada`); un escenario de ese tipo se rechaza con un aviso.
  - `python vaciado.py --tiempo`: los dos escenarios por consola. Once ejemplos nuevos en `ejemplos/horno_olla/` y
    `ejemplos/olla_distribuidor/`. Los ejemplos heredados pasaron a `ejemplos/horno_cavidad_3d/` y
    `ejemplos/distribuidor_moldes/`.
  - Nombre provisional de la ventana y del ejecutable: «Modelo-Vaciado» (antes «Vaciado-EAF»; decisión N1).
  - Estados nuevos en la interfaz: «cálculo del proveedor» (◇) y «ejemplo» (□).
- Impacto numérico: ninguno en los cálculos heredados (horno con cavidad 3D y secuencia); las 30 pruebas heredadas siguen
  pasando. `test_ventana` se adaptó a la ventana nueva sin cambiar lo que comprueba del horno ni de la página de la secuencia.
- Evidencia (cálculo directo):
  - Prisma contra la solución cerrada de Torricelli, con caída, contrapresión y válvula: a una parte en 10 000.
  - Olla de Pesquería con el distribuidor a 1 100 mm: 4 664,1 s, igual que `colada_continua.vaciado_libre_olla`.
  - Horno de Pesquería como prisma (450 t, 969 mm y 94,5 t de talón, tomados de la cavidad a 0°): 622 s, contra 613,5 s de la
    cavidad 3D a ángulo fijo 0° (+1,5 %).
  - Llenado del distribuidor: la masa recibida coincide con la vaciada a 0,2 %.
- Verificación (Linux, Python 3.13.18, PySide6 sin pantalla): `python -m pytest verificacion -q -p no:cacheprovider`:
  `43 passed`; `ruff check .`: limpio; `python vaciado.py --probar-ventana` con los cuatro diseños: «ok».
- Pendientes: datos medidos de tiempos de vaciado; la densidad de 7,0 t/m³ que se usa si un escenario no la trae es un supuesto.

### MV-001: Traslado del modelo de vaciado desde LWD-EAF

- Motivo: el modelo de vaciado nació como proyecto paralelo dentro de LWD-EAF (EAF-064 a EAF-069). Se abre este repositorio para
  que el modelo crezca por su cuenta, con el objetivo de estimar tiempos de vaciado con las ecuaciones de flujo (decisión del
  usuario del 2026-11-24).
- Origen: `moro079-boop/LWD-EAF`, rama `main`, commit `d3c7ad23dbb6794de3347e408849f00c4e868e0a` (2026-11-23).
- Qué se copió:
  - `lwd_eaf/vaciado/*.py` → `modelo_vaciado/` (sin cambios de cálculo; sólo las importaciones).
  - Motor geométrico del horno que el modelo usa (`cache`, `cavidad`, `cavidad_general`, `desgaste`, `geometria`, `niveles`,
    `planta`) → `modelo_vaciado/horno3d/`, con `PROCEDENCIA.md`.
  - `rutas.py`, `texto.py` → `modelo_vaciado/`; `interfaz/{tema,tema_qt,widgets,formato}.py` e icono →
    `modelo_vaciado/interfaz/`, con `PROCEDENCIA.md`.
  - `datos/plantas/` (las siete plantas), `datos/vaciado/`, `datos/estudios/`, `ejemplos/vaciado/`.
  - `herramientas/vaciado_ebt.py`, `verificacion/test_vaciado_*.py`, `vaciado.py`, `empaquetado/construir_vaciado.py` (ahora
    `empaquetado/construir.py`).
  - `docs/vaciado/proyecto.md` (ahora `docs/proyecto.md`), `docs/vaciado-ebt.md`, el documento de integración en Word con su
    generador (ahora en `docs/documento-de-integracion/`, con `lib2.js`, `paginar.py` y el logotipo del documento de
    LWD-EAF), las figuras `docs/figuras/vaciado_*.png`, `docs/estilo-de-documentos.md` y `docs/plantilla-cambio.md`.
- Qué no se copió: el resto de LWD-EAF (campaña de desgaste, calibración, ventana de LWD-EAF, lectura de planos).
- Impacto numérico: ninguno. Los formatos de archivo (`lwd_eaf.vaciado/1`, `lwd_eaf.vaciado.planta/1`,
  `lwd_eaf.vaciado.colada_continua/1`, `lwd_eaf.vaciado.colada/1`, `lwd_eaf.planta/1`) se conservan.
- Verificación (Linux, Python 3.13.18, PySide6 sin pantalla): `python -m pytest verificacion -q -p no:cacheprovider`:
  `30 passed` (las mismas 30 pruebas que en LWD-EAF, que también dan `30 passed` en el commit de origen);
  `python vaciado.py --probar-ventana`: «ventana abierta, calculada (horno 386 s; olla 78 min), exportada y cerrada»;
  `ruff check .`: limpio.
- Pendientes: los de LWD-EAF para el modelo (decisiones W, X e Y de aquel repositorio), trasladados a `docs/pendientes.md`.

## Historia heredada de LWD-EAF

Entradas del registro de cambios de LWD-EAF que corresponden al modelo de vaciado, copiadas sin cambios. Las rutas que citan son
las de aquel repositorio.

#### EAF-064 — Pesquería: el estudio de vaciado por el EBT de Magnesita, transcrito y reproducido

- Solicitud (usuario, 2026-11-15): analizar el plano AV00025170 rev. A de Magnesita, que trae el cálculo del tiempo de vaciado por el EBT según el ángulo y el tonelaje; descubrir cómo se hizo cada tabla y, después, «reproducir el CAD con el que se hizo el cálculo, así como los escenarios de inclinación con las cargas». El objetivo declarado es llegar a un modelo de vaciado basado en las ecuaciones de flujo, para este y otros hornos (EBT u OBT). El PDF queda fuera del repositorio.
- Resultado:
  - `datos/estudios/vaciado_ebt_pesqueria.json` (carpeta nueva): lo que el plano escribe (tablas, cotas de nivel, marcas a 0° de cinco desgastes), las curvas leídas de la gráfica y los puntos de referencia medidos a escala, cada uno con su estado.
  - `herramientas/vaciado_ebt.py`: construye el sólido nuevo y gastado, calcula los niveles de cada vista inclinada, las curvas de carga segura y mínima, rehace la tabla de Magnesita y dibuja tres figuras (`docs/figuras/vaciado_ebt_pesqueria_{nuevo,gastado,curvas}.png`).
  - `docs/vaciado-ebt.md`: cómo calculó Magnesita (Torricelli con la altura media de cada ángulo, Cd implícito 0,731 nuevo y 0,741 gastado, niveles medidos desde el centro de la boca del EBT), la reproducción y lo que no cuadra.
  - `python -m herramientas.vaciado_ebt --cad` escribe en `reportes/cad_vaciado_ebt/` (sin versionar) el sólido de la cavidad en STL, nuevo y gastado, y las vistas inclinadas con sus niveles en DXF. El volumen de la malla coincide con el del sólido (98,97 y 129,08 m³ hasta Y 3 290).
  - `verificacion/test_vaciado_ebt.py`: 9 pruebas.
- Evidencia: con el fondo de la piquera construido por **barrido** (el perfil del casquete trasladado a lo largo de la rampa; supuesto de la herramienta) las marcas de 150 y 450 t a 0° de las cinco hojas salen a ±4 mm **sin calibrar** (una a +14); los niveles inclinados, de +1 a −23 mm con revestimiento nuevo y +9 a +13 con el gastado; las curvas de carga, a ≤ 6 t; los tiempos totales, a menos de 0,5 %. La cavidad del programa (calibrada +32,9 mm) da de +3 a −33 mm en los niveles inclinados del revestimiento nuevo; dibujada, de −30 a −64.
- Impacto numérico: ninguno. No cambian el programa (`lwd_eaf`), `pesqueria.json` ni la versión.
- Verificación (Linux, Python 3.13.18, NumPy 2.5.3, matplotlib 3.11, sin PySide6): `python -m pytest verificacion/test_vaciado_ebt.py verificacion/test_pesqueria.py -q -p no:cacheprovider`: `17 passed`. `ruff check herramientas/vaciado_ebt.py verificacion/test_vaciado_ebt.py`: limpio. **La suite completa no se terminó de correr en esta sesión** (en un solo proceso y sin PySide6 llevaba el 25 % sin fallos cuando se detuvo); el cambio no toca `lwd_eaf` ni los archivos de planta.
- Límites y pendientes: es la reproducción de un cálculo teórico del proveedor, no una validación. El revestimiento nuevo se desvía con el ángulo (−23 mm a 15°) sin causa encontrada. La hoja 9 usa una altura que no cuadra con las hojas 7 y 8. El criterio de la carga mínima (700 mm sobre la boca) se dedujo, no está escrito. Decisión V de [docs/pendientes.md](docs/pendientes.md): si el barrido pasa al programa. Sigue: el modelo de flujo.

#### EAF-065 — Modelo de vaciado por la piquera, primera versión (preliminar; proyecto paralelo)

- Solicitud (usuario, 2026-11-15): «comienza con la creación del modelo; prepáralo como app independiente o extensión de LWD-EAF; entrégame un resultado final que pueda considerarse un entregable preliminar, para dar inicio con este proyecto en paralelo», documentando en el documento de integración o en un documento de proyecto paralelo.
- Resultado:
  - Paquete `lwd_eaf/vaciado/` (modelo 0.1.0-preliminar): `tabla` (nivel sobre la boca por masa y ángulo, de la cavidad del programa), `hidraulica` (coeficiente de descarga o pérdidas explícitas; carga a la boca o a la salida), `basculado` (escalones, seguir la carga segura, ángulo fijo), `simulacion` (integrador de Heun, avisos de panel y de arrastre), `escenario`, `reporte` y consola (`python vaciado.py`).
  - `datos/vaciado/pesqueria.json`: piquera, panel y valores por omisión, cada uno con su estado. `ejemplos/vaciado/`: seis escenarios. `docs/figuras/vaciado_modelo_pesqueria.png`.
  - `docs/vaciado/proyecto.md`: documento de proyecto (objetivo, modelo, datos, verificación, resultados, límites, datos que faltan, hoja de ruta, bitácora).
  - `verificacion/test_vaciado_modelo.py`: 11 pruebas.
- Evidencia: un recipiente prismático da el tiempo de Torricelli a 1 parte en 100 000. Con escalones instantáneos y Cd 0,731 a la boca el modelo da 413,4 s para los 300 t de Pesquería (el plano, 411,5; +0,5 %); con el revestimiento gastado, 408,0 s (413,8; −1,4 %). Primeros resultados: bascular en continuo hasta lo que permite el panel, 386 s; con el canal en Ø240 mm, 268 s; con pérdidas de manual y carga hasta la salida, 255 s.
- Impacto numérico: ninguno en el programa. No cambian `lwd_eaf` fuera del paquete nuevo, los archivos de planta ni la versión de LWD-EAF (0.23.0).
- Verificación (Linux, Python 3.13.18, NumPy 2.5.3, sin PySide6): `python -m pytest verificacion/test_vaciado_modelo.py verificacion/test_vaciado_ebt.py verificacion/test_niveles.py verificacion/test_pesqueria.py -q -p no:cacheprovider`: `54 passed` (con `test_entrega.py`, `69 passed, 1 skipped`). `ruff check lwd_eaf/vaciado vaciado.py`: limpio. **La suite completa no se corrió.**
- Límites y pendientes: **ningún parámetro hidráulico está validado con tiempos de vaciado medidos**; la velocidad de basculado (1 °/s), el ángulo máximo y los valores de K, rugosidad y viscosidad son supuestos; la altura mínima de 3,5 diámetros es una deducción. Solo Pesquería tiene datos. Datos V1 a V7 de [docs/vaciado/proyecto.md](docs/vaciado/proyecto.md) y decisión W de [docs/pendientes.md](docs/pendientes.md).

## 2026-11-16

#### EAF-066 — Vaciado-EAF: el modelo de vaciado como aplicación propia, con ventana y ejecutable

- Solicitud (usuario, 2026-11-16): entre una página en la ventana de LWD-EAF y una aplicación propia, «sigue el camino 2: aplicación propia».
- Resultado:
  - `lwd_eaf/vaciado/ventana.py`: ventana de PySide6 con el tema Magnesita. Escenario a la izquierda; pestañas «Colada», «Corte» (el horno inclinado en el instante elegido), «Límites» y «Comparar»; a la derecha, tiempo de vaciado, avisos y botones para abrir, guardar y exportar.
  - `lwd_eaf/vaciado/reporte.py`: exportación a Excel (resumen, datos con su estado, serie con cuatro gráficas nativas) y a PDF (dos páginas).
  - `vaciado.py`: sin argumentos abre la ventana; `--consola`, `--curvas`, `--probar-ventana`, `--version`.
  - `empaquetado/construir_vaciado.py`: ejecutable propio (`dist/Vaciado-EAF/`), que al terminar se prueba a sí mismo. La CI de Windows lo construye y lo guarda como artefacto `Vaciado-EAF-windows`.
  - Los datos de vaciado se buscan con `lwd_eaf.rutas`, para que el ejecutable los encuentre.
- Impacto numérico: ninguno. El modelo sigue en 0.1.0-preliminar y LWD-EAF en 0.23.0.
- Verificación (Linux, Python 3.13.18, PySide6 6.12.0, sin pantalla): `python -m pytest verificacion/test_vaciado_modelo.py -q -p no:cacheprovider`: `13 passed` (incluye la ventana y las exportaciones). `python vaciado.py --probar-ventana`: ok. `python empaquetado/construir_vaciado.py`: el ejecutable de Linux se construyó (187 MB en zip) y pasó su propia prueba de ventana. `ruff check`: limpio. **El ejecutable de Windows no se construyó ni se abrió aquí**: lo hace la CI en este push. La suite completa no se corrió en esta sesión.
- Límites y pendientes: nadie ha visto la ventana en una pantalla real (solo capturas sin pantalla); el nombre «Vaciado-EAF» y el icono son provisionales (decisión W). Todo lo de EAF-062 sigue valiendo: sin validar con tiempos de vaciado medidos.

## 2026-11-17

#### EAF-069: Vaciado-EAF, olla, tundish y moldes; mapas del horno; interfaz Qt; documento de integración

- Solicitud (usuario, 2026-11-20): continuar con la mejora y la optimización del programa de vaciado y su documentación, con el objetivo de estimar el tiempo de vaciado del EAF en distintos ángulos, el de las ollas en la máquina de colada continua y el del tundish hacia el molde; preparar un plan e implementar los cambios. Durante el trabajo pidió añadir al plan la configuración de la interfaz en Qt.
- Resultado:
  - Plan por fases en [docs/vaciado/proyecto.md](docs/vaciado/proyecto.md), reescrito con las reglas de [docs/estilo-de-documentos.md](docs/estilo-de-documentos.md).
  - Horno: `lwd_eaf/vaciado/mapa.py` (tiempo a ángulo fijo, por diámetro y por vida de la piquera; comparación con el basculado óptimo).
  - Colada continua: `olla.py` (geometría con la regla del LWD), `valvula.py` (fracción abierta de la válvula deslizante, la del SGW), `artesa.py` (tundish y moldes), `colada_continua.py` (secuencia acoplada olla–tundish–moldes con control de nivel, cambio de olla y avisos), `reporte_colada.py` (Excel, PDF y CSV).
  - Datos: `datos/vaciado/colada_continua/pesqueria.json`. La geometría de la olla y sus marcas se copiaron del repositorio Ladle-Wear-Diagnosis- (revisión `bce1cda`, plano CS129722) como heredadas sin verificar; la válvula toma el diámetro y el coeficiente del SGW (otra olla) como supuestos; el tundish, los moldes y la secuencia son ejemplos. Cuatro escenarios en `ejemplos/vaciado/colada_continua/`.
  - Ventana: dos páginas («Horno (EAF) → olla», con la pestaña nueva «Mapas», y «Olla → tundish → moldes»). Primera parte de la fase de interfaz Qt: tarjetas, etiquetas de estado de cada dato, selectores y botones de LWD-EAF (`ventana_formulario.py`). `python vaciado.py --colada` corre la máquina sin ventana.
  - Documento de integración del proyecto en Word, con el formato del de LWD-EAF: [docs/vaciado/documento-de-integracion/](docs/vaciado/documento-de-integracion/README.md) (16 páginas). El documento de LWD-EAF no se tocó.
- Evidencia: la olla de Pesquería da 304.1 t a la cota de la marca de 300 t y 257.6 t a la de 255 t (1.4 %, igual que el LWD); una olla cilíndrica con la válvula abierta da el tiempo de Torricelli a 0.2 %; el volumen del tundish en forma cerrada coincide con la integración numérica a 1·10⁻⁶; la secuencia conserva la masa a 1 %; el mapa por vida de la piquera coincide con el cálculo directo a 0.2 %. Horno de Pesquería a ángulo fijo: de 614 s a 0° a 335 s a 15° (450 → 150 t). Máquina con datos de ejemplo: con la válvula de 55 mm la olla no alcanza la demanda de 1.2 m/min desde que quedan 90 t; con 80 mm, sólo con las últimas 14 t.
- Impacto numérico: ninguno en LWD-EAF ni en el modelo del horno; el modelo de vaciado sigue en 0.1.0-preliminar (propuesta de 0.2.0 en la decisión W).
- Verificación (Linux, Python 3.13.18, PySide6 6.12.0, sin pantalla): `python -m pytest verificacion/test_vaciado_ebt.py verificacion/test_vaciado_modelo.py verificacion/test_vaciado_colada_continua.py -q -p no:cacheprovider`: ver la nota final. `python vaciado.py --probar-ventana`: ok. `ruff check .`: limpio. La suite completa no se corrió.
- Límites y pendientes: sin datos de planta de la válvula, del tundish ni de la máquina; ningún tiempo medido. La interfaz no se vio en una pantalla real ni en Windows. Decisiones W y Y de [docs/pendientes.md](docs/pendientes.md).
