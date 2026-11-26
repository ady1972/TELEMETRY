"""Verify the real V0.40.5 configurator port and its real RC3.3 boot integration."""
from pathlib import Path
import re
import json
import hashlib
import subprocess
import tempfile
import yaml
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'firmware/rlcd-42-3-colori'
ORIGINAL=BASE/'GOATS_V0405_BOOT_FAST_FONT_TEST/components/goats_spi_diag/goats_m9n_cfg.h'
PASSIVE=ROOT/'firmware/rlcd-42/GOATS_RLCD_RC3_3'
PORT=BASE/'GOATS_RLCD_COLOR_RC3_3'
original=ORIGINAL.read_text()
ported=(PORT/'goats_m9n_cfg.h').read_text()
assert ported==original.replace('#include <Arduino.h>','#include "esphome/core/hal.h"').replace('delay(','esphome::delay(')
for source in PASSIVE.glob('*.h'):
 assert source.read_bytes()==(PORT/source.name).read_bytes(),source.name
manifest=json.loads((ROOT/'tests/rlcd_color_gnss_config/reference_manifest.json').read_text())
for name,digest in manifest['files'].items():
 assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
current=(BASE/'goats_42_color_rc3_3.yaml').read_text()
def section(text,name):return re.search(r'^'+name+r':\n.*?(?=^[a-z_]+:|\Z)',text,re.M|re.S)[0]
for name,digest in manifest['sections'].items():
 assert hashlib.sha256(section(current,name).encode()).hexdigest()==digest,name
assert not re.search(r'^(wifi|ota|api|web_server|psram|image):',current,re.M)
for text in ['rx_pin: GPIO1','tx_pin: GPIO2','baud_rate: 38400','rx_buffer_size: 16384']:
 assert text in section(current,'uart')
assert 'splash_started' not in current and 'goats_splash_static' not in current
assert not (PORT/'splash_assets').exists()
class Loader(yaml.SafeLoader):pass
Loader.add_multi_constructor('!',lambda loader,tag,node:loader.construct_scalar(node))
config=yaml.load(current,Loader=Loader)
boot=config['esphome']['on_boot'];assert boot['priority']==-100
bootcode=boot['then'][0]['lambda'];assert bootcode.count('goats_cfg::configure')==1
with tempfile.TemporaryDirectory() as tmp:
 t=Path(tmp)
 files={
 'esphome/core/hal.h':'''#pragma once
#include <cstdint>
inline uint32_t test_ms=0;
namespace esphome {inline void delay(uint32_t ms){test_ms+=ms;}}
''',
 'Arduino.h':'#pragma once\n#include "esphome/core/hal.h"\nusing esphome::delay;\n',
 'esphome/components/uart/uart.h':'''#pragma once
#include <vector>
#include <cstddef>
#include <cstdint>
#include "esphome/core/hal.h"
namespace esphome::uart {
struct Frame {uint32_t baud,ms;std::vector<uint8_t>bytes;
bool operator==(const Frame&other)const{return baud==other.baud&&ms==other.ms&&bytes==other.bytes;}};
class UARTComponent {public:
uint32_t baud=38400;unsigned flushes=0;std::vector<uint32_t> bauds;std::vector<Frame>frames;
void set_baud_rate(uint32_t v){baud=v;}void load_settings(){bauds.push_back(baud);}
void write_array(const uint8_t*d,size_t n){frames.push_back({baud,test_ms,{d,d+n}});}
void flush(){flushes++;}
};}
'''}
 for name,data in files.items():
  p=t/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(data)
 source=(ROOT/'tests/rlcd_color_gnss_config/test_config.cpp').read_text().replace('ACTUAL_BOOT_LAMBDA',bootcode)
 cpp=t/'test.cpp';cpp.write_text(source);exe=t/'test_config'
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-Wno-misleading-indentation',
  '-fsanitize=address,undefined','-fno-omit-frame-pointer','-DORIGINAL_CFG_HEADER="'+str(ORIGINAL)+'"',
  '-I'+str(t),'-I'+str(PORT),str(cpp),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
print('PASS: V0.40.5 exact UART frames/timing; all four boot baud scenarios; UBX checksums,')
print('RAM-only layer, rates/constellations/messages, repeated normal boot, no GNSS writes in USB MSC')
print('PASS: RC3.3 core/parser/layout/driver/fonts/scheduling preserved; RX1/TX2, no splash, no network/OTA')
