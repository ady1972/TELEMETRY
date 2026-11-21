// Display-only extraction from V0.40.5: initialization, pixel mapping and local font.
#include "goats_power_test.h"
#include "goats_font_bitmap.h"
#include "esphome/core/log.h"
#include "esp_system.h"
#include "esp_timer.h"
#include <cstdio>

namespace esphome::goats_power_test {
static const char *const TAG = "goats_power_test";
void GoatsPowerTest::cmd_(uint8_t value) {
  dc_pin_->digital_write(false); this->enable(); this->write_byte(value); this->disable();
}
void GoatsPowerTest::data_(uint8_t value) {
  dc_pin_->digital_write(true); this->enable(); this->write_byte(value); this->disable();
}
void GoatsPowerTest::controller_init_() {
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

static int font_width_(const char* str,int size) {
 auto t=goats_font::table(size);int w=0;
 for(int i=0;str[i];i++)w+=t.g[goats_font::idx(str[i])].advance;
 return w;
}

void GoatsPowerTest::font_text_(int x,int y,const char* str,int size,uint8_t color,int align) {
 auto t=goats_font::table(size);int xx=x;
 const int w=font_width_(str,size);
 if(align==1)xx-=w/2;else if(align==2)xx-=w;
 for(int k=0;str[k];k++){
  const auto &g=t.g[goats_font::idx(str[k])];
  const uint8_t *pix=t.data+g.off;
  for(int yy=0;yy<g.h;yy++)for(int col=0;col<g.w;col++){
   int j=yy*g.w+col;
   if(pix[j>>3]&(0x80>>(j&7)))pixel_(xx+col,y+g.top+yy,color);
  }
  xx+=g.advance;
 }
}

void GoatsPowerTest::pixel_(int x,int y,uint8_t color) {
 if(x<0||x>=400||y<0||y>=300)return;
 const int px=299-y,py=x;
 const int idx=(py/2)*150+(px/2);
 const int parity_y=py&1,parity_x=px&1;
 const int bit1=7-(parity_x*4+parity_y);
 const int bit0=bit1-2;
 uint8_t c=(color==BLACK)?3:((color==RED)?1:2);
 const uint8_t mask=uint8_t((1U<<bit1)|(1U<<bit0));
 const uint8_t v=uint8_t((((c>>1)&1U)<<bit1)|((c&1U)<<bit0));
 framebuffer_[idx]=(framebuffer_[idx]&uint8_t(~mask))|v;
}

void GoatsPowerTest::rect_(int x,int y,int w,int h,uint8_t color){
 int x0=x<0?0:x,y0=y<0?0:y,x1=x+w>400?400:x+w,y1=y+h>300?300:y+h;
 for(int yy=y0;yy<y1;yy++)for(int xx=x0;xx<x1;xx++)pixel_(xx,yy,color);
}

static const char *reset_label(esp_reset_reason_t reason) {
  switch (reason) {
    case ESP_RST_POWERON: return "ACCENSIONE";
    case ESP_RST_EXT: return "RESET ESTERNO";
    case ESP_RST_SW: return "SOFTWARE";
    case ESP_RST_PANIC: return "PANIC";
    case ESP_RST_INT_WDT: return "INT WATCHDOG";
    case ESP_RST_TASK_WDT: return "TASK WATCHDOG";
    case ESP_RST_WDT: return "WATCHDOG";
    case ESP_RST_DEEPSLEEP: return "DEEP SLEEP";
    case ESP_RST_BROWNOUT: return "BROWNOUT";
    case ESP_RST_SDIO: return "SDIO";
    default: return "ALTRO/SCONOSCIUTO";
  }
}
void GoatsPowerTest::setup() {
  const auto reason = esp_reset_reason();
  reset_reason_ = static_cast<int>(reason);
  reset_label_ = reset_label(reason);
  this->spi_setup();
  dc_pin_->setup(); dc_pin_->digital_write(true);
  reset_pin_->setup(); reset_pin_->digital_write(true);
  // Same 200 ms reset pulse and controller delays as V0.40.5.
  reset_pin_->digital_write(false); delay(200); reset_pin_->digital_write(true);
  controller_init_();
  counter_started_us_ = esp_timer_get_time();
  render_(0); flush_();  // First frame without waiting for any peripheral or fix.
  ESP_LOGI(TAG, "TEST ALIMENTAZIONE 01: reset %s (%d)", reset_label_, reset_reason_);
}
void GoatsPowerTest::render_(uint64_t seconds) {
  rect_(0, 0, 400, 300, WHITE);
  font_text_(200, 12, "TEST ALIMENTAZIONE 01", 28, BLACK, 1);
  font_text_(200, 48, "ESP32-S3-ZERO / ST7306", 20, BLACK, 1);
  // Fixed color reference: white patch has a black border.
  rect_(12, 82, 120, 48, BLACK); rect_(14, 84, 116, 44, WHITE);
  rect_(140, 82, 120, 48, BLACK); rect_(268, 82, 120, 48, RED);
  font_text_(72, 98, "BIANCO", 16, BLACK, 1);
  font_text_(200, 98, "NERO", 16, WHITE, 1);
  font_text_(328, 98, "ROSSO", 16, WHITE, 1);
  char value[32];
  snprintf(value, sizeof(value), "%llu", static_cast<unsigned long long>(seconds));
  int size = 64;
  for (int candidate : {64, 60, 52, 44, 36, 28, 20, 16}) {
    size = candidate;
    if (font_width_(value, size) <= 376) break;
  }
  font_text_(200, 143, value, size, BLACK, 1);
  font_text_(200, 211, "SECONDI / RIPARTE DA ZERO AL RESET", 16, BLACK, 1);
  char reset[64];
  snprintf(reset, sizeof(reset), "RESET %d: %s", reset_reason_, reset_label_);
  font_text_(200, 239, reset, 16, BLACK, 1);
  font_text_(200, 270, "GPS SOLO VCC E GND / TX RX SCOLLEGATI", 16, BLACK, 1);
}
void GoatsPowerTest::flush_() {
  // Original full-screen region: 50 groups of 6 x 2 physical pixels per row.
  cmd_(0x2A); data_(0x05); data_(0x36);
  cmd_(0x2B); data_(0); data_(199); cmd_(0x2C);
  dc_pin_->digital_write(true); this->enable();
  this->write_array(framebuffer_.data(), framebuffer_.size()); this->disable();
}
void GoatsPowerTest::update() {
  // 64-bit monotonic time avoids the millis() wrap after about 49 days.
  const auto seconds = static_cast<uint64_t>((esp_timer_get_time() - counter_started_us_) / 1000000);
  render_(seconds); flush_();
  ESP_LOGI(TAG, "secondi=%llu reset=%s (%d)",
           static_cast<unsigned long long>(seconds), reset_label_, reset_reason_);
}
void GoatsPowerTest::dump_config() {
  ESP_LOGCONFIG(TAG, "TEST ALIMENTAZIONE 01, 4 MB, SPI 4 MHz, refresh 1 s");
  LOG_PIN("  DC: ", dc_pin_); LOG_PIN("  RESET: ", reset_pin_);
}
}  // namespace esphome::goats_power_test
