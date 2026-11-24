"""Hace el ejecutable del modelo de vaciado con PyInstaller:
``python empaquetado/construir.py``.

Corre en la máquina donde se va a usar (**un ejecutable de Windows se hace en Windows**), necesita
``requirements.txt`` y ``pip install pyinstaller``, y no pide permisos de administrador.

Salida: ``dist/<nombre>/`` (carpeta con el ejecutable) y ``dist/<nombre>-<versión>-<sistema>.zip``. Incluye los datos de
planta, los datos de vaciado y los escenarios de ejemplo. Al terminar corre ``--probar-ventana`` con el ejecutable recién hecho.
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from modelo_vaciado import VERSION_MODELO  # noqa: E402

NOMBRE = "VaciaT"
# Módulos que el programa no usa y que otras bibliotecas arrastran si están instalados (adelgazan el ejecutable; medido en Linux:
# ver CHANGELOG, MV-004). Matplotlib necesita Pillow y fontTools (PDF), que se quedan.
EXCLUIDOS = ("scipy", "pandas", "lxml", "IPython", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtNetwork", "PySide6.QtPdf",
             "matplotlib.backends.backend_gtk3agg", "matplotlib.backends.backend_gtk3cairo", "matplotlib.backends.backend_gtk4agg",
             "gi")


def construir() -> Path:
    try:
        import PyInstaller  # noqa: F401
        import PySide6  # noqa: F401
    except ImportError as error:
        sys.exit(f"Falta {error.name}: pip install -r requirements.txt pyinstaller")
    sep = os.pathsep
    datos = [(RAIZ / "datos" / "plantas", "datos/plantas"), (RAIZ / "datos" / "vaciado", "datos/vaciado"), (RAIZ / "datos" / "estudios", "datos/estudios"),
             (RAIZ / "ejemplos", "ejemplos"), (RAIZ / "modelo_vaciado" / "interfaz" / "recursos", "modelo_vaciado/interfaz/recursos")]
    comando = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--windowed",
               "--name", NOMBRE, "--icon", str(RAIZ / "modelo_vaciado" / "interfaz" / "recursos" / "icono.ico"),
               "--distpath", str(RAIZ / "dist"), "--workpath", str(RAIZ / "build"), "--specpath", str(RAIZ / "build"),
               "--hidden-import", "matplotlib.backends.backend_qtagg", "--hidden-import", "matplotlib.backends.backend_pdf",
               "--hidden-import", "openpyxl", "--exclude-module", "tkinter", "--exclude-module", "matplotlib.backends.backend_tkagg",
               *[a for m in EXCLUIDOS for a in ("--exclude-module", m)],
               "--collect-submodules", "modelo_vaciado"]
    for origen, destino in datos:
        comando += ["--add-data", f"{origen}{sep}{destino}"]
    comando.append(str(RAIZ / "vaciado.py"))
    print(" ".join(comando))
    subprocess.run(comando, check=True, cwd=RAIZ)
    carpeta = RAIZ / "dist" / NOMBRE
    ejecutable = carpeta / (NOMBRE + (".exe" if platform.system() == "Windows" else ""))
    if not ejecutable.is_file():
        sys.exit(f"No se encontró {ejecutable}")
    entorno = dict(os.environ, QT_QPA_PLATFORM=os.environ.get("QT_QPA_PLATFORM", "offscreen"))
    try:
        prueba = subprocess.run([str(ejecutable), "--probar-ventana"], env=entorno, timeout=300)
        if prueba.returncode != 0:
            sys.exit(f"El ejecutable no pasó --probar-ventana (código {prueba.returncode})")
        print("El ejecutable abre la ventana, calcula y exporta.")
    except PermissionError as error:        # un antivirus o una política puede negar ejecutar el .exe recién hecho
        if os.environ.get("CI"):
            raise
        print(f"AVISO: el sistema no dejó ejecutar {ejecutable.name} para probarlo ({error}). Se sigue hasta el .zip.")
    zip_ruta = RAIZ / "dist" / f"{NOMBRE}-{VERSION_MODELO}-{platform.system().lower()}.zip"
    with zipfile.ZipFile(zip_ruta, "w", zipfile.ZIP_DEFLATED) as z:
        for archivo in sorted(carpeta.rglob("*")):
            if archivo.is_file():
                z.write(archivo, Path(NOMBRE) / archivo.relative_to(carpeta))
    print(f"Hecho: {zip_ruta} ({zip_ruta.stat().st_size / 1e6:.0f} MB)")
    return zip_ruta


if __name__ == "__main__":
    construir()
