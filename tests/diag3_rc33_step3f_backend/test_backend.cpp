#define GOATS_RC33_STEP1_IMPL
#include "goats_rc33_step1.h"
#include "goats_step3_runtime.h"
#include <cassert>
#include <iostream>
#include <sstream>
#include <fstream>
#include <new>
namespace goats_lap_storage {inline unsigned begins=0;inline void begin(){++begins;}}
namespace goats_ui {inline void capture(uint32_t){}}
#include "goats_postfix_runtime.h"
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
int main(int argc,char**argv){
 assert(argc==2);const auto mode=unsigned(std::strtoul(argv[1],nullptr,10));assert(mode<=4);
 const bool storage=mode==2||mode==3,transport=mode==2||mode==4,backend=storage||transport;
 GoatsTrackUsb track;track.name="TEST";track.start_lat=45;track.start_lon=8.9999;track.finish_lat=45;track.finish_lon=9.0001;track.trigger_radius_m=20;
 goats_tracks::tracks.push_back(track);goats_postfix::set(mode);goats_postfix::prepare();goats_postfix::start();pump();
 assert(goats_lap_storage::begins==storage);
 assert(rt::state().started==backend);
 if(backend)assert(rt::state().store_enabled==storage&&rt::state().usb_enabled==transport);
 assert((st::state().partition!=nullptr)==storage&&st::state().ready==storage);
 assert(usb_installs==unsigned(transport)&&usb::state().ready==transport);
 assert(st::state().id_commits==unsigned(storage)&&nvs_writes==unsigned(storage));
 assert(flash_writes==0&&flash_erases==0&&st::state().write_ops==0);
 uint32_t time=1000;
 for(unsigned i=0;i<50;i++,time+=40){feed(time,45,9,0,0);goats_postfix::tick();}
 for(unsigned i=0;i<500;i++,time+=40){feed(time,45,9,0);goats_postfix::tick();}
 assert(goats_gps_diag::stability.fix_active&&goats_m9n::state.pvt_hz==25.0f);
 assert(goats_gps_diag::counters.pvt==550&&goats_b::state().pvt_samples==(mode?550u:0u));
 assert(!goats_laptimer_running()&&!st::state().recording&&flash_writes==0&&flash_erases==0);
 assert(st::state().write_ops==0&&st::state().id_commits==unsigned(storage));
 assert(uart.writes==0);
 if(!transport)assert(usb_installs==0&&usb_reads==0&&usb_writes==0);
 else{
  assert(command("GSD_PING\n")=="GSD_PONG TEST3_INTERNAL\n");
  if(!storage){
   assert(command("GREC_START\n")=="GREC_ERR BUSY_OR_STORAGE\n");
   assert(command("GREC_ERASE\n")=="GREC_ERR BUSY\n");
   assert(!st::state().partition&&flash_writes==0&&flash_erases==0&&nvs_writes==0);
  }
 }
 if(storage){
  assert(rt::free_start());const auto before_flash=flash_writes;
  feed(time,45,9,0);assert(st::state().active&&flash_writes==before_flash);pump(1);
  for(unsigned i=1;i<=100;i++){
   const auto before=flash_writes;feed(time+i*40,45,9,0);assert(flash_writes==before);pump(1);
  }
  assert(st::state().sessions[0].points==101&&st::state().dropped==0);
  assert(st::state().write_ops==flash_writes&&flash_writes>0&&st::state().id_commits==1);
  assert(rt::stop());pump();const auto csv=read_csv(st::state().sessions[0].header.sid);
  assert(csv.find("elapsed_ms,lap,latitude,longitude,speed_kmh,hdop,satellites")!=std::string::npos);
  assert(csv.find("mode=FREE")!=std::string::npos&&st::idle()&&flash_erases==0);
  if(!transport)assert(usb_installs==0&&usb_reads==0&&usb_writes==0);
 }
 std::cout<<"PASS: real backend mode "<<mode<<", receiver/core/USB/flash gates, no idle-fix writes, ID/W counters, 101-point 25Hz trace when enabled\n";
}
