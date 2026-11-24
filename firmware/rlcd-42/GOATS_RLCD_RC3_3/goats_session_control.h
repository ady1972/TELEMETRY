#pragma once
#include <cstdint>
namespace goats_session_ctl {
inline bool &paused(){static bool v=false;return v;}
inline bool &has_started(){static bool v=false;return v;}
inline uint32_t &last_moving_ms(){static uint32_t v=0;return v;}
inline uint32_t &auto_timeout_ms(){static uint32_t v=60000;return v;}
inline void observe(float speed,bool running){
 if(running)has_started()=true;
 if(running && speed>=3.0f)last_moving_ms()=millis();
}
inline void stop(){paused()=true;has_started()=false;}
inline void resume(){paused()=false;has_started()=false;last_moving_ms()=millis();}
}
