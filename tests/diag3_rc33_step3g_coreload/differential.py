from pathlib import Path
import ast,subprocess,tempfile,importlib.util,hashlib
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'firmware/rlcd-42-3-colori'
OLD=BASE/'GOATS_DIAG3_RC33_STEP3F_BACKEND/components/goats_spi_diag';NEW=BASE/'GOATS_DIAG3_RC33_STEP3G_CORELOAD/components/goats_spi_diag'
tree=ast.parse((ROOT/'tests/diag3_rc33_step1/run.py').read_text())
files=next(ast.literal_eval(n.value) for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='files' for t in n.targets))
spec=importlib.util.spec_from_file_location('coreload_sdk',ROOT/'tests/diag3_rc33_step3/sdk.py');sdk=importlib.util.module_from_spec(spec);spec.loader.exec_module(sdk);files.update(sdk.FILES)
files['Arduino.h']+='\ninline uint32_t micros(){return clock_ms*1000u;}\n'
source=(ROOT/'tests/diag3_rc33_step3g_coreload/test_differential.cpp').read_text()
with tempfile.TemporaryDirectory(prefix='coreload-differential-') as tmp:
 t=Path(tmp)
 for name,data in files.items():
  p=t/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(data)
 exes={}
 for label,step in [('reference',OLD),('cache',NEW)]:
  cpp=(step/'goats_spi_diag.cpp').read_text();poll=cpp[cpp.index('void GoatsSpiDiag::gps_poll_()'):cpp.index('void GoatsSpiDiag::menu_draw_()')]
  p=t/(label+'.cpp');p.write_text(source.replace('ACTUAL_GPS_POLL',poll));exe=t/label
  subprocess.run(['g++','-std=c++17','-O1','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer',*(['-DNEW_CACHE'] if label=='cache' else []),'-I'+str(t),'-I'+str(step),str(p),'-o',str(exe)],check=True);exes[label]=exe
 for scenario in range(3):
  ref=subprocess.run([str(exes['reference']),str(scenario),'0'],capture_output=True,check=True)
  off=subprocess.run([str(exes['cache']),str(scenario),'0'],capture_output=True,check=True)
  on=subprocess.run([str(exes['cache']),str(scenario),'1'],capture_output=True,check=True)
  assert ref.stdout==off.stdout==on.stdout,(scenario,ref.stdout[:200],on.stdout[:200])
  _,calls_off,eval_off=off.stderr.decode().strip().split();_,calls_on,eval_on=on.stderr.decode().strip().split()
  assert calls_off==calls_on and eval_off==calls_off and int(eval_on)<int(eval_off)
  print(f'PASS: scenario {scenario}, old/cache-off/cache-on byte-identical state+CSV {hashlib.sha256(ref.stdout).hexdigest()[:16]}, cos {eval_off} -> {eval_on} / {calls_on} calls')
print('PASS: original STEP3F vs exact cache on/off: stationary AUTO, multiple laps/sectors/live deltas, no-fix/duplicates, catalog edits/reorder/clear/reload')
