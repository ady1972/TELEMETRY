"""Compare the uploaded COLOR parser with its ESP-IDF port and RC3.3 adapter."""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'firmware/rlcd-42-3-colori'
PORT = BASE / 'GOATS_RLCD_COLOR_RC3_3'
ORIGINAL = BASE / 'GOATS_V0405_BOOT_FAST_FONT_TEST/components/goats_spi_diag/goats_ubx_m9n_ak97_full.h'
original = ORIGINAL.read_text()
expected = original.replace('#include <Arduino.h>', '#include "esphome/core/hal.h"\n#include <cstdio>')
expected = expected.replace('delay(', 'esphome::delay(').replace('millis()', 'esphome::millis()')
expected = expected.replace('struct Parser {', '''// Observation only: validated payloads are forwarded unchanged to RC3.3.
using FrameObserver = void (*)(uint8_t, uint8_t, const std::vector<uint8_t>&);
inline FrameObserver frame_observer{nullptr};
inline uint32_t rx_bytes{0}, checksum_errors{0}, last_rx_ms{0};
struct Parser {''')
expected = expected.replace('  void dispatch(){', '  void dispatch(){\n    if(frame_observer)frame_observer(cls,id,p);')
expected = expected.replace('case 8:if(rxa==cka&&c==ckb)dispatch();reset();break;',
                            'case 8:if(rxa==cka&&c==ckb)dispatch();else checksum_errors++;reset();break;')
expected = expected.replace('    parser.feed(c);}', '    rx_bytes++;last_rx_ms=esphome::millis();\n    parser.feed(c);}')
assert expected == (PORT / 'goats_color_gnss_v0405.h').read_text(), 'Unexpected change to proven parser'
yaml = (BASE / 'goats_42_color_rc3_3.yaml').read_text()
assert '- GOATS_RLCD_COLOR_RC3_3/goats_color_gnss_v0405.h' in yaml
assert '- GOATS_RLCD_COLOR_RC3_3/goats_color_gnss_bridge.h' in yaml
assert '- GOATS_RLCD_COLOR_RC3_3/m9n_passive.h' not in yaml
assert 'goats_m9n::configure' not in yaml
with tempfile.TemporaryDirectory() as tmp:
    t = Path(tmp)
    files = {
        'esphome/core/hal.h': '''#pragma once
#include <cstdint>
inline uint32_t test_ms=100;
namespace esphome {
inline uint32_t millis(){return test_ms;}
inline void delay(uint32_t ms){test_ms+=ms;}
}
''',
        'Arduino.h': '''#pragma once
#include <cstdio>
#include "esphome/core/hal.h"
using esphome::millis;
using esphome::delay;
''',
        'esphome/components/uart/uart.h': '''#pragma once
#include <cstdint>
#include <vector>
#include <deque>
namespace esphome::uart {
class UARTComponent {public:
std::deque<uint8_t> rx; unsigned writes=0,bauds=0;
unsigned available(){return rx.size();}
bool read_byte(uint8_t *out){if(rx.empty())return false;*out=rx.front();rx.pop_front();return true;}
void write_array(const uint8_t*,size_t){++writes;}
void flush(){}
void set_baud_rate(uint32_t){++bauds;}
void load_settings(){}
void append(const std::vector<uint8_t>&v){rx.insert(rx.end(),v.begin(),v.end());}
};}
''',
    }
    for name, content in files.items():
        p=t/name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    exe=t/'test_reception'
    subprocess.run(['g++', '-std=c++17', '-Wall', '-Wextra', '-Werror',
                    '-Wno-misleading-indentation', '-Wno-format-truncation',
                    '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                    '-DORIGINAL_PARSER_HEADER="'+str(ORIGINAL)+'"',
                    '-I'+str(t), '-I'+str(PORT),
                    str(ROOT/'tests/rlcd_color_gnss_config/test_reception.cpp'),
                    '-o', str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
print('PASS: original COLOR reception/state/queue parity; fragmented/corrupt/oversize frames,')
print('NMEA/noise, 100-sample bursts, expiry, raw NAV-PVT delivery once to RC3.3, zero runtime UART writes')
