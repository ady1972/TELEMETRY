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
  bool valid_fix{false}, fix_ok{false};
};

struct SatelliteStatus {
  uint32_t received_ms{0};
  uint8_t seen{0}, gps{0}, galileo{0}, beidou{0}, glonass{0}, sbas{0};
  uint8_t reported{0}, cno_min{0}, cno_max{0}, cno_at_least_30{0};
  float cno_mean{0};
};

struct DopStatus {
  uint32_t received_ms{0};
  float hdop{-1.0f};
};

// New implementation, not copied from the RLCD firmware. Fixed storage, no I/O.
// Unknown UBX packets are checksum-checked then ignored; no GNSS commands exist.
class NavPvtParser {
 public:
  bool consume(uint8_t byte, uint32_t now_ms, NavSample &out);
  void update_rate(uint32_t now_ms);
  uint32_t pvt_frames() const { return pvt_frames_; }
  uint32_t duplicates() const { return duplicates_; }
  uint32_t checksum_errors() const { return checksum_errors_; }
  uint32_t pvt_checksum_errors() const { return pvt_checksum_errors_; }
  uint32_t sat_checksum_errors() const { return sat_checksum_errors_; }
  uint32_t dop_checksum_errors() const { return dop_checksum_errors_; }
  uint32_t other_checksum_errors() const { return other_checksum_errors_; }
  uint32_t oversized_frames() const { return oversized_frames_; }
  uint32_t sat_frames() const { return sat_frames_; }
  uint32_t dop_frames() const { return dop_frames_; }
  const SatelliteStatus &satellites() const { return satellites_; }
  const DopStatus &dop() const { return dop_; }
  float pvt_hz() const { return pvt_hz_; }

 private:
  void checksum_(uint8_t value) { ck_a_ += value; ck_b_ += ck_a_; }
  static uint32_t u32_(const uint8_t *p) {
    return uint32_t(p[0]) | uint32_t(p[1]) << 8 | uint32_t(p[2]) << 16 | uint32_t(p[3]) << 24;
  }
  static uint16_t u16_(const uint8_t *p) {
    return uint16_t(p[0]) | (uint16_t(p[1]) << 8);
  }
  uint8_t phase_{0}, cls_{0}, id_{0}, ck_a_{0}, ck_b_{0}, rx_a_{0};
  uint16_t length_{0}, offset_{0};
  // Same bounded UBX payload capacity as the passive RLCD reader.
  std::array<uint8_t, 1200> payload_{};
  bool have_itow_{false};
  uint32_t last_itow_{0}, pvt_frames_{0}, duplicates_{0};
  uint32_t checksum_errors_{0}, oversized_frames_{0};
  uint32_t pvt_checksum_errors_{0}, sat_checksum_errors_{0};
  uint32_t dop_checksum_errors_{0}, other_checksum_errors_{0};
  SatelliteStatus satellites_;
  DopStatus dop_;
  uint32_t sat_frames_{0}, dop_frames_{0};
  uint32_t rate_started_ms_{0}, rate_frames_{0};
  bool rate_started_{false};
  float pvt_hz_{0};
};
}  // namespace esphome::goats_core
