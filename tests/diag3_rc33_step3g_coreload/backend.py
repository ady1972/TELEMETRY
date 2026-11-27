from pathlib import Path
import ast,subprocess,tempfile,sys,struct,zlib,importlib.util
ROOT=Path(__file__).resolve().parents[2]
STEP=ROOT/'firmware/rlcd-42-3-colori/GOATS_DIAG3_RC33_STEP3G_CORELOAD/components/goats_spi_diag'
# Shared IDF/ESPHome doubles; actual parser/core/store/USB/runtime stay production code.
tree=ast.parse((ROOT/'tests/diag3_rc33_step1/run.py').read_text())
files=next(ast.literal_eval(n.value) for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='files' for t in n.targets))
spec=importlib.util.spec_from_file_location('step3g_sdk',ROOT/'tests/diag3_rc33_step3/sdk.py');sdk=importlib.util.module_from_spec(spec);spec.loader.exec_module(sdk);files.update(sdk.FILES)
files['Arduino.h']+='\ninline uint32_t micros(){return clock_ms*1000u;}\n'
cpp=(STEP/'goats_spi_diag.cpp').read_text();poll=cpp[cpp.index('void GoatsSpiDiag::gps_poll_()'):cpp.index('void GoatsSpiDiag::menu_draw_()')]
# Run the established real Windows Manager protocol/CSV client against FULL too.
manager_tree=ast.parse((ROOT/'tests/diag3_rc33_step3/run.py').read_text())
functions=[n for n in manager_tree.body if isinstance(n,ast.FunctionDef) and n.name in ['module','client_test']]
exec(compile(ast.fix_missing_locations(ast.Module(body=functions,type_ignores=[])),'step3g_manager_client','exec'),globals())
with tempfile.TemporaryDirectory(prefix='step3g-backend-') as tmp:
 t=Path(tmp)
 for name,data in files.items():
  p=t/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(data)
 for name,source in [('backend',ROOT/'tests/diag3_rc33_step3g_coreload/test_backend.cpp'),('manager',ROOT/'tests/diag3_rc33_step3/test_manager.cpp')]:
  p=t/(name+'.cpp');p.write_text(source.read_text().replace('ACTUAL_GPS_POLL',poll));exe=t/name
  subprocess.run(['g++','-std=c++17','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(t),'-I'+str(STEP),str(p),'-o',str(exe)],check=True)
  if name=='backend':
   for mode in range(5):subprocess.run([str(exe),str(mode)],check=True)
  else:
   subprocess.run([str(exe)],check=True);client_test(exe)
print('PASS: real split backend plus unchanged FULL catalog/CSV/Manager integration')
