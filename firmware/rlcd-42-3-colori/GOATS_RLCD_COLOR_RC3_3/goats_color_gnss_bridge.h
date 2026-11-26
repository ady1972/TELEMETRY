#pragma once
#include "goats_color_gnss_v0405.h"

namespace goats_b { void on_pvt(const uint8_t *, uint16_t); }
// Presentation/diagnostics API expected by the RC3.3 YAML and trace writer.
// Reception and decoding are owned exclusively by the V0.40.5 parser.
namespace goats_diag {
struct State {
  uint32_t bytes{0}, good{0}, bad{0}, last_pvt{0}, last_sat{0}, last_dop{0};
  uint32_t rate{230400}, nmea_valid{0}, last_valid{0};
  uint32_t cfg_ack{0}, cfg_nak{0}, poll_calls{0};
  bool locked{false}, found_ubx{false};
  uint8_t seen{0}, used{0}, fix_type{0};
  float hdop{-1.f}, pvt_hz{0.f}, speed_kmh{0.f};
};
inline State &data() { static State state; return state; }
inline float trace_hdop() { return data().hdop; }

inline void on_frame(uint8_t cls, uint8_t id, const std::vector<uint8_t> &payload) {
  auto &s = data();
  ++s.good;
  s.last_valid = esphome::millis();
  // Observe receiver replies without changing configuration, timing or parsing.
  if (cls == 0x05 && payload.size() >= 2 && payload[0] == 0x06) {
    if (id == 0x01) ++s.cfg_ack;
    else if (id == 0x00) ++s.cfg_nak;
  }
  if (cls != 0x01) return;
  if (id == 0x07 && payload.size() >= 92) {
    s.last_pvt = esphome::millis();
    s.fix_type = payload[20];
    s.used = payload[23];
    s.speed_kmh = goats_m9n::i4(payload, 60) * 0.0036f;
    // No reconstructed payload, timestamp substitution or alternate lap engine.
    // RC3.3 retains its fix criteria, duplicate handling, dates and recording.
    goats_b::on_pvt(payload.data(), static_cast<uint16_t>(payload.size()));
  } else if (id == 0x04 && payload.size() >= 18) {
    s.last_dop = esphome::millis();
    s.hdop = goats_m9n::u2(payload, 12) * 0.01f;
  } else if (id == 0x35 && payload.size() >= 8) {
    s.last_sat = esphome::millis();
    s.seen = payload[5]; // Same visible-satellite count as the working COLOR.
  }
}

inline void poll(esphome::uart::UARTComponent *uart) {
  if (uart == nullptr) return;
  ++data().poll_calls;
  goats_m9n::frame_observer = on_frame;
  goats_m9n::poll(uart); // Same UART drain, parser and expiry rules as V0.40.5.
  auto &s = data();
  const auto &original = goats_m9n::state;
  s.bytes = goats_m9n::rx_bytes;
  s.bad = goats_m9n::checksum_errors;
  s.last_pvt = original.last_pvt_ms;
  s.used = original.used_sats;
  s.seen = original.visible_sats;
  s.speed_kmh = original.speed_kmh;
  s.pvt_hz = original.pvt_hz;
  s.locked = s.good >= 2 && uint32_t(esphome::millis() - s.last_valid) < 6500U;
  s.found_ubx = s.locked;
  // Each validated NAV-PVT was already delivered synchronously above. Keeping
  // a second consumer queue would duplicate samples or let it grow needlessly.
  goats_m9n::pending_samples.clear();
}
}  // namespace goats_diag
