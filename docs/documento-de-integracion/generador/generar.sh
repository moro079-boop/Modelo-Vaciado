#!/bin/bash
# Regenera el documento de integración de Vaciado-EAF en Word y su paginación (mismo formato que el de LWD-EAF).
# Requisitos: Node.js con el paquete npm "docx" (NODE_PATH al directorio global), LibreOffice (soffice), poppler-utils y Python 3
# con Pillow. Las figuras propias se regeneran antes con: python docs/documento-de-integracion/generador/figuras.py
# Uso: ./generar.sh salida.docx
set -e
cd "$(dirname "$0")"
OUT=${1:-documento.docx}
PAGINAR=./paginar.py
rm -f pages.json refs.json
node contenido.js "$OUT" >/dev/null
cp "$OUT.refs.json" refs.json
REFS=refs.json node contenido.js "$OUT" >/dev/null
soffice --headless --convert-to pdf "$OUT" >/dev/null 2>&1
python3 "$PAGINAR" "${OUT%.docx}.pdf" "$OUT.heads.json" pages.json
REFS=refs.json PAGES=pages.json node contenido.js "$OUT"
soffice --headless --convert-to pdf "$OUT" >/dev/null 2>&1
echo "Generado $OUT (y su PDF de comprobación); los archivos .json y .pdf intermedios no se versionan."
