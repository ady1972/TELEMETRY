from pathlib import Path
import subprocess,tempfile
ROOT=Path(__file__).resolve().parents[2]
STEP=ROOT/'firmware/rlcd-42-3-colori/GOATS_DIAG3_RC33_STEP3F_BACKEND/components/goats_spi_diag'
dst=(STEP/'goats_spi_diag.cpp').read_text()
with tempfile.TemporaryDirectory(prefix='diag3-core33-') as tmp:
 t=Path(tmp)
 files={
 'Arduino.h':'''#pragma once
#include <cstdint>
#include <cstdio>
inline uint32_t clock_ms=1000;
inline uint32_t millis(){return clock_ms;}
inline void delay(uint32_t ms){clock_ms+=ms;}
''',
 'esphome/core/hal.h':'''#pragma once
#include <Arduino.h>
namespace esphome {inline uint32_t millis(){return clock_ms-500;}}
''',
 'esphome/components/uart/uart.h':'''#pragma once
#include <cstdint>
#include <cstddef>
#include <vector>
#include <deque>
namespace esphome::uart {
struct UARTComponent {
 uint32_t baud=38400,reads=0,writes=0;
 std::deque<uint8_t>rx;
 void set_baud_rate(uint32_t b){baud=b;}void load_settings(){}
 void write_array(const uint8_t*,size_t){++writes;}void flush(){}
 unsigned available(){return rx.size();}
 bool read_byte(uint8_t*p){if(rx.empty())return false;*p=rx.front();rx.pop_front();++reads;return true;}
};}
''',
 'driver/usb_serial_jtag.h':'''#pragma once
#include <cstddef>
#include <cstdint>
#define pdMS_TO_TICKS(ms) (ms)
inline unsigned usb_installs=0,usb_reads=0,usb_writes=0;
struct usb_serial_jtag_driver_config_t {size_t rx_buffer_size=0,tx_buffer_size=0;};
inline int usb_serial_jtag_driver_install(const usb_serial_jtag_driver_config_t*){++usb_installs;return 0;}
inline int usb_serial_jtag_write_bytes(const void*,size_t n,unsigned){++usb_writes;return n;}
inline int usb_serial_jtag_read_bytes(uint8_t*,size_t,unsigned){++usb_reads;return 0;}
''',
 'nvs.h':'''#pragma once
#include <cstddef>
#include <cstdint>
#define ESP_OK 0
#define ESP_ERR_INVALID_STATE 0x103
#define NVS_READONLY 0
#define NVS_READWRITE 1
using esp_err_t=int;using nvs_handle_t=int;
inline unsigned nvs_calls=0;
inline int nvs_open(const char*,int,nvs_handle_t*){++nvs_calls;return 1;}
inline int nvs_get_blob(nvs_handle_t,const char*,void*,size_t*){++nvs_calls;return 1;}
inline int nvs_get_u32(nvs_handle_t,const char*,uint32_t*){++nvs_calls;return 1;}
inline int nvs_set_blob(nvs_handle_t,const char*,const void*,size_t){++nvs_calls;return 0;}
inline int nvs_set_u32(nvs_handle_t,const char*,uint32_t){++nvs_calls;return 0;}
inline int nvs_commit(nvs_handle_t){++nvs_calls;return 0;}
inline void nvs_close(nvs_handle_t){++nvs_calls;}
''',
 'nvs_flash.h':'#pragma once\n#include "nvs.h"\n'}
 for name,data in files.items():
  p=t/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(data)
 source=ROOT/'tests/diag3_rc33_step3f_backend/test_modes.cpp';exe=t/'core'
 poll_body=dst[dst.index('void GoatsSpiDiag::gps_poll_()'):dst.index('void GoatsSpiDiag::menu_draw_()')]
 assert poll_body.count('goats_m9n::poll(gps_uart_)')==1 and 'goats_laptimer_update' not in poll_body
 (t/'test.cpp').write_text(source.read_text().replace('ACTUAL_GPS_POLL',poll_body))
 subprocess.run(['g++','-std=c++17','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(t),'-I'+str(STEP),str(t/'test.cpp'),'-o',str(exe)],check=True)
 for mode in [0,1,2,3,4]:subprocess.run([str(exe),str(mode)],check=True)
 # Main.cpp must not instantiate the private engine or the RC3.3 application.
 (t/'public.cpp').write_text('''#include "goats_laptimer.h"
#include "goats_rc33_step1.h"
#include "rc33_goats_test_b.h"
int main(){return 0;}
''')
 subprocess.run(['g++','-std=c++17','-I'+str(t),'-I'+str(STEP),str(t/'public.cpp'),'-o',str(t/'public')],check=True)

print('PASS: real parser + core on no-fix/fix at 25Hz; all five mode entry gates and no extra UART writes')
