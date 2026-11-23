#pragma once
#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <vector>
namespace goats_port {
template<class T, size_t Capacity> class Ring {
 public:
  bool push(const T &v) { if(size_==Capacity)return false; items_[(read_+size_)%Capacity]=v; ++size_;return true; }
  bool pop(T &v) { if(!size_)return false;v=items_[read_];read_=(read_+1)%Capacity;--size_;return true; }
  const T *front() const { return size_?&items_[read_]:nullptr; }
  size_t size() const { return size_; }
  bool empty() const { return size_==0; }
  void clear() { read_=size_=0; }
 private:
  std::array<T,Capacity> items_{}; size_t read_{0},size_{0};
};
// Trace clock only: no change to the timing engine's sample.ms timebase.
class EpochClock {
 public:
  void reset(){have_=false;last_=elapsed_=0;}
  bool observe(uint32_t itow){
    constexpr uint32_t week=604800000U;
    if(itow>=week)return false;
    if(!have_){have_=true;last_=itow;return true;}
    const uint32_t step=itow>=last_?itow-last_:week-last_+itow;
    last_=itow;
    if(step==0 || step>week/2)return false;
    elapsed_+=step;return true;
  }
  uint32_t elapsed()const{return elapsed_;}
 private:
  bool have_{false};uint32_t last_{0},elapsed_{0};
};
struct SectorLap { uint16_t number{0};uint32_t lap_ms{0};std::vector<uint32_t> sectors; };
inline uint32_t crc32(const uint8_t*p,size_t n){
  uint32_t c=~0U;while(n--){c^=*p++;for(unsigned b=0;b<8;++b)c=(c>>1)^(0xEDB88320U&(0U-(c&1U)));}return ~c;
}
inline void put(std::vector<uint8_t>&v,uint32_t x,unsigned n){while(n--){v.push_back(static_cast<uint8_t>(x));x>>=8;}}
inline bool get(const std::vector<uint8_t>&v,size_t&at,uint32_t&x,unsigned n){
  if(at+n>v.size())return false;x=0;for(unsigned i=0;i<n;++i)x|=uint32_t(v[at++])<<(8*i);return true;
}
inline std::vector<uint8_t> encode_sectors(uint32_t sid,const std::vector<SectorLap>&laps){
  std::vector<uint8_t>v{'G','S','E','1'};put(v,sid,4);put(v,static_cast<uint32_t>(laps.size()),2);
  for(const auto&l:laps){put(v,l.number,2);put(v,l.lap_ms,4);put(v,static_cast<uint32_t>(l.sectors.size()),1);for(auto ms:l.sectors)put(v,ms,4);}
  put(v,crc32(v.data(),v.size()),4);return v;
}
inline bool decode_sectors(const std::vector<uint8_t>&v,uint32_t sid,std::vector<SectorLap>&out){
  if(v.size()<14||std::memcmp(v.data(),"GSE1",4))return false;
  size_t at=v.size()-4;uint32_t checksum=0;
  if(!get(v,at,checksum,4)||checksum!=crc32(v.data(),v.size()-4))return false;
  at=4;uint32_t stored=0,count=0;
  if(!get(v,at,stored,4)||stored!=sid||!get(v,at,count,2)||count>80)return false;
  std::vector<SectorLap> result;
  for(uint32_t i=0;i<count;++i){
    SectorLap l;uint32_t number=0,n=0;
    if(!get(v,at,number,2)||!number||!get(v,at,l.lap_ms,4)||!get(v,at,n,1)||n>13)return false;
    l.number=static_cast<uint16_t>(number);
    for(uint32_t j=0;j<n;++j){uint32_t ms=0;if(!get(v,at,ms,4))return false;l.sectors.push_back(ms);}
    for(const auto&prev:result)if(prev.number==l.number)return false;
    result.push_back(l);
  }
  if(at!=v.size()-4)return false;out=std::move(result);return true;
}
}
