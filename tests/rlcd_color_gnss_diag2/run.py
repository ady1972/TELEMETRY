"""DIAG2 Arduino GNSS owner + unchanged RC3.3 core/rendering contracts."""
from pathlib import Path
import subprocess, tempfile, sys, os, re, yaml
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'firmware/rlcd-42-3-colori'
PORT=BASE/'GOATS_RLCD_COLOR_RC3_3_GNSS_DIAG2'
COMP=PORT/'components/goats_gnss_color'
REF=BASE/'GOATS_V0405_BOOT_FAST_FONT_TEST/components/goats_spi_diag'
RC33=ROOT/'firmware/rlcd-42/GOATS_RLCD_RC3_3'
OLD=BASE/'GOATS_RLCD_COLOR_RC3_3'
class Loader(yaml.SafeLoader):pass
Loader.add_multi_constructor('!',lambda loader,tag,node:loader.construct_scalar(node))
new=yaml.load((BASE/'goats_42_color_rc3_3_gnss_diag2.yaml').read_text(),Loader=Loader)
old=yaml.load((BASE/'goats_42_color_rc3_3.yaml').read_text(),Loader=Loader)
original=yaml.load((BASE/'GOATS_V0405_BOOT_FAST_FONT_TEST/v0405_boot_fast_font_test.yaml').read_text(),Loader=Loader)
for p in RC33.glob('*.h'):assert p.read_bytes()==(PORT/p.name).read_bytes(),p.name
for key in ['display','font','sensor','interval','binary_sensor','spi']:
 a=str(new[key]).replace('GOATS_RLCD_COLOR_RC3_3_GNSS_DIAG2/','GOATS_RLCD_COLOR_RC3_3/')
 assert a==str(old[key]),key
assert new['uart']==original['uart']
assert new['logger']==original['logger']
assert new['esp32']['framework']['type']=='arduino'
assert (PORT/'partitions_rc33.csv').read_bytes()==(OLD/'partitions_rc33.csv').read_bytes()
for component in ['goats_st7306','goats_arduino_usb_compat']:
 for p in (OLD/'components'/component).glob('*'):
  if p.is_file():assert p.read_bytes()==(PORT/'components'/component/p.name).read_bytes()
assert not set(new)&{'wifi','ota','api','web_server','psram'}
assert 'goats_cfg::configure' not in str(new['esphome'])
assert 'goats_diag::begin(id(gnss_color))' in str(new['esphome'])
# These files are private so esphome.h cannot instantiate a second parser in main.
def unwrap(path):
 s=path.read_text();pre='#pragma once\n#ifdef GOATS_GNSS_COLOR_IMPLEMENTATION\n';post='\n#endif // GOATS_GNSS_COLOR_IMPLEMENTATION\n'
 assert s.startswith(pre) and s.endswith(post)
 return s[len(pre):-len(post)]
assert unwrap(COMP/'goats_m9n_cfg.h')==(REF/'goats_m9n_cfg.h').read_text()
expected=(REF/'goats_ubx_m9n_ak97_full.h').read_text()
expected=expected.replace('#pragma once','#pragma once\n#include "goats_gps_diag.h"',1)
expected=expected.replace('struct Parser {','''// Passive hook: expose the validated original payload to the RC3.3 engine.
using FrameObserver=void (*)(uint8_t,uint8_t,const std::vector<uint8_t>&);
inline FrameObserver frame_observer{nullptr};
struct Parser {''',1)
expected=expected.replace('  void dispatch(){','  void dispatch(){\n    goats_gps_diag::counters.frame(cls,id,p.data(),p.size(),millis());\n    if(frame_observer)frame_observer(cls,id,p);',1)
expected=expected.replace('if(len>1024)reset();','if(len>1024){++goats_gps_diag::counters.oversize;reset();}',1)
expected=expected.replace('if(rxa==cka&&c==ckb)dispatch();reset();','if(rxa==cka&&c==ckb)dispatch();else ++goats_gps_diag::counters.checksum_errors;reset();',1)
expected=expected.replace('    parser.feed(c);','    goats_gps_diag::counters.byte(c,millis());\n    parser.feed(c);',1)
assert unwrap(COMP/'goats_ubx_m9n_ak97_full.h')==expected
with tempfile.TemporaryDirectory(prefix='rc33-gnss2-') as tmp:
 t=Path(tmp)
 files={
 'esphome/core/component.h':'''#pragma once
namespace esphome {class Component {public:virtual ~Component()=default;virtual void setup(){}};}
''',
 'esphome/core/hal.h':'''#pragma once
#include <cstdint>
inline uint32_t arduino_ms=1000;
namespace esphome {
inline uint32_t millis(){return arduino_ms-500;}
inline void delay(uint32_t ms){arduino_ms+=ms;}
}
''',
 'Arduino.h':'''#pragma once
#define ARDUINO_STUB_INCLUDED 1
#include <cstdio>
#include <vector>
#include "esphome/core/hal.h"
inline std::vector<uint32_t> delays;
inline uint32_t millis(){return arduino_ms;}
inline void delay(uint32_t ms){delays.push_back(ms);arduino_ms+=ms;}
''',
 'esphome/components/uart/uart.h':'''#pragma once
#include <cstdint>
#include <cstddef>
#include <vector>
#include <deque>
namespace esphome::uart {
class UARTComponent {public:
 std::deque<uint8_t> rx;std::vector<std::vector<uint8_t>> writes;
 std::vector<uint32_t> bauds;uint32_t baud=38400,reads=0;
 unsigned available(){return rx.size();}
 bool read_byte(uint8_t*p){if(rx.empty())return false;*p=rx.front();rx.pop_front();++reads;return true;}
 void write_array(const uint8_t*p,size_t n){writes.emplace_back(p,p+n);}
 void flush(){}void set_baud_rate(uint32_t b){baud=b;}uint32_t get_baud_rate(){return baud;}
 void load_settings(){bauds.push_back(baud);}
 void append(const std::vector<uint8_t>&v){rx.insert(rx.end(),v.begin(),v.end());}
};}
'''}
 for name,data in files.items():
  p=t/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(data)
 public=t/'public.cpp';public.write_text('''#include "goats_gnss_color.h"
#include "goats_m9n_cfg.h"
#include "goats_ubx_m9n_ak97_full.h"
#include "goats_gps_diag.h"
#ifdef ARDUINO_STUB_INCLUDED
#error Private Arduino headers must not leak into main.cpp
#endif
int main(){return 0;}
''')
 subprocess.run(['g++','-std=c++17','-I'+str(t),'-I'+str(COMP),str(public),'-o',str(t/'public')],check=True)
 (t/'esphome/components/goats_gnss_color').mkdir(parents=True)
 (t/'esphome/components/goats_gnss_color/goats_gnss_color.h').symlink_to(COMP/'goats_gnss_color.h')
 source=(ROOT/'tests/rlcd_color_gnss_diag2/test_receiver.cpp').read_text()
 source=source.replace('REFERENCE_PARSER',str(REF/'goats_ubx_m9n_ak97_full.h')).replace('REFERENCE_CONFIG',str(t/'reference_cfg.h')).replace('COMPONENT_CPP',str(COMP/'goats_gnss_color.cpp')).replace('BRIDGE_HEADER',str(PORT/'goats_color_gnss_bridge.h'))
 (t/'reference_cfg.h').write_text((REF/'goats_m9n_cfg.h').read_text().replace('#pragma once',''))
 (t/'test.cpp').write_text(source)
 exe=t/'test'
 subprocess.run(['g++','-std=c++17','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(t),'-I'+str(COMP),str(t/'test.cpp'),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
print('PASS: private Arduino owner, original DIAG2 UART/config/parser, RC3.3 core/UI/scheduling, clock epochs')
if '--all' in sys.argv:
 env=dict(os.environ,COLOR_PORT_FOLDER=PORT.name,COLOR_YAML_NAME='goats_42_color_rc3_3_gnss_diag2.yaml')
 subprocess.run([sys.executable,str(ROOT/'tests/rlcd_color_rc3/test_layout.py')],env=env,check=True)
 with tempfile.TemporaryDirectory(prefix='rc33-core-') as tmp:
  for name,stubs in [('test_clock.cpp','tests/rc2/stubs'),('test_dates.cpp','tests/rc2/stubs'),('test_screen_mode.cpp','tests/rc2/screen_mode_stubs'),('test_rlcd_summary.cpp','tests/guition_port/stubs')]:
   exe=Path(tmp)/name.removesuffix('.cpp')
   subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-I'+str(ROOT/stubs),'-I'+str(ROOT/'tests/guition_port/stubs'),'-I'+str(PORT),str(ROOT/'tests/rc2'/name),'-o',str(exe)],check=True)
   subprocess.run([str(exe)],check=True)
 subprocess.run([sys.executable,str(ROOT/'tests/rc2/test_rlcd_restart.py'),str(PORT.relative_to(ROOT))],check=True)
