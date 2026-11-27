#define GOATS_RC33_STEP1_IMPL
#include "goats_rc33_step1.h"
#include "goats_step3_runtime.h"
#include "rc33_goats_postlap_ui.h"
#include <cassert>
#include <iostream>
#include <sstream>
#include <fstream>
#include <new>
using UART=esphome::uart::UARTComponent;
namespace esphome::goats_spi_diag {struct GoatsSpiDiag{UART *gps_uart_=nullptr;bool gps_configured_=true;void gps_poll_();};
ACTUAL_GPS_POLL
}
namespace st=goats_step3_store;namespace rt=goats_step3;namespace usb=goats_step3_usb;
UART uart;
static void pump(unsigned n=300){for(unsigned i=0;i<n;i++)rt::tick();}
static std::vector<uint8_t> packet(uint32_t itow,double lat,double lon,float speed,uint8_t type=3){
 std::vector<uint8_t>p(92);auto put=[&](unsigned at,uint32_t v,unsigned n=4){for(unsigned i=0;i<n;i++)p[at+i]=v>>(i*8);};
 put(0,itow);put(4,2026,2);p[6]=11;p[7]=26;p[8]=12;p[11]=3;p[20]=type;p[21]=1;p[23]=13;
 put(24,int32_t(llround(lon*1e7)));put(28,int32_t(llround(lat*1e7)));put(60,int32_t(llround(speed/.0036f)));
 return goats_m9n::frame(1,7,p);
}
static void feed(uint32_t now,double lat=44.9995,double lon=9,float speed=0,uint8_t type=3){
 clock_ms=now;const auto f=packet(now%604800000,lat,lon,speed,type);for(auto b:f)uart.rx.push_back(b);
 esphome::goats_spi_diag::GoatsSpiDiag c;c.gps_uart_=&uart;inside_pvt=true;c.gps_poll_();inside_pvt=false;
 goats_gps_diag::stability.tick(::millis());
}
static std::vector<uint8_t> transact(const std::vector<uint8_t>&bytes){usb_tx.clear();for(auto c:bytes)usb_rx.push_back(c);pump(2000);auto out=usb_tx;usb_tx.clear();return out;}
static std::string command(const std::string&s){auto v=transact(std::vector<uint8_t>(s.begin(),s.end()));return {v.begin(),v.end()};}
template<class T>void put(std::vector<uint8_t>&v,const T&x){auto*p=(const uint8_t*)&x;v.insert(v.end(),p,p+sizeof(x));}
static std::vector<uint8_t> catalog(){
 std::vector<uint8_t>v={'G','T','C','3',1,0,2,0};
 for(int k=0;k<2;k++){
  std::string name=k?"OTHER":"TEST";put(v,uint8_t(name.size()));v.insert(v.end(),name.begin(),name.end());
  put(v,45.0+k);put(v,8.9999+k);put(v,45.0+k);put(v,9.0001+k);put(v,20.f);put(v,uint8_t(0));put(v,uint8_t(0));
 }return v;
}
static void upload(const std::vector<uint8_t>&data,bool good=true){
 char c[80];snprintf(c,sizeof(c),"GTRK_BEGIN %u %08lX\n",(unsigned)data.size(),(unsigned long)(goats_b::crc32(data.data(),data.size())+(good?0:1)));
 assert(command(c)=="GTRK_READY\n");const auto reply=transact(data);
 std::string r(reply.begin(),reply.end());assert(r==(good?"GTRK_OK 2\n":"GTRK_ERR CRC\n"));
}
static void init(){goats_tracks::load();goats_rc33_step1::attach();rt::start();pump();assert(st::state().ready&&usb_installs>=1&&uart.writes==0);}
static void reboot_store(){new(&st::state())st::State();st::init();pump(2000);}
static std::string read_csv(uint32_t id){st::Reader reader;assert(reader.open(id));std::string out;uint8_t bytes[137];for(;;){size_t n=reader.read(bytes,sizeof(bytes));if(!n)break;out.append((const char*)bytes,n);}assert(!reader.error&&out.size()==st::file_size(*st::find(id)));return out;}
static uint32_t bits(float v){uint32_t n;memcpy(&n,&v,4);return n;}
static void seed(){
 auto&v=goats_b::state().tracks;v.clear();
 for(int i=0;i<50;i++){
  goats_b::Track t;t.name="T"+std::to_string(i);t.a=t.c=45+i*.002;t.b=8.9999;t.d=9.0001;t.radius=20;
  t.sectors.push_back({"S1",t.a+.0005,8.9999,t.a+.0005,9.0001});v.push_back(t);
 }
}
static void snapshot(uint32_t now){
 const auto&b=goats_b::state();
 std::cout<<b.pvt_samples<<','<<b.active_track<<','<<b.auto_candidate<<','<<unsigned(b.auto_hits)<<','<<b.running<<','<<b.laps<<','<<b.last_lap<<','<<b.best_lap<<','<<b.last_cross<<',';
 std::cout<<goats_laptimer_running()<<','<<goats_laptimer_current_ms(now)<<','<<goats_laptimer_display_current_ms(now)<<','<<goats_laptimer_lap_number()<<','<<goats_laptimer_last_lap_ms()<<','<<goats_laptimer_best_lap_ms()<<','<<goats_laptimer_last_finish_ms()<<',';
 std::cout<<bits(goats_laptimer_live_delta_seconds())<<','<<bits(goats_laptimer_display_delta_seconds(now))<<','<<bits(goats_laptimer_display_speed_delta_kmh(now))<<',';
 std::cout<<goats_laptimer_race_pace_ms()<<','<<goats_laptimer_race_pace_lap_count()<<','<<bits(goats_laptimer_race_average_speed_kmh())<<','<<bits(goats_laptimer_last_lap_average_speed_kmh())<<',';
 std::cout<<bits(goats_laptimer_post_lap_best_delta_seconds())<<','<<bits(goats_laptimer_post_lap_pace_delta_seconds())<<','<<bits(goats_laptimer_post_lap_speed_delta_kmh())<<',';
 for(unsigned k=0;k<3;k++)std::cout<<goats_laptimer_sector_status(k)<<','<<bits(goats_laptimer_sector_display_delta_seconds(k,now))<<','<<goats_laptimer_sector_display_status(k,now)<<','<<goats_laptimer_last_timing_sector_ms(k)<<',';
 std::cout<<goats_laptimer_last_text()<<','<<goats_laptimer_best_text()<<','<<goats_ui::best_time_ms()<<','<<goats_ui::best_until()<<','<<goats_ui::show_until()<<',';
 std::cout<<st::state().active<<','<<st::state().recording<<','<<st::state().queued<<','<<st::state().dropped<<'\n';
}
int main(int argc,char**argv){
 assert(argc==3);const unsigned scenario=std::stoul(argv[1]);assert(scenario<3);
#ifdef NEW_CACHE
 goats_core_cache::set_enabled(std::stoul(argv[2])!=0);
#endif
 goats_rc33_step1::attach();seed();rt::start();pump();
 const unsigned count=scenario==1?4200:1200;
 for(unsigned i=0;i<count;i++){
  const uint32_t now=1000+i*40;
  if(scenario==2){
   if(i==300){goats_b::state().tracks[0].a+=.001;goats_b::state().tracks[0].c+=.001;rt::catalog_changed();}
   if(i==600){std::reverse(goats_b::state().tracks.begin(),goats_b::state().tracks.end());rt::catalog_changed();}
   if(i==900){goats_b::state().tracks.clear();rt::catalog_changed();}
   if(i==950){seed();rt::catalog_changed();}
  }
  const double phase=(double(i)+.13)*6.283185307179586/1200.;
  const double lat=45+(scenario==1?.001:.00001)*std::sin(phase),lon=9+.00001*std::cos(phase);
  const bool nofix=(i>=250&&i<270);const float speed=scenario==1?(i>=700&&i<900?0.f:float(45+10*std::sin(phase))):0.f;
  feed(now,lat,lon,speed,nofix?0:3);goats_ui::capture(now);pump(1);snapshot(now);
  if(i&&i%997==0){feed(now,lat,lon,speed);snapshot(now);}
 }
 if(scenario==1)assert(goats_laptimer_lap_number()>=2&&goats_laptimer_best_lap_ms()>0);
 const uint32_t last=1000+count*40;feed(last,45.0001,9,0);pump();
 if(st::state().active){assert(rt::stop());pump();}
 for(unsigned i=0;i<st::state().count;i++)std::cout<<read_csv(st::state().sessions[i].header.sid);
#ifdef NEW_CACHE
 std::cerr<<"CACHE "<<goats_core_cache::requests<<" "<<goats_core_cache::evaluations<<"\n";
#endif
}
