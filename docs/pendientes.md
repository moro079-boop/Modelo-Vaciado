# Pendientes y decisiones abiertas

Actualizado el 2026-11-24 (MV-001). Las decisiones son del usuario; las propuestas de esta lista no están aprobadas mientras no
se diga lo contrario.

## Decisiones tomadas por el usuario

| Tema | Decisión |
|---|---|
| Repositorio | Este (`moro079-boop/Modelo-Vaciado`), separado de LWD-EAF (2026-11-24) |
| Objetivo | Estimar tiempos de vaciado con las ecuaciones de flujo (Bernoulli, Torricelli…) y refinar el programa con el tiempo (2026-11-24) |
| Motor de la interfaz | Qt (2026-11-24) |

## Heredadas de LWD-EAF

Decisiones abiertas de LWD-EAF sobre el modelo de vaciado, copiadas sin cambios del commit `d3c7ad2` de aquel repositorio. Las
rutas que citan son las de aquel repositorio.

- **Y (EAF-069). Vaciado-EAF en la colada continua.** Lo que se decidió con valor provisional y puede cambiarse: (a) la olla de Pesquería se toma del LWD (plano CS129722) sin volver a contrastarla con el plano; (b) la válvula de la olla usa el diámetro de 55 mm y el C_d de 0.75 del SGW, que corresponden a otra olla (válvula LG22L); (c) caída del piso de la olla a la salida del tubo de 900 mm y remanente de 3 t, supuestos; (d) tundish, moldes y secuencia con valores de ejemplo (7 000 × 1 000 mm, niveles 500, 1 100 y 1 300 mm; una línea de 1 600 × 250 mm a 1.2 m/min; cuatro ollas de 300 t y cambio de 180 s); (e) control de nivel proporcional con τ = 30 s; (f) densidad del acero sólido 7.6 t/m³; (g) versión del modelo: se propone 0.2.0-preliminar por las etapas nuevas (no se cambió). **Datos por conseguir:** los de la sección 8 de [vaciado/proyecto.md](vaciado/proyecto.md).
- **W (EAF-065). Modelo de vaciado por la piquera (proyecto paralelo, [vaciado/proyecto.md](vaciado/proyecto.md)).** Lo que decidí para la primera versión y el usuario puede cambiar: (a) y (b) ~~extensión por consola~~ **decidido por el usuario el 2026-11-16 (EAF-063): aplicación propia, Vaciado-EAF**, con ventana y ejecutable; queda por confirmar el **nombre «Vaciado-EAF»**, el **icono** (usa el de LWD-EAF) y que comparta repositorio y biblioteca con LWD-EAF; **nadie ha abierto todavía la ventana ni el `.exe` en un escritorio de Windows**; (c) usa la **cavidad calibrada del programa**, no el barrido de la decisión V; (d) el documento es `docs/vaciado/proyecto.md`, no un capítulo del documento de integración en Word; (e) no sube la versión de LWD-EAF (el modelo lleva la suya, 0.1.0-preliminar). **Valores provisionales sin dato:** velocidad de basculado 1 °/s, ángulo máximo 15°, K de entrada 0,5, rugosidad 1 mm, viscosidad 0,006 Pa·s, altura mínima 3,5 diámetros. **Datos por conseguir:** V1 a V7 de ese documento; el primero, tiempos de vaciado medidos por colada con la edad de la piquera.
- **X (EAF-064). Pesquería: el fondo del lado de la piquera.** El estudio de vaciado de Magnesita (plano AV00025170, [vaciado-ebt.md](vaciado-ebt.md)) trae 22 pares tonelaje–nivel nuevos (cinco desgastes a 0° y dos series inclinadas). Con el fondo de la piquera por **barrido** (perfil del casquete trasladado a lo largo de la rampa) las marcas a 0° salen a ±4 mm sin calibrar; la regla del programa (mezcla por ángulo) necesita los +32,9 mm de EAF-050. **Por decidir (usuario):** (a) si el barrido sustituye a la regla del programa en Pesquería (quitaría la calibración; cambia niveles y capacidades) y si se prueba en Danieli, que usa la misma regla y no cierra; (b) si se pregunta a Magnesita por el coeficiente 0,731 / 0,741, el criterio de la carga mínima (aquí deducido: 700 mm sobre la boca del EBT) y la altura de la hoja 9, que no cuadra con las hojas 7 y 8. Mientras tanto el barrido vive solo en `herramientas/vaciado_ebt.py`.
