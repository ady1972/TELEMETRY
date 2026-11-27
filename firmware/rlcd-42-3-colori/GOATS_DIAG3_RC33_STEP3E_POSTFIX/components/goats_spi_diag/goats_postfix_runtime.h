#pragma once
#ifdef GOATS_RC33_STEP1_IMPL
#include <cstdint>
// Startup-only isolation. Never switches receivers or changes GNSS parameters.
namespace goats_postfix {
enum Mode : uint8_t { GPS_ONLY=0, CORE_ONLY=1, FULL=2 };
inline Mode mode=FULL;
inline void set(uint8_t value){mode=static_cast<Mode>(value);}
inline const char* name(){return mode==GPS_ONLY?"GPS ONLY":mode==CORE_ONLY?"CORE ONLY":"FULL";}
inline bool full(){return mode==FULL;}
inline void prepare(){if(full())goats_lap_storage::begin();}
inline void start(){
 if(mode==GPS_ONLY){goats_gps_diag::frame_observer=nullptr;return;}
 goats_rc33_step1::attach();
 if(full())goats_step3::start();
}
inline void tick(){
 if(full())goats_step3::tick();
 if(mode!=GPS_ONLY)goats_ui::capture(::millis());
}
inline void record_toggle(){
 if(!full())return;
 if(goats_step3_store::state().active)goats_step3::stop();else goats_step3::free_start();
}
}
#endif
