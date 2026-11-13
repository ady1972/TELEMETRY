#pragma once
#include <cstdint>
// KEY/BOOT UI navigation following the legacy direction/confirm/back behavior.
// No serial communication with GPS; legacy SD/session menus are not enabled yet.
namespace goats_gps_trace { void finish(bool); bool &recording(); }
namespace goats_menu {
inline int &screen(){static int v=0;return v;} // 0 racing, 1 menu, 2 postlap, 3 tracks, 4 GPS info, 5 best alert
inline int &cursor(){static int v=0;return v;}
inline int &session_offset(){static int v=0;return v;}
inline int &selected_session(){static int v=0;return v;}
inline int &selected_lap(){static int v=0;return v;}
inline bool &discard_confirm(){static bool v=false;return v;}
inline int &lap_cursor(){static int v=0;return v;}
inline int &track_cursor(){static int v=0;return v;}
inline uint32_t &guard_until(){static uint32_t v=0;return v;}
inline bool &armed(){static bool v=false;return v;}
inline uint32_t &key_down(){static uint32_t v=0;return v;}
inline uint32_t &boot_down(){static uint32_t v=0;return v;}
inline bool &key_moved(){static bool v=false;return v;}
inline void init(){guard_until()=millis()+1800;armed()=false;}
inline void arm_if_ready(bool key_released, bool boot_released){
 if(!armed() && (int32_t)(millis()-guard_until())>=0 && key_released && boot_released)armed()=true;
}
inline int count(){return screen()==1?6:screen()==12?2:screen()==13?1:screen()==11?4:screen()==2?4:screen()==5?3:screen()==3?(int)goats_b::state().tracks.size():screen()==6?std::max(1,goats_archive::session_count()):screen()==7?std::max(1,goats_archive::laps_in_session(selected_session())):screen()==8?3:screen()==9?2:screen()==10?4:1;}
inline void move(int step){int n=count();if(n<=0)return;cursor()=(cursor()+step+n)%n;if(screen()==3)track_cursor()=cursor();}
inline void key_press(){if(!armed())return; key_down()=millis();key_moved()=false;if(screen()!=0 && screen()!=4){move(1);key_moved()=true;}}
inline void key_release(){if(!armed())return;uint32_t ms=millis()-key_down();if(key_moved()){key_moved()=false;return;}
 if(screen()==0){if(ms>=700){screen()=1;cursor()=0;}return;}
 if(screen()==4){screen()=1;cursor()=0;return;}
 if(screen()==12 && ms>=700){screen()=1;cursor()=4;return;}
 if(screen()==8 && ms>=700){screen()=0;cursor()=0;return;}
 if(ms>=700)move(-1);
}
inline void boot_press(){if(!armed())return;boot_down()=millis();}
inline void finish(bool save){
 if(!goats_dual_core::wait_idle())return;
 if(!save && !goats_archive::discard_current()) {screen()=9;cursor()=0;return;}
 if(goats_dual_core::lock(portMAX_DELAY)){
  goats_gps_trace::finish(save);
  goats_dual_core::unlock();
 }
 goats_session_ctl::stop();goats_laptimer_reset();
 auto &s=goats_b::state();s.running=false;s.have_prev=false;s.laps=0;s.armed=true;
 s.last_lap=s.best_lap=0;s.last_cross=0;
 goats_archive::next_session();screen()=0;cursor()=0;
}
inline void boot_release(){if(!armed())return;uint32_t held=millis()-boot_down();bool longp=held>=800;
 if(screen()==0 && held>=3000){screen()=8;cursor()=0;return;}

 if(longp){if(screen()==0)return;if(screen()==1)screen()=0;else if(screen()==8){screen()=0;cursor()=0;}else if(screen()==9){screen()=8;cursor()=1;}else if(screen()==10){screen()=11;cursor()=2;}else if(screen()==11){screen()=1;cursor()=0;}else if(screen()==12 || screen()==13){screen()=1;cursor()=4;}else if(screen()==14){screen()=7;cursor()=selected_lap();}else if(screen()==7){screen()=6;cursor()=selected_session();}else if(screen()==2 || screen()==5){screen()=11;cursor()=0;}else {screen()=1;cursor()=0;}return;}
 if(screen()==0){screen()=1;cursor()=0;return;}
 if(screen()==12){
   if(cursor()==0){
     if(goats_session_ctl::has_started() || goats_gps_trace::recording() || goats_sd_storage::live_open()){
       screen()=13;cursor()=0;return;
     }
     if(!goats_dual_core::wait_idle()){screen()=13;cursor()=0;return;}
     if(goats_dual_core::lock(portMAX_DELAY)){
       bool ok=goats_usb_msc::request_reboot();
       goats_dual_core::unlock();
       if(!ok){screen()=13;cursor()=0;}
     }
   }else{screen()=1;cursor()=4;}
   return;
 }
 if(screen()==13){screen()=1;cursor()=4;return;}
 if(screen()==8){if(cursor()==0)finish(true);else if(cursor()==1){screen()=9;cursor()=0;}else {screen()=0;cursor()=0;}return;}
 if(screen()==9){if(cursor()==0)finish(false);else {screen()=8;cursor()=1;}return;}
 if(screen()==10){if(cursor()==0)goats_session_ctl::auto_timeout_ms()=30000;else if(cursor()==1)goats_session_ctl::auto_timeout_ms()=60000;else if(cursor()==2)goats_session_ctl::auto_timeout_ms()=90000;screen()=11;cursor()=2;return;}
 if(screen()==1){switch(cursor()){
  case 0:screen()=11;cursor()=0;break;
  case 1:screen()=3;cursor()=goats_b::state().active_track<0?0:goats_b::state().active_track;break;
  case 2:screen()=4;cursor()=0;break;
  case 3:screen()=6;cursor()=0;break;
  case 4:screen()=12;cursor()=1;break;
  default:screen()=0;cursor()=0;break;
 }return;}
 if(screen()==11){switch(cursor()){
  case 0:screen()=2;cursor()=0;break;
  case 1:screen()=5;cursor()=0;break;
  case 2:screen()=10;cursor()=1;break;
  default:screen()=1;cursor()=0;break;
 }return;}
 if(screen()==2){switch(cursor()){
 case 0:goats_ui::mode()=(goats_ui::mode()+1)%3;break;
 case 1:goats_ui::duration_ms()=goats_ui::duration_ms()>=30000?3000:goats_ui::duration_ms()+1000;break;
 case 2:goats_ui::content()=1-goats_ui::content();break;
 default:screen()=11;cursor()=0;break;
 }return;}
 if(screen()==5){switch(cursor()){
 case 0:goats_ui::best_enabled()=!goats_ui::best_enabled();break;
 case 1:goats_ui::best_duration_ms()=goats_ui::best_duration_ms()>=10000?1000:goats_ui::best_duration_ms()+1000;break;
 default:screen()=11;cursor()=1;break;
 }return;}
 if(screen()==3){auto &s=goats_b::state();if(cursor()>=0 && cursor()<(int)s.tracks.size()){
 s.active_track=cursor();s.manual_track=true;s.have_prev=false;s.running=false;s.laps=0;s.best_lap=s.last_lap=0;
 goats_laptimer_reset();} screen()=1;cursor()=0;return;}
 if(screen()==6){if(goats_archive::session_count()>0){selected_session()=cursor();screen()=7;cursor()=0;}return;}
 if(screen()==7){if(goats_archive::laps_in_session(selected_session())>0){selected_lap()=cursor();screen()=14;cursor()=0;}return;}
 if(screen()==14){screen()=7;cursor()=selected_lap();return;}
 if(screen()==4){screen()=1;cursor()=0;}
}
}
