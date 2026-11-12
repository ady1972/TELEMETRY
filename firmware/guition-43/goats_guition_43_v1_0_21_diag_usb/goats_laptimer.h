#pragma once
// GoatsTrackUsb defined by goats_usb_tracks_v1025.h in Guition includes

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <limits>
#include <string>
#include <vector>

class GoatsLaptimerEngine {
 public:
  struct TracePoint {
    double lat;
    double lon;
    uint32_t elapsed_ms;
    float speed_kmh;
  };

  struct PaceLap {
    uint32_t lap_ms;
    float average_speed_kmh;
    bool pit_stop;
  };

  void reset() {
    track_ = nullptr;
    have_previous_ = false;
    running_ = false;
    finish_armed_ = true;
    lap_start_ms_ = 0;
    lap_start_wall_ms_ = 0;
    last_lap_ms_ = 0;
    best_lap_ms_ = 0;
    lap_number_ = 0;
    next_sector_ = 0;
    sector_start_ms_ = 0;
    sector_times_ms_.clear();
    previous_sector_times_ms_.clear();
    best_sector_times_ms_.clear();
    sector_status_.clear();
    sector_display_delta_seconds_.clear();
    sector_display_status_.clear();
    sector_display_reset_at_ms_ = 0;
    sector_hold_until_ms_ = 0;
    last_sector_delta_seconds_ = nan_();
    last_sector_status_ = 0;
    last_sector_number_ = 0;
    last_finish_ms_ = 0;
    live_delta_seconds_ = nan_();
    last_live_delta_filter_ms_ = 0;
    final_delta_seconds_ = nan_();
    final_hold_until_ms_ = 0;
    new_best_event_ = false;
    current_trace_.clear();
    best_trace_.clear();
    previous_lap_trace_.clear();
    pace_laps_.clear();
    last_trace_sample_ms_ = 0;
    live_speed_delta_kmh_ = nan_();
    final_speed_delta_kmh_ = nan_();
    previous_lap_average_speed_kmh_ = 0.0f;
    lap_speed_sum_ = 0.0;
    lap_speed_samples_ = 0;
    current_lap_pit_stop_ = false;
    low_speed_started_ms_ = 0;
    race_pace_ms_ = 0;
    race_pace_lap_count_ = 0;
    race_average_speed_kmh_ = 0.0f;
    last_lap_average_speed_kmh_ = 0.0f;
    post_lap_speed_delta_kmh_ = nan_();
    post_lap_pace_delta_seconds_ = nan_();
    post_lap_best_delta_seconds_ = nan_();
    last_lap_pace_valid_ = false;
    lap_completed_event_ = false;
  }

  void update(const GoatsTrackUsb *track, bool gps_fix,
              double lat, double lon, float speed_kmh, uint32_t now_ms,
              uint32_t gnss_itow_ms = 0) {
    (void) gnss_itow_ms;
    if (sector_display_reset_at_ms_ != 0 &&
        static_cast<int32_t>(now_ms - sector_display_reset_at_ms_) >= 0) {
      sector_display_delta_seconds_.clear();
      sector_display_status_.clear();
      sector_display_reset_at_ms_ = 0;
    }
    if (track != track_) {
      reset();
      track_ = track;
    }

    if (track == nullptr || !gps_fix || !valid_coordinate_(lat, lon)) {
      have_previous_ = false;
      live_delta_seconds_ = nan_();
      last_live_delta_filter_ms_ = 0;
      return;
    }

    if (!have_previous_) {
      previous_lat_ = lat;
      previous_lon_ = lon;
      have_previous_ = true;
      return;
    }

    if (running_) {
      if (std::isfinite(speed_kmh) && speed_kmh >= 0.0f) {
        lap_speed_sum_ += speed_kmh;
        lap_speed_samples_++;
      }

      if (speed_kmh < pit_speed_threshold_kmh_) {
        if (low_speed_started_ms_ == 0)
          low_speed_started_ms_ = now_ms;
        else if (static_cast<uint32_t>(
                     now_ms - low_speed_started_ms_) >= pit_stop_hold_ms_)
          current_lap_pit_stop_ = true;
      } else {
        low_speed_started_ms_ = 0;
      }

      sample_trace_(lat, lon, speed_kmh, now_ms);
      calculate_live_delta_(lat, lon, now_ms);
      calculate_live_speed_delta_(lat, lon, speed_kmh, now_ms);
    }

    const double finish_distance = point_segment_distance_m_(
        lat, lon, track->start_lat, track->start_lon,
        track->finish_lat, track->finish_lon);
    const double rearm_distance =
        std::max(10.0, static_cast<double>(track->trigger_radius_m));
    if (!finish_armed_ && finish_distance > rearm_distance)
      finish_armed_ = true;

    if (running_ && next_sector_ < track->sectors.size() &&
        speed_kmh >= minimum_speed_kmh_) {
      const auto &sector = track->sectors[next_sector_];
      if (segments_intersect_local_(
              previous_lat_, previous_lon_, lat, lon,
              sector.lat1, sector.lon1, sector.lat2, sector.lon2)) {
        const uint32_t sector_ms = safe_elapsed_(now_ms, sector_start_ms_);
        sector_times_ms_.push_back(sector_ms);
        const size_t sector_index = sector_times_ms_.size() - 1;
        update_sector_status_(sector_index, sector_ms);
        start_sector_hold_(sector_index, sector_ms, now_ms);
        sector_start_ms_ = now_ms;
        next_sector_++;
      }
    }

    const bool crossed_finish =
        finish_armed_ && speed_kmh >= minimum_speed_kmh_ &&
        segments_intersect_local_(
            previous_lat_, previous_lon_, lat, lon,
            track->start_lat, track->start_lon,
            track->finish_lat, track->finish_lon);

    if (crossed_finish) {
      finish_armed_ = false;
      last_finish_ms_ = now_ms;
      if (!running_) {
        start_lap_(now_ms);
      } else {
        const uint32_t elapsed = current_ms(now_ms);
        if (elapsed >= minimum_lap_ms_)
          complete_lap_(now_ms, elapsed);
      }
    }

    previous_lat_ = lat;
    previous_lon_ = lon;
  }

  bool running() const { return running_; }
  uint32_t current_ms(uint32_t now_ms) const {
    if (!running_) return 0;
    const int32_t d = static_cast<int32_t>(now_ms - lap_start_ms_);
    return d > 0 ? static_cast<uint32_t>(d) : 0U;
  }

  // TEMP fail-safe UI clock: uses the ESP monotonic clock only for display.
  // Lap detection and recorded lap times continue to use the GNSS-mapped timebase.
  uint32_t display_current_ms(uint32_t wall_now_ms) const {
    if (!running_ || lap_start_wall_ms_ == 0) return 0U;
    return static_cast<uint32_t>(wall_now_ms - lap_start_wall_ms_);
  }
  uint32_t last_lap_ms() const { return last_lap_ms_; }
  uint32_t best_lap_ms() const { return best_lap_ms_; }
  uint32_t lap_number() const { return lap_number_; }
  uint32_t last_finish_ms() const { return last_finish_ms_; }

  float live_delta_seconds() const { return live_delta_seconds_; }

  float display_delta_seconds(uint32_t now_ms) const {
    if (final_hold_active(now_ms) &&
        static_cast<int32_t>(final_hold_until_ms_ - now_ms) > 5000)
      return final_delta_seconds_; // 5 s di riepilogo, poi delta live
    return live_delta_seconds_;
  }

  float display_speed_delta_kmh(uint32_t now_ms) const {
    if (final_hold_active(now_ms)) return final_speed_delta_kmh_;
    return live_speed_delta_kmh_;
  }

  uint32_t race_pace_ms() const { return race_pace_ms_; }
  uint32_t race_pace_lap_count() const { return race_pace_lap_count_; }

  std::string race_pace_text() const {
    return race_pace_ms_
        ? format_time_(race_pace_ms_)
        : std::string("--:--.---");
  }

  float race_average_speed_kmh() const {
    return race_average_speed_kmh_;
  }

  float last_lap_average_speed_kmh() const {
    return last_lap_average_speed_kmh_;
  }

  // Delta velocità media del giro appena chiuso rispetto alla media
  // velocità dei giri validi (stesso filtro del passo gara).
  float post_lap_speed_delta_kmh() const {
    return post_lap_speed_delta_kmh_;
  }

  // Delta del giro appena chiuso rispetto al passo gara filtrato.
  float post_lap_pace_delta_seconds() const {
    return post_lap_pace_delta_seconds_;
  }

  // Delta del giro appena chiuso rispetto al best esistente prima del giro.
  float post_lap_best_delta_seconds() const {
    return post_lap_best_delta_seconds_;
  }

  // True only when the just-completed lap is eligible for Race Pace.
  bool last_lap_pace_valid() const {
    return last_lap_pace_valid_;
  }

  bool consume_lap_completed_event() {
    const bool value = lap_completed_event_;
    lap_completed_event_ = false;
    return value;
  }

  bool final_hold_active(uint32_t now_ms) const {
    return final_hold_until_ms_ != 0 &&
           static_cast<int32_t>(final_hold_until_ms_ - now_ms) > 0;
  }

  bool final_blink_on(uint32_t now_ms) const {
    return ((now_ms / 400U) % 2U) == 0U;
  }

  bool consume_new_best_event() {
    const bool result = new_best_event_;
    new_best_event_ = false;
    return result;
  }

  std::string current_text(uint32_t now_ms) const {
    // UI5: il GIRO CORRENTE non mostra i minuti per recuperare spazio.
    // Il valore resta espresso come SS.mmm; last/best mantengono MM:SS.mmm.
    if (!running_) return "--.---";
    const uint32_t ms = current_ms(now_ms);
    char b[20];
    std::snprintf(b, sizeof(b), "%02lu.%03lu",
      static_cast<unsigned long>((ms / 1000U) % 60U),
      static_cast<unsigned long>(ms % 1000U));
    return std::string(b);
  }
  std::string last_text() const {
    return last_lap_ms_ ? format_time_(last_lap_ms_) : "--:--.---";
  }
  std::string best_text() const {
    return best_lap_ms_ ? format_time_(best_lap_ms_) : "--:--.---";
  }

  size_t timing_sector_count() const {
    if (track_ == nullptr) return 1;
    return std::max<size_t>(1, track_->sectors.size() + 1);
  }

  int sector_status(size_t index) const {
    if (index >= sector_status_.size()) return 0;
    return static_cast<int>(sector_status_[index]);
  }

  bool sector_hold_active(uint32_t now_ms) const {
    return sector_hold_until_ms_ != 0 &&
           static_cast<int32_t>(sector_hold_until_ms_ - now_ms) > 0;
  }

  float sector_hold_delta_seconds() const {
    return last_sector_delta_seconds_;
  }

  int sector_hold_status() const {
    return static_cast<int>(last_sector_status_);
  }

  size_t sector_hold_number() const {
    return last_sector_number_;
  }

  size_t configured_sector_count() const {
    return track_ ? track_->sectors.size() : 0U;
  }

  float sector_display_delta_seconds(size_t index, uint32_t now_ms) const {
    if (sector_display_reset_at_ms_ != 0 &&
        static_cast<int32_t>(now_ms - sector_display_reset_at_ms_) >= 0)
      return nan_();
    return index < sector_display_delta_seconds_.size()
        ? sector_display_delta_seconds_[index] : nan_();
  }

  int sector_display_status(size_t index, uint32_t now_ms) const {
    if (sector_display_reset_at_ms_ != 0 &&
        static_cast<int32_t>(now_ms - sector_display_reset_at_ms_) >= 0)
      return 0;
    return index < sector_display_status_.size()
        ? static_cast<int>(sector_display_status_[index]) : 0;
  }

  // V1.5 RLCD TRACK TEST: expose the timing sectors of the last completed lap
  // for the three compact S1/S2/S3 cells on the racing dashboard.
  size_t last_timing_sector_count() const {
    return previous_sector_times_ms_.size();
  }

  uint32_t last_timing_sector_ms(size_t index) const {
    return index < previous_sector_times_ms_.size()
        ? previous_sector_times_ms_[index] : 0U;
  }

 private:
  const GoatsTrackUsb *track_{nullptr};
  bool have_previous_{false}, running_{false}, finish_armed_{true};
  bool new_best_event_{false};
  double previous_lat_{0}, previous_lon_{0};
  uint32_t lap_start_ms_{0}, last_lap_ms_{0}, best_lap_ms_{0};
  uint32_t lap_start_wall_ms_{0};
  uint32_t lap_number_{0}, last_finish_ms_{0};
  uint32_t sector_start_ms_{0}, last_trace_sample_ms_{0};
  uint32_t final_hold_until_ms_{0};
  uint32_t sector_hold_until_ms_{0};
  float last_sector_delta_seconds_{nan_()};
  uint8_t last_sector_status_{0};
  size_t last_sector_number_{0};
  size_t next_sector_{0};
  std::vector<uint32_t> sector_times_ms_;
  std::vector<uint32_t> previous_sector_times_ms_;
  std::vector<uint32_t> best_sector_times_ms_;
  std::vector<uint8_t> sector_status_;
  std::vector<float> sector_display_delta_seconds_;
  std::vector<uint8_t> sector_display_status_;
  uint32_t sector_display_reset_at_ms_{0};
  std::vector<TracePoint> current_trace_, best_trace_, previous_lap_trace_;
  std::vector<PaceLap> pace_laps_;

  float live_delta_seconds_{nan_()}, final_delta_seconds_{nan_()};
  uint32_t last_live_delta_filter_ms_{0};
  float live_speed_delta_kmh_{nan_()}, final_speed_delta_kmh_{nan_()};

  float previous_lap_average_speed_kmh_{0.0f};
  double lap_speed_sum_{0.0};
  uint32_t lap_speed_samples_{0};

  bool current_lap_pit_stop_{false};
  uint32_t low_speed_started_ms_{0};

  uint32_t race_pace_ms_{0};
  uint32_t race_pace_lap_count_{0};
  float race_average_speed_kmh_{0.0f};

  float last_lap_average_speed_kmh_{0.0f};
  float post_lap_speed_delta_kmh_{nan_()};
  float post_lap_pace_delta_seconds_{nan_()};
  float post_lap_best_delta_seconds_{nan_()};
  bool last_lap_pace_valid_{false};
  bool lap_completed_event_{false};

  static constexpr float minimum_speed_kmh_ = 5.0f;
  static constexpr float pit_speed_threshold_kmh_ = 5.0f;
  static constexpr uint32_t pit_stop_hold_ms_ = 10000U;
  static constexpr uint32_t race_pace_max_gap_ms_ = 30000U;
  static constexpr uint32_t minimum_lap_ms_ = 8000;
  static constexpr uint32_t trace_period_ms_ = 100;
  static constexpr float live_delta_filter_tau_ms_ = 1000.0f;
  static constexpr size_t max_trace_points_ = 3000;
  static constexpr double max_match_distance_m_ = 35.0;

  static float nan_() { return std::numeric_limits<float>::quiet_NaN(); }

  static uint32_t safe_elapsed_(uint32_t now_ms, uint32_t start_ms) {
    const int32_t d = static_cast<int32_t>(now_ms - start_ms);
    return d > 0 ? static_cast<uint32_t>(d) : 0U;
  }

  void start_lap_(uint32_t now_ms) {
    running_ = true;
    lap_start_ms_ = sector_start_ms_ = now_ms;
    lap_start_wall_ms_ = millis();
    next_sector_ = 0;
    sector_times_ms_.clear();
    sector_status_.assign(timing_sector_count(), 0);
    sector_hold_until_ms_ = 0;
    last_sector_delta_seconds_ = nan_();
    last_sector_status_ = 0;
    last_sector_number_ = 0;
    lap_number_ = 1;
    live_delta_seconds_ = nan_();
    last_live_delta_filter_ms_ = 0;
    live_speed_delta_kmh_ = nan_();
    current_trace_.clear();
    last_trace_sample_ms_ = 0;
    lap_speed_sum_ = 0.0;
    lap_speed_samples_ = 0;
    current_lap_pit_stop_ = false;
    low_speed_started_ms_ = 0;
  }

  void complete_lap_(uint32_t now_ms, uint32_t elapsed) {
    // Last timing sector runs from the last sector line (or start line when
    // there are no sector lines) to the finish line.
    const size_t expected = timing_sector_count();
    if (sector_times_ms_.size() < expected) {
      const uint32_t final_sector_ms = safe_elapsed_(now_ms, sector_start_ms_);
      sector_times_ms_.push_back(final_sector_ms);
      const size_t final_sector_index = sector_times_ms_.size() - 1;
      update_sector_status_(final_sector_index, final_sector_ms);
      // The last timing sector ends at the finish line and must be displayed
      // exactly like the intermediate sectors (e.g. 2 split lines => S1/S2/S3).
      start_sector_hold_(final_sector_index, final_sector_ms, now_ms);
    }

    const uint32_t previous_best = best_lap_ms_;
    last_lap_ms_ = elapsed;
    const bool new_best = previous_best == 0 || elapsed < previous_best;

    if (previous_best > 0) {
      post_lap_best_delta_seconds_ =
          (static_cast<int64_t>(elapsed) -
           static_cast<int64_t>(previous_best)) / 1000.0f;
    } else {
      post_lap_best_delta_seconds_ = nan_();
    }

    if (previous_best > 0)
      final_delta_seconds_ =
          (static_cast<int64_t>(elapsed) -
           static_cast<int64_t>(previous_best)) / 1000.0f;
    else
      final_delta_seconds_ = 0.0f;

    const float lap_average_speed =
        lap_speed_samples_ > 0
            ? static_cast<float>(
                  lap_speed_sum_ / lap_speed_samples_)
            : 0.0f;

    if (previous_lap_average_speed_kmh_ > 0.0f &&
        lap_average_speed > 0.0f)
      final_speed_delta_kmh_ =
          lap_average_speed - previous_lap_average_speed_kmh_;
    else
      final_speed_delta_kmh_ = nan_();

    if (new_best) {
      best_lap_ms_ = elapsed;
      best_trace_ = current_trace_;
      best_sector_times_ms_ = sector_times_ms_;
      new_best_event_ = previous_best > 0;
    }

    last_lap_average_speed_kmh_ = lap_average_speed;

    // V12.0.11.9.5 / RLCD V1.5:
    // a pit/very slow lap or a lap slower than BEST+30s is excluded.
    // Exclusion does NOT break the valid-lap sequence.
    const uint64_t valid_limit =
        static_cast<uint64_t>(best_lap_ms_) + race_pace_max_gap_ms_;
    last_lap_pace_valid_ =
        !current_lap_pit_stop_ &&
        elapsed <= valid_limit;

    pace_laps_.push_back(
        {elapsed, lap_average_speed, current_lap_pit_stop_});
    recompute_race_pace_();

    if (race_average_speed_kmh_ > 0.0f &&
        last_lap_average_speed_kmh_ > 0.0f) {
      post_lap_speed_delta_kmh_ =
          last_lap_average_speed_kmh_ - race_average_speed_kmh_;
    } else {
      post_lap_speed_delta_kmh_ = nan_();
    }

    if (race_pace_ms_ > 0) {
      post_lap_pace_delta_seconds_ =
          (static_cast<int64_t>(elapsed) -
           static_cast<int64_t>(race_pace_ms_)) / 1000.0f;
    } else {
      post_lap_pace_delta_seconds_ = nan_();
    }

    lap_completed_event_ = true;

    previous_lap_trace_ = current_trace_;
    previous_sector_times_ms_ = sector_times_ms_;
    previous_lap_average_speed_kmh_ = lap_average_speed;

    final_hold_until_ms_ = now_ms + 10000U;
    // Keep each completed sector delta visible through the finish, then
    // clear all sector cells 5 s after the finish for the next lap.
    sector_display_reset_at_ms_ = now_ms + 5000U;
    lap_number_++;
    lap_start_ms_ = sector_start_ms_ = now_ms;
    lap_start_wall_ms_ = millis();
    next_sector_ = 0;
    sector_times_ms_.clear();
    sector_status_.assign(timing_sector_count(), 0);
    current_trace_.clear();
    last_trace_sample_ms_ = 0;
    live_delta_seconds_ = nan_();
    last_live_delta_filter_ms_ = 0;
    live_speed_delta_kmh_ = nan_();
    lap_speed_sum_ = 0.0;
    lap_speed_samples_ = 0;
    current_lap_pit_stop_ = false;
    low_speed_started_ms_ = 0;
  }

  void start_sector_hold_(
      size_t index, uint32_t current_ms, uint32_t now_ms) {
    // Called for every completed timing sector, including the final sector
    // that ends on the finish line.
    last_sector_number_ = index + 1;
    last_sector_status_ =
        index < sector_status_.size() ? sector_status_[index] : 0;

    // Delta displayed against the Best Lap sector when available.
    // If there is no Best reference yet, use the previous-lap sector.
    if (index < best_sector_times_ms_.size() &&
        best_sector_times_ms_[index] > 0) {
      last_sector_delta_seconds_ =
          (static_cast<int64_t>(current_ms) -
           static_cast<int64_t>(best_sector_times_ms_[index])) / 1000.0f;
    } else if (index < previous_sector_times_ms_.size() &&
               previous_sector_times_ms_[index] > 0) {
      last_sector_delta_seconds_ =
          (static_cast<int64_t>(current_ms) -
           static_cast<int64_t>(previous_sector_times_ms_[index])) / 1000.0f;
    } else {
      last_sector_delta_seconds_ = nan_();
    }

    if (sector_display_delta_seconds_.size() <= index)
      sector_display_delta_seconds_.resize(index + 1, nan_());
    if (sector_display_status_.size() <= index)
      sector_display_status_.resize(index + 1, 0);
    sector_display_delta_seconds_[index] = last_sector_delta_seconds_;
    sector_display_status_[index] = last_sector_status_;
    sector_hold_until_ms_ = now_ms + 5000U;
  }

  void update_sector_status_(size_t index, uint32_t current_ms) {
    if (sector_status_.size() < timing_sector_count())
      sector_status_.resize(timing_sector_count(), 0);
    if (index >= sector_status_.size()) return;

    const bool have_best = index < best_sector_times_ms_.size() &&
                           best_sector_times_ms_[index] > 0;
    const bool have_previous = index < previous_sector_times_ms_.size() &&
                               previous_sector_times_ms_[index] > 0;

    // 1 = fucsia: più veloce del corrispondente settore del Best Lap.
    if (have_best && current_ms < best_sector_times_ms_[index]) {
      sector_status_[index] = 1;
      return;
    }

    // 2 = rosso: peggiore o uguale al giro precedente.
    if (have_previous && current_ms >= previous_sector_times_ms_[index]) {
      sector_status_[index] = 2;
      return;
    }

    // 3 = verde: non batte il Best Lap ma migliora il giro precedente.
    if (have_best && have_previous &&
        current_ms >= best_sector_times_ms_[index] &&
        current_ms < previous_sector_times_ms_[index]) {
      sector_status_[index] = 3;
      return;
    }

    sector_status_[index] = 0;
  }

  void sample_trace_(
      double lat, double lon, float speed_kmh, uint32_t now_ms) {
    if (current_trace_.size() >= max_trace_points_) return;
    if (last_trace_sample_ms_ != 0 &&
        now_ms - last_trace_sample_ms_ < trace_period_ms_) return;
    last_trace_sample_ms_ = now_ms;
    current_trace_.push_back({lat, lon, safe_elapsed_(now_ms, lap_start_ms_), speed_kmh});
  }

  void calculate_live_delta_(double lat, double lon, uint32_t now_ms) {
    if (best_trace_.size() < 5) return;
    double best_d = 1e30;
    uint32_t reference_ms = 0;
    for (const auto &p : best_trace_) {
      const double d = distance_m_(lat, lon, p.lat, p.lon);
      if (d < best_d) {
        best_d = d;
        reference_ms = p.elapsed_ms;
      }
    }
    if (best_d <= max_match_distance_m_) {
      // Filtro passa-basso temporale (costante 1 s) applicato SOLO al
      // delta mostrato. Il matching spaziale resta sul Best Lap e i
      // tempi dei giri/settori e la traccia registrata non cambiano.
      const float raw_delta =
          (static_cast<int64_t>(now_ms - lap_start_ms_) -
           static_cast<int64_t>(reference_ms)) / 1000.0f;
      if (!std::isfinite(live_delta_seconds_) ||
          last_live_delta_filter_ms_ == 0 ||
          static_cast<int32_t>(now_ms - last_live_delta_filter_ms_) <= 0) {
        live_delta_seconds_ = raw_delta;
      } else {
        const uint32_t dt_ms = now_ms - last_live_delta_filter_ms_;
        const float alpha = static_cast<float>(dt_ms) /
                            (live_delta_filter_tau_ms_ + static_cast<float>(dt_ms));
        live_delta_seconds_ += alpha * (raw_delta - live_delta_seconds_);
      }
      last_live_delta_filter_ms_ = now_ms;
    }
  }

  void calculate_live_speed_delta_(
      double lat, double lon, float speed_kmh, uint32_t now_ms) {
    if (previous_lap_trace_.size() < 5 ||
        final_hold_active(now_ms) ||
        !std::isfinite(speed_kmh))
      return;

    double best_d = 1e30;
    float reference_speed = 0.0f;

    for (const auto &p : previous_lap_trace_) {
      const double d = distance_m_(lat, lon, p.lat, p.lon);
      if (d < best_d) {
        best_d = d;
        reference_speed = p.speed_kmh;
      }
    }

    if (best_d <= max_match_distance_m_ &&
        std::isfinite(reference_speed))
      live_speed_delta_kmh_ = speed_kmh - reference_speed;
  }

  void recompute_race_pace_() {
    race_pace_ms_ = 0;
    race_pace_lap_count_ = 0;
    race_average_speed_kmh_ = 0.0f;

    if (best_lap_ms_ == 0) return;

    const uint64_t maximum =
        static_cast<uint64_t>(best_lap_ms_) +
        race_pace_max_gap_ms_;

    std::vector<const PaceLap*> valid;
    valid.reserve(pace_laps_.size());

    for (const auto &lap : pace_laps_) {
      if (lap.pit_stop) continue;
      if (lap.lap_ms > maximum) continue;
      valid.push_back(&lap);
    }

    if (valid.empty()) return;

    // During the first laps the available valid sample is used.
    // From 10 valid laps onward the displayed PASSO GARA is the fastest
    // average window of 10 valid laps. Invalid laps are simply skipped.
    const size_t window = std::min<size_t>(10, valid.size());

    uint64_t best_sum = std::numeric_limits<uint64_t>::max();
    double best_speed_sum = 0.0;

    for (size_t first = 0; first + window <= valid.size(); ++first) {
      uint64_t sum = 0;
      double speed_sum = 0.0;
      size_t speed_n = 0;

      for (size_t j = 0; j < window; ++j) {
        const PaceLap &p = *valid[first + j];
        sum += p.lap_ms;
        if (std::isfinite(p.average_speed_kmh) &&
            p.average_speed_kmh > 0.0f) {
          speed_sum += p.average_speed_kmh;
          speed_n++;
        }
      }

      if (sum < best_sum) {
        best_sum = sum;
        best_speed_sum = speed_n ? speed_sum / speed_n : 0.0;
      }
    }

    if (best_sum != std::numeric_limits<uint64_t>::max()) {
      race_pace_lap_count_ = static_cast<uint32_t>(window);
      race_pace_ms_ =
          static_cast<uint32_t>(best_sum / window);
      race_average_speed_kmh_ =
          static_cast<float>(best_speed_sum);
    }
  }

  static bool valid_coordinate_(double lat, double lon) {
    return std::isfinite(lat) && std::isfinite(lon) &&
           lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180 &&
           !(lat == 0.0 && lon == 0.0);
  }

  struct XY { double x, y; };
  static XY to_local_(double lat, double lon, double o_lat, double o_lon) {
    constexpr double m = 111319.49079327358;
    return {(lon-o_lon)*m*std::cos(o_lat*3.141592653589793/180.0),
            (lat-o_lat)*m};
  }
  static double orientation_(const XY&a,const XY&b,const XY&c) {
    return (b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x);
  }
  static bool segments_intersect_local_(
      double a1,double o1,double a2,double o2,
      double b1,double p1,double b2,double p2) {
    double ol=(a1+a2+b1+b2)*.25, on=(o1+o2+p1+p2)*.25;
    XY A=to_local_(a1,o1,ol,on),B=to_local_(a2,o2,ol,on);
    XY C=to_local_(b1,p1,ol,on),D=to_local_(b2,p2,ol,on);
    double x1=orientation_(A,B,C),x2=orientation_(A,B,D);
    double x3=orientation_(C,D,A),x4=orientation_(C,D,B);
    return ((x1>0&&x2<0)||(x1<0&&x2>0)) &&
           ((x3>0&&x4<0)||(x3<0&&x4>0));
  }
  static double distance_m_(double a,double o,double b,double p) {
    XY q=to_local_(b,p,a,o);
    return std::hypot(q.x,q.y);
  }
  static double point_segment_distance_m_(
      double p_lat,double p_lon,double a_lat,double a_lon,
      double b_lat,double b_lon) {
    XY p{0,0}, a=to_local_(a_lat,a_lon,p_lat,p_lon),
       b=to_local_(b_lat,b_lon,p_lat,p_lon);
    double vx=b.x-a.x,vy=b.y-a.y, l=vx*vx+vy*vy;
    if(l<1e-9) return std::hypot(a.x,a.y);
    double t=std::max(0.0,std::min(1.0,(-a.x*vx-a.y*vy)/l));
    return std::hypot(a.x+t*vx,a.y+t*vy);
  }
  static std::string format_time_(uint32_t ms) {
    char b[24];
    std::snprintf(b,sizeof(b),"%02lu:%02lu.%03lu",
      static_cast<unsigned long>(ms/60000),
      static_cast<unsigned long>((ms/1000)%60),
      static_cast<unsigned long>(ms%1000));
    return std::string(b);
  }
};

static GoatsLaptimerEngine GOATS_LAPTIMER;

inline void goats_laptimer_reset(){GOATS_LAPTIMER.reset();}
inline void goats_laptimer_update(const GoatsTrackUsb*t,bool f,double a,double o,
 float s,uint32_t n,uint32_t itow=0){GOATS_LAPTIMER.update(t,f,a,o,s,n,itow);}
inline bool goats_laptimer_running(){return GOATS_LAPTIMER.running();}
inline uint32_t goats_laptimer_lap_number(){return GOATS_LAPTIMER.lap_number();}
inline uint32_t goats_laptimer_last_lap_ms(){return GOATS_LAPTIMER.last_lap_ms();}
inline uint32_t goats_laptimer_best_lap_ms(){return GOATS_LAPTIMER.best_lap_ms();}
inline uint32_t goats_laptimer_last_finish_ms(){return GOATS_LAPTIMER.last_finish_ms();}
inline float goats_laptimer_live_delta_seconds(){
 return GOATS_LAPTIMER.live_delta_seconds();}
inline float goats_laptimer_display_delta_seconds(uint32_t n){
 return GOATS_LAPTIMER.display_delta_seconds(n);}
inline float goats_laptimer_display_speed_delta_kmh(uint32_t n){
 return GOATS_LAPTIMER.display_speed_delta_kmh(n);}
inline uint32_t goats_laptimer_race_pace_ms(){
 return GOATS_LAPTIMER.race_pace_ms();}
inline uint32_t goats_laptimer_race_pace_lap_count(){
 return GOATS_LAPTIMER.race_pace_lap_count();}
inline std::string goats_laptimer_race_pace_text(){
 return GOATS_LAPTIMER.race_pace_text();}
inline float goats_laptimer_race_average_speed_kmh(){
 return GOATS_LAPTIMER.race_average_speed_kmh();}
inline float goats_laptimer_last_lap_average_speed_kmh(){
 return GOATS_LAPTIMER.last_lap_average_speed_kmh();}
inline float goats_laptimer_post_lap_speed_delta_kmh(){
 return GOATS_LAPTIMER.post_lap_speed_delta_kmh();}
inline float goats_laptimer_post_lap_pace_delta_seconds(){
 return GOATS_LAPTIMER.post_lap_pace_delta_seconds();}
inline float goats_laptimer_post_lap_best_delta_seconds(){
 return GOATS_LAPTIMER.post_lap_best_delta_seconds();}
inline bool goats_laptimer_last_lap_pace_valid(){
 return GOATS_LAPTIMER.last_lap_pace_valid();}
inline bool goats_laptimer_consume_lap_completed_event(){
 return GOATS_LAPTIMER.consume_lap_completed_event();}
inline bool goats_laptimer_final_hold_active(uint32_t n){
 return GOATS_LAPTIMER.final_hold_active(n);}
inline bool goats_laptimer_final_blink_on(uint32_t n){
 return GOATS_LAPTIMER.final_blink_on(n);}
inline bool goats_laptimer_consume_new_best_event(){
 return GOATS_LAPTIMER.consume_new_best_event();}
inline std::string goats_laptimer_current_text(){
 return GOATS_LAPTIMER.current_text(millis());}
inline uint32_t goats_laptimer_current_ms(uint32_t now_ms){ return GOATS_LAPTIMER.current_ms(now_ms); }
inline uint32_t goats_laptimer_display_current_ms(uint32_t now_ms){ return GOATS_LAPTIMER.display_current_ms(now_ms); }
inline std::string goats_laptimer_last_text(){return GOATS_LAPTIMER.last_text();}
inline std::string goats_laptimer_best_text(){return GOATS_LAPTIMER.best_text();}
inline size_t goats_laptimer_timing_sector_count(){
 return GOATS_LAPTIMER.timing_sector_count();}
inline int goats_laptimer_sector_status(size_t i){
 return GOATS_LAPTIMER.sector_status(i);}
inline bool goats_laptimer_sector_hold_active(uint32_t now_ms){
 return GOATS_LAPTIMER.sector_hold_active(now_ms);}
inline float goats_laptimer_sector_hold_delta_seconds(){
 return GOATS_LAPTIMER.sector_hold_delta_seconds();}
inline int goats_laptimer_sector_hold_status(){
 return GOATS_LAPTIMER.sector_hold_status();}
inline size_t goats_laptimer_sector_hold_number(){
 return GOATS_LAPTIMER.sector_hold_number();}
inline size_t goats_laptimer_configured_sector_count(){
 return GOATS_LAPTIMER.configured_sector_count();}
inline float goats_laptimer_sector_display_delta_seconds(size_t i,uint32_t n){
 return GOATS_LAPTIMER.sector_display_delta_seconds(i,n);}
inline int goats_laptimer_sector_display_status(size_t i,uint32_t n){
 return GOATS_LAPTIMER.sector_display_status(i,n);}
inline size_t goats_laptimer_last_timing_sector_count(){
 return GOATS_LAPTIMER.last_timing_sector_count();}
inline uint32_t goats_laptimer_last_timing_sector_ms(size_t i){
 return GOATS_LAPTIMER.last_timing_sector_ms(i);}

// Guition V1.0.15 GUI compatibility: RLCD TEST26 keeps the displayed sector
// delta in its own display state, while the Guition UI expects this accessor.
inline float goats_laptimer_sector_delta_best_seconds(size_t i) {
  return GOATS_LAPTIMER.sector_display_delta_seconds(i, millis());
}
