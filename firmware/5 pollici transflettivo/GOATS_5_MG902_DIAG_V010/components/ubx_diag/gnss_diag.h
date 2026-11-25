#pragma once
// Decodifica, statistiche e testi diagnostici. Nessuna dipendenza da ESPHome.

#include <cmath>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <string>

#include "ubx_parser.h"

namespace ubx {

enum Level : uint8_t { LVL_OK = 0, LVL_WARN = 1, LVL_ERR = 2 };

// Aggiunge testo formattato a una stringa.
__attribute__((format(printf, 2, 3))) inline void appendf(std::string &s, const char *fmt, ...) {
  char tmp[160];
  va_list ap;
  va_start(ap, fmt);
  vsnprintf(tmp, sizeof(tmp), fmt, ap);
  va_end(ap);
  s += tmp;
}

struct Pvt {
  uint32_t itow{0};
  uint16_t year{0};
  uint8_t month{0}, day{0}, hour{0}, min{0}, sec{0}, valid{0};
  uint8_t fix_type{0}, flags{0}, num_sv{0};
  int32_t lon{0}, lat{0}, h_msl{0};
  uint32_t h_acc{0}, v_acc{0}, s_acc{0}, head_acc{0};
  int32_t g_speed{0}, head_mot{0}, vel_d{0};
  uint16_t p_dop{0};
  bool fix_ok() const { return (flags & 0x01) != 0; }
  bool diff() const { return (flags & 0x02) != 0; }
  bool time_resolved() const { return (valid & 0x07) == 0x07; }
};

struct Sat {
  uint8_t gnss, sv, cno;
  int8_t elev;
  int16_t azim;
  bool used, diff;
};

static constexpr int MAX_SATS = 96;
static constexpr int MAX_MSG_TYPES = 16;
static constexpr int GNSS_IDS = 7;  // 0 GPS, 1 SBAS, 2 GAL, 3 BDS, 4 IMES, 5 QZSS, 6 GLO

struct MsgStat {
  uint8_t cls{0}, id{0};
  uint16_t last_len{0};
  uint32_t count{0}, window{0};
  float hz{0};
};

struct CfgItem {
  uint32_t key;
  const char *name;
  int64_t expected;  // -1 = solo informativo
  uint8_t group;
  bool received;
  uint32_t value;
};

static constexpr int CFG_ITEMS = 13;
static constexpr int CFG_GROUPS = 3;

class GnssDiag {
 public:
  GnssDiag() { init_cfg_(); }

  void set_expected(uint32_t rate_hz, uint32_t baud) {
    exp_rate_ = rate_hz;
    exp_period_ms_ = 1000 / rate_hz;
    exp_baud_ = baud;
    init_cfg_();
  }

  // ---------------- ingresso dati ----------------
  void feed(const uint8_t *data, size_t n, uint32_t now) {
    if (n == 0)
      return;
    bytes_ += n;
    win_bytes_ += n;
    last_byte_ms_ = now;
    got_byte_ = true;
    for (size_t i = 0; i < n; i++) {
      if (parser_.feed(data[i]))
        handle_(parser_.frame(), now);
    }
  }

  // Da chiamare spesso: chiude la finestra statistica di circa 1 s.
  void tick(uint32_t now) {
    uint32_t el = now - win_start_;
    if (el < 1000)
      return;
    float k = 1000.0f / static_cast<float>(el);
    bytes_s_ = win_bytes_ * k;
    frames_s_ = (parser_.stats.frames_ok - win_frames_base_) * k;
    pvt_hz_ = win_pvt_ * k;
    dt_min_ = win_dt_n_ ? win_dt_min_ : 0;
    dt_max_ = win_dt_n_ ? win_dt_max_ : 0;
    dt_avg_ = win_dt_n_ ? static_cast<float>(win_dt_sum_) / win_dt_n_ : 0;
    for (int i = 0; i < n_msgs_; i++) {
      msgs_[i].hz = msgs_[i].window * k;
      msgs_[i].window = 0;
    }
    uint32_t errs = error_total_();
    if (errs != last_error_total_) {
      last_error_ms_ = now;
      had_error_ = true;
      last_error_total_ = errs;
    }
    win_start_ = now;
    win_bytes_ = 0;
    win_pvt_ = 0;
    win_frames_base_ = parser_.stats.frames_ok;
    win_dt_n_ = 0;
    win_dt_sum_ = 0;
    win_dt_min_ = UINT32_MAX;
    win_dt_max_ = 0;
  }

  void note_rx_saturation() { rx_saturations_++; }
  void note_loop_gap(uint32_t ms) {
    if (ms > loop_gap_max_)
      loop_gap_max_ = ms;
  }

  // Azzera contatori e statistiche; conserva versione modulo e configurazione letta.
  void reset_stats(uint32_t now) {
    parser_.reset();
    bytes_ = 0;
    win_bytes_ = win_pvt_ = win_frames_base_ = 0;
    win_dt_n_ = 0;
    win_dt_sum_ = 0;
    win_dt_min_ = UINT32_MAX;
    win_dt_max_ = 0;
    bytes_s_ = frames_s_ = pvt_hz_ = dt_avg_ = 0;
    dt_min_ = dt_max_ = dt_worst_ = 0;
    pvt_count_ = lost_epochs_ = time_anomalies_ = rx_saturations_ = loop_gap_max_ = 0;
    last_error_total_ = 0;
    had_error_ = false;
    have_prev_ = false;
    n_msgs_ = 0;
    max_speed_ = 0;
    disp_n_ = 0;
    win_start_ = stats_start_ = now;
  }

  // ---------------- valori principali ----------------
  const Pvt &pvt() const { return pvt_; }
  bool pvt_fresh(uint32_t now) const { return have_pvt_ && now - last_pvt_ms_ < 1000; }
  float pvt_hz() const { return pvt_hz_; }
  uint32_t lost_epochs() const { return lost_epochs_; }
  uint32_t checksum_errors() const { return parser_.stats.checksum_errors; }
  const ParserStats &parser_stats() const { return parser_.stats; }
  float speed_kmh(uint32_t now) const { return pvt_fresh(now) && pvt_.fix_ok() ? pvt_.g_speed * 0.0036f : NAN; }
  float h_acc_m(uint32_t now) const { return pvt_fresh(now) ? pvt_.h_acc / 1000.0f : NAN; }
  int sv_used(uint32_t now) const { return pvt_fresh(now) ? pvt_.num_sv : 0; }
  int sat_count() const { return n_sats_; }
  int sv_seen(uint32_t now) const {
    if (!sats_fresh_(now)) return -1;
    int seen = 0;
    for (int i = 0; i < n_sats_; i++) seen += sats_[i].cno > 0;
    return seen;
  }

  std::string fix_text(uint32_t now) const {
    if (!pvt_fresh(now))
      return "NO DATI";
    static const char *const NAMES[] = {"NO FIX", "SOLO DR", "FIX 2D", "FIX 3D", "GNSS+DR", "SOLO TEMPO"};
    const char *n = pvt_.fix_type < 6 ? NAMES[pvt_.fix_type] : "?";
    if (pvt_.fix_type >= 2 && pvt_.fix_type <= 4 && !pvt_.fix_ok())
      return "FIX NON VALIDO";
    std::string s = n;
    if (pvt_.fix_ok() && pvt_.diff())
      s += " DGNSS";
    return s;
  }
  Level fix_level(uint32_t now) const {
    if (!pvt_fresh(now))
      return LVL_ERR;
    if (pvt_.fix_ok() && pvt_.fix_type == 3)
      return LVL_OK;
    return LVL_WARN;
  }

  // ---------------- verdetto sul collegamento ----------------
  Level link_level(uint32_t now) const { return verdict_(now, nullptr); }
  std::string link_text(uint32_t now) const {
    std::string s;
    verdict_(now, &s);
    return s;
  }

  // ---------------- testi per le pagine ----------------
  std::string header_text(uint32_t now) const {
    std::string s = "DIAG-R1  ";
    appendf(s, "%4.1f Hz  %s  SV %d  ", pvt_hz_, fix_text(now).c_str(), sv_used(now));
    if (pvt_fresh(now) && pvt_.time_resolved())
      appendf(s, "%02u:%02u:%02u UTC", pvt_.hour, pvt_.min, pvt_.sec);
    else
      s += "--:--:-- UTC";
    return s;
  }

  std::string fix_position_text(uint32_t now) const {
    std::string s;
    if (!pvt_fresh(now))
      return "POSIZIONE\n\nIn attesa di NAV-PVT...";
    const bool ok = pvt_.fix_ok();
    s += ok ? "POSIZIONE\n" : "POSIZIONE (non valida)\n";
    appendf(s, "Lat    %12.7f\n", pvt_.lat * 1e-7);
    appendf(s, "Lon    %12.7f\n", pvt_.lon * 1e-7);
    appendf(s, "Quota  %9.2f m slm\n", pvt_.h_msl / 1000.0);
    appendf(s, "Rotta  %9.1f deg\n", pvt_.head_mot * 1e-5);
    appendf(s, "Vel.D  %9.2f m/s\n", pvt_.vel_d / 1000.0);
    appendf(s, "Vmax   %9.1f km/h\n", max_speed_ * 0.0036);
    if (pvt_.time_resolved())
      appendf(s, "Data   %04u-%02u-%02u\n", pvt_.year, pvt_.month, pvt_.day);
    else
      s += "Data   non risolta\n";
    return s;
  }

  std::string fix_quality_text(uint32_t now) const {
    std::string s = "QUALITA'\n";
    if (pvt_fresh(now)) {
      appendf(s, "hAcc   %8.2f m\n", pvt_.h_acc / 1000.0);
      appendf(s, "vAcc   %8.2f m\n", pvt_.v_acc / 1000.0);
      appendf(s, "sAcc   %8.2f m/s\n", pvt_.s_acc / 1000.0);
      appendf(s, "pDOP   %8.2f\n", pvt_.p_dop / 100.0);
    } else {
      s += "hAcc         --\nvAcc         --\nsAcc         --\npDOP         --\n";
    }
    if (have_dop_ && now - last_dop_ms_ < 5000)
      appendf(s, "hDOP   %8.2f  vDOP %.2f\n", h_dop_ / 100.0, v_dop_ / 100.0);
    else
      s += "hDOP         --\n";
    if (have_status_ && now - last_status_ms_ < 5000 && ttff_ms_ > 0)
      appendf(s, "TTFF   %8.1f s\n", ttff_ms_ / 1000.0);
    else
      s += "TTFF         --\n";
    if (pvt_fresh(now) && disp_n_ > 1) {
      double sn = std::sqrt(m2_n_ / (disp_n_ - 1)), se = std::sqrt(m2_e_ / (disp_n_ - 1));
      appendf(s, "Dispersione (v < 0.5 m/s)\n  sN %.2f m  sE %.2f m\n  2DRMS %.2f m", sn, se,
              2.0 * std::sqrt(sn * sn + se * se));
    } else {
      s += "Dispersione: attendi da fermo";
    }
    return s;
  }

  std::string link_stats_text(uint32_t now) const {
    const ParserStats &p = parser_.stats;
    std::string s;
    appendf(s, "Byte/s      %8.0f\n", bytes_s_);
    appendf(s, "Frame/s     %8.1f\n", frames_s_);
    appendf(s, "NAV-PVT Hz  %8.1f /%u\n", pvt_hz_, static_cast<unsigned>(exp_rate_));
    appendf(s, "PVT totali  %8u\n", static_cast<unsigned>(pvt_count_));
    appendf(s, "dt iTOW ms  %u / %.1f / %u\n", static_cast<unsigned>(dt_min_), dt_avg_,
            static_cast<unsigned>(dt_max_));
    appendf(s, "dt peggiore %8u ms\n", static_cast<unsigned>(dt_worst_));
    appendf(s, "Epoche perse%8u\n", static_cast<unsigned>(lost_epochs_));
    appendf(s, "Salti tempo %8u\n", static_cast<unsigned>(time_anomalies_));
    appendf(s, "Err checksum%8u\n", static_cast<unsigned>(p.checksum_errors));
    appendf(s, "Err lunghez.%8u\n", static_cast<unsigned>(p.length_errors));
    appendf(s, "Byte non UBX%8u\n", static_cast<unsigned>(p.junk_bytes));
    appendf(s, "Frasi NMEA  %8u\n", static_cast<unsigned>(p.nmea_hits));
    appendf(s, "RX saturo   %8u\n", static_cast<unsigned>(rx_saturations_));
    appendf(s, "Loop max ms %8u\n", static_cast<unsigned>(loop_gap_max_));
    appendf(s, "Durata test %8u s", static_cast<unsigned>((now - stats_start_) / 1000));
    return s;
  }

  std::string link_messages_text() const {
    std::string s = "MESSAGGIO     Hz  LEN   TOTALE\n";
    for (int i = 0; i < n_msgs_; i++) {
      const MsgStat &m = msgs_[i];
      char name[16];
      msg_name_(m.cls, m.id, name, sizeof(name));
      appendf(s, "%-11s%5.1f %4u %8u\n", name, m.hz, m.last_len, static_cast<unsigned>(m.count));
    }
    if (n_msgs_ == 0)
      s += "(nessuno)";
    return s;
  }

  std::string sat_summary_text(uint32_t now) const {
    if (!sats_fresh_(now))
      return "SATELLITI\n\nNessun NAV-SAT.\nCollega il TX verso il GPS\no abilita NAV-SAT sul modulo.";
    std::string s = "SISTEMA VISTI USATI C/N0\n";
    static const uint8_t ORDER[] = {0, 6, 2, 3, 1, 5};
    for (uint8_t g : ORDER) {
      int seen = 0, used = 0, n = 0, sum = 0, diff = 0;
      for (int i = 0; i < n_sats_; i++) {
        if (sats_[i].gnss != g)
          continue;
        if (sats_[i].cno > 0) {
          seen++;
          sum += sats_[i].cno;
          n++;
        }
        used += sats_[i].used ? 1 : 0;
        diff += sats_[i].diff ? 1 : 0;
      }
      appendf(s, "%-8s %4d %5d %5.1f\n", gnss_name_(g), seen, used, n ? static_cast<float>(sum) / n : 0.0f);
    }
    int diff_total = 0;
    for (int i = 0; i < n_sats_; i++)
      diff_total += sats_[i].diff ? 1 : 0;
    appendf(s, "\nSV con correzioni: %d\n", diff_total);
    appendf(s, "Soluzione DGNSS:   %s\n", pvt_fresh(now) && pvt_.diff() ? "SI" : "NO");
    s += "C/N0 in dBHz, media dei visti";
    return s;
  }

  // Elenco dei satelliti ordinati per C/N0; column 0 = primi 14, column 1 = successivi.
  std::string sat_list_text(uint32_t now, int column) const {
    if (!sats_fresh_(now))
      return "";
    static constexpr int ROWS = 14;
    uint8_t idx[MAX_SATS];
    int n = 0;
    for (int i = 0; i < n_sats_; i++) {
      if (sats_[i].cno == 0)
        continue;
      int j = n++;
      while (j > 0 && sats_[idx[j - 1]].cno < sats_[i].cno) {
        idx[j] = idx[j - 1];
        j--;
      }
      idx[j] = i;
    }
    std::string s = "SV   dB  EL U\n";
    for (int r = column * ROWS; r < n && r < (column + 1) * ROWS; r++) {
      const Sat &t = sats_[idx[r]];
      appendf(s, "%c%-3u %2u %3d %c\n", gnss_letter_(t.gnss), t.sv, t.cno, t.elev, t.used ? '*' : ' ');
    }
    return s;
  }

  std::string module_text(uint32_t now) const {
    std::string s = "MODULO (MON-VER)\n";
    if (have_ver_) {
      appendf(s, "SW  %.30s\n", sw_);
      appendf(s, "HW  %.10s\n", hw_);
      appendf(s, "%.30s\n%.30s\n", mod_[0] ? mod_ : "MOD=?", prot_[0] ? prot_ : "PROTVER=?");
    } else {
      s += "nessuna risposta\n\n\n\n";
    }
    s += "\nRF / ANTENNA (MON-RF)\n";
    if (have_rf_ && now - last_rf_ms_ < 5000) {
      static const char *const ANT[] = {"INIT", "SCONOSC.", "OK", "CORTO", "APERTA"};
      static const char *const JAM[] = {"n/d", "ok", "AVVISO", "CRITICO"};
      for (int i = 0; i < n_rf_; i++) {
        const Rf &r = rf_[i];
        appendf(s, "RF%u ant %s  jam %s %u/255\n", r.block, r.ant < 5 ? ANT[r.ant] : "?", JAM[r.jam_state & 3], r.jam_ind);
        appendf(s, "    rumore %u  AGC %u%%\n", r.noise, static_cast<unsigned>(r.agc * 100u / 8191u));
      }
    } else {
      s += "nessun dato";
    }
    return s;
  }

  std::string config_text() const {
    std::string s = "CONFIG (lettura RAM, UART1)\n";
    int received = 0;
    for (const CfgItem &c : cfg_) {
      appendf(s, "%-13s", c.name);
      if (!c.received) {
        s += group_state_[c.group] == 2 ? " rifiutato\n" :
             (group_attempts_[c.group] >= 3 ? " non letto\n" : " --\n");
        continue;
      }
      received++;
      if (c.key == KEY_DYNMODEL)
        appendf(s, " %-8s", dyn_name_(c.value));
      else
        appendf(s, " %-8u", static_cast<unsigned>(c.value));
      if (c.expected < 0)
        s += "\n";
      else
        s += static_cast<int64_t>(c.value) == c.expected ? " OK\n" : " DIVERSO\n";
    }
    if (received == 0)
      s += "Serve il filo TX ESP -> RX GPS";
    return s;
  }

  // Numero di voci di configurazione diverse da quanto atteso (-1 se nulla e' stato letto).
  int config_mismatches() const {
    int bad = 0, got = 0;
    for (const CfgItem &c : cfg_) {
      if (!c.received)
        continue;
      got++;
      if (c.expected >= 0 && static_cast<int64_t>(c.value) != c.expected)
        bad++;
    }
    return got ? bad : -1;
  }

  // ---------------- interrogazioni (sola lettura) ----------------
  bool have_version() const { return have_ver_; }
  // Primo gruppo di configurazione non ancora risposto, oppure -1.
  int next_cfg_group() const {
    for (int g = 0; g < CFG_GROUPS; g++)
      if (group_state_[g] == 0 && group_attempts_[g] < 3)
        return g;
    return -1;
  }
  // Prepara una richiesta CFG-VALGET (layer RAM). out >= 64 byte.
  size_t build_cfg_poll(int group, uint8_t *out) {
    if (group < 0 || group >= CFG_GROUPS || group_state_[group] != 0 || group_attempts_[group] >= 3)
      return 0;
    uint8_t pl[4 + 4 * CFG_ITEMS] = {0, 0, 0, 0};
    uint16_t len = 4;
    for (const CfgItem &c : cfg_) {
      if (c.group != group || c.received)
        continue;
      for (int b = 0; b < 4; b++)
        pl[len++] = (c.key >> (8 * b)) & 0xFF;
    }
    group_attempts_[group]++;
    pending_group_ = group;
    return build_frame(out, 0x06, 0x8B, pl, len);
  }
  void restart_queries() {
    have_ver_ = false;
    pending_group_ = -1;
    for (int g = 0; g < CFG_GROUPS; g++) {
      group_state_[g] = 0;
      group_attempts_[g] = 0;
    }
    for (CfgItem &c : cfg_)
      c.received = false;
  }

 private:
  static constexpr uint32_t KEY_DYNMODEL = 0x20110021;

  struct Rf {
    uint8_t block, ant, jam_state, jam_ind;
    uint16_t noise, agc;
  };

  void init_cfg_() {
    const CfgItem init[CFG_ITEMS] = {
        {0x40520001, "Baud UART1", static_cast<int64_t>(exp_baud_), 0, false, 0},
        {0x30210001, "Periodo ms", static_cast<int64_t>(exp_period_ms_), 0, false, 0},
        {0x30210002, "Nav ratio", 1, 0, false, 0},
        {0x10740001, "Uscita UBX", 1, 0, false, 0},
        {0x10740002, "Uscita NMEA", 0, 0, false, 0},
        {0x20910007, "NAV-PVT rate", 1, 0, false, 0},
        {0x1031001f, "GPS", 1, 1, false, 0},
        {0x10310025, "GLONASS", 1, 1, false, 0},
        {0x10310021, "Galileo", 1, 1, false, 0},
        {0x10310022, "BeiDou", 1, 1, false, 0},
        {0x10310020, "SBAS", 1, 1, false, 0},
        {0x10310024, "QZSS", -1, 1, false, 0},
        {KEY_DYNMODEL, "Modello din.", -1, 2, false, 0},
    };
    for (int i = 0; i < CFG_ITEMS; i++)
      cfg_[i] = init[i];
  }

  uint32_t error_total_() const {
    const ParserStats &p = parser_.stats;
    return p.checksum_errors + p.length_errors + p.junk_bytes + p.nmea_hits + lost_epochs_ + time_anomalies_ + rx_saturations_;
  }

  Level verdict_(uint32_t now, std::string *out) const {
    auto say = [out](Level l, const char *t) {
      if (out != nullptr)
        *out = t;
      return l;
    };
    if (!got_byte_ || now - last_byte_ms_ > 2000)
      return say(LVL_ERR, "NESSUN BYTE: controlla 5V, GND e TX GPS -> ingresso ESP");
    if (!have_frame_ || now - last_frame_ms_ > 2000) {
      if (parser_.stats.nmea_hits > 0)
        return say(LVL_ERR, "ARRIVA SOLO NMEA: UBX non attivo in uscita");
      return say(LVL_ERR, "BYTE SENZA UBX VALIDO: baud errato o linea disturbata");
    }
    if (!pvt_fresh(now))
      return say(LVL_ERR, "UBX ricevuto ma manca NAV-PVT");
    if (now - stats_start_ < 2500)
      return say(LVL_WARN, "Misura in corso...");
    if (pvt_hz_ < exp_rate_ * 0.94f || pvt_hz_ > exp_rate_ * 1.08f) {
      if (out != nullptr) {
        out->clear();
        appendf(*out, "RATE ANOMALO: %.1f Hz invece di %u Hz", pvt_hz_, static_cast<unsigned>(exp_rate_));
      }
      return LVL_WARN;
    }
    if (had_error_ && now - last_error_ms_ < 10000)
      return say(LVL_WARN, "Errori recenti sul collegamento (vedi pagina LINK)");
    return say(LVL_OK, "LINK OK");
  }

  void handle_(const Frame &f, uint32_t now) {
    have_frame_ = true;
    last_frame_ms_ = now;
    count_msg_(f);
    const uint8_t *p = f.payload;
    if (f.cls == 0x01 && f.id == 0x07 && f.len >= 92) {
      on_pvt_(p, now);
    } else if (f.cls == 0x01 && f.id == 0x35 && f.len >= 8) {
      on_sat_(p, f.len, now);
    } else if (f.cls == 0x01 && f.id == 0x04 && f.len >= 18) {
      v_dop_ = u2(p + 10);
      h_dop_ = u2(p + 12);
      have_dop_ = true;
      last_dop_ms_ = now;
    } else if (f.cls == 0x01 && f.id == 0x03 && f.len >= 16) {
      ttff_ms_ = u4(p + 8);
      have_status_ = true;
      last_status_ms_ = now;
    } else if (f.cls == 0x0A && f.id == 0x04 && f.len >= 40) {
      on_ver_(p, f.len);
    } else if (f.cls == 0x0A && f.id == 0x38 && f.len >= 4) {
      on_rf_(p, f.len, now);
    } else if (f.cls == 0x06 && f.id == 0x8B && f.len >= 4) {
      on_valget_(p, f.len);
    } else if (f.cls == 0x05 && f.id == 0x00 && f.len >= 2 && p[0] == 0x06 && p[1] == 0x8B) {
      if (pending_group_ >= 0)
        group_state_[pending_group_] = 2;  // NAK
      pending_group_ = -1;
    }
  }

  void count_msg_(const Frame &f) {
    int i = 0;
    while (i < n_msgs_ && !(msgs_[i].cls == f.cls && msgs_[i].id == f.id))
      i++;
    if (i == n_msgs_) {
      if (n_msgs_ >= MAX_MSG_TYPES)
        return;
      msgs_[i] = MsgStat{};
      msgs_[i].cls = f.cls;
      msgs_[i].id = f.id;
      n_msgs_++;
    }
    msgs_[i].count++;
    msgs_[i].window++;
    msgs_[i].last_len = f.len;
  }

  void on_pvt_(const uint8_t *p, uint32_t now) {
    Pvt n;
    n.itow = u4(p);
    n.year = u2(p + 4);
    n.month = p[6];
    n.day = p[7];
    n.hour = p[8];
    n.min = p[9];
    n.sec = p[10];
    n.valid = p[11];
    n.fix_type = p[20];
    n.flags = p[21];
    n.num_sv = p[23];
    n.lon = i4(p + 24);
    n.lat = i4(p + 28);
    n.h_msl = i4(p + 36);
    n.h_acc = u4(p + 40);
    n.v_acc = u4(p + 44);
    n.vel_d = i4(p + 56);
    n.g_speed = i4(p + 60);
    n.head_mot = i4(p + 64);
    n.s_acc = u4(p + 68);
    n.head_acc = u4(p + 72);
    n.p_dop = u2(p + 76);

    pvt_count_++;
    win_pvt_++;
    // La continuita' si valuta solo con tempo risolto: prima del fix iTOW puo' saltare.
    if (have_prev_ && n.time_resolved() && pvt_.time_resolved()) {
      int64_t dt = static_cast<int64_t>(n.itow) - static_cast<int64_t>(pvt_.itow);
      if (dt < -302400000LL)
        dt += 604800000LL;  // cambio settimana GPS
      if (dt <= 0 || dt > 60000) {
        time_anomalies_++;
      } else {
        uint32_t d = static_cast<uint32_t>(dt);
        win_dt_n_++;
        win_dt_sum_ += d;
        if (d < win_dt_min_)
          win_dt_min_ = d;
        if (d > win_dt_max_)
          win_dt_max_ = d;
        if (d > dt_worst_)
          dt_worst_ = d;
        uint32_t steps = (d + exp_period_ms_ / 2) / exp_period_ms_;
        if (steps > 1)
          lost_epochs_ += steps - 1;
      }
    }
    pvt_ = n;
    have_prev_ = true;
    have_pvt_ = true;
    last_pvt_ms_ = now;

    if (n.fix_ok() && n.fix_type >= 2 && n.fix_type <= 4) {
      if (n.g_speed > max_speed_)
        max_speed_ = n.g_speed;
    }
    if (n.fix_ok() && n.fix_type == 3 && n.g_speed >= 0 && n.g_speed < 500) {
      if (disp_n_ == 0) {
        ref_lat_ = n.lat;
        ref_lon_ = n.lon;
        mean_n_ = mean_e_ = m2_n_ = m2_e_ = 0;
      }
      // 1e-7 gradi di latitudine = 0.011132 m
      double dn = (static_cast<double>(n.lat) - ref_lat_) * 0.011132;
      double de = (static_cast<double>(n.lon) - ref_lon_) * 0.011132 * std::cos(ref_lat_ * 1e-7 * 0.017453292519943295);
      disp_n_++;
      double d1 = dn - mean_n_;
      mean_n_ += d1 / disp_n_;
      m2_n_ += d1 * (dn - mean_n_);
      double d2 = de - mean_e_;
      mean_e_ += d2 / disp_n_;
      m2_e_ += d2 * (de - mean_e_);
    } else {
      // Una nuova sosta deve iniziare una nuova misura, senza campioni in movimento.
      disp_n_ = 0;
    }
  }

  void on_sat_(const uint8_t *p, uint16_t len, uint32_t now) {
    int num = p[5];
    int avail = (len - 8) / 12;
    if (num > avail)
      num = avail;
    if (num > MAX_SATS)
      num = MAX_SATS;
    for (int i = 0; i < num; i++) {
      const uint8_t *q = p + 8 + 12 * i;
      uint32_t flags = u4(q + 8);
      sats_[i] = Sat{q[0], q[1], q[2], static_cast<int8_t>(q[3]), i2(q + 4), (flags & 0x08) != 0, (flags & 0x40) != 0};
    }
    n_sats_ = num;
    have_sat_ = true;
    last_sat_ms_ = now;
  }

  static void copy_str_(char *dst, size_t cap, const uint8_t *src, size_t n) {
    size_t i = 0;
    for (; i < n && i + 1 < cap && src[i] != 0; i++)
      dst[i] = (src[i] >= 32 && src[i] < 127) ? static_cast<char>(src[i]) : '?';
    dst[i] = 0;
  }

  void on_ver_(const uint8_t *p, uint16_t len) {
    copy_str_(sw_, sizeof(sw_), p, 30);
    copy_str_(hw_, sizeof(hw_), p + 30, 10);
    mod_[0] = prot_[0] = 0;
    for (int off = 40; off + 30 <= len; off += 30) {
      char ext[31];
      copy_str_(ext, sizeof(ext), p + off, 30);
      if (strncmp(ext, "MOD=", 4) == 0)
        memcpy(mod_, ext, sizeof(ext));
      if (strncmp(ext, "PROTVER", 7) == 0)
        memcpy(prot_, ext, sizeof(ext));
    }
    have_ver_ = true;
  }

  void on_rf_(const uint8_t *p, uint16_t len, uint32_t now) {
    int n = p[1];
    if (n > 2)
      n = 2;
    int avail = (len - 4) / 24;
    if (n > avail)
      n = avail;
    for (int i = 0; i < n; i++) {
      const uint8_t *q = p + 4 + 24 * i;
      rf_[i] = Rf{q[0], q[2], static_cast<uint8_t>(q[1] & 0x03), q[16], u2(q + 12), u2(q + 14)};
    }
    n_rf_ = n;
    have_rf_ = true;
    last_rf_ms_ = now;
  }

  void on_valget_(const uint8_t *p, uint16_t len) {
    size_t off = 4;
    while (off + 4 <= len) {
      uint32_t key = u4(p + off);
      off += 4;
      static const uint8_t SIZES[8] = {0, 1, 1, 2, 4, 8, 0, 0};
      size_t sz = SIZES[(key >> 28) & 0x07];
      if (sz == 0 || off + sz > len)
        break;
      uint32_t val = 0;
      for (size_t b = 0; b < sz && b < 4; b++)
        val |= static_cast<uint32_t>(p[off + b]) << (8 * b);
      off += sz;
      for (CfgItem &c : cfg_) {
        if (c.key == key) {
          c.value = val;
          c.received = true;
        }
      }
    }
    for (int g = 0; g < CFG_GROUPS; g++) {
      bool complete = true;
      for (const CfgItem &c : cfg_)
        if (c.group == g && !c.received) complete = false;
      if (complete) group_state_[g] = 1;
    }
    pending_group_ = -1;
  }

  bool sats_fresh_(uint32_t now) const { return have_sat_ && now - last_sat_ms_ < 5000; }

  static const char *gnss_name_(uint8_t g) {
    static const char *const N[GNSS_IDS] = {"GPS", "SBAS", "Galileo", "BeiDou", "IMES", "QZSS", "GLONASS"};
    return g < GNSS_IDS ? N[g] : "?";
  }
  static char gnss_letter_(uint8_t g) {
    static const char L[GNSS_IDS] = {'G', 'S', 'E', 'C', 'I', 'J', 'R'};
    return g < GNSS_IDS ? L[g] : '?';
  }
  static const char *dyn_name_(uint32_t v) {
    static const char *const N[] = {"portatile", "?",       "fermo",   "pedone",  "auto", "mare",
                                    "aereo<1g",  "aereo<2g", "aereo<4g", "polso", "bici"};
    return v < 11 ? N[v] : "?";
  }
  static void msg_name_(uint8_t cls, uint8_t id, char *out, size_t cap) {
    struct N {
      uint8_t c, i;
      const char *n;
    };
    static const N T[] = {{0x01, 0x07, "NAV-PVT"},    {0x01, 0x35, "NAV-SAT"},    {0x01, 0x04, "NAV-DOP"},
                          {0x01, 0x03, "NAV-STATUS"}, {0x01, 0x43, "NAV-SIG"},    {0x01, 0x61, "NAV-EOE"},
                          {0x01, 0x21, "NAV-TIMEUTC"}, {0x01, 0x02, "NAV-POSLLH"}, {0x01, 0x12, "NAV-VELNED"},
                          {0x0A, 0x04, "MON-VER"},    {0x0A, 0x38, "MON-RF"},     {0x05, 0x01, "ACK-ACK"},
                          {0x05, 0x00, "ACK-NAK"},    {0x06, 0x8B, "CFG-VALGET"}};
    for (const N &t : T) {
      if (t.c == cls && t.i == id) {
        snprintf(out, cap, "%s", t.n);
        return;
      }
    }
    snprintf(out, cap, "%02X-%02X", cls, id);
  }

  Parser parser_;
  uint32_t exp_rate_{25}, exp_period_ms_{40}, exp_baud_{230400};

  Pvt pvt_;
  bool got_byte_{false}, have_frame_{false}, have_pvt_{false}, have_prev_{false};
  uint32_t last_byte_ms_{0}, last_frame_ms_{0}, last_pvt_ms_{0};

  uint64_t bytes_{0};
  uint32_t win_start_{0}, stats_start_{0}, win_bytes_{0}, win_pvt_{0}, win_frames_base_{0};
  uint32_t win_dt_n_{0}, win_dt_sum_{0}, win_dt_min_{UINT32_MAX}, win_dt_max_{0};
  float bytes_s_{0}, frames_s_{0}, pvt_hz_{0}, dt_avg_{0};
  uint32_t dt_min_{0}, dt_max_{0}, dt_worst_{0};
  uint32_t pvt_count_{0}, lost_epochs_{0}, time_anomalies_{0}, rx_saturations_{0}, loop_gap_max_{0};
  uint32_t last_error_total_{0}, last_error_ms_{0};
  bool had_error_{false};

  MsgStat msgs_[MAX_MSG_TYPES];
  int n_msgs_{0};

  int32_t max_speed_{0}, ref_lat_{0}, ref_lon_{0};
  uint32_t disp_n_{0};
  double mean_n_{0}, mean_e_{0}, m2_n_{0}, m2_e_{0};

  Sat sats_[MAX_SATS];
  int n_sats_{0};
  bool have_sat_{false};
  uint32_t last_sat_ms_{0};

  bool have_dop_{false}, have_status_{false};
  uint16_t h_dop_{0}, v_dop_{0};
  uint32_t ttff_ms_{0}, last_dop_ms_{0}, last_status_ms_{0};

  bool have_ver_{false};
  char sw_[31]{}, hw_[11]{}, mod_[31]{}, prot_[31]{};

  Rf rf_[2]{};
  int n_rf_{0};
  bool have_rf_{false};
  uint32_t last_rf_ms_{0};

  CfgItem cfg_[CFG_ITEMS];
  uint8_t group_state_[CFG_GROUPS]{};  // 0 in attesa, 1 letto, 2 rifiutato
  uint8_t group_attempts_[CFG_GROUPS]{};
  int pending_group_{-1};
};

}  // namespace ubx
