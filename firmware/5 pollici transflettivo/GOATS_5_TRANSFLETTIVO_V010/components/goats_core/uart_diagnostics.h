#pragma once
#include <cstdint>

namespace esphome::goats_core {
// Snapshots at poll boundaries, not UART-driver overflow/lost-byte counters.
struct UartDiagnostics {
  uint32_t pending_bytes{0}, max_pending_bytes{0};
  uint32_t poll_gap_ms{0}, max_poll_gap_ms{0};
  uint32_t polls{0}, bytes_read{0}, limited_polls{0};

  void begin_poll(uint32_t now_ms, uint32_t pending) {
    if (started_) {
      poll_gap_ms = now_ms - last_poll_ms_;
      if (poll_gap_ms > max_poll_gap_ms) max_poll_gap_ms = poll_gap_ms;
    }
    started_ = true;
    last_poll_ms_ = now_ms;
    ++polls;
    observe_(pending);
  }
  void end_poll(uint32_t pending, uint32_t read, bool reached_limit) {
    observe_(pending);
    bytes_read += read;
    if (reached_limit && pending > 0) ++limited_polls;
  }

 private:
  void observe_(uint32_t pending) {
    pending_bytes = pending;
    if (pending > max_pending_bytes) max_pending_bytes = pending;
  }
  bool started_{false};
  uint32_t last_poll_ms_{0};
};
}  // namespace esphome::goats_core
