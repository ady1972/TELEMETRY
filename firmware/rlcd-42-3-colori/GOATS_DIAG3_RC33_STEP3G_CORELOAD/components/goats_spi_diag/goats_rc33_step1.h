#pragma once
#ifdef GOATS_RC33_STEP1_IMPL
#include "goats_track_catalog.h"
#include "goats_ubx_m9n_ak97_full.h"
#include "goats_laptimer.h"
#include "rc33_goats_recording_clock.h"
#include "rc33_goats_session_control.h"
#include "rc33_goats_lap_speed_stats.h"
// Storage/export/trace and USB transport are intentionally not activated yet.
namespace goats_archive {inline void export_csv(){}}
namespace goats_gps_trace {
inline void on_pvt(const uint8_t*,bool,double,double,float,uint32_t,uint8_t,float,const char*){}
}
namespace goats_diag {inline float trace_hdop(){return goats_m9n::state.hdop;}}
#include "rc33_goats_test_b.h"
namespace goats_step3_catalog {inline uint32_t crc=0;}
#include "rc33_goats_racing_bridge.h"
namespace goats_rc33_step1 {
struct State {bool ready{false};uint32_t valid_samples{0};};
inline State &state(){static State s;return s;}
inline void on_frame(uint8_t cls,uint8_t id,const uint8_t *p,size_t n,uint32_t at){
 if(cls!=1 || id!=7 || n<92 || !state().ready)return;
 const uint32_t before=goats_b::state().pvt_samples;
 const uint32_t core_started=::micros();
 goats_b::on_pvt(p,static_cast<uint16_t>(n));
 const uint32_t core_us=::micros()-core_started;
 const auto &b=goats_b::state();
 if(b.pvt_samples!=before)goats_core_cache::timing.observe(core_us,at);
 if(b.pvt_samples!=before && b.fix_type>=3 && b.fix_ok && b.num_sv>=4 &&
    std::abs(b.lat)<=90 && std::abs(b.lon)<=180)++state().valid_samples;
}
inline void attach(){
 if(state().ready)return;
 auto &b=goats_b::state();
 // Reuse the catalog already loaded by DIAG3; no additional NVS/USB setup.
 b.tracks.reserve(goats_tracks::tracks.size());
 for(const auto &src:goats_tracks::tracks){
   goats_b::Track track;track.name=src.name;track.a=src.start_lat;track.b=src.start_lon;
   track.c=src.finish_lat;track.d=src.finish_lon;track.radius=src.trigger_radius_m;track.direction=src.direction;
   for(const auto &s:src.sectors)track.sectors.push_back({s.name,s.lat1,s.lon1,s.lat2,s.lon2});
   b.tracks.push_back(std::move(track));
 }
 goats_laptimer_reset();goats_lap_speed::reset();goats_session_ctl::resume();
 state().ready=true;
 goats_gps_diag::frame_observer=on_frame;
 // Do not call goats_b::setup/tick_usb or any SD, archive or Manager startup.
}
inline const char *line(){
 static char text[100];const auto &b=goats_b::state();
 std::snprintf(text,sizeof(text),"CORE RC3.3:%lu V:%lu G:%lu P:%u",
   (unsigned long)b.pvt_samples,(unsigned long)state().valid_samples,
   (unsigned long)goats_laptimer_lap_number(),(unsigned)b.tracks.size());
 return text;
}
} // namespace goats_rc33_step1
#endif // GOATS_RC33_STEP1_IMPL
