from pathlib import Path
import os
import subprocess
import tempfile
ROOT=Path(__file__).resolve().parents[2]
COMP=ROOT/'firmware/rlcd-42-3-colori/GOATS_RLCD_COLOR_RC3_3/components/goats_st7306'
with tempfile.TemporaryDirectory() as tmp:
 t=Path(tmp)
 files={
 'esphome/components/display/display_buffer.h':'''#pragma once
#include <cstdint>
#include <functional>
namespace esphome {
struct Color {uint8_t red,green,blue;Color(uint8_t r,uint8_t g,uint8_t b):red(r),green(g),blue(b){}};
class GPIOPin {public:void setup(){} void digital_write(bool){}};
inline void delay(int){}
namespace display {
enum class DisplayType {DISPLAY_TYPE_COLOR};
class DisplayBuffer {public:
std::function<void()> writer;
virtual void setup(){} virtual void update(){}
virtual DisplayType get_display_type()=0;
virtual void draw_absolute_pixel_internal(int,int,Color)=0;
protected:
virtual int get_width_internal()=0;virtual int get_height_internal()=0;
void do_update_(){writer();}
};}}
''',
 'esphome/components/spi/spi.h':'''#pragma once
#include <cstddef>
#include <cstdint>
namespace esphome::spi {
enum {BIT_ORDER_MSB_FIRST,CLOCK_POLARITY_LOW,CLOCK_PHASE_LEADING,DATA_RATE_4MHZ};
template<int,int,int,int>class SPIDevice {public:
void spi_setup(){} void enable(){} void disable(){}
void write_byte(uint8_t){} void write_array(const uint8_t*,size_t){}
};}
''',
 'esphome/core/log.h':'''#pragma once
#define ESP_LOGI(...) do{}while(0)
'''}
 for name,contents in files.items():
  p=t/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(contents)
 exe=t/'display_tests'
 subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-Wno-unused-variable',
  '-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(t),'-I'+str(COMP),
  str(COMP/'goats_st7306.cpp'),str(ROOT/'tests/rlcd_color_rc3/test_display.cpp'),'-o',str(exe)],check=True)
 args=[str(exe)]
 if os.environ.get('COLOR_PREVIEW_DIR'):
  out=Path(os.environ['COLOR_PREVIEW_DIR']);out.mkdir(parents=True,exist_ok=True)
  args +=[str(out/'lap.ppm'),str(out/'delta.ppm')]
 subprocess.run(args,check=True)
print('PASS: real driver and native renderer under ASan/UBSan; no unchanged-group writes,')
print('coalesced SPI windows, glyph bounds/ink, UTF-8, screen mode, blink and static pages')
