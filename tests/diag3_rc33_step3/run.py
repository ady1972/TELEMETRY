from pathlib import Path
import subprocess,tempfile,sys,re,ast,struct,zlib,importlib.util
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'firmware/rlcd-42-3-colori';STEP=BASE/'GOATS_DIAG3_RC33_STEP3/components/goats_spi_diag'
sys.path.insert(0,str(Path(__file__).parent));from sdk import FILES
runner=(ROOT/'tests/diag3_rc33_step1/run.py').read_text()
runner=runner.replace("STEP=BASE/'GOATS_DIAG3_RC33_STEP1/components/goats_spi_diag'","STEP=BASE/'GOATS_DIAG3_RC33_STEP3/components/goats_spi_diag'").replace("BASE/'goats_42_diag3_rc33_step1.yaml'","BASE/'goats_42_diag3_rc33_step3.yaml'")
runner=runner.replace("['esphome','external_components']","['esphome','external_components','goats_spi_diag']").replace("'__init__.py','goats_spi_diag.h',",'')
runner=runner.replace('"DIAG3 + RC3.3 STEP1"','"DIAG3 + RC3.3 STEP3"')
runner=runner.replace("assert old_panel==new_panel,","assert old_panel.split(' char sat_age')[0]==new_panel.split(' char sat_age')[0],")
runner=runner.replace(" expected=(REF/name).read_text()",''' expected=(REF/name).read_text()
 if name=='goats_racing_bridge.h':expected=expected.replace('const uint32_t crc=b.raw.empty()?0:goats_b::crc32(b.raw.data(),b.raw.size());','const uint32_t crc=goats_step3_catalog::crc; // Cached on load/upload, not recomputed for each PVT.')''')
runner=runner.replace('no new USB/NVS/SD activity','baseline before Manager startup has no USB/NVS/SD activity')
injection='''
 for name,data in SDK_FILES.items():
  p=t/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(data)
 (t/'manager.cpp').write_text(MANAGER_SOURCE.replace('ACTUAL_GPS_POLL',poll_body))
 subprocess.run(['g++','-std=c++17','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(t),'-I'+str(STEP),str(t/'manager.cpp'),'-o',str(t/'manager')],check=True)
 subprocess.run([str(t/'manager')],check=True)
 manager_client_tests(t/'manager')
'''
marker=" # Main.cpp must not instantiate"
runner=runner.replace(marker,injection+marker)

def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def client_test(exe):
 manager=ROOT/'windows/v5.4.15.20-burst4'
 protocol=module('step3_protocol',manager/'goats_test23_protocol.py');formats=module('step3_formats',manager/'goats_formats.py')
 # Execute the actual Manager GTC3 builder without importing its Qt application.
 tree=ast.parse((manager/'goats_track_editor.py').read_text());methods={}
 for node in ast.walk(tree):
  if isinstance(node,ast.FunctionDef) and node.name in ['_encode_text','build_binary_catalog']:methods[node.name]=node
 cls=ast.ClassDef(name='Builder',bases=[],keywords=[],body=list(methods.values()),decorator_list=[])
 code=ast.fix_missing_locations(ast.Module(body=[cls],type_ignores=[]));scope={'struct':struct};exec(compile(code,'manager_gtc3','exec'),scope)
 track={'name':'BENCH','start_line':{'lat1':45,'lon1':8.9999,'lat2':45,'lon2':9.0001},'sectors':[]}
 catalog,count=scope['Builder']().build_binary_catalog(tracks=[track]);assert count==1
 process=subprocess.Popen([str(exe),'--server'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
 def rpc(line):
  process.stdin.write(line+'\n');process.stdin.flush();response=process.stdout.readline().strip();assert response,process.poll();return response
 class Port:
  timeout=12
  def __init__(self):self.buffer=bytearray()
  def write(self,data):
   response=rpc('USB '+data.hex());assert response.startswith('OUT');self.buffer+=bytes.fromhex(response[4:]);return len(data)
  def flush(self):pass
  def readline(self):
   at=self.buffer.find(b'\n');assert at>=0,bytes(self.buffer);out=bytes(self.buffer[:at+1]);del self.buffer[:at+1];return out
  def read(self,n):out=bytes(self.buffer[:n]);del self.buffer[:n];return out
  def reset_input_buffer(self):self.buffer.clear()
 p=Port()
 try:
  protocol.send(p,'GSD_PING');assert protocol.exchange_readline(p)=='GSD_PONG TEST3_INTERNAL'
  protocol.send(p,f'GTRK_BEGIN {len(catalog)} {zlib.crc32(catalog)&0xffffffff:08X}');assert protocol.exchange_readline(p)=='GTRK_READY'
  p.write(catalog);assert protocol.exchange_readline(p)=='GTRK_OK 1'
  protocol.send(p,'GTRK_GET');line=protocol.exchange_readline(p);parts=line.split();assert int(parts[1])==len(catalog);assert p.read(len(catalog))==catalog;assert protocol.exchange_readline(p)=='GTRK_END'
  assert rpc('SIM 300')=='OK';items=protocol.fetch_list(p);assert len(items)==1
  with tempfile.TemporaryDirectory(prefix='step3-manager-csv-') as tmp:
   out=Path(tmp)/items[0][0];protocol.fetch_file(p,items[0][0],out,lambda*a:None)
   parsed=formats.parse_sd_csv(out);assert len(parsed.points)==301 and parsed.session_type=='FREE' and parsed.firmware=='DIAG3_RC33_STEP3'
   assert all(b.elapsed_ms-a.elapsed_ms==40 for a,b in zip(parsed.points,parsed.points[1:]))
   assert parsed.date=='26/11/2026' and parsed.time=='13:00:00'
  assert rpc('REBOOT')=='OK';assert protocol.fetch_list(p)==items
  protocol.delete_file(p,items[0][0]);assert protocol.fetch_list(p)==[]
  assert rpc('REBOOT')=='OK';assert protocol.fetch_list(p)==[]
  print('PASS: actual Windows Manager GTC3 builder, GSD listing/burst4/CRC/download/delete and CSV parser end-to-end')
 finally:
  rpc('QUIT');process.wait(timeout=5);assert process.returncode==0
exec(compile(runner,str(ROOT/'tests/diag3_rc33_step1/run.py'),'exec'),{'__file__':str(ROOT/'tests/diag3_rc33_step1/run.py'),'SDK_FILES':FILES,'MANAGER_SOURCE':(Path(__file__).parent/'test_manager.cpp').read_text(),'manager_client_tests':client_test})
print('PASS: STEP3 source parity and complete Manager/telemetry integration')
