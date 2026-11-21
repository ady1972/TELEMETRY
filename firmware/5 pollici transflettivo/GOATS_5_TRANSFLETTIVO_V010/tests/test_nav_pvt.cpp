#include <cassert>
#include <cstddef>
#include <cmath>
#include <iostream>
#include <vector>
#include "nav_pvt.h"
using esphome::goats_core::NavPvtParser;
using esphome::goats_core::NavSample;

static std::vector<uint8_t> frame(uint32_t itow, bool fix=true) {
  std::vector<uint8_t> v{0xB5,0x62,1,7,92,0};
  v.resize(98,0);
  for(unsigned i=0;i<4;++i)v[6+i]=static_cast<uint8_t>(itow>>(i*8));
  v[26]=3;v[27]=fix?1:0;v[29]=10;
  const int32_t lon=90000000,lat=450000000,speed=10000;
  for(unsigned i=0;i<4;++i){
    v[30+i]=static_cast<uint8_t>(lon>>(i*8));
    v[34+i]=static_cast<uint8_t>(lat>>(i*8));
    v[66+i]=static_cast<uint8_t>(speed>>(i*8));
  }
  uint8_t a=0,b=0;for(std::size_t i=2;i<v.size();++i){a+=v[i];b+=a;}
  v.push_back(a);v.push_back(b);return v;
}

static std::vector<uint8_t> packet(uint8_t id, const std::vector<uint8_t> &payload) {
  std::vector<uint8_t> v{0xB5,0x62,1,id,uint8_t(payload.size()),uint8_t(payload.size()>>8)};
  v.insert(v.end(),payload.begin(),payload.end());
  uint8_t a=0,b=0;
  for(std::size_t i=2;i<v.size();++i){a+=v[i];b+=a;}
  v.push_back(a);v.push_back(b);return v;
}

static unsigned feed(NavPvtParser &parser, const std::vector<uint8_t> &bytes,
                     uint32_t now, NavSample &sample) {
  unsigned samples=0;
  for(auto b:bytes) if(parser.consume(b,now,sample)) ++samples;
  return samples;
}
int main(){
  NavPvtParser parser;NavSample sample;unsigned received=0;
  for(auto b:frame(1000))if(parser.consume(b,50,sample))++received;
  assert(received==1 && sample.itow_ms==1000 && sample.received_ms==50);
  assert(sample.valid_fix && sample.latitude==45 && sample.longitude==9);
  assert(sample.speed_kmh>35.99f && sample.speed_kmh<36.01f);
  for(auto b:frame(1000))if(parser.consume(b,60,sample))++received;
  assert(received==1 && parser.duplicates()==1);
  auto corrupt=frame(1040);corrupt.back()^=1;
  for(auto b:corrupt)if(parser.consume(b,70,sample))++received;
  assert(received==1 && parser.checksum_errors()==1);
  for(auto b:frame(1040,false))if(parser.consume(b,80,sample))++received;
  assert(received==2 && !sample.valid_fix);

  // NAV-SAT >92 bytes: only SVs with C/N0 >0 count as seen, like RLCD.
  // A QZSS SV contributes to the total even without a dedicated UI subtotal.
  std::vector<uint8_t> sat(8+12*12,0);
  sat[4]=1;sat[5]=12;
  const uint8_t systems[]={0,1,2,3,6,5};
  for(unsigned i=0;i<6;++i){sat[8+12*i]=systems[i];sat[10+12*i]=30;}
  assert(feed(parser,packet(0x35,sat),100,sample)==0);
  assert(parser.sat_frames()==1 && parser.satellites().received_ms==100);
  const auto &sv=parser.satellites();
  assert(sv.seen==6 && sv.gps==1 && sv.sbas==1 && sv.galileo==1 && sv.beidou==1 && sv.glonass==1);
  assert(sample.itow_ms==1040 && sample.received_ms==80 && sample.satellites==10);
  auto bad_sat=packet(0x35,sat);bad_sat.back()^=1;
  assert(feed(parser,bad_sat,110,sample)==0 && parser.sat_frames()==1);
  assert(parser.checksum_errors()==2 && sv.received_ms==100);
  auto truncated=sat;truncated.pop_back();
  feed(parser,packet(0x35,truncated),120,sample);
  auto version=sat;version[4]=2;
  feed(parser,packet(0x35,version),130,sample);
  assert(parser.sat_frames()==1 && sv.seen==6);
  std::vector<uint8_t> empty(8,0);empty[4]=1;
  feed(parser,packet(0x35,empty),140,sample);
  assert(parser.sat_frames()==2 && sv.seen==0 && sv.gps==0 && sv.received_ms==140);

  std::vector<uint8_t> dop(18,0);dop[12]=123;
  assert(feed(parser,packet(0x04,dop),150,sample)==0);
  assert(parser.dop_frames()==1 && std::abs(parser.dop().hdop-1.23f)<0.0001f);
  assert(parser.dop().received_ms==150);
  auto bad_dop=packet(0x04,dop);bad_dop.back()^=1;
  feed(parser,bad_dop,160,sample);
  dop.pop_back();feed(parser,packet(0x04,dop),170,sample);
  assert(parser.dop_frames()==1 && parser.dop().received_ms==150);
  dop.resize(18);dop[12]=dop[13]=0xFF;
  feed(parser,packet(0x04,dop),180,sample);
  assert(parser.dop().hdop<0);
  assert(feed(parser,packet(0x22,std::vector<uint8_t>(1200,0)),190,sample)==0);
  feed(parser,packet(0x22,std::vector<uint8_t>(1201,0)),200,sample);
  assert(parser.oversized_frames()==1);
  assert(feed(parser,frame(1080),210,sample)==1 && sample.valid_fix);

  // Rate is measured over real PVT traffic, becomes zero after silence and
  // handles the ESP millis rollover without changing navigation timestamps.
  for(uint32_t start:{uint32_t(100),uint32_t(0xFFFFFF00)}) {
    NavPvtParser rate;rate.update_rate(start);
    for(unsigned n=1;n<=50;++n)feed(rate,frame(n*40U),start+n*40U,sample);
    rate.update_rate(start+2000U);
    assert(std::abs(rate.pvt_hz()-25.0f)<0.001f);
    rate.update_rate(start+4000U);assert(rate.pvt_hz()==0.0f);
  }
  std::cout<<"PASS: PVT, NAV-SAT RLCD counting, DOP, checksum/truncation, bounded payload, recovery and measured rate\n";
}
