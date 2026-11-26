#pragma once
#include <cstdint>
namespace goats_sd_r14_bridge {
inline bool initialized=false,last_write_ok=false;
inline uint32_t writes=0,errors=0,last_ms=0;
inline void begin(){}
inline void save_lap(uint32_t,uint32_t,uint32_t,uint32_t,float,const char*){}
}
