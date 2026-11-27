#include "goats_st7306.h"
#include "pixel_pack.h"
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
void GoatsST7306::pixel_(int x, int y, uint8_t color) {
  pack_pixel(framebuffer_.data(), x, y, color);
}
void GoatsST7306::setup() {
  this->spi_setup(); dc_pin_->setup(); reset_pin_->setup();
  reset_pin_->digital_write(false); delay(200); reset_pin_->digital_write(true);
  controller_init_();
  framebuffer_.fill(0xCC); first_frame_=true;
}
void GoatsST7306::draw_absolute_pixel_internal(int x,int y,Color color) {
  const bool red=color.red>color.green && color.red>color.blue;
  pixel_(x,y,red?RED:((color.red||color.green||color.blue)?BLACK:WHITE));
}
void GoatsST7306::update() {
  this->do_update_();
  last_transfer_bytes_=last_windows_=0;
  // One complete composed frame per diagnostic update; no intermediate blank.
  cmd_(0x2A); data_(0x05); data_(0x36);
  cmd_(0x2B); data_(0); data_(199); cmd_(0x2C);
  dc_pin_->digital_write(true); this->enable();
  this->write_array(framebuffer_.data(),framebuffer_.size());
  this->disable(); last_transfer_bytes_=framebuffer_.size(); last_windows_=1;
  first_frame_=false;
}
}  // namespace esphome::goats_st7306
