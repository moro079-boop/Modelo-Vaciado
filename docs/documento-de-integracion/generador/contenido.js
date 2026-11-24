// Documento de integración de Vaciado-EAF. Usa el formato del documento de integración de LWD-EAF (lib2.js).
const { Builder } = require('./lib2.js');
const FIG = __dirname + '/../../figuras/';
const IMG = __dirname + '/';
const out = process.argv[2];

const B = new Builder({
  titulo: 'Vaciado-EAF: tiempos de vaciado del horno de arco eléctrico, la olla y el tundish',
  cabecera: 'Noviembre 2026 / T&P Refractarios',
});

B.title('Vaciado-EAF: tiempos de vaciado del horno de arco eléctrico, la olla y el tundish', 'Versión 0.1', [
  ['Proyecto', 'Estimación del tiempo de vaciado del acero líquido del horno de arco eléctrico (EAF) a la olla, de la olla al tundish y del tundish a los moldes de la máquina de colada continua (programa **Vaciado-EAF**)'],
  ['Versión', '**Modelo 0.1.0-preliminar**, planta Pesquería'],
  ['Etapa', 'Modelo completo de las tres etapas, verificado contra soluciones analíticas y contra el cálculo teórico del proveedor de refractarios. Sin validación con tiempos de vaciado medidos.'],
  ['Relación', 'Proyecto paralelo a LWD-EAF. Comparte su biblioteca de cálculo (cavidad del horno, archivos de planta, desgaste del revestimiento y tema visual).'],
]);

B.h2u('Resumen');
B.p('Vaciado-EAF es un programa, escrito en Python, que estima el tiempo de vaciado del acero líquido en las tres etapas de la acería: del horno de arco eléctrico a la olla por la piquera, de la olla al tundish por la válvula deslizante y del tundish a los moldes por las buzas sumergidas. En el horno, el cálculo depende del ángulo de inclinación, del tonelaje, del desgaste del revestimiento y del diámetro de la piquera; en la máquina de colada continua, de la geometría de la olla, de la abertura de la válvula, del nivel del tundish y de la velocidad de colada.');
B.p('Las tres etapas se describen con el mismo principio: un recipiente que se vacía por un orificio, con un caudal que depende de la carga de acero sobre la salida, integrado en el tiempo. El nivel del baño en el horno se obtiene de la cavidad tridimensional construida con el plano del horno; el de la olla, de la geometría de su plano con la regla del Ladle Wear Diagnosis (LWD).');
B.p('El modelo reproduce el estudio de vaciado que el proveedor de refractarios incluyó en el plano del horno de Pesquería con una diferencia de 0.5 % en el tiempo total. Sin embargo, ningún parámetro hidráulico se ha contrastado con tiempos medidos en planta, y la válvula de la olla, el tundish y la máquina se describen con valores supuestos o de ejemplo. Por ello, los resultados constituyen escenarios y no pronósticos.');

B.contents();

// ================================================================ 1
B.h1('s1', 'Objetivo y alcance');
B.h2('s11', 'Objetivo general');
B.p('El objetivo es disponer de un programa que estime el tiempo de vaciado del horno de arco eléctrico en distintos ángulos de inclinación, el de las ollas en la máquina de colada continua y el del tundish hacia los moldes, para cualquier horno y máquina cuya geometría se describa en un archivo de datos.');
B.p('El programa debe ser un ejecutable con interfaz, utilizable en un equipo sin Python, y a la vez una biblioteca de cálculo cuyo núcleo no dependa de la ventana.');

B.h2('s12', 'Objetivos específicos');
B.p('El trabajo se organiza en fases, de modo que cada una entregue un resultado utilizable. {T:fases} resume su contenido y estado.');
B.table('fases', 'Fases del proyecto y su estado.', ['Fase', 'Contenido', 'Estado'], [
  ['0', 'Análisis del estudio del proveedor y reproducción de su cálculo', 'Hecha'],
  ['1', 'Modelo del horno: nivel por masa y ángulo, hidráulica de la piquera, basculado e integración en el tiempo', 'Hecha'],
  ['2', 'Aplicación con ventana, exportación a Excel, PDF y CSV, y ejecutable', 'Hecha'],
  ['3', 'Mapas del horno por ángulo y por vida de la piquera; olla, válvula deslizante, tundish, moldes y secuencia de ollas', 'Hecha, con datos supuestos fuera del horno y de la olla'],
  ['4', 'Interfaz con los componentes Qt de LWD-EAF', 'En curso'],
  ['5', 'Datos de planta: tiempos medidos, diámetros, tundish y máquina', 'Pendiente de datos'],
  ['6', 'Calibración de los coeficientes de descarga y ley de crecimiento de la piquera', 'Pendiente de la fase 5'],
  ['7', 'Otras plantas y un horno con canal de vaciado (OBT)', 'Pendiente de datos'],
  ['8', 'Vórtice y arrastre de escoria, temperatura del acero y plan de basculado con restricciones de proceso', 'Propuesta'],
], [1, 6, 3]);

B.h2('s13', 'Alcance del modelo');
B.p('El programa entrega, para cada etapa, la evolución en el tiempo de la masa de acero, del nivel y del caudal, junto con los avisos de operación. En particular:');
B.ul([
  '**Horno:** tiempo de vaciado con una forma de basculado dada, tiempo a cada ángulo fijo, tiempo a lo largo de la vida de la piquera, y límites por ángulo (carga segura respecto del panel refrigerado, carga mínima por arrastre de escoria y acero que no puede salir).',
  '**Olla:** tiempo de colado con el control de nivel del tundish y tiempo mínimo con la válvula abierta del todo; abertura de la válvula durante la colada.',
  '**Tundish y moldes:** nivel del tundish durante la secuencia, margen en el cambio de olla, velocidad máxima de colada que admiten la válvula de la olla y las buzas.',
]);

// ================================================================ 2
B.h1('s2', 'Justificación');
B.p('El tiempo de vaciado del horno condiciona la duración de la colada y la temperatura con que el acero llega a la olla. Depende del ángulo de inclinación, porque éste fija la carga de acero sobre la piquera, y del diámetro del canal, que crece con las coladas. Conocer esa relación permite planear el basculado y anticipar el cambio de piquera.');
B.p('En la máquina de colada continua, el tiempo de colado de una olla lo fija la velocidad de colada mientras la válvula de la olla alcanza la demanda. Cuando la carga en la olla disminuye, la válvula se abre hasta su límite y, si no basta, el tundish pierde nivel. El margen del tundish durante el cambio de olla y la velocidad máxima que admiten la válvula y las buzas determinan la continuidad de la secuencia.');
B.p('El proveedor de refractarios entregó para el horno de Pesquería un estudio teórico del vaciado por escalones de ángulo. El presente proyecto reconstruye ese cálculo, lo extiende a un modelo continuo en el tiempo y lo prolonga a la olla y al tundish.');

// ================================================================ 3
B.h1('s3', 'Fundamentos del modelo');
B.p('Este apartado describe el principio común a las tres etapas y las particularidades de cada una.');

B.h2('s31', 'Balance de masa y caudal por un orificio');
B.p('Para un recipiente de masa M que recibe un caudal Q_ent y entrega un caudal Q_sal, el balance de masa es:');
B.eq('dM/dt = Q_ent − Q_sal', 'balance');
B.p('El horno y la olla sólo entregan; el tundish recibe de la olla y entrega a los moldes. El caudal por un orificio se obtiene de la ecuación de energía entre la superficie libre y la salida:');
B.eq('Q = ρ · C_d · f_A · A · √(2 · g · H)', 'caudal');
B.donde([['ρ', 'Densidad del acero líquido.'], ['C_d', 'Coeficiente de descarga, que agrupa las pérdidas.'], ['f_A', 'Fracción de área abierta (1 sin válvula).'], ['A', 'Área del orificio.'], ['H', 'Carga: altura de la superficie libre sobre la salida, descontada la contrapresión del recipiente de destino.']]);
B.p('Cuando las pérdidas se conocen por separado, la velocidad en el canal se escribe en la forma siguiente, donde K es la pérdida de entrada y f el factor de fricción de Darcy del canal de largo L y diámetro D, obtenido con la ecuación de Swamee y Jain:');
B.eq('v = √(2 · g · H / (1 + K + f · L / D))', 'perdidas');

B.h2('s32', 'Horno');
B.h3('Nivel del baño');
B.p('La altura del acero sobre la boca de la piquera se obtiene de la cavidad tridimensional del horno, cortada por el plano inclinado de la superficie libre. La relación entre la masa, el ángulo y el nivel se tabula cada 0.5° y cada 10 mm, y se interpola durante la integración.');
B.h3('Carga sobre la piquera');
B.p('La carga se mide desde la boca de la piquera, como en el estudio del proveedor, o desde la salida del canal, sumando su caída vertical con el canal lleno. En el primer caso el coeficiente de descarga absorbe la diferencia entre ambas referencias.');
B.h3('Basculado');
B.p('El ángulo sigue una de tres formas: escalones fijos, como en el estudio del proveedor; ángulo fijo; o el mayor ángulo que deja 300 mm entre el baño y el panel refrigerado. Esta última forma es la más rápida posible con esa restricción, porque a mayor ángulo hay más acero sobre la piquera. El ángulo sigue al objetivo con una velocidad máxima de basculado.');
B.h3('Límites por ángulo');
B.ul([
  '**Carga segura:** toneladas con el baño a 300 mm del panel refrigerado.',
  '**Carga mínima:** toneladas con la altura mínima de acero sobre la boca de la piquera, por debajo de la cual se arrastra escoria. El valor de 3.5 diámetros reproduce la curva del proveedor.',
  '**Acero no drenable:** toneladas que quedan por debajo de la boca a ese ángulo.',
]);

B.h2('s33', 'Olla y válvula deslizante');
B.p('La coraza de la olla es un tronco de cono; la cara caliente es la coraza menos el aislante, la capa de seguridad y el espesor de trabajo de cada hilada, y el acero ocupa el volumen sobre el piso. Es la misma regla del LWD, de modo que los niveles de los dos programas coinciden. El desgaste se aplica como pérdida uniforme de la capa de trabajo de la pared y del piso.');
B.p('La carga sobre la válvula es la altura del acero en la olla más la caída desde el piso de la olla hasta la salida del tubo largo, menos la altura del acero del tundish sobre esa salida. La válvula deslizante se representa como dos orificios circulares de diámetro D desplazados una distancia e, que dejan abierta la fracción:');
B.eq('f_A = (2/π) · [arccos(x) − x · √(1 − x²)] ;  x = e / D', 'fa');
B.p('Es la relación que emplea el modelo de desgaste de la válvula deslizante (SGW).');

B.h2('s34', 'Tundish y moldes');
B.p('El tundish es un prisma de fondo rectangular, de largo L y ancho W, con paredes en talud de ángulo α. El volumen hasta el nivel h tiene forma cerrada:');
B.eq('V(h) = L·W·h + (L + W)·tan α·h² + (4/3)·tan² α·h³', 'tundish');
B.p('La demanda de los moldes la fija la velocidad de colada:');
B.eq('Q_moldes = n · ρ_s · a · e · v', 'demanda');
B.donde([['n', 'Número de líneas.'], ['ρ_s', 'Densidad del acero sólido.'], ['a, e', 'Ancho y espesor del producto.'], ['v', 'Velocidad de colada.']]);
B.p('Cada buza sumergida deja pasar como máximo el caudal de la ec. {E:caudal} con f_A = 1 y una carga igual al nivel del tundish más el largo de la buza bajo el fondo, menos su inmersión en el molde. Si la demanda supera esa capacidad, la velocidad de colada disminuye.');

B.h2('s35', 'Control de nivel y secuencia de ollas');
B.p('La válvula de la olla entrega la demanda de los moldes más una corrección proporcional al error de nivel del tundish, sin exceder la válvula abierta del todo:');
B.eq('Q_olla = mín[ Q_moldes + ρ · A_t(h) · (h_op − h) / τ ;  Q_abierta ]', 'control');
B.donde([['A_t(h)', 'Área de la superficie libre del tundish al nivel h.'], ['h_op', 'Nivel de operación del tundish.'], ['τ', 'Constante de tiempo del control.']]);
B.p('Cada olla se abre con su acero y se cierra al quedar el remanente. Durante el cambio de olla el tundish sólo entrega, y la olla siguiente repone primero lo perdido. Tras la última olla, el tundish se vacía hasta su nivel mínimo. El modelo avisa cuando la válvula, abierta del todo, ya no alcanza la demanda; cuando el tundish baja de su mínimo en un cambio o supera su máximo; y cuando las buzas limitan la velocidad.');

B.h2('s36', 'Integración numérica');
B.p('El sistema se integra con el método de Heun, de segundo orden, con paso fijo de 0.25 s en el horno y de 1 s en la máquina de colada continua. El último paso se acorta para terminar exactamente en la masa objetivo.');

// ================================================================ 4
B.h1('s4', 'Desarrollo y resultados');
B.p('Este apartado describe el análisis del estudio del proveedor, la verificación del modelo y los resultados para Pesquería.');

B.h2('s41', 'Estudio del proveedor');
B.p('El plano AV00025170 del horno de Pesquería contiene un estudio teórico del vaciado de 300 t (de 450 t a 150 t) en cinco escalones de ángulo (2°, 5°, 8°, 11° y 15°), con el revestimiento nuevo y gastado. Para cada escalón, el proveedor toma dos niveles del baño medidos en el dibujo desde el centro de la boca de la piquera, los promedia como altura ferrostática y calcula el caudal con la ley de Torricelli. El coeficiente de descarga implícito es 0.731 con el revestimiento nuevo y 0.741 con el gastado. El tiempo total es de 411.5 s y 413.8 s, respectivamente.');
B.p('Las curvas de carga segura y de carga mínima del estudio ({F:estudio}) se reproducen con el baño a 300 mm del panel refrigerado y con 700 mm de acero sobre la boca de la piquera. El segundo criterio no figura en el plano y se dedujo del ajuste.');
B.fig('estudio', FIG + 'vaciado_ebt_pesqueria_curvas.png', 'Reproducción de las gráficas del estudio del proveedor: acero en el horno con sus dos límites (arriba) y nivel sobre la boca de la piquera (abajo), con el revestimiento nuevo y gastado.', 6.4);

B.h2('s42', 'Verificación');
B.p('{T:verif} reúne las comprobaciones del modelo. Reproducir el estudio del proveedor comprueba que el modelo efectúa correctamente la misma cuenta, pero no que la cuenta represente el vaciado real.');
B.table('verif', 'Comprobaciones del modelo.', ['Comprobación', 'Resultado'], [
  ['Recipiente prismático contra la solución de Torricelli', 'Igual a una parte en 100 000'],
  ['Paso de tiempo de 2 s contra 0.1 s', 'Diferencia menor que 0.1 %'],
  ['Estudio del proveedor, revestimiento nuevo', '413.4 s contra 411.5 s (+0.5 %)'],
  ['Estudio del proveedor, revestimiento gastado', '408.0 s contra 413.8 s (−1.4 %)'],
  ['Olla de Pesquería contra las marcas de su plano', '304.1 t a la cota de 300 t; 257.6 t a la de 255 t'],
  ['Olla cilíndrica con la válvula abierta contra Torricelli', 'Diferencia de 0.2 %'],
  ['Volumen del tundish, forma cerrada contra integración numérica', 'Igual a una parte en un millón'],
  ['Conservación de la masa en la secuencia de ollas', 'Diferencia menor que 1 %'],
], [6, 4]);

B.h2('s43', 'Horno de Pesquería');
B.p('{T:horno} resume el vaciado de 450 t a 150 t con distintas formas de bascular. El basculado continuo hasta lo que permite el panel refrigerado reduce el tiempo en 27 s (6.5 %) respecto de los cinco escalones del proveedor sin acercar el baño al panel. El diámetro del canal es la variable de mayor efecto: de 200 mm a 240 mm el tiempo disminuye un 31 %.');
B.table('horno', 'Vaciado del horno de Pesquería, de 450 t a 150 t.', ['Escenario', 'Tiempo, s', 'Caudal medio, t/min'], [
  ['Escalones del proveedor, basculado instantáneo', '413', '43.5'],
  ['Mismos escalones, basculado a 1 °/s', '414', '43.5'],
  ['Basculado continuo hasta lo que permite el panel', '386', '46.6'],
  ['Igual, con el canal de 240 mm', '268', '67.1'],
  ['Igual, con pérdidas explícitas y carga hasta la salida', '255', '70.6'],
  ['Escalones del proveedor, revestimiento gastado', '408', '44.1'],
], [6, 2, 2]);
B.p('Con las pérdidas de entrada y de fricción tomadas de la bibliografía y la carga medida hasta la salida del canal, el caudal resulta un 60 % mayor que con el coeficiente del proveedor. Ambas descripciones no pueden ser ciertas a la vez; sólo los tiempos medidos permitirán decidir.');
B.p('A ángulo fijo ({F:mapas}, izquierda), el tiempo disminuye de 614 s a 0° a 335 s a 15°; sin embargo, desde 3° el baño inicial de 450 t queda a menos de 300 mm del panel. Con el canal creciendo 0.3 mm por colada, valor supuesto a falta de dato, el tiempo disminuye de 386 s en la primera colada a 292 s en la colada 101 ({F:mapas}, derecha).');
B.fig('mapas', IMG + 'mapas_horno.png', 'Tiempo de vaciado del horno a ángulo fijo (izquierda) y a lo largo de la vida de la piquera con un crecimiento supuesto del canal de 0.3 mm por colada (derecha).', 6.4);

B.h2('s44', 'Olla, tundish y moldes');
B.p('La geometría de la olla de Pesquería (300 t) procede de su plano a través del LWD, y el modelo reproduce sus marcas de llenado con una diferencia de 1.4 % ({F:olla}, izquierda). Con la válvula abierta del todo, la olla se vaciaría en 78 min con un orificio de 55 mm y en 37 min con uno de 80 mm ({F:olla}, derecha).');
B.fig('olla', IMG + 'olla.png', 'Olla de Pesquería: cara caliente con las marcas del plano y los niveles del modelo (izquierda) y vaciado con la válvula abierta del todo para dos diámetros (derecha).', 6.4);
B.p('{T:colada} resume cuatro secuencias de cuatro ollas con los datos de ejemplo del tundish y de la máquina. Con la máquina a velocidad constante, el colado de una olla lo fija la demanda de los moldes; la válvula sólo limita al final de cada olla, cuando la carga ya no alcanza. {F:secuencia} muestra la secuencia con la válvula de 80 mm.');
B.table('colada', 'Secuencias de cuatro ollas de 300 t con datos de ejemplo.', ['Escenario', 'Colado de una olla, min', 'Observación'], [
  ['Válvula de 55 mm, 1.2 m/min', '78', 'La válvula abierta no alcanza la demanda desde que quedan 90 t'],
  ['Válvula de 80 mm, 1.2 m/min', '78', 'Sólo al final (14 t) la válvula no alcanza la demanda'],
  ['Válvula de 80 mm, 1.6 m/min', '58', 'La válvula no alcanza la demanda desde que quedan 31 t'],
  ['Válvula de 80 mm, cambio de olla de 10 min', '71', 'El tundish baja a 509 mm en cada cambio, a 9 mm de su mínimo'],
], [4, 2, 5]);
B.fig('secuencia', IMG + 'secuencia_colada.png', 'Secuencia de cuatro ollas con la válvula de 80 mm: acero en la olla, nivel del tundish, abertura de la válvula y caudales. Las franjas sombreadas son los cambios de olla.', 6.4);

B.h2('s45', 'Datos y su procedencia');
B.p('Cada valor lleva su estado en el archivo de datos, en la ventana y en los reportes. {T:datos} distingue los valores que proceden de planos de los que son supuestos o de ejemplo.');
B.table('datos', 'Procedencia de los datos de Pesquería.', ['Dato', 'Valor', 'Estado'], [
  ['Cavidad del horno', 'Plano CS128936', 'Medido a escala, calibrado con las marcas del plano'],
  ['Piquera del horno', 'Ø200 mm; largo 1 359 mm', 'Cota y medido a escala'],
  ['Coeficiente de descarga del horno', '0.731', 'Implícito en el estudio del proveedor'],
  ['Geometría de la olla', 'Plano CS129722 (300 t)', 'Heredado del LWD, sin verificar'],
  ['Válvula de la olla', 'Ø55 mm; C_d 0.75', 'Tomado del SGW (otra olla): supuesto'],
  ['Caída hasta la salida del tubo; remanente', '900 mm; 3 t', 'Supuesto'],
  ['Tundish', '7 000 × 1 000 mm; niveles 500, 1 100 y 1 300 mm', 'Ejemplo'],
  ['Moldes', 'Una línea de 1 600 × 250 mm a 1.2 m/min', 'Ejemplo'],
], [4, 4, 4]);

B.h2('s46', 'Límites del modelo');
B.ul([
  '**Validación:** ninguna cifra se ha contrastado con tiempos medidos en planta.',
  '**Flujo:** el canal se supone lleno y el chorro libre; no se representan el vórtice ni la entrada de aire.',
  '**Escoria:** el arrastre sólo se señala; no se calcula cuánta escoria pasa, y no se considera la escoria en la olla ni en el tundish.',
  '**Desgaste de los orificios:** el diámetro es constante dentro de una colada; su crecimiento entre coladas sólo se estudia con una tasa supuesta.',
  '**Control:** el control de nivel del tundish es proporcional e ideal, sin retardo ni banda muerta.',
  '**Temperatura:** no se considera la temperatura del acero ni la solidificación en los orificios.',
]);

B.h2('s47', 'Trabajo pendiente');
B.p('{T:faltan} lista los datos de planta que permitirían pasar de escenarios a estimaciones calibradas.');
B.table('faltan', 'Datos de planta necesarios.', ['Dato', 'Uso'], [
  ['Tiempos de vaciado del horno por colada, con el peso vaciado y la edad de la piquera', 'Calibrar la hidráulica del horno'],
  ['Diámetro de la piquera nueva y al cambiarla', 'Ley de crecimiento del canal'],
  ['Secuencia real de basculado y velocidad mecánica del horno', 'Forma de bascular y su límite'],
  ['Diámetro y carrera de la válvula de la olla; caída hasta la salida del tubo', 'Válvula de la olla'],
  ['Serie de peso de la olla durante la colada', 'Coeficiente de descarga de la válvula'],
  ['Geometría y niveles del tundish', 'Tundish'],
  ['Formato, líneas, velocidades y buzas', 'Moldes'],
  ['Tiempo de cambio de olla y acero remanente', 'Secuencia'],
], [6, 4]);

// ================================================================ 5
B.h1('s5', 'Descripción del código');
B.p('Este apartado describe la organización del programa, sus datos y su uso.');

B.h2('s51', 'Organización');
B.p('El cálculo vive en el paquete `lwd_eaf.vaciado`, separado de la ventana. {T:modulos} resume sus módulos.');
B.table('modulos', 'Módulos del paquete de vaciado.', ['Módulo', 'Contenido'], [
  ['`tabla.py`', 'Nivel del baño del horno por masa y ángulo'],
  ['`hidraulica.py`', 'Caudal por el canal del horno'],
  ['`basculado.py`', 'Formas de bascular el horno'],
  ['`simulacion.py`', 'Integración del vaciado del horno, límites y avisos'],
  ['`mapa.py`', 'Tiempo por ángulo fijo, por diámetro y por vida de la piquera'],
  ['`olla.py`', 'Geometría de la olla y nivel por masa'],
  ['`valvula.py`', 'Fracción abierta de la válvula y caudal por un orificio'],
  ['`artesa.py`', 'Tundish y moldes'],
  ['`colada_continua.py`', 'Secuencia acoplada olla, tundish y moldes'],
  ['`reporte.py`, `reporte_colada.py`', 'Reportes en texto, CSV, Excel y PDF'],
  ['`ventana.py`, `ventana_colada.py`', 'Ventana de PySide6'],
], [3, 7]);

B.h2('s52', 'Datos y escenarios');
B.p('Los datos del horno se guardan en `datos/vaciado/<planta>.json` y los de la olla, la válvula, el tundish y los moldes en `datos/vaciado/colada_continua/<planta>.json`. La geometría de la olla tiene el formato del LWD. Agregar una planta consiste en agregar estos archivos, sin modificar el código. Los escenarios se guardan en JSON y se abren desde la ventana o desde la línea de órdenes.');

B.h2('s53', 'Interfaz');
B.p('La ventana tiene dos páginas. La del horno contiene el escenario y las pestañas Colada, Corte, Límites, Comparar y Mapas ({F:app1}). La de la colada continua contiene los datos de la máquina, cada uno con la marca de su estado, y las pestañas Secuencia, Olla y Tundish y moldes ({F:app2}). En ambas, la columna derecha presenta el resultado, los avisos y las exportaciones. La interfaz usa los componentes Qt y la hoja de estilo de LWD-EAF.');
B.fig('app1', FIG + 'vaciado_app_mapas.png', 'Página del horno, pestaña Mapas: tiempo a ángulo fijo y a lo largo de la vida de la piquera.', 6.4);
B.fig('app2', FIG + 'vaciado_app_colada_continua.png', 'Página de la colada continua, pestaña Secuencia, con la válvula de 80 mm.', 6.4);

B.h2('s54', 'Uso');
B.code([
  'python vaciado.py                          ventana',
  'python vaciado.py escenario.json           ventana con ese escenario',
  'python vaciado.py --consola [a.json ...]   horno, sin ventana',
  'python vaciado.py --colada [a.json ...]    colada continua, sin ventana',
  'python vaciado.py --curvas pesqueria       límites del horno por ángulo',
  'python vaciado.py --probar-ventana         comprobación de la ventana',
  'python empaquetado/construir_vaciado.py    ejecutable sin Python',
].join('\n'));

B.h2('s55', 'Pruebas');
B.p('Treinta pruebas automáticas comprueban la transcripción del estudio del proveedor, el integrador contra soluciones analíticas, la geometría de la olla contra su plano, la conservación de la masa en la secuencia, los mapas del horno, la ventana y las exportaciones.');

// ================================================================ 6
B.h1('s6', 'Referencias');
B.p('El proyecto no se apoya en bibliografía externa, salvo la ecuación de Swamee y Jain para el factor de fricción. Las fuentes de datos y de código son las siguientes.');
B.ul([
  '**Plano del horno:** Magnesita, plano CS128936 rev. B01, horno de Pesquería.',
  '**Estudio de vaciado:** Magnesita, plano AV00025170 rev. A (estado «for approval»), estudio teórico del vaciado por la piquera.',
  '**Plano de la olla:** RHI Magnesita, plano CS129722 rev. A05 (estado «for approval»), olla de Pesquería, a través de los datos del LWD.',
  '**Programa LWD:** Ladle Wear Diagnosis, datos de las ollas medidos de sus planos.',
  '**Modelo SGW:** modelo de desgaste de la válvula deslizante, relación de la fracción abierta y valores de la válvula LG22L.',
  '**Programa LWD-EAF:** cavidad del horno, archivos de planta y componentes de la interfaz.',
]);

B.build(out).then(() => console.log('ok', out));
