#pragma once
#ifdef GOATS_RC33_STEP1_IMPL
#pragma once
// TEST D: adapts Manager GTC3 tracks and validated V3 samples to the original racing engine.
// No UART access; no GPS commands; no SD operations.
#include <cmath>
#include "rc33_goats_lap_speed_stats.h"
#include <vector>
#include <string>
#include "goats_track_types.h"
#include "goats_laptimer.h"
#include "rc33_goats_session_control.h"
namespace goats_racing {
inline GoatsTrackUsb &mapped(){static GoatsTrackUsb t;return t;}
inline bool &has_track(){static bool v=false;return v;}
inline int &last_index(){static int v=-999;return v;}
inline uint32_t &last_crc(){static uint32_t v=0;return v;}
inline void consume(bool valid,double lat,double lon,float speed,uint32_t itow){
 const auto &b=goats_b::state();
 const int index=b.active_track;
 const uint32_t crc=goats_step3_catalog::crc; // Cached on load/upload, not recomputed for each PVT.
 if(index!=last_index()||crc!=last_crc()){
   last_index()=index;last_crc()=crc;has_track()=false;
   goats_laptimer_reset();
   goats_lap_speed::reset();
   if(index>=0 && index<(int)b.tracks.size()){
     const auto &src=b.tracks[(size_t)index];auto &dst=mapped();
     dst.name=src.name;dst.start_lat=src.a;dst.start_lon=src.b;
     dst.finish_lat=src.c;dst.finish_lon=src.d;
     dst.trigger_radius_m=src.radius;dst.direction=src.direction;
     dst.sectors.clear();dst.sectors.reserve(src.sectors.size());
     for(const auto &sect:src.sectors){
       GoatsSectorUsb d;d.name=sect.name;d.lat1=sect.a;d.lon1=sect.b;
       d.lat2=sect.c;d.lon2=sect.d;dst.sectors.push_back(d);
     }
     has_track()=true;
   }
 }
 if(goats_session_ctl::paused())return;
 const bool was_running=goats_laptimer_running();
 const uint32_t prior_lap=goats_laptimer_lap_number();
 if(!was_running)goats_lap_speed::current()=0;
 if(was_running && valid)goats_lap_speed::observe(speed);
 goats_laptimer_update(has_track()?&mapped():nullptr,valid,lat,lon,speed,millis(),itow);
 if(was_running && goats_laptimer_lap_number()!=prior_lap && goats_laptimer_last_lap_ms()>0)
   goats_lap_speed::complete();
 goats_session_ctl::observe(speed,goats_laptimer_running());
}
}

#endif // GOATS_RC33_STEP1_IMPL
