#pragma once
#include <string>
#include <vector>
#include "esphome/core/component.h"
#include "esphome/components/uart/uart.h"
#include "goats_ubx_m9n_ak97_full.h"
namespace esphome::goats_diag3 {
class GoatsDiag3 : public Component, public uart::UARTDevice {
 public:
  void setup() override;
  void loop() override;
  void dump_config() override;
  std::string status_text() const;
  std::string visible_text() const;
  std::string used_text() const;
  std::string hdop_text() const;
  std::string speed_text() const;
  std::string stability_text() const;
  std::string transport_text() const;
  std::string age_text() const;
  bool position_valid() const;
 private:
  bool configured_{false};
  uint32_t started_{0}, last_log_{0};
  std::vector<goats_m9n::NavSample> batch_;
};
}
