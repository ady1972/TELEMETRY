"""Host checks; run with Python 3 + g++. No hardware claims."""
from pathlib import Path
import os
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / 'components/goats_power_test'
ORIGINAL = ROOT.parent / 'GOATS_V0405_BOOT_FAST_FONT_TEST/components/goats_spi_diag'
config = (ROOT.parent / 'goats_s3_zero_test_alimentazione_01.yaml').read_text()
assert 'flash_size: 4MB' in config and 'USB_SERIAL_JTAG' in config
for forbidden in ['uart', 'wifi', 'ota', 'api', 'web_server', 'psram', 'sd_mmc', 'binary_sensor']:
    assert not re.search(r'^' + forbidden + r':', config, re.M), forbidden
for pin in [8, 9, 10, 11, 12]:
    assert f'GPIO{pin}' in config
source = (COMPONENT / 'goats_power_test.cpp').read_text()
for forbidden in ['uart.h', 'gps_poll', 'goats_cfg', 'goats_laptimer', 'nvs_', 'f_write', 'f_sync']:
    assert forbidden not in source, forbidden
if ORIGINAL.exists():
    original = (ORIGINAL / 'goats_spi_diag.cpp').read_text()
    def body(text, marker):
        start = text.index('{', text.index(marker)); end = start + 1; depth = 1
        while depth:
            if text[end] == '{': depth += 1
            if text[end] == '}': depth -= 1
            end += 1
        return text[start:end]
    for method in ['controller_init_', 'pixel_', 'font_text_', 'rect_']:
        assert body(source, 'GoatsPowerTest::'+method) == body(original, 'GoatsSpiDiag::'+method), method
    assert (COMPONENT/'goats_font_bitmap.h').read_bytes() == (ORIGINAL/'goats_font_bitmap.h').read_bytes()
    print('PASS: original init, RBW mapping, rotation, rasterizer and font preserved')
else:
    print('Original V0.40.5 absent from standalone ZIP: parity check skipped')

with tempfile.TemporaryDirectory() as temporary:
    stub = Path(temporary)
    files = {
        'esphome/core/component.h': '''#pragma once
#include <cstdint>
#include <vector>
inline int64_t test_now_us=0;
namespace esphome {
class GPIOPin {public:bool level=false;std::vector<bool> history;void setup(){} void digital_write(bool b){level=b;history.push_back(b);}};
namespace setup_priority {constexpr float HARDWARE=800;}
class PollingComponent {public:virtual void setup(){} virtual void update(){} virtual void dump_config(){} virtual float get_setup_priority() const{return 0;}};
inline void delay(uint32_t ms){test_now_us+=static_cast<int64_t>(ms)*1000;}
}
''',
        'esphome/components/spi/spi.h': '''#pragma once
#include <cstddef>
#include <cstdint>
#include <vector>
namespace esphome::spi {
enum {BIT_ORDER_MSB_FIRST,CLOCK_POLARITY_LOW,CLOCK_PHASE_LEADING,DATA_RATE_4MHZ};
template<int,int,int,int>class SPIDevice {public:
std::vector<uint8_t> written_bytes;std::vector<size_t> write_sizes;
void spi_setup(){} void enable(){} void disable(){}
void write_byte(uint8_t b){written_bytes.push_back(b);}
void write_array(const uint8_t*,size_t n){write_sizes.push_back(n);}
};}
''',
        'esphome/core/log.h': '''#pragma once
#define ESP_LOGI(...) do{}while(0)
#define ESP_LOGCONFIG(...) do{}while(0)
#define LOG_PIN(...) do{}while(0)
''',
        'esp_system.h': '''#pragma once
enum esp_reset_reason_t {ESP_RST_POWERON=1,ESP_RST_EXT,ESP_RST_SW,ESP_RST_PANIC,ESP_RST_INT_WDT,ESP_RST_TASK_WDT,ESP_RST_WDT,ESP_RST_DEEPSLEEP,ESP_RST_BROWNOUT,ESP_RST_SDIO};
inline esp_reset_reason_t test_reason=ESP_RST_POWERON;
inline esp_reset_reason_t esp_reset_reason(){return test_reason;}
''',
        'esp_timer.h': '''#pragma once
#include "esphome/core/component.h"
inline int64_t esp_timer_get_time(){return test_now_us;}
''',
    }
    for name, contents in files.items():
        path = stub / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents)
    binary = stub / 'test_driver'
    subprocess.run(['g++', '-std=c++17', '-Wall', '-Wextra', '-Werror', '-Wno-unused-variable',
                    '-Wno-unused-parameter', '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                    '-I'+str(stub), '-I'+str(COMPONENT), str(ROOT/'tests/test_driver.cpp'),
                    str(COMPONENT/'goats_power_test.cpp'), '-o', str(binary)], check=True)
    # Optional visual preview path; no generated files in the source directory.
    args = [str(binary)]
    if os.environ.get('POWER_PREVIEW'): args.append(os.environ['POWER_PREVIEW'])
    subprocess.run(args, check=True)
print('PASS: real renderer/driver under ASan+UBSan; all pixels/colors, bounds, reset pulse,')
print('first frame zero, 1 Hz elapsed time, >49 days, 10 digits, brownout/software reset, full SPI frame')
