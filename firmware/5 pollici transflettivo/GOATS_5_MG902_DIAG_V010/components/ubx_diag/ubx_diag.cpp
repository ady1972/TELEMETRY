#include "ubx_diag.h"

#include "esphome/core/hal.h"
#include "esphome/core/log.h"

#ifdef USE_ESP32
#include <esp_heap_caps.h>
#include <esp_system.h>
#endif

namespace esphome::ubx_diag {

static const char *const TAG = "ubx_diag";

// Deve restare allineato a rx_buffer_size nello YAML: sopra questa soglia si rischia l'overflow.
static constexpr int RX_SATURATION_LEVEL = 7600;

void UbxDiag::setup() {
  this->started_ms_ = millis();
  this->diag_.reset_stats(this->started_ms_);
}

void UbxDiag::loop() {
  const uint32_t now = millis();
  if (this->last_loop_ms_ != 0)
    this->diag_.note_loop_gap(now - this->last_loop_ms_);
  this->last_loop_ms_ = now;

  int avail = this->available();
  if (avail >= RX_SATURATION_LEVEL)
    this->diag_.note_rx_saturation();

  uint8_t buf[256];
  // Limite per ciclo: evita di bloccare il loop in caso di flusso continuo.
  int budget = 12288;
  while (avail > 0 && budget > 0) {
    int n = avail < static_cast<int>(sizeof(buf)) ? avail : static_cast<int>(sizeof(buf));
    if (n > budget) n = budget;
    if (!this->read_array(buf, n))
      break;
    this->diag_.feed(buf, n, millis());
    budget -= n;
    avail = this->available();
  }
  this->diag_.tick(now);

  // I primi secondi includono l'avvio del display: si ripulisce tutto una volta.
  if (!this->warmed_up_ && now - this->started_ms_ > 4000) {
    this->warmed_up_ = true;
    this->diag_.reset_stats(now);
  }

  if (this->poll_ && this->warmed_up_)
    this->poll_module_(now);

  if (now - this->last_log_ms_ >= 10000) {
    this->last_log_ms_ = now;
    const auto &p = this->diag_.parser_stats();
    const uint32_t t = millis();  // riletto: i dati appena elaborati sono piu' recenti di "now"
    ESP_LOGI(TAG, "%s | %.1f Hz | %s | SV %d | perse %u | ck %u | non-UBX %u | NMEA %u",
             this->diag_.link_text(t).c_str(), this->diag_.pvt_hz(), this->diag_.fix_text(t).c_str(),
             this->diag_.sv_used(t), (unsigned) this->diag_.lost_epochs(), (unsigned) p.checksum_errors,
             (unsigned) p.junk_bytes, (unsigned) p.nmea_hits);
  }
}

// Solo richieste di lettura (poll e CFG-VALGET): la configurazione del modulo non viene toccata.
void UbxDiag::poll_module_(uint32_t now) {
  if (now - this->last_poll_ms_ >= 250) {
    this->last_poll_ms_ = now;
    switch (this->poll_step_) {
      case 0:
        this->send_poll_(0x01, 0x35);  // NAV-SAT
        break;
      case 1:
        this->send_poll_(0x01, 0x04);  // NAV-DOP
        break;
      case 2:
        this->send_poll_(0x01, 0x03);  // NAV-STATUS
        break;
      default:
        this->send_poll_(0x0A, 0x38);  // MON-RF
        break;
    }
    this->poll_step_ = (this->poll_step_ + 1) % 4;
  }
  if (now - this->last_cfg_ms_ >= 1500) {
    this->last_cfg_ms_ = now;
    if (!this->diag_.have_version())
      this->send_poll_(0x0A, 0x04);  // MON-VER
    const int group = this->diag_.next_cfg_group();
    if (group >= 0) {
      uint8_t frame[64];
      const size_t len = this->diag_.build_cfg_poll(group, frame);
      this->write_array(frame, len);
    }
  }
}

void UbxDiag::send_poll_(uint8_t cls, uint8_t id) {
  uint8_t frame[8];
  const size_t len = ubx::build_frame(frame, cls, id, nullptr, 0);
  this->write_array(frame, len);
}

void UbxDiag::reset_statistics() {
  this->diag_.reset_stats(millis());
  this->diag_.restart_queries();
  ESP_LOGI(TAG, "Statistiche azzerate");
}

void UbxDiag::dump_config() {
  ESP_LOGCONFIG(TAG, "UBX diagnostica:");
  ESP_LOGCONFIG(TAG, "  Rate atteso: %u Hz", (unsigned) this->expected_rate_);
  ESP_LOGCONFIG(TAG, "  Baud atteso: %u", (unsigned) this->expected_baud_);
  ESP_LOGCONFIG(TAG, "  Interrogazioni al modulo: %s", this->poll_ ? "si" : "no");
}

float UbxDiag::pvt_rate() { return this->diag_.pvt_hz(); }
float UbxDiag::speed_kmh() { return this->diag_.speed_kmh(millis()); }
float UbxDiag::h_acc_m() { return this->diag_.h_acc_m(millis()); }
int UbxDiag::sv_used() { return this->diag_.sv_used(millis()); }
int UbxDiag::link_level() { return this->diag_.link_level(millis()); }
int UbxDiag::fix_level() { return this->diag_.fix_level(millis()); }
std::string UbxDiag::fix_text() { return this->diag_.fix_text(millis()); }
std::string UbxDiag::link_text() { return this->diag_.link_text(millis()); }
std::string UbxDiag::header_text() { return this->diag_.header_text(millis()); }

std::string UbxDiag::speed_text() {
  const float v = this->speed_kmh();
  std::string s;
  if (std::isnan(v))
    s = "--.- km/h";
  else
    ubx::appendf(s, "%.1f km/h", v);
  return s;
}

std::string UbxDiag::sv_text() {
  std::string s;
  const int seen = this->diag_.sv_seen(millis());
  if (seen < 0)
    ubx::appendf(s, "Usati %d\nVisti --", this->sv_used());
  else
    ubx::appendf(s, "Usati %d\nVisti %d", this->sv_used(), seen);
  return s;
}

std::string UbxDiag::fix_position_text() { return this->diag_.fix_position_text(millis()); }
std::string UbxDiag::fix_quality_text() { return this->diag_.fix_quality_text(millis()); }
std::string UbxDiag::link_stats_text() { return this->diag_.link_stats_text(millis()); }
std::string UbxDiag::sat_summary_text() { return this->diag_.sat_summary_text(millis()); }
std::string UbxDiag::sat_list_text(int column) { return this->diag_.sat_list_text(millis(), column); }
std::string UbxDiag::module_text() { return this->diag_.module_text(millis()); }

std::string UbxDiag::system_text() {
  std::string s = "SISTEMA\n";
  ubx::appendf(s, "Uptime        %u s\n", (unsigned) (millis() / 1000));
#ifdef USE_ESP32
  ubx::appendf(s, "RAM libera    %u kB\n", (unsigned) (heap_caps_get_free_size(MALLOC_CAP_INTERNAL) / 1024));
  ubx::appendf(s, "RAM minima    %u kB\n", (unsigned) (heap_caps_get_minimum_free_size(MALLOC_CAP_INTERNAL) / 1024));
  ubx::appendf(s, "PSRAM totale  %u kB\n", (unsigned) (heap_caps_get_total_size(MALLOC_CAP_SPIRAM) / 1024));
  ubx::appendf(s, "PSRAM libera  %u kB\n", (unsigned) (heap_caps_get_free_size(MALLOC_CAP_SPIRAM) / 1024));
  ubx::appendf(s, "Causa reset   %d\n", (int) esp_reset_reason());
#endif
  return s;
}

}  // namespace esphome::ubx_diag
