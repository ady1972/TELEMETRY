#include <cassert>
#include <cstdint>
#include "goats_diagnostics.h"
#include "goats_nav_sample_queue.h"
int64_t fake_us = 0;
unsigned log_lines = 0;

int main() {
  using namespace goats_diag_v1021;
  // Nominal rate, duplicate, missing epoch, week rollover and backwards epoch.
  continuity(boot, boot_continuity, 604799960U, 1);
  continuity(boot, boot_continuity, 0, 41);
  assert(boot.max_itow_step_ms == 40 && boot.itow_gap_events == 0);
  continuity(boot, boot_continuity, 0, 42);
  continuity(boot, boot_continuity, 80, 122);
  continuity(boot, boot_continuity, 40, 123);
  assert(boot.pvt_duplicates == 1 && boot.itow_gap_events == 1);
  assert(boot.itow_sequence_errors == 1 && boot.max_itow_step_ms == 80);

  session_begin();
  const auto sid = session_id;
  session_begin();
  assert(session_id == sid);  // Must not silently reset an active session.
  for (unsigned i = 0; i < 55; ++i) goats_nav_queue::push(true, i, 1, 10, i * 40);
  assert(session.queue_pushed == 55 && session.queue_overflow == 5);
  assert(session.queue_high_water == 50 && goats_nav_queue::samples.size() == 50);
  goats_nav_queue::Sample sample;
  assert(goats_nav_queue::pop(sample) && sample.lat == 5); // Retains baseline drop-oldest policy.
  increment(&Counters::queue_processed);
  goats_nav_queue::clear();
  assert(session.queue_popped == 1 && session.queue_processed == 1 && session.queue_cleared == 49);
  assert(!goats_nav_queue::pop(sample));

  // Strict, cumulative thresholds; nesting must not double-count SD_ALL.
  { SdScope outer(SdKind::POINT);
    fake_us += 10000;
    { SdScope sync(SdKind::SYNC); fake_us += 40001; }
  }
  auto &all = session.sd[static_cast<unsigned>(SdKind::ALL)];
  assert(all.operations == 1 && all.max_us == 50001);
  assert(all.over_10ms == 1 && all.over_20ms == 1 && all.over_40ms == 1);
  Counters exact{};
  record_sd(exact, SdKind::POINT, 10000);
  record_sd(exact, SdKind::POINT, 20000);
  record_sd(exact, SdKind::POINT, 40000);
  auto &s = exact.sd[static_cast<unsigned>(SdKind::POINT)];
  assert(s.over_10ms == 2 && s.over_20ms == 1 && s.over_40ms == 0);
  increment(&Counters::csv_points);
  session_end();
  session_end();
  assert(report_count == 1 && reports[0].session.csv_points == 1);
  increment(&Counters::csv_points);
  assert(boot.csv_points == 2 && reports[0].boot.csv_points == 1);
  report_tick(true, false);
  report_tick(false, true);
  assert(log_lines == 0 && report_line == 0);
  session_begin();
  report_tick(false, false);
  assert(log_lines == 0 && session.csv_points == 0);
  session_end();
  for (unsigned i = 0; i < 24; ++i) report_tick(false, false);
  assert(log_lines == 24 && report_count == 1 && report_line == 0);
  for (unsigned i = 0; i < 5; ++i) { session_begin(); session_end(); }
  assert(report_count == 4 && reports_dropped == 2);
  assert(sd_depth == 0);
  std::puts("PASS: continuity, FIFO/overflow, session scopes, SD thresholds/nesting, frozen reports and output guards");
}
