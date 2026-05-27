import logging
import os
from pathlib import Path
import sys

import click

from wireviz_gui.app import Application


@click.command()
@click.option(
    "--graphviz-path",
    "-p",
    default=None,
    help="Ruta al directorio bin/ de Graphviz (opcional si está en PATH o bundleado).",
)
@click.option(
    "--debug",
    is_flag=True,
    default=False,
    help="Activar logging de depuración.",
)
def main(graphviz_path, debug):
    # ── 1. Graphviz bundleado (cuando se ejecuta como EXE compilado) ─────────
    if hasattr(sys, "_MEIPASS"):
        # Añadir _MEIPASS al PATH de subprocesos.
        # PyInstaller solo registra _MEIPASS via AddDllDirectory (para extensiones
        # .pyd de Python), pero NOT en os.environ["PATH"], por lo que los
        # subprocesos como dot.exe no encuentran tcl86.dll de Python (8.6.15)
        # que PyInstaller coloca ahí. dot.exe falla al arrancar → BrokenPipeError.
        os.environ["PATH"] = sys._MEIPASS + os.pathsep + os.environ.get("PATH", "")
        bundled_gv = Path(sys._MEIPASS) / "graphviz"
        if bundled_gv.exists():
            os.environ["PATH"] = str(bundled_gv) + os.pathsep + os.environ.get("PATH", "")

    # ── 2. Graphviz pasado por argumento en línea de comandos ────────────────
    if graphviz_path is not None:
        os.environ["PATH"] = graphviz_path + os.pathsep + os.environ.get("PATH", "")

    # ── 3. Nivel de log ──────────────────────────────────────────────────────
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(level=level, format="%(levelname)s [%(name)s] %(message)s")

    Application()


main()
