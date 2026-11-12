#pragma once
#include "esphome/components/goats_core/nav_pvt.h"
#include <cstdint>

namespace goats5::timing {
// Boundary for a future implementation. No placeholder produces lap results.
struct LapResult { uint32_t number, elapsed_ms; };
class TimingEngine {
 public:
  virtual ~TimingEngine() = default;
  virtual void reset() = 0;
  virtual void on_nav_sample(const esphome::goats_core::NavSample &sample) = 0;
};
}  // namespace goats5::timing
