#pragma once

#include <string>

#include "esphome/components/uart/uart.h"
#include "esphome/core/component.h"

#include "gnss_diag.h"

namespace esphome::ubx_diag {

class UbxDiag : public Component, public uart::UARTDevice {
 public:
  void setup() override;
  void loop() override;
  void dump_config() override;
  float get_setup_priority() const override { return setup_priority::DATA; }

  void set_poll(bool poll) { this->poll_ = poll; }
  void set_expected(uint32_t rate_hz, uint32_t baud) {
    this->expected_rate_ = rate_hz;
    this->expected_baud_ = baud;
    this->diag_.set_expected(rate_hz, baud);
  }

  // Azzera le statistiche e ripete la lettura di versione e configurazione.
  void reset_statistics();

  // Valori per sensori e interfaccia
  float pvt_rate();
  float speed_kmh();
  float h_acc_m();
  int sv_used();
  uint32_t lost_epochs() { return this->diag_.lost_epochs(); }
  uint32_t checksum_errors() { return this->diag_.checksum_errors(); }
  int link_level();
  int fix_level();
  std::string fix_text();
  std::string link_text();
  std::string header_text();
  std::string speed_text();
  std::string sv_text();
  std::string fix_position_text();
  std::string fix_quality_text();
  std::string link_stats_text();
  std::string link_messages_text() { return this->diag_.link_messages_text(); }
  std::string sat_summary_text();
  std::string sat_list_text(int column);
  std::string module_text();
  std::string config_text() { return this->diag_.config_text(); }
  std::string system_text();

 protected:
  void poll_module_(uint32_t now);
  void send_poll_(uint8_t cls, uint8_t id);

  ubx::GnssDiag diag_;
  bool poll_{false};
  uint32_t expected_rate_{25};
  uint32_t expected_baud_{230400};
  uint32_t started_ms_{0};
  uint32_t last_loop_ms_{0};
  uint32_t last_poll_ms_{0};
  uint32_t last_cfg_ms_{0};
  uint32_t last_log_ms_{0};
  uint8_t poll_step_{0};
  bool warmed_up_{false};
};

}  // namespace esphome::ubx_diag
