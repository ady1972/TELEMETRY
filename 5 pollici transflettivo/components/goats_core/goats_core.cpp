#include "goats_core.h"
#include "esphome/core/hal.h"
#include "esphome/core/log.h"

namespace esphome::goats_core {
static const char *const TAG = "goats_core";
void GoatsCore::loop() {
  uint8_t byte;
  unsigned budget = 4096;  // RLCD reference: bound work per UART poll.
  while (budget-- && this->available()) {
    if (!this->read_byte(&byte)) break;
    NavSample sample;
    if (parser_.consume(byte, millis(), sample)) {
      latest_ = sample;
      has_sample_ = true;
      ++sample_count_;
      // Future timing/trace consumers belong here. No lap is simulated.
    }
  }
}
void GoatsCore::dump_config() {
  ESP_LOGCONFIG(TAG, "GOATS 5 transflettivo %s: scaffold, GNSS RX-only", firmware_version_.c_str());
  this->check_uart_settings(230400, 1, uart::UART_CONFIG_PARITY_NONE, 8);
}
}  // namespace esphome::goats_core
