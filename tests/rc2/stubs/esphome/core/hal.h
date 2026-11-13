#pragma once
#include <cstdint>
inline uint32_t fake_millis=0;
namespace esphome { inline uint32_t millis(){return fake_millis;} }
