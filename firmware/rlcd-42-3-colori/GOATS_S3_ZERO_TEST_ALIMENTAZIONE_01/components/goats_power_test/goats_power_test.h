#pragma once
#include "esphome/core/component.h"
#include "esphome/components/spi/spi.h"
#include <array>
#include <cstdint>

namespace esphome::goats_power_test {
class GoatsPowerTest : public PollingComponent,
    public spi::SPIDevice<spi::BIT_ORDER_MSB_FIRST, spi::CLOCK_POLARITY_LOW,
                         spi::CLOCK_PHASE_LEADING, spi::DATA_RATE_4MHZ> {
 public:
  void set_dc_pin(GPIOPin *pin) { dc_pin_ = pin; }
  void set_reset_pin(GPIOPin *pin) { reset_pin_ = pin; }
  void setup() override;
  void update() override;
  void dump_config() override;
  float get_setup_priority() const override { return setup_priority::HARDWARE; }

 protected:
  GPIOPin *dc_pin_{nullptr}, *reset_pin_{nullptr};
  static constexpr uint8_t WHITE = 0, BLACK = 1, RED = 2;
  std::array<uint8_t, 30000> framebuffer_{};
  int64_t counter_started_us_{0};
  int reset_reason_{0};
  const char *reset_label_{"SCONOSCIUTO"};
  void cmd_(uint8_t value);
  void data_(uint8_t value);
  void controller_init_();
  void pixel_(int x, int y, uint8_t color);
  void rect_(int x, int y, int w, int h, uint8_t color);
  void font_text_(int x, int y, const char *text, int size, uint8_t color, int align);
  void render_(uint64_t seconds);
  void flush_();
};
}  // namespace esphome::goats_power_test
