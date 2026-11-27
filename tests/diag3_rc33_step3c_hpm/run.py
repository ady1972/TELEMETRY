from pathlib import Path
import subprocess,tempfile,re,yaml
ROOT=Path(__file__).resolve().parents[2];BASE=ROOT/'firmware/rlcd-42-3-colori'
STEP=BASE/'GOATS_DIAG3_RC33_STEP3C_HPM/components/goats_spi_diag';OLD=BASE/'GOATS_DIAG3_RC33_STEP3/components/goats_spi_diag'
SIZES=[13,16,20,28,36,42,44,52,60,64,72,78,82]
for f in OLD.iterdir():
 if f.is_file() and f.name not in ['__init__.py','goats_spi_diag.cpp','goats_spi_diag.h']:
  assert (STEP/f.name).read_bytes()==f.read_bytes(),f.name
assert (STEP.parents[1]/'fonts/RobotoCondensed-Bold.ttf').read_bytes()==(OLD.parents[1]/'fonts/RobotoCondensed-Bold.ttf').read_bytes()
newconfig=yaml.safe_load((BASE/'goats_42_diag3_rc33_step3c_hpm.yaml').read_text());oldconfig=yaml.safe_load((BASE/'goats_42_diag3_rc33_step3.yaml').read_text())
for key in ['esp32','logger','uart']:assert newconfig[key]==oldconfig[key],key
assert newconfig['goats_spi_diag']['lcd_data_swap'] is True
assert newconfig['goats_spi_diag']['alignment_test'] is False
cpp=(STEP/'goats_spi_diag.cpp').read_text();old=(OLD/'goats_spi_diag.cpp').read_text()
def section(text,begin,end):return text[text.index(begin):text.index(end)]
for begin,end in [('void GoatsSpiDiag::pixel_(','void GoatsSpiDiag::rect_('),('uint32_t GoatsSpiDiag::region_(','static const uint8_t label_delta_original'),('void GoatsSpiDiag::gps_poll_()','void GoatsSpiDiag::menu_draw_()'),('void GoatsSpiDiag::setup()','void GoatsSpiDiag::loop()')]:
 assert section(cpp,begin,end)==section(old,begin,end),begin
init=section(cpp,'void GoatsSpiDiag::controller_init_()','#include "goats_font_bitmap.h"')
old_b=(BASE/'GOATS_DIAG3_RC33_STEP3B_SMOOTH/components/goats_spi_diag/goats_spi_diag.cpp').read_text()
normalized=init.replace('ESP_LOGI(TAG, "INIT: ST7306 %s, inizio",lcd_high_power_?"HPM 51Hz":"LPM");','ESP_LOGI(TAG, "INIT: sequenza ST7306 LPM, inizio");')
normalized=normalized.replace('  // ST7306 sections 8.2.3/8.2.23: HFRA=1 + OSC 0x80,E9 -> HPM 51Hz.\n  // Program once after sleep-out; never toggle power modes during RAMWR.\n  if(lcd_high_power_){cmd_(0xD8);data_(0x80);data_(0xE9);}', '')
normalized=normalized.replace('delay(400);\n\n','delay(400);\n').replace('cmd_(lcd_high_power_?0x38:0x39);','cmd_(0x39);')
assert normalized==section(old_b,'void GoatsSpiDiag::controller_init_()','#include "goats_font_bitmap.h"')
# Runtime, including every GPS/USB/storage call and display chunk, unchanged.
assert section(cpp,'void GoatsSpiDiag::loop()','void GoatsSpiDiag::alignment_draw_()')==section(old_b,'void GoatsSpiDiag::loop()','void GoatsSpiDiag::alignment_draw_()')
assert section(cpp,'void GoatsSpiDiag::racing_draw_()','// DIAG3 stability page')==section(old_b,'void GoatsSpiDiag::racing_draw_()','// DIAG3 stability page')
assert newconfig['goats_spi_diag']['lcd_high_power'] is True

# Execute the actual SPI/renderer/packing test from STEP2A with STEP3 hooks.
s=(ROOT/'tests/diag3_rc33_step2a/run.py').read_text();s=s[s.index('# Use the glyph'):]
a=s.index(' # Exercise real core');b=s.index(' # Production pixel packing',a);s=s[:a]+s[b:]
s=s.replace('goats-diag3-rc33-step2a','goats-rc33-step3c-hpm').replace('GOATS_DIAG3_RC33_STEP2A','GOATS_DIAG3_RC33_STEP3C_HPM')
# New alignment drawing uses the same pixel helpers and the original font objects.
extra=init+section(cpp,'void GoatsSpiDiag::alignment_draw_()','void GoatsSpiDiag::racing_draw_()')+section(cpp,'void GoatsSpiDiag::rect_(','void GoatsSpiDiag::text_(')
patch='''
 code=code.replace('struct GoatsSpiDiag {', 'namespace goats_step3_store {struct State{unsigned active=0;};inline State&state(){static State s;return s;}}\\nnamespace goats_step3 {inline bool free_start(){return true;}inline bool stop(){return true;}}\\n#define ESP_LOGI(...)\\nvoid delay(uint32_t ms){test_now+=ms;}\\nstruct GoatsSpiDiag {')
 code=code.replace(' static constexpr uint8_t WHITE=', ' bool lcd_data_swap_=true,alignment_test_=false,fast_display_=true,lcd_high_power_=false;\\n esphome::HighFrequencyLoopRequester display_loop_;\\n uint32_t frame_started_ms_=0,last_frame_ms_=0;\\n void controller_init_();void alignment_draw_();void rect_(int,int,int,int,uint8_t);void border_(int,int,int,int,uint8_t);\\n static constexpr uint8_t WHITE=')
 code=code.replace('int main(int argc,char**argv){', EXTRA+'\\nint main(int argc,char**argv){')
 code=code.replace(' GoatsSpiDiag c;', ' GoatsSpiDiag c;'+REGISTER_TEST)
 code=code.replace(' puts("PASS:', PERFORMANCE_TEST+'\\n'+ALIGNMENT_TEST+'\\n puts("PASS:')
 code=code.replace('largest=std::max<unsigned>(largest,n);++chunks;closed=false;', 'largest=std::max<unsigned>(largest,n);++chunks;closed=false;test_now+=(n*8+3999)/4000;')
 code=code.replace('assert(wire.cs_high&&sent_valid_', 'assert(!esphome::HighFrequencyLoopRequester::is_high_frequency());assert(wire.cs_high&&sent_valid_')
 code=code.replace('assert(c.flush_row_==200);', 'assert(c.flush_row_==200&&!esphome::HighFrequencyLoopRequester::is_high_frequency());')
 code=code.replace('assert(c.diagnostics_);', 'assert(c.diagnostics_&&!esphome::HighFrequencyLoopRequester::is_high_frequency());')
 (t/'test.cpp').write_text(code)
'''
s=s.replace(" (t/'test.cpp').write_text(code)",patch)
register_test='''
 wire.reset();c.fast_display_=false;c.lcd_data_swap_=false;c.controller_init_();const auto baseline=wire.commands;
 wire.reset();c.lcd_data_swap_=true;c.controller_init_();const auto corrected=wire.commands;
 assert(baseline.size()==corrected.size());unsigned changes=0;
 for(size_t i=0;i<baseline.size();i++)if(baseline[i]!=corrected[i]){++changes;assert(i>0&&baseline[i-1]==0x3A&&baseline[i]==0x111&&corrected[i]==0x101);}
 assert(changes==1);assert((0x01&1)==(0x11&1)); // BPS/24-bit SPI format retained.
 assert((0x01^0x11)==0x10); // Only the XDE bit changes.
 wire.reset();c.fast_display_=false;c.controller_init_();const auto slow_frc=wire.commands;
 wire.reset();c.fast_display_=true;c.controller_init_();const auto fast_frc=wire.commands;
 changes=0;for(size_t i=0;i<slow_frc.size();i++)if(slow_frc[i]!=fast_frc[i]){++changes;assert(i>0&&slow_frc[i-1]==0xB2&&slow_frc[i]==0x112&&fast_frc[i]==0x115);}
 assert(changes==1); // LFRA=2 (1Hz) -> LFRA=5 (8Hz), HPM selection preserved.

 // HPM uses a single explicit oscillator setup; all remaining init bytes match.
 wire.reset();c.lcd_high_power_=true;c.controller_init_();const auto high_frc=wire.commands;
 std::vector<uint16_t> expected;
 for(const auto v:fast_frc){
  expected.push_back(v==0x39?0x38:v);
  if(v==0x11){expected.push_back(0xD8);expected.push_back(0x180);expected.push_back(0x1E9);}
 }
 assert(high_frc==expected);
 assert(std::count(high_frc.begin(),high_frc.end(),0xD8)==1);
 assert(std::count(high_frc.begin(),high_frc.end(),0x38)==1);
 assert(std::count(high_frc.begin(),high_frc.end(),0x39)==0);
 // Diagnostic/test state changes do not reinitialize or toggle power modes.

 wire.reset();test_now=1000;
'''
alignment_test='''
 c.alignment_test_=true;c.racing_draw_();c.drain();
 assert(c.canvas_.has("STEP3C - PROVA HPM")&&c.canvas_.has("0123456789  GPS"));
 std::ofstream pic(out+"/alignment_expected.ppm",std::ios::binary);pic<<"P6\\n400 300\\n255\\n";
 for(int y=0;y<300;y++)for(int x=0;x<400;x++){
  int px=299-y,py=x,idx=(py/2)*150+px/2,bit=7-((px&1)*4+(py&1));
  unsigned value=((wire.panel[idx]>>bit)&1)*2+((wire.panel[idx]>>(bit-2))&1);
  if(value==3)pic.write("\\0\\0\\0",3);else if(value==1)pic.write("\\377\\0\\0",3);else pic.write("\\377\\377\\377",3);
 }
 pic.close();
'''
performance_test='''
 // Simulate the ESPHome 16ms component gate; SPI chunks are rounded to 5ms.
 goats_ui::show_until()=0;goats_ui::best_until()=0;
 auto duration=[&](bool fast){
  c.racing_cancel_();wire.reset();c.fast_display_=fast;c.alignment_test_=false;
  c.racing_draw_();assert(esphome::HighFrequencyLoopRequester::is_high_frequency()==fast);
  unsigned polls=0;
  while(c.flush_row_<200){
   ++polls; // Production loop calls gps_poll_ before each chunk (source checked).
   c.racing_flush_();
   if(c.flush_row_<200&&!esphome::HighFrequencyLoopRequester::is_high_frequency())test_now+=16;
  }
  assert(polls==13&&wire.payload.size()==30000&&wire.chunks==13&&wire.largest==2400);
  assert(!esphome::HighFrequencyLoopRequester::is_high_frequency());
  return c.last_frame_ms_;
 };
 const auto legacy=duration(false),rapid=duration(true);
 assert(legacy==255&&rapid==63&&rapid*3<legacy);
 printf("PASS: scheduler/SPI model: legacy %ums vs scoped fast loop %ums (not a hardware benchmark)\\n",legacy,rapid);
 // Cancel a partially transmitted frame and release the shared requester.
 c.racing_cancel_();c.fast_display_=true;c.racing_draw_();c.racing_flush_();
 assert(esphome::HighFrequencyLoopRequester::is_high_frequency());
 c.racing_cancel_();assert(!esphome::HighFrequencyLoopRequester::is_high_frequency());
 esphome::HighFrequencyLoopRequester other;other.start();c.racing_draw_();c.racing_cancel_();
 assert(esphome::HighFrequencyLoopRequester::is_high_frequency());other.stop();
 assert(!esphome::HighFrequencyLoopRequester::is_high_frequency());
'''
# Variables passed to the source fixture, not to production firmware.
helper_header=Path('/workspace/esphome-venv/lib/python3.12/site-packages/esphome/core/helpers.h').read_text()
helper_cpp=Path('/workspace/esphome-venv/lib/python3.12/site-packages/esphome/core/helpers.cpp').read_text()
requester_decl=helper_header[helper_header.index('class HighFrequencyLoopRequester {'):helper_header.index('/// Get the device MAC address',helper_header.index('class HighFrequencyLoopRequester {'))]
requester_impl=helper_cpp[helper_cpp.index('uint8_t HighFrequencyLoopRequester::num_requests'):helper_cpp.index('// get_mac_address,',helper_cpp.index('uint8_t HighFrequencyLoopRequester::num_requests'))]
extra='namespace esphome {\n'+requester_decl+requester_impl+'\n}\n'+extra
# Requester must be declared before the simulated controller, not just before main.
s=s.replace(" code=code.replace('struct GoatsSpiDiag {',", " code=code.replace('struct GoatsSpiDiag {', REQUESTER+")
# Keep the register test's controller init body from EXTRA but move its helper to the top.
extra=extra.removeprefix('namespace esphome {\n'+requester_decl+requester_impl+'\n}\n')
requester='namespace esphome {\n'+requester_decl+requester_impl+'\n}\n'
globals().update(EXTRA=extra,REGISTER_TEST=register_test,ALIGNMENT_TEST=alignment_test,REQUESTER=requester,PERFORMANCE_TEST=performance_test)

exec(compile(s,'step3c_hpm_graphics','exec'),globals())
from PIL import Image
for p in (STEP.parents[1]/'preview').glob('*.ppm'):Image.open(p).save(p.with_suffix('.png'));p.unlink()
print('PASS: HPM OSC 0x80/E9 + 0x38, exact LPM fallback, scoped requester lifecycle/timing, unchanged fonts/geometry/poll/USB/trace and complete SPI stream')

old_a=(BASE/'GOATS_DIAG3_RC33_STEP3A_LCD/components/goats_spi_diag/goats_spi_diag.cpp').read_text()
assert section(cpp,'void GoatsSpiDiag::gps_poll_()','void GoatsSpiDiag::menu_draw_()')==section(old_a,'void GoatsSpiDiag::gps_poll_()','void GoatsSpiDiag::menu_draw_()')
loop=section(cpp,'void GoatsSpiDiag::loop()','void GoatsSpiDiag::alignment_draw_()')
assert loop.index('gps_poll_();')<loop.index('goats_step3::tick();')<loop.index('racing_flush_();')

assert "(fast_display_?125u:100u)" in loop
