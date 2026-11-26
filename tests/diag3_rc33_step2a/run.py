"""Regression of confirmed STEP1 plus RC3.3 renderer and bounded SPI transfers."""
from pathlib import Path
import subprocess, tempfile,re,yaml,sys,hashlib
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'firmware/rlcd-42-3-colori'
STEP=BASE/'GOATS_DIAG3_RC33_STEP2A/components/goats_spi_diag'
OLD=BASE/'GOATS_DIAG3_RC33_STEP1/components/goats_spi_diag'
REF=ROOT/'firmware/rlcd-42/goats_rlcd_rc3_3.yaml'
SIZES=[13,16,20,28,36,42,44,52,60,64,72,78,82]
# The existing host tests use the actual single-reader gps_poll_ body. Re-run
# on STEP2A without changing the stable STEP1 tests or their reference firmware.
runner=(ROOT/'tests/diag3_rc33_step1/run.py').read_text()
runner=runner.replace("STEP=BASE/'GOATS_DIAG3_RC33_STEP1/components/goats_spi_diag'","STEP=BASE/'GOATS_DIAG3_RC33_STEP2A/components/goats_spi_diag'")
runner=runner.replace("BASE/'goats_42_diag3_rc33_step1.yaml'","BASE/'goats_42_diag3_rc33_step2a.yaml'")
runner=runner.replace("['esphome','external_components']","['esphome','external_components','goats_spi_diag']")
runner=runner.replace("'__init__.py','goats_spi_diag.h',",'')
runner=runner.replace('"DIAG3 + RC3.3 STEP1"','"DIAG3 + RC3.3 STEP2A"')
for n in ['goats_gps_diag.h','goats_rc33_step1.h','goats_track_catalog.h','goats_laptimer.h','rc33_goats_test_b.h','rc33_goats_racing_bridge.h']:
 assert (STEP/n).read_bytes()==(OLD/n).read_bytes(),n
ref=REF.read_text()
expected=ref[ref.index('      // Barra inferiore:'):ref.index('\n\n\n\ninterval:')]
expected='\n'.join(l[6:] if l.startswith('      ') else l for l in expected.splitlines())
expected=expected.replace('goats_screen_mode::delta()','screen_delta_mode').replace(' && goats_menu::screen()==0','')
for i,s in enumerate(SIZES):expected=expected.replace(f'id(f{s})',f'fonts[{i}]')
a=expected.index('if(id(bat_percent).has_state()');b=expected.index('// Delta live',a)
expected=expected[:a]+'// Battery level deliberately unknown: no ADC or power wiring assumed.\n'+expected[b:]
actual=(STEP/'goats_racing_step2.h').read_text()
assert actual[actual.index('// Barra inferiore:'):actual.rindex('\n}\n}')]==expected,'RC3.3 Racing body parity'
post=(STEP/'rc33_goats_postlap_ui.h').read_text()
assert post.removeprefix('#pragma once\n#ifdef GOATS_RC33_STEP1_IMPL\n').removesuffix('\n#endif // GOATS_RC33_STEP1_IMPL\n')==(ROOT/'firmware/rlcd-42/GOATS_RLCD_RC3_3/goats_postlap_ui.h').read_text()
config=yaml.safe_load((BASE/'goats_42_diag3_rc33_step2a.yaml').read_text())
assert config['goats_spi_diag']['start_in_diagnostics'] is False
for size,entry in zip(SIZES,config['font']):
 assert entry['size']==size and entry['bpp']==1 and entry['id']==f'f{size}'
 assert entry['file'].endswith('fonts/RobotoCondensed-Bold.ttf')
cpp=(STEP/'goats_spi_diag.cpp').read_text()
loop=cpp[cpp.index('void GoatsSpiDiag::loop()'):cpp.index('void GoatsSpiDiag::racing_draw_()')]
assert loop.index('gps_poll_();')<loop.index('goats_ui::capture')<loop.index('racing_flush_();')
assert 'goats_b::tick_usb' not in loop and 'delay(' not in loop[loop.index('if(stage_!=7)return;'):]
assert not set(config)&{'sensor','binary_sensor','display','interval','spi','wifi','ota','api','web_server','psram'}
print('PASS: unchanged GNSS/core paths, original RC3.3 Racing body/fonts/post-lap source, GPS polled before bounded SPI stream chunk')

# Use the glyph bitmap data actually emitted by ESPHome for this firmware.
main=(BASE/'.esphome/build/goats-diag3-rc33-step2a/src/main.cpp').read_text()
with tempfile.TemporaryDirectory(prefix='step2a-graphics-') as tmp:
 t=Path(tmp);data=[];init=[]
 for i,size in enumerate(SIZES):
  args=re.search(r'new\(f'+str(size)+r'\) font::Font\(([^;]+)\);',main).group(1)
  glyphname=args.split(',')[0]
  glyph=re.search(r'static const font::Glyph '+glyphname+r'\[\] = .*?;',main).group(0)
  bitmapname=re.search(r'\((\w+) \+ 0\)',glyph).group(1)
  bitmap=re.search(r'(?:static )?constexpr uint8_t '+bitmapname+r'\[\].*?= \{.*?\};',main,re.S).group(0)
  bitmap=bitmap.replace('PROGMEM','')
  data.extend([bitmap,glyph]);init.append(f'static font::Font f{size}({args});')
 (t/'glyphs.h').write_text('\n'.join(data+init)+ '\nfont::Font *fonts[]={'+','.join('&f'+str(s) for s in SIZES)+'};\n')
 # Exercise real core + real renderer in the same translation unit, using
 # the original UART/parser fixture while font drawing occurs every fifth PVT.
 integrated=(ROOT/'tests/diag3_rc33_step1/test_core.cpp').read_text()
 integrated=integrated.replace('#include <cassert>', '#include "graphics.h"\nusing namespace esphome;\n#include "glyphs.h"\n#include "rc33_goats_postlap_ui.h"\n#include "goats_racing_step2.h"\n#include <cassert>')
 integrated=integrated.replace(' std::cout<<"PASS:', '\n const uint32_t initial_count=b.pvt_samples;\n esphome::display::Display canvas;\n for(unsigned i=1;i<=250;i++){\n  const uint32_t now=70000+i*40;\n  feed(u,packet(now,45.001,9.0,84),now);\n  goats_ui::capture(::millis());\n  if(i%5==0){goats_step2_render::draw(canvas,fonts,now,false);assert(canvas.has("84"));}\n }\n assert(b.pvt_samples==initial_count+250 && goats_gps_diag::stability.pvt_fresh(::millis()));\n assert(usb_installs==0 && usb_reads==0 && usb_writes==0 && nvs_calls==0);\n std::cout<<"PASS:')
 runner=runner.replace("source.read_text().replace('ACTUAL_GPS_POLL',poll_body)","integrated_source.replace('ACTUAL_GPS_POLL',poll_body)")
 runner=runner.replace("'-I'+str(STEP),str(t/'test.cpp')","'-I'+str(STEP),'-I'+GRAPHICS_DIR,'-I'+GENERATED_DIR,str(t/'test.cpp')")
 exec(compile(runner,str(ROOT/'tests/diag3_rc33_step1/run.py'),'exec'),{'__file__':str(ROOT/'tests/diag3_rc33_step1/run.py'),'integrated_source':integrated,'GRAPHICS_DIR':str(ROOT/'tests/diag3_rc33_step2a'),'GENERATED_DIR':str(t)})
 # Production pixel packing, bounded flush and BOOT actions are exercised directly.
 def method(start,end):return cpp[cpp.index(start):cpp.index(end)]
 methods=method('void GoatsSpiDiag::racing_draw_()','// DIAG3 stability page')
 pixel=method('void GoatsSpiDiag::pixel_(','void GoatsSpiDiag::rect_(')
 wire=method('void GoatsSpiDiag::cmd_(','void GoatsSpiDiag::controller_init_()')+method('uint32_t GoatsSpiDiag::region_(','static const uint8_t label_delta_original')
 code=(ROOT/'tests/diag3_rc33_step2a/test_render.cpp').read_text().replace('ACTUAL_FLUSH_AND_BOOT',methods).replace('ACTUAL_PIXEL',pixel).replace('ACTUAL_WIRE',wire)
 (t/'test.cpp').write_text(code)
 subprocess.run(['g++','-std=c++17','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(t),'-I'+str(STEP),'-I'+str(ROOT/'tests/diag3_rc33_step2a'),str(t/'test.cpp'),'-o',str(t/'render')],check=True)
 out=ROOT/'firmware/rlcd-42-3-colori/GOATS_DIAG3_RC33_STEP2A/preview';out.mkdir(exist_ok=True)
 subprocess.run([str(t/'render'),str(out)],check=True)
 # PGM -> PNG for review; nearest-neighbour output keeps native 1-bit pixels.
 from PIL import Image
 for pgm in out.glob('*.pgm'):
  Image.open(pgm).save(pgm.with_suffix('.png'));pgm.unlink()
print('PASS: actual ESPHome glyphs, Racing both modes, fresh/stale GPS, best-lap overlay, packing, full-window wire parity and chunk cap and BOOT page transitions')
