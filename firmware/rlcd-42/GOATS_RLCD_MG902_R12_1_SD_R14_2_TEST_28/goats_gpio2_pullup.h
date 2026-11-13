#pragma once
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
}
