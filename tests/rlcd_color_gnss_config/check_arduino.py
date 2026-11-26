"""Guard the Arduino compatibility runtime, RC3.3 layouts/storage and USB owner.
Run using the ESPHome Python environment. Pass --build after compilation.
"""
from pathlib import Path
import csv
import json
import shlex
import struct
import subprocess
import sys
import tempfile
import yaml
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'firmware/rlcd-42-3-colori'
PORT=BASE/'GOATS_RLCD_COLOR_RC3_3'
class Loader(yaml.SafeLoader):pass
Loader.add_multi_constructor('!',lambda loader,tag,node:loader.construct_scalar(node))
def config(name):
    p=subprocess.run([sys.executable,'-m','esphome','config',str(BASE/name)],capture_output=True,text=True)
    assert p.returncode==0,p.stderr
    return yaml.load(p.stdout,Loader=Loader)
base=config('goats_42_color_rc3_3_uart0.yaml')
racing=config('goats_42_color_rc3_3_arduino.yaml')
diag=config('goats_42_color_rc3_3_arduino_diag.yaml')
original=config('GOATS_V0405_BOOT_FAST_FONT_TEST/v0405_boot_fast_font_test.yaml')
assert racing['esp32']['framework']['type']==original['esp32']['framework']['type']=='arduino'
assert racing['logger']['baud_rate']==original['logger']['baud_rate']==0
for key in base:
    if key not in ('esphome','esp32','external_components'):
        assert racing[key]==base[key],key
for key in base['esphome']:
    if key not in ('friendly_name','comment'):
        assert racing['esphome'][key]==base['esphome'][key],key
for key in base['esp32']:
    if key not in ('framework','partitions'):
        assert racing['esp32'][key]==base['esp32'][key],key
for key in ('components','sdkconfig_options'):
    assert racing['esp32']['framework'][key]==base['esp32']['framework'][key],key
assert len(racing['external_components'])==len(base['external_components'])+1
assert racing['goats_arduino_usb_compat']=={}
for key in racing:
    if key not in ('esphome','display'):
        assert diag[key]==racing[key],key
for key in racing['esphome']:
    if key not in ('friendly_name','comment'):
        assert diag['esphome'][key]==racing['esphome'][key],key
assert len(diag['display'])==1
for key in racing['display'][0]:
    if key!='lambda':assert diag['display'][0][key]==racing['display'][0][key],key
assert 'RC3.3 - GPS ARDUINO' in diag['display'][0]['lambda']
# Compare storage semantics to the real previously delivered factory table.
def binary_table(blob):
    result=[]
    for at in range(0,len(blob),32):
        magic,typ,sub,offset,size,label,flags=struct.unpack_from('<HBBII16sI',blob,at)
        if magic!=0x50AA:break
        result.append((label.rstrip(b'\0').decode(),typ,sub,offset,size,flags))
    return result
factory=(PORT/'download/GOATS_RLCD_COLOR_RC3.3_GNSS_V0405.factory.bin').read_bytes()
reference=binary_table(factory[0x8000:0x9000])
rows=[]
for row in csv.reader((PORT/'partitions_rc33.csv').read_text().splitlines()):
    if not row or row[0].startswith('#'):continue
    name,typ,sub,offset,size,flags=[v.strip() for v in row]
    rows.append((name,{'app':0,'data':1}[typ],{'ota':0,'phy':1,'nvs':2,'ota_0':16,'ota_1':17}[sub],int(offset,0),int(size,0),int(flags or '0',0)))
assert rows==reference
assert max(r[3]+r[4] for r in rows)==16*1024*1024
for left,right in zip(rows,rows[1:]):assert left[3]+left[4]<=right[3]
if '--build' in sys.argv:
    build=BASE/'.esphome/build/goats-42-color-rc3-3/build'
    commands=json.loads((build/'compile_commands.json').read_text())
    arduino=next(c for c in commands if c['file'].endswith('/cores/esp32/USBMSC.cpp'))
    app=next(c for c in commands if c['file'].endswith('/src/main.cpp'))
    msc=next(c for c in commands if 'espressif__esp_tinyusb' in c['file'] and 'msc' in Path(c['file']).name)
    assert 'arduino_usb_owner.h' in arduino['command']
    assert '-DGOATS_ARDUINO_CORE_USB_COMPAT=1' in arduino['command']
    assert 'GOATS_ARDUINO_CORE_USB_COMPAT' not in app['command']
    assert 'GOATS_ARDUINO_CORE_USB_COMPAT' not in msc['command']
    assert 'arduino_usb_owner.h' not in app['command']
    assert 'arduino_usb_owner.h' not in msc['command']
    assert '-DUSE_ARDUINO' in app['command'] and '-DUSE_ESP_IDF ' not in app['command']
    # The component header is also collected into esphome.h. Its private guard
    # must keep the application SDK flag enabled despite that ordinary include.
    with tempfile.TemporaryDirectory() as tmp:
        cpp=Path(tmp)/'usb_scope.cpp'
        cpp.write_text("""#include "sdkconfig.h"
#include "arduino_usb_owner.h"
#ifdef GOATS_ARDUINO_CORE_USB_COMPAT
#ifdef CONFIG_TINYUSB_MSC_ENABLED
#error Arduino wrapper must be excluded
#endif
#else
static_assert(CONFIG_TINYUSB_MSC_ENABLED == 1, "Application MSC flag must stay enabled");
#endif
int main(){}
""")
        for flags in [[],['-DGOATS_ARDUINO_CORE_USB_COMPAT=1']]:
            subprocess.run(['g++','-std=c++17','-I'+str(build/'config'),
                            '-I'+str(PORT/'components/goats_arduino_usb_compat'),
                            *flags,str(cpp),'-o',str(Path(tmp)/'usb_scope')],check=True)
    actual=(build/'partition_table/partition-table.bin').read_bytes()
    assert binary_table(actual)==reference
    # The Arduino MSC object must contain none of the TinyUSB callbacks.
    compiler=Path(shlex.split(arduino['command'])[0])
    nm=compiler.with_name(compiler.name.removesuffix('g++')+'nm')
    obj=Path(arduino['directory'])/arduino['output'] if 'output' in arduino else None
    if obj is None:
        argv=shlex.split(arduino['command']);obj=Path(arduino['directory'])/argv[argv.index('-o')+1]
    result=subprocess.check_output([str(nm),'--defined-only',str(obj)],text=True)
    assert 'tud_msc_' not in result and 'tusb_msc_load_descriptor' not in result
    print('PASS: real compile flags scope USB override only to Arduino; no Arduino MSC callbacks; compiled partition table matches RC3.3')
print('PASS: Arduino/logger match proven COLOR; Racing/core/GNSS/timers/SD/USB configurations preserved')
print('PASS: RC3.3 flash offsets and NVS region preserved against the delivered factory image')
