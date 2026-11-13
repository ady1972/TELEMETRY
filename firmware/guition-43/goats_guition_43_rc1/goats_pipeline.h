#pragma once
#include "goats_nav_sample_queue.h"
#include "goats_sessions.h"
namespace goats_pipeline {
inline void observe_track(const GoatsTrackUsb *track) {
  static uint32_t seen_revision=goats_track_revision();
  static const GoatsTrackUsb *seen_track=nullptr;
  const uint32_t revision=goats_track_revision();
  if(track!=seen_track || revision!=seen_revision) {
    // Catalog replacement may reuse addresses. Observe its revision as RLCD
    // does; never mix two tracks in one saved Guition session.
    if(goats_sessions_active() && !goats_sessions_free_active())
      GOATS_SESSIONS.request_finish(millis()); // RAM only; I/O is deferred.
    else if(!goats_sessions_free_active())goats_laptimer_reset();
    seen_track=track;seen_revision=revision;
  }
}
// RAM-only: both consumers see each complete epoch after byte decoding.
inline void drain(const GoatsTrackUsb *track,const char *date,const char *time) {
  observe_track(track);
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
