#include "nav_pvt.h"
#include <cmath>

namespace esphome::goats_core {
void NavPvtParser::update_rate(uint32_t now_ms) {
  if (!rate_started_) {
    rate_started_ = true;
    rate_started_ms_ = now_ms;
    rate_frames_ = pvt_frames_;
    return;
  }
  const uint32_t elapsed = now_ms - rate_started_ms_;
  if (elapsed >= 2000U) {
    pvt_hz_ = 1000.0f * (pvt_frames_ - rate_frames_) / elapsed;
    rate_started_ms_ = now_ms;
    rate_frames_ = pvt_frames_;
  }
}

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
      if (length_ > payload_.size()) { ++oversized_frames_; phase_ = 0; }
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
      if (rx_a_ != ck_a_ || b != ck_b_) {
        ++checksum_errors_;
        // Classification uses the received header, which itself may be corrupt.
        if (cls_ == 0x01 && id_ == 0x07) ++pvt_checksum_errors_;
        else if (cls_ == 0x01 && id_ == 0x35) ++sat_checksum_errors_;
        else if (cls_ == 0x01 && id_ == 0x04) ++dop_checksum_errors_;
        else ++other_checksum_errors_;
        break;
      }
      if (cls_ != 0x01) break;
      if (id_ == 0x35 && length_ >= 8 && payload_[4] == 1) {
        const unsigned count = payload_[5];
        if (count > (length_ - 8U) / 12U) break;
        SatelliteStatus status;
        status.received_ms = now_ms;
        status.reported = static_cast<uint8_t>(count);
        uint32_t cno_sum = 0;
        for (unsigned n = 0; n < count; ++n) {
          const uint8_t *sv = payload_.data() + 8U + 12U * n;
          // RLCD: a seen satellite has C/N0 > 0; PVT supplies used SVs.
          if (sv[2] == 0) continue;
          ++status.seen;
          if (status.seen == 1 || sv[2] < status.cno_min) status.cno_min = sv[2];
          if (sv[2] > status.cno_max) status.cno_max = sv[2];
          cno_sum += sv[2];
          if (sv[2] >= 30) ++status.cno_at_least_30;
          switch (sv[0]) {
            case 0: ++status.gps; break;
            case 1: ++status.sbas; break;
            case 2: ++status.galileo; break;
            case 3: ++status.beidou; break;
            case 6: ++status.glonass; break;
            default: break;
          }
        }
        if (status.seen > 0) status.cno_mean = static_cast<float>(cno_sum) / status.seen;
        satellites_ = status;
        ++sat_frames_;
        break;
      }
      if (id_ == 0x04 && length_ >= 18) {
        const uint16_t hdop = u16_(payload_.data() + 12);
        dop_.hdop = hdop == 0xFFFFU ? -1.0f : hdop / 100.0f;
        dop_.received_ms = now_ms;
        ++dop_frames_;
        break;
      }
      if (id_ != 0x07 || length_ < 92) break;
      ++pvt_frames_;
      const uint32_t itow = u32_(payload_.data());
      if (have_itow_ && itow == last_itow_) { ++duplicates_; break; }
      have_itow_ = true; last_itow_ = itow;
      NavSample sample;
      sample.itow_ms = itow; sample.received_ms = now_ms;
      sample.fix_type = payload_[20]; sample.satellites = payload_[23];
      sample.fix_ok = (payload_[21] & 1U) != 0;
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
