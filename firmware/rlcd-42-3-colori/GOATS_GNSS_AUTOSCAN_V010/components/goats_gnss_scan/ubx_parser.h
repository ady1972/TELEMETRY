#pragma once
// Parser UBX a macchina a stati. Nessuna dipendenza da ESPHome (testabile su PC).

#include <cstddef>
#include <cstdint>

namespace ubx {

// NAV-SAT: 8 + 12*N, NAV-SIG: 8 + 16*N. 2048 byte bastano per 127 voci NAV-SIG.
static constexpr size_t MAX_PAYLOAD = 2048;

struct Frame {
  uint8_t cls;
  uint8_t id;
  uint16_t len;
  const uint8_t *payload;
};

struct ParserStats {
  uint32_t frames_ok{0};
  uint32_t checksum_errors{0};
  uint32_t length_errors{0};
  uint32_t junk_bytes{0};  // byte fuori da un frame UBX (contati solo dopo il primo frame valido)
  uint32_t nmea_hits{0};   // intestazioni NMEA ("$Gxxxx,") fuori dai frame UBX
};

class Parser {
 public:
  // Ritorna true quando il byte completa un frame con checksum corretto.
  bool feed(uint8_t b) {
    switch (state_) {
      case ST_SYNC1:
        if (b == 0xB5) {
          state_ = ST_SYNC2;
        } else {
          junk_(b);
        }
        return false;
      case ST_SYNC2:
        if (b == 0x62) {
          state_ = ST_CLS;
          ck_a_ = ck_b_ = 0;
        } else {
          junk_(0xB5);
          if (b == 0xB5)
            return false;  // resta in ST_SYNC2
          state_ = ST_SYNC1;
          junk_(b);
        }
        return false;
      case ST_CLS:
        cls_ = b;
        add_(b);
        state_ = ST_ID;
        return false;
      case ST_ID:
        id_ = b;
        add_(b);
        state_ = ST_LEN1;
        return false;
      case ST_LEN1:
        len_ = b;
        add_(b);
        state_ = ST_LEN2;
        return false;
      case ST_LEN2:
        len_ |= static_cast<uint16_t>(b) << 8;
        add_(b);
        pos_ = 0;
        if (len_ > MAX_PAYLOAD) {
          stats.length_errors++;
          state_ = ST_SYNC1;
        } else {
          state_ = len_ == 0 ? ST_CKA : ST_PAYLOAD;
        }
        return false;
      case ST_PAYLOAD:
        buf_[pos_++] = b;
        add_(b);
        if (pos_ >= len_)
          state_ = ST_CKA;
        return false;
      case ST_CKA:
        if (b != ck_a_) {
          stats.checksum_errors++;
          state_ = b == 0xB5 ? ST_SYNC2 : ST_SKIP;
        } else {
          state_ = ST_CKB;
        }
        return false;
      case ST_SKIP:  // secondo byte di checksum di un frame gia' scartato
        state_ = b == 0xB5 ? ST_SYNC2 : ST_SYNC1;
        return false;
      case ST_CKB:
        if (b != ck_b_) {
          stats.checksum_errors++;
          state_ = b == 0xB5 ? ST_SYNC2 : ST_SYNC1;
          return false;
        }
        state_ = ST_SYNC1;
        stats.frames_ok++;
        synced_ = true;
        return true;
    }
    return false;
  }

  Frame frame() const { return Frame{cls_, id_, len_, buf_}; }

  void reset() {
    state_ = ST_SYNC1;
    stats = ParserStats{};
    synced_ = false;
    for (uint8_t &c : hist_)
      c = 0;
  }

  ParserStats stats;

 private:
  enum State : uint8_t { ST_SYNC1, ST_SYNC2, ST_CLS, ST_ID, ST_LEN1, ST_LEN2, ST_PAYLOAD, ST_CKA, ST_CKB, ST_SKIP };

  void add_(uint8_t b) {
    ck_a_ = static_cast<uint8_t>(ck_a_ + b);
    ck_b_ = static_cast<uint8_t>(ck_b_ + ck_a_);
  }
  void junk_(uint8_t b) {
    if (synced_)
      stats.junk_bytes++;
    for (int i = 0; i < 6; i++)
      hist_[i] = hist_[i + 1];
    hist_[6] = b;
    // Es. "$GNRMC,": un criterio stretto evita falsi positivi con baud errato.
    if (b == ',' && hist_[0] == '$' && hist_[1] == 'G' && upper_(hist_[2]) && upper_(hist_[3]) && upper_(hist_[4]) &&
        upper_(hist_[5]))
      stats.nmea_hits++;
  }
  static bool upper_(uint8_t c) { return c >= 'A' && c <= 'Z'; }

  State state_{ST_SYNC1};
  uint8_t cls_{0}, id_{0}, ck_a_{0}, ck_b_{0};
  uint8_t hist_[7]{};
  uint16_t len_{0}, pos_{0};
  bool synced_{false};
  uint8_t buf_[MAX_PAYLOAD];
};

// Costruisce un frame UBX in out (deve avere almeno len + 8 byte). Ritorna la lunghezza totale.
inline size_t build_frame(uint8_t *out, uint8_t cls, uint8_t id, const uint8_t *payload, uint16_t len) {
  out[0] = 0xB5;
  out[1] = 0x62;
  out[2] = cls;
  out[3] = id;
  out[4] = len & 0xFF;
  out[5] = len >> 8;
  for (uint16_t i = 0; i < len; i++)
    out[6 + i] = payload[i];
  uint8_t a = 0, b = 0;
  for (size_t i = 2; i < static_cast<size_t>(len) + 6; i++) {
    a = static_cast<uint8_t>(a + out[i]);
    b = static_cast<uint8_t>(b + a);
  }
  out[6 + len] = a;
  out[7 + len] = b;
  return static_cast<size_t>(len) + 8;
}

inline uint16_t u2(const uint8_t *p) { return static_cast<uint16_t>(p[0] | (p[1] << 8)); }
inline int16_t i2(const uint8_t *p) { return static_cast<int16_t>(u2(p)); }
inline uint32_t u4(const uint8_t *p) {
  return static_cast<uint32_t>(p[0]) | (static_cast<uint32_t>(p[1]) << 8) | (static_cast<uint32_t>(p[2]) << 16) |
         (static_cast<uint32_t>(p[3]) << 24);
}
inline int32_t i4(const uint8_t *p) { return static_cast<int32_t>(u4(p)); }

}  // namespace ubx
