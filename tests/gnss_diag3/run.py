from pathlib import Path
import subprocess,tempfile,sys,re,yaml
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'firmware/rlcd-42-3-colori'
D2=BASE/'GOATS_V0405_GPS_DIAG2/components/goats_spi_diag'
D3=BASE/'GOATS_V0405_GPS_DIAG3/components/goats_spi_diag'
assert (D2/'goats_m9n_cfg.h').read_bytes()==(D3/'goats_m9n_cfg.h').read_bytes()
assert (D2/'goats_ubx_m9n_ak97_full.h').read_bytes()==(D3/'goats_ubx_m9n_ak97_full.h').read_bytes()
old=yaml.safe_load((BASE/'goats_42_v0405_gps_diag2.yaml').read_text())
new=yaml.safe_load((BASE/'goats_42_v0405_gps_diag3.yaml').read_text())
for section in ['esp32','logger','uart','goats_spi_diag']:assert old[section]==new[section],section
assert not set(new)&{'wifi','ota','psram','api','web_server'}
s=(D3/'goats_spi_diag.cpp').read_text()
assert 'stability.tick(::millis())' in s
assert 'const uint32_t now=::millis()' in s[s.index('void GoatsSpiDiag::gps_diag_draw_()'):]
subprocess.run([sys.executable,str(ROOT/'tests/gnss_v0405_diag/run.py'),'3'],check=True)
with tempfile.TemporaryDirectory(prefix='gps-diag3-') as tmp:
 t=Path(tmp)
 exe=t/'stability'
 subprocess.run(['g++','-std=c++17','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(D3),str(ROOT/'tests/gnss_diag3/test_stability.cpp'),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
 # Execute the actual panel method with original bitmap font tables.
 (t/'esphome/components/uart').mkdir(parents=True)
 (t/'Arduino.h').write_text('#pragma once\n#include <cstdint>\n#include <cstdio>\ninline uint32_t clock_ms=0;\ninline uint32_t millis(){return clock_ms;}\ninline void delay(uint32_t){}\n')
 (t/'esphome/components/uart/uart.h').write_text('#pragma once\n#include <cstdint>\n#include <cstddef>\nnamespace esphome::uart {\nstruct UARTComponent {\n uint32_t baud=230400;\n void set_baud_rate(uint32_t b){baud=b;}uint32_t get_baud_rate(){return baud;}\n void load_settings(){}void write_array(const uint8_t*,size_t){}void flush(){}\n unsigned available(){return 0;}bool read_byte(uint8_t*){return false;}\n};}\n')
 source=(ROOT/'tests/gnss_diag3/test_panel.cpp').read_text()
 firmware=(D3/'goats_spi_diag.cpp').read_text()
 font=firmware[firmware.index('static int font_width_('):firmware.index('void GoatsSpiDiag::font_text_(')]
 panel=firmware[firmware.index('void GoatsSpiDiag::gps_diag_draw_()'):firmware.index('void GoatsSpiDiag::dump_config()')]
 (t/'panel.cpp').write_text(source.replace('FONT_WIDTH_FUNCTION',font).replace('PANEL_FUNCTION',panel))
 exe=t/'panel'
 subprocess.run(['g++','-std=c++17','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(t),'-I'+str(D3),str(t/'panel.cpp'),'-o',str(exe)],check=True)
 subprocess.run([str(exe),'/tmp/gps-diag3-panel.pgm'],check=True)
print('PASS: DIAG2 config/parser/startup parity; real stability observer, fix loss, data gaps, stale SAT/DOP, 2D/3D/time-only, week/timer wrap')
