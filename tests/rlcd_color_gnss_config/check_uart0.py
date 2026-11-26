"""Verify the resolved variants and execute ESPHome's real UART allocator code.
Run with ESPHome's Python. No physical UART is emulated by this test.
"""
from pathlib import Path
import subprocess
import sys
import tempfile
import yaml
import esphome
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'firmware/rlcd-42-3-colori'
class Loader(yaml.SafeLoader):pass
Loader.add_multi_constructor('!',lambda loader,tag,node:loader.construct_scalar(node))
def config(filename):
    p=subprocess.run([sys.executable,'-m','esphome','config',str(BASE/filename)],capture_output=True,text=True)
    assert p.returncode==0,p.stderr
    return yaml.load(p.stdout,Loader=Loader)
base=config('goats_42_color_rc3_3.yaml')
racing=config('goats_42_color_rc3_3_uart0.yaml')
diag=config('goats_42_color_rc3_3_uart0_diag.yaml')
for variant in [racing,diag]:
    for key in base:
        if key not in ('logger','esphome','display'):
            assert base[key]==variant[key],key
    expected_logger=dict(base['logger']);expected_logger['baud_rate']=0
    assert expected_logger==variant['logger']
    for key in base['esphome']:
        if key not in ('friendly_name','comment'):
            assert base['esphome'][key]==variant['esphome'][key],key
assert base['display']==racing['display'], 'Racing layout drift'
assert len(diag['display'])==1
for key in base['display'][0]:
    if key!='lambda':assert base['display'][0][key]==diag['display'][0][key],key
assert 'RC3.3 - GPS UART0' in diag['display'][0]['lambda']
# Exercise the installed ESPHome allocator, not a separately rewritten rule.
source=(Path(esphome.__file__).parent/'components/uart/uart_component_esp_idf.cpp').read_text()
start=source.index('void IDFUARTComponent::setup() {')
end=start+len('void IDFUARTComponent::setup() {');depth=1
while depth:
    if source[end]=='{':depth+=1
    if source[end]=='}':depth-=1
    end+=1
setup=source[start:end]
cpp='''
#include <cassert>
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#define USE_LOGGER
#define SOC_UART_NUM 3
#define SOC_UART_LP_NUM 0
#define SOC_UART_FIFO_LEN 128
#define ESP_LOGW(...) do{}while(0)
using uart_port_t=int;
namespace logger {
struct Logger {unsigned baud;unsigned get_baud_rate(){return baud;}unsigned get_uart_num(){return 0;}};
inline Logger *global_logger;
}
class IDFUARTComponent {public:
void setup();int uart_num_=-1,loaded_port=-1;size_t rx_buffer_size_=16384;bool failed=false;
void mark_failed(){failed=true;}void load_settings(bool){loaded_port=uart_num_;}
};
'''+setup+'''
int main(int argc,char **argv){
 assert(argc==3);logger::Logger log{unsigned(std::strtoul(argv[1],nullptr,10))};logger::global_logger=&log;
 const int expected=std::atoi(argv[2]);
 IDFUARTComponent gps;gps.setup();assert(!gps.failed&&gps.uart_num_==expected&&gps.loaded_port==expected);
 IDFUARTComponent second;second.setup();assert(!second.failed&&second.uart_num_==expected+1);
}
'''
with tempfile.TemporaryDirectory() as tmp:
    source=Path(tmp)/'allocator.cpp';source.write_text(cpp);exe=Path(tmp)/'allocator'
    subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',
                    '-fsanitize=address,undefined','-fno-omit-frame-pointer',str(source),'-o',str(exe)],check=True)
    subprocess.run([str(exe),'115200','1'],check=True)
    subprocess.run([str(exe),'0','0'],check=True)
print('PASS: real ESPHome UART allocation: logger UART0 enabled -> GPS UART1; disabled -> GPS UART0')
print('PASS: UART0 variants change only serial logger, identity and diagnostic renderer; Racing/core/GNSS/USB/SD preserved')
