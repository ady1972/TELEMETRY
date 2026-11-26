"""Exercise the real menu finalizer, racing bridge and lap engine across sessions."""
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[2]
variant = sys.argv[1] if len(sys.argv) > 1 else 'GOATS_RLCD_RC2'
firmware = root / variant if '/' in variant else root / 'firmware/rlcd-42' / variant
source = (firmware / 'goats_legacy_menu_ui.h').read_text()
start = source.index('inline void finish(bool save){')
end = source.index('inline void boot_release()', start)
finalizer = source[start:end]
staged = 'inline constexpr int CLOSING_SCREEN=16;' in source
key_handlers = ''
boot_handlers = ''
if staged:
    key_handlers = source[source.index('inline void key_press()'):source.index('inline void boot_press()')]
    boot_handlers = source[source.index('inline void boot_release()'):
                           source.index(' if(screen()==10){if(cursor()==0)')]
    boot_handlers += '}'


harness = r'''
#include <cassert>
#include <cstdint>
#include <string>
#include <vector>
uint32_t now_ms=1000;
uint32_t millis(){return now_ms;}
template<typename... Args> void host_log(Args...){}
#define ESP_LOGI(...) host_log(__VA_ARGS__)
#include "goats_laptimer.h"
#include "goats_session_control.h"
#ifdef EXPECT_STAGED_CLOSE
#include "goats_screen_mode.h"
#endif
namespace goats_b {
struct Sector {std::string name;double a,b,c,d;};
struct Track {std::string name;double a,b,c,d;float radius;uint8_t direction;std::vector<Sector> sectors;};
struct State {
 std::vector<Track> tracks{{"TEST",45.0,8.9999,45.0,9.0001,20,0,{}}};
 std::vector<uint8_t> raw;int active_track=0;
 bool running=false,have_prev=false,armed=true;unsigned laps=0,last_lap=0,best_lap=0,last_cross=0;
};
State &state(){static State s;return s;}
uint32_t crc32(const uint8_t*,size_t){return 0;}
}
#include "goats_racing_bridge.h"
namespace goats_archive {
unsigned session_id=1; bool discard_ok=true;
bool discard_current(){return discard_ok;}
bool next_session(){++session_id;return true;}
}
namespace goats_gps_trace {
unsigned saves=0,discards=0;
bool recording(){return false;}
void finish(bool save){if(save)++saves;else ++discards;}
}
#ifdef EXPECT_STAGED_CLOSE
namespace goats_sd_storage {bool live_open(){return false;}}
namespace goats_usb_msc {bool request_reboot(){assert(false);return false;}}
#endif
namespace goats_menu {
int &screen(){static int s=0;return s;}
int &cursor(){static int s=0;return s;}
#ifdef EXPECT_STAGED_CLOSE
inline constexpr int CLOSING_SCREEN=16;
bool &armed(){static bool value=true;return value;}
bool &key_moved(){static bool value=false;return value;}
uint32_t &key_down(){static uint32_t value=0;return value;}
uint32_t &boot_down(){static uint32_t value=0;return value;}
void move(int step){cursor()+=step;}
int selected_lap(){return 0;}
int selected_session(){return 0;}
KEY_HANDLERS
#endif
FINALIZER
#ifdef EXPECT_STAGED_CLOSE
BOOT_HANDLERS
#endif
}
void point(double lat,bool valid=true){
 now_ms+=20000;
 goats_racing::consume(valid,lat,9.0,40,now_ms);
}
void start_session(){
 point(44.9995);point(45.0005);
 assert(goats_laptimer_running());
 assert(goats_session_ctl::has_started());
}
int main(){
#ifdef EXPECT_STAGED_CLOSE
 goats_menu::key_press();now_ms+=100;goats_menu::key_release();
 assert(goats_screen_mode::delta() && goats_menu::screen()==0);
 goats_menu::key_press();now_ms+=100;goats_menu::key_release();
 assert(!goats_screen_mode::delta() && goats_menu::screen()==0);
 goats_menu::key_press();now_ms+=700;goats_menu::key_release();
 assert(!goats_screen_mode::delta() && goats_menu::screen()==0);
 goats_menu::boot_down()=now_ms;now_ms+=100;goats_menu::boot_release();
 assert(goats_menu::screen()==1);
 goats_menu::key_press();now_ms+=100;goats_menu::key_release();
 assert(!goats_screen_mode::delta() && goats_menu::cursor()==1);
 goats_menu::screen()=0;
#endif
 start_session();
 for(bool save:{true,true,false}){
  unsigned old_id=goats_archive::session_id;
#ifdef EXPECT_STAGED_CLOSE
  const unsigned saves=goats_gps_trace::saves;
  const unsigned discards=goats_gps_trace::discards;
  goats_menu::armed()=true;
  goats_menu::boot_down()=now_ms;now_ms+=3000;goats_menu::boot_release();
  assert(goats_menu::screen()==8);
  if(!save){
   goats_menu::key_press();now_ms+=100;goats_menu::key_release();
   goats_menu::boot_down()=now_ms;now_ms+=100;goats_menu::boot_release();
   assert(goats_menu::screen()==9);
  }
  goats_menu::boot_down()=now_ms;now_ms+=100;goats_menu::boot_release();
  assert(goats_menu::save_requested()==save);
  assert(goats_menu::screen()==goats_menu::CLOSING_SCREEN && !goats_menu::armed());
  assert(goats_session_ctl::paused() && goats_session_ctl::has_started());
  assert(goats_archive::session_id==old_id);
  assert(goats_gps_trace::saves==saves && goats_gps_trace::discards==discards);
#endif
  goats_menu::finish(save);
  assert(goats_archive::session_id==old_id+1);
  assert(!goats_session_ctl::paused());
  assert(!goats_session_ctl::has_started());
  assert(!goats_laptimer_running());
  assert(goats_menu::screen()==0);
#ifdef EXPECT_LAP_SPEED_RESET
  assert(goats_lap_speed::current()==0 && std::isnan(goats_lap_speed::last()));
#endif
  point(44.9995,false);
  assert(!goats_session_ctl::has_started());
  start_session(); // Same track, no reboot or catalogue change.
  point(45.0006);point(44.9995);
  assert(goats_laptimer_last_lap_ms()>0);
  assert(goats_lap_speed::last()==40);
 }
 assert(goats_gps_trace::saves==2 && goats_gps_trace::discards==1);
 // A rejected discard must leave the current session running.
 goats_archive::discard_ok=false;
#ifdef EXPECT_STAGED_CLOSE
 goats_menu::request_finish(false);
#endif
 goats_menu::finish(false);
 assert(goats_menu::screen()==9 && goats_laptimer_running() && !goats_session_ctl::paused());
}
'''.replace('FINALIZER', finalizer).replace('KEY_HANDLERS', key_handlers).replace('BOOT_HANDLERS', boot_handlers)
with tempfile.TemporaryDirectory() as tmp:
    cpp=Path(tmp)/'restart.cpp'
    cpp.write_text(harness)
    exe=Path(tmp)/'restart'
    flags = ['-DEXPECT_LAP_SPEED_RESET'] if 'goats_lap_speed::reset();' in finalizer else []
    if staged:
        flags.extend(['-DEXPECT_STAGED_CLOSE', '-I', str(root/'tests/rc2/screen_mode_stubs')])
    subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-Wno-unused-variable',
                    *flags,'-I',str(firmware),str(cpp),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
print('PASS: RLCD save/save/discard -> next finish crossing and timed lap without reboot; failed discard preserves session')
