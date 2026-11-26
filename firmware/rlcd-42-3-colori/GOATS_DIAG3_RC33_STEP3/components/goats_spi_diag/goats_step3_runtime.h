#pragma once
#ifdef GOATS_RC33_STEP1_IMPL
#include "goats_step3_store.h"
#include "goats_step3_usb.h"
namespace goats_step3 {
struct State {bool started=false,free_pending=false,free_mode=false,closing=false;uint32_t moving=0;};
inline State&state(){static State s;return s;}
inline bool moving(){const auto&m=goats_gps_diag::stability;return m.pvt_fresh(::millis())&&m.fix_active&&goats_m9n::state.speed_kmh>=3;}
inline void reset_engine(){
 auto&b=goats_b::state();goats_laptimer_reset();goats_lap_speed::reset();
 b.running=false;b.have_prev=false;b.laps=0;b.armed=true;b.last_lap=b.best_lap=0;b.last_cross=0;
}
inline void catalog_changed(){
 auto&b=goats_b::state();b.active_track=-1;b.manual_track=false;b.auto_candidate=-1;b.auto_hits=0;
 goats_step3_catalog::crc=b.raw.empty()?0:goats_b::crc32(b.raw.data(),b.raw.size());
 goats_racing::last_index()=-999;reset_engine();goats_session_ctl::resume();
}
inline bool arm(){if(!goats_step3_store::idle()||moving())return false;state().free_pending=false;state().free_mode=false;reset_engine();goats_session_ctl::resume();return true;}
inline bool free_start(){if(!goats_step3_store::can_begin()||moving()||goats_step3_usb::state().file||goats_step3_usb::state().raw_tx||goats_step3_usb::state().listing)return false;arm();state().free_pending=true;state().moving=::millis();return true;}
inline bool stop(){
 auto&s=state();auto&m=goats_step3_store::state();
 if(moving()||(!m.active&&!s.free_pending&&!goats_session_ctl::has_started()))return false;
 s.free_pending=false;goats_step3_store::stop();goats_session_ctl::stop();reset_engine();s.closing=true;return true;
}
inline const char *status(){
 static char line[260];const auto&b=goats_b::state();const auto&m=goats_step3_store::state();
 snprintf(line,sizeof(line),"GREC_STATUS USB=%u TRACKS=%u ACTIVE=%d PVT=%lu REC=%u READY=%u PTS=%lu DROP=%lu FREE=%lu G=%lu LAST=%lu BEST=%lu STATE=%s",goats_step3_usb::state().ready,(unsigned)b.tracks.size(),b.active_track,(unsigned long)b.pvt_samples,m.active!=0,m.ready&&!m.erasing,(unsigned long)(m.count?m.sessions[m.count-1].points:0),(unsigned long)(m.active?m.dropped:m.last_dropped),(unsigned long)(m.partition?m.partition->size-m.next:0),(unsigned long)goats_laptimer_lap_number(),(unsigned long)goats_laptimer_last_lap_ms(),(unsigned long)goats_laptimer_best_lap_ms(),m.stage);return line;
}
inline void on_frame(uint8_t cls,uint8_t id,const uint8_t*p,size_t n,uint32_t at){
 const auto before=goats_b::state().pvt_samples;
 goats_rc33_step1::on_frame(cls,id,p,n,at);
 auto&b=goats_b::state();if(b.pvt_samples==before)return;
 const bool valid=b.fix_type>=3&&b.fix_ok&&b.num_sv>=4&&fabs(b.lat)<=90&&fabs(b.lon)<=180;
 if(!valid){b.auto_candidate=-1;b.auto_hits=0;return;}
 auto&s=state();auto&m=goats_step3_store::state();
 if(b.speed>=3)s.moving=::millis();
 const bool transport_busy=goats_step3_usb::state().file||goats_step3_usb::state().raw_tx||goats_step3_usb::state().listing||b.receiving;
 if(!m.active&&!transport_busy&&!goats_session_ctl::paused()&&(s.free_pending||goats_session_ctl::has_started())){
  const char *name=s.free_pending?"REGISTRAZIONE LIBERA":(b.active_track>=0&&b.active_track<int(b.tracks.size())?b.tracks[b.active_track].name.c_str():"AUTO");
  if(goats_step3_store::begin(name,goats_clock::latest,b.last_sample_itow,s.free_pending)){s.free_mode=s.free_pending;s.free_pending=false;s.moving=::millis();}
 }
 const float hdop=goats_gps_diag::stability.dop_fresh(::millis())?goats_m9n::state.hdop:-1;
 goats_step3_store::observe(b.last_sample_itow,s.free_mode?0:goats_laptimer_lap_number(),goats_b::i32(p+28),goats_b::i32(p+24),b.speed,hdop,b.num_sv,b.fix_type);
}
inline void start(){
 auto&s=state();if(s.started)return;s.started=true;
 // Original GNSS setup/attach already completed. Load the catalog bytes once
 // for Manager round-trip; never install another UART or invoke legacy setup.
 auto&b=goats_b::state();nvs_handle_t h;
 if(nvs_open("goats_tracks",NVS_READONLY,&h)==ESP_OK){
  size_t n=0;if(nvs_get_blob(h,"catalog",nullptr,&n)==ESP_OK&&n>=8&&n<=60000){
   std::vector<uint8_t>raw(n);uint32_t crc=0;std::vector<goats_b::Track>tracks;
   const bool have_crc=nvs_get_u32(h,"catalog_crc",&crc)==ESP_OK;
   if(nvs_get_blob(h,"catalog",raw.data(),&n)==ESP_OK&&(!have_crc||goats_b::crc32(raw.data(),raw.size())==crc)&&goats_step3_usb::validate(raw,tracks)){b.raw=std::move(raw);b.tracks=std::move(tracks);}
  }nvs_close(h);
 }
 catalog_changed();goats_step3_store::init();goats_step3_usb::init();goats_gps_diag::frame_observer=on_frame;
}
inline void tick(){
 if(!state().started)return;
 goats_step3_usb::tick();goats_step3_store::tick();goats_step3_store::reserve_ids();
 if((goats_step3_store::state().recording||goats_session_ctl::has_started()||state().free_pending)&&uint32_t(::millis()-state().moving)>=goats_session_ctl::auto_timeout_ms())stop();
 if(state().closing&&goats_step3_store::idle()){state().closing=false;state().free_mode=false;goats_session_ctl::resume();}
}
}
#endif
