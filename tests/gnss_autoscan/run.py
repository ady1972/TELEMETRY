from pathlib import Path
import subprocess,tempfile
ROOT=Path(__file__).resolve().parents[2]
COMP=ROOT/'firmware/rlcd-42-3-colori/GOATS_GNSS_AUTOSCAN_V010/components/goats_gnss_scan'
with tempfile.TemporaryDirectory() as tmp:
 exe=Path(tmp)/'test_engine'
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-Wno-misleading-indentation',
                 '-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(COMP),
                 str(ROOT/'tests/gnss_autoscan/test_engine.cpp'),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
