from pathlib import Path
import subprocess, tempfile, sys
root=Path(__file__).resolve().parents[2]
rlcd=root/'firmware/rlcd-42/GOATS_RLCD_RC2'
guition=root/'firmware/guition-43/goats_guition_43_rc2'
assert (rlcd/'goats_recording_clock.h').read_bytes()==(guition/'goats_recording_clock.h').read_bytes()
assert (rlcd/'goats_recording_time_runtime.h').read_bytes()==(guition/'goats_recording_time_runtime.h').read_bytes()
for folder,base in [(rlcd,rlcd.parent/'GOATS_RLCD_RC1'),(guition,guition.parent/'goats_guition_43_rc1')]:
    for name in ['goats_laptimer.h','goats_session_control.h','goats_ubx_m9n_v11.h','goats_gnss_assist_v1023.h']:
        if folder==guition and name=='goats_laptimer.h':
            # Guition RC2 intentionally fixes the equal-timestamp delta filter;
            # GNSS headers and the complete RLCD timing engine stay immutable.
            continue
        if (base/name).exists():assert (base/name).read_bytes()==(folder/name).read_bytes(),name

def run(args):subprocess.run([str(a) for a in args],cwd=root,check=True)
with tempfile.TemporaryDirectory() as tmp:
    for file,include in [('test_clock.cpp',rlcd),('test_dates.cpp',rlcd),('test_queue.cpp',guition)]:
        exe=Path(tmp)/file.removesuffix('.cpp')
        run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-I',root/'tests/rc2/stubs','-I',root/'tests/guition_port/stubs','-I',include,root/'tests/rc2'/file,'-o',exe]);run([exe])
    exe=Path(tmp)/'test_rlcd_summary'
    run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-I',root/'tests/guition_port/stubs','-I',rlcd,root/'tests/rc2/test_rlcd_summary.cpp','-o',exe]);run([exe])
    for folder in (rlcd,guition):
        exe=Path(tmp)/'test_screen_mode'
        run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-I',root/'tests/rc2/screen_mode_stubs','-I',folder,root/'tests/rc2/test_screen_mode.cpp','-o',exe]);run([exe])
    exe=Path(tmp)/'test_guition_delta'
    run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Wno-unused-variable','-I',guition,'-I',rlcd,root/'tests/rc2/test_guition_delta.cpp','-o',exe]);run([exe])
    run([sys.executable,root/'tests/rc2/test_guition_summary_ui.py'])
    run([sys.executable,root/'tests/rc2/test_storage.py'])
    run([sys.executable,root/'tests/rc2/test_rlcd_restart.py'])
    run([sys.executable,root/'tests/guition_port/prepare_host.py',tmp,'goats_guition_43_rc2'])
    exe=Path(tmp)/'test_port'
    run(['g++','-std=c++17','-Wall','-Wextra','-Wno-misleading-indentation','-I',tmp,'-I',root/'tests/guition_port/stubs','-I',guition,root/'tests/guition_port/test_port.cpp','-o',exe]);run([exe])
print('PASS RC2: date/DST, immutable metadata/NVS recovery, midnight queue, real FAT finalizers and legacy GSA3/25 Hz integration')
