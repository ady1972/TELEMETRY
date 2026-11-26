#include <cassert>
#include <vector>
#include <cstdint>
#include <cstddef>
#include "esphome/components/uart/uart.h"
#define goats_m9n baseline_gnss
#include ORIGINAL_PARSER_HEADER
#undef goats_m9n
static std::vector<std::vector<uint8_t>> delivered;
namespace goats_b {
void on_pvt(const uint8_t *p,uint16_t n){delivered.emplace_back(p,p+n);}
}
#include "goats_color_gnss_bridge.h"
using esphome::uart::UARTComponent;
static std::vector<uint8_t> packet(uint8_t cls,uint8_t id,const std::vector<uint8_t>&p){
 std::vector<uint8_t> f{0xB5,0x62,cls,id,uint8_t(p.size()),uint8_t(p.size()>>8)};
 f.insert(f.end(),p.begin(),p.end());uint8_t a=0,b=0;
 for(size_t i=2;i<f.size();++i){a+=f[i];b+=a;}f.push_back(a);f.push_back(b);return f;
}
static void put(std::vector<uint8_t>&p,size_t at,uint32_t value,unsigned n=4){
 for(unsigned i=0;i<n;++i)p[at+i]=uint8_t(value>>(8*i));
}
static std::vector<uint8_t> pvt(uint32_t itow){
 std::vector<uint8_t> p(92);put(p,0,itow);put(p,4,2026,2);
 p[6]=11;p[7]=26;p[8]=10;p[9]=35;p[10]=12;p[11]=7;
 p[20]=3;p[21]=1;p[23]=12;put(p,24,123456789);put(p,28,451234567);
 put(p,60,25000);put(p,64,12345000);return p;
}
static void parity(){
 const auto &a=baseline_gnss::state;const auto &b=goats_m9n::state;
 assert(a.fix==b.fix&&a.used_sats==b.used_sats&&a.visible_sats==b.visible_sats);
 assert(a.speed_kmh==b.speed_kmh&&a.heading_deg==b.heading_deg&&a.hdop==b.hdop);
 assert(a.latitude==b.latitude&&a.longitude==b.longitude&&a.pvt_hz==b.pvt_hz);
 assert(a.last_pvt_ms==b.last_pvt_ms&&a.rate_window_ms==b.rate_window_ms&&a.rate_count==b.rate_count);
 assert(a.date_text==b.date_text&&a.time_text==b.time_text);
 assert(baseline_gnss::nav_timebase_set==goats_m9n::nav_timebase_set);
 assert(baseline_gnss::nav_timebase_offset==goats_m9n::nav_timebase_offset);
 const auto &x=baseline_gnss::pending_samples;const auto &y=goats_m9n::pending_samples;
 assert(x.size()==y.size());
 for(size_t i=0;i<x.size();++i){
  assert(x[i].now_ms==y[i].now_ms&&x[i].gnss_itow_ms==y[i].gnss_itow_ms);
  assert(x[i].fix==y[i].fix&&x[i].satellites==y[i].satellites);
  assert(x[i].latitude==y[i].latitude&&x[i].longitude==y[i].longitude);
  assert(x[i].speed_kmh==y[i].speed_kmh&&x[i].heading_deg==y[i].heading_deg);
 }
}
int main(){
 UARTComponent a,b;
 auto feed=[&](const std::vector<uint8_t>&bytes){
  a.append(bytes);b.append(bytes);baseline_gnss::poll(&a);goats_m9n::poll(&b);parity();
 };
 std::vector<uint8_t> noise{'$', 'G','N','R','M','C',',','0','*','0','0','\r','\n',0,0xff};feed(noise);
 auto p=pvt(1000);auto f=packet(1,7,p);
 for(uint8_t byte:f)feed({byte});
 assert(goats_m9n::state.fix&&goats_m9n::state.used_sats==12);
 auto corrupt=f;corrupt.back()^=0x80;feed(corrupt);
 assert(goats_m9n::checksum_errors==1);
 feed({0xB5,0x62,1,7,1,4}); // >1024 bytes: reject length and recover.
 feed(packet(1,7,std::vector<uint8_t>(91))); // Valid packet, short NAV-PVT.
 feed(f);
 std::vector<uint8_t> dop(18);put(dop,12,87,2);feed(packet(1,4,dop));
 std::vector<uint8_t> sat(8);sat[5]=23;feed(packet(1,0x35,sat));
 assert(goats_m9n::state.visible_sats==23); // Count from p[5], not C/N0 filtering.
 std::vector<uint8_t> burst;
 for(unsigned i=0;i<100;i++){
  auto v=packet(1,7,pvt(2000+i*40));burst.insert(burst.end(),v.begin(),v.end());
 }
 test_ms+=1000;feed(burst);assert(goats_m9n::pending_samples.size()==64);
 assert(goats_m9n::state.pvt_hz==102.0f); // Two valid initial PVT plus burst.
 test_ms+=1501;feed({});assert(!goats_m9n::state.fix);
 test_ms+=1500;feed({});assert(goats_m9n::state.speed_kmh==0&&goats_m9n::state.pvt_hz==0);
 // Start actual RC3.3 adapter with clean parser; no alternate laptimer queue.
 goats_m9n::parser={};goats_m9n::state={};goats_m9n::pending_samples.clear();
 goats_m9n::nav_timebase_set=false;goats_m9n::rx_bytes=goats_m9n::checksum_errors=0;
 goats_diag::data()={};UARTComponent runtime;
 runtime.append(packet(1,4,dop));runtime.append(packet(1,0x35,sat));
 runtime.append(noise);runtime.append(corrupt);runtime.append(packet(1,7,std::vector<uint8_t>(91)));
 goats_diag::poll(&runtime);assert(delivered.empty());
 runtime.append(burst);goats_diag::poll(&runtime);
 assert(delivered.size()==100&&runtime.available()==0&&goats_m9n::pending_samples.empty());
 for(unsigned i=0;i<100;i++)assert(delivered[i]==pvt(2000+i*40));
 assert(goats_diag::data().bad==1&&goats_diag::data().seen==23);
 assert(goats_diag::data().used==12&&goats_diag::trace_hdop()==.87f);
 assert(goats_diag::data().locked&&goats_diag::data().speed_kmh==90.f);
 goats_diag::poll(&runtime);assert(delivered.size()==100); // No duplicate consumer.
 test_ms+=3001;goats_diag::poll(&runtime);
 assert(goats_diag::data().speed_kmh==0&&goats_diag::data().pvt_hz==0);
 test_ms+=3500;goats_diag::poll(&runtime);assert(!goats_diag::data().locked);
 // Preserve even invalid/2D raw PVT: eligibility remains RC3.3's responsibility.
 p[20]=2;p[21]=0;p[23]=2;runtime.append(packet(1,7,p));
 goats_diag::poll(&runtime);assert(delivered.back()==p&&delivered.size()==101);
 assert(runtime.writes==0&&runtime.bauds==0&&a.writes==0&&b.writes==0);
}
