# Documento de integración del proyecto

Documento técnico en Word del modelo de vaciado, con el formato del documento de integración de LWD-EAF (formato Ternium, A4,
cabecera con logotipo).

- `Vaciado-EAF_documento_de_integracion.docx`: versión 0.1 del documento (2026-11-20), escrita cuando el modelo formaba parte de
  LWD-EAF. Describe el modelo 0.1.0-preliminar: objetivo y alcance, plan por fases, justificación, fundamentos, desarrollo y
  resultados, y descripción del código. Se trasladó sin cambios; las rutas de código que menciona son las de LWD-EAF
  (`lwd_eaf/vaciado/`), que en este repositorio corresponden a `modelo_vaciado/`.
- `generador/`: `contenido.js` contiene el texto y usa el formato de `lib2.js` y su logotipo (copiados del documento de
  LWD-EAF); `figuras.py` regenera `mapas_horno.png`, `secuencia_colada.png` y `olla.png`; `generar.sh` arma el documento y su
  paginación con `paginar.py`.

## Regeneración

Requisitos: Node.js con el paquete npm `docx`, LibreOffice, poppler-utils, Python 3 con Pillow y las dependencias del programa
para las figuras.

```bash
python docs/documento-de-integracion/generador/figuras.py
cd docs/documento-de-integracion/generador
./generar.sh Vaciado-EAF_documento_de_integracion.docx
mv Vaciado-EAF_documento_de_integracion.docx ..
```

Los archivos `.json` y `.pdf` intermedios no se versionan. Las capturas de la ventana se toman de `docs/figuras/`.
