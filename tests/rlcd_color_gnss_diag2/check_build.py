"""Check the actual compiled transport isolation, USB ownership and flash map."""
from pathlib import Path
import subprocess,json,shlex,tempfile,struct,os
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'firmware/rlcd-42-3-colori'
NOSD=os.environ.get('COLOR_GNSS_NOSD')=='1'
PORT=BASE/('GOATS_RLCD_COLOR_RC3_3_GNSS2_NOSD' if NOSD else 'GOATS_RLCD_COLOR_RC3_3_GNSS_DIAG2')
BUILD=BASE/('.esphome/build/goats-rc33-gnss2-nosd/build' if NOSD else '.esphome/build/goats-42-color-rc3-3-gnss2/build')
commands=json.loads((BUILD/'compile_commands.json').read_text())
def entry(suffix):return next(c for c in commands if c['file'].endswith(suffix))
main=entry('/src/main.cpp');gnss=entry('/goats_gnss_color/goats_gnss_color.cpp')
arduino=entry('/cores/esp32/USBMSC.cpp')
assert '-DUSE_ARDUINO' in main['command']
assert '-DUSE_ESP_IDF ' not in main['command']
if NOSD:
 for c in commands:assert 'GOATS_ARDUINO_CORE_USB_COMPAT' not in c['command']
 config=(BUILD/'config/sdkconfig.h').read_text()
 assert '#define CONFIG_TINYUSB_MSC_ENABLED' not in config
else:
 msc=next(c for c in commands if 'espressif__esp_tinyusb' in c['file'] and 'msc' in Path(c['file']).name)
 assert 'arduino_usb_owner.h' in arduino['command'] and 'GOATS_ARDUINO_CORE_USB_COMPAT=1' in arduino['command']
 for c in [main,gnss,msc]:assert 'arduino_usb_owner.h' not in c['command'] and 'GOATS_ARDUINO_CORE_USB_COMPAT' not in c['command']
def preprocess(c,path):
 args=shlex.split(c['command']);clean=[];i=0
 while i<len(args):
  if args[i] in ['-o','-MF','-MT','-MQ']:i+=2;continue
  if args[i] in ['-c','-MD','-MMD','-MP']:i+=1;continue
  clean.append(args[i]);i+=1
 subprocess.run(clean+['-E','-P','-o',str(path)],cwd=c['directory'],capture_output=True,text=True,check=True)
 return path.read_text()
with tempfile.TemporaryDirectory(prefix='rc33-build-scope-') as tmp:
 t=Path(tmp)
 app=preprocess(main,t/'main.ii');owner=preprocess(gnss,t/'gnss.ii')
 assert 'namespace goats_m9n {' not in app and 'namespace goats_cfg {' not in app
 assert 'frame_observer' not in app
 assert 'namespace goats_m9n {' in owner and 'namespace goats_cfg {' in owner
 assert 'goats_hal_millis' not in owner and 'goats_hal_delay' not in owner
 assert 'u.load_settings()' in owner
 assert 'goats_hal_millis' in app
 print('PASS: real preprocessor isolates Arduino GNSS parser/config from generated main and RC3.3 clock macros')
def table(blob):
 rows=[]
 for at in range(0,len(blob),32):
  magic,typ,sub,offset,size,label,flags=struct.unpack_from('<HBBII16sI',blob,at)
  if magic!=0x50aa:break
  rows.append((label.rstrip(b'\0'),typ,sub,offset,size,flags))
 return rows
factory=(BASE/'GOATS_RLCD_COLOR_RC3_3/download/GOATS_RLCD_COLOR_RC3.3_GNSS_V0405.factory.bin').read_bytes()
assert table((BUILD/'partition_table/partition-table.bin').read_bytes())==table(factory[0x8000:0x9000])
compiler=Path(shlex.split(arduino['command'])[0]);nm=compiler.with_name(compiler.name.removesuffix('g++')+'nm')
args=shlex.split(arduino['command']);obj=Path(arduino['directory'])/args[args.index('-o')+1]
symbols=subprocess.check_output([str(nm),'--defined-only',str(obj)],text=True)
assert 'tud_msc_' not in symbols and 'tusb_msc_load_descriptor' not in symbols
if NOSD:
 elf=next(BUILD.glob('*.elf'))
 linked=subprocess.check_output([str(nm),'--defined-only',str(elf)],text=True)
 for forbidden in ['esp_vfs_fat_sdmmc_mount','sdmmc_card_init','tinyusb_driver_install','tinyusb_msc_new_storage','tud_msc_',' f_mount']:
  assert forbidden not in linked,forbidden
 print('PASS: linked NOSD firmware has no SD mount, SD card init, FatFS mount or TinyUSB MSC functions; RC3.3 NVS/partitions preserved')
else:
 print('PASS: actual USB override belongs only to Arduino core, no duplicate Arduino MSC callbacks, RC3.3 partition offsets preserved')
