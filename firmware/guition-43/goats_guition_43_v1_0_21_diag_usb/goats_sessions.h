#pragma once

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
#include "nvs.h"
#include "nvs_flash.h"
#include "goats_sd_storage.h"

struct GoatsTracePoint {
  int32_t latitude_e7{0};
  int32_t longitude_e7{0};

  // GSA3: tempo relativo quantizzato a 40 ms.
  // 1 tick = 1 aggiornamento nominale del GPS a 25 Hz.
  // uint16_t copre circa 43 minuti per singolo giro/traccia.
  uint16_t elapsed_40ms{0};

  // Velocita in decimi di km/h.
  uint16_t speed_tenth_kmh{0};
};

struct GoatsLapRecord {
  uint16_t number{0};
  uint32_t lap_time_ms{0};
  float max_speed_kmh{0.0f};
  float average_speed_kmh{0.0f};
  std::vector<GoatsTracePoint> trace;
};

struct GoatsSessionRecord {
  uint32_t session_id{0};
  std::string date;
  std::string time;
  std::string track_name;
  uint32_t duration_ms{0};
  uint32_t best_lap_ms{0};
  uint32_t last_lap_ms{0};
  float max_speed_kmh{0.0f};
  float average_speed_kmh{0.0f};
  float average_hdop{0.0f};
  float average_satellites{0.0f};
  std::vector<GoatsLapRecord> laps;
};

class GoatsSessionManager {
 public:
  void setup() {
    load_archive_();
    recover_checkpoint_();
    reset_runtime();
  }

  // V11.0.2.30: SD is initialized post-boot, after the normal session setup.
  // Reload only persistent data when the SD becomes ready, without resetting
  // an already running session state.
  void reload_persistent() {
    if (!goats_sd_storage::ready()) return;
    load_archive_();
    recover_checkpoint_();
  }

  void reset_runtime() {
    goats_diag_v1021::session_end();
    active_ = false;
    free_mode_ = false;
    finished_ = false;
    auto_finished_ = false;
    summary_visible_request_ = false;
    last_save_ok_ = false;
    start_ms_ = 0;
    end_ms_ = 0;
    last_seen_lap_number_ = 0;
    best_lap_ms_ = 0;
    last_lap_ms_ = 0;
    session_max_speed_kmh_ = 0.0f;
    session_speed_sum_ = 0.0;
    session_speed_samples_ = 0;
    lap_max_speed_kmh_ = 0.0f;
    lap_speed_sum_ = 0.0;
    lap_speed_samples_ = 0;
    hdop_sum_ = 0.0;
    sat_sum_ = 0.0;
    quality_samples_ = 0;
    current_laps_.clear();
    current_trace_.clear();
    last_trace_sample_ms_ = 0;
    last_sd_trace_sample_ms_ = 0;
    lap_trace_start_ms_ = 0;
    last_saved_session_id_ = 0;
    checkpoint_session_id_ = 0;
    current_track_name_.clear();
    current_date_.clear();
    current_time_.clear();
  }

  void update(bool laptimer_running,
              uint32_t lap_number,
              uint32_t last_lap_ms,
              uint32_t best_lap_ms,
              uint32_t last_finish_ms,
              float speed_kmh,
              float hdop,
              int satellites,
              uint32_t now_ms,
              const char *track_name,
              const char *date_text,
              const char *time_text,
              double latitude,
              double longitude) {
    if (finished_) return;

    // In registrazione libera il laptimer circuito viene ignorato.
    // La sessione raccoglie direttamente GPS, tempo e velocità.
    if (free_mode_) {
      if (!active_) return;
      update_free_(speed_kmh, hdop, satellites, now_ms,
                   latitude, longitude);
      return;
    }

    if (laptimer_running && !active_) {
      active_ = true;
      goats_diag_v1021::session_begin();
      start_ms_ = now_ms;
      last_seen_lap_number_ = lap_number;
      current_track_name_ = safe_text_(track_name, "Circuito");
      current_date_ = safe_text_(date_text, "--/--/----");
      current_time_ = safe_text_(time_text, "--:--");
      checkpoint_session_id_ = next_session_id_();
      lap_trace_start_ms_ = now_ms;
      last_trace_sample_ms_ = 0;
      last_sd_trace_sample_ms_ = 0;
      current_trace_.clear();

      const bool sd_started = goats_sd_storage::begin_live_session(
          "CIRCUITO",
          current_date_.c_str(),
          current_time_.c_str(),
          current_track_name_.c_str());
      if (!sd_started) {
        active_ = false;
        finished_ = true;
        goats_diag_v1021::session_end();
        last_save_ok_ = false;
        return;
      }
    }

    if (!active_) return;

    // V9.2 - Traccia integrale su microSD: nessun limite RAM/endurance.
    if (std::isfinite(latitude) && std::isfinite(longitude) &&
        std::fabs(latitude) <= 90.0 && std::fabs(longitude) <= 180.0 &&
        !(latitude == 0.0 && longitude == 0.0) &&
        (last_sd_trace_sample_ms_ == 0 ||
         static_cast<uint32_t>(now_ms - last_sd_trace_sample_ms_) >= TRACE_PERIOD_MS)) {
      goats_sd_storage::append_live_point(
          now_ms >= start_ms_ ? now_ms - start_ms_ : 0,
          lap_number,
          latitude,
          longitude,
          speed_kmh,
          hdop,
          satellites);
      last_sd_trace_sample_ms_ = now_ms;
    }

    // Buffer RAM ridotto usato solo per compatibilita con archivio GSA3/UI.
    // La traccia completa continua invece sulla microSD.
    // High Resolution GPS: registra fino a 25 punti al secondo
    // (un campione ogni 40 ms) senza interpolazione.
    // Coordinate compresse a 1e-7 gradi.
    if (std::isfinite(latitude) && std::isfinite(longitude) &&
        std::fabs(latitude) <= 90.0 && std::fabs(longitude) <= 180.0 &&
        (last_trace_sample_ms_ == 0 ||
         static_cast<uint32_t>(now_ms - last_trace_sample_ms_) >= TRACE_PERIOD_MS) &&
        current_trace_.size() < MAX_TRACE_POINTS_PER_LAP &&
        stored_trace_points_() + current_trace_.size() <
            MAX_TRACE_POINTS_PER_SESSION) {
      GoatsTracePoint point;
      point.latitude_e7 = static_cast<int32_t>(std::llround(latitude * 10000000.0));
      point.longitude_e7 = static_cast<int32_t>(std::llround(longitude * 10000000.0));
      point.elapsed_40ms = static_cast<uint16_t>(
          std::min<uint32_t>(
              (now_ms - lap_trace_start_ms_) / TRACE_PERIOD_MS,
              65535UL));
      point.speed_tenth_kmh = static_cast<uint16_t>(
          std::min<float>(std::max<float>(speed_kmh, 0.0f) * 10.0f, 65535.0f));
      current_trace_.push_back(point);
      last_trace_sample_ms_ = now_ms;
    }

    if (std::isfinite(speed_kmh) && speed_kmh >= 0.0f) {
      session_max_speed_kmh_ = std::max(session_max_speed_kmh_, speed_kmh);
      session_speed_sum_ += speed_kmh;
      session_speed_samples_++;
      lap_max_speed_kmh_ = std::max(lap_max_speed_kmh_, speed_kmh);
      lap_speed_sum_ += speed_kmh;
      lap_speed_samples_++;
    }

    if (std::isfinite(hdop) && hdop > 0.0f && hdop < 50.0f) {
      hdop_sum_ += hdop;
      sat_sum_ += std::max(0, satellites);
      quality_samples_++;
    }

    if (lap_number != last_seen_lap_number_) {
      last_seen_lap_number_ = lap_number;
      if (last_lap_ms > 0 && current_laps_.size() < MAX_LAPS_PER_SESSION) {
        GoatsLapRecord lap;
        lap.number = static_cast<uint16_t>(current_laps_.size() + 1);
        lap.lap_time_ms = last_lap_ms;
        lap.max_speed_kmh = lap_max_speed_kmh_;
        lap.average_speed_kmh = lap_speed_samples_ > 0
            ? static_cast<float>(lap_speed_sum_ / lap_speed_samples_) : 0.0f;
        lap.trace = current_trace_;
        current_laps_.push_back(std::move(lap));
        last_lap_ms_ = last_lap_ms;
        best_lap_ms_ = best_lap_ms;
        // V10.2.5F: checkpoint persistente dopo ogni giro completato.
        save_checkpoint_(now_ms);
      }
      lap_max_speed_kmh_ = 0.0f;
      lap_speed_sum_ = 0.0;
      lap_speed_samples_ = 0;
      current_trace_.clear();
      lap_trace_start_ms_ = now_ms;
      last_trace_sample_ms_ = 0;
    }

    if (last_finish_ms > 0 &&
        static_cast<uint32_t>(now_ms - last_finish_ms) >= 600000UL) {
      finish_(now_ms, true);
    }
  }

  bool prepare_free(uint32_t now_ms,
                    const char *date_text,
                    const char *time_text) {
    if (active_ && !finished_) return false;

    reset_runtime();
    active_ = true;
    goats_diag_v1021::session_begin();
    free_mode_ = true;
    free_storage_attached_ = false;
    start_ms_ = now_ms;
    lap_trace_start_ms_ = now_ms;
    last_trace_sample_ms_ = 0;
    current_track_name_ = "REGISTRAZIONE LIBERA";
    current_date_ = safe_text_(date_text, "--/--/----");
    current_time_ = safe_text_(time_text, "--:--");
    checkpoint_session_id_ = next_session_id_();
    last_sd_trace_sample_ms_ = 0;
    return true;
  }

  bool attach_free_storage() {
    if (!free_mode_ || !active_ || finished_) return false;
    const bool sd_started = goats_sd_storage::begin_live_session(
        "LIBERA",
        current_date_.c_str(),
        current_time_.c_str(),
        current_track_name_.c_str());
    free_storage_attached_ = sd_started;
    if (!sd_started) {
      // V11.0.2.26: an SD attach error must NOT stop the free session.
      // Keep collecting the RAM trace so we can diagnose the exact SD stage
      // without the apparent "5 points then stop" behaviour.
      last_save_ok_ = false;
      return false;
    }
    return true;
  }

  bool free_storage_attached() const {
    return free_mode_ && free_storage_attached_ &&
           goats_sd_storage::live_open();
  }

  bool start_free(uint32_t now_ms,
                  const char *date_text,
                  const char *time_text) {
    if (!prepare_free(now_ms, date_text, time_text)) return false;
    return attach_free_storage();
  }

  bool finish_free(uint32_t now_ms) {
    if (!free_mode_ || !active_ || finished_) return false;

    const uint32_t duration =
        now_ms > start_ms_ ? now_ms - start_ms_ : 0;

    GoatsLapRecord trace_record;
    trace_record.number = 1;
    trace_record.lap_time_ms = duration;
    trace_record.max_speed_kmh = session_max_speed_kmh_;
    trace_record.average_speed_kmh =
        session_speed_samples_ > 0
            ? static_cast<float>(
                  session_speed_sum_ / session_speed_samples_)
            : 0.0f;
    trace_record.trace = current_trace_;

    current_laps_.clear();
    current_laps_.push_back(std::move(trace_record));
    last_lap_ms_ = duration;
    best_lap_ms_ = duration;

    finish_(now_ms, false);
    summary_visible_request_ = true;
    return last_save_ok_;
  }

  bool last_save_ok() const {
    return last_save_ok_;
  }

  bool free_active() const {
    return free_mode_ && active_ && !finished_;
  }

  uint32_t free_elapsed_ms(uint32_t now_ms) const {
    return free_active() && now_ms >= start_ms_
        ? now_ms - start_ms_
        : 0;
  }

  size_t free_trace_points() const {
    return free_mode_ ? current_trace_.size() : 0;
  }

  float current_max_speed() const {
    return session_max_speed_kmh_;
  }

  bool trace_storage_full() const {
    if (free_mode_)
      return current_trace_.size() >= MAX_FREE_TRACE_POINTS;
    return stored_trace_points_() + current_trace_.size() >=
           MAX_TRACE_POINTS_PER_SESSION;
  }

  void discard_current() {
    goats_sd_storage::discard_live_session();
    goats_sd_storage::remove_checkpoint();
    reset_runtime();
  }

  void finish_manual(uint32_t now_ms) {
    if (!active_ || finished_) return;
    if (free_mode_) {
      finish_free(now_ms);
      return;
    }
    finish_(now_ms, false);
    summary_visible_request_ = true;
  }

  bool active() const { return active_ && !finished_; }

  uint32_t stint_elapsed_ms(uint32_t now_ms) const {
    if (!active() || now_ms < start_ms_) return 0;
    return now_ms - start_ms_;
  }
  bool auto_finished() const { return auto_finished_; }
  void clear_auto_finished() { auto_finished_ = false; }
  bool summary_visible_request() const { return summary_visible_request_; }
  void clear_summary_visible_request() { summary_visible_request_ = false; }

  size_t count() const { return archive_.size(); }

  const GoatsSessionRecord *display_session(size_t display_index) const {
    if (display_index >= archive_.size()) return nullptr;
    return &archive_[archive_.size() - 1 - display_index];
  }

  bool delete_display_session(size_t display_index) {
    if (display_index >= archive_.size()) return false;
    const size_t real_index = archive_.size() - 1 - display_index;
    const uint32_t session_id = archive_[real_index].session_id;
    archive_.erase(archive_.begin() + real_index);
    goats_sd_storage::remove_trace(session_id);
    goats_sd_storage::remove_session_meta(session_id);
    return save_archive_();
  }

  bool clear_archive() {
    archive_.clear();
    goats_sd_storage::clear_session_files();
    return goats_sd_storage::remove_archive();
  }


  std::vector<uint8_t> export_blob() const {
    // V11.0.2.40: send only compact persistent metadata through GSES2/GSES.
    // The Manager retrieves the full 25 Hz trace separately from Sxxxxxx.CSV
    // with the already streaming-safe GSD_GET command. This avoids rebuilding
    // a potentially huge GSA3 payload in ESP32 RAM and removes the reset path.
    std::vector<uint8_t> data;
    data.insert(data.end(), {'G','S','A','3'});
    append_u16_(data, 3);
    append_u16_(data, static_cast<uint16_t>(archive_.size()));
    for (const auto &archived : archive_) {
      serialize_session_(data, archived);
      taskYIELD();
    }
    return data;
  }

  std::string list_date(size_t i) const {
    const auto *s = display_session(i);
    return s ? s->date : "";
  }
  std::string list_time(size_t i) const {
    const auto *s = display_session(i);
    return s ? s->time : "";
  }
  std::string list_track(size_t i) const {
    const auto *s = display_session(i);
    return s ? s->track_name : "";
  }
  std::string detail_header(size_t i) const {
    const auto *s = display_session(i);
    if (!s) return "NESSUNA SESSIONE";
    return s->date + "  " + s->time + "  -  " + s->track_name;
  }
  std::string detail_laps(size_t i) const {
    const auto *s = display_session(i);
    if (!s) return "";
    std::string out = "GIRO    TEMPO         V MAX    V MED\n";
    for (const auto &lap : s->laps) {
      char line[72];
      const bool best = lap.lap_time_ms == s->best_lap_ms;
      std::snprintf(line, sizeof(line),
          "%-3u     %s     %5.1f    %5.1f%s\n",
          static_cast<unsigned>(lap.number),
          format_lap_(lap.lap_time_ms).c_str(),
          lap.max_speed_kmh, lap.average_speed_kmh,
          best ? "  BEST" : "");
      out += line;
    }
    return out;
  }

  std::string detail_laps_number(size_t i) const {
    const auto *sess = display_session(i);
    if (!sess) return "";
    std::string out;
    for (const auto &lap : sess->laps) {
      out += std::to_string(lap.number);
      out += "\n";
    }
    return out;
  }

  std::string detail_laps_time(size_t i) const {
    const auto *sess = display_session(i);
    if (!sess) return "";
    std::string out;
    for (const auto &lap : sess->laps) {
      out += format_lap_(lap.lap_time_ms);
      out += "\n";
    }
    return out;
  }

  std::string detail_laps_vmax(size_t i) const {
    const auto *sess = display_session(i);
    if (!sess) return "";
    std::string out;
    char b[24];
    for (const auto &lap : sess->laps) {
      std::snprintf(b, sizeof(b), "%.1f", lap.max_speed_kmh);
      out += b;
      out += "\n";
    }
    return out;
  }

  std::string detail_laps_vavg(size_t i) const {
    const auto *sess = display_session(i);
    if (!sess) return "";
    std::string out;
    char b[24];
    for (const auto &lap : sess->laps) {
      std::snprintf(b, sizeof(b), "%.1f", lap.average_speed_kmh);
      out += b;
      out += "\n";
    }
    return out;
  }

  std::string detail_laps_best(size_t i) const {
    const auto *sess = display_session(i);
    if (!sess) return "";
    std::string out;
    for (const auto &lap : sess->laps) {
      out += (lap.lap_time_ms == sess->best_lap_ms) ? "BEST" : "";
      out += "\n";
    }
    return out;
  }

  std::string detail_lap_count(size_t i) const {
    const auto *s = display_session(i);
    return s ? std::to_string(s->laps.size()) : "0";
  }
  std::string detail_duration(size_t i) const {
    const auto *s = display_session(i);
    return s ? format_duration_(s->duration_ms) : "00:00";
  }
  std::string detail_best(size_t i) const {
    const auto *s = display_session(i);
    return s ? format_lap_(s->best_lap_ms) : "--:--.---";
  }
  std::string detail_vmax(size_t i) const {
    const auto *s = display_session(i);
    return s ? format_float_(s->max_speed_kmh) : "0.0";
  }
  std::string detail_vavg(size_t i) const {
    const auto *s = display_session(i);
    return s ? format_float_(s->average_speed_kmh) : "0.0";
  }

  std::string summary_laps() const {
    return std::to_string(current_laps_.size());
  }
  std::string summary_best() const { return format_lap_(best_lap_ms_); }
  std::string summary_last() const { return format_lap_(last_lap_ms_); }
  std::string summary_duration() const {
    return format_duration_(end_ms_ > start_ms_ ? end_ms_ - start_ms_ : 0);
  }
  std::string summary_vmax() const {
    return format_float_(session_max_speed_kmh_) + " km/h";
  }

 private:
  static constexpr const char *NAMESPACE = "goats_sess2";
  static constexpr const char *KEY_ARCHIVE = "archive";
  static constexpr uint32_t MAGIC = 0x47534133;
  // Le tracce GPS occupano più spazio: manteniamo le 3 sessioni più recenti.
  static constexpr size_t MAX_SESSIONS = 20;
  static constexpr size_t MAX_LAPS_PER_SESSION = 80;

  // High Resolution GPS.
  static constexpr uint32_t TRACE_PERIOD_MS = 40UL;  // 25 Hz

  // Fino a 4.000 punti per giro = 160 s a 25 Hz.
  static constexpr size_t MAX_TRACE_POINTS_PER_LAP = 4000;

  // Budget complessivo della traiettoria per una sessione circuito.
  // 9.000 punti = circa 6 minuti di dati GPS continui a 25 Hz.
  // Tempi/statistiche continuano anche quando questo budget e esaurito.
  static constexpr size_t MAX_TRACE_POINTS_PER_SESSION = 3000;

  // Registrazione libera: stesso budget ad alta risoluzione.
  static constexpr size_t MAX_FREE_TRACE_POINTS = 3000;

  bool active_{false};
  bool free_mode_{false};
  bool free_storage_attached_{false};
  bool finished_{false};
  bool auto_finished_{false};
  bool summary_visible_request_{false};
  bool last_save_ok_{false};
  uint32_t start_ms_{0};
  uint32_t end_ms_{0};
  uint32_t last_seen_lap_number_{0};
  uint32_t best_lap_ms_{0};
  uint32_t last_lap_ms_{0};
  float session_max_speed_kmh_{0.0f};
  double session_speed_sum_{0.0};
  uint32_t session_speed_samples_{0};
  float lap_max_speed_kmh_{0.0f};
  double lap_speed_sum_{0.0};
  uint32_t lap_speed_samples_{0};
  double hdop_sum_{0.0};
  double sat_sum_{0.0};
  uint32_t quality_samples_{0};
  std::string current_track_name_;
  std::string current_date_;
  std::string current_time_;
  std::vector<GoatsLapRecord> current_laps_;
  std::vector<GoatsTracePoint> current_trace_;
  uint32_t last_trace_sample_ms_{0};
  uint32_t last_sd_trace_sample_ms_{0};
  uint32_t lap_trace_start_ms_{0};
  uint32_t last_saved_session_id_{0};
  uint32_t checkpoint_session_id_{0};
  std::vector<GoatsSessionRecord> archive_;

  size_t stored_trace_points_() const {
    size_t total = 0;
    for (const auto &lap : current_laps_)
      total += lap.trace.size();
    return total;
  }

  void update_free_(float speed_kmh,
                    float hdop,
                    int satellites,
                    uint32_t now_ms,
                    double latitude,
                    double longitude) {
    // V9.2 - Registrazione libera integrale su microSD.
    if (std::isfinite(latitude) && std::isfinite(longitude) &&
        std::fabs(latitude) <= 90.0 &&
        std::fabs(longitude) <= 180.0 &&
        !(latitude == 0.0 && longitude == 0.0) &&
        (last_sd_trace_sample_ms_ == 0 ||
         static_cast<uint32_t>(
             now_ms - last_sd_trace_sample_ms_) >= TRACE_PERIOD_MS)) {
      goats_sd_storage::append_live_point(
          now_ms >= start_ms_ ? now_ms - start_ms_ : 0,
          0,
          latitude,
          longitude,
          speed_kmh,
          hdop,
          satellites);
      last_sd_trace_sample_ms_ = now_ms;
    }

    // Registrazione libera alla massima risoluzione nominale del GPS:
    // un punto ogni 40 ms (25 Hz), senza interpolazione.
    if (std::isfinite(latitude) && std::isfinite(longitude) &&
        std::fabs(latitude) <= 90.0 &&
        std::fabs(longitude) <= 180.0 &&
        !(latitude == 0.0 && longitude == 0.0) &&
        (last_trace_sample_ms_ == 0 ||
         static_cast<uint32_t>(
             now_ms - last_trace_sample_ms_) >= TRACE_PERIOD_MS) &&
        current_trace_.size() < MAX_FREE_TRACE_POINTS) {
      GoatsTracePoint point;
      point.latitude_e7 = static_cast<int32_t>(
          std::llround(latitude * 10000000.0));
      point.longitude_e7 = static_cast<int32_t>(
          std::llround(longitude * 10000000.0));
      point.elapsed_40ms = static_cast<uint16_t>(
          std::min<uint32_t>(
              (now_ms - start_ms_) / TRACE_PERIOD_MS,
              65535UL));
      point.speed_tenth_kmh = static_cast<uint16_t>(
          std::min<float>(
              std::max<float>(speed_kmh, 0.0f) * 10.0f,
              65535.0f));
      current_trace_.push_back(point);
      last_trace_sample_ms_ = now_ms;
    }

    if (std::isfinite(speed_kmh) && speed_kmh >= 0.0f) {
      session_max_speed_kmh_ =
          std::max(session_max_speed_kmh_, speed_kmh);
      session_speed_sum_ += speed_kmh;
      session_speed_samples_++;
    }

    if (std::isfinite(hdop) && hdop > 0.0f && hdop < 50.0f) {
      hdop_sum_ += hdop;
      sat_sum_ += std::max(0, satellites);
      quality_samples_++;
    }
  }

  static std::string safe_text_(const char *value, const char *fallback) {
    if (value == nullptr || value[0] == 0) return fallback;
    return std::string(value);
  }

  void finish_(uint32_t now_ms, bool automatic) {
    finished_ = true;
    active_ = false;
    end_ms_ = now_ms;
    auto_finished_ = automatic;
    // Salva anche una sessione senza giri se esiste una traccia live sulla SD.
    // In questo modo un test interrotto resta visibile nell'archivio e recuperabile.
    bool archived = false;
    bool trace_ok = false;
    if (!current_laps_.empty() || goats_sd_storage::live_points() > 0) {
      archived = save_current_();
      trace_ok =
          goats_sd_storage::finish_live_session(last_saved_session_id_);
      // The status file is deliberately tiny and human-readable from the
      // Manager SD browser.
      goats_sd_storage::write_last_save_status(
          last_saved_session_id_,
          archived,  // persistence accepted (meta and/or archive)
          archived,
          trace_ok);
    } else {
      trace_ok = goats_sd_storage::finish_live_session(0);
      goats_sd_storage::write_last_save_status(0, false, false, trace_ok);
    }
    last_save_ok_ = archived;
    // Cancella il checkpoint solo dopo una scrittura archivio riuscita.
    if (archived) goats_sd_storage::remove_checkpoint();
    goats_diag_v1021::session_end();
  }

  bool save_current_() {
    GoatsSessionRecord item;
    item.session_id = checkpoint_session_id_ != 0
        ? checkpoint_session_id_ : next_session_id_();
    last_saved_session_id_ = item.session_id;
    item.date = current_date_;
    item.time = current_time_;
    item.track_name = current_track_name_;
    item.duration_ms = end_ms_ > start_ms_ ? end_ms_ - start_ms_ : 0;
    item.best_lap_ms = best_lap_ms_;
    item.last_lap_ms = last_lap_ms_;
    item.max_speed_kmh = session_max_speed_kmh_;
    item.average_speed_kmh = session_speed_samples_ > 0
        ? static_cast<float>(session_speed_sum_ / session_speed_samples_) : 0.0f;
    item.average_hdop = quality_samples_ > 0
        ? static_cast<float>(hdop_sum_ / quality_samples_) : 0.0f;
    item.average_satellites = quality_samples_ > 0
        ? static_cast<float>(sat_sum_ / quality_samples_) : 0.0f;
    item.laps = current_laps_;
    // Persistent archive is intentionally compact. The complete 25 Hz
    // trajectory is kept in session_XXXXXX_trace.csv.
    for (auto &lap : item.laps) lap.trace.clear();

    if (archive_.size() >= MAX_SESSIONS)
      archive_.erase(archive_.begin());

    archive_.push_back(std::move(item));

    // First commit an independent one-session metadata file.
    // This is the primary persistence guarantee.
    std::vector<uint8_t> meta;
    meta.insert(meta.end(), {'G','S','A','3'});
    append_u16_(meta, 3);
    append_u16_(meta, 1);
    serialize_session_(meta, archive_.back());
    const bool meta_ok =
        goats_sd_storage::write_session_meta(last_saved_session_id_, meta);

    // archive.gsa3 remains a convenient global index/mirror.
    const bool archive_ok = save_archive_();

    // A session is considered saved when at least one persistent index
    // succeeded. On the next boot load_archive_() merges the redundant
    // per-session metadata back into the global list.
    if (meta_ok || archive_ok) return true;

    if (!archive_.empty() &&
        archive_.back().session_id == last_saved_session_id_) {
      archive_.pop_back();
    }
    return false;
  }

  GoatsSessionRecord make_current_record_(uint32_t now_ms) const {
    GoatsSessionRecord item;
    item.session_id = checkpoint_session_id_ != 0 ? checkpoint_session_id_ : next_session_id_();
    item.date = current_date_;
    item.time = current_time_;
    item.track_name = current_track_name_;
    item.duration_ms = now_ms > start_ms_ ? now_ms - start_ms_ : 0;
    item.best_lap_ms = best_lap_ms_;
    item.last_lap_ms = last_lap_ms_;
    item.max_speed_kmh = session_max_speed_kmh_;
    item.average_speed_kmh = session_speed_samples_ > 0
        ? static_cast<float>(session_speed_sum_ / session_speed_samples_) : 0.0f;
    item.average_hdop = quality_samples_ > 0
        ? static_cast<float>(hdop_sum_ / quality_samples_) : 0.0f;
    item.average_satellites = quality_samples_ > 0
        ? static_cast<float>(sat_sum_ / quality_samples_) : 0.0f;
    item.laps = current_laps_;
    return item;
  }

  bool save_checkpoint_(uint32_t now_ms) {
    if (!goats_sd_storage::ready() || current_laps_.empty()) return false;
    GoatsSessionRecord item = make_current_record_(now_ms);
    for (auto &lap : item.laps) lap.trace.clear();
    std::vector<uint8_t> data;
    data.insert(data.end(), {'G','S','A','3'});
    append_u16_(data, 3);
    append_u16_(data, 1);
    serialize_session_(data, item);
    return goats_sd_storage::write_checkpoint(data);
  }

  void recover_checkpoint_() {
    std::vector<uint8_t> data;
    if (!goats_sd_storage::read_checkpoint(data)) return;

    const auto saved_archive = archive_;
    if (!parse_archive_(data) || archive_.size() != 1) {
      archive_ = saved_archive;
      return;
    }
    const GoatsSessionRecord recovered = archive_[0];
    archive_ = saved_archive;

    bool exists = false;
    for (const auto &s : archive_) {
      if (s.session_id == recovered.session_id) { exists = true; break; }
    }
    bool committed = exists;
    if (!exists) {
      if (archive_.size() >= MAX_SESSIONS) archive_.erase(archive_.begin());
      archive_.push_back(recovered);
      committed = save_archive_();
      if (!committed) {
        // Non perdere il recovery: il checkpoint resta sulla SD.
        archive_ = saved_archive;
      }
    }
    if (committed) goats_sd_storage::remove_checkpoint();
  }

  uint32_t next_session_id_() const {
    uint32_t max_id = 0;
    for (const auto &s : archive_) max_id = std::max(max_id, s.session_id);
    return max_id + 1;
  }

  bool save_archive_() {
    if (!goats_sd_storage::ready()) return false;
    const std::vector<uint8_t> data = export_blob();
    return goats_sd_storage::write_archive(data);
  }


  void load_archive_() {
    archive_.clear();
    if (!goats_sd_storage::ready()) return;

    std::vector<uint8_t> data;
    if (goats_sd_storage::read_archive(data)) {
      if (!parse_archive_(data)) archive_.clear();
    }

    // Merge redundant per-session metadata. This recovers sessions even
    // when archive.gsa3 was missing/corrupted during the previous shutdown.
    bool added = false;
    const auto ids = goats_sd_storage::list_session_meta_ids();
    for (const uint32_t id : ids) {
      bool exists = false;
      for (const auto &s : archive_) {
        if (s.session_id == id) { exists = true; break; }
      }
      if (exists) continue;

      std::vector<uint8_t> meta;
      if (!goats_sd_storage::read_session_meta(id, meta)) continue;

      const auto saved = archive_;
      if (!parse_archive_(meta) || archive_.size() != 1 ||
          archive_[0].session_id != id) {
        archive_ = saved;
        continue;
      }

      GoatsSessionRecord recovered = archive_[0];
      archive_ = saved;
      if (archive_.size() >= MAX_SESSIONS)
        archive_.erase(archive_.begin());
      archive_.push_back(std::move(recovered));
      added = true;
    }

    std::sort(
        archive_.begin(), archive_.end(),
        [](const GoatsSessionRecord &a, const GoatsSessionRecord &b) {
          return a.session_id < b.session_id;
        });

    if (added) save_archive_();
  }


  bool parse_archive_(const std::vector<uint8_t> &data) {
    if (data.size() < 8) return false;

    const bool is_gsa2 =
        std::memcmp(data.data(), "GSA2", 4) == 0;
    const bool is_gsa3 =
        std::memcmp(data.data(), "GSA3", 4) == 0;
    if (!is_gsa2 && !is_gsa3) return false;

    size_t o = 4;
    uint16_t version = 0, count = 0;
    if (!read_(data, o, version) || !read_(data, o, count) ||
        !((is_gsa2 && (version == 1 || version == 2)) ||
          (is_gsa3 && version == 3)) ||
        count > MAX_SESSIONS) return false;
    std::vector<GoatsSessionRecord> parsed;
    for (uint16_t i = 0; i < count; i++) {
      GoatsSessionRecord s;
      uint16_t lap_count = 0;
      if (!read_(data,o,s.session_id) || !read_string_(data,o,s.date) ||
          !read_string_(data,o,s.time) || !read_string_(data,o,s.track_name) ||
          !read_(data,o,s.duration_ms) || !read_(data,o,s.best_lap_ms) ||
          !read_(data,o,s.last_lap_ms) || !read_(data,o,s.max_speed_kmh) ||
          !read_(data,o,s.average_speed_kmh) || !read_(data,o,s.average_hdop) ||
          !read_(data,o,s.average_satellites) || !read_(data,o,lap_count) ||
          lap_count > MAX_LAPS_PER_SESSION) return false;
      for (uint16_t l=0; l<lap_count; l++) {
        GoatsLapRecord lap;
        if (!read_(data,o,lap.number) || !read_(data,o,lap.lap_time_ms) ||
            !read_(data,o,lap.max_speed_kmh) ||
            !read_(data,o,lap.average_speed_kmh)) return false;
        if (version >= 2) {
          uint16_t trace_count = 0;
          if (!read_(data,o,trace_count) ||
              trace_count > MAX_FREE_TRACE_POINTS) return false;

          for (uint16_t t=0; t<trace_count; t++) {
            GoatsTracePoint point;
            if (!read_(data,o,point.latitude_e7) ||
                !read_(data,o,point.longitude_e7))
              return false;

            if (is_gsa3) {
              if (!read_(data,o,point.elapsed_40ms))
                return false;
            } else {
              // GSA2: il vecchio timestamp era espresso in 100 ms.
              uint16_t elapsed_100ms = 0;
              if (!read_(data,o,elapsed_100ms))
                return false;
              const uint32_t elapsed_ms =
                  static_cast<uint32_t>(elapsed_100ms) * 100UL;
              point.elapsed_40ms = static_cast<uint16_t>(
                  std::min<uint32_t>(
                      elapsed_ms / TRACE_PERIOD_MS, 65535UL));
            }

            if (!read_(data,o,point.speed_tenth_kmh))
              return false;

            lap.trace.push_back(point);
          }
        }
        s.laps.push_back(std::move(lap));
      }
      parsed.push_back(std::move(s));
    }
    if (o != data.size()) return false;
    archive_ = std::move(parsed);
    return true;
  }

  static bool hydrate_trace_from_sd_(GoatsSessionRecord &session) {
    if (session.session_id == 0 || session.laps.empty() ||
        !goats_sd_storage::ready()) {
      return false;
    }

    // Persistent metadata deliberately stores no trace.
    for (auto &lap : session.laps) lap.trace.clear();

    const bool free_mode =
        session.track_name == "REGISTRAZIONE LIBERA" &&
        session.laps.size() == 1;

    std::vector<uint32_t> first_elapsed(session.laps.size(), 0);
    std::vector<bool> first_seen(session.laps.size(), false);

    size_t accepted = 0;
    const bool read_ok = goats_sd_storage::visit_saved_trace(
        session.session_id,
        [&](const goats_sd_storage::SavedTraceRow &row) {
          size_t lap_index = session.laps.size();

          if (free_mode) {
            // Free recording is stored with lap=0 on SD but exported as lap 1.
            lap_index = 0;
          } else {
            for (size_t i = 0; i < session.laps.size(); ++i) {
              if (session.laps[i].number == row.lap) {
                lap_index = i;
                break;
              }
            }
          }

          if (lap_index >= session.laps.size()) return;
          auto &lap = session.laps[lap_index];

          // GSA3 trace_count is uint16_t.
          if (lap.trace.size() >= 65535) return;

          if (!first_seen[lap_index]) {
            first_elapsed[lap_index] = row.elapsed_ms;
            first_seen[lap_index] = true;
            // Avoid repeated small reallocations without reserving the entire
            // possible 65535-point trace up front.
            lap.trace.reserve(4096);
          }

          const uint32_t rel_ms =
              row.elapsed_ms >= first_elapsed[lap_index]
                  ? row.elapsed_ms - first_elapsed[lap_index]
                  : 0;

          GoatsTracePoint point;
          point.latitude_e7 = static_cast<int32_t>(
              std::llround(row.latitude * 10000000.0));
          point.longitude_e7 = static_cast<int32_t>(
              std::llround(row.longitude * 10000000.0));
          point.elapsed_40ms = static_cast<uint16_t>(
              std::min<uint32_t>(rel_ms / TRACE_PERIOD_MS, 65535UL));
          point.speed_tenth_kmh = static_cast<uint16_t>(
              std::min<float>(
                  std::max<float>(row.speed_kmh, 0.0f) * 10.0f,
                  65535.0f));

          lap.trace.push_back(point);
          ++accepted;
        },
        65535);

    return read_ok && accepted > 0;
  }

  static void serialize_session_(std::vector<uint8_t> &d,
                                 const GoatsSessionRecord &s) {
    append_(d,s.session_id); append_string_(d,s.date);
    append_string_(d,s.time); append_string_(d,s.track_name);
    append_(d,s.duration_ms); append_(d,s.best_lap_ms);
    append_(d,s.last_lap_ms); append_(d,s.max_speed_kmh);
    append_(d,s.average_speed_kmh); append_(d,s.average_hdop);
    append_(d,s.average_satellites);
    append_u16_(d,static_cast<uint16_t>(s.laps.size()));
    for (const auto &lap : s.laps) {
      append_(d,lap.number); append_(d,lap.lap_time_ms);
      append_(d,lap.max_speed_kmh); append_(d,lap.average_speed_kmh);
      append_u16_(d, static_cast<uint16_t>(lap.trace.size()));
      for (const auto &point : lap.trace) {
        append_(d, point.latitude_e7);
        append_(d, point.longitude_e7);
        append_(d, point.elapsed_40ms);
        append_(d, point.speed_tenth_kmh);
      }
    }
  }

  template<typename T>
  static void append_(std::vector<uint8_t> &d, const T &v) {
    const uint8_t *p = reinterpret_cast<const uint8_t *>(&v);
    d.insert(d.end(), p, p + sizeof(T));
  }
  static void append_u16_(std::vector<uint8_t> &d, uint16_t v) { append_(d,v); }
  static void append_string_(std::vector<uint8_t> &d, const std::string &s) {
    const uint8_t n = static_cast<uint8_t>(std::min<size_t>(s.size(),255));
    d.push_back(n); d.insert(d.end(),s.begin(),s.begin()+n);
  }
  template<typename T>
  static bool read_(const std::vector<uint8_t> &d,size_t &o,T &v) {
    if (o+sizeof(T)>d.size()) return false;
    std::memcpy(&v,d.data()+o,sizeof(T)); o+=sizeof(T); return true;
  }
  static bool read_string_(const std::vector<uint8_t> &d,size_t &o,std::string &s) {
    if (o>=d.size()) return false;
    uint8_t n=d[o++]; if(o+n>d.size()) return false;
    s.assign(reinterpret_cast<const char*>(d.data()+o),n); o+=n; return true;
  }

  static std::string format_lap_(uint32_t ms) {
    if (!ms) return "--:--.---";
    char b[24];
    std::snprintf(b,sizeof(b),"%02lu:%02lu.%03lu",
      static_cast<unsigned long>(ms/60000),
      static_cast<unsigned long>((ms/1000)%60),
      static_cast<unsigned long>(ms%1000));
    return b;
  }
  static std::string format_duration_(uint32_t ms) {
    const uint32_t sec=ms/1000;
    char b[24];
    std::snprintf(b,sizeof(b),"%02lu:%02lu",
      static_cast<unsigned long>(sec/60),
      static_cast<unsigned long>(sec%60));
    return b;
  }
  static std::string format_float_(float v) {
    char b[20]; std::snprintf(b,sizeof(b),"%.1f",v); return b;
  }
};

static GoatsSessionManager GOATS_SESSIONS;

inline void goats_sessions_setup(){GOATS_SESSIONS.setup();}
inline void goats_sessions_reload_persistent(){GOATS_SESSIONS.reload_persistent();}
inline void goats_sessions_reset_runtime(){GOATS_SESSIONS.reset_runtime();}
inline void goats_sessions_update(bool r,uint32_t n,uint32_t last,uint32_t best,
 uint32_t finish,float speed,float hdop,int sats,uint32_t now,
 const char *track,const char *date,const char *time,double lat,double lon){
 GOATS_SESSIONS.update(r,n,last,best,finish,speed,hdop,sats,now,
                       track,date,time,lat,lon);
}
inline void goats_sessions_finish_manual(uint32_t n){GOATS_SESSIONS.finish_manual(n);}
inline void goats_sessions_discard_current(){GOATS_SESSIONS.discard_current();}
inline bool goats_sessions_prepare_free(uint32_t n,const char *date,const char *time){
 return GOATS_SESSIONS.prepare_free(n,date,time);}
inline bool goats_sessions_attach_free_storage(){
 return GOATS_SESSIONS.attach_free_storage();}
inline bool goats_sessions_start_free(uint32_t n,const char *date,const char *time){
 return GOATS_SESSIONS.start_free(n,date,time);}
inline bool goats_sessions_finish_free(uint32_t n){
 return GOATS_SESSIONS.finish_free(n);}
inline bool goats_sessions_last_save_ok(){
 return GOATS_SESSIONS.last_save_ok();}
inline bool goats_sessions_free_active(){return GOATS_SESSIONS.free_active();}
inline bool goats_sessions_free_storage_attached(){
 return GOATS_SESSIONS.free_storage_attached();}
inline uint32_t goats_sessions_free_elapsed_ms(uint32_t n){
 return GOATS_SESSIONS.free_elapsed_ms(n);}
inline size_t goats_sessions_free_trace_points(){
 return GOATS_SESSIONS.free_trace_points();}
inline float goats_sessions_current_max_speed(){
 return GOATS_SESSIONS.current_max_speed();}
inline bool goats_sessions_trace_storage_full(){
 return GOATS_SESSIONS.trace_storage_full();}
inline bool goats_sessions_active(){return GOATS_SESSIONS.active();}
inline uint32_t goats_sessions_stint_elapsed_ms(uint32_t n){
 return GOATS_SESSIONS.stint_elapsed_ms(n);}
inline bool goats_sessions_auto_finished(){return GOATS_SESSIONS.auto_finished();}
inline void goats_sessions_clear_auto_finished(){GOATS_SESSIONS.clear_auto_finished();}
inline bool goats_sessions_summary_visible_request(){return GOATS_SESSIONS.summary_visible_request();}
inline void goats_sessions_clear_summary_visible_request(){GOATS_SESSIONS.clear_summary_visible_request();}
inline std::string goats_sessions_summary_laps(){return GOATS_SESSIONS.summary_laps();}
inline std::string goats_sessions_summary_best(){return GOATS_SESSIONS.summary_best();}
inline std::string goats_sessions_summary_last(){return GOATS_SESSIONS.summary_last();}
inline std::string goats_sessions_summary_duration(){return GOATS_SESSIONS.summary_duration();}
inline std::string goats_sessions_summary_vmax(){return GOATS_SESSIONS.summary_vmax();}
inline size_t goats_sessions_count(){return GOATS_SESSIONS.count();}
inline bool goats_sessions_delete_display(size_t i){return GOATS_SESSIONS.delete_display_session(i);}
inline bool goats_sessions_clear_archive(){return GOATS_SESSIONS.clear_archive();}
inline std::vector<uint8_t> goats_sessions_export_blob(){return GOATS_SESSIONS.export_blob();}
inline std::string goats_sessions_list_date(size_t i){return GOATS_SESSIONS.list_date(i);}
inline std::string goats_sessions_list_time(size_t i){return GOATS_SESSIONS.list_time(i);}
inline std::string goats_sessions_list_track(size_t i){return GOATS_SESSIONS.list_track(i);}
inline std::string goats_sessions_detail_header(size_t i){return GOATS_SESSIONS.detail_header(i);}
inline std::string goats_sessions_detail_laps(size_t i){return GOATS_SESSIONS.detail_laps(i);}
inline std::string goats_sessions_detail_laps_number(size_t i){return GOATS_SESSIONS.detail_laps_number(i);}
inline std::string goats_sessions_detail_laps_time(size_t i){return GOATS_SESSIONS.detail_laps_time(i);}
inline std::string goats_sessions_detail_laps_vmax(size_t i){return GOATS_SESSIONS.detail_laps_vmax(i);}
inline std::string goats_sessions_detail_laps_vavg(size_t i){return GOATS_SESSIONS.detail_laps_vavg(i);}
inline std::string goats_sessions_detail_laps_best(size_t i){return GOATS_SESSIONS.detail_laps_best(i);}
inline std::string goats_sessions_detail_lap_count(size_t i){return GOATS_SESSIONS.detail_lap_count(i);}
inline std::string goats_sessions_detail_duration(size_t i){return GOATS_SESSIONS.detail_duration(i);}
inline std::string goats_sessions_detail_best(size_t i){return GOATS_SESSIONS.detail_best(i);}
inline std::string goats_sessions_detail_vmax(size_t i){return GOATS_SESSIONS.detail_vmax(i);}
inline std::string goats_sessions_detail_vavg(size_t i){return GOATS_SESSIONS.detail_vavg(i);}
