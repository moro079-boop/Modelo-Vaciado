"""Diseños de la ventana: paleta de roles, tamaño de letra, hoja de estilo adicional, acomodo e icono.

Todos usan Qt (PySide6, estilo Fusion) y los mismos componentes; cambian el aspecto y el acomodo de la ventana:

- ``magnesita``  el diseño heredado de LWD-EAF: claro, arena y verde escoria; pestañas arriba.
- ``colada``     oscuro, grafito con el naranja del acero fundido; navegación lateral e indicadores en la cabecera. Pensado
                 para salas de control con poca luz.
- ``plano``      claro, blanco y azul de plano técnico; barra de marca y pestañas planas. Pensado para el escritorio de
                 ingeniería y para capturas en informes.
- ``turno``      alto contraste, letra grande y botones anchos; tablero con indicadores grandes siempre a la vista. Pensado para
                 una pantalla de piso de planta o de turno.

Un diseño se aplica antes de construir la ventana (``aplicar``): copia su paleta sobre ``tema.PALETA``, de modo que la hoja de
estilo, los widgets y las gráficas de Matplotlib lo siguen sin conocerlo.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import tema

_BASE = dict(tema.PALETA)          # Magnesita, tal como la define tema.py


@dataclass(frozen=True)
class Diseno:
    nombre: str
    etiqueta: str
    descripcion: str
    acomodo: str                    # "pestanas", "lateral" o "tablero"
    icono: str                      # archivo de recursos/iconos/ (o recursos/icono.png)
    tamano: float = 10.0            # puntos de la letra de los controles
    paleta: dict = field(default_factory=dict)
    hoja: str = ""                  # hoja de estilo adicional (se formatea con la paleta)


COLADA = dict(
    FONDO="#15181C", SUPERFICIE="#1E2227", SUPERFICIE_2="#292E35", SUPERFICIE_3="#3B2A1A", BORDE="#3A414A",
    TEXTO="#ECEEF1", TEXTO_2="#BAC0C8", TEXTO_3="#9AA2AC", ACENTO="#F28C28", ACENTO_SUAVE="#3B2A1A", SOBRE_ACENTO="#15181C",
    ACENTO_OSCURO="#C96E14", PELIGRO_SUAVE="#4A2420", ENFOQUE="#23282E",
    ALARMA="#FF7A6B", CORRECTO="#62D394", AVISO="#F4C55A",
    ACERO_LIQUIDO="#F59A2E", ACERO_TEXTO="#FFB866", SOBRE_ACERO="#1A1206", ESCORIA="#8FA35E", PAPEL="#1A1E23", TINTA="#ECEEF1",
    CORAZA="#C9CED5", HACHURA="#6B5A3E", JUNTA="#6B5A3E",
    E_COTA="#ECEEF1", E_LEIDO="#62D394", E_ESCALA="#BAC0C8", E_DERIVADO="#9AA2AC", E_SUPUESTO="#F4C55A", E_HEREDADO="#9AA2AC",
    E_PENDIENTE="#FF7A6B", E_LWD="#F28C28", E_DECISION="#F28C28", E_USUARIO="#ECEEF1", E_MODIFICADO="#F4C55A",
    VERDE_TENUE="#5A3C1C", SERIE_2="#5AA9FF", SERIE_3="#F28C28", SERIE_5="#C792EA",
)
PLANO = dict(
    FONDO="#EDF1F6", SUPERFICIE="#FFFFFF", SUPERFICIE_2="#E2E8F0", SUPERFICIE_3="#D7E4F6", BORDE="#C2CCD8",
    TEXTO="#13203B", TEXTO_2="#3A4863", TEXTO_3="#55627A", ACENTO="#1D4ED8", ACENTO_SUAVE="#DCE6FA", SOBRE_ACENTO="#FFFFFF",
    ACENTO_OSCURO="#173EA8", PELIGRO_SUAVE="#FBE2DF", ENFOQUE="#FFFFFF",
    ALARMA="#B42318", CORRECTO="#1E7B45", AVISO="#8A5A00",
    ACERO_LIQUIDO="#F3A847", ACERO_TEXTO="#984C00", PAPEL="#FFFFFF", TINTA="#13203B", CORAZA="#13203B",
    E_COTA="#13203B", E_LEIDO="#1E7B45", E_ESCALA="#3A4863", E_SUPUESTO="#8A5A00", E_LWD="#1D4ED8", E_DECISION="#1D4ED8",
    E_USUARIO="#13203B", E_MODIFICADO="#8A5A00", VERDE_TENUE="#B9CBF2", SERIE_2="#0E9AA7", SERIE_3="#D9480F", SERIE_5="#7048E8",
)
TURNO = dict(
    FONDO="#F2F2EE", SUPERFICIE="#FFFFFF", SUPERFICIE_2="#E4E4DE", SUPERFICIE_3="#CFEDEE", BORDE="#7D7D76",
    TEXTO="#000000", TEXTO_2="#1F1F1F", TEXTO_3="#3D3D3D", ACENTO="#005F69", ACENTO_SUAVE="#CFEDEE", SOBRE_ACENTO="#FFFFFF",
    ACENTO_OSCURO="#00434A", PELIGRO_SUAVE="#FAD9D4", ENFOQUE="#FFFFFF",
    ALARMA="#A30D00", CORRECTO="#0B6B2A", AVISO="#7A4E00",
    ACERO_LIQUIDO="#FFB000", ACERO_TEXTO="#7A4E00", PAPEL="#FFFFFF", TINTA="#000000", CORAZA="#000000",
    E_COTA="#000000", E_LEIDO="#0B6B2A", E_ESCALA="#1F1F1F", E_SUPUESTO="#7A4E00", E_LWD="#005F69", E_DECISION="#005F69",
    E_USUARIO="#000000", E_MODIFICADO="#7A4E00", VERDE_TENUE="#9FD8DC", SERIE_2="#0057B8", SERIE_3="#D9480F", SERIE_5="#6F2DA8",
)

_HOJA_COLADA = """
QFrame#Navegacion { background: %(SUPERFICIE)s; border-right: 1px solid %(BORDE)s; }
QPushButton#Nav { text-align: left; background: transparent; border: none; border-left: 4px solid transparent; border-radius: 0;
    padding: 12px 14px; color: %(TEXTO_2)s; font-size: 10.5pt; font-weight: 500; }
QPushButton#Nav:hover { background: %(SUPERFICIE_2)s; color: %(TEXTO)s; }
QPushButton#Nav:checked { border-left: 4px solid %(ACENTO)s; background: %(ACENTO_SUAVE)s; color: %(ACENTO)s; font-weight: 700; }
QFrame#Indicadores { background: %(SUPERFICIE)s; border-bottom: 1px solid %(BORDE)s; }
QFrame#Kpi { background: %(SUPERFICIE_2)s; border-radius: 10px; }
QLabel#KpiValor { font-size: 19pt; font-weight: 700; color: %(TEXTO)s; }
QLabel#KpiValorAcento { font-size: 19pt; font-weight: 700; color: %(ACENTO)s; }
QLabel#KpiRotulo { font-size: 8pt; font-weight: 600; color: %(TEXTO_3)s; }
"""
_HOJA_PLANO = """
QFrame#Barra { background: %(TEXTO)s; }
QLabel#MarcaBarra { color: #FFFFFF; font-size: 14pt; font-weight: 700; letter-spacing: 1px; }
QLabel#LemaBarra { color: #AFC3EA; font-size: 9pt; }
QTabWidget#Paginas::pane { border: none; background: %(FONDO)s; }
QTabWidget#Paginas > QTabBar::tab { background: transparent; color: %(TEXTO_2)s; padding: 10px 22px; font-size: 10.5pt;
    border: none; border-bottom: 3px solid transparent; }
QTabWidget#Paginas > QTabBar::tab:selected { color: %(ACENTO)s; border-bottom: 3px solid %(ACENTO)s; font-weight: 700; }
QFrame#Tarjeta { border-radius: 4px; }
QLabel#Encabezado { border-top-left-radius: 3px; border-top-right-radius: 3px; letter-spacing: 1px; }
QPushButton { border-radius: 3px; }
"""
_HOJA_TURNO = """
QFrame#Cabecera { background: %(TEXTO)s; }
QLabel#MarcaBarra { color: #FFFFFF; font-size: 16pt; font-weight: 800; }
QPushButton#Paso { background: #2B2B2B; color: #FFFFFF; border: 2px solid #2B2B2B; border-radius: 8px; padding: 12px 22px;
    font-size: 12pt; font-weight: 700; }
QPushButton#Paso:hover { border-color: %(ACERO_LIQUIDO)s; }
QPushButton#Paso:checked { background: %(ACERO_LIQUIDO)s; color: #000000; border-color: %(ACERO_LIQUIDO)s; }
QFrame#Kpi { background: #FFFFFF; border: 2px solid #000000; border-radius: 10px; }
QLabel#KpiValor { font-size: 26pt; font-weight: 800; color: #000000; }
QLabel#KpiValorAcento { font-size: 26pt; font-weight: 800; color: %(ACENTO)s; }
QLabel#KpiRotulo { font-size: 9.5pt; font-weight: 700; color: #000000; }
QPushButton { padding: 8px 14px; font-size: 10.5pt; border-width: 2px; }
QDoubleSpinBox, QComboBox, QLineEdit { border-width: 2px; padding: 6px 8px; }
QLabel#Encabezado { font-size: 10pt; background: %(TEXTO)s; color: #FFFFFF; }
"""

DISENOS = {
    "magnesita": Diseno("magnesita", "Magnesita (actual)", "El diseño heredado de LWD-EAF: claro, arena y verde escoria.",
                        "pestanas", "../icono.png"),
    "colada": Diseno("colada", "Colada (oscuro)", "Grafito con el naranja del acero fundido; navegación lateral e indicadores.",
                     "lateral", "chorro.png", 10.0, COLADA, _HOJA_COLADA),
    "plano": Diseno("plano", "Plano (técnico)", "Blanco y azul de plano técnico; barra de marca y pestañas planas.",
                    "pestanas", "torricelli.png", 10.0, PLANO, _HOJA_PLANO),
    "turno": Diseno("turno", "Turno (alto contraste)", "Letra grande, botones anchos e indicadores grandes para el piso de planta.",
                    "tablero", "reloj.png", 11.5, TURNO, _HOJA_TURNO),
}
POR_OMISION = "magnesita"


def aplicar(nombre: str) -> Diseno:
    """Copia la paleta del diseño sobre ``tema.PALETA`` (y sus constantes de módulo) y lo devuelve."""
    if nombre not in DISENOS:
        raise ValueError(f"diseño desconocido: {nombre!r}; los posibles: {', '.join(DISENOS)}")
    d = DISENOS[nombre]
    tema.PALETA.clear()
    tema.PALETA.update(_BASE)
    tema.PALETA.update(d.paleta)
    vars(tema).update(tema.PALETA)
    tema.LINEA_ACERO = tema.PALETA["ACERO_TEXTO"]
    tema.LINEA_ESCORIA = tema.PALETA["ESCORIA_TEXTO"]
    tema.DISENO, tema.ETIQUETA = d.nombre, d.etiqueta
    return d


def hoja_adicional(d: Diseno) -> str:
    return d.hoja % tema.PALETA if d.hoja else ""
