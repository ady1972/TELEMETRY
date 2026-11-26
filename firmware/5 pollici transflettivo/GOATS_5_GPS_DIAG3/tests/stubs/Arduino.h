#pragma once
#include "esphome/core/hal.h"
inline uint32_t millis(){return esphome::millis();}
inline void delay(uint32_t ms){esphome::delay(ms);}
