#pragma once
#include "esphome.h"
#include <vector>
#include <cstdint>
#include <cstring>

namespace goats_ubx_v11 {

static inline void checksum(const uint8_t *p, size_t n, uint8_t &a, uint8_t &b) {
  a = 0; b = 0;
  for (size_t i=0;i<n;i++) { a = uint8_t(a + p[i]); b = uint8_t(b + a); }
}

static inline std::vector<uint8_t> frame(uint8_t cls, uint8_t id,
                                         const std::vector<uint8_t> &pl) {
  std::vector<uint8_t> f{0xB5,0x62,cls,id,uint8_t(pl.size()),uint8_t(pl.size()>>8)};
  f.insert(f.end(), pl.begin(), pl.end());
  uint8_t a=0,b=0; checksum(f.data()+2, f.size()-2, a, b);
  f.push_back(a); f.push_back(b);
  return f;
}

static inline void put_key_u1(std::vector<uint8_t> &p, uint32_t key, uint8_t v) {
  p.push_back(uint8_t(key)); p.push_back(uint8_t(key>>8));
  p.push_back(uint8_t(key>>16)); p.push_back(uint8_t(key>>24)); p.push_back(v);
}
static inline void put_key_u2(std::vector<uint8_t> &p, uint32_t key, uint16_t v) {
  p.push_back(uint8_t(key)); p.push_back(uint8_t(key>>8));
  p.push_back(uint8_t(key>>16)); p.push_back(uint8_t(key>>24));
  p.push_back(uint8_t(v)); p.push_back(uint8_t(v>>8));
}
static inline void put_key_u4(std::vector<uint8_t> &p, uint32_t key, uint32_t v) {
  p.push_back(uint8_t(key)); p.push_back(uint8_t(key>>8));
  p.push_back(uint8_t(key>>16)); p.push_back(uint8_t(key>>24));
  p.push_back(uint8_t(v)); p.push_back(uint8_t(v>>8));
  p.push_back(uint8_t(v>>16)); p.push_back(uint8_t(v>>24));
}

static inline void send(esphome::uart::UARTComponent *u, const std::vector<uint8_t> &f) {
  if (u && !f.empty()) u->write_array(f.data(), f.size());
}

// M9 configuration in RAM. 230400 is also configured explicitly so the
// receiver configuration is deterministic on every GOATS RT boot.
// CFG-UART1-BAUDRATE  0x40520001 U4
// CFG-UART1-INPROT-UBX 0x10730001 L
// CFG-UART1-OUTPROT-UBX 0x10740001 L
// CFG-UART1-OUTPROT-NMEA 0x10740002 L
// CFG-RATE-MEAS 0x30210001 U2 = 40 ms (25 Hz)
// CFG-RATE-NAV  0x30210002 U2 = 1
// CFG-NAVSPG-INFIL_MAXSVS 0x201100A2 U1 = 32
static inline void configure_m9n(esphome::uart::UARTComponent *u) {
  if (!u) return;

  // Keep UBX input/output alive while disabling NMEA output.
  std::vector<uint8_t> p{0x00,0x01,0x00,0x00}; // version 0, RAM layer
  put_key_u4(p, 0x40520001u, 230400u);
  put_key_u1(p, 0x10730001u, 1);
  put_key_u1(p, 0x10740001u, 1);
  put_key_u1(p, 0x10740002u, 0);
  put_key_u2(p, 0x30210001u, 40);
  put_key_u2(p, 0x30210002u, 1);
  put_key_u1(p, 0x201100A2u, 32);

  // SBAS explicitly enabled by GOATS RT.
  // Use ranging, differential/ionosphere corrections and integrity.
  // Test-mode SBAS satellites are intentionally not accepted.
  put_key_u1(p, 0x10310020u, 1);  // CFG-SIGNAL-SBAS_ENA
  put_key_u1(p, 0x10360002u, 1);  // CFG-SBAS-USE_RANGING
  put_key_u1(p, 0x10360003u, 1);  // CFG-SBAS-USE_DIFFCORR
  put_key_u1(p, 0x10360004u, 1);  // CFG-SBAS-USE_INTEGRITY
  put_key_u1(p, 0x10360005u, 0);  // CFG-SBAS-USE_TESTMODE

  send(u, frame(0x06,0x8A,p));
  delay(120);

  // Message rates on UART1. Legacy CFG-MSG is retained by M9 for message
  // configuration and avoids hard-coding a large MSGOUT key table here.
  auto cfg_msg = [&](uint8_t cls, uint8_t id, uint8_t uart1_rate) {
    // rates: I2C, UART1, UART2, USB, SPI, reserved
    std::vector<uint8_t> m{cls,id,0,uart1_rate,0,0,0,0};
    send(u, frame(0x06,0x01,m));
    delay(35);
  };
  cfg_msg(0x01,0x07,1);   // UBX-NAV-PVT every nav epoch = 25 Hz
  cfg_msg(0x01,0x04,1);   // UBX-NAV-DOP every nav epoch = 25 Hz
  cfg_msg(0x01,0x35,25);  // UBX-NAV-SAT every 25 epochs = 1 Hz
}

static inline uint16_t u2(const std::vector<uint8_t>&p,size_t o) {
  return (o+2<=p.size()) ? uint16_t(p[o]) | (uint16_t(p[o+1])<<8) : 0;
}
static inline uint32_t u4(const std::vector<uint8_t>&p,size_t o) {
  return (o+4<=p.size()) ? uint32_t(p[o]) | (uint32_t(p[o+1])<<8) |
    (uint32_t(p[o+2])<<16) | (uint32_t(p[o+3])<<24) : 0;
}
static inline int32_t i4(const std::vector<uint8_t>&p,size_t o) {
  return static_cast<int32_t>(u4(p,o));
}

} // namespace goats_ubx_v11
