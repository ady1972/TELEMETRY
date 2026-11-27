#pragma once
#include "esphome/core/component.h"
#include "esphome/core/helpers.h"
#include <Arduino.h>
#include <SPI.h>
#include "esphome/components/display/display.h"
#include "esphome/components/font/font.h"
#include "esphome/components/uart/uart.h"
namespace esphome { namespace goats_spi_diag {
class GoatsSpiDiag : public Component {
 public:
  void setup() override; void loop() override; void dump_config() override;
  void set_gps_uart(esphome::uart::UARTComponent *u){gps_uart_=u;}
  void set_racing_font(unsigned i,esphome::font::Font *f){if(i<13)fonts_[i]=f;}
  void set_start_in_diagnostics(bool v){diagnostics_=v;}
  void set_delta_screen(bool v){delta_screen_=v;}
  void set_lcd_data_swap(bool value){lcd_data_swap_=value;}
  void set_alignment_test(bool value){alignment_test_=value;}
  void set_fast_display(bool value){fast_display_=value;}
  void set_lcd_high_power(bool value){lcd_high_power_=value;}
 private:
  bool lcd_data_swap_{true},alignment_test_{false},fast_display_{true},lcd_high_power_{true};
  esphome::HighFrequencyLoopRequester display_loop_;
  uint32_t frame_started_ms_{0},last_frame_ms_{0};
  void alignment_draw_();
  // Drawing adapter only: never registered as an ESPHome display/component.
  class Canvas : public esphome::display::Display {
   public:
    explicit Canvas(GoatsSpiDiag *owner):owner_(owner){}
    void update() override {}
    void draw_pixel_at(int x,int y,Color c) override {owner_->pixel_(x,y,c.is_on()?BLACK:WHITE);}
    esphome::display::DisplayType get_display_type() override {return esphome::display::DISPLAY_TYPE_BINARY;}
   protected:
    int get_width_internal() override {return 400;}
    int get_height_internal() override {return 300;}
    GoatsSpiDiag *owner_;
  };
  Canvas canvas_{this};
  esphome::font::Font *fonts_[13]{};
  bool diagnostics_{false},delta_screen_{false},boot_down_{false};
  uint32_t boot_since_{0},boot_changed_{0};
  uint8_t sent_frame_[30000]{};
  uint16_t flush_row_{200};
  bool sent_valid_{false};
  void racing_draw_();void racing_flush_();void racing_cancel_();void boot_key_();
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
  void gps_diag_draw_();
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
