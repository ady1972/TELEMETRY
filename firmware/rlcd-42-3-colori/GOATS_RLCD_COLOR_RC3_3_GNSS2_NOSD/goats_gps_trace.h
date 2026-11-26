#pragma once
#include <cstdint>
#include "goats_recording_time_runtime.h"
#include "goats_session_archive.h"
#include "goats_session_control.h"
#include "goats_recording_dates.h"
namespace goats_gps_trace {
// Preserve session dating, while removing the SD trace queue and file work.
inline void on_pvt(const uint8_t *,bool valid,double,double,float,uint32_t,
                   uint8_t,float,const char *){
  if(valid && !goats_session_ctl::paused() && goats_session_ctl::has_started())
    goats_dates::capture(goats_archive::session(),goats_clock::latest);
}
inline void tick(){goats_clock_runtime::tick();goats_dates::tick();}
inline bool &recording(){static bool value=false;return value;}
inline bool drain_for_save(){return true;}
inline void finish(bool){}
}
