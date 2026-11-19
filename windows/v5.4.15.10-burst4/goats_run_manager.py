from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
_DLL_HANDLES = []


def prepare_qt_runtime() -> None:
    # Ignore Qt paths inherited from IDEs / Anaconda / QGIS / old PyQt installs.
    for key in (
        "QT_PLUGIN_PATH",
        "QT_QPA_PLATFORM_PLUGIN_PATH",
        "QML2_IMPORT_PATH",
        "QML_IMPORT_PATH",
        "PYTHONHOME",
        "QT_API",
    ):
        os.environ.pop(key, None)

    pyside = Path(sys.prefix) / "Lib" / "site-packages" / "PySide6"
    platforms = pyside / "plugins" / "platforms"
    if pyside.is_dir():
        os.environ["PATH"] = str(pyside) + os.pathsep + str(Path(sys.prefix) / "Scripts") + os.pathsep + os.environ.get("PATH", "")
        if hasattr(os, "add_dll_directory"):
            _DLL_HANDLES.append(os.add_dll_directory(str(pyside)))
    if platforms.is_dir():
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(platforms)
        if hasattr(os, "add_dll_directory"):
            _DLL_HANDLES.append(os.add_dll_directory(str(platforms)))
    os.environ["QT_QPA_PLATFORM"] = "windows"


def main() -> int:
    target_name = sys.argv[1] if len(sys.argv) > 1 else "goats_rt_manager_v5_4_15_10.py"
    target = (APP_DIR / target_name).resolve()
    if not target.is_file():
        print(f"ERRORE: file Manager non trovato: {target}")
        return 30
    prepare_qt_runtime()
    sys.path.insert(0, str(APP_DIR))
    sys.argv = [str(target)] + sys.argv[2:]
    runpy.run_path(str(target), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
