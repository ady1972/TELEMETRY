#include "nav_pvt.h"
#include <cmath>

namespace esphome::goats_core {
bool NavPvtParser::consume(uint8_t b, uint32_t now_ms, NavSample &out) {
  switch (phase_) {
    case 0: phase_ = b == 0xB5 ? 1 : 0; break;
    case 1:
      phase_ = b == 0x62 ? 2 : (b == 0xB5 ? 1 : 0);
      ck_a_ = ck_b_ = 0;
      break;
    case 2: cls_ = b; checksum_(b); phase_ = 3; break;
    case 3: id_ = b; checksum_(b); phase_ = 4; break;
    case 4: length_ = b; checksum_(b); phase_ = 5; break;
    case 5:
      length_ |= uint16_t(b) << 8; checksum_(b); offset_ = 0;
      if (length_ > 1200) { ++oversized_frames_; phase_ = 0; }
      else phase_ = length_ == 0 ? 7 : 6;
      break;
    case 6:
      if (offset_ < payload_.size()) payload_[offset_] = b;
      ++offset_; checksum_(b);
      if (offset_ == length_) phase_ = 7;
      break;
    case 7: rx_a_ = b; phase_ = 8; break;
    case 8: {
      phase_ = 0;
      if (rx_a_ != ck_a_ || b != ck_b_) { ++checksum_errors_; break; }
      if (cls_ != 0x01 || id_ != 0x07 || length_ < 92) break;
      ++pvt_frames_;
      const uint32_t itow = u32_(payload_.data());
      if (have_itow_ && itow == last_itow_) { ++duplicates_; break; }
      have_itow_ = true; last_itow_ = itow;
      NavSample sample;
      sample.itow_ms = itow; sample.received_ms = now_ms;
      sample.fix_type = payload_[20]; sample.satellites = payload_[23];
      sample.longitude = static_cast<int32_t>(u32_(payload_.data() + 24)) * 1e-7;
      sample.latitude = static_cast<int32_t>(u32_(payload_.data() + 28)) * 1e-7;
      sample.speed_kmh = static_cast<int32_t>(u32_(payload_.data() + 60)) * 0.0036f;
      // RLCD functional reference: 3D fix, gnssFixOK, >=4 satellites.
      sample.valid_fix = sample.fix_type >= 3 && (payload_[21] & 1U) &&
          sample.satellites >= 4 && std::abs(sample.latitude) <= 90 &&
          std::abs(sample.longitude) <= 180;
      out = sample;
      return true;
    }
    default: phase_ = 0; break;
  }
  return false;
}
}  // namespace esphome::goats_core
