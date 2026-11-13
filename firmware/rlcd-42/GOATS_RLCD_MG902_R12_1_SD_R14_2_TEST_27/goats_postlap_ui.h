#pragma once
#include <cstdint>
#include <cmath>
#include <cstdio>
// Visual options, no GPS/UART writes. Driven by KEY and BOOT.
namespace goats_ui {
// Best Lap alert (independent of normal post-lap alert).
inline bool &best_enabled(){static bool v=true;return v;}
inline uint32_t &best_duration_ms(){static uint32_t v=3000;return v;}
inline uint32_t &best_until(){static uint32_t v=0;return v;}
inline uint32_t &best_time_ms(){static uint32_t v=0;return v;}
inline bool best_active(uint32_t now){return best_enabled() && best_until()!=0 && (int32_t)(best_until()-now)>0;}
inline uint8_t &mode(){static uint8_t v=2;return v;} // 0=OFF,1=POPUP,2=BLINK
inline uint8_t &content(){static uint8_t v=0;return v;} // 0=LAST+DELTA, 1=LAST only
inline uint32_t &duration_ms(){static uint32_t v=5000;return v;}
inline uint32_t &show_until(){static uint32_t v=0;return v;}
inline uint32_t &last_ms(){static uint32_t v=0;return v;}
inline float &last_delta(){static float v=NAN;return v;}
inline bool &settings(){static bool v=false;return v;}
inline uint8_t &cursor(){static uint8_t v=0;return v;}
inline bool active(uint32_t now){return mode()!=0 && show_until()!=0 && (int32_t)(show_until()-now)>0;}
inline bool lit(uint32_t now){return ((now/500U)&1U)==0;}
inline void capture(uint32_t now){
 // Consume once per record, whether notification is enabled or disabled.
 if(goats_laptimer_consume_new_best_event()){
   best_time_ms()=goats_laptimer_best_lap_ms();
   best_until()=best_enabled()?now+best_duration_ms():0;
 }
 if(!goats_laptimer_consume_lap_completed_event())return;
 last_ms()=goats_laptimer_last_lap_ms();
 last_delta()=goats_laptimer_post_lap_best_delta_seconds();
 show_until()=mode()?now+duration_ms():0;
}
inline void select(){if(settings())cursor()=(cursor()+1)%4;else {settings()=true;cursor()=0;}}
inline void change(){
 if(!settings())return;
 if(cursor()==0)mode()=(mode()+1)%3;
 else if(cursor()==1)duration_ms()=(duration_ms()==3000)?5000:(duration_ms()==5000)?10000:3000;
 else if(cursor()==2)content()=(content()+1)%2;
 else settings()=false;
}
}
