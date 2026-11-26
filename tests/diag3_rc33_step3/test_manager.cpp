#define GOATS_RC33_STEP1_IMPL
#include "goats_rc33_step1.h"
#include "goats_step3_runtime.h"
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
static void units(){
 init();assert(flash_writes==0&&flash_erases==0);auto raw=catalog();upload(raw);
 assert(goats_b::state().tracks.size()==2&&goats_step3_catalog::crc==goats_b::crc32(raw.data(),raw.size()));
 auto download=command("GTRK_GET\n");auto first=download.find('\n');assert(first!=std::string::npos&&download.substr(first+1,raw.size())==std::string(raw.begin(),raw.end()));assert(download.substr(first+1+raw.size())=="GTRK_END\n");
 upload(raw,false);assert(goats_b::state().raw==raw);test_heap=100;assert(command("GTRK_BEGIN 100 00000000\n")=="GTRK_ERR MEMORY\n");assert(goats_b::state().raw==raw);test_heap=512*1024;
 auto &b=goats_b::state();feed(1000);assert(b.auto_hits==1&&b.active_track==-1);
 feed(1000);assert(b.auto_hits==1);feed(1040,44.9995,9,0,2);assert(b.auto_hits==0);
 feed(1080);feed(1120);assert(b.active_track==-1);feed(1160);assert(b.active_track==0);feed(1200);
 const auto writes=flash_writes;feed(21200,45.0005,9,40);assert(goats_laptimer_running()&&st::state().recording&&st::state().active==1&&flash_writes==writes);pump();
 usb_connected=false;const uint32_t before=b.pvt_samples;
 for(unsigned i=1;i<=1000;i++){feed(21200+i*40,45.0005,9,40);if(i%100==0)usb::reply("GREC_STATUS test");pump(1);}
 assert(b.pvt_samples==before+1000&&st::state().sessions[0].points==1001&&st::state().dropped==0&&flash_erases==0&&uart.writes==0);
 feed(61240,46.0001,10,40);assert(b.active_track==0);assert(!rt::stop());
 feed(61280,45.0005,9,0);assert(rt::stop());pump();usb_connected=true;pump();usb_tx.clear();
 assert(st::idle()&&!goats_session_ctl::has_started());auto csv=read_csv(1);assert(csv.find("mode=CIRCUIT")!=std::string::npos&&csv.find("track=TEST")!=std::string::npos);
 assert(csv.find("elapsed_ms,lap,latitude,longitude,speed_kmh,hdop,satellites")!=std::string::npos);
 const auto bytes=st::state().sessions[0].body_bytes;reboot_store();assert(st::find(1)->body_bytes==bytes&&read_csv(1)==csv);
 nvs_failure=true;assert(command("GTRK_CLEAR\n")=="GTRK_ERR STORAGE\n");assert(b.raw==raw);nvs_failure=false;
 assert(command("GSD_DELETE 532e2e2f312e435356\n")=="GSD_ERR NAME_OR_STORAGE\n");
 assert(command("GSD_DELETE "+usb::hex(st::filename(*st::find(1)))+"\n")=="GSD_DELETE_OK\n");assert(st::find(1)->deleted);reboot_store();assert(st::find(1)->deleted);
 assert(rt::free_start());feed(70000);pump();assert(st::state().recording);clock_ms+=60001;pump();assert(st::idle()&&!goats_session_ctl::has_started());
 // Recover a valid prefix after a torn final record without erasing user data.
 auto tail=st::state().next;flash_bytes[tail]=0;reboot_store();assert(st::state().readonly&&st::find(2)->points==1&&flash_erases==0);
 assert(command("GREC_ERASE\n")=="GREC_ERASING\n");pump(1000);assert(st::can_begin()&&st::state().count==0&&flash_erases==512);
 st::id_floor=st::id_limit=0;st::id_retry=0;pump();assert(st::id_floor>=256);
 // Finite capacity stops recording and keeps the valid prefix exportable.
 test_partition.size=4096;reboot_store();assert(rt::free_start());
 for(unsigned i=0;i<200;i++){feed(80000+i*40);pump(1);}assert(st::state().readonly&&!st::state().recording);assert(rt::stop()||!goats_session_ctl::has_started());pump();assert(st::state().count==1&&st::state().sessions[0].points>0);
 test_partition.size=flash_bytes.size();
 goats_b::state().~State();new(&goats_b::state())goats_b::State();new(&goats_rc33_step1::state())goats_rc33_step1::State();new(&rt::state())rt::State();
 goats_tracks::load();goats_rc33_step1::attach();rt::start();pump();
 assert(goats_b::state().raw==raw&&goats_b::state().tracks.size()==2&&goats_tracks::tracks.empty());
 std::cout<<"PASS: Manager catalog persistence/CRC, three-fix AUTO and lock, actual GNSS reader, 25Hz trace with USB disconnected, no PVT flash writes/auto erase, reboot, deletion, torn tail and full capacity\n";
}
static std::vector<uint8_t>decode(const std::string&h){std::vector<uint8_t>v;assert(h.size()%2==0);for(size_t i=0;i<h.size();i+=2)v.push_back(usb::unhex(h[i])*16+usb::unhex(h[i+1]));return v;}
static std::string encode(const std::vector<uint8_t>&v){return usb::hex(std::string(v.begin(),v.end()));}
int main(int argc,char**argv){
 if(argc==1){units();return 0;}init();std::string line;
 while(std::getline(std::cin,line)){
  if(line.rfind("USB ",0)==0)std::cout<<"OUT "<<encode(transact(decode(line.substr(4))))<<std::endl;
  else if(line.rfind("SIM ",0)==0){unsigned n=std::stoul(line.substr(4));assert(rt::free_start());for(unsigned i=0;i<n;i++){feed(1000+i*40,45.0005+i*.000001,9,40);pump(1);}feed(1000+n*40,45.0005,9,0);assert(rt::stop());pump();std::cout<<"OK"<<std::endl;}
  else if(line=="REBOOT"){reboot_store();std::cout<<"OK"<<std::endl;}
  else if(line=="QUIT"){std::cout<<"OK"<<std::endl;return 0;}
  else {std::cout<<"ERR"<<std::endl;}
 }
}
