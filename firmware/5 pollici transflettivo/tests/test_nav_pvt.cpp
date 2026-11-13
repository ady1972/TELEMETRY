#include <cassert>
#include <cstddef>
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
}
