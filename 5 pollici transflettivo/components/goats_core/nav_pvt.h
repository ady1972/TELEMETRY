#pragma once
#include <array>
#include <cstdint>

namespace esphome::goats_core {
struct NavSample {
  uint32_t itow_ms{0};
  uint32_t received_ms{0};
  double latitude{0}, longitude{0};
  float speed_kmh{0};
  uint8_t satellites{0}, fix_type{0};
  bool valid_fix{false};
};

// New implementation, not copied from the RLCD firmware. Fixed storage, no I/O.
// Unknown UBX packets are checksum-checked then ignored; no GNSS commands exist.
class NavPvtParser {
 public:
  bool consume(uint8_t byte, uint32_t now_ms, NavSample &out);
  uint32_t pvt_frames() const { return pvt_frames_; }
  uint32_t duplicates() const { return duplicates_; }
  uint32_t checksum_errors() const { return checksum_errors_; }
  uint32_t oversized_frames() const { return oversized_frames_; }

 private:
  void checksum_(uint8_t value) { ck_a_ += value; ck_b_ += ck_a_; }
  static uint32_t u32_(const uint8_t *p) {
    return uint32_t(p[0]) | uint32_t(p[1]) << 8 | uint32_t(p[2]) << 16 | uint32_t(p[3]) << 24;
  }
  uint8_t phase_{0}, cls_{0}, id_{0}, ck_a_{0}, ck_b_{0}, rx_a_{0};
  uint16_t length_{0}, offset_{0};
  std::array<uint8_t, 92> payload_{};
  bool have_itow_{false};
  uint32_t last_itow_{0}, pvt_frames_{0}, duplicates_{0};
  uint32_t checksum_errors_{0}, oversized_frames_{0};
};
}  // namespace esphome::goats_core
