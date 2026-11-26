#pragma once
// DIAG3 uses the Arduino global clock. On ESP-IDF all its callers share
// these same functions; do not mix this clock with a different epoch.
#include <cstdint>
#include <cstdio>
#include "esphome/core/hal.h"
inline uint32_t millis() { return esphome::millis(); }
inline void delay(uint32_t ms) { esphome::delay(ms); }
