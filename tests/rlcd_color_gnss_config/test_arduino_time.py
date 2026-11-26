"""Qualified RC3.3 and unqualified Arduino calls must share ESPHome's timebase."""
from pathlib import Path
import re
import subprocess
import tempfile
ROOT=Path(__file__).resolve().parents[2]
PORT=ROOT/'firmware/rlcd-42-3-colori/GOATS_RLCD_COLOR_RC3_3'
main=(PORT.parent/'.esphome/build/goats-42-color-rc3-3/src/main.cpp').read_text()
macros='\n'.join(re.findall(r'^#(?:undef (?:millis|delay)|define (?:millis|delay)\([^\n]*)$',main,re.M))
assert '#define millis() esphome::millis()' in macros
assert '#define delay(x) esphome::delay(x)' in macros
with tempfile.TemporaryDirectory() as tmp:
    t=Path(tmp);hal=t/'esphome/core/hal.h';hal.parent.mkdir(parents=True)
    hal.write_text('''#pragma once
#include <cstdint>
inline uint32_t test_ms=42;
namespace esphome {
inline uint32_t millis(){return test_ms;}
inline void delay(uint32_t ms){test_ms+=ms;}
}
inline unsigned long millis(){return 999999;}
inline void delay(unsigned long){}
''')
    prefix='#include "esphome/core/hal.h"\n'+macros+'\n'
    broken=t/'broken.cpp';broken.write_text(prefix+'int main(){return esphome::millis();}\n')
    p=subprocess.run(['g++','-std=c++17','-I'+str(t),str(broken),'-o',str(t/'broken')],capture_output=True,text=True)
    assert p.returncode!=0 and 'esphome::esphome' in p.stderr
    test=t/'fixed.cpp';test.write_text(prefix+'''#define USE_ARDUINO
#include "goats_arduino_time.h"
#include <cassert>
namespace example_rc33 {
uint32_t unqualified(){return millis();}
uint32_t qualified(){return esphome::millis();}
void advance(){delay(10);esphome::delay(20);}
}
int main(){
 assert(example_rc33::unqualified()==42&&example_rc33::qualified()==42);
 example_rc33::advance();
 assert(test_ms==72&&example_rc33::qualified()==72&&example_rc33::unqualified()==72);
}
''')
    exe=t/'fixed'
    subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
                    '-fno-omit-frame-pointer','-I'+str(t),'-I'+str(PORT),str(test),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
print('PASS: actual generated Arduino macros reproduce qualified-call failure; adapter preserves ESPHome clock/delay for both call styles')
