from __future__ import annotations

import os
import sys
from pathlib import Path

# Keep the handles alive for the whole probe. On Windows, dropping the handle
# returned by os.add_dll_directory() immediately removes the directory again.
_DLL_HANDLES = []


def prepare_qt_runtime() -> None:
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

    if not pyside.is_dir():
        raise RuntimeError(f"Cartella PySide6 non trovata: {pyside}")
    if not platforms.is_dir():
        raise RuntimeError(f"Plugin platforms non trovato: {platforms}")

    os.environ["QT_QPA_PLATFORM"] = "windows"
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = str(platforms)
    os.environ["PATH"] = str(pyside) + os.pathsep + str(Path(sys.prefix) / "Scripts") + os.pathsep + os.environ.get("PATH", "")

    if hasattr(os, "add_dll_directory"):
        # IMPORTANT: retain returned handles until QApplication has finished.
        _DLL_HANDLES.append(os.add_dll_directory(str(pyside)))
        _DLL_HANDLES.append(os.add_dll_directory(str(platforms)))


def main() -> int:
    try:
        prepare_qt_runtime()
        import PySide6
        from PySide6.QtWidgets import QApplication
        app = QApplication([])
        print("PySide6", PySide6.__version__)
        print("Qt platform OK:", app.platformName())
        app.quit()
        return 0
    except Exception as exc:
        print("QT PROBE ERROR:", repr(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
