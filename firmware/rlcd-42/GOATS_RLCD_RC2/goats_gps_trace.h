#pragma once
// MG902 TEST25: campioni NAV-PVT 25Hz in coda RAM; FatFS SOLO nel tick non nel parser.
#include <cstdint>
#include <cstdio>
#include <cstring>
#include "goats_sd_storage.h"
#include "goats_session_archive.h"
#include "goats_session_control.h"
#include "goats_recording_dates.h"
namespace goats_gps_trace {
struct Point {uint32_t elapsed, lap; double lat,lon; float kmh,hdop; uint8_t sv;};
static constexpr unsigned CAP=512;
inline Point* queue(){static Point q[CAP];return q;}
inline unsigned &rd(){static unsigned v=0;return v;}
inline unsigned &wr(){static unsigned v=0;return v;}
inline bool &pending(){static bool v=false;return v;}
inline bool &recording(){static bool v=false;return v;}
inline uint32_t &start_itow(){static uint32_t v=0;return v;}
inline uint32_t &dropped(){static uint32_t v=0;return v;}
inline char* date_text(){static char v[16]="";return v;}
inline char* time_text(){static char v[16]="";return v;}
inline char* track_text(){static char v[48]="AUTO";return v;}
inline uint32_t &pending_sid(){static uint32_t v=0;return v;}
// Chiamata da NAV-PVT: soltanto copia in RAM; nessun accesso alla SD.
inline void on_pvt(const uint8_t *p,bool valid,double lat,double lon,float speed,
                   uint32_t itow,uint8_t num_sv,float hdop,const char *track){
 if(!valid || goats_session_ctl::paused())return;
 // TEST25: non aprire una traccia prima che il cronometro/sessione sia partita.
 // Un fix in movimento da solo non deve aprire un file LIVE sulla microSD.
 if(!recording() && !goats_session_ctl::has_started())return;
 goats_dates::capture(goats_archive::session(),goats_clock::latest);
 if(!recording()){
   // Avvia dalla prima posizione valida in movimento (prima del passaggio sul traguardo).
   if(speed<3.0f || !goats_sd_storage::ready() || !goats_sd_storage::writable())return;
   recording()=true;pending()=true;start_itow()=itow;rd()=wr()=0;dropped()=0;
   std::snprintf(track_text(),48,"%s",track&&*track?track:"AUTO");
   goats_clock::format(goats_dates::date(goats_archive::session()),date_text(),16,time_text(),16);
   pending_sid()=goats_archive::session();
 }
 const unsigned next=(wr()+1)%CAP;
 if(next==rd()){++dropped();return;}
 // iTOW is millisecond resolution, including wrap at GNSS week boundary.
 queue()[wr()]={uint32_t(itow-start_itow()),
   (uint32_t)goats_laptimer_lap_number(),lat,lon,speed,hdop,num_sv};
 wr()=next;
}
inline void flush(unsigned max_points){
 if(!goats_sd_storage::live_open())return;
 while(max_points-- && rd()!=wr()){
   const auto &p=queue()[rd()];
   goats_sd_storage::append_live_point(p.elapsed,p.lap,p.lat,p.lon,p.kmh,p.hdop,p.sv);
   if(!goats_sd_storage::live_open()){ESP_LOGE("GPS_TRACE","SD write failed: %s",goats_sd_storage::last_stage());return;}
   rd()=(rd()+1)%CAP;
 }
}
inline void tick(){
 goats_clock_runtime::tick();goats_dates::tick();
 if(!recording()||goats_session_ctl::paused())return;
 if(pending()){
   pending()=false;
   if(!goats_sd_storage::begin_live_session("TRACK",date_text(),time_text(),track_text())){
     ESP_LOGE("GPS_TRACE","Cannot start trace: %s",goats_sd_storage::last_stage());
     recording()=false;rd()=wr()=0;return;
   }
 }
 flush(8);
}
inline void finish(bool save){
 if(recording()){
   if(pending())tick();
   // Fine sessione: svuota la coda prima di chiudere il file.
   while(goats_sd_storage::live_open() && rd()!=wr())flush(64);
   if(goats_sd_storage::live_open()){
     if(save){
       const uint32_t save_start=millis();
       const bool ok=goats_sd_storage::finish_live_session(pending_sid());
       ESP_LOGI("GPS_TRACE","saved=%d duration_ms=%lu points=%lu dropped=%lu stage=%s",ok,
         (unsigned long)(millis()-save_start),
         (unsigned long)goats_sd_storage::live_points(),(unsigned long)dropped(),goats_sd_storage::last_stage());
     }else{goats_sd_storage::discard_live_session();}
   }
 }
 recording()=false;pending()=false;rd()=wr()=0;
}
}
