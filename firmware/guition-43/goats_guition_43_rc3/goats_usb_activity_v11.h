#pragma once
#include <cstdint>
namespace goats_usb_activity_v11 {
static uint32_t last_activity_ms = 0;
static inline void mark(uint32_t now_ms){ last_activity_ms = now_ms; }
static inline uint32_t last_ms(){ return last_activity_ms; }
}
