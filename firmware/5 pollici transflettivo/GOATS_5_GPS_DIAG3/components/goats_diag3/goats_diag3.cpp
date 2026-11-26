#include "goats_diag3.h"
#include "goats_m9n_cfg.h"
#include "esphome/core/log.h"
namespace esphome::goats_diag3 {
static const char *const TAG = "goats_diag3";
void GoatsDiag3::setup() { started_ = ::millis(); }
void GoatsDiag3::loop() {
  if (!configured_) {
    // Match DIAG3's 900 ms startup threshold; only the LCD/NVS setup is replaced.
    if (uint32_t(::millis() - started_) < 900) return;
    ESP_LOGI(TAG, "DIAG3: configurazione GNSS originale in RAM, RX17/TX10");
    goats_cfg::configure(*this->parent_);
    configured_ = true;
    ESP_LOGI(TAG, "Sequenza DIAG3 inviata: 230400 baud / richiesta 25 Hz (ACK da verificare)");
  }
  // Original DIAG3 reader and original batch size; no other UART consumer.
  goats_m9n::poll(this->parent_);
  goats_m9n::take_samples(batch_, 8);
  goats_gps_diag::stability.tick(::millis());
  const uint32_t now = ::millis();
  if (uint32_t(now - last_log_) >= 10000) {
    last_log_ = now;
    ESP_LOGI(TAG, "%s | visti=%s usati=%s HDOP=%s km/h=%s", status_text().c_str(),
      visible_text().c_str(), used_text().c_str(), hdop_text().c_str(), speed_text().c_str());
    ESP_LOGI(TAG, "%s | %s", transport_text().c_str(), age_text().c_str());
  }
}
void GoatsDiag3::dump_config() {
  ESP_LOGCONFIG(TAG, "GOATS 5 GPS DIAG3 / 0.1.0, base RLCD DIAG3 1e73b8b");
  ESP_LOGCONFIG(TAG, "GPS RX17/TX10: 38400 iniziali, bootstrap originale a 230400, buffer 16384");
}
bool GoatsDiag3::position_valid() const {
  const auto &m = goats_gps_diag::stability;
  return configured_ && m.pvt_fresh(::millis()) && m.fix_active;
}
std::string GoatsDiag3::status_text() const {
  if (!configured_) return "AVVIO - CONFIGURAZIONE GPS DIAG3";
  const auto &m = goats_gps_diag::stability;
  const uint32_t now = ::millis();
  if (!m.pvt_fresh(now)) return goats_gps_diag::counters.status(now, false);
  if (position_valid()) return std::string("DATI OK - ") + m.fix_name();
  return m.fix_type == 5 ? "DATI OK - SOLO TEMPO" : "DATI OK - ATTESA FIX";
}
std::string GoatsDiag3::visible_text() const {
  if (!goats_gps_diag::stability.sat_fresh(::millis())) return "--";
  return std::to_string(goats_m9n::state.visible_sats);
}
std::string GoatsDiag3::used_text() const {
  if (!goats_gps_diag::stability.pvt_fresh(::millis())) return "--";
  return std::to_string(goats_m9n::state.used_sats);
}
std::string GoatsDiag3::hdop_text() const {
  if (!goats_gps_diag::stability.dop_fresh(::millis())) return "--";
  char b[24]; snprintf(b, sizeof(b), "%.2f", double(goats_m9n::state.hdop)); return b;
}
std::string GoatsDiag3::speed_text() const {
  if (!position_valid()) return "--";
  char b[24]; snprintf(b, sizeof(b), "%.1f", double(goats_m9n::state.speed_kmh)); return b;
}
std::string GoatsDiag3::stability_text() const {
  const auto &m = goats_gps_diag::stability;
  char b[220];
  const uint32_t seconds = m.continuous_fix_ms() / 1000;
  snprintf(b, sizeof(b), "FIX CONT %lu:%02lu   PERSI %lu\nBUCHI PVT %lu   GAP MAX %lu ms",
    (unsigned long)(seconds / 60), (unsigned long)(seconds % 60), (unsigned long)m.fix_losses,
    (unsigned long)m.stream_losses, (unsigned long)m.max_gap_ms);
  return b;
}
std::string GoatsDiag3::transport_text() const {
  const auto &m = goats_gps_diag::stability;
  const auto &d = goats_gps_diag::counters;
  char b[256], step[24], rate[24];
  if (m.have_step) snprintf(step, sizeof(step), "%lu", (unsigned long)m.step_ms);
  else snprintf(step, sizeof(step), "--");
  if (m.pvt_fresh(::millis())) snprintf(rate, sizeof(rate), "%.1f", double(goats_m9n::state.pvt_hz));
  else snprintf(rate, sizeof(rate), "--");
  snprintf(b, sizeof(b), "PVT %s Hz   PASSO GPS %s ms   ERR CK %lu\nRX %lu   UBX %lu   ACK %lu   NAK %lu",
    rate, step, (unsigned long)d.checksum_errors, (unsigned long)d.bytes,
    (unsigned long)d.frames, (unsigned long)d.ack, (unsigned long)d.nak);
  return b;
}
std::string GoatsDiag3::age_text() const {
  const auto &m = goats_gps_diag::stability;
  const uint32_t now = ::millis();
  char pvt[24], sat[24], dop[24], b[160];
  auto age = [now](char *out, bool have, uint32_t last) {
    if (have) snprintf(out, 24, "%lu ms", (unsigned long)(now-last));
    else snprintf(out, 24, "MAI");
  };
  age(pvt, m.have_pvt, m.last_pvt); age(sat, m.have_sat, m.last_sat); age(dop, m.have_dop, m.last_dop);
  snprintf(b, sizeof(b), "ETA PVT %s   SAT %s   HDOP %s", pvt, sat, dop); return b;
}
}
