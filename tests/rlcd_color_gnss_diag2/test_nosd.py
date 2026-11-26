"""No-SD facades cannot touch storage; preserve non-SD session date capture."""
from pathlib import Path
import subprocess,tempfile
ROOT=Path(__file__).resolve().parents[2]
PORT=ROOT/'firmware/rlcd-42-3-colori/GOATS_RLCD_COLOR_RC3_3_GNSS2_NOSD'
with tempfile.TemporaryDirectory(prefix='rc33-nosd-api-') as tmp:
 t=Path(tmp);(t/'driver').mkdir()
 (t/'driver/usb_serial_jtag.h').write_text('''#pragma once
#include <string>
inline std::string usb_reply;
inline int usb_serial_jtag_write_bytes(const char *p,unsigned n,unsigned){usb_reply.append(p,n);return n;}
''')
 # Isolate the real trace facade body from its already separately tested NVS/time headers.
 trace='\n'.join(l for l in (PORT/'goats_gps_trace.h').read_text().splitlines() if not l.startswith('#include "'))
 cpp=t/'test.cpp';cpp.write_text('''#include <cassert>
#include <cstdint>
#include "goats_sd_storage.h"
#include "goats_sd_r14_bridge.h"
#include "goats_sd_usb_export.h"
#include "goats_usb_msc.h"
namespace goats_clock {inline int latest=42;}
namespace goats_clock_runtime {inline unsigned ticks=0;inline void tick(){++ticks;}}
namespace goats_archive {inline unsigned session(){return 7;}}
namespace goats_session_ctl {inline bool paused_flag=false,started=false;inline bool paused(){return paused_flag;}inline bool has_started(){return started;}}
namespace goats_dates {inline unsigned captures=0,ticks=0;inline void capture(unsigned sid,int date){assert(sid==7 && date==42);++captures;}inline void tick(){++ticks;}}
'''+trace+'''
int main(){
 for(unsigned i=0;i<100;i++){
  goats_sd_r14_bridge::begin();goats_sd_r14_bridge::save_lap(1,i,10000,9000,50,"TEST");
  assert(!goats_sd_storage::ready() && !goats_sd_storage::writable() && !goats_sd_storage::live_open());
  assert(!goats_usb_msc::active() && !goats_usb_msc::boot_if_requested() && !goats_usb_msc::request_reboot());
  assert(goats_gps_trace::drain_for_save() && !goats_gps_trace::recording());
 }
 assert(goats_sd_r14_bridge::errors==0 && goats_sd_r14_bridge::writes==0);
 assert(!goats_sd_usb_export::handle_command("GTRK_GET") && usb_reply.empty());
 assert(goats_sd_usb_export::handle_command("GSD_LIST") && usb_reply=="GSD_ERR SD_DISABLED\\n");
 goats_gps_trace::on_pvt(nullptr,true,0,0,0,0,0,0,nullptr);assert(goats_dates::captures==0);
 goats_session_ctl::started=true;
 goats_gps_trace::on_pvt(nullptr,true,0,0,0,0,0,0,nullptr);assert(goats_dates::captures==1);
 goats_session_ctl::paused_flag=true;
 goats_gps_trace::on_pvt(nullptr,true,0,0,0,0,0,0,nullptr);assert(goats_dates::captures==1);
 goats_session_ctl::paused_flag=false;
 goats_gps_trace::on_pvt(nullptr,false,0,0,0,0,0,0,nullptr);assert(goats_dates::captures==1);
 goats_gps_trace::tick();assert(goats_dates::ticks==1 && goats_clock_runtime::ticks==1);
 goats_gps_trace::finish(true);goats_gps_trace::finish(false);assert(goats_gps_trace::drain_for_save());
}
''')
 exe=t/'test';subprocess.run(['g++','-std=c++17','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(t),'-I'+str(PORT),str(cpp),'-o',str(exe)],check=True);subprocess.run([str(exe)],check=True)
print('PASS: no SD mount/write/reboot/error loops, SD commands report unavailable, session dating and clocks retained')
