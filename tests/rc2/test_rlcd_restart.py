"""Exercise the real menu finalizer, racing bridge and lap engine across sessions."""
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[2]
variant = sys.argv[1] if len(sys.argv) > 1 else 'GOATS_RLCD_RC2'
firmware = root / 'firmware/rlcd-42' / variant
source = (firmware / 'goats_legacy_menu_ui.h').read_text()
start = source.index('inline void finish(bool save){')
end = source.index('inline void boot_release()', start)
finalizer = source[start:end]
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
void finish(bool save){if(save)++saves;else ++discards;}
}
namespace goats_menu {
int &screen(){static int s=0;return s;}
int &cursor(){static int s=0;return s;}
FINALIZER
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
 start_session();
 for(bool save:{true,true,false}){
  unsigned old_id=goats_archive::session_id;
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
 goats_menu::finish(false);
 assert(goats_menu::screen()==9 && goats_laptimer_running());
}
'''.replace('FINALIZER', finalizer)
with tempfile.TemporaryDirectory() as tmp:
    cpp=Path(tmp)/'restart.cpp'
    cpp.write_text(harness)
    exe=Path(tmp)/'restart'
    flags = ['-DEXPECT_LAP_SPEED_RESET'] if variant == 'GOATS_RLCD_RC3_1' else []
    subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-Wno-unused-variable',
                    *flags,'-I',str(firmware),str(cpp),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
print('PASS: RLCD save/save/discard -> next finish crossing and timed lap without reboot; failed discard preserves session')
