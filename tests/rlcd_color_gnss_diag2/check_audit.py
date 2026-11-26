"""Audit must keep the failing complete runtime and only observe it."""
from pathlib import Path
import subprocess,sys,tempfile,yaml
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'firmware/rlcd-42-3-colori'
PORT=BASE/'GOATS_RLCD_COLOR_RC3_3_GNSS2_NOSD'
class Loader(yaml.SafeLoader):pass
Loader.add_multi_constructor('!',lambda loader,tag,node:loader.construct_scalar(node))
def config(name):
 p=subprocess.run([sys.executable,'-m','esphome','config',str(BASE/name)],capture_output=True,text=True)
 assert p.returncode==0,p.stderr
 return yaml.load(p.stdout,Loader=Loader)
a=config('goats_42_color_rc3_3_gnss2_nosd.yaml');b=config('goats_42_color_rc3_3_gnss2_nosd_audit.yaml')
for key in a:
 if key not in ['esphome','display']:assert a[key]==b[key],key
for key in a['esphome']:
 if key not in ['name','friendly_name','comment','includes','build_path']:assert a['esphome'][key]==b['esphome'][key],key
assert b['esphome']['includes']==a['esphome']['includes']+[str(PORT/'goats_gnss_audit.h')]
for key in a['display'][0]:
 if key!='lambda':assert a['display'][0][key]==b['display'][0][key],key
assert a['display'][0]['update_interval']==b['display'][0]['update_interval']
normal=a['display'][0]['lambda'].rstrip('\n')
expected=''.join('  '+line+'\n' for line in normal.splitlines())
def clean_blank_lines(text):return '\n'.join('' if not line.strip() else line for line in text.splitlines())
assert clean_blank_lines(expected) in clean_blank_lines(b['display'][0]['lambda']), 'The exact normal renderer must still execute'
assert 'render_rc33();' in b['display'][0]['lambda']
assert '10000U' in b['display'][0]['lambda']
with tempfile.TemporaryDirectory(prefix='rc33-audit-') as tmp:
 t=Path(tmp)
 files={
 'esphome/components/uart/uart_component_esp_idf.h':'''#pragma once
#include <cstdint>
namespace esphome::uart {
struct UARTComponent{};
struct IDFUARTComponent:UARTComponent{bool failed=false;bool is_failed(){return failed;}uint8_t port=0;uint8_t get_hw_serial_number(){return port;}};
}
''',
 'esphome/core/version.h':'#pragma once\n#define ESPHOME_VERSION "test"\n',
 'driver/uart.h':'''#pragma once
#include <cstdint>
#include <cstddef>
#define SOC_UART_NUM 3
using uart_port_t=int;
inline bool installed=true;inline unsigned read_calls=0;
inline bool uart_is_driver_installed(int){return installed;}
inline int uart_get_baudrate(int,uint32_t*p){++read_calls;*p=230432;return 0;}
inline int uart_get_buffered_data_len(int,size_t*p){++read_calls;*p=12;return 0;}
''',
 'driver/gpio.h':'#pragma once\n#define GPIO_NUM_1 1\ninline int gpio_get_level(int){return 1;}\n',
 'esp_heap_caps.h':'''#pragma once
#define MALLOC_CAP_INTERNAL 1
inline unsigned heap_caps_get_free_size(int){return 120000;}
inline unsigned heap_caps_get_largest_free_block(int){return 80000;}
''',
 'esp_idf_version.h':'#pragma once\n'}
 for name,data in files.items():
  p=t/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(data)
 cpp=t/'test.cpp';cpp.write_text('''#include <cassert>
#include <cstring>
#include "goats_gnss_audit.h"
using namespace goats_gnss_audit;
int main(){
 esphome::uart::IDFUARTComponent bus;
 auto h=inspect(bus);assert(h.port==0 && h.baud==230432 && h.installed && !h.failed);
 assert(h.buffered==12 && h.rx_level==1 && h.free_internal==120000 && h.largest_internal==80000 && read_calls==2);
 installed=false;bus.failed=true;h=inspect(bus);assert(!h.installed && h.failed && h.read_error==-1 && h.baud==0 && read_calls==2);
 bus.port=255;h=inspect(bus);assert(h.port==255 && !h.installed && read_calls==2);
 assert(!strcmp(status(1,0,0,0,0,0,0,0,0,0),"USB MSC: GPS SOSPESO"));
 assert(!strcmp(status(0,0,0,0,0,0,0,0,0,0),"GNSS NON ATTIVATO AL BOOT"));
 assert(!strcmp(status(0,1,0,0,0,0,0,0,0,0),"POLL NON ESEGUITO"));
 assert(!strcmp(status(0,1,0,0,1,0,0,0,0,0),"CONFIGURAZIONE NON TERMINATA"));
 assert(!strcmp(status(0,1,1,1,1,0,0,0,0,0),"ERRORE DRIVER UART"));
 assert(!strcmp(status(0,1,1,0,1,0,0,0,0,0),"NESSUN BYTE DAL GPS"));
 assert(!strcmp(status(0,1,1,0,1,1,0,0,0,0),"BYTE RX, NESSUN UBX VALIDO"));
 assert(!strcmp(status(0,1,1,0,1,1,1,0,0,0),"UBX OK, NAV-PVT ASSENTE"));
 assert(!strcmp(status(0,1,1,0,1,1,1,1,0,0),"NAV-PVT NON ARRIVA AL CORE"));
 assert(!strcmp(status(0,1,1,0,1,1,1,1,1,0),"CORE RC3.3: ATTESA FIX"));
 assert(!strcmp(status(0,1,1,0,1,1,1,1,1,1),"CORE RC3.3: FIX PRESENTE"));
}
''')
 exe=t/'test';subprocess.run(['g++','-std=c++17','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(t),'-I'+str(PORT),str(cpp),'-o',str(exe)],check=True);subprocess.run([str(exe)],check=True)
print('PASS: full normal runtime/transport/scheduling unchanged, audit only reads UART metadata, missing driver/invalid port guards, stage classification')
