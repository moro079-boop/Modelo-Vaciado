# Estilo de los documentos

Reglas de estilo y de redacción que se aplican a **todos los documentos** que se generan o se editan en este
repositorio y en los demás proyectos del mismo autor (Slide-Gate-Wear-Model, Ladle-Wear-Diagnosis-, LWD-EAF,
Modelo-1D-TT y Modelo-Vaciado): documentos técnicos, guías, informes, README, notas de `docs/` y documentos de Word. Son
permanentes: no caducan con el uso ni con el tiempo, y mandan sobre cualquier costumbre de redacción anterior.
El mismo texto está en `docs/estilo-de-documentos.md` de cada repositorio; si cambia, se cambia en los cinco.

**Papel.** Se actúa como editor técnico de documentos de ingeniería en español (formal, impersonal). La tarea es
uniformizar el estilo y la redacción de cada documento según las reglas siguientes. Se edita el texto, no el
contenido técnico: no se cambian cifras, ecuaciones, unidades, nombres de materiales ni referencias
bibliográficas, y no se agrega información que no esté verificada. Si algo parece técnicamente dudoso, se
corrige y se marca en la lista final.

## 1. Registro y redacción

- Redactar en tono formal, neutro e impersonal («se calcula», «se obtiene»); evitar la primera persona y el
  tono y las palabras coloquiales o narrativas.
- Sustituir las frases enfáticas o literarias por descripciones técnicas. Ejemplo: «Lo que se desploma no es la
  pared, sino la superficie» pasa a «inicialmente sólo la superficie cae en temperatura».
- Usar conectores explícitos entre ideas («Por ello», «En consecuencia», «Sin embargo», «Cabe mencionar que»).
- Preferir oraciones concretas; dividir las que contengan varias ideas.
- No usar rayas largas (—) como recurso de énfasis ni de incisos; usar comas, dos puntos o paréntesis.
- Mantener «sólo» con acento y el resto de la ortografía del documento; corregir erratas y concordancias.
- Retirar todas las referencias al usuario, del tipo «el usuario pidió» o «a petición del usuario».

## 2. Terminología

- Unificar un término por concepto en todo el documento. Por ejemplo: «pared» o «perfil» (no «muro») cuando se
  habla del campo de temperaturas, «semi-infinito», «interfase». La lista se ajusta a cada documento.
- Escribir siglas y nombres propios igual en todo el documento (GUE, Icarus, Fenix).

## 3. Separación entre teoría y código

- En las secciones de fundamentos o de explicación, quitar nombres de funciones, parámetros, ficheros y rutas
  (por ejemplo `condiciones_del_modo()`, `debe_parar`, `docs/...`) y describir el concepto en su lugar.
- Los identificadores de código sólo se conservan en las secciones que describen el software (módulos,
  estructura, uso), en fuente monoespaciada, y sin listas exhaustivas de firmas o atributos.

## 4. Contenido que se retira o se reduce

- Eliminar notas internas y de gestión: «pendiente de contrastar», «acordado en el diseño», «por acuerdo con el
  usuario», referencias a ramas, tareas o conversaciones, y aclaraciones del tipo «cifras inconsistentes».
- Eliminar los apartes históricos de versión («desde la v0.24...», «antes esto vivía en...»), salvo que sean el
  tema de la sección.
- Reducir los apartados que describen casos de estudio, comandos, formatos de fichero o detalles de
  verificación cuando no aportan a la explicación. No se borran sin avisar: se listan al final como «retirados».
- En las tablas, quitar las columnas y filas que sólo aportan detalle operativo y dejar las que sostienen la
  explicación. Se conserva el significado de cada fila que permanece.

## 5. Estructura y títulos

- Títulos de subapartado cortos y nominales, con inicial mayúscula y sin punto final («Criterio de reposo», no
  «El criterio de reposo: una velocidad, no una tolerancia»).
- Encabezados de módulo en la forma «`archivo.py`: Descripción nominal».
- Listas con etiqueta en negrita seguida de dos puntos y la explicación: «**Concepto:** explicación.»
- Texto de tabla: inicial mayúscula, sin punto final, unidades en una columna aparte.
- Cada apartado abre con una frase que dice qué contiene y cierra sin resumen redundante.

## 6. Ampliaciones permitidas

- Si una explicación es demasiado escueta para un lector no especialista, se amplía con una o dos frases de
  contexto que usen únicamente lo que el documento ya dice. Esas ampliaciones se marcan en la lista final.

## 7. Salvaguardas (se revisan antes de entregar)

- Conservar superíndices, subíndices y ecuaciones (por ejemplo 10⁻³, T_amb); no convertirlos en texto plano.
- Si se quitan o se agregan tablas, figuras o ecuaciones, renumerar todas en orden y actualizar cada referencia
  cruzada («Tabla 5», «Figura 3», «ec. (12)», «sección 3.9»). Verificar que no quede ninguna referencia a un
  elemento que ya no existe.
- Actualizar el índice si cambian los títulos. En Word, los números de página se refrescan con «Actualizar
  campo».
- Mantener los estilos y el formato del documento original (tipos de párrafo, tablas, pies de figura).
- No tocar lo que no esté cubierto por estas reglas.

## 8. Entrega

Con cada documento se devuelve:

1. El documento editado.
2. Una lista breve con:
   - los cambios por categoría, con dos o tres ejemplos de cada una;
   - el contenido retirado;
   - las ampliaciones añadidas;
   - los puntos técnicos dudosos que se dejaron sin tocar;
   - las referencias cruzadas que se renumeraron.

## Relación con las reglas de cada proyecto

Las bitácoras y registros de cambios (`BITACORA.md`, `CHANGELOG.md`, `docs/pendientes.md`,
`docs/bitacora-fenix.md`) y los archivos de instrucciones (`CLAUDE.md`, `AGENTS.md`) tienen por regla propia
registrar las decisiones que fijan un valor o un criterio, y quién las tomó. En esos archivos se aplica este
estilo (registro impersonal, sin rayas largas, términos unificados), pero se conserva el registro de las
decisiones que exige cada proyecto. Esta excepción es definitiva (decisión del usuario del 2026-11-18). La regla de retirar las referencias al usuario
y las notas de gestión se aplica sin excepción al resto de los documentos.
