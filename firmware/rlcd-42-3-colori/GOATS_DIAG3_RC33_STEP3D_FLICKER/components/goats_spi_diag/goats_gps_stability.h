#pragma once
#include <cstdint>
#include <cstddef>
namespace goats_gps_diag {
// Observes validated UBX only. All times use the same Arduino clock as DIAG2.
struct Stability {
  bool have_pvt{false},link_active{false},fix_active{false},have_dop{false},have_sat{false};
  bool have_step{false},fix_ok{false};uint8_t fix_type{0};
  uint32_t last_pvt{0},last_dop{0},last_sat{0},last_itow{0};
  uint32_t fix_since{0},last_fix_pvt{0},longest_fix_ms{0};
  uint32_t fix_losses{0},stream_losses{0},gap_ms{0},max_gap_ms{0};
  uint32_t step_ms{0},duplicates{0},time_restarts{0};
  bool pvt_fresh(uint32_t now)const{return have_pvt && uint32_t(now-last_pvt)<=1500;}
  bool dop_fresh(uint32_t now)const{return have_dop && uint32_t(now-last_dop)<=5000;}
  bool sat_fresh(uint32_t now)const{return have_sat && uint32_t(now-last_sat)<=5000;}
  uint32_t continuous_fix_ms()const{return fix_active?uint32_t(last_fix_pvt-fix_since):0;}
  void lose_fix(){if(fix_active){++fix_losses;fix_active=false;}}
  void tick(uint32_t now){
    if(link_active && uint32_t(now-last_pvt)>1500){
      ++stream_losses;link_active=false;lose_fix();
    }
  }
  void frame(uint8_t cls,uint8_t id,const uint8_t *p,size_t n,uint32_t now){
    if(cls!=1)return;
    if(id==4 && n>=18){have_dop=true;last_dop=now;return;}
    if(id==0x35 && n>=8){have_sat=true;last_sat=now;return;}
    if(id!=7 || n<92)return;
    tick(now); // Count a real gap even if it ends before another loop tick.
    const uint32_t tow=uint32_t(p[0])|(uint32_t(p[1])<<8)|(uint32_t(p[2])<<16)|(uint32_t(p[3])<<24);
    if(have_pvt){
      gap_ms=uint32_t(now-last_pvt);if(gap_ms>max_gap_ms)max_gap_ms=gap_ms;
      if(tow>=last_itow){step_ms=tow-last_itow;have_step=true;if(!step_ms)++duplicates;}
      else if(last_itow>604740000U && tow<60000U){step_ms=604800000U-last_itow+tow;have_step=true;}
      else{++time_restarts;have_step=false;step_ms=0;}
    }
    have_pvt=true;link_active=true;last_pvt=now;last_itow=tow;
    fix_type=p[20];fix_ok=(p[21]&1U)!=0;
    // Distinguish a position fix from time-only or dead-reckoning-only modes.
    const bool position=fix_ok && (fix_type==2 || fix_type==3 || fix_type==4);
    if(position){
      if(!fix_active){fix_active=true;fix_since=now;}
      last_fix_pvt=now;
      const uint32_t length=continuous_fix_ms();if(length>longest_fix_ms)longest_fix_ms=length;
    }else lose_fix();
  }
  const char *fix_name()const{
    if(!fix_active)return "NO FIX";
    return fix_type==2?"FIX 2D":fix_type==3?"FIX 3D":"FIX GNSS+DR";
  }
};
inline Stability stability;
} // namespace goats_gps_diag
