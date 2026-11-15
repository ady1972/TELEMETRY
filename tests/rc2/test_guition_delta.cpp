#include <cstdio>
#include <cassert>
#include <cmath>
#include <algorithm>
#include <vector>
#include <cstdint>
uint32_t wall_ms=0;
uint32_t millis(){return wall_ms;}
#include "goats_track_types.h"
#include "goats_laptimer.h"
int main(){
 GoatsTrackUsb track;track.name="synthetic loop";
 track.start_lat=track.finish_lat=45.0;
 track.start_lon=9.0008;track.finish_lon=9.0012;track.trigger_radius_m=20;
 for(bool slower:{false,true}) for(unsigned batch:{40u,200u,400u}){
  GoatsLaptimerEngine engine;engine.reset();
  float lo=1e9,hi=-1e9,jump=0,prev=NAN;unsigned n=0;
  for(unsigned i=0;i<1500*4;++i){
   unsigned t=i*40;
   wall_ms=1000+((t+batch-1)/batch)*batch;
   double turns=slower && t>=120000 ? 2.0+(t-120000)/66000.0 : double(i)/1500.0;
   double phase=2*3.141592653589793*turns-0.1;
   const float before=engine.live_delta_seconds();
   const uint32_t previous_ms=(i==0?0:1000+(((i-1)*40+batch-1)/batch)*batch);
   engine.update(&track,true,45.0+.001*std::sin(phase),9.0+.001*std::cos(phase),40,wall_ms,t);
   float d=engine.live_delta_seconds();
   if(previous_ms==wall_ms && std::isfinite(before) && std::isfinite(d)) assert(d==before);
   if(i>3200 && i%1500>200 && i%1500<1300 && std::isfinite(d)){
    lo=std::min(lo,d);hi=std::max(hi,d);if(std::isfinite(prev))jump=std::max(jump,std::abs(d-prev));prev=d;++n;
   }else prev=NAN;
  }
  assert(n>1000);
  if(slower) assert(hi>0.5f); // A real loss must still change the displayed delta.
  printf("slower=%d decode batch=%ums: trajectory delta min=%.6f max=%.6f range=%.6f max_step=%.6f samples=%u\n",slower,batch,lo,hi,hi-lo,jump,n);
 }
}
