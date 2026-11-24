"""Dibuja el icono de TapFlow con Qt (sin imágenes externas): ``python -m herramientas.iconos``.

El icono es un reloj de arena con acero fundido (el tiempo de vaciado), en la paleta del diseño: fondo de tinta oscura, marco
claro, tapas en azul y acero en ámbar. Escribe ``modelo_vaciado/interfaz/recursos/icono.png`` (256 px) e ``icono.ico`` (16 a
256 px) y una muestra en ``docs/figuras/icono.png``.

Las otras opciones de la primera propuesta (Chorro, Torricelli, Piquera y el reloj de alto contraste) se conservan como historial
en la rama ``archivo/disenos-iniciales`` y en ``docs/historial/disenos-iniciales/iconos.png``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import (QBrush, QColor, QFont, QGuiApplication, QImage, QLinearGradient, QPainter, QPen, QPolygonF)

RAIZ = Path(__file__).resolve().parent.parent
CARPETA = RAIZ / "modelo_vaciado" / "interfaz" / "recursos"
MUESTRA = RAIZ / "docs" / "figuras" / "icono.png"
NARANJA, AMARILLO = QColor("#F3A847"), QColor("#FFD27A")      # acero de la paleta TapFlow (ACERO_LIQUIDO) y su brillo
TINTA, CLARO, AZUL = "#13203B", "#DCE6FA", "#5B8DEF"          # fondo (TINTA), marco (ACENTO_SUAVE) y tapas (azul del acento, aclarado)


def _acero(p: QPainter, rect: QRectF) -> QBrush:
    g = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    g.setColorAt(0, AMARILLO)
    g.setColorAt(1, NARANJA)
    return QBrush(g)


def _fondo(p: QPainter, color: str):
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(color))
    p.drawRoundedRect(QRectF(8, 8, 240, 240), 52, 52)


def reloj(p: QPainter):
    _fondo(p, TINTA)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(AZUL))
    p.drawRoundedRect(QRectF(58, 38, 140, 20), 7, 7)
    p.drawRoundedRect(QRectF(58, 198, 140, 20), 7, 7)
    p.setPen(QPen(QColor(CLARO), 9, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPolyline(QPolygonF([QPointF(76, 60), QPointF(76, 80), QPointF(120, 128), QPointF(76, 176), QPointF(76, 196)]))
    p.drawPolyline(QPolygonF([QPointF(180, 60), QPointF(180, 80), QPointF(136, 128), QPointF(180, 176), QPointF(180, 196)]))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(_acero(p, QRectF(80, 90, 96, 100)))
    p.drawPolygon(QPolygonF([QPointF(92, 92), QPointF(164, 92), QPointF(128, 124)]))
    p.drawPolygon(QPolygonF([QPointF(86, 192), QPointF(170, 192), QPointF(170, 182), QPointF(128, 154), QPointF(86, 182)]))
    p.drawRect(QRectF(125, 120, 6, 50))


OPCIONES = {"reloj": reloj}


def dibujar(nombre: str, lado: int = 256) -> QImage:
    imagen = QImage(256, 256, QImage.Format.Format_ARGB32)
    imagen.fill(Qt.GlobalColor.transparent)
    p = QPainter(imagen)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    OPCIONES[nombre](p)
    p.end()
    return imagen if lado == 256 else imagen.scaled(lado, lado, Qt.AspectRatioMode.KeepAspectRatio,
                                                     Qt.TransformationMode.SmoothTransformation)


def _ico(nombre: str, ruta: Path):
    """ICO con varias resoluciones, armado a mano (Qt sólo escribe una por archivo)."""
    import struct

    from PySide6.QtCore import QBuffer, QByteArray, QIODevice

    pngs = []
    for lado in (16, 24, 32, 48, 64, 128, 256):
        datos = QByteArray()
        b = QBuffer(datos)
        b.open(QIODevice.OpenModeFlag.WriteOnly)
        dibujar(nombre, lado).save(b, "PNG")
        pngs.append((lado, bytes(datos)))
    cabecera = struct.pack("<HHH", 0, 1, len(pngs))
    entradas, cuerpo, desplazamiento = b"", b"", 6 + 16 * len(pngs)
    for lado, png in pngs:
        entradas += struct.pack("<BBBBHHII", lado % 256, lado % 256, 0, 0, 1, 32, len(png), desplazamiento)
        cuerpo += png
        desplazamiento += len(png)
    ruta.write_bytes(cabecera + entradas + cuerpo)


def muestra(ruta: Path):
    """El icono a 256, 48 y 24 px sobre el fondo de la ventana, para ver cómo se lee a cada tamaño."""
    imagen = QImage(460, 300, QImage.Format.Format_ARGB32)
    imagen.fill(QColor("#EDF1F6"))
    p = QPainter(imagen)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.drawImage(QPointF(20, 22), dibujar("reloj"))
    p.drawImage(QPointF(310, 60), dibujar("reloj", 48))
    p.drawImage(QPointF(320, 140), dibujar("reloj", 24))
    fuente = QFont()
    fuente.setPixelSize(22)
    fuente.setBold(True)
    p.setFont(fuente)
    p.setPen(QColor(TINTA))
    p.drawText(QRectF(290, 200, 160, 40), Qt.AlignmentFlag.AlignCenter, "TapFlow")
    p.end()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    imagen.save(str(ruta))


def main() -> int:
    QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
    dibujar("reloj").save(str(CARPETA / "icono.png"))
    _ico("reloj", CARPETA / "icono.ico")
    muestra(MUESTRA)
    print(f"Icono en {CARPETA} y muestra en {MUESTRA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
