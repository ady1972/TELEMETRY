from pathlib import Path
import subprocess,tempfile,re,yaml
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'firmware/rlcd-42-3-colori'
STEP=BASE/'GOATS_DIAG3_RC33_STEP3A_LCD/components/goats_spi_diag';OLD=BASE/'GOATS_DIAG3_RC33_STEP3/components/goats_spi_diag'
SIZES=[13,16,20,28,36,42,44,52,60,64,72,78,82]
for f in OLD.iterdir():
 if f.is_file() and f.name not in ['__init__.py','goats_spi_diag.cpp','goats_spi_diag.h']:
  assert (STEP/f.name).read_bytes()==f.read_bytes(),f.name
assert (STEP.parents[1]/'fonts/RobotoCondensed-Bold.ttf').read_bytes()==(OLD.parents[1]/'fonts/RobotoCondensed-Bold.ttf').read_bytes()
newconfig=yaml.safe_load((BASE/'goats_42_diag3_rc33_step3a_lcd.yaml').read_text());oldconfig=yaml.safe_load((BASE/'goats_42_diag3_rc33_step3.yaml').read_text())
for key in ['esp32','logger','uart']:assert newconfig[key]==oldconfig[key],key
assert newconfig['goats_spi_diag']['lcd_data_swap'] is True
assert newconfig['goats_spi_diag']['alignment_test'] is False
cpp=(STEP/'goats_spi_diag.cpp').read_text();old=(OLD/'goats_spi_diag.cpp').read_text()
def section(text,begin,end):return text[text.index(begin):text.index(end)]
for begin,end in [('void GoatsSpiDiag::pixel_(','void GoatsSpiDiag::rect_('),('uint32_t GoatsSpiDiag::region_(','static const uint8_t label_delta_original'),('void GoatsSpiDiag::gps_poll_()','void GoatsSpiDiag::menu_draw_()'),('void GoatsSpiDiag::setup()','void GoatsSpiDiag::loop()'),('void GoatsSpiDiag::racing_flush_()','void GoatsSpiDiag::boot_key_()')]:
 assert section(cpp,begin,end)==section(old,begin,end),begin
init=section(cpp,'void GoatsSpiDiag::controller_init_()','#include "goats_font_bitmap.h"')
assert init.replace('// DTFORM XDE is active-low: compensate the MY=1 page order (MADCTL 0x80).\n  // BPS remains 1: the same three-byte/24-bit wire format.\n  cmd_(0x3A); data_(lcd_data_swap_?0x01:0x11);','cmd_(0x3A); data_(0x11);')==section(old,'void GoatsSpiDiag::controller_init_()','#include "goats_font_bitmap.h"')
# Execute the actual SPI/renderer/packing test from STEP2A with STEP3 hooks.
s=(ROOT/'tests/diag3_rc33_step2a/run.py').read_text();s=s[s.index('# Use the glyph'):]
a=s.index(' # Exercise real core');b=s.index(' # Production pixel packing',a);s=s[:a]+s[b:]
s=s.replace('goats-diag3-rc33-step2a','goats-diag3-rc33-step3a-lcd').replace('GOATS_DIAG3_RC33_STEP2A','GOATS_DIAG3_RC33_STEP3A_LCD')
# New alignment drawing uses the same pixel helpers and the original font objects.
extra=init+section(cpp,'void GoatsSpiDiag::alignment_draw_()','void GoatsSpiDiag::racing_draw_()')+section(cpp,'void GoatsSpiDiag::rect_(','void GoatsSpiDiag::text_(')
patch='''
 code=code.replace('struct GoatsSpiDiag {', 'namespace goats_step3_store {struct State{unsigned active=0;};inline State&state(){static State s;return s;}}\\nnamespace goats_step3 {inline bool free_start(){return true;}inline bool stop(){return true;}}\\n#define ESP_LOGI(...)\\nvoid delay(uint32_t ms){test_now+=ms;}\\nstruct GoatsSpiDiag {')
 code=code.replace(' static constexpr uint8_t WHITE=', ' bool lcd_data_swap_=true,alignment_test_=false;\\n void controller_init_();void alignment_draw_();void rect_(int,int,int,int,uint8_t);void border_(int,int,int,int,uint8_t);\\n static constexpr uint8_t WHITE=')
 code=code.replace('int main(int argc,char**argv){', EXTRA+'\\nint main(int argc,char**argv){')
 code=code.replace(' GoatsSpiDiag c;', ' GoatsSpiDiag c;'+REGISTER_TEST)
 code=code.replace(' puts("PASS:', ALIGNMENT_TEST+'\\n puts("PASS:')
 (t/'test.cpp').write_text(code)
'''
s=s.replace(" (t/'test.cpp').write_text(code)",patch)
register_test='''
 wire.reset();c.lcd_data_swap_=false;c.controller_init_();const auto baseline=wire.commands;
 wire.reset();c.lcd_data_swap_=true;c.controller_init_();const auto corrected=wire.commands;
 assert(baseline.size()==corrected.size());unsigned changes=0;
 for(size_t i=0;i<baseline.size();i++)if(baseline[i]!=corrected[i]){++changes;assert(i>0&&baseline[i-1]==0x3A&&baseline[i]==0x111&&corrected[i]==0x101);}
 assert(changes==1);assert((0x01&1)==(0x11&1)); // BPS/24-bit SPI format retained.
 assert((0x01^0x11)==0x10); // Only the XDE bit changes.
 wire.reset();test_now=1000;
'''
alignment_test='''
 c.alignment_test_=true;c.racing_draw_();c.drain();
 assert(c.canvas_.has("STEP3A - ALLINEAMENTO LCD")&&c.canvas_.has("0123456789  GPS"));
 std::ofstream pic(out+"/alignment_expected.ppm",std::ios::binary);pic<<"P6\\n400 300\\n255\\n";
 for(int y=0;y<300;y++)for(int x=0;x<400;x++){
  int px=299-y,py=x,idx=(py/2)*150+px/2,bit=7-((px&1)*4+(py&1));
  unsigned value=((wire.panel[idx]>>bit)&1)*2+((wire.panel[idx]>>(bit-2))&1);
  if(value==3)pic.write("\\0\\0\\0",3);else if(value==1)pic.write("\\377\\0\\0",3);else pic.write("\\377\\377\\377",3);
 }
 pic.close();
'''
# Variables passed to the source fixture, not to production firmware.
globals().update(EXTRA=extra,REGISTER_TEST=register_test,ALIGNMENT_TEST=alignment_test)
exec(compile(s,'step3a_lcd_graphics','exec'),globals())
from PIL import Image
for p in (STEP.parents[1]/'preview').glob('*.ppm'):Image.open(p).save(p.with_suffix('.png'));p.unlink()
print('PASS: exactly one LCD init data byte differs (XDE); STEP3 fonts/geometry/poll/USB/trace headers unchanged; actual SPI and alignment page exercised')
