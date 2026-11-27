#pragma once
#ifdef GOATS_RC33_STEP1_IMPL
#include <cmath>
#include <cstdint>
#include <cstring>
#include <array>
// Memoize only bit-identical cosine arguments. No approximation or rate change.
namespace goats_core_cache {
inline bool enabled=true;
inline uint32_t requests=0,evaluations=0;
struct CosMemo {
 uint64_t key=0;double value=0;bool ready=false;
 double get(double angle){
  ++requests;uint64_t bits;static_assert(sizeof(bits)==sizeof(angle));memcpy(&bits,&angle,sizeof(bits));
  if(enabled&&ready&&bits==key)return value;
  ++evaluations;const double result=std::cos(angle);
  if(enabled){key=bits;value=result;ready=true;}return result;
 }
};
inline std::array<CosMemo,50> auto_track;
inline CosMemo bridge_xy,engine_xy;
inline double track_cos(size_t index,double angle){
 if(index<auto_track.size())return auto_track[index].get(angle);
 ++requests;++evaluations;return std::cos(angle);
}
inline void set_enabled(bool value){enabled=value;}
inline unsigned hit_percent(){return requests?unsigned(uint64_t(requests-evaluations)*100/requests):0;}
struct Timing {
 uint32_t at=0,samples=0,total_us=0,maximum_us=0,mean_us=0,peak_us=0;
 void observe(uint32_t duration,uint32_t now){
  if(!samples)at=now;
  ++samples;total_us+=duration;if(duration>maximum_us)maximum_us=duration;
  if(uint32_t(now-at)>=1000){mean_us=total_us/samples;peak_us=maximum_us;samples=total_us=maximum_us=0;}
 }
};
inline Timing timing;
}
#endif
