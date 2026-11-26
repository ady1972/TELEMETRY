#pragma once
#include <cstdint>
#include <cstdio>
#include <vector>
inline uint32_t clock_ms=0;
inline std::vector<uint32_t> delays;
namespace esphome {
inline uint32_t millis(){return clock_ms;}
inline void delay(uint32_t ms){delays.push_back(ms);clock_ms+=ms;}
}
