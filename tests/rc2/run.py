from pathlib import Path
import subprocess, tempfile, sys
root=Path(__file__).resolve().parents[2]
rlcd=root/'firmware/rlcd-42/GOATS_RLCD_RC2'
guition=root/'firmware/guition-43/goats_guition_43_rc2'
assert (rlcd/'goats_recording_clock.h').read_bytes()==(guition/'goats_recording_clock.h').read_bytes()
assert (rlcd/'goats_recording_time_runtime.h').read_bytes()==(guition/'goats_recording_time_runtime.h').read_bytes()
for folder,base in [(rlcd,rlcd.parent/'GOATS_RLCD_RC1'),(guition,guition.parent/'goats_guition_43_rc1')]:
    for name in ['goats_laptimer.h','goats_session_control.h','goats_ubx_m9n_v11.h','goats_gnss_assist_v1023.h']:
        if (base/name).exists():assert (base/name).read_bytes()==(folder/name).read_bytes(),name

def run(args):subprocess.run([str(a) for a in args],cwd=root,check=True)
with tempfile.TemporaryDirectory() as tmp:
    for file,include in [('test_clock.cpp',rlcd),('test_dates.cpp',rlcd),('test_queue.cpp',guition)]:
        exe=Path(tmp)/file.removesuffix('.cpp')
        run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-I',root/'tests/rc2/stubs','-I',root/'tests/guition_port/stubs','-I',include,root/'tests/rc2'/file,'-o',exe]);run([exe])
    run([sys.executable,root/'tests/rc2/test_storage.py'])
    run([sys.executable,root/'tests/guition_port/prepare_host.py',tmp,'goats_guition_43_rc2'])
    exe=Path(tmp)/'test_port'
    run(['g++','-std=c++17','-Wall','-Wextra','-Wno-misleading-indentation','-I',tmp,'-I',root/'tests/guition_port/stubs','-I',guition,root/'tests/guition_port/test_port.cpp','-o',exe]);run([exe])
print('PASS RC2: date/DST, immutable metadata/NVS recovery, midnight queue, real FAT finalizers and legacy GSA3/25 Hz integration')
