#define GOATS_RC33_STEP1_IMPL
#include "goats_rc33_step1.h"
#include <cassert>
#include <cstring>
#include <cmath>
#include <iostream>
using UART=esphome::uart::UARTComponent;
namespace goats_lap_storage {inline unsigned begins=0;inline void begin(){++begins;}}
namespace goats_step3_store {struct State{unsigned active=0;};inline State&state(){static State s;return s;}}
namespace goats_step3 {
inline unsigned starts=0,ticks=0,free_starts=0,stops=0;
inline bool store_flag=false,usb_flag=false;inline void start(bool storage=true,bool usb=true){store_flag=storage;usb_flag=usb;++starts;goats_gps_diag::frame_observer=goats_rc33_step1::on_frame;}
inline void tick(){++ticks;}
inline bool free_start(){++free_starts;return true;}
inline bool stop(){++stops;return true;}
}
namespace goats_ui {inline unsigned captures=0;inline void capture(uint32_t){++captures;}}
#include "goats_postfix_runtime.h"
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
int main(int argc,char**argv){
 assert(argc==2);const auto mode=unsigned(std::strtoul(argv[1],nullptr,10));assert(mode<=4);const bool storage=mode==2||mode==3,usb=mode==2||mode==4,backend=storage||usb;
 GoatsTrackUsb track;track.name="TEST";track.start_lat=45;track.start_lon=8.9999;track.finish_lat=45;track.finish_lon=9.0001;track.trigger_radius_m=20;
 goats_tracks::tracks.push_back(track);goats_postfix::set(mode);goats_postfix::prepare();goats_postfix::start();
 auto&b=goats_b::state();
 assert(goats_lap_storage::begins==storage);assert(goats_step3::starts==backend);
 assert(goats_rc33_step1::state().ready==(mode!=0));assert((goats_gps_diag::frame_observer==nullptr)==(mode==0));
 assert(goats_step3::store_flag==storage&&goats_step3::usb_flag==usb);UART uart;uint32_t time=1000;
 for(unsigned i=0;i<50;i++,time+=40){feed(uart,packet(time,45,9,0,0,false,0),time);goats_postfix::tick();}
 assert(!goats_gps_diag::stability.fix_active);
 for(unsigned i=0;i<500;i++,time+=40){feed(uart,packet(time,45,9,0,3,true,13),time);goats_postfix::tick();}
 assert(goats_gps_diag::stability.fix_active&&goats_gps_diag::stability.pvt_fresh(::millis()));
 assert(goats_m9n::state.fix&&goats_m9n::state.pvt_hz==25.0f);
 assert(goats_gps_diag::counters.pvt==550&&goats_gps_diag::counters.checksum_errors==0);
 assert(b.pvt_samples==(mode?550u:0u));
 assert(goats_rc33_step1::state().valid_samples==(mode?500u:0u));
 assert(b.active_track==(mode?0:-1)); // actual AUTO requires three valid fixes.
 assert(goats_step3::ticks==(backend?550u:0u));assert(goats_ui::captures==(mode?550u:0u));
 assert(!goats_laptimer_running()); // fix at standstill alone must not start a lap.
 const auto core_before=b.pvt_samples;
 feed(uart,packet(time-40,45,9,0),time);assert(b.pvt_samples==core_before); // duplicate iTOW.
 auto corrupt=packet(time,45,9,0);corrupt.back()^=1;feed(uart,corrupt,time+40);assert(b.pvt_samples==core_before);
 assert(goats_gps_diag::counters.checksum_errors==1);
 goats_postfix::record_toggle();assert(goats_step3::free_starts==storage);
 goats_step3_store::state().active=1;goats_postfix::record_toggle();assert(goats_step3::stops==storage);
 assert(uart.writes==0&&goats_m9n::pending_samples.empty());
 assert(usb_installs==0&&usb_reads==0&&usb_writes==0&&nvs_calls==0);
 std::cout<<"PASS: mode "<<mode<<", 50 no-fix + 500 fix PVT at 25Hz, observer/core/track/start/tick/REC gates, duplicate/corrupt frames\n";
}
