"""Dibuja las opciones de icono del programa con Qt (sin imágenes externas): ``python -m herramientas.iconos``.

Escribe en ``modelo_vaciado/interfaz/recursos/iconos/`` un PNG de 256 px y un ICO (16 a 256 px) por opción, y una lámina con
todas en ``docs/figuras/disenos/iconos.png``:

- ``chorro``      olla de colada vertiendo un chorro de acero (diseño Colada).
- ``torricelli``  depósito con el orificio en el fondo y la parábola del chorro (diseño Plano).
- ``reloj``       reloj de arena con acero fundido: el tiempo de vaciado (diseño Turno).
- ``piquera``     horno basculado con el chorro saliendo por la piquera excéntrica (opción libre).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import (QBrush, QColor, QFont, QGuiApplication, QImage, QLinearGradient, QPainter, QPainterPath,  # noqa: E402
                           QPen, QPolygonF)

RAIZ = Path(__file__).resolve().parent.parent
CARPETA = RAIZ / "modelo_vaciado" / "interfaz" / "recursos" / "iconos"
LAMINA = RAIZ / "docs" / "figuras" / "disenos" / "iconos.png"
NARANJA, AMARILLO = QColor("#F28C28"), QColor("#FFC14D")


def _acero(p: QPainter, rect: QRectF) -> QBrush:
    g = QLinearGradient(rect.topLeft(), rect.bottomLeft())
    g.setColorAt(0, AMARILLO)
    g.setColorAt(1, NARANJA)
    return QBrush(g)


def _fondo(p: QPainter, color: str):
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(color))
    p.drawRoundedRect(QRectF(8, 8, 240, 240), 52, 52)


def chorro(p: QPainter):
    _fondo(p, "#1E2227")
    olla = QPolygonF([QPointF(52, 70), QPointF(150, 46), QPointF(168, 128), QPointF(86, 150)])
    p.setBrush(QColor("#C9CED5"))
    p.drawPolygon(olla)
    p.setBrush(QColor("#1E2227"))
    p.drawPolygon(QPolygonF([QPointF(66, 78), QPointF(142, 60), QPointF(154, 118), QPointF(92, 134)]))
    p.setBrush(_acero(p, QRectF(70, 62, 86, 72)))
    p.drawPolygon(QPolygonF([QPointF(72, 104), QPointF(146, 76), QPointF(154, 118), QPointF(92, 134)]))
    camino = QPainterPath(QPointF(150, 52))
    camino.cubicTo(QPointF(176, 60), QPointF(186, 120), QPointF(184, 214))
    camino.lineTo(QPointF(166, 214))
    camino.cubicTo(QPointF(168, 130), QPointF(160, 80), QPointF(146, 66))
    camino.closeSubpath()
    p.setBrush(_acero(p, QRectF(140, 50, 50, 170)))
    p.drawPath(camino)
    p.setBrush(QColor(NARANJA))
    p.drawEllipse(QRectF(140, 206, 72, 18))


def torricelli(p: QPainter):
    _fondo(p, "#FFFFFF")
    p.setPen(QPen(QColor("#1D4ED8"), 10, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPolyline(QPolygonF([QPointF(52, 44), QPointF(52, 170), QPointF(96, 170)]))
    p.drawPolyline(QPolygonF([QPointF(124, 170), QPointF(168, 170), QPointF(168, 44)]))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(_acero(p, QRectF(57, 80, 106, 86)))
    p.drawRect(QRectF(57, 82, 106, 84))
    camino = QPainterPath(QPointF(97, 165))
    camino.cubicTo(QPointF(100, 200), QPointF(150, 222), QPointF(214, 220))
    camino.lineTo(QPointF(214, 206))
    camino.cubicTo(QPointF(160, 206), QPointF(124, 194), QPointF(123, 165))
    camino.closeSubpath()
    p.setBrush(QColor(NARANJA))
    p.drawPath(camino)
    p.setPen(QPen(QColor("#13203B"), 5, Qt.PenStyle.DashLine))
    p.drawLine(QPointF(186, 82), QPointF(186, 170))
    p.setPen(QPen(QColor("#13203B"), 6))
    p.drawLine(QPointF(176, 82), QPointF(196, 82))
    p.drawLine(QPointF(176, 170), QPointF(196, 170))


def reloj(p: QPainter):
    _fondo(p, "#000000")
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#FFFFFF"))
    p.drawRoundedRect(QRectF(60, 40, 136, 18), 6, 6)
    p.drawRoundedRect(QRectF(60, 198, 136, 18), 6, 6)
    p.setPen(QPen(QColor("#FFFFFF"), 9, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPolyline(QPolygonF([QPointF(76, 60), QPointF(76, 80), QPointF(120, 128), QPointF(76, 176), QPointF(76, 196)]))
    p.drawPolyline(QPolygonF([QPointF(180, 60), QPointF(180, 80), QPointF(136, 128), QPointF(180, 176), QPointF(180, 196)]))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(_acero(p, QRectF(80, 90, 96, 100)))
    p.drawPolygon(QPolygonF([QPointF(92, 92), QPointF(164, 92), QPointF(128, 124)]))
    p.drawPolygon(QPolygonF([QPointF(86, 192), QPointF(170, 192), QPointF(170, 182), QPointF(128, 154), QPointF(86, 182)]))
    p.drawRect(QRectF(125, 120, 6, 50))


def piquera(p: QPainter):
    _fondo(p, "#2B3A4A")
    p.save()
    p.translate(118, 112)
    p.rotate(12)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("#D5DAE0"))
    camino = QPainterPath()
    camino.moveTo(-78, -40)
    camino.lineTo(78, -40)
    camino.lineTo(78, 20)
    camino.quadTo(78, 62, 0, 62)
    camino.quadTo(-78, 62, -78, 20)
    camino.closeSubpath()
    p.drawPath(camino)
    p.setBrush(_acero(p, QRectF(-66, -6, 132, 60)))
    bano = QPainterPath()
    bano.moveTo(-66, 0)
    bano.lineTo(66, 0)
    bano.lineTo(66, 20)
    bano.quadTo(66, 50, 0, 50)
    bano.quadTo(-66, 50, -66, 20)
    bano.closeSubpath()
    p.drawPath(bano)
    p.setBrush(QColor("#2B3A4A"))
    p.drawRect(QRectF(-58, 46, 14, 24))
    p.restore()
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(_acero(p, QRectF(44, 160, 24, 60)))
    p.drawRect(QRectF(47, 160, 13, 58))
    p.setBrush(QColor(NARANJA))
    p.drawEllipse(QRectF(24, 212, 60, 14))


OPCIONES = {"chorro": chorro, "torricelli": torricelli, "reloj": reloj, "piquera": piquera}


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


def lamina(ruta: Path):
    ancho = 4 * 300
    imagen = QImage(ancho, 360, QImage.Format.Format_ARGB32)
    imagen.fill(QColor("#F4F4F0"))
    p = QPainter(imagen)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    fuente = QFont()
    fuente.setPixelSize(26)
    fuente.setBold(True)
    p.setFont(fuente)
    for i, nombre in enumerate(OPCIONES):
        p.drawImage(QPointF(22 + 300 * i, 22), dibujar(nombre))
        p.setPen(QColor("#13203B"))
        p.drawText(QRectF(300 * i, 290, 300, 50), Qt.AlignmentFlag.AlignCenter, nombre.capitalize())
    p.end()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    imagen.save(str(ruta))


def main() -> int:
    QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
    CARPETA.mkdir(parents=True, exist_ok=True)
    for nombre in OPCIONES:
        dibujar(nombre).save(str(CARPETA / f"{nombre}.png"))
        _ico(nombre, CARPETA / f"{nombre}.ico")
    lamina(LAMINA)
    print(f"Iconos en {CARPETA} y lámina en {LAMINA}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
