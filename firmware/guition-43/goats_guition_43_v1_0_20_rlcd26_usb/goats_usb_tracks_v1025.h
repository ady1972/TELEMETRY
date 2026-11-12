#pragma once
#include "goats_usb_activity_v11.h"
#include "goats_sd_storage.h"

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>
#include "driver/usb_serial_jtag.h"
#include "esp_heap_caps.h"
#include "nvs.h"
#include "nvs_flash.h"
#include "esp_err.h"

// Funzioni archivio sessioni, definite in goats_sessions.h.
std::vector<uint8_t> goats_sessions_export_blob();
bool goats_sessions_delete_display(size_t index);
bool goats_sessions_clear_archive();
size_t goats_sessions_count();

// Defined later by goats_usb_sd_msc.h in the same generated translation unit.
namespace goats_usb_sd_msc {
static inline bool start();
}


struct GoatsSectorUsb {
  std::string name;
  double lat1{};
  double lon1{};
  double lat2{};
  double lon2{};
};

struct GoatsTrackUsb {
  std::string name;
  double start_lat{};
  double start_lon{};
  double finish_lat{};
  double finish_lon{};
  float trigger_radius_m{20.0f};
  uint8_t direction{0};
  std::vector<GoatsSectorUsb> sectors;
};

class GoatsUsbTrackStore {
 public:
  void setup() {
    load_from_nvs_();
    usb_serial_jtag_driver_config_t cfg{};
    cfg.rx_buffer_size = 8192;
    cfg.tx_buffer_size = 1024;
    esp_err_t err = usb_serial_jtag_driver_install(&cfg);
    usb_ready_ = (err == ESP_OK || err == ESP_ERR_INVALID_STATE);
    last_usb_activity_ms_ = millis(); goats_usb_activity_v11::mark(last_usb_activity_ms_);
  }

  void loop() {
    if (!usb_ready_) return;

    uint8_t buffer[256];
    int count = usb_serial_jtag_read_bytes(buffer, sizeof(buffer), 0);
    if (count > 0) last_usb_activity_ms_ = millis(); goats_usb_activity_v11::mark(last_usb_activity_ms_);
    for (int i = 0; i < count; i++) consume_byte_(buffer[i]);

    service_session_transfer_();
  }

  uint32_t last_usb_activity_ms() const {
    return last_usb_activity_ms_;
  }

  void suspend_for_msc() {
    usb_ready_ = false;
    session_tx_state_ = SessionTxState::IDLE;
    session_tx_payload_.clear();
    command_.clear();
    (void) usb_serial_jtag_driver_uninstall();
  }

  size_t count() const { return tracks_.size(); }
  uint32_t revision() const { return revision_; }

  const GoatsTrackUsb *track(size_t index) const {
    if (index >= tracks_.size()) return nullptr;
    return &tracks_[index];
  }

  bool delete_track(size_t index) {
    if (index >= tracks_.size()) return false;
    tracks_.erase(tracks_.begin() + index);
    std::vector<uint8_t> serialized;
    if (!serialize_catalog_(tracks_, serialized) || !save_to_nvs_(serialized)) return false;
    revision_++;
    return true;
  }

  bool clear_tracks() {
    tracks_.clear();
    std::vector<uint8_t> serialized;
    if (!serialize_catalog_(tracks_, serialized) || !save_to_nvs_(serialized)) return false;
    revision_++;
    return true;
  }

 public:
  bool take_assistnow_apply_request() {
    if (!assistnow_apply_requested_) return false;
    assistnow_apply_requested_ = false;
    return true;
  }

  void send_assistnow_apply_result(uint32_t accepted, uint32_t retries,
                                   uint32_t rejected, uint32_t timeouts,
                                   uint32_t malformed) {
    char line[128];
    std::snprintf(line, sizeof(line),
                  "GANO_APPLY_OK %lu %lu %lu %lu %lu",
                  (unsigned long)accepted, (unsigned long)retries,
                  (unsigned long)rejected, (unsigned long)timeouts,
                  (unsigned long)malformed);
    write_line_(line);
  }

  void send_assistnow_apply_error(const char *reason) {
    char line[80];
    std::snprintf(line, sizeof(line), "GANO_APPLY_ERR %s", reason ? reason : "UNKNOWN");
    write_line_(line);
  }

  bool take_identity_request() {
    if (!identity_requested_) return false;
    identity_requested_ = false;
    return true;
  }
  void send_identity_result(const std::string &s) {
    if (identity_response_mode_ == IdentityResponseMode::GGID) {
      if (s.empty()) {
        write_line_("GGID_ERR IDENTITY");
        return;
      }
      const size_t sep = s.find(' ');
      if (sep == std::string::npos || sep == 0 || sep + 1 >= s.size()) {
        write_line_("GGID_ERR FORMAT");
        return;
      }
      const std::string uniq = s.substr(0, sep);
      const std::string monver = s.substr(sep + 1);
      write_line_("GGID_BEGIN");
      const std::string l1 = std::string("GGID_UNIQID ") + uniq;
      write_line_(l1.c_str());
      const std::string l2 = std::string("GGID_MONVER ") + monver;
      write_line_(l2.c_str());
      write_line_("GGID_END");
      return;
    }

    if (s.empty()) {
      write_line_("GANO_ERR IDENTITY");
    } else {
      const std::string line = std::string("GANO_IDENTITY ") + s;
      write_line_(line.c_str());
    }
  }

 private:
  enum class IdentityResponseMode { GANO, GGID };
  enum class State { COMMAND, PAYLOAD };
  enum class PayloadKind { TRACKS, ASSISTNOW };

  enum class SessionTxState {
    IDLE,
    WAIT_READY,
    READY_TO_SEND,
    WAIT_ACK
  };

  State state_{State::COMMAND};
  PayloadKind payload_kind_{PayloadKind::TRACKS};
  bool usb_ready_{false};
  uint32_t last_usb_activity_ms_{0};

  SessionTxState session_tx_state_{SessionTxState::IDLE};
  std::vector<uint8_t> session_tx_payload_;
  size_t session_tx_offset_{0};
  uint32_t session_tx_index_{0};
  uint32_t session_tx_total_crc_{0};
  uint32_t session_tx_last_action_ms_{0};
  uint8_t session_tx_retries_{0};

  static constexpr size_t SESSION_CHUNK_SIZE = 512;
  static constexpr uint32_t SESSION_ACK_TIMEOUT_MS = 2000;
  static constexpr uint8_t SESSION_MAX_RETRIES = 5;
  std::string command_;
  bool identity_requested_{false};
  bool assistnow_apply_requested_{false};
  IdentityResponseMode identity_response_mode_{IdentityResponseMode::GANO};
  std::vector<uint8_t> incoming_;
  uint8_t *assist_buffer_{nullptr};
  size_t assist_received_{0};
  size_t assist_chunk_remaining_{0};
  uint32_t assist_crc_state_{0xFFFFFFFFu};
  uint8_t assist_first_[2]{0,0};
  size_t expected_size_{0};
  uint32_t expected_crc_{0};
  std::vector<GoatsTrackUsb> tracks_;
  uint32_t revision_{0};

  static uint32_t crc32_(const uint8_t *data, size_t length) {
    uint32_t crc = 0xFFFFFFFFu;
    for (size_t i = 0; i < length; i++) {
      crc ^= data[i];
      for (int bit = 0; bit < 8; bit++)
        crc = (crc >> 1) ^ (0xEDB88320u & (0u - (crc & 1u)));
    }
    return crc ^ 0xFFFFFFFFu;
  }

  void write_line_(const char *text) {
    usb_serial_jtag_write_bytes(text, std::strlen(text), 100 / portTICK_PERIOD_MS);
    usb_serial_jtag_write_bytes("\n", 1, 100 / portTICK_PERIOD_MS);
    last_usb_activity_ms_ = millis(); goats_usb_activity_v11::mark(last_usb_activity_ms_);
  }

  bool write_binary_all_(const uint8_t *data, size_t length,
                         uint32_t timeout_ms = 3000) {
    const uint32_t started = millis();
    size_t offset = 0;

    while (offset < length &&
           static_cast<uint32_t>(millis() - started) < timeout_ms) {
      const int written = usb_serial_jtag_write_bytes(
          data + offset,
          length - offset,
          250 / portTICK_PERIOD_MS);

      if (written > 0) {
        offset += static_cast<size_t>(written);
        last_usb_activity_ms_ = millis(); goats_usb_activity_v11::mark(last_usb_activity_ms_);
      } else {
        vTaskDelay(5 / portTICK_PERIOD_MS);
      }

      taskYIELD();
    }

    return offset == length;
  }

  void reset_session_transfer_() {
    session_tx_state_ = SessionTxState::IDLE;
    session_tx_payload_.clear();
    session_tx_offset_ = 0;
    session_tx_index_ = 0;
    session_tx_total_crc_ = 0;
    session_tx_last_action_ms_ = 0;
    session_tx_retries_ = 0;
  }

  void fail_session_transfer_(const char *reason) {
    char line[64];
    std::snprintf(line, sizeof(line), "GSES2_ERR %s", reason);
    write_line_(line);
    reset_session_transfer_();
  }

  void send_current_session_chunk_() {
    if (session_tx_state_ != SessionTxState::READY_TO_SEND) return;

    if (session_tx_offset_ >= session_tx_payload_.size()) {
      write_line_("GSES2_END");
      reset_session_transfer_();
      return;
    }

    const size_t chunk_size = std::min<size_t>(
        SESSION_CHUNK_SIZE,
        session_tx_payload_.size() - session_tx_offset_);

    const uint8_t *chunk =
        session_tx_payload_.data() + session_tx_offset_;
    const uint32_t chunk_crc = crc32_(chunk, chunk_size);

    char header_line[96];
    std::snprintf(
        header_line,
        sizeof(header_line),
        "GSES2_CHUNK %lu %u %08lX",
        static_cast<unsigned long>(session_tx_index_),
        static_cast<unsigned>(chunk_size),
        static_cast<unsigned long>(chunk_crc));

    write_line_(header_line);
    vTaskDelay(15 / portTICK_PERIOD_MS);

    if (!write_binary_all_(chunk, chunk_size)) {
      fail_session_transfer_("WRITE");
      return;
    }

    session_tx_state_ = SessionTxState::WAIT_ACK;
    session_tx_last_action_ms_ = millis();
  }

  void service_session_transfer_() {
    if (session_tx_state_ == SessionTxState::READY_TO_SEND) {
      send_current_session_chunk_();
      return;
    }

    if (session_tx_state_ != SessionTxState::WAIT_ACK) return;

    if (static_cast<uint32_t>(
            millis() - session_tx_last_action_ms_) <
        SESSION_ACK_TIMEOUT_MS) {
      return;
    }

    if (++session_tx_retries_ > SESSION_MAX_RETRIES) {
      fail_session_transfer_("ACK_TIMEOUT");
      return;
    }

    // Ritrasmette lo stesso pacchetto.
    session_tx_state_ = SessionTxState::READY_TO_SEND;
  }

  bool stream_session_trace_(uint32_t session_id) {
    if (session_id == 0) {
      write_line_("GSDT_ERR BAD_ID");
      return false;
    }

    // V11.0.2.40 lightweight SD recovery:
    // Do not unmount/remount SDSPI at runtime. Probe the existing FatFS mount
    // and only continue if the GOATS directory is directly accessible.
    if (!goats_sd_storage::ready() &&
        !goats_sd_storage::ensure_ready_for_usb_read(3)) {
      char err[128];
      std::snprintf(
          err, sizeof(err),
          "GSDT_ERR NOT_READY FAT=%d STAGE=%s",
          goats_sd_storage::last_fresult(),
          goats_sd_storage::last_stage());
      write_line_(err);
      return false;
    }

    char fat_name[160];
    if (!goats_sd_storage::resolve_trace_path(
            session_id, fat_name, sizeof(fat_name))) {
      write_line_("GSDT_ERR NO_FILE");
      return false;
    }

    FIL file{};
    FRESULT fr = f_open(&file, fat_name, FA_READ);

    // If the cached state was stale, perform only a lightweight FatFS probe
    // and retry the open once; never rebuild the SPI/VFS stack here.
    if (fr == FR_NOT_READY || fr == FR_INVALID_OBJECT ||
        fr == FR_NOT_ENABLED) {
      if (goats_sd_storage::ensure_ready_for_usb_read(2)) {
        fr = f_open(&file, fat_name, FA_READ);
      }
    }

    if (fr != FR_OK) {
      char err[128];
      std::snprintf(
          err, sizeof(err),
          "GSDT_ERR OPEN %d %s",
          static_cast<int>(fr),
          goats_sd_storage::fresult_name_(static_cast<int>(fr)));
      write_line_(err);
      return false;
    }

    const uint32_t size = static_cast<uint32_t>(f_size(&file));
    char header[96];
    std::snprintf(
        header, sizeof(header),
        "GSDT_BEGIN %lu %lu",
        static_cast<unsigned long>(size),
        static_cast<unsigned long>(session_id));
    write_line_(header);
    vTaskDelay(30 / portTICK_PERIOD_MS);

    uint8_t buffer[512];
    uint32_t sent = 0;
    bool ok = true;
    while (sent < size) {
      UINT got = 0;
      const UINT want = static_cast<UINT>(
          std::min<uint32_t>(sizeof(buffer), size - sent));
      fr = f_read(&file, buffer, want, &got);
      if (fr != FR_OK || got == 0 ||
          !write_binary_all_(buffer, got, 5000)) {
        ok = false;
        break;
      }
      sent += static_cast<uint32_t>(got);
      vTaskDelay(1 / portTICK_PERIOD_MS);
    }
    (void) f_close(&file);

    if (!ok || sent != size) {
      write_line_("GSDT_ERR READ");
      return false;
    }
    write_line_("GSDT_END");
    return true;
  }

  bool stream_sd_file_(const char *name) {
    uint32_t size = 0;
    FILE *f = goats_sd_storage::open_read_file(name, size);
    if (!f) {
      write_line_("GSD_ERR OPEN");
      return false;
    }

    char header[128];
    std::snprintf(header, sizeof(header), "GSD_BEGIN %lu %s",
                  static_cast<unsigned long>(size), name);
    write_line_(header);
    vTaskDelay(25 / portTICK_PERIOD_MS);

    uint8_t buffer[512];
    uint32_t sent = 0;
    bool ok = true;
    while (sent < size) {
      const size_t want = std::min<size_t>(sizeof(buffer), size - sent);
      const size_t got = std::fread(buffer, 1, want, f);
      if (got == 0 || !write_binary_all_(buffer, got, 5000)) {
        ok = false;
        break;
      }
      sent += static_cast<uint32_t>(got);
      taskYIELD();
    }
    std::fclose(f);
    if (!ok || sent != size) {
      write_line_("GSD_ERR READ");
      return false;
    }
    write_line_("GSD_END");
    return true;
  }

  void consume_byte_(uint8_t value) {
    if (state_ == State::COMMAND) {
      if (value == '\r') return;
      if (value != '\n') {
        if (command_.size() < 128) command_.push_back(static_cast<char>(value));
        return;
      }

      if (command_ == "GTRK_CLEAR") {
        if (clear_tracks()) write_line_("GTRK_CLEAR_OK");
        else write_line_("GTRK_ERR STORAGE");
        command_.clear();
        return;
      }

      if (command_ == "GTRK_GET") {
        std::vector<uint8_t> payload;
        if (!serialize_catalog_(tracks_, payload)) {
          write_line_("GTRK_ERR FORMAT");
          command_.clear();
          return;
        }

        const uint32_t crc = crc32_(payload.data(), payload.size());
        char header[64];
        std::snprintf(
            header, sizeof(header),
            "GTRK_DATA %u %08lX",
            static_cast<unsigned>(payload.size()),
            static_cast<unsigned long>(crc));
        write_line_(header);

        if (!payload.empty() &&
            !write_binary_all_(payload.data(), payload.size(), 5000)) {
          write_line_("GTRK_ERR TX");
          command_.clear();
          return;
        }

        write_line_("GTRK_END");
        command_.clear();
        return;
      }

      if (command_ == "GSES2_GET") {
        if (session_tx_state_ != SessionTxState::IDLE) {
          write_line_("GSES2_ERR BUSY");
          command_.clear();
          return;
        }

        session_tx_payload_ = goats_sessions_export_blob();
        session_tx_offset_ = 0;
        session_tx_index_ = 0;
        session_tx_retries_ = 0;
        session_tx_total_crc_ = crc32_(
            session_tx_payload_.data(),
            session_tx_payload_.size());

        const size_t chunk_count =
            (session_tx_payload_.size() + SESSION_CHUNK_SIZE - 1) /
            SESSION_CHUNK_SIZE;

        char line[96];
        std::snprintf(
            line,
            sizeof(line),
            "GSES2_BEGIN %u %08lX %u %u",
            static_cast<unsigned>(session_tx_payload_.size()),
            static_cast<unsigned long>(session_tx_total_crc_),
            static_cast<unsigned>(SESSION_CHUNK_SIZE),
            static_cast<unsigned>(chunk_count));

        write_line_(line);
        session_tx_state_ = SessionTxState::WAIT_READY;
        session_tx_last_action_ms_ = millis();
        command_.clear();
        return;
      }

      if (command_ == "GSES2_READY") {
        if (session_tx_state_ == SessionTxState::WAIT_READY) {
          session_tx_state_ = SessionTxState::READY_TO_SEND;
          session_tx_last_action_ms_ = millis();
        } else {
          write_line_("GSES2_ERR STATE");
        }
        command_.clear();
        return;
      }

      unsigned long ack_index = 0;
      if (std::sscanf(
              command_.c_str(),
              "GSES2_ACK %lu",
              &ack_index) == 1) {
        if (session_tx_state_ != SessionTxState::WAIT_ACK ||
            ack_index != session_tx_index_) {
          write_line_("GSES2_ERR ACK");
          command_.clear();
          return;
        }

        const size_t chunk_size = std::min<size_t>(
            SESSION_CHUNK_SIZE,
            session_tx_payload_.size() - session_tx_offset_);

        session_tx_offset_ += chunk_size;
        session_tx_index_++;
        session_tx_retries_ = 0;
        session_tx_state_ = SessionTxState::READY_TO_SEND;
        session_tx_last_action_ms_ = millis();
        command_.clear();
        return;
      }

      unsigned long nack_index = 0;
      if (std::sscanf(
              command_.c_str(),
              "GSES2_NACK %lu",
              &nack_index) == 1) {
        if (session_tx_state_ == SessionTxState::WAIT_ACK &&
            nack_index == session_tx_index_) {
          if (++session_tx_retries_ > SESSION_MAX_RETRIES) {
            fail_session_transfer_("CRC_RETRY");
          } else {
            session_tx_state_ = SessionTxState::READY_TO_SEND;
          }
        } else {
          write_line_("GSES2_ERR NACK");
        }
        command_.clear();
        return;
      }

      if (command_ == "GSES2_CANCEL") {
        reset_session_transfer_();
        write_line_("GSES2_CANCELLED");
        command_.clear();
        return;
      }

      // Protocollo precedente mantenuto per compatibilità.
      if (command_ == "GSES_GET") {
        std::vector<uint8_t> payload = goats_sessions_export_blob();
        const uint32_t crc = crc32_(payload.data(), payload.size());
        char header[64];
        std::snprintf(header, sizeof(header), "GSES_BEGIN %u %08lX",
                      static_cast<unsigned>(payload.size()),
                      static_cast<unsigned long>(crc));
        write_line_(header);
        if (!payload.empty())
          usb_serial_jtag_write_bytes(payload.data(), payload.size(),
                                     2000 / portTICK_PERIOD_MS);
        command_.clear();
        return;
      }

      if (command_ == "GSES_CLEAR") {
        if (goats_sessions_clear_archive()) write_line_("GSES_CLEAR_OK");
        else write_line_("GSES_ERR STORAGE");
        command_.clear();
        return;
      }

      unsigned long session_index = 0;
      if (std::sscanf(command_.c_str(), "GSES_DELETE %lu", &session_index) == 1) {
        if (goats_sessions_delete_display(static_cast<size_t>(session_index))) {
          char answer[48];
          std::snprintf(answer, sizeof(answer), "GSES_DELETE_OK %u",
                        static_cast<unsigned>(goats_sessions_count()));
          write_line_(answer);
        } else {
          write_line_("GSES_ERR INDEX");
        }
        command_.clear();
        return;
      }

      unsigned long delete_index = 0;
      if (std::sscanf(command_.c_str(), "GTRK_DELETE %lu", &delete_index) == 1) {
        if (delete_track(static_cast<size_t>(delete_index))) {
          char answer[48];
          std::snprintf(answer, sizeof(answer), "GTRK_DELETE_OK %u", static_cast<unsigned>(tracks_.size()));
          write_line_(answer);
        } else {
          write_line_("GTRK_ERR INDEX");
        }
        command_.clear();
        return;
      }

      if (command_ == "USB_SD_MODE") {
        // Acknowledge while Serial/JTAG is still alive, then hand USB + SD
        // ownership to TinyUSB MSC. The serial COM port will disappear.
        write_line_("USB_SD_ACK");
        command_.clear();
        delay(250);
        (void) goats_usb_sd_msc::start();
        return;
      }

      if (command_ == "GSD_PING") {
        write_line_("GSD_PONG GUITION_V1_0_10");
        command_.clear();
        return;
      }
      if (command_ == "GSD_STATUS") {
        char status[120];
        std::snprintf(status, sizeof(status),
          "GSD_STATUS READY=%u LIVE=%u SESSION=%u",
          static_cast<unsigned>(goats_sd_storage::ready()),
          static_cast<unsigned>(goats_sd_storage::live_open()),
          static_cast<unsigned>(goats_sessions_count() > 0));
        write_line_(status);
        command_.clear();
        return;
      }

      if (command_ == "GSD_LIST") {
        if (!goats_sd_storage::ready()) {
          write_line_("GSD_ERR NO_SD");
          command_.clear();
          return;
        }
        const auto files = goats_sd_storage::list_files();
        char head[48];
        std::snprintf(head, sizeof(head), "GSD_LIST_BEGIN %u",
                      static_cast<unsigned>(files.size()));
        write_line_(head);
        for (const auto &item : files) {
          char line[160];
          std::snprintf(line, sizeof(line), "GSD_FILE %lu %s",
                        static_cast<unsigned long>(item.size), item.name.c_str());
          write_line_(line);
        }
        write_line_("GSD_LIST_END");
        command_.clear();
        return;
      }

      unsigned long trace_session_id = 0;
      if (std::sscanf(
              command_.c_str(),
              "GSD_SESSION %lu",
              &trace_session_id) == 1) {
        stream_session_trace_(static_cast<uint32_t>(trace_session_id));
        command_.clear();
        return;
      }

      char sd_name[96]{};
      if (std::sscanf(command_.c_str(), "GSD_GET %95s", sd_name) == 1) {
        stream_sd_file_(sd_name);
        command_.clear();
        return;
      }

      if (command_ == "GANO_IDENTITY") {
        identity_response_mode_ = IdentityResponseMode::GANO;
        identity_requested_ = true;
        command_.clear();
        return;
      }

      if (command_ == "GGID_GET") {
        identity_response_mode_ = IdentityResponseMode::GGID;
        identity_requested_ = true;
        command_.clear();
        return;
      }

      if (command_ == "GANO_APPLY") {
        nvs_handle_t h;
        size_t n = 0;
        if (nvs_open("goats_gnss", NVS_READONLY, &h) == ESP_OK) {
          if (nvs_get_blob(h, "assist", nullptr, &n) != ESP_OK) n = 0;
          nvs_close(h);
        }
        if (n < 8 || n > 196608) {
          write_line_("GANO_APPLY_ERR NO_DATA");
        } else {
          assistnow_apply_requested_ = true;
          write_line_("GANO_APPLY_READY");
        }
        command_.clear();
        return;
      }

      if (command_ == "GANO_STATUS") {
        nvs_handle_t h;
        size_t n = 0;
        if (nvs_open("goats_gnss", NVS_READONLY, &h) == ESP_OK) {
          if (nvs_get_blob(h, "assist", nullptr, &n) != ESP_OK) n = 0;
          nvs_close(h);
        }
        char answer[48];
        std::snprintf(answer, sizeof(answer), "GANO_STATUS %u",
                      static_cast<unsigned>(n));
        write_line_(answer);
        command_.clear();
        return;
      }

      if (command_ == "GANO_CLEAR") {
        nvs_handle_t h;
        bool ok = false;
        if (nvs_open("goats_gnss", NVS_READWRITE, &h) == ESP_OK) {
          esp_err_t e = nvs_erase_key(h, "assist");
          if (e == ESP_ERR_NVS_NOT_FOUND) e = ESP_OK;
          if (e == ESP_OK) e = nvs_commit(h);
          nvs_close(h);
          ok = (e == ESP_OK);
        }
        write_line_(ok ? "GANO_CLEAR_OK" : "GANO_ERR STORAGE");
        command_.clear();
        return;
      }

      unsigned long ano_size = 0;
      unsigned long ano_crc = 0;
      if (std::sscanf(command_.c_str(), "GANO_BEGIN %lu %lx",
                      &ano_size, &ano_crc) == 2 &&
          ano_size >= 8 && ano_size <= 196608) {
        expected_size_ = static_cast<size_t>(ano_size);
        expected_crc_ = static_cast<uint32_t>(ano_crc);
        payload_kind_ = PayloadKind::ASSISTNOW;
        assist_received_ = 0;
        assist_crc_state_ = 0xFFFFFFFFu;
        assist_first_[0] = assist_first_[1] = 0;
        assist_chunk_remaining_ = std::min<size_t>(512, expected_size_);

        if (assist_buffer_) {
          heap_caps_free(assist_buffer_);
          assist_buffer_ = nullptr;
        }
        assist_buffer_ = static_cast<uint8_t *>(
            heap_caps_malloc(expected_size_, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
        if (!assist_buffer_) {
          assist_buffer_ = static_cast<uint8_t *>(
              heap_caps_malloc(expected_size_, MALLOC_CAP_8BIT));
        }
        if (!assist_buffer_) {
          write_line_("GANO_ERR MEMORY");
          command_.clear();
          return;
        }

        state_ = State::PAYLOAD;
        write_line_("GANO_READY");
        command_.clear();
        return;
      }

      unsigned long size = 0;
      unsigned long crc = 0;
      if (std::sscanf(command_.c_str(), "GTRK_BEGIN %lu %lx", &size, &crc) == 2 &&
          size > 8 && size <= 60000) {
        expected_size_ = static_cast<size_t>(size);
        expected_crc_ = static_cast<uint32_t>(crc);
        incoming_.clear();
        incoming_.reserve(expected_size_);
        payload_kind_ = PayloadKind::TRACKS;
        state_ = State::PAYLOAD;
        write_line_("GTRK_READY");
      } else {
        write_line_("GTRK_ERR COMMAND");
      }
      command_.clear();
      return;
    }

    if (payload_kind_ == PayloadKind::ASSISTNOW) {
      if (!assist_buffer_ || assist_received_ >= expected_size_) {
        state_ = State::COMMAND;
        write_line_("GANO_ERR MEMORY");
        return;
      }

      assist_buffer_[assist_received_] = value;
      if (assist_received_ < 2) assist_first_[assist_received_] = value;
      assist_crc_state_ ^= value;
      for (int bit = 0; bit < 8; ++bit)
        assist_crc_state_ = (assist_crc_state_ >> 1) ^
            (0xEDB88320u & (0u - (assist_crc_state_ & 1u)));

      ++assist_received_;
      if (assist_chunk_remaining_ > 0) --assist_chunk_remaining_;

      if (assist_chunk_remaining_ == 0) {
        char ack[64];
        std::snprintf(ack, sizeof(ack), "GANO_CHUNK_OK %u %u",
                      static_cast<unsigned>(assist_received_),
                      static_cast<unsigned>(expected_size_));
        write_line_(ack);
        if (assist_received_ < expected_size_) {
          const size_t remain = expected_size_ - assist_received_;
          assist_chunk_remaining_ = std::min<size_t>(512, remain);
          return;
        }
      }

      if (assist_received_ < expected_size_) return;

      state_ = State::COMMAND;
      const uint32_t actual_crc = assist_crc_state_ ^ 0xFFFFFFFFu;
      if (actual_crc != expected_crc_) {
        heap_caps_free(assist_buffer_);
        assist_buffer_ = nullptr;
        write_line_("GANO_ERR CRC");
        return;
      }
      if (assist_first_[0] != 0xB5 || assist_first_[1] != 0x62) {
        heap_caps_free(assist_buffer_);
        assist_buffer_ = nullptr;
        write_line_("GANO_ERR FORMAT");
        return;
      }

      nvs_handle_t h;
      esp_err_t e = nvs_open("goats_gnss", NVS_READWRITE, &h);
      if (e == ESP_OK) {
        e = nvs_set_blob(h, "assist", assist_buffer_, assist_received_);
        if (e == ESP_OK) e = nvs_commit(h);
        nvs_close(h);
      }
      heap_caps_free(assist_buffer_);
      assist_buffer_ = nullptr;

      if (e != ESP_OK) {
        char line[80];
        std::snprintf(line, sizeof(line), "GANO_ERR NVS %s", esp_err_to_name(e));
        write_line_(line);
        return;
      }

      char answer[48];
      std::snprintf(answer, sizeof(answer), "GANO_OK %u",
                    static_cast<unsigned>(assist_received_));
      write_line_(answer);
      return;
    }

    incoming_.push_back(value);
    if (incoming_.size() < expected_size_) return;

    state_ = State::COMMAND;
    uint32_t actual_crc = crc32_(incoming_.data(), incoming_.size());
    if (actual_crc != expected_crc_) {
      write_line_("GTRK_ERR CRC");
      incoming_.clear();
      return;
    }

    std::vector<GoatsTrackUsb> parsed;
    if (!parse_catalog_(incoming_, parsed)) {
      write_line_("GTRK_ERR FORMAT");
      incoming_.clear();
      return;
    }

    if (!save_to_nvs_(incoming_)) {
      write_line_("GTRK_ERR STORAGE");
      incoming_.clear();
      return;
    }

    tracks_ = std::move(parsed);
    revision_++;
    char answer[48];
    std::snprintf(answer, sizeof(answer), "GTRK_OK %u", static_cast<unsigned>(tracks_.size()));
    write_line_(answer);
    incoming_.clear();
  }

  template<typename T>
  static bool read_value_(const std::vector<uint8_t> &data, size_t &offset, T &value) {
    if (offset + sizeof(T) > data.size()) return false;
    std::memcpy(&value, data.data() + offset, sizeof(T));
    offset += sizeof(T);
    return true;
  }

  static bool read_string_(const std::vector<uint8_t> &data, size_t &offset, std::string &value) {
    uint8_t length = 0;
    if (!read_value_(data, offset, length)) return false;
    if (offset + length > data.size()) return false;
    value.assign(reinterpret_cast<const char *>(data.data() + offset), length);
    offset += length;
    return true;
  }

  static bool parse_catalog_(const std::vector<uint8_t> &data,
                             std::vector<GoatsTrackUsb> &result) {
    if (data.size() < 8 || std::memcmp(data.data(), "GTC3", 4) != 0) return false;
    size_t offset = 4;
    uint16_t version = 0, count = 0;
    if (!read_value_(data, offset, version) || !read_value_(data, offset, count)) return false;
    if (version != 1 || count > 50) return false;

    result.clear();
    result.reserve(count);
    for (uint16_t i = 0; i < count; i++) {
      GoatsTrackUsb track;
      uint8_t sector_count = 0;
      if (!read_string_(data, offset, track.name) ||
          !read_value_(data, offset, track.start_lat) ||
          !read_value_(data, offset, track.start_lon) ||
          !read_value_(data, offset, track.finish_lat) ||
          !read_value_(data, offset, track.finish_lon) ||
          !read_value_(data, offset, track.trigger_radius_m) ||
          !read_value_(data, offset, track.direction) ||
          !read_value_(data, offset, sector_count)) return false;
      if (track.name.empty() || sector_count > 12) return false;

      for (uint8_t s = 0; s < sector_count; s++) {
        GoatsSectorUsb sector;
        if (!read_string_(data, offset, sector.name) ||
            !read_value_(data, offset, sector.lat1) ||
            !read_value_(data, offset, sector.lon1) ||
            !read_value_(data, offset, sector.lat2) ||
            !read_value_(data, offset, sector.lon2)) return false;
        track.sectors.push_back(std::move(sector));
      }
      result.push_back(std::move(track));
    }
    return offset == data.size();
  }

  template<typename T>
  static void append_value_(std::vector<uint8_t> &data, const T &value) {
    const auto *ptr = reinterpret_cast<const uint8_t *>(&value);
    data.insert(data.end(), ptr, ptr + sizeof(T));
  }

  static bool append_string_(std::vector<uint8_t> &data, const std::string &value) {
    if (value.size() > 255) return false;
    uint8_t length = static_cast<uint8_t>(value.size());
    append_value_(data, length);
    data.insert(data.end(), value.begin(), value.end());
    return true;
  }

  static bool serialize_catalog_(const std::vector<GoatsTrackUsb> &tracks,
                                 std::vector<uint8_t> &data) {
    if (tracks.size() > 50) return false;
    data.clear();
    data.insert(data.end(), {'G', 'T', 'C', '3'});
    uint16_t version = 1;
    uint16_t count = static_cast<uint16_t>(tracks.size());
    append_value_(data, version);
    append_value_(data, count);
    for (const auto &track : tracks) {
      if (!append_string_(data, track.name) || track.sectors.size() > 12) return false;
      append_value_(data, track.start_lat);
      append_value_(data, track.start_lon);
      append_value_(data, track.finish_lat);
      append_value_(data, track.finish_lon);
      append_value_(data, track.trigger_radius_m);
      append_value_(data, track.direction);
      uint8_t sector_count = static_cast<uint8_t>(track.sectors.size());
      append_value_(data, sector_count);
      for (const auto &sector : track.sectors) {
        if (!append_string_(data, sector.name)) return false;
        append_value_(data, sector.lat1);
        append_value_(data, sector.lon1);
        append_value_(data, sector.lat2);
        append_value_(data, sector.lon2);
      }
    }
    return true;
  }

  bool save_to_nvs_(const std::vector<uint8_t> &data) {
    nvs_handle_t handle;
    if (nvs_open("goats_tracks", NVS_READWRITE, &handle) != ESP_OK) return false;
    esp_err_t err = nvs_set_blob(handle, "catalog", data.data(), data.size());
    if (err == ESP_OK) err = nvs_commit(handle);
    nvs_close(handle);
    return err == ESP_OK;
  }

  void load_from_nvs_() {
    nvs_handle_t handle;
    if (nvs_open("goats_tracks", NVS_READONLY, &handle) != ESP_OK) return;
    size_t size = 0;
    if (nvs_get_blob(handle, "catalog", nullptr, &size) != ESP_OK || size == 0 || size > 60000) {
      nvs_close(handle);
      return;
    }
    std::vector<uint8_t> data(size);
    if (nvs_get_blob(handle, "catalog", data.data(), &size) == ESP_OK) {
      std::vector<GoatsTrackUsb> parsed;
      if (parse_catalog_(data, parsed)) tracks_ = std::move(parsed);
    }
    nvs_close(handle);
  }
};

static GoatsUsbTrackStore GOATS_USB_TRACKS;

inline void goats_tracks_setup() { GOATS_USB_TRACKS.setup(); }
inline void goats_tracks_loop() { GOATS_USB_TRACKS.loop(); }
inline void goats_usb_suspend_for_msc() { GOATS_USB_TRACKS.suspend_for_msc(); }
inline uint32_t goats_usb_last_activity_ms() {
  return GOATS_USB_TRACKS.last_usb_activity_ms();
}
inline size_t goats_track_count() { return GOATS_USB_TRACKS.count(); }
inline uint32_t goats_track_revision() { return GOATS_USB_TRACKS.revision(); }
inline const GoatsTrackUsb *goats_track(size_t index) { return GOATS_USB_TRACKS.track(index); }
inline const char *goats_track_name(size_t index) {
  const auto *track = GOATS_USB_TRACKS.track(index);
  return track ? track->name.c_str() : "NESSUN CIRCUITO";
}
inline std::vector<size_t> goats_track_sorted_indices() {
  std::vector<size_t> idx;
  idx.reserve(goats_track_count());
  for (size_t i = 0; i < goats_track_count(); i++) idx.push_back(i);
  std::sort(idx.begin(), idx.end(), [](size_t a, size_t b) {
    std::string an = goats_track_name(a);
    std::string bn = goats_track_name(b);
    std::transform(an.begin(), an.end(), an.begin(),
                   [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    std::transform(bn.begin(), bn.end(), bn.begin(),
                   [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    return an < bn;
  });
  return idx;
}

inline esphome::FixedVector<const char *> goats_track_dropdown_options() {
  // ESPHome 2026.10.x: LVGL set_options() accepts FixedVector<const char *>.
  // Keep the backing strings static so the c_str() pointers remain valid
  // after this helper returns and for the lifetime of the LVGL options.
  static std::vector<std::string> option_storage;
  option_storage.clear();
  option_storage.reserve(goats_track_count() + 1);
  option_storage.emplace_back("AUTO");

  const auto idx = goats_track_sorted_indices();
  for (size_t physical_index : idx) {
    option_storage.emplace_back(goats_track_name(physical_index));
  }

  esphome::FixedVector<const char *> result;
  result.init(option_storage.size());
  for (const auto &option : option_storage) {
    result.push_back(option.c_str());
  }
  return result;
}

inline int goats_track_dropdown_to_physical(int menu_index) {
  if (menu_index <= 0) return 0;
  const auto idx = goats_track_sorted_indices();
  const size_t pos = static_cast<size_t>(menu_index - 1);
  if (pos >= idx.size()) return 0;
  return static_cast<int>(idx[pos] + 1);
}

inline int goats_track_physical_to_dropdown(int selected_circuit) {
  if (selected_circuit <= 0) return 0;
  const size_t physical = static_cast<size_t>(selected_circuit - 1);
  const auto idx = goats_track_sorted_indices();
  for (size_t pos = 0; pos < idx.size(); pos++) {
    if (idx[pos] == physical) return static_cast<int>(pos + 1);
  }
  return 0;
}
inline bool goats_delete_track(size_t index) { return GOATS_USB_TRACKS.delete_track(index); }
inline bool goats_clear_tracks() { return GOATS_USB_TRACKS.clear_tracks(); }
