#pragma once
#include "esphome/core/component.h"
#include <Arduino.h>
#include <SPI.h>
#include "esphome/components/uart/uart.h"
namespace esphome { namespace goats_spi_diag {
class GoatsSpiDiag : public Component {
 public:
  void setup() override; void loop() override; void dump_config() override;
  void set_gps_uart(esphome::uart::UARTComponent *u){gps_uart_=u;}
 private:
  static constexpr int CS=10, DC=9, RES=8, SCLK=12, MOSI=11;
  static constexpr int W=300,H=400,TW=50,TH=200;
  static constexpr uint8_t WHITE=0,BLACK=1,RED=2;
  SPIClass spi_{HSPI};
  esphome::uart::UARTComponent *gps_uart_{nullptr};
  static constexpr int KEY_UP=4,KEY_DOWN=5,KEY_BACK=6,KEY_OK=7;
  int track_index_{-1},menu_item_{0},screen_{0};
  bool auto_track_{true},was_running_{false},gps_configured_{false};
  uint32_t last_gps_{0},last_keys_{0},last_ui_{0},last_circuit_scan_{0};
  uint8_t old_keys_{0x0F};
  void gps_poll_();void buttons_();void menu_draw_();void menu_action_();
  void clear_session_();void status_draw_();
  void choose_track_(int idx);
  uint8_t framebuffer_[W*H/4]{};  // 2 bit/pixel, 30,000 byte
  uint32_t started_{0}, heartbeat_{0},sim_start_{0},last_lap_{0},last_aux_{0},stat_start_{0};
  uint32_t updates_{0},bytes_{0},spi_us_{0},max_us_{0},missed_{0};
  uint8_t stage_{0}; bool redraw_{false};
  void cmd_(uint8_t); void data_(uint8_t);void controller_init_();
  void pixel_(int,int,uint8_t);void rect_(int,int,int,int,uint8_t);
  void border_(int,int,int,int,uint8_t);void text_(int,int,const char*,uint8_t,int);
  uint32_t region_(int,int,int,int,const char*);
  void font_text_(int,int,const char*,int,uint8_t,int);
  void speed_native_(int,int,const char*,uint8_t);
  void signed_delta_(int,int,const char*,int,uint8_t);
  void native_label_(int,int,const uint8_t*,int,int,uint8_t);
  void vertical_(int,int,const char*,uint8_t,int);void static_layout_();void lap_big_(int,int,const char*,uint8_t);
 void best_big_(int,int,uint8_t);void best_dynamic_(int,int,const char*,uint8_t);
 void clock_();void auxiliaries_();void calibration_();
}; }}
