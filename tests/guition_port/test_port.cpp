#include <cassert>
#include <cstdio>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>
#include "goats_port_types.h"
#include "goats_diagnostics.h"
int64_t fake_us=0;
unsigned log_lines=0;
inline uint32_t millis(){return static_cast<uint32_t>(fake_us/1000);}
inline void taskYIELD(){}
static bool engine_running=true;
inline void goats_laptimer_reset(){engine_running=false;}
inline bool goats_laptimer_running(){return engine_running;}
inline uint32_t goats_laptimer_last_finish_ms(){return 9000;}
inline size_t goats_laptimer_last_timing_sector_count(){return 3;}
inline uint32_t goats_laptimer_last_timing_sector_ms(size_t i){return i==0?2000:3000;}
// Prepared from the actual header; only the SD adapter is replaced for the host.
#include "sessions_host.h"
#include "legacy_sessions_host.h"

int main(){
  using namespace goats_port;
  Ring<int,2> ring;assert(ring.push(1)&&ring.push(2)&&!ring.push(3));
  int v;assert(ring.pop(v)&&v==1&&ring.push(3));assert(ring.pop(v)&&v==2);assert(ring.pop(v)&&v==3&&!ring.pop(v));
  EpochClock clock;assert(clock.observe(604799960));assert(clock.observe(0)&&clock.elapsed()==40);
  assert(!clock.observe(0));assert(clock.observe(80)&&clock.elapsed()==120);
  assert(!clock.observe(40));assert(clock.observe(80)&&clock.elapsed()==160);
  std::vector<SectorLap> laps{{1,8000,{2000,3000,3000}}},decoded;
  auto encoded=encode_sectors(7,laps);assert(decode_sectors(encoded,7,decoded)&&decoded[0].sectors==laps[0].sectors);
  assert(!decode_sectors(encoded,8,decoded));encoded[8]^=1;assert(!decode_sectors(encoded,7,decoded));

  GoatsSessionManager mgr;mgr.setup();
  const unsigned initial_io=goats_sd_storage::io_calls;
  for(unsigned i=0;i<250;++i){
    fake_us=(1000+i*40)*1000ULL;
    mgr.update(true,i>=200?2:1,i>=200?8000:0,i>=200?8000:0,9000,
        60,0.8f,12,millis(),"TRACK","12/11/2026","12:00",45,9,true,
        (604799960U+i*40U)%604800000U);
    if(i==0)assert(goats_sd_storage::io_calls==initial_io); // No I/O in NAV consumer.
    if(i%8==7)mgr.storage_tick();
  }
  mgr.finish_manual(millis());
  assert(!engine_running && mgr.last_save_ok() && !goats_sd_storage::live_open());
  assert(goats_sd_storage::rows.size()==250);
  for(size_t i=0;i<250;++i)assert(goats_sd_storage::rows[i].elapsed_ms==i*40);
  assert(mgr.count()==1 && mgr.display_session(0)->laps[0].sectors_ms==laps[0].sectors);
  assert(goats_sd_storage::rows[199].lap==1&&goats_sd_storage::rows[200].lap==2);
  assert(!mgr.accepts_samples());
  // Original V1.0.20 reader consumes the unchanged GSA3 wire/disk archive.
  LegacyGoatsSessionManager legacy;legacy.setup();assert(legacy.count()==1);
  assert(legacy.display_session(0)->laps[0].lap_time_ms==8000);
  GoatsSessionManager reboot;reboot.setup();assert(reboot.display_session(0)->laps[0].sectors_ms==laps[0].sectors);

  // SD absent: keep timing/metadata and recover the lap journal after restart.
  goats_sd_storage::card_ready=false;GoatsSessionManager no_sd;no_sd.setup();engine_running=true;
  no_sd.update(true,1,0,0,1000,50,1,10,1000,"NO_SD","12/11/2026","13:00",45,9,true,0);
  no_sd.storage_tick();
  no_sd.update(true,2,8000,8000,9000,50,1,10,9000,"NO_SD","12/11/2026","13:00",45,9,true,8000);
  no_sd.finish_manual(9000);assert(no_sd.last_save_ok() && no_sd.trace_dropped()>=1);
  GoatsSessionManager recovery;recovery.setup();assert(recovery.count()>=2);
  assert(recovery.display_session(0)->track_name=="NO_SD");
  assert(recovery.display_session(0)->laps[0].sectors_ms==laps[0].sectors);
  const size_t before=recovery.count();
  recovery.prepare_free(10000,"12/11/2026","14:00");recovery.attach_free_storage();
  recovery.update(false,0,0,0,0,20,1,10,10040,"", "","",45,9,true,8040);
  recovery.discard_current();assert(recovery.count()==before && !recovery.accepts_samples());
  std::puts("PASS: FIFO, epoch wrap, GSE CRC, 25 Hz trace, deferred I/O, lap attribution, legacy GSA3 reader, SD/NVS recovery, discard");
}
