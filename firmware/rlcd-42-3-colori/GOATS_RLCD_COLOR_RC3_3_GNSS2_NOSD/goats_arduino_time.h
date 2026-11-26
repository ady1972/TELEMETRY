#pragma once
#include "esphome/core/hal.h"

#ifdef USE_ARDUINO
// ESPHome's generated Arduino macros expand millis()/delay() to esphome::...
// Qualified calls in unchanged RC3.3 headers would expand to esphome::esphome::...
// Unique adapter names support both call styles and keep ESPHome's clock/delay.
namespace esphome {
inline uint32_t goats_hal_millis() { return (esphome::millis)(); }
inline void goats_hal_delay(uint32_t ms) { (esphome::delay)(ms); }
}
using esphome::goats_hal_millis;
using esphome::goats_hal_delay;
#undef millis
#define millis() goats_hal_millis()
#undef delay
#define delay(ms) goats_hal_delay(ms)
#endif
