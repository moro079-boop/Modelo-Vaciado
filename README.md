# Modelo-Vaciado

Estimación del tiempo de vaciado del acero líquido con las ecuaciones de flujo (balance de masa, Bernoulli y Torricelli). El
alcance actual son dos escenarios:

- **Horno (EAF) → olla**, por la piquera: con las variables que define el usuario (tonelaje, altura metalostática, área de paso,
  coeficiente de descarga…) o con la cavidad 3D de la planta, el basculado y los límites del panel refrigerado.
- **Olla → distribuidor**, por la válvula deslizante: con la olla de una planta o un recipiente que define el usuario, y con el
  distribuidor a nivel constante, llenándose o sin contrapresión.

**Preliminar:** ningún parámetro hidráulico está validado con tiempos de vaciado medidos en planta. Cada dato lleva su estado
(cota del plano, cálculo del proveedor, supuesto, ejemplo, dato del usuario) en la ventana y en los reportes.

## Uso

```bash
pip install -r requirements.txt
```

```bash
python vaciado.py
```

| Orden | Qué hace |
|---|---|
| `python vaciado.py` | Abre la ventana |
| `python vaciado.py escenario.json` | Abre la ventana con ese escenario |
| `python vaciado.py --diseno colada` | Abre la ventana con otro diseño: `magnesita`, `colada`, `plano` o `turno` |
| `python vaciado.py --tiempo [a.json …]` | Cálculo directo de los dos escenarios, en texto |
| `python vaciado.py --consola [a.json …]` | Horno con cavidad 3D, sin ventana: CSV y figura |
| `python vaciado.py --curvas pesqueria` | Límites del horno por ángulo |
| `python vaciado.py --colada [a.json …]` | Secuencia olla → distribuidor → moldes (etapa posterior), en texto |
| `python empaquetado/construir.py` | Ejecutable sin Python ([empaquetado/LEEME.md](empaquetado/LEEME.md)) |

Pruebas: `pip install -r requirements-dev.txt` y `python -m pytest verificacion -q -p no:cacheprovider`.

## Documentos

| Documento | Contenido |
|---|---|
| [docs/proyecto.md](docs/proyecto.md) | Objetivo, fundamentos, datos, verificación, resultados y software |
| [docs/disenos.md](docs/disenos.md) | Diseños de la ventana, opciones de icono y de nombre |
| [docs/vaciado-ebt.md](docs/vaciado-ebt.md) | Estudio de vaciado por el EBT del proveedor, transcrito y reproducido |
| [docs/documento-de-integracion/](docs/documento-de-integracion/README.md) | Documento técnico en Word (versión 0.1, escrita en LWD-EAF) |
| [docs/pendientes.md](docs/pendientes.md) | Decisiones abiertas |
| [docs/siguiente-sesion.md](docs/siguiente-sesion.md) | Por dónde continuar |
| [CHANGELOG.md](CHANGELOG.md) | Registro de cambios |

## Origen

El modelo nació dentro de LWD-EAF (diagnóstico de desgaste del horno de arco eléctrico) y se trasladó a este repositorio el
2026-11-24. El motor geométrico del horno (`modelo_vaciado/horno3d/`) es una copia del de LWD-EAF, con su procedencia.
