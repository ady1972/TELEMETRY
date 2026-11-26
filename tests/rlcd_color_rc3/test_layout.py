"""Execute both actual YAML renderers with ESPHome's real Font rasterizer on host.

Requires ESPHome 2026.7.3 and g++; optionally COLOR_PREVIEW_DIR for native PPMs.
No hand-drawn replacement screen is used for previews.
"""
from pathlib import Path
import os
import re
import subprocess
import tempfile
import yaml
import freetype
from esphome.components.font import glyph_to_glyphinfo, pt_to_px
import esphome
ROOT=Path(__file__).resolve().parents[2]
PORT=ROOT/'firmware/rlcd-42-3-colori/GOATS_RLCD_COLOR_RC3_3'
COMP=PORT/'components/goats_st7306'
class Loader(yaml.SafeLoader):pass
Loader.add_multi_constructor('!',lambda loader,tag,node:loader.construct_scalar(node))
mono=yaml.load((ROOT/'firmware/rlcd-42/goats_rlcd_rc3_3.yaml').read_text(),Loader=Loader)['display'][0]['lambda']
color=yaml.load((PORT.parent/'goats_42_color_rc3_3.yaml').read_text(),Loader=Loader)['display'][0]['lambda']
def normalize(text):
    text=text.replace('COLOR ${firmware_version}','RLCD ${firmware_version}')
    text=text.replace('FW: RLCD ${firmware_version}','FW: MG902 ${firmware_version}')
    text=text.replace('"SU/GIU: SCORRI  OK: CONFERMA  BACK: INDIETRO"',
      'page==8?"KEY: SCORRI/LUNGO ANNULLA  BOOT: OK": "KEY: AVANTI   BOOT: OK   BOOT LUNGO: INDIETRO"')
    text=re.sub(r'^const Color R\(255,0,0\);.*\n','',text,flags=re.M)
    # Only four named negative-delta background fills may use red ink.
    for call in ['it.filled_rectangle(1,133,185,64,R)','it.filled_rectangle(2,2,396,88,R)',
                 'it.filled_rectangle(left+1,top+1,width-2,height-2,R)','it.filled_rectangle(85,175,230,32,R)']:
        text=text.replace(call,call[:-2]+'W)')
    return text
assert normalize(color)==mono,'Unexpected layout or rendering change relative to RC3.3'
package=Path(esphome.__file__).parent
with tempfile.TemporaryDirectory() as temporary:
    tmp=Path(temporary)
    files={
      'esphome/core/color.h':'''#pragma once
#include <cstdint>
namespace esphome {
struct Color {
 union {struct {uint8_t r,g,b,w;};struct {uint8_t red,green,blue,white;};};
 Color(uint8_t rr=0,uint8_t gg=0,uint8_t bb=0,uint8_t ww=0):r(rr),g(gg),b(bb),w(ww){}
 bool is_on()const{return r||g||b||w;}
};
inline const Color COLOR_OFF(0,0,0),COLOR_ON(255,255,255);
}
''',
      'esphome/core/defines.h':'#pragma once\n#define USE_DISPLAY\n',
      'esphome/core/hal.h':'#pragma once\n#define progmem_read_byte(addr) (*(addr))\n',
      'esphome/core/log.h':'#pragma once\n#define ESP_LOGI(...) do{}while(0)\n#define ESP_LOGW(...) do{}while(0)\n',
      'esphome/core/datatypes.h':'''#pragma once
#include <cstddef>
namespace esphome {
template<typename T> class ConstVector {
 const T *data_;size_t size_;
 public:ConstVector(const T*d,size_t n):data_(d),size_(n){}
 size_t size()const{return size_;}bool empty()const{return !size_;}
 const T &operator[](size_t i)const{return data_[i];}
};}
''',
      'esphome/components/display/display.h':(ROOT/'tests/rlcd_color_rc3/layout_display.h').read_text(),
      'esphome/components/display/display_buffer.h':'#pragma once\n#include "display.h"\n',
      'esphome/components/spi/spi.h':'''#pragma once
#include <cstdint>
#include <cstddef>
namespace esphome::spi {
enum {BIT_ORDER_MSB_FIRST,CLOCK_POLARITY_LOW,CLOCK_PHASE_LEADING,DATA_RATE_4MHZ};
template<int,int,int,int>class SPIDevice {public:
void spi_setup(){}void enable(){}void disable(){}void write_byte(uint8_t){}void write_array(const uint8_t*,size_t){}
};}
''',
    }
    for name,data in files.items():
        p=tmp/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(data)
    source=['#pragma once','#include "esphome/components/font/font.h"']
    face=freetype.Face(str(PORT/'fonts/RobotoCondensed-Bold.ttf'))
    for size in (13,16,20,28,36,42,44,52,60,64,72,78,82):
        data=[];rows=[]
        for code in [*range(32,127),*range(160,256)]:
            g=glyph_to_glyphinfo(chr(code),face,size,1)
            offset=len(data);data.extend(g.bitmap_data)
            rows.append(f'{{{code},data_{size}+{offset},{g.advance},{g.offset_x},{g.offset_y},{g.width},{g.height}}}')
        source.append(f'inline const uint8_t data_{size}[]={{'+','.join(map(str,data))+'};')
        source.append(f'inline const esphome::font::Glyph glyphs_{size}[]={{'+','.join(rows)+'};')
        source.append(f'inline esphome::font::Font face_{size}(glyphs_{size},{len(rows)},{pt_to_px(face.size.ascender)},{pt_to_px(face.size.height)},{abs(pt_to_px(face.size.descender))},0,0,1);')
        source.append(f'inline auto *f{size}=&face_{size};')
    (tmp/'generated_fonts.h').write_text('\n'.join(source))
    rendered=[]
    for name,code in [('mono',mono),('color',color)]:
        code=code.replace('${firmware_version}','RC3.3')
        rendered.append('inline void render_'+name+'(esphome::display::DisplayBuffer &it){\n'+code+'\n}')
    (tmp/'generated_render.h').write_text('\n'.join(rendered))
    exe=tmp/'layout_test'
    subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-Wno-unused-variable','-Wno-unused-but-set-variable',
      '-fsanitize=address,undefined','-fno-omit-frame-pointer',
      '-I'+str(tmp),'-I'+str(package.parent),'-I'+str(ROOT/'tests/rlcd_color_rc3'),'-I'+str(COMP),
      str(package/'components/font/font.cpp'),str(COMP/'goats_st7306.cpp'),
      str(ROOT/'tests/rlcd_color_rc3/test_layout.cpp'),'-o',str(exe)],check=True)
    args=[str(exe)]
    if os.environ.get('COLOR_PREVIEW_DIR'):
        out=Path(os.environ['COLOR_PREVIEW_DIR']);out.mkdir(parents=True,exist_ok=True)
        args +=[str(out/'lap.ppm'),str(out/'delta.ppm')]
    subprocess.run(args,check=True)
print('PASS: entire render lambda matches RC3.3, except model/help text and negative red ink')
