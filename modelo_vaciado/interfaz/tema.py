"""El diseño de la ventana: **Magnesita** (claro), el definitivo.

Plano sobre la mesa de dibujo: gris arena mate, hoja clara con marco y cajetín, hachurado por capa y
verde escoria apagado como acento. Los colores, las familias tipográficas y las marcas de estado son
los del prototipo de interfaz de la rama ``diseno/magnesita`` (EAF-002 y EAF-003, commit ``723edee``;
ver ``PROCEDENCIA.md``), con los roles que hacen falta para lo que el programa ya calcula (nivel de
escoria, capacidad, desgaste, campaña).

Una paleta es un diccionario de roles (``ACENTO``, ``ACERO_LIQUIDO``, ``TRABAJO``…): la ventana y los
dibujos no hablan de colores sino de roles. El diseño original, Arco (oscuro), se conserva en la rama
``archivo/diseno-arco`` y no se desarrolla.
"""

from __future__ import annotations

DISENO = "magnesita"
ETIQUETA = "Magnesita (claro)"

PALETA = dict(
    FONDO="#E3DFD6", SUPERFICIE="#F2F0EA", SUPERFICIE_2="#E8E4DB", SUPERFICIE_3="#DCE5C6",
    BORDE="#C6C0B2", TEXTO="#25272A", TEXTO_2="#4F5154", TEXTO_3="#5F6164",
    ACENTO="#4A6320", ACENTO_SUAVE="#DCE5C6", SOBRE_ACENTO="#FBFAF7",
    ALARMA="#A93526", CORRECTO="#3F6A24", AVISO="#8A5D00",
    ACERO_LIQUIDO="#E3B84F", ACERO_TEXTO="#8A5D00", SOBRE_ACERO="#3A2A05",
    ESCORIA="#9DB26A", PAPEL="#FBFAF7", TINTA="#25272A",
    TRABAJO="#EAD9B8", SEGURIDAD="#D5CDBB", CAPA32="#A8A190", FONDO_REF="#DDD2BC",
    JUNTA="#A88E5C", CORAZA="#25272A", HACHURA="#B39560",
    E_COTA="#25272A", E_LEIDO="#3F6A24", E_ESCALA="#4F5154", E_DERIVADO="#5F6164",
    E_SUPUESTO="#8A5D00", E_HEREDADO="#5F6164", E_PENDIENTE="#A93526",
    # Añadidos para lo que el programa calcula y el prototipo no tenía:
    ESCORIA_TEXTO="#4F6B22", UMBRAL="#A93526", CONSUMIDO="#9A8F78", VERDE_TENUE="#B9C79A",
    E_LWD="#4A6320", E_DECISION="#4A6320", E_USUARIO="#25272A", E_MODIFICADO="#8A5D00",
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
