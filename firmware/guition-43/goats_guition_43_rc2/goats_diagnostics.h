#pragma once
// Observation only. All mutation occurs on the ESPHome application task.
#include <algorithm>
#include <cstddef>
#include <cstdint>
#include "esp_timer.h"
#include "esphome/core/log.h"

namespace goats_diag_v1021 {
enum class SdKind : uint8_t { ALL, MOUNT, OPEN, POINT, SYNC, CHECKPOINT, METADATA, READ, FINALIZE, COUNT };
static constexpr size_t SD_KINDS = static_cast<size_t>(SdKind::COUNT);
struct SdStats {
  uint64_t operations{0}, max_us{0}, over_10ms{0}, over_20ms{0}, over_40ms{0};
};
struct Counters {
  uint64_t pvt_received{0}, pvt_valid{0}, pvt_fix_valid{0}, pvt_bad_checksum{0}, pvt_duplicates{0};
  uint64_t itow_gap_events{0}, itow_sequence_errors{0};
  uint64_t queue_pushed{0}, queue_popped{0}, queue_processed{0}, queue_overflow{0}, queue_cleared{0};
  uint64_t csv_points{0};
  uint32_t max_itow_step_ms{0}, max_decode_gap_ms{0};
  size_t queue_high_water{0};
  SdStats sd[SD_KINDS]{};
};
struct Continuity { bool have_previous{false}; uint32_t itow{0}, decoded_ms{0}; };
struct Report { uint32_t session_id{0}; Counters session{}, boot{}; };
// Fixed storage: no allocation, filesystem, UART access or logging in hooks.
static Counters boot{}, session{};
static Continuity boot_continuity{}, session_continuity{};
static bool session_active = false;
static uint32_t session_id = 0;
static Report reports[4]{};
static uint8_t report_read = 0, report_write = 0, report_count = 0, report_line = 0;
static uint32_t reports_dropped = 0;
static unsigned sd_depth = 0;

inline void increment(uint64_t Counters::*field, uint64_t amount = 1) {
  boot.*field += amount;
  if (session_active) session.*field += amount;
}
inline void queue_depth(size_t depth) {
  boot.queue_high_water = std::max(boot.queue_high_water, depth);
  if (session_active) session.queue_high_water = std::max(session.queue_high_water, depth);
}
inline void continuity(Counters &c, Continuity &prev, uint32_t itow, uint32_t now_ms) {
  constexpr uint32_t WEEK_MS = 604800000U;
  if (prev.have_previous) {
    c.max_decode_gap_ms = std::max(c.max_decode_gap_ms, uint32_t(now_ms - prev.decoded_ms));
    if (itow == prev.itow) {
      ++c.pvt_duplicates;
    } else if (itow < WEEK_MS && prev.itow < WEEK_MS) {
      const uint32_t step = itow >= prev.itow ? itow - prev.itow : WEEK_MS - prev.itow + itow;
      // Half-week ambiguity: backwards/reset epochs are not counted as lost PVT.
      if (step > WEEK_MS / 2U) ++c.itow_sequence_errors;
      else {
        c.max_itow_step_ms = std::max(c.max_itow_step_ms, step);
        if (step > 40U) ++c.itow_gap_events;
        if (step % 40U != 0U) ++c.itow_sequence_errors;
      }
    } else ++c.itow_sequence_errors;
  } else if (itow >= WEEK_MS) ++c.itow_sequence_errors;
  prev = {true, itow, now_ms};
}
inline void pvt_received(uint32_t itow) {
  const uint32_t now_ms = static_cast<uint32_t>(esp_timer_get_time() / 1000);
  ++boot.pvt_valid;
  continuity(boot, boot_continuity, itow, now_ms);
  if (session_active) {
    ++session.pvt_valid;
    continuity(session, session_continuity, itow, now_ms);
  }
}
inline void session_begin() {
  if (session_active) return;
  session = {};
  session_continuity = {};
  ++session_id;
  session_active = true;
}
inline void session_end() {
  if (!session_active) return;
  session_active = false;
  if (report_count == 4) { ++reports_dropped; return; }
  reports[report_write] = {session_id, session, boot};
  report_write = (report_write + 1U) % 4U;
  ++report_count;
}
inline void record_sd(Counters &c, SdKind kind, uint64_t us) {
  auto &s = c.sd[static_cast<size_t>(kind)];
  ++s.operations;
  s.max_us = std::max(s.max_us, us);
  if (us > 10000U) ++s.over_10ms;
  if (us > 20000U) ++s.over_20ms;
  if (us > 40000U) ++s.over_40ms;
}
class SdScope {
 public:
  explicit SdScope(SdKind kind) : kind_(kind), outer_(sd_depth++ == 0), start_(esp_timer_get_time()) {}
  ~SdScope() {
    const uint64_t us = static_cast<uint64_t>(esp_timer_get_time() - start_);
    --sd_depth;
    record_sd(boot, kind_, us);
    if (outer_) record_sd(boot, SdKind::ALL, us);
    if (session_active) {
      record_sd(session, kind_, us);
      if (outer_) record_sd(session, SdKind::ALL, us);
    }
  }
  SdScope(const SdScope &) = delete;
  SdScope &operator=(const SdScope &) = delete;
 private:
  SdKind kind_; bool outer_; int64_t start_;
};

// Caller must also guard live filesystem ownership, laptimer and USB state.
// One line per idle tick; never write diagnostics to SD or the Manager transport.
inline void report_tick(bool timing_or_recording, bool usb_busy) {
  if (timing_or_recording || usb_busy || session_active || report_count == 0) return;
  const auto &r = reports[report_read];
  constexpr unsigned LINES_PER_SCOPE = 3U + SD_KINDS;
  const bool global = report_line >= LINES_PER_SCOPE;
  const unsigned line = report_line % LINES_PER_SCOPE;
  const Counters &c = global ? r.boot : r.session;
  const char *scope = global ? "BOOT" : "SESSION";
  if (line == 0) {
    ESP_LOGW("goats_diag", "sid=%lu %s PVT=%llu valid=%llu fix=%llu bad_ck=%llu dup=%llu UART_OVF=NA reports_lost=%lu",
      (unsigned long)r.session_id, scope, (unsigned long long)c.pvt_received,
      (unsigned long long)c.pvt_valid,
      (unsigned long long)c.pvt_fix_valid, (unsigned long long)c.pvt_bad_checksum,
      (unsigned long long)c.pvt_duplicates, (unsigned long)reports_dropped);
  } else if (line == 1) {
    ESP_LOGW("goats_diag", "sid=%lu %s q_in=%llu q_out=%llu processed=%llu overflow=%llu cleared=%llu high=%u CSV=%llu",
      (unsigned long)r.session_id, scope, (unsigned long long)c.queue_pushed,
      (unsigned long long)c.queue_popped, (unsigned long long)c.queue_processed,
      (unsigned long long)c.queue_overflow, (unsigned long long)c.queue_cleared,
      (unsigned)c.queue_high_water, (unsigned long long)c.csv_points);
  } else if (line == 2) {
    ESP_LOGW("goats_diag", "sid=%lu %s itow_max_ms=%lu gaps=%llu seq_err=%llu decode_max_ms=%lu",
      (unsigned long)r.session_id, scope, (unsigned long)c.max_itow_step_ms,
      (unsigned long long)c.itow_gap_events, (unsigned long long)c.itow_sequence_errors,
      (unsigned long)c.max_decode_gap_ms);
  } else {
    static const char *const names[] = {"ALL", "MOUNT", "OPEN", "POINT", "SYNC", "CHECKPOINT", "METADATA", "READ", "FINALIZE"};
    const unsigned i = line - 3U;
    const auto &s = c.sd[i];
    ESP_LOGW("goats_diag", "sid=%lu %s SD_%s n=%llu max_us=%llu gt10=%llu gt20=%llu gt40=%llu",
      (unsigned long)r.session_id, scope, names[i], (unsigned long long)s.operations,
      (unsigned long long)s.max_us, (unsigned long long)s.over_10ms,
      (unsigned long long)s.over_20ms, (unsigned long long)s.over_40ms);
  }
  if (++report_line == 2U * LINES_PER_SCOPE) {
    report_line = 0;
    report_read = (report_read + 1U) % 4U;
    --report_count;
  }
}
}  // namespace goats_diag_v1021
