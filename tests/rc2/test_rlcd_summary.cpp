#include <cassert>
#include <cmath>
#include <string>
#include "nvs.h"
using esp_err_t=int;
constexpr int NVS_READONLY=1;
struct EngineStub {uint32_t last_timing_sector_ms(size_t i){return 1000+i;}} GOATS_LAPTIMER;
namespace goats_b {inline void reply(const char*){}}
#include "goats_session_archive.h"
#include "goats_lap_speed_stats.h"
static_assert(sizeof(goats_archive::Record)==72,"Legacy NVS record layout must stay unchanged");
int main(){
 using namespace goats_archive;
 goats_lap_speed::reset();goats_lap_speed::observe(55);goats_lap_speed::observe(90);
 goats_lap_speed::observe(NAN);goats_lap_speed::observe(-5);goats_lap_speed::complete();
 assert(goats_lap_speed::last()==90 && goats_lap_speed::current()==0);
 goats_lap_speed::observe(40);goats_lap_speed::complete();assert(goats_lap_speed::last()==40);
 setup();assert(ready());
 assert(save(1,60000,60000,50,"TRACK",90));
 assert(save(2,50000,50000,60,"TRACK",100));
 assert(save(3,50000,50000,59,"TRACK",95));
 Record r{};float maximum=0;
 assert(lap_in_session(0,0,r)&&maximum_for(r,maximum)&&maximum==90);
 assert(best_retained_ms(0)==50000); // Both tied fastest laps can be marked.
 // Cold boot clears RAM and reloads companion records without changing Record.
 invalidate_cache();setup();assert(session_count()==1);
 assert(lap_in_session(0,1,r)&&maximum_for(r,maximum)&&maximum==100);
 assert(save(1,70000,70000,40,"NEXT",75));
 assert(discard_current());assert(session_count()==1);
 assert(lap_in_session(0,2,r)&&maximum_for(r,maximum)&&maximum==95);
 // Legacy records have no companion metadata; truncated/stale metadata is ignored.
 fake_nvs.erase("max00");invalidate_cache();
 assert(lap_in_session(0,0,r)&&!maximum_for(r,maximum));
 MaxRecord wrong{r.session+1,r.lap,r.lap_ms,190};
 fake_nvs["max00"]={reinterpret_cast<uint8_t*>(&wrong),reinterpret_cast<uint8_t*>(&wrong)+sizeof(wrong)};
 invalidate_cache();assert(!maximum_for(r,maximum));
 wrong.session=r.session;
 fake_nvs["max00"]={reinterpret_cast<uint8_t*>(&wrong),reinterpret_cast<uint8_t*>(&wrong)+12};
 invalidate_cache();assert(!maximum_for(r,maximum));
 // More than one ring revolution must never associate an old maximum with a new lap.
 for(unsigned i=0;i<85;++i)assert(save(i+1,80000+i,80000,45,"RING",80+i));
 assert(count()==80 && laps_in_session(0)==80);
 for(int i=0;i<80;++i){assert(lap_in_session(0,i,r));assert(maximum_for(r,maximum));assert(maximum==80+(r.lap-1));}
 invalidate_cache();setup();assert(lap_in_session(0,79,r)&&maximum_for(r,maximum)&&maximum==164);
}
