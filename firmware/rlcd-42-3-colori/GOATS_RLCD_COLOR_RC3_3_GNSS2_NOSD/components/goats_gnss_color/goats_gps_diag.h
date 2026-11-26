#pragma once
#ifdef GOATS_GNSS_COLOR_IMPLEMENTATION
#pragma once
#include <cstdint>
#include <cstddef>

// Passive observer: never reads UART, never sends or changes GNSS settings.
namespace goats_gps_diag {
struct Counters {
  uint32_t bytes{0}, frames{0}, checksum_errors{0}, oversize{0};
  uint32_t pvt{0}, dop{0}, sat{0}, ack{0}, nak{0};
  uint32_t last_byte_ms{0}, last_pvt_ms{0}, max_pvt_gap_ms{0};
  uint8_t raw[12]{};
  uint8_t raw_size{0}, last_class{0}, last_id{0}, ack_class{0}, ack_id{0};
  bool last_ack_positive{false};
  void byte(uint8_t value, uint32_t now) {
    ++bytes; last_byte_ms=now;
    if(raw_size<sizeof(raw))raw[raw_size++]=value;
  }
  void frame(uint8_t cls, uint8_t id, const uint8_t *p, size_t size, uint32_t now) {
    ++frames; last_class=cls; last_id=id;
    if(cls==1 && id==7 && size>=92) {
      if(pvt) {const uint32_t gap=now-last_pvt_ms;if(gap>max_pvt_gap_ms)max_pvt_gap_ms=gap;}
      ++pvt; last_pvt_ms=now;
    } else if(cls==1 && id==4 && size>=18)++dop;
    else if(cls==1 && id==0x35 && size>=8)++sat;
    else if(cls==5 && (id==0 || id==1) && size>=2) {
      if(id==1)++ack;else ++nak;
      ack_class=p[0];ack_id=p[1];last_ack_positive=id==1;
    }
  }
  const char *status(uint32_t now, bool fix) const {
    if(!bytes)return "NESSUN BYTE DAL GPS";
    if(uint32_t(now-last_byte_ms)>3000)return "FLUSSO INTERROTTO";
    if(!frames)return "BYTE RX, NESSUN UBX VALIDO";
    if(!pvt)return "UBX OK, NAV-PVT ASSENTE";
    if(uint32_t(now-last_pvt_ms)>1500)return "NAV-PVT INTERROTTO";
    return fix?"COMUNICAZIONE OK - FIX SI":"COMUNICAZIONE OK - NO FIX";
  }
};
inline Counters counters;
} // namespace goats_gps_diag

#endif // GOATS_GNSS_COLOR_IMPLEMENTATION
