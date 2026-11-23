from pathlib import Path
import os, subprocess, sys

base = Path(__file__).resolve().parent
venv_py = base / ".goats_venv" / "Scripts" / "python.exe"

print("GOATS RT MANAGER V5.4.15.11 - DIAGNOSTICA")
print("Bootstrap Python:", sys.version)
print("Bootstrap exe:", sys.executable)
print("Cartella:", base)
print("Venv presente:", venv_py.exists())

if venv_py.exists():
    r = subprocess.run(
        [str(venv_py), "-c",
         "import sys; print('Venv Python:',sys.version); "
         "import PySide6; print('PySide6:',PySide6.__version__); "
         "import serial; print('pyserial:',serial.VERSION); "
         "import requests; print('requests:',requests.__version__)"],
        cwd=str(base),
    )
    print("Esito dipendenze:", r.returncode)
