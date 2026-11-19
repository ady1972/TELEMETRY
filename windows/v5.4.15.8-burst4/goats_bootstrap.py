from __future__ import annotations

import os
import subprocess
import sys
import venv
from datetime import datetime
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
REQ = APP_DIR / "requirements.txt"
MAIN = APP_DIR / "goats_rt_manager_v5_4_15_8.py"
RUNNER = APP_DIR / "goats_run_manager.py"
PROBE = APP_DIR / "goats_qt_probe.py"

# IMPORTANT: the Python/Qt virtual environment must not live inside the
# Manager folder when that folder is synchronized by Google Drive/OneDrive.
# Cloud clients can lock or partially synchronize DLL/__pycache__ files and
# corrupt a perfectly working Qt runtime between two launches.
LOCALAPPDATA = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
RUNTIME_ROOT = LOCALAPPDATA / "GOATS_RT_Manager"
PY_TAG = f"py{sys.version_info.major}{sys.version_info.minor}"
BASE_RUNTIME = RUNTIME_ROOT / f"runtime_{PY_TAG}"
ACTIVE_FILE = RUNTIME_ROOT / f"active_{PY_TAG}.txt"


def runtime_python(runtime_dir: Path) -> Path:
    return runtime_dir / "Scripts" / "python.exe"


def run(args, *, cwd: Path | None = None, quiet: bool = False):
    if not quiet:
        print(">", " ".join(str(x) for x in args))
    kwargs = {}
    if quiet:
        kwargs.update(stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return subprocess.run([str(x) for x in args], cwd=str(cwd or APP_DIR), **kwargs)


def deps_ok(runtime_dir: Path, *, quiet: bool = True) -> bool:
    py = runtime_python(runtime_dir)
    if not py.exists():
        return False
    return run(
        [py, "-c", "import PySide6,serial,requests"],
        cwd=APP_DIR,
        quiet=quiet,
    ).returncode == 0


def qt_ok(runtime_dir: Path, *, quiet: bool = True) -> bool:
    py = runtime_python(runtime_dir)
    if not py.exists():
        return False
    return run([py, PROBE], cwd=APP_DIR, quiet=quiet).returncode == 0


def runtime_ok(runtime_dir: Path, *, quiet: bool = True) -> bool:
    return deps_ok(runtime_dir, quiet=quiet) and qt_ok(runtime_dir, quiet=quiet)


def install_requirements(runtime_dir: Path) -> bool:
    py = runtime_python(runtime_dir)
    if run([py, "-m", "pip", "install", "--disable-pip-version-check", "--upgrade", "pip"]).returncode != 0:
        return False
    return run([py, "-m", "pip", "install", "--disable-pip-version-check", "-r", REQ]).returncode == 0


def create_runtime(runtime_dir: Path) -> bool:
    print(f"Creo runtime locale fuori dalla cartella sincronizzata:\n  {runtime_dir}")
    try:
        runtime_dir.parent.mkdir(parents=True, exist_ok=True)
        venv.EnvBuilder(with_pip=True, clear=False).create(runtime_dir)
    except Exception as exc:
        print("ERRORE creazione runtime:", exc)
        return False
    if not install_requirements(runtime_dir):
        return False
    if not runtime_ok(runtime_dir, quiet=False):
        print("ERRORE: il nuovo runtime non supera il test Qt Windows.")
        return False
    return True


def read_active_runtime() -> Path | None:
    try:
        if ACTIVE_FILE.is_file():
            raw = ACTIVE_FILE.read_text(encoding="utf-8").strip()
            if raw:
                return Path(raw)
    except Exception:
        pass
    return None


def write_active_runtime(runtime_dir: Path) -> None:
    try:
        RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
        ACTIVE_FILE.write_text(str(runtime_dir), encoding="utf-8")
    except Exception:
        # Not fatal: the runtime still works, only startup selection is slower.
        pass


def existing_candidates() -> list[Path]:
    out: list[Path] = []
    active = read_active_runtime()
    if active is not None:
        out.append(active)
    out.append(BASE_RUNTIME)
    if RUNTIME_ROOT.is_dir():
        # Newest recovery runtime first.
        recoveries = sorted(
            RUNTIME_ROOT.glob(f"runtime_{PY_TAG}_recovery_*"),
            key=lambda p: p.name,
            reverse=True,
        )
        out.extend(recoveries)
    # de-duplicate without resolving paths that may not exist.
    uniq: list[Path] = []
    seen: set[str] = set()
    for p in out:
        k = os.path.normcase(str(p))
        if k not in seen:
            seen.add(k)
            uniq.append(p)
    return uniq


def choose_runtime() -> Path | None:
    print("Runtime Qt per-utente:", RUNTIME_ROOT)
    print("La .goats_venv dentro la cartella del Manager viene ignorata intenzionalmente.")

    for candidate in existing_candidates():
        if runtime_python(candidate).exists():
            print("Verifico runtime:", candidate)
            if runtime_ok(candidate):
                print("Runtime Qt Windows OK.")
                write_active_runtime(candidate)
                return candidate
            print("Runtime non valido: lo lascio intatto e provo un'alternativa.")

    # Never delete/repair an environment in place. A locked DLL or cache may
    # prevent deletion. Create a clean sibling instead.
    if not BASE_RUNTIME.exists():
        target = BASE_RUNTIME
    else:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = RUNTIME_ROOT / f"runtime_{PY_TAG}_recovery_{stamp}"
        n = 1
        while target.exists():
            target = RUNTIME_ROOT / f"runtime_{PY_TAG}_recovery_{stamp}_{n}"
            n += 1

    if create_runtime(target):
        write_active_runtime(target)
        return target
    return None



def diagnostic_main() -> int:
    print()
    print("GOATS RT MANAGER V5.4.15.8 - DIAGNOSTICA RUNTIME")
    print("----------------------------------------------")
    print("Python di controllo:", sys.version.split()[0])
    print("Eseguibile:", sys.executable)
    print("Cartella Manager:", APP_DIR)
    print("Runtime per-utente:", RUNTIME_ROOT)
    print(".goats_venv nella cartella Manager: IGNORATA (per evitare lock Google Drive/OneDrive)")
    print()

    found = False
    for candidate in existing_candidates():
        py = runtime_python(candidate)
        if not py.exists():
            continue
        found = True
        print("RUNTIME:", candidate)
        run([py, "-c", "import sys; print('  Python',sys.version); print('  Eseguibile:',sys.executable)"])
        dep = deps_ok(candidate, quiet=False)
        print("  Dipendenze:", "OK" if dep else "ERRORE")
        qt = qt_ok(candidate, quiet=False) if dep else False
        print("  Qt Windows:", "OK" if qt else "ERRORE")
        if dep:
            mods = run([py, "-c", "import goats_formats,goats_store,goats_exporters; print('  Moduli GOATS OK')"], cwd=APP_DIR).returncode == 0
            print("  Moduli GOATS:", "OK" if mods else "ERRORE")
        print()
        if dep and qt:
            print("DIAGNOSTICA OK: esiste almeno un runtime Qt funzionante.")
            return 0

    if not found:
        print("Nessun runtime per-utente ancora creato.")
    print("DIAGNOSTICA: nessun runtime Qt funzionante. Avvia il Manager per crearne uno pulito.")
    return 21


def main() -> int:
    print()
    print("GOATS RT MANAGER V5.4.15.8 - AVVIO")
    print("--------------------------------")
    print("Python bootstrap:", sys.version.split()[0])
    print("Eseguibile:", sys.executable)
    print("Cartella Manager:", APP_DIR)

    if not ((3, 10) <= sys.version_info[:2] < (3, 15)):
        print("ERRORE: serve Python da 3.10 a 3.14.")
        return 10

    runtime = choose_runtime()
    if runtime is None:
        print()
        print("ERRORE: non sono riuscito a creare un runtime Qt funzionante in LOCALAPPDATA.")
        print("Esegui DIAGNOSTICA_GOATS_RT_MANAGER.bat per il dettaglio.")
        return 21

    py = runtime_python(runtime)
    print()
    print("Avvio Manager con runtime:")
    print(" ", runtime)
    return run([py, RUNNER, MAIN], cwd=APP_DIR).returncode


if __name__ == "__main__":
    try:
        if "--diagnose" in sys.argv[1:]:
            raise SystemExit(diagnostic_main())
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
