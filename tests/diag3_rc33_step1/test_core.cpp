#define GOATS_RC33_STEP1_IMPL
#include "goats_rc33_step1.h"
#include <cassert>
#include <cstring>
#include <cmath>
#include <iostream>
using UART=esphome::uart::UARTComponent;
namespace esphome::goats_spi_diag {
struct GoatsSpiDiag {UART *gps_uart_{nullptr};bool gps_configured_{true};void gps_poll_();};
ACTUAL_GPS_POLL
}

static std::vector<uint8_t> packet(uint32_t itow,double lat,double lon,float kmh=40,uint8_t type=3,bool ok=true,uint8_t sv=13){
 std::vector<uint8_t>p(92);auto put=[&](unsigned at,uint32_t v,unsigned n=4){for(unsigned i=0;i<n;i++)p[at+i]=uint8_t(v>>(8*i));};
 put(0,itow);put(4,2026,2);p[6]=11;p[7]=26;p[8]=12;p[11]=3;p[20]=type;p[21]=ok;p[23]=sv;
 put(24,static_cast<int32_t>(llround(lon*1e7)));put(28,static_cast<int32_t>(llround(lat*1e7)));put(60,static_cast<int32_t>(llround(kmh/0.0036f)));
 return goats_m9n::frame(1,7,p);
}
static void feed(UART&u,const std::vector<uint8_t>&f,uint32_t now){
 clock_ms=now;const auto before=u.reads;for(auto c:f)u.rx.push_back(c);
 esphome::goats_spi_diag::GoatsSpiDiag controller;controller.gps_uart_=&u;controller.gps_poll_();
 assert(u.reads-before==f.size() && u.writes==0);
 goats_gps_diag::stability.tick(::millis());
 assert(usb_installs==0 && usb_reads==0 && usb_writes==0 && nvs_calls==0);
}
int main(){
 GoatsTrackUsb track;track.name="TEST";track.start_lat=45;track.start_lon=8.9999;track.finish_lat=45;track.finish_lon=9.0001;track.trigger_radius_m=20;
 track.sectors.push_back({"S1",45.001,8.9999,45.001,9.0001});goats_tracks::tracks.push_back(track);
 goats_rc33_step1::attach();goats_rc33_step1::attach();
 auto &b=goats_b::state();assert(b.tracks.size()==1 && b.tracks[0].name=="TEST" && b.tracks[0].sectors.size()==1);
 assert(usb_installs==0 && usb_reads==0 && usb_writes==0 && nvs_calls==0 && !b.usb);
 esphome::goats_spi_diag::GoatsSpiDiag not_ready;not_ready.gps_poll_();
 UART guarded;not_ready.gps_uart_=&guarded;not_ready.gps_configured_=false;
 for(auto byte:packet(100,45,9))guarded.rx.push_back(byte);
 not_ready.gps_poll_();assert(guarded.reads==0 && b.pvt_samples==0);
 b.manual_track=true;b.active_track=0;UART u;
 GoatsLaptimerEngine expected;
 auto sample=[&](uint32_t now,double lat,float speed=40,uint8_t type=3,bool ok=true,uint8_t sv=13){
  feed(u,packet(now,lat,9,speed,type,ok,sv),now);
  const bool valid=type>=3 && ok && sv>=4;
  expected.update(&track,valid,b.lat,b.lon,b.speed,now,now);
  assert(expected.running()==goats_laptimer_running());
  assert(expected.lap_number()==goats_laptimer_lap_number());
  assert(expected.last_lap_ms()==goats_laptimer_last_lap_ms());
  assert(expected.best_lap_ms()==goats_laptimer_best_lap_ms());
  assert(expected.last_finish_ms()==goats_laptimer_last_finish_ms());
  assert(expected.race_pace_ms()==goats_laptimer_race_pace_ms());
  assert(expected.race_pace_lap_count()==goats_laptimer_race_pace_lap_count());
  assert(expected.last_lap_average_speed_kmh()==goats_laptimer_last_lap_average_speed_kmh());
 };
 sample(1000,44.9995);sample(21000,45.0005);assert(goats_laptimer_running() && goats_session_ctl::has_started());
 sample(41000,45.001,80);sample(61000,44.9995,60);
 assert(goats_laptimer_lap_number()>0 && goats_laptimer_last_lap_ms()>0);
 assert(std::fabs(goats_lap_speed::last()-80)<0.01f);
 const uint32_t count=b.pvt_samples,valid=goats_rc33_step1::state().valid_samples;
 feed(u,packet(61000,44.9995,9.0),61040);assert(b.pvt_samples==count && goats_rc33_step1::state().valid_samples==valid);
 auto corrupt=packet(62000,45.0,9.0);corrupt.back()^=1;feed(u,corrupt,62000);assert(b.pvt_samples==count);
 feed(u,packet(63000,45.0,9.0,0,2,true,3),63000);
 assert(b.pvt_samples==count+1 && goats_rc33_step1::state().valid_samples==valid && b.fix_type==2);
 assert(goats_gps_diag::stability.fix_active && goats_gps_diag::stability.fix_type==2);
 const uint32_t before_burst=b.pvt_samples;
 std::vector<uint8_t>burst;
 for(unsigned i=0;i<100;i++){auto f=packet(64000+40*i,45.001,9.0);burst.insert(burst.end(),f.begin(),f.end());}
 feed(u,burst,68000);assert(b.pvt_samples==before_burst+100);
 for(unsigned i=0;i<10;i++)feed(u,{},68000+i);assert(b.pvt_samples==before_burst+100);
 assert(goats_m9n::pending_samples.empty());
 assert(goats_clock::observed_ms==68000); // Arduino epoch used consistently in this stage.
 assert(std::strstr(goats_rc33_step1::line(),"CORE RC3.3:")!=nullptr);
 std::cout<<"PASS: catalog copied in RAM, original RC3.3 crossings/sector/lap/pace, speed/session state, duplicate/corrupt rejection, 2D distinction, burst exactly once, no USB/NVS writes\n";
}
