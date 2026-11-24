#pragma once
#include <string>
#include "esphome/core/component.h"
#include "esphome/components/uart/uart.h"
#include "nav_pvt.h"
#include "uart_diagnostics.h"

namespace esphome::goats_core {
class GoatsCore : public Component, public uart::UARTDevice {
 public:
  void set_firmware_version(const std::string &version) { firmware_version_ = version; }
  void loop() override;
  void dump_config() override;
  const NavSample &latest_sample() const { return latest_; }
  bool has_sample() const { return has_sample_; }
  uint32_t sample_count() const { return sample_count_; }
  const NavPvtParser &diagnostics() const { return parser_; }
  const UartDiagnostics &uart_diagnostics() const { return uart_diagnostics_; }
  uint32_t uart_buffer_capacity() const {
    return parent_ == nullptr ? 0 : static_cast<uint32_t>(parent_->get_rx_buffer_size());
  }

 private:
  std::string firmware_version_;
  NavPvtParser parser_;
  UartDiagnostics uart_diagnostics_;
  NavSample latest_;
  uint32_t sample_count_{0};
  bool has_sample_{false};
};
}  // namespace esphome::goats_core
