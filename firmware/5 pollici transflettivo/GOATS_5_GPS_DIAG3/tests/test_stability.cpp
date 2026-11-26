#include <cassert>
#include <vector>
#include "goats_gps_stability.h"
using goats_gps_diag::Stability;
static std::vector<uint8_t> nav(uint32_t itow,uint8_t type=3,bool ok=true){
 std::vector<uint8_t>p(92);for(unsigned i=0;i<4;i++)p[i]=uint8_t(itow>>(8*i));p[20]=type;p[21]=ok;return p;
}
static void pvt(Stability&s,uint32_t now,uint32_t tow,uint8_t type=3,bool ok=true){auto p=nav(tow,type,ok);s.frame(1,7,p.data(),p.size(),now);}
int main(){
 Stability s;assert(!s.pvt_fresh(0) && !s.dop_fresh(0) && !s.sat_fresh(0));
 s.tick(50000);assert(s.stream_losses==0 && s.fix_losses==0);
 for(unsigned i=0;i<100;i++)pvt(s,1000+40*i,1000+40*i);
 assert(s.fix_active && s.fix_type==3 && s.fix_losses==0 && s.stream_losses==0);
 assert(s.step_ms==40 && s.max_gap_ms==40 && s.continuous_fix_ms()==3960);
 assert(s.pvt_fresh(6460));s.tick(6460);assert(s.fix_active);
 s.tick(6461);assert(!s.fix_active && s.stream_losses==1 && s.fix_losses==1);
 s.tick(20000);assert(s.stream_losses==1 && s.fix_losses==1);
 pvt(s,20000,20000,0,false);assert(!s.fix_active && s.fix_losses==1);
 pvt(s,20040,20040,2);assert(s.fix_active && s.continuous_fix_ms()==0);
 pvt(s,20080,20080,2);assert(s.continuous_fix_ms()==40);
 pvt(s,20120,20120,3,false);assert(!s.fix_active && s.fix_losses==2 && s.stream_losses==1);
 pvt(s,20160,20160,5,true);assert(!s.fix_active); // Time-only is not a position fix.
 pvt(s,20200,20200,1,true);assert(!s.fix_active); // DR-only is not GNSS position.
 pvt(s,20240,20240,4,true);assert(s.fix_active);
 // A gap ending in a packet is counted without requiring an intervening tick.
 pvt(s,24000,24000);assert(s.stream_losses==2 && s.fix_losses==3 && s.fix_active);
 assert(s.continuous_fix_ms()==0 && s.longest_fix_ms==3960);
 std::vector<uint8_t>dop(18),sat(8);
 s.frame(1,4,dop.data(),17,24000);s.frame(1,0x35,sat.data(),7,24000);
 assert(!s.have_dop && !s.have_sat);
 s.frame(1,4,dop.data(),18,24000);s.frame(1,0x35,sat.data(),8,24000);
 assert(s.dop_fresh(29000) && s.sat_fresh(29000));
 assert(!s.dop_fresh(29001) && !s.sat_fresh(29001));
 // Lower actual navigation frequency must not be mistaken for lost epochs.
 Stability slow;for(unsigned i=0;i<50;i++)pvt(slow,1000+200*i,1000+200*i);
 assert(slow.step_ms==200 && !slow.stream_losses && !slow.fix_losses);
 Stability wrap;pvt(wrap,0xfffffff0,604799960);pvt(wrap,24,0);
 assert(wrap.step_ms==40 && wrap.max_gap_ms==40 && wrap.fix_active && !wrap.stream_losses);
 assert(wrap.continuous_fix_ms()==40 && wrap.pvt_fresh(24));
 pvt(wrap,64,0);assert(wrap.duplicates==1 && wrap.step_ms==0);
 pvt(wrap,104,10000);pvt(wrap,144,9000);assert(wrap.time_restarts==1 && !wrap.have_step);
}
