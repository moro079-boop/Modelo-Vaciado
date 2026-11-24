"""El diseño de la ventana: **TapFlow**, claro, con la paleta de plano técnico (blanco, azul y tinta) y el acero en ámbar.

Una paleta es un diccionario de roles (``ACENTO``, ``ACERO_LIQUIDO``, ``TINTA``…): la ventana y las gráficas no hablan de
colores sino de roles. Los roles y las marcas de estado vienen del diseño Magnesita de LWD-EAF; los colores, del diseño «Plano»
de la primera propuesta (MV-003). Los diseños de esa propuesta (Magnesita, Colada, Plano y Turno) se conservan como historial en
la rama ``archivo/disenos-iniciales`` y en ``docs/historial/disenos-iniciales/``.
"""

from __future__ import annotations

DISENO = "vaciat"
ETIQUETA = "TapFlow"

PALETA = dict(
    FONDO="#EDF1F6", SUPERFICIE="#FFFFFF", SUPERFICIE_2="#E2E8F0", SUPERFICIE_3="#D7E4F6",
    BORDE="#C2CCD8", TEXTO="#13203B", TEXTO_2="#3A4863", TEXTO_3="#55627A",
    ACENTO="#1D4ED8", ACENTO_SUAVE="#DCE6FA", SOBRE_ACENTO="#FFFFFF", ACENTO_OSCURO="#173EA8",
    PELIGRO_SUAVE="#FBE2DF", ENFOQUE="#FFFFFF",
    ALARMA="#B42318", CORRECTO="#1E7B45", AVISO="#8A5A00",
    ACERO_LIQUIDO="#F3A847", ACERO_TEXTO="#984C00", SOBRE_ACERO="#3A2A05",
    ESCORIA="#9DB26A", PAPEL="#FFFFFF", TINTA="#13203B",
    TRABAJO="#EAD9B8", SEGURIDAD="#D5CDBB", CAPA32="#A8A190", FONDO_REF="#DDD2BC",
    JUNTA="#A88E5C", CORAZA="#13203B", HACHURA="#B39560",
    E_COTA="#13203B", E_LEIDO="#1E7B45", E_ESCALA="#3A4863", E_DERIVADO="#55627A",
    E_SUPUESTO="#8A5A00", E_HEREDADO="#55627A", E_PENDIENTE="#B42318",
    ESCORIA_TEXTO="#4F6B22", UMBRAL="#B42318", CONSUMIDO="#9A8F78", VERDE_TENUE="#B9CBF2",
    E_LWD="#1D4ED8", E_DECISION="#1D4ED8", E_USUARIO="#13203B", E_MODIFICADO="#8A5A00",
    # Series de las gráficas y la cabecera oscura del tablero
    SERIE_2="#0E9AA7", SERIE_3="#D9480F", SERIE_5="#7048E8",
    CABECERA="#13203B", SOBRE_CABECERA="#FFFFFF", CABECERA_2="#24345A", CABECERA_TENUE="#AFC3EA",
)

# Familias candidatas, en orden de preferencia; se usa la primera que haya instalada (la elige ``tema_qt.resolver_familias``).
_SANS = ("Trebuchet MS", "Fira Sans", "DejaVu Sans")
_MONO = ("Consolas", "DejaVu Sans Mono")

# Marcas de estado: la forma las distingue aunque el color no se vea.
MARCAS = {
    "cota_del_plano": "●", "leido_del_plano": "●", "medido_a_escala": "◆", "derivado": "●",
    "supuesto": "■", "heredado_sin_verificar": "▼", "heredado": "▼", "por_definir": "○",
    "tomado_del_lwd": "▲", "decision_del_usuario": "▶", "dato_del_usuario": "●", "modificado": "◐", "ajustado": "◈",
    "calculo_del_proveedor": "◇", "ejemplo": "□",
}
_COLOR_ESTADO = {
    "cota_del_plano": "E_COTA", "leido_del_plano": "E_LEIDO", "medido_a_escala": "E_ESCALA",
    "derivado": "E_DERIVADO", "supuesto": "E_SUPUESTO", "heredado_sin_verificar": "E_HEREDADO",
    "heredado": "E_HEREDADO", "por_definir": "E_PENDIENTE", "tomado_del_lwd": "E_LWD",
    "decision_del_usuario": "E_DECISION", "dato_del_usuario": "E_USUARIO", "modificado": "E_MODIFICADO",
    "ajustado": "E_LEIDO", "calculo_del_proveedor": "E_ESCALA", "ejemplo": "E_SUPUESTO",
}
TEXTO_ESTADO = {
    "cota_del_plano": "cota del plano", "leido_del_plano": "leído del plano",
    "medido_a_escala": "medido a escala", "derivado": "derivado", "supuesto": "supuesto",
    "heredado_sin_verificar": "heredado sin verificar", "heredado": "heredado sin verificar",
    "por_definir": "por definir", "tomado_del_lwd": "tomado del LWD",
    "decision_del_usuario": "decisión del usuario", "dato_del_usuario": "dato del usuario",
    "modificado": "modificado", "ajustado": "ajustado a mediciones",
    "calculo_del_proveedor": "cálculo del proveedor", "ejemplo": "ejemplo",
}

FAMILIA_SANS = _SANS[0]
FAMILIA_CIFRA = _MONO[0]
FAMILIA_MONO = _MONO[0]

# Cada rol es una constante del módulo (``tema.ACENTO``) para que el código se lea como el del prototipo.
globals().update(PALETA)
# Líneas finas sobre el papel: los rellenos del plano (acero, escoria) no tienen contraste suficiente como trazo.
LINEA_ACERO = PALETA["ACERO_TEXTO"]
LINEA_ESCORIA = PALETA["ESCORIA_TEXTO"]

def fuente(tamano: int, negrita: bool = False):
    return (FAMILIA_SANS, tamano, "bold") if negrita else (FAMILIA_SANS, tamano)


def fuente_cifra(tamano: int):
    return (FAMILIA_CIFRA, tamano)


def fuente_mono(tamano: int):
    return (FAMILIA_MONO, tamano)


def marca(estado: str) -> str:
    return MARCAS.get(estado, "○")


def color_estado(estado: str) -> str:
    return PALETA[_COLOR_ESTADO.get(estado, "E_PENDIENTE")]


def texto_estado(estado: str) -> str:
    return TEXTO_ESTADO.get(estado, estado.replace("_", " "))


def luminancia(color: str) -> float:
    c = color.lstrip("#")
    r, g, b = (int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))

    def f(v):
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contraste(a: str, b: str) -> float:
    la, lb = sorted((luminancia(a), luminancia(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def suavizar(color: str, parte: float = 0.4, base: str | None = None) -> str:
    """Mezcla ``parte`` de ``color`` con ``base`` (el papel): los colores del plano, apagados para la hoja."""
    base = base or PALETA["PAPEL"]
    a, b = color.lstrip("#"), base.lstrip("#")
    mezcla = [round(int(a[i:i + 2], 16) * parte + int(b[i:i + 2], 16) * (1 - parte)) for i in (0, 2, 4)]
    return "#%02X%02X%02X" % tuple(mezcla)


def estilo_matplotlib() -> dict:
    """rcParams para que las figuras incrustadas sean parte de la hoja."""
    P = PALETA
    return {
        "figure.facecolor": P["PAPEL"], "axes.facecolor": P["PAPEL"], "savefig.facecolor": P["PAPEL"],
        "axes.edgecolor": P["TINTA"], "axes.labelcolor": P["TEXTO_2"], "axes.titlecolor": P["TEXTO"],
        "axes.grid": True, "grid.color": P["BORDE"], "grid.linewidth": 0.6, "grid.alpha": 0.7,
        "xtick.color": P["TEXTO_3"], "ytick.color": P["TEXTO_3"], "text.color": P["TEXTO"],
        "font.family": [FAMILIA_SANS, "DejaVu Sans"], "font.size": 9, "axes.titlesize": 10,
        "axes.labelsize": 9, "legend.facecolor": P["PAPEL"], "legend.edgecolor": P["BORDE"],
        "legend.labelcolor": P["TEXTO_2"], "legend.fontsize": 8, "figure.autolayout": False,
        "hatch.color": P["HACHURA"], "hatch.linewidth": 0.7,
        "figure.dpi": 100,          # Qt escala el lienzo en pantallas de alta densidad; un matplotlibrc del sistema no debe hacerlo dos veces
    }
