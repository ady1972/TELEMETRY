#pragma once
#include <deque>
#include <cstdint>
namespace goats_nav_queue {
struct Sample { bool fix; double lat, lon; float speed_kmh; uint32_t ms; };
static std::deque<Sample> samples;
static inline void push(bool fix, double lat, double lon, float speed, uint32_t ms) {
  // 2 seconds of backlog at 25 Hz; overflow removes the oldest sample.
  if (samples.size() >= 50) samples.pop_front();
  samples.push_back({fix,lat,lon,speed,ms});
}
static inline bool pop(Sample &out) {
  if (samples.empty()) return false;
  out=samples.front(); samples.pop_front(); return true;
}
static inline void clear() { samples.clear(); }
}
