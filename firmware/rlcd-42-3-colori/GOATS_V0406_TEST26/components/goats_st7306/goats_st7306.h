#pragma once
#include "esphome/components/display/display_buffer.h"
#include "esphome/components/spi/spi.h"
#include <array>
#include <string>
namespace esphome::goats_st7306 {
struct RacingData {
 uint32_t clock_ms{0}, laps{0}, best_ms{0};
 float delta{0}, speed{0};
 std::array<float,3> sectors{};
 uint8_t used{0}, seen{0};
 bool manual{false}, blink_clock{false}, blink_delta{false}, lit{true};
 std::string track, best;
};
class GoatsST7306 : public display::DisplayBuffer,
    public spi::SPIDevice<spi::BIT_ORDER_MSB_FIRST, spi::CLOCK_POLARITY_LOW, spi::CLOCK_PHASE_LEADING, spi::DATA_RATE_4MHZ> {
 public:
  void set_dc_pin(GPIOPin *pin) { dc_pin_=pin; }
  void set_reset_pin(GPIOPin *pin) { reset_pin_=pin; }
  void setup() override;
  void update() override;
  void draw_racing(const RacingData &data);
  display::DisplayType get_display_type() override { return display::DisplayType::DISPLAY_TYPE_COLOR; }
 protected:
  int get_width_internal() override { return 400; }
  int get_height_internal() override { return 300; }
  void draw_absolute_pixel_internal(int x,int y,Color color) override;
  GPIOPin *dc_pin_, *reset_pin_;
  static constexpr int TW=50, TH=200;
  static constexpr uint8_t WHITE=0, BLACK=1, RED=2;
  std::array<uint8_t,30000> framebuffer_{};
  std::array<uint8_t,30000> sent_{};
  bool first_frame_{true};
  RacingData racing_;
  void cmd_(uint8_t); void data_(uint8_t); void controller_init_();
  void pixel_(int,int,uint8_t); void rect_(int,int,int,int,uint8_t);
  void border_(int,int,int,int,uint8_t); void text_(int,int,const char*,uint8_t,int);
  uint32_t region_(int,int,int,int,const char*) { return 0; }
  void status_draw_();
  void font_text_(int,int,const char*,int,uint8_t,int);
  void speed_native_(int,int,const char*,uint8_t);
  void signed_delta_(int,int,const char*,int,uint8_t);
  void native_label_(int,int,const uint8_t*,int,int,uint8_t);
  void vertical_(int,int,const char*,uint8_t,int);void static_layout_();void lap_big_(int,int,const char*,uint8_t);
 void best_big_(int,int,uint8_t);void best_dynamic_(int,int,const char*,uint8_t);
 void clock_();void auxiliaries_();void calibration_();
};
}
