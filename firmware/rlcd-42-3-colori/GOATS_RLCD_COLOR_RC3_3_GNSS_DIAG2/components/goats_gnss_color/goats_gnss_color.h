#pragma once
#include "esphome/core/component.h"
#include "esphome/components/uart/uart.h"
#include <cstdint>
#include <cstddef>

namespace esphome::goats_gnss_color {
// Public timestamps are all ESPHome ticks, for the unchanged RC3.3 UI/core.
// Private V0.40.5 parser timestamps remain Arduino millis, as in DIAG2.
struct State {
  uint32_t bytes{0},good{0},bad{0},last_pvt{0},last_sat{0},last_dop{0};
  uint32_t rate{38400},nmea_valid{0},last_valid{0};
  uint32_t cfg_ack{0},cfg_nak{0},poll_calls{0};
  bool locked{false},found_ubx{false};
  uint8_t seen{0},used{0},fix_type{0};
  float hdop{-1.f},pvt_hz{0.f},speed_kmh{0.f};
};
class GoatsGnssColor: public Component {
 public:
  using PvtCallback=void (*)(const uint8_t *,uint16_t);
  void set_gps_uart(uart::UARTComponent *bus){gps_uart_=bus;}
  void set_pvt_callback(PvtCallback callback){callback_=callback;}
  void setup() override;
  void enable(){enabled_=true;}
  void poll();
  State &data(){return data_;}
  bool configured() const{return configured_;}
 private:
  uart::UARTComponent *gps_uart_{nullptr};
  PvtCallback callback_{nullptr};
  State data_{};
  uint32_t started_ms_{0};
  bool enabled_{false},configured_{false};
  static GoatsGnssColor *active_;
  static void frame_(uint8_t cls,uint8_t id,const uint8_t *p,size_t n);
};
} // namespace esphome::goats_gnss_color
