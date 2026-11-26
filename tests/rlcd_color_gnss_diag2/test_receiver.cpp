#include <cassert>
#include <cstring>
#include <vector>
#include <iostream>
#define goats_cfg reference_cfg
#include "REFERENCE_CONFIG"
#undef goats_cfg
#define goats_m9n reference_m9n
#include "REFERENCE_PARSER"
#undef goats_m9n
#include "COMPONENT_CPP"
using UART=esphome::uart::UARTComponent;
using Receiver=esphome::goats_gnss_color::GoatsGnssColor;
static std::vector<std::vector<uint8_t>> delivered;
namespace goats_b {void on_pvt(const uint8_t*p,uint16_t n){delivered.emplace_back(p,p+n);}}
#include "BRIDGE_HEADER"
void parity(){
 const auto&a=reference_m9n::state;const auto&b=goats_m9n::state;
 assert(a.fix==b.fix && a.used_sats==b.used_sats && a.visible_sats==b.visible_sats);
 assert(a.speed_kmh==b.speed_kmh && a.heading_deg==b.heading_deg && a.hdop==b.hdop);
 assert(a.latitude==b.latitude && a.longitude==b.longitude && a.pvt_hz==b.pvt_hz);
 assert(a.last_pvt_ms==b.last_pvt_ms && a.date_text==b.date_text && a.time_text==b.time_text);
 assert(reference_m9n::nav_timebase_offset==goats_m9n::nav_timebase_offset);
}
void feed(Receiver&r,UART&u,const std::vector<uint8_t>&bytes,uint32_t now){
 arduino_ms=now;UART original;original.append(bytes);u.append(bytes);
 reference_m9n::poll(&original);const auto before=u.reads;goats_diag::poll(&u);
 assert(u.reads-before==bytes.size() && original.reads==bytes.size());
 assert(u.writes.size()==17 && goats_m9n::pending_samples.empty());
 reference_m9n::pending_samples.clear();parity();
}
void put(std::vector<uint8_t>&p,size_t at,uint32_t v,unsigned n=4){for(unsigned i=0;i<n;i++)p[at+i]=uint8_t(v>>(8*i));}
std::vector<uint8_t> nav(uint32_t itow,bool fix=true){
 std::vector<uint8_t>p(92);put(p,0,itow);put(p,4,2026,2);p[6]=11;p[7]=26;p[8]=12;p[11]=7;
 p[20]=fix?3:0;p[21]=fix?1:0;p[23]=fix?13:0;
 put(p,24,123456789);put(p,28,451234567);put(p,60,25000);return p;
}
int main(){
 UART expected,u;delays.clear();arduino_ms=1000;reference_cfg::configure(expected);auto wait=delays;
 Receiver r;r.set_gps_uart(&u);
 arduino_ms=1000;r.setup();r.poll();assert(!r.configured() && u.writes.empty());
 goats_diag::begin(&r);assert(&goats_diag::data()==&r.data());
 arduino_ms=1899;goats_diag::poll(&u);assert(u.writes.empty());
 delays.clear();arduino_ms=1900;r.poll();assert(r.configured());
 assert(u.writes==expected.writes && u.bauds==expected.bauds && delays==wait);
 assert(u.writes.size()==17 && arduino_ms==4330);
 UART empty;reference_m9n::poll(&empty); // Same first empty drain after configuration.
 feed(r,u,{'$','G','P','G','G','A',',','0','*','0','0','\r','\n'},5000);
 assert(r.data().bytes==13 && !r.data().locked);
 auto p=nav(1000,false);auto f=goats_m9n::frame(1,7,p);
 for(uint8_t byte:f)feed(r,u,{byte},5040);
 assert(delivered.size()==1 && delivered.back()==p);
 assert(!goats_m9n::state.fix && r.data().last_pvt==4540);
 assert(uint32_t(esphome::millis()-r.data().last_pvt)==0); // Different epochs.
 auto corrupt=f;corrupt.back()^=1;feed(r,u,corrupt,5050);assert(r.data().bad==1);
 feed(r,u,{0xb5,0x62,1,7,0xff,0xff},5060);
 feed(r,u,goats_m9n::frame(1,7,std::vector<uint8_t>(91)),5070);assert(delivered.size()==1);
 feed(r,u,goats_m9n::frame(5,1,{6,0x8a}),5080);
 feed(r,u,goats_m9n::frame(5,0,{6,1}),5080);assert(r.data().cfg_ack==1 && r.data().cfg_nak==1);
 std::vector<uint8_t> dop(18);put(dop,12,75,2);feed(r,u,goats_m9n::frame(1,4,dop),5090);
 std::vector<uint8_t> sat(8);sat[5]=23;feed(r,u,goats_m9n::frame(1,0x35,sat),5090);
 assert(r.data().hdop==0.75f && r.data().seen==23 && goats_diag::trace_hdop()==0.75f);
 for(unsigned i=0;i<100;i++){
  auto v=nav(2000+40*i);auto packet=goats_m9n::frame(1,7,v);feed(r,u,packet,6000+40*i);
  assert(delivered.back()==v && delivered.size()==i+2 && r.data().locked);
  assert(r.data().last_pvt==5500+40*i);
 }
 assert(goats_m9n::state.fix && r.data().used==13 && r.data().pvt_hz==25.0f);
 // Bursts must deliver every complete original payload exactly once.
 std::vector<uint8_t> burst;
 for(unsigned i=0;i<80;i++){auto packet=goats_m9n::frame(1,7,nav(10000+40*i));burst.insert(burst.end(),packet.begin(),packet.end());}
 feed(r,u,burst,11000);assert(delivered.size()==181);
 feed(r,u,{},12501);assert(!goats_m9n::state.fix);
 feed(r,u,{},14001);assert(r.data().pvt_hz==0 && r.data().speed_kmh==0);
 feed(r,u,{},18000);assert(!r.data().locked);
 auto last=nav(20000);feed(r,u,goats_m9n::frame(1,7,last),18010);assert(r.data().locked);
 feed(r,u,goats_m9n::frame(1,7,last),0xfffffff0);
 feed(r,u,goats_m9n::frame(1,7,last),24);assert(r.data().locked);
 assert(uint32_t(esphome::millis()-r.data().last_pvt)==0);
 assert(u.writes==expected.writes); // No recovery configuration or extra polls.
 std::cout<<"PASS: original config trace, startup delay, single reader, raw PVT once, parser parity, errors, stale/no-fix, separate clock epochs, wrap and reacquisition\n";
}
