# Instrucciones para trabajar en Modelo-Vaciado

## Objetivo

Programa que estima el tiempo que tarda un recipiente de acero líquido en vaciar su contenido con las ecuaciones de flujo
(balance de masa, Bernoulli, Torricelli, pérdidas del canal), y que se refina con el tiempo. Escenarios del alcance actual:
**horno (EAF) → olla** y **olla → distribuidor (tundish)**. El distribuidor → moldes queda para una etapa posterior.

## Reglas

- Todo documento que se genere o se edite sigue `docs/estilo-de-documentos.md` (regla permanente, común a los proyectos del
  mismo autor), y su entrega lleva la lista de cambios de la sección 8 de ese archivo.
- Antes de cambiar algo, lee `README.md`, `docs/siguiente-sesion.md`, `docs/proyecto.md` y `docs/pendientes.md`.
- Las decisiones abiertas de `docs/pendientes.md` son del usuario. No las cierres por iniciativa propia: pregunta, o avanza con
  un valor provisional declarado como tal.
- No inventes cotas, coeficientes de descarga, diámetros, tiempos medidos ni validaciones. Todo dato lleva procedencia y estado:
  cota del plano, medido a escala, cálculo del proveedor, heredado sin verificar, supuesto, ejemplo o dato del usuario.
- Un parámetro hidráulico sin tiempos de vaciado medidos que lo respalden se marca como preliminar en el archivo, en la
  interfaz y en los reportes.
- `modelo_vaciado/horno3d/` es una copia del motor geométrico de LWD-EAF (ver su `PROCEDENCIA.md`). No se modifica salvo las
  importaciones; si LWD-EAF cambia, se vuelve a copiar con su nueva procedencia. No modifiques el repositorio de LWD-EAF desde
  este proyecto.
- Geometría y datos de planta viven en `datos/`, no en el código. Agregar una planta es agregar archivos.
- Mantén separados cálculo, geometría, interfaz y entradas/salidas. El cálculo no importa Qt. No incorpores dependencias sin
  necesidad.
- La interfaz es de Qt (PySide6). Presenta mm, m, t, s y min, en español.
- Convención de signos del horno: inclinación positiva hacia la piquera (nariz EBT), negativa hacia la puerta. Coordenadas del
  horno: origen en el eje a nivel del fondo exterior de la coraza; +X hacia la puerta, −X hacia la piquera; Y desde el fondo de
  la coraza.
- Por cada avance, agrega una entrada a `CHANGELOG.md` (identificador `MV-NNN`) con motivo, evidencia y pendientes; usa
  `docs/plantilla-cambio.md` para cambios sustanciales. Actualiza `docs/siguiente-sesion.md` y `docs/pendientes.md` al
  terminar.
- Ejecuta las pruebas (`python -m pytest verificacion -q -p no:cacheprovider`) y registra el resultado real. No cambies una
  prueba para ocultar una divergencia.
- No incluyas cachés, credenciales, entornos ni reportes generados en commits. Las figuras de `docs/figuras/` sí se versionan.
- La versión vive sólo en `modelo_vaciado/__init__.py` y se sube con cada cambio que lo amerite, según `docs/versiones.md`
  (decisión del usuario del 2026-11-24). No cambies la visibilidad del repositorio por iniciativa propia.
- El programa se llama TapFlow y tiene un solo diseño (`docs/disenos.md`). La rama `archivo/disenos-iniciales` guarda la
  primera propuesta como historial: no se fusiona ni se desarrolla.
