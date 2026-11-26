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
  bool manual{false}, blink_clock{false}, blink_delta{false}, lit{true}, delta_mode{false};
  std::string track;
};
class GoatsST7306 : public display::DisplayBuffer,
    public spi::SPIDevice<spi::BIT_ORDER_MSB_FIRST, spi::CLOCK_POLARITY_LOW,
                         spi::CLOCK_PHASE_LEADING, spi::DATA_RATE_4MHZ> {
 public:
  void set_dc_pin(GPIOPin *pin) { dc_pin_=pin; }
  void set_reset_pin(GPIOPin *pin) { reset_pin_=pin; }
  void setup() override;
  void update() override;
  void draw_racing(const RacingData &data);
  display::DisplayType get_display_type() override { return display::DisplayType::DISPLAY_TYPE_COLOR; }
  // COLOR_OFF/ON retain ESPHome's existing white/black drawing convention.
  void draw_absolute_pixel_internal(int x, int y, Color color) override;
  uint32_t last_transfer_bytes() const { return last_transfer_bytes_; }
  uint32_t last_windows() const { return last_windows_; }

 protected:
  int get_width_internal() override { return 400; }
  int get_height_internal() override { return 300; }
  GPIOPin *dc_pin_{nullptr}, *reset_pin_{nullptr};
  static constexpr uint8_t WHITE=0, BLACK=1, RED=2;
  std::array<uint8_t,30000> framebuffer_{};
  std::array<uint8_t,30000> sent_{};
  bool first_frame_{true};
  uint32_t last_transfer_bytes_{0}, last_windows_{0};
  void cmd_(uint8_t value);
  void data_(uint8_t value);
  void controller_init_();
  void pixel_(int x, int y, uint8_t color);
  void rect_(int x, int y, int w, int h, uint8_t color);
  void border_(int x, int y, int w, int h, uint8_t color);
  void text_(int x, int y, int w, int h, const char *text, int max_size, uint8_t color);
  void label_(int x, int y, const uint8_t *bits, int w, int h, uint8_t color);
};
}  // namespace esphome::goats_st7306
