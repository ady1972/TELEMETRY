"""Keep the proven DIAG3 hardware path, add only a passive raw-PVT core consumer."""
from pathlib import Path
import subprocess,tempfile,sys,yaml,re,json,shlex,os
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'firmware/rlcd-42-3-colori'
D3=BASE/'GOATS_V0405_GPS_DIAG3/components/goats_spi_diag'
STEP=BASE/'GOATS_DIAG3_RC33_STEP1/components/goats_spi_diag'
REF=ROOT/'firmware/rlcd-42/GOATS_RLCD_RC3_3'
a=yaml.safe_load((BASE/'goats_42_v0405_gps_diag3.yaml').read_text());b=yaml.safe_load((BASE/'goats_42_diag3_rc33_step1.yaml').read_text())
for key in a:
 if key not in ['esphome','external_components']:assert a[key]==b[key],key
assert not set(b)&{'interval','display','spi','wifi','ota','api','web_server','psram'}
for filename in ['__init__.py','goats_spi_diag.h','goats_m9n_cfg.h','goats_ubx_m9n_ak97_full.h','goats_gps_stability.h','goats_font_bitmap.h','goats_lap_storage.h']:
 assert (D3/filename).read_bytes()==(STEP/filename).read_bytes(),filename
src=(D3/'goats_spi_diag.cpp').read_text();dst=(STEP/'goats_spi_diag.cpp').read_text()
for begin,end in [('void GoatsSpiDiag::controller_init_()', '#include "goats_font_bitmap.h"'),('void GoatsSpiDiag::setup()','void GoatsSpiDiag::loop()'),('void GoatsSpiDiag::pixel_(','void GoatsSpiDiag::rect_('),('uint32_t GoatsSpiDiag::region_(','static const uint8_t label_delta_original')]:
 assert src[src.index(begin):src.index(end)]==dst[dst.index(begin):dst.index(end)],begin
old_panel=src[src.index('void GoatsSpiDiag::gps_diag_draw_()'):src.index('void GoatsSpiDiag::dump_config()')]
new_panel=dst[dst.index('void GoatsSpiDiag::gps_diag_draw_()'):dst.index('void GoatsSpiDiag::dump_config()')]
new_panel=new_panel.replace('"DIAG3 + RC3.3 STEP1"','"GPS DIAG3 - STABILITA"').replace('snprintf(b,sizeof(b),"%s",goats_rc33_step1::line());','snprintf(b,sizeof(b),"RX1/TX2 - %lu BAUD - NO SD",(unsigned long)(gps_uart_?gps_uart_->get_baud_rate():0));')
assert old_panel==new_panel,'Only the title and core footer may differ from the proven screen'
def unwrap(p):
 s=p.read_text();prefix='#pragma once\n#ifdef GOATS_RC33_STEP1_IMPL\n';suffix='\n#endif // GOATS_RC33_STEP1_IMPL\n'
 assert s.startswith(prefix) and s.endswith(suffix)
 return s[len(prefix):-len(suffix)]
assert unwrap(STEP/'goats_laptimer.h')==(REF/'goats_laptimer.h').read_text()
assert (STEP/'goats_track_types.h').read_bytes()==(REF/'goats_track_types.h').read_bytes()
for name in ['goats_recording_clock.h','goats_session_control.h','goats_lap_speed_stats.h','goats_racing_bridge.h','goats_test_b.h']:
 expected=(REF/name).read_text()
 if name=='goats_test_b.h':expected=expected.replace('#include "esphome.h"','#include "esphome/core/hal.h"',1)
 for include in ['goats_recording_clock.h','goats_lap_speed_stats.h','goats_session_control.h','goats_sd_usb_export.h']:
  expected=expected.replace('#include \"'+include+'\"','#include \"rc33_'+include+'\"')
 assert unwrap(STEP/('rc33_'+name))==expected,name
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
 source=ROOT/'tests/diag3_rc33_step1/test_core.cpp';exe=t/'core'
 poll_body=dst[dst.index('void GoatsSpiDiag::gps_poll_()'):dst.index('void GoatsSpiDiag::menu_draw_()')]
 assert poll_body.count('goats_m9n::poll(gps_uart_)')==1 and 'goats_laptimer_update' not in poll_body
 (t/'test.cpp').write_text(source.read_text().replace('ACTUAL_GPS_POLL',poll_body))
 subprocess.run(['g++','-std=c++17','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(t),'-I'+str(STEP),str(t/'test.cpp'),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
 # Main.cpp must not instantiate the private engine or the RC3.3 application.
 (t/'public.cpp').write_text('''#include "goats_laptimer.h"
#include "goats_rc33_step1.h"
#include "rc33_goats_test_b.h"
int main(){return 0;}
''')
 subprocess.run(['g++','-std=c++17','-I'+str(t),'-I'+str(STEP),str(t/'public.cpp'),'-o',str(t/'public')],check=True)
print('PASS: same DIAG3 UART/config/parser/LCD/boot, RC3.3 core source parity, raw-PVT handoff, no new USB/NVS/SD activity')
