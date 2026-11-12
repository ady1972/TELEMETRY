#pragma once
#include "goats_nav_sample_queue.h"
#include "goats_sessions.h"
namespace goats_pipeline {
// RAM-only: both consumers see each complete epoch after byte decoding.
inline void drain(const GoatsTrackUsb *track,const char *date,const char *time) {
  goats_nav_queue::Sample sample;
  while(goats_nav_queue::pop(sample)) {
    if(!GOATS_SESSIONS.accepts_samples())continue;
    if(!goats_sessions_free_active()) {
      goats_diag_v1021::increment(&goats_diag_v1021::Counters::queue_processed);
      goats_laptimer_update(track,sample.fix,sample.lat,sample.lon,sample.speed_kmh,sample.ms,sample.itow);
    }
    GOATS_SESSIONS.update(goats_laptimer_running(),goats_laptimer_lap_number(),
        goats_laptimer_last_lap_ms(),goats_laptimer_best_lap_ms(),goats_laptimer_last_finish_ms(),
        sample.speed_kmh,sample.hdop,sample.satellites,sample.ms,
        track?track->name.c_str():"Circuito",date,time,sample.lat,sample.lon,sample.fix,sample.itow);
  }
}
}
