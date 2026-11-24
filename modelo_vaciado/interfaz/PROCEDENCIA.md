# Procedencia de los componentes de la interfaz

Copiados de `lwd_eaf/interfaz/` del repositorio LWD-EAF (commit `d3c7ad23dbb6794de3347e408849f00c4e868e0a`, 2026-11-23).

| Archivo | Origen | Cambio |
|---|---|---|
| `tema.py` | `lwd_eaf/interfaz/tema.py` | Mismos roles y marcas de estado; paleta VaciaT en lugar de Magnesita (MV-004); estados «cálculo del proveedor» y «ejemplo»; 100 ppp en las figuras |
| `tema_qt.py` | `lwd_eaf/interfaz/tema_qt.py` | Flechas propias, tamaño de letra, color de foco, campos numéricos, pestañas, menús, barra de estado y el acomodo de tablero (cabecera, pasos e indicadores) en la hoja de estilo (MV-003, MV-004) |
| `widgets.py`, `formato.py` | `lwd_eaf/interfaz/` | Ninguno |
| `recursos/icono.png`, `recursos/icono.ico` | Nuevos (MV-004) | Icono de VaciaT, dibujado con `herramientas/iconos.py`; reemplaza al de LWD-EAF |

Estos componentes pueden evolucionar en este repositorio; a diferencia de `horno3d/`, no son una copia de solo lectura.
