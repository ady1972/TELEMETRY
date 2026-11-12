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
#include "goats_port_types.h"
#include "goats_lap_journal.h"

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
  std::vector<uint32_t> sectors_ms;
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
    goats_lap_journal::setup();
    load_archive_();
    recover_checkpoint_();
    merge_journal_();
    load_sector_files_();
    reset_runtime();
  }

  // V11.0.2.30: SD is initialized post-boot, after the normal session setup.
  // Reload only persistent data when the SD becomes ready, without resetting
  // an already running session state.
  void reload_persistent() {
    if (!goats_sd_storage::ready() || active()) return;
    load_archive_();
    recover_checkpoint_();
    merge_journal_();
    load_sector_files_();
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
    trace_queue_.clear();
    journal_queue_.clear();
    epoch_.reset();
    pending_open_ = false;
    storage_failed_ = false;
    trace_dropped_ = 0;
    journal_dropped_ = 0;
    journal_saved_ = 0;
    journal_failed_ = false;
    journal_retry_at_ = 0;
    current_track_name_.clear();
    current_date_.clear();
    current_time_.clear();
  }

  // Called exactly once per distinct NAV-PVT. RAM work only: no FatFS/NVS.
  void update(bool laptimer_running, uint32_t lap_number,
              uint32_t last_lap_ms, uint32_t best_lap_ms, uint32_t last_finish_ms,
              float speed_kmh, float hdop, int satellites, uint32_t now_ms,
              const char *track_name, const char *date_text, const char *time_text,
              double latitude, double longitude, bool gps_valid, uint32_t itow) {
    (void)last_finish_ms;
    if (finished_) return;
    if (laptimer_running && !active_ && !free_mode_) {
      active_=true;
      goats_diag_v1021::session_begin();
      start_ms_=now_ms;
      last_seen_lap_number_=lap_number;
      current_track_name_=safe_text_(track_name,"Circuito");
      current_date_=safe_text_(date_text,"--/--/----");
      current_time_=safe_text_(time_text,"--:--");
      checkpoint_session_id_=next_session_id_();
      goats_lap_journal::max_session=checkpoint_session_id_;
      lap_trace_start_ms_=now_ms;
      pending_open_=true;
      epoch_.reset();
    }
    if (!active_) return;
    if (!free_mode_ && lap_number!=last_seen_lap_number_) {
      last_seen_lap_number_=lap_number;
      if(last_lap_ms) {
        GoatsLapRecord lap;
        lap.number=static_cast<uint16_t>(lap_number-1);
        lap.lap_time_ms=last_lap_ms;
        lap.max_speed_kmh=lap_max_speed_kmh_;
        lap.average_speed_kmh=lap_speed_samples_ ? static_cast<float>(lap_speed_sum_/lap_speed_samples_):0;
        lap.trace=std::move(current_trace_);
        for(size_t i=0;i<goats_laptimer_last_timing_sector_count() && i<13;++i)
          lap.sectors_ms.push_back(goats_laptimer_last_timing_sector_ms(i));
        if(current_laps_.size()>=MAX_LAPS_PER_SESSION) current_laps_.erase(current_laps_.begin());
        current_laps_.push_back(std::move(lap));
        last_lap_ms_=last_lap_ms;best_lap_ms_=best_lap_ms;
        enqueue_journal_(current_laps_.back(),now_ms);
      }
      lap_max_speed_kmh_=0;lap_speed_sum_=0;lap_speed_samples_=0;
      current_trace_.clear();lap_trace_start_ms_=now_ms;last_trace_sample_ms_=0;
    }
    if(!gps_valid || !std::isfinite(latitude) || !std::isfinite(longitude) ||
        std::fabs(latitude)>90 || std::fabs(longitude)>180 ||
        (latitude==0 && longitude==0) || !epoch_.observe(itow))return;
    TracePoint point{epoch_.elapsed(),free_mode_?0:lap_number,
        latitude,longitude,speed_kmh,hdop,satellites};
    if(storage_failed_ || !trace_queue_.push(point))++trace_dropped_;
    // Keep the legacy RAM trace compact; the CSV queue has no 40 ms decimator.
    if(current_trace_.size()<MAX_TRACE_POINTS_PER_LAP &&
        stored_trace_points_()+current_trace_.size()<MAX_TRACE_POINTS_PER_SESSION) {
      GoatsTracePoint t;
      t.latitude_e7=static_cast<int32_t>(std::llround(latitude*10000000));
      t.longitude_e7=static_cast<int32_t>(std::llround(longitude*10000000));
      t.elapsed_40ms=static_cast<uint16_t>(std::min<uint32_t>((now_ms-lap_trace_start_ms_)/40,65535));
      t.speed_tenth_kmh=static_cast<uint16_t>(std::min<float>(std::max<float>(speed_kmh,0)*10,65535));
      current_trace_.push_back(t);
    }
    if(std::isfinite(speed_kmh) && speed_kmh>=0) {
      session_max_speed_kmh_=std::max(session_max_speed_kmh_,speed_kmh);
      session_speed_sum_+=speed_kmh;++session_speed_samples_;
      lap_max_speed_kmh_=std::max(lap_max_speed_kmh_,speed_kmh);
      lap_speed_sum_+=speed_kmh;++lap_speed_samples_;
    }
    if(std::isfinite(hdop) && hdop>0 && hdop<50) {
      hdop_sum_+=hdop;sat_sum_+=std::max(0,satellites);++quality_samples_;
    }
  }

  // RLCD-style bounded I/O slices on the application task, outside acquisition.
  // Individual FatFS/NVS calls can still block: this is not a real-time worker.
  void storage_tick() {
    if(pending_open_) {
      pending_open_=false;
      storage_failed_=!goats_sd_storage::begin_live_session(
          free_mode_?"LIBERA":"CIRCUITO",current_date_.c_str(),current_time_.c_str(),current_track_name_.c_str());
      free_storage_attached_=free_mode_ && !storage_failed_;
      if(storage_failed_){trace_dropped_+=trace_queue_.size();trace_queue_.clear();}
    }
    flush_trace_(8);
    if(const auto *r=journal_queue_.front(); r && static_cast<int32_t>(millis()-journal_retry_at_)>=0) {
      if(goats_lap_journal::save(*r)) {
        goats_lap_journal::Record used;journal_queue_.pop(used);++journal_saved_;
      } else {journal_failed_=true;journal_retry_at_=millis()+1000U;}
    }
  }
  void check_timeout(uint32_t now_ms) {
    if(active() && !free_mode_ && goats_laptimer_last_finish_ms()>0 &&
        uint32_t(now_ms-goats_laptimer_last_finish_ms())>=600000U) {
      goats_laptimer_reset();finish_(now_ms,true);
    }
  }
  uint64_t trace_dropped()const{return trace_dropped_;}
  bool accepts_samples()const{return !finished_;}

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
    goats_lap_journal::max_session=checkpoint_session_id_;
    epoch_.reset();
    last_sd_trace_sample_ms_ = 0;
    return true;
  }

  bool attach_free_storage() {
    if(!free_mode_ || !active_ || finished_)return false;
    pending_open_=true;return true; // Actual FatFS open belongs to storage_tick().
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
    enqueue_journal_(current_laps_.back(),now_ms);

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
    goats_laptimer_reset();
    pending_open_=false;trace_queue_.clear();journal_queue_.clear();
    if(checkpoint_session_id_!=0)(void)goats_lap_journal::erase_session(checkpoint_session_id_);
    goats_sd_storage::discard_live_session();
    goats_sd_storage::remove_checkpoint();
    reset_runtime();
    finished_=true;
  }

  void finish_manual(uint32_t now_ms) {
    if (!active_ || finished_) return;
    goats_laptimer_reset();
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
    if(active() || goats_laptimer_running())return false;
    if (display_index >= archive_.size()) return false;
    const size_t real_index = archive_.size() - 1 - display_index;
    const uint32_t session_id = archive_[real_index].session_id;
    if(!goats_lap_journal::erase_session(session_id))return false;
    goats_sd_storage::remove_sector_file(session_id);
    archive_.erase(archive_.begin() + real_index);
    goats_sd_storage::remove_trace(session_id);
    goats_sd_storage::remove_session_meta(session_id);
    return !goats_sd_storage::ready() || save_archive_();
  }

  bool clear_archive() {
    if(active() || goats_laptimer_running())return false;
    if(!goats_lap_journal::erase_session(0))return false;
    for(const auto &item:archive_)goats_sd_storage::remove_sector_file(item.session_id);
    archive_.clear();
    goats_sd_storage::clear_session_files();
    return !goats_sd_storage::ready() || goats_sd_storage::remove_archive();
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
      out.append(lap.sectors_ms.size(),'\n');
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
      for(size_t j=0;j<lap.sectors_ms.size();++j)
        out += "S"+std::to_string(j+1)+" "+format_lap_(lap.sectors_ms[j])+"\n";
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
      out.append(lap.sectors_ms.size(),'\n');
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
      out.append(lap.sectors_ms.size(),'\n');
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
      out.append(lap.sectors_ms.size(),'\n');
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

  struct TracePoint { uint32_t elapsed,lap;double lat,lon;float speed,hdop;int sats; };
  goats_port::Ring<TracePoint,512> trace_queue_;
  goats_port::Ring<goats_lap_journal::Record,80> journal_queue_;
  goats_port::EpochClock epoch_;
  bool pending_open_{false},storage_failed_{false},journal_failed_{false};
  uint32_t journal_retry_at_{0};
  uint64_t trace_dropped_{0},journal_dropped_{0};
  size_t journal_saved_{0};
  bool sector_save_ok_{true};

  void flush_trace_(unsigned budget) {
    while(budget-- && !trace_queue_.empty() && goats_sd_storage::live_open()) {
      const auto *p=trace_queue_.front();
      const size_t before=goats_sd_storage::live_points();
      goats_sd_storage::append_live_point(p->elapsed,p->lap,p->lat,p->lon,p->speed,p->hdop,p->sats);
      if(goats_sd_storage::live_points()==before || !goats_sd_storage::live_open()) {
        storage_failed_=true;trace_dropped_+=trace_queue_.size();trace_queue_.clear();return;
      }
      TracePoint used;trace_queue_.pop(used);
    }
  }
  void enqueue_journal_(const GoatsLapRecord &lap,uint32_t now_ms) {
    if(!lap.lap_time_ms)return;
    goats_lap_journal::Record r{};
    r.session=checkpoint_session_id_;r.duration=now_ms-start_ms_;r.number=lap.number;
    r.lap_ms=lap.lap_time_ms;r.best_ms=best_lap_ms_;
    r.max_speed=lap.max_speed_kmh;r.average_speed=lap.average_speed_kmh;
    r.sector_count=static_cast<uint8_t>(std::min<size_t>(13,lap.sectors_ms.size()));
    for(size_t i=0;i<r.sector_count;++i)r.sectors[i]=lap.sectors_ms[i];
    std::snprintf(r.date,sizeof(r.date),"%s",current_date_.c_str());
    std::snprintf(r.time,sizeof(r.time),"%s",current_time_.c_str());
    std::snprintf(r.track,sizeof(r.track),"%s",current_track_name_.c_str());
    if(!journal_queue_.push(r))++journal_dropped_;
  }
  bool write_sectors_(const GoatsSessionRecord &item) {
    std::vector<goats_port::SectorLap> laps;
    for(const auto &lap:item.laps)laps.push_back({lap.number,lap.lap_time_ms,lap.sectors_ms});
    return goats_sd_storage::write_sector_file(item.session_id,goats_port::encode_sectors(item.session_id,laps));
  }
  void load_sector_files_() {
    for(auto &item:archive_) {
      std::vector<uint8_t> data;std::vector<goats_port::SectorLap> laps;
      if(!goats_sd_storage::read_sector_file(item.session_id,data) ||
          !goats_port::decode_sectors(data,item.session_id,laps))continue;
      for(auto &lap:item.laps)for(const auto &saved:laps)
        if(lap.number==saved.number && lap.lap_time_ms==saved.lap_ms)lap.sectors_ms=saved.sectors;
    }
  }
  void merge_journal_() {
    std::vector<const goats_lap_journal::Record*> records;
    for(const auto &r:goats_lap_journal::cache)if(goats_lap_journal::valid(r))records.push_back(&r);
    std::sort(records.begin(),records.end(),[](const auto*a,const auto*b){return a->sequence<b->sequence;});
    for(const auto *r:records) {
      auto it=std::find_if(archive_.begin(),archive_.end(),[r](const auto &item){return item.session_id==r->session;});
      if(it==archive_.end()) { GoatsSessionRecord item;item.session_id=r->session;archive_.push_back(item);it=archive_.end()-1; }
      auto &item=*it;
      // Never overwrite a different legacy session that happens to reuse an ID
      // (for example a card moved from another device).
      if((!item.date.empty() && item.date.substr(0,15)!=r->date) ||
         (!item.time.empty() && item.time.substr(0,11)!=r->time) ||
         (!item.track_name.empty() && item.track_name.substr(0,63)!=r->track))continue;
      auto lap=std::find_if(item.laps.begin(),item.laps.end(),[r](const auto&l){return l.number==r->number;});
      if(lap!=item.laps.end() && lap->lap_time_ms!=r->lap_ms)continue;
      if(item.date.empty())item.date=r->date;
      if(item.time.empty())item.time=r->time;
      if(item.track_name.empty())item.track_name=r->track;
      item.duration_ms=std::max(item.duration_ms,r->duration);
      item.best_lap_ms=item.best_lap_ms?std::min(item.best_lap_ms,r->best_ms):r->best_ms;
      item.max_speed_kmh=std::max(item.max_speed_kmh,r->max_speed);
      if(lap==item.laps.end()){item.laps.emplace_back();lap=item.laps.end()-1;}
      lap->number=r->number;lap->lap_time_ms=r->lap_ms;lap->max_speed_kmh=r->max_speed;
      lap->average_speed_kmh=r->average_speed;lap->sectors_ms.assign(r->sectors,r->sectors+r->sector_count);
      uint16_t newest=0;for(const auto &l:item.laps)newest=std::max(newest,l.number);
      if(r->number>=newest)item.last_lap_ms=r->lap_ms;
    }
    for(auto &item:archive_) {
      std::sort(item.laps.begin(),item.laps.end(),[](const auto&a,const auto&b){return a.number<b.number;});
      if(item.laps.size()>MAX_LAPS_PER_SESSION)item.laps.erase(item.laps.begin(),item.laps.end()-MAX_LAPS_PER_SESSION);
      if(item.average_speed_kmh==0 && !item.laps.empty()) {double sum=0;for(const auto &l:item.laps)sum+=l.average_speed_kmh;item.average_speed_kmh=sum/item.laps.size();}
    }
    std::sort(archive_.begin(),archive_.end(),[](const auto&a,const auto&b){return a.session_id<b.session_id;});
    if(archive_.size()>MAX_SESSIONS)archive_.erase(archive_.begin(),archive_.end()-MAX_SESSIONS);
  }

  size_t stored_trace_points_() const {
    size_t total = 0;
    for (const auto &lap : current_laps_)
      total += lap.trace.size();
    return total;
  }

  static std::string safe_text_(const char *value, const char *fallback) {
    if (value == nullptr || value[0] == 0) return fallback;
    return std::string(value);
  }

  void finish_(uint32_t now_ms, bool automatic) {
    storage_tick();
    while(!trace_queue_.empty() && goats_sd_storage::live_open())flush_trace_(64);
    while(!journal_queue_.empty()) {
      const size_t before=journal_queue_.size();storage_tick();
      if(journal_queue_.size()==before)break;
    }
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
      trace_ok = goats_sd_storage::live_open() &&
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
    pending_open_=false;
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
    sector_save_ok_=write_sectors_(archive_.back());

    // A session is considered saved when at least one persistent index
    // succeeded. On the next boot load_archive_() merges the redundant
    // per-session metadata back into the global list.
    // Keep the RAM archive even when SD is absent. The last 80 journaled laps
    // are recoverable from NVS without changing GSA3/Manager wire encoding.
    return ((meta_ok || archive_ok) && sector_save_ok_) ||
        (journal_saved_>0 && journal_queue_.empty() && journal_dropped_==0);

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
    uint32_t max_id = goats_lap_journal::max_session;
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
                       track,date,time,lat,lon,false,0);
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

inline void goats_sessions_storage_tick(){GOATS_SESSIONS.storage_tick();}
inline void goats_sessions_check_timeout(uint32_t now){GOATS_SESSIONS.check_timeout(now);}
