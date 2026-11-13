#pragma once
// GOATS TEST27 - GPIO2 ESP32-S3 collegato fisicamente a RX del MG-902.
// GPIO2 NON e abilitato come TX UART: ingresso con pull-up interno debole.
// Nessuna trasmissione o inizializzazione GNSS.
#include "driver/gpio.h"

namespace goats_gpio2_pullup {
inline void init() {
  gpio_config_t cfg = {};
  cfg.pin_bit_mask = (1ULL << GPIO_NUM_2);
  cfg.mode = GPIO_MODE_INPUT;
  cfg.pull_up_en = GPIO_PULLUP_ENABLE;
  cfg.pull_down_en = GPIO_PULLDOWN_DISABLE;
  cfg.intr_type = GPIO_INTR_DISABLE;
  gpio_config(&cfg);
}
}  // namespace goats_gpio2_pullup
