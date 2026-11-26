from pathlib import Path
import subprocess,tempfile,re,hashlib
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'firmware/rlcd-42-3-colori';SIZES=[13,16,20,28,36,42,44,52,60,64,72,78,82]
STEP=BASE/'GOATS_DIAG3_RC33_STEP3/components/goats_spi_diag';OLD=BASE/'GOATS_DIAG3_RC33_STEP2A/components/goats_spi_diag'
for n in ['goats_spi_diag.h','__init__.py','goats_racing_step2.h','rc33_goats_postlap_ui.h','goats_font_bitmap.h']:
 assert (STEP/n).read_bytes()==(OLD/n).read_bytes(),n
assert (STEP.parents[1]/'fonts/RobotoCondensed-Bold.ttf').read_bytes()==(OLD.parents[1]/'fonts/RobotoCondensed-Bold.ttf').read_bytes()
cpp=(STEP/'goats_spi_diag.cpp').read_text();old=(OLD/'goats_spi_diag.cpp').read_text()
for begin,end in [('void GoatsSpiDiag::racing_draw_()','void GoatsSpiDiag::boot_key_()'),('void GoatsSpiDiag::gps_poll_()','void GoatsSpiDiag::menu_draw_()')]:
 assert cpp[cpp.index(begin):cpp.index(end)]==old[old.index(begin):old.index(end)]
loop=cpp[cpp.index('void GoatsSpiDiag::loop()'):cpp.index('void GoatsSpiDiag::racing_draw_()')]
assert loop.index('configure(*gps_uart_)')<loop.index('goats_rc33_step1::attach()')<loop.index('goats_step3::start()')
assert loop.index('gps_poll_();')<loop.index('goats_step3::tick()')<loop.index('racing_flush_()')
# Reuse STEP2A's actual SPI/packing/renderer test on STEP3, with the new BOOT
# action hooks stubbed separately (their real implementation is in run.py).
s=(ROOT/'tests/diag3_rc33_step2a/run.py').read_text();s=s[s.index('# Use the glyph'):]
a=s.index(' # Exercise real core');b=s.index(' # Production pixel packing',a);s=s[:a]+s[b:]
s=s.replace('goats-diag3-rc33-step2a','goats-diag3-rc33-step3').replace('GOATS_DIAG3_RC33_STEP2A','GOATS_DIAG3_RC33_STEP3')
s=s.replace(" (t/'test.cpp').write_text(code)",''' code=code.replace('struct GoatsSpiDiag {', 'namespace goats_step3_store {struct State{unsigned active=0;};inline State&state(){static State s;return s;}}\\nnamespace goats_step3 {inline bool free_start(){goats_step3_store::state().active=1;return true;}inline bool stop(){goats_step3_store::state().active=0;return true;}}\\nstruct GoatsSpiDiag {')
 code=code.replace(' puts("PASS:', ' boot_level=0;test_now=2900;c.boot_key_();boot_level=1;test_now=6100;c.boot_key_();assert(goats_step3_store::state().active==1);c.drain();\\n boot_level=0;test_now=6200;c.boot_key_();boot_level=1;test_now=9400;c.boot_key_();assert(goats_step3_store::state().active==0);c.drain();\\n puts("PASS:')
 (t/'test.cpp').write_text(code)''')
exec(compile(s,'step3_graphics','exec'),globals())
print('PASS: STEP2A renderer and full-window SPI unchanged; startup order, poll order and new BOOT hooks verified')
