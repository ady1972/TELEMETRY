#pragma once
#include "goats_diagnostics.h"
#include "goats_port_types.h"
#include <cstdint>
namespace goats_nav_queue {
struct Sample { bool fix; double lat, lon; float speed_kmh; uint32_t ms,itow; float hdop; uint8_t satellites; };
static goats_port::Ring<Sample,512> samples;
static bool have_itow=false;
static uint32_t last_itow=0;
static inline void push(bool fix, double lat, double lon, float speed, uint32_t ms,
                        uint32_t itow,float hdop,uint8_t satellites) {
  // RLCD rule: suppress consecutive repeated epochs, including invalid fixes.
  if(have_itow && itow==last_itow)return;
  have_itow=true;last_itow=itow;
  if (!samples.push({fix,lat,lon,speed,ms,itow,hdop,satellites})) {
    goats_diag_v1021::increment(&goats_diag_v1021::Counters::queue_overflow);
    return;
  }
  goats_diag_v1021::increment(&goats_diag_v1021::Counters::queue_pushed);
  goats_diag_v1021::queue_depth(samples.size());
}
static inline bool pop(Sample &out) {
  if (!samples.pop(out)) return false;
  goats_diag_v1021::increment(&goats_diag_v1021::Counters::queue_popped);
  return true;
}
static inline void clear() {
  goats_diag_v1021::increment(&goats_diag_v1021::Counters::queue_cleared, samples.size());
  samples.clear();
}
}
