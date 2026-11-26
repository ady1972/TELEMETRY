#include "goats_st7306.h"
#include "pixel_pack.h"
#include "changed_regions.h"
#include "native_text.h"
#include "esphome/core/log.h"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>
namespace esphome::goats_st7306 {
static const char *const TAG = "goats_st7306";
void GoatsST7306::cmd_(uint8_t value) {
  dc_pin_->digital_write(false); this->enable(); this->write_byte(value); this->disable();
}
void GoatsST7306::data_(uint8_t value) {
  dc_pin_->digital_write(true); this->enable(); this->write_byte(value); this->disable();
}
void GoatsST7306::controller_init_() {
  ESP_LOGI(TAG, "INIT: sequenza ST7306 LPM, inizio");
  cmd_(0xD6); data_(0x17); data_(0x02);
  cmd_(0xD1); data_(0x01);
  cmd_(0xC0); data_(0x08); data_(0x00);
  cmd_(0xC1); for (int i=0;i<4;i++) data_(0x2C);
  cmd_(0xC2); for (int i=0;i<4;i++) data_(0x26);
  cmd_(0xC4); for (int i=0;i<4;i++) data_(0x42);
  cmd_(0xC5); for (int i=0;i<4;i++) data_(0x32);
  cmd_(0xB2); data_(0x12);
  const uint8_t b3[] = {0xE5,0xF6,0x05,0x46,0x77,0x77,0x77,0x77,0x76,0x45};
  cmd_(0xB3); for (uint8_t v : b3) data_(v);
  const uint8_t b4[] = {0x05,0x46,0x77,0x77,0x77,0x77,0x77,0x76,0x45};
  cmd_(0xB4); for (uint8_t v : b4) data_(v);
  cmd_(0xB7); data_(0x13);
  cmd_(0xB0); data_(0x64);
  cmd_(0xC9); data_(0x00);
  cmd_(0x11); delay(400);
  cmd_(0x36); data_(0x80);
  cmd_(0x3A); data_(0x11);
  cmd_(0xB9); data_(0x20);
  cmd_(0xB8); data_(0x09);
  cmd_(0xD0); data_(0xFF);
  cmd_(0x72); data_(0x13);
  cmd_(0x39);
  cmd_(0x29); delay(200);
  ESP_LOGI(TAG, "INIT: sequenza comandi trasmessa; nessun ACK LCD disponibile");
}
static const uint8_t label_delta_original[] = {0x00,0x00,0xE0,0x3F,0x87,0xBC,0x60,0xC6,0x04,0x60,0xC3,0xFC,0x3F,0x80,0x00,0x00,0x43,0x9C,0x7F,0x86,0x60,0x66,0x07,0xFC,0x7F,0xC0,0x00,0x00,0x07,0xFC,0x7F,0xC0,0x00,0x00,0x02,0x7C,0x67,0xC6,0x64,0x60,0xC6,0x0C,0x3F,0xC1,0xF8,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x0C,0x07,0xC3,0xF0,0x71,0x07,0x90,0x1F,0x80,0x3C,0x00,0x46,0x00,0x60,0x07,0xFC,0x7F,0xC6,0x00,0x60,0xC6,0x0C,0x00,0xC0,0x0C,0x7F,0xC7,0xFC,0x00,0x00,0x0C,0x64,0xC6,0x4C,0x64,0xC7,0xFC,0x7F,0xC0,0x00,0x00,0x01,0xF8,0x3F,0x86,0x0C,0x60,0xC6,0x0C,0x7F,0xC7,0xFC,0x00,0x00,0x00};
static const uint8_t label_best_original[] = {0x00,0x00,0x00,0x3C,0x07,0xE0,0x66,0x06,0x60,0x7F,0xC7,0xFC,0x00,0x00,0x00,0x00,0xC0,0x7C,0x3F,0x07,0x10,0x79,0x01,0xF8,0x03,0xC0,0x0C,0x00,0xC0,0x0C,0x00,0xC7,0xFC,0x7F,0xC0,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x06,0x00,0x60,0x07,0xFC,0x7F,0xC6,0x00,0x60,0x06,0x00,0x03,0x86,0x7C,0x66,0xC6,0xC4,0x7C,0xC3,0xCC,0x00,0x00,0x00,0x00,0xC6,0x4C,0x64,0xC6,0x4C,0x7F,0xC7,0xFC,0x00,0x00,0x00,0x3F,0xC7,0xFC,0x64,0xC6,0x4C,0x7F,0xC7,0xFC,0x00,0x00,0x00};
static const uint8_t label_lap_time[] = {0x00,0x00,0x00,0xC0,0x6C,0xC6,0xCC,0x6C,0xC6,0xFF,0xEF,0xFE,0x00,0x0F,0xFE,0xFF,0xEF,0xFE,0x7E,0x00,0x7E,0x01,0xE1,0xFC,0xFC,0x0F,0xFE,0xFF,0xE0,0x00,0x00,0x0F,0xFE,0xFF,0xE0,0x00,0xC0,0x0C,0x00,0xC0,0x0F,0xFE,0xFF,0xEC,0x00,0xC0,0x08,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x38,0x07,0xC0,0xC6,0x0C,0x60,0xC6,0x0F,0xFE,0xFF,0xE0,0x00,0x00,0x20,0x1E,0x1F,0xEF,0xF8,0xF1,0x8F,0xF8,0x1F,0xE0,0x1E,0x00,0x20,0x06,0x00,0x60,0x06,0x00,0x6F,0xFE,0xFF,0xE0,0x00};

void GoatsST7306::pixel_(int x, int y, uint8_t color) {
  pack_pixel(framebuffer_.data(), x, y, color);
}
void GoatsST7306::rect_(int x, int y, int w, int h, uint8_t color) {
  for (int yy=std::max(0,y); yy<std::min(300,y+h); ++yy)
    for (int xx=std::max(0,x); xx<std::min(400,x+w); ++xx) pixel_(xx,yy,color);
}
void GoatsST7306::border_(int x, int y, int w, int h, uint8_t color) {
  rect_(x,y,w,2,color); rect_(x,y+h-2,w,2,color);
  rect_(x,y,2,h,color); rect_(x+w-2,y,2,h,color);
}
void GoatsST7306::text_(int x, int y, int w, int h, const char *text, int max_size, uint8_t color) {
  native::draw(text,x,y,w,h,max_size,[&](int px,int py){pixel_(px,py,color);});
}
void GoatsST7306::label_(int x,int y,const uint8_t *bits,int w,int h,uint8_t color) {
  for (int yy=0; yy<h; ++yy) for (int xx=0; xx<w; ++xx) {
    const int at=yy*w+xx;
    if (bits[at/8] & (0x80>>(at&7))) pixel_(x+xx,y+yy,color);
  }
}
static std::string format_time(uint32_t ms) {
  if (!ms) return "--:--.---";
  char text[24];
  snprintf(text,sizeof(text),"%lu:%02lu.%03lu",static_cast<unsigned long>(ms/60000),
    static_cast<unsigned long>((ms/1000)%60),static_cast<unsigned long>(ms%1000));
  return text;
}
void GoatsST7306::draw_racing(const RacingData &data) {
  // Compose a complete frame in RAM; never send this clearing step to the LCD.
  rect_(0,0,400,300,WHITE);
  rect_(0,29,400,2,BLACK);
  char value[40];
  snprintf(value,sizeof(value),"GPS %u/%u",unsigned(data.used),unsigned(data.seen));
  text_(5,3,117,22,value,16,BLACK);
  std::string track=data.track;
  // Truncate complete UTF-8 codepoints only; do not squeeze glyphs to fit.
  while (!track.empty() && !native::fit(track.c_str(),264,22,16)) {
    size_t at=track.size()-1;
    while (at>0 && (static_cast<uint8_t>(track[at])&0xC0)==0x80) --at;
    track.resize(at);
  }
  text_(128,3,264,22,track.c_str(),16,BLACK);
  border_(1,33,227,137,BLACK);
  text_(10,36,95,18,"VELOCITA'",16,BLACK);
  const float speed=std::isfinite(data.speed) && data.speed>=3.f?data.speed:0.f;
  snprintf(value,sizeof(value),"%.1f",static_cast<double>(speed));
  text_(7,58,216,105,value,95,BLACK);

  const bool negative=std::isfinite(data.delta) && data.delta<0.f;
  char delta[24];
  if (std::isfinite(data.delta)) snprintf(delta,sizeof(delta),"%+.3f",static_cast<double>(data.delta));
  else snprintf(delta,sizeof(delta),"--.---");
  const bool clock_visible=!data.blink_clock || data.lit;
  const bool delta_visible=!data.blink_delta || data.lit;
  const auto lap=format_time(data.clock_ms);
  border_(230,33,169,75,BLACK);
  const uint8_t side_bg=!data.delta_mode && negative && delta_visible?RED:WHITE;
  const uint8_t side_ink=side_bg==RED?WHITE:BLACK;
  rect_(232,35,165,71,side_bg);
  label_(233,35,data.delta_mode?label_lap_time:label_delta_original,12,data.delta_mode?60:72,side_ink);
  if (data.delta_mode?clock_visible:delta_visible)
    text_(247,40,148,61,data.delta_mode?lap.c_str():delta,60,side_ink);

  border_(230,111,169,59,BLACK);
  label_(233,113,label_best_original,12,60,BLACK);
  const auto best=format_time(data.best_ms);
  text_(247,116,148,49,best.c_str(),60,BLACK);

  border_(1,173,398,80,BLACK);
  const uint8_t main_bg=data.delta_mode && negative && delta_visible?RED:WHITE;
  const uint8_t main_ink=main_bg==RED?WHITE:BLACK;
  rect_(3,175,394,76,main_bg);
  text_(9,175,90,14,data.delta_mode?"DELTA":"LAP TIME",13,main_ink);
  if (data.delta_mode?delta_visible:clock_visible)
    text_(6,190,388,60,data.delta_mode?delta:lap.c_str(),95,main_ink);

  for (int i=0; i<3; ++i) {
    border_(1+133*i,256,132,21,BLACK);
    if (std::isfinite(data.sectors[i])) snprintf(value,sizeof(value),"S%d %+.2f",i+1,static_cast<double>(data.sectors[i]));
    else snprintf(value,sizeof(value),"S%d --",i+1);
    text_(5+133*i,258,124,17,value,16,BLACK);
  }
  snprintf(value,sizeof(value),"GIRI %lu",static_cast<unsigned long>(data.laps));
  text_(5,280,140,18,value,16,BLACK);
  text_(260,280,134,18,data.manual?"MANUALE":"AUTO",16,BLACK);
}
void GoatsST7306::setup() {
  this->spi_setup(); dc_pin_->setup(); reset_pin_->setup();
  reset_pin_->digital_write(false); delay(200); reset_pin_->digital_write(true);
  controller_init_();
  framebuffer_.fill(0xCC); sent_.fill(0); first_frame_=true;
}
void GoatsST7306::draw_absolute_pixel_internal(int x,int y,Color color) {
  const bool red=color.red>color.green && color.red>color.blue;
  pixel_(x,y,red?RED:((color.red||color.green||color.blue)?BLACK:WHITE));
}
void GoatsST7306::update() {
  this->do_update_();
  last_transfer_bytes_=last_windows_=0;
  // Exactly one composed frame, then maximal dirty runs / coalesced rows.
  // No periodic panel reset, mode switch, blank flush or full-screen refresh.
  flush_changed(framebuffer_.data(),sent_.data(),first_frame_,[&](int left,int right,int top,int bottom){
    cmd_(0x2A); data_(0x05+left); data_(0x05+right-1);
    cmd_(0x2B); data_(top); data_(bottom-1); cmd_(0x2C);
    dc_pin_->digital_write(true); this->enable();
    for (int row=top; row<bottom; ++row) {
      const int length=(right-left)*3;
      this->write_array(framebuffer_.data()+row*150+left*3,length);
      last_transfer_bytes_+=length;
    }
    this->disable(); ++last_windows_;
  });
  first_frame_=false;
}
}  // namespace esphome::goats_st7306
