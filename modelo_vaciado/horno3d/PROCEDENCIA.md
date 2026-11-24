# Procedencia del motor geométrico del horno

Los módulos de esta carpeta son copias de los módulos del mismo nombre del paquete `lwd_eaf` del repositorio LWD-EAF
(`moro079-boop/LWD-EAF`, rama `main`, commit `d3c7ad23dbb6794de3347e408849f00c4e868e0a`, 2026-11-23).

| Archivo | Origen | Cambio |
|---|---|---|
| `cache.py`, `cavidad.py`, `cavidad_general.py`, `desgaste.py`, `geometria.py`, `niveles.py` | `lwd_eaf/<mismo nombre>.py` | Ninguno |
| `planta.py` | `lwd_eaf/planta.py` | La importación de `rutas` sube un nivel (`..rutas`) |

Los archivos de planta de `datos/plantas/` (formato `lwd_eaf.planta/1`) se copiaron del mismo commit, sin cambios.

Reglas:

- No se modifican aquí salvo las importaciones. Si LWD-EAF corrige la cavidad o los niveles, se vuelven a copiar los
  módulos y los archivos de planta y se actualiza esta tabla con el nuevo commit.
- Las referencias internas de las docstrings (`lwd_eaf.niveles`, `lwd_eaf.campana`…) son las del repositorio de origen.
