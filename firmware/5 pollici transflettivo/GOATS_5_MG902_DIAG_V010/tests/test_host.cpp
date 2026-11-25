// Test su PC del parser e della diagnostica con frame UBX sintetici.
//   g++ -std=c++17 -Wall -Wextra -fsanitize=address,undefined tests/test_host.cpp -o /tmp/ubxtest && /tmp/ubxtest
#include <cassert>
#include <cstdlib>
#include <iostream>
#include <vector>

#include "../components/ubx_diag/gnss_diag.h"

using Bytes = std::vector<uint8_t>;
static int checks = 0, failures = 0;
#define CHECK(x) \
  do { \
    checks++; \
    if (!(x)) { \
      failures++; \
      std::cout << "FALLITO riga " << __LINE__ << ": " #x "\n"; \
    } \
  } while (0)

static void put(Bytes &p, size_t off, uint32_t v, int n) {
  for (int i = 0; i < n; i++)
    p[off + i] = (v >> (8 * i)) & 0xFF;
}
static Bytes frame(uint8_t c, uint8_t i, const Bytes &p) {
  Bytes o(p.size() + 8);
  ubx::build_frame(o.data(), c, i, p.data(), p.size());
  return o;
}
static Bytes pvt(uint32_t itow, bool fix = true) {
  Bytes p(92, 0);
  put(p, 0, itow, 4);
  put(p, 4, 2026, 2);
  p[6] = 11, p[7] = 25, p[8] = 13, p[9] = 5, p[10] = 42;
  p[11] = 0x07;
  p[20] = fix ? 3 : 0;
  p[21] = fix ? 0x03 : 0;
  p[23] = 29;
  put(p, 24, 124964000, 4);   // lon
  put(p, 28, 419028000, 4);   // lat
  put(p, 36, 57300, 4);       // hMSL mm
  put(p, 40, 620, 4);         // hAcc mm
  put(p, 44, 910, 4);
  put(p, 56, static_cast<uint32_t>(-150), 4);
  put(p, 60, 27778, 4);       // 100 km/h
  put(p, 64, 8750000, 4);
  put(p, 68, 120, 4);
  put(p, 76, 112, 2);
  return frame(0x01, 0x07, p);
}
static Bytes navsat() {
  Bytes p(8 + 12 * 34, 0);
  p[4] = 1, p[5] = 34;
  for (int i = 0; i < 34; i++) {
    size_t o = 8 + 12 * i;
    uint8_t g = i < 11 ? 0 : i < 18 ? 6 : i < 25 ? 2 : i < 32 ? 3 : 1;
        p[o] = g;
    p[o + 1] = g == 1 ? 123 + (i - 32) * 13 : i + 1;
    p[o + 2] = 47 - i;
    p[o + 3] = 70 - i;
    put(p, o + 4, i * 10, 2);
    put(p, o + 8, (i < 28 ? 0x08 : 0) | (i < 20 ? 0x40 : 0), 4);
  }
  return frame(0x01, 0x35, p);
}
static Bytes monver() {
  Bytes p(40 + 4 * 30, 0);
  auto s = [&](size_t off, const char *t) { memcpy(&p[off], t, strlen(t)); };
  s(0, "EXT CORE 4.04 (7f89f7)");
  s(30, "00190000");
  s(40, "ROM BASE 0x118B2060");
  s(70, "FWVER=SPG 4.04");
  s(100, "PROTVER=32.01");
  s(130, "MOD=NEO-M9N");
  return frame(0x0A, 0x04, p);
}
static Bytes monrf() {
  Bytes p(4 + 24, 0);
  p[1] = 1;
  p[5] = 1, p[6] = 2, p[7] = 1;
  put(p, 4 + 12, 95, 2);
  put(p, 4 + 14, 4096, 2);
  p[4 + 16] = 12;
  return frame(0x0A, 0x38, p);
}
static Bytes valget(const std::vector<std::pair<uint32_t, uint32_t>> &kv) {
  Bytes p = {1, 0, 0, 0};
  for (auto &e : kv) {
    for (int b = 0; b < 4; b++)
      p.push_back((e.first >> (8 * b)) & 0xFF);
    static const int SZ[8] = {0, 1, 1, 2, 4, 8, 0, 0};
    for (int b = 0; b < SZ[(e.first >> 28) & 7]; b++)
      p.push_back((e.second >> (8 * b)) & 0xFF);
  }
  return frame(0x06, 0x8B, p);
}

static void send(ubx::GnssDiag &d, const Bytes &b, uint32_t now) {
  // a pezzi irregolari, come arriva da una UART
  size_t i = 0;
  while (i < b.size()) {
    size_t n = std::min<size_t>(1 + rand() % 70, b.size() - i);
    d.feed(b.data() + i, n, now);
    i += n;
  }
}
// ms millisecondi di PVT a 25 Hz
static void run(ubx::GnssDiag &d, uint32_t &t, uint32_t &itow, uint32_t ms, int period = 40) {
  for (uint32_t e = 0; e < ms; e += period) {
    t += period;
    itow += period;
    send(d, pvt(itow), t);
    d.tick(t);
  }
}

int main(int argc, char **) {
  srand(1);
  // 1) flusso pulito a 25 Hz
  static ubx::GnssDiag d;
  uint32_t t = 1000, itow = 300000000;
  d.reset_stats(t);
  CHECK(d.link_level(t) == ubx::LVL_ERR);
  CHECK(d.link_text(t).find("NESSUN BYTE") == 0);
  run(d, t, itow, 20000);
  CHECK(d.pvt_hz() > 24.5f && d.pvt_hz() < 25.5f);
  CHECK(d.lost_epochs() == 0);
  CHECK(d.checksum_errors() == 0);
  CHECK(d.parser_stats().junk_bytes == 0);
  CHECK(d.link_level(t) == ubx::LVL_OK);
  CHECK(d.pvt().num_sv == 29);
  CHECK(std::fabs(d.speed_kmh(t) - 100.0f) < 0.01f);
  CHECK(std::fabs(d.h_acc_m(t) - 0.62f) < 0.001f);
  CHECK(d.fix_text(t) == "FIX 3D DGNSS");
  CHECK(d.fix_position_text(t).find("41.9028000") != std::string::npos);
  CHECK(d.fix_position_text(t).find("12.4964000") != std::string::npos);
  CHECK(d.header_text(t).find("13:05:42 UTC") != std::string::npos);

  // 2) tre epoche mancanti
  itow += 120;
  t += 120;
  run(d, t, itow, 1200);
  CHECK(d.lost_epochs() == 3);
  CHECK(d.link_level(t) == ubx::LVL_WARN);

  // 3) checksum corrotto: contato, il frame successivo passa
  Bytes bad = pvt(itow += 40);
  bad[30] ^= 0x55;
  send(d, bad, t += 40);
  const uint32_t before = d.parser_stats().frames_ok;
  send(d, pvt(itow += 40), t += 40);
  CHECK(d.checksum_errors() == 1);
  CHECK(d.parser_stats().frames_ok == before + 1);
  CHECK(d.lost_epochs() == 4);

  // 4) NMEA mescolato
  const char *nmea = "$GNRMC,130542.00,A,4154.168,N,01229.784,E,0.0,,251126,,,A*00\r\n";
  send(d, Bytes(nmea, nmea + strlen(nmea)), t);
  CHECK(d.parser_stats().nmea_hits == 1);
  CHECK(d.parser_stats().junk_bytes == strlen(nmea));

  // 5) lunghezza assurda
  send(d, Bytes{0xB5, 0x62, 0x01, 0x07, 0xFF, 0xFF}, t);
  CHECK(d.parser_stats().length_errors == 1);
  send(d, pvt(itow += 40), t += 40);
  CHECK(d.pvt().itow == itow);

  // 6) cambio settimana GPS senza falsi errori
  d.reset_stats(t);
  itow = 604800000 - 400;
  send(d, pvt(itow), t);
  for (int i = 0; i < 20; i++) {
    itow = (itow + 40) % 604800000;
    send(d, pvt(itow), t += 40);
  }
  CHECK(d.lost_epochs() == 0);

  // 7) rate sbagliato (10 Hz)
  d.reset_stats(t);
  itow = 1000000;
  run(d, t, itow, 6000, 100);
  CHECK(d.pvt_hz() > 9.5f && d.pvt_hz() < 10.5f);
  CHECK(d.link_text(t).find("RATE ANOMALO") == 0);

  // 8) baud errato: solo rumore
  static ubx::GnssDiag noise;
  noise.reset_stats(0);
  for (uint32_t k = 0; k < 3000; k++) {
    uint8_t buf[64];
    for (auto &b : buf)
      b = rand() & 0xFF;
    noise.feed(buf, sizeof(buf), k);
    noise.tick(k);
  }
  CHECK(noise.link_text(3000).find("BYTE SENZA UBX") == 0);
  CHECK(noise.parser_stats().frames_ok == 0);

  // 9) messaggi ausiliari
  d.reset_stats(t);
  itow = 2000000;
  run(d, t, itow, 6000);
  send(d, navsat(), t);
  send(d, monver(), t);
  send(d, monrf(), t);
  Bytes dop(18, 0);
  put(dop, 10, 98, 2);
  put(dop, 12, 61, 2);
  send(d, frame(0x01, 0x04, dop), t);
  Bytes st(16, 0);
  put(st, 8, 24500, 4);
  send(d, frame(0x01, 0x03, st), t);
  CHECK(d.sat_count() == 34);
  CHECK(d.sat_summary_text(t).find("GPS        11    11") != std::string::npos);
  CHECK(d.module_text(t).find("MOD=NEO-M9N") != std::string::npos);
  CHECK(d.module_text(t).find("ant OK") != std::string::npos);
  CHECK(d.module_text(t).find("AGC 50%") != std::string::npos);
  CHECK(d.fix_quality_text(t).find("0.61") != std::string::npos);
  CHECK(d.fix_quality_text(t).find("24.5 s") != std::string::npos);
  CHECK(d.sat_list_text(t, 0).find("G1  ") != std::string::npos);
  CHECK(!d.sat_list_text(t, 1).empty());

  // 10) configurazione: richiesta, risposta, NAK
  CHECK(d.config_mismatches() == -1);
  uint8_t out[64];
  CHECK(d.next_cfg_group() == 0);
  size_t n = d.build_cfg_poll(0, out);
  CHECK(n == 8 + 4 + 6 * 4);
  CHECK(out[2] == 0x06 && out[3] == 0x8B && out[6] == 0 && out[7] == 0);
  send(d, valget({{0x40520001, 230400}, {0x30210001, 40}, {0x30210002, 1}, {0x10740001, 1}, {0x10740002, 0},
                  {0x20910007, 1}}),
       t);
  CHECK(d.next_cfg_group() == 1);
  d.build_cfg_poll(1, out);
  send(d, valget({{0x1031001f, 1}, {0x10310025, 1}, {0x10310021, 1}, {0x10310022, 0}, {0x10310020, 1},
                  {0x10310024, 1}}),
       t);
  d.build_cfg_poll(2, out);
  send(d, frame(0x05, 0x00, {0x06, 0x8B}), t);
  CHECK(d.next_cfg_group() == -1);
  CHECK(d.config_mismatches() == 1);  // BeiDou disattivato
  CHECK(d.config_text().find("DIVERSO") != std::string::npos);
  CHECK(d.config_text().find("rifiutato") != std::string::npos);
  d.restart_queries();
  CHECK(d.next_cfg_group() == 0);

  // R1: PVT ricevuti a 25 Hz ma iTOW congelato non devono dare LINK OK.
  ubx::GnssDiag frozen;
  frozen.reset_stats(0);
  for (uint32_t ms = 40; ms <= 6000; ms += 40) {
    send(frozen, pvt(100000), ms);
    frozen.tick(ms);
  }
  CHECK(frozen.pvt_hz() > 24.5f);
  CHECK(frozen.link_level(6000) != ubx::LVL_OK);

  // R1: NAV-DOP e NAV-STATUS non devono apparire attuali dopo cinque secondi.
  ubx::GnssDiag aging;
  send(aging, frame(1, 4, dop), 1000);
  send(aging, frame(1, 3, st), 1000);
  CHECK(aging.fix_quality_text(1000).find("vDOP") != std::string::npos);
  CHECK(aging.fix_quality_text(6000).find("vDOP") == std::string::npos);
  CHECK(aging.fix_quality_text(6000).find("TTFF         --") != std::string::npos);

  // R1: dispersione solo a velocita' < 0.5 m/s; una nuova sosta riparte da zero.
  auto stationary = [](uint32_t tow, uint32_t lat) {
    Bytes raw = pvt(tow);
    Bytes payload(raw.begin() + 6, raw.end() - 2);
    put(payload, 60, 0, 4);
    put(payload, 28, lat, 4);
    return frame(1, 7, payload);
  };
  ubx::GnssDiag dispersion;
  send(dispersion, pvt(1000), 1000);
  send(dispersion, pvt(1040), 1040);
  CHECK(dispersion.fix_quality_text(1040).find("2DRMS") == std::string::npos);
  send(dispersion, stationary(1080, 419028000), 1080);
  send(dispersion, stationary(1120, 419028010), 1120);
  CHECK(dispersion.fix_quality_text(1120).find("2DRMS") != std::string::npos);
  send(dispersion, pvt(1160), 1160);
  send(dispersion, stationary(1200, 419038000), 1200);
  CHECK(dispersion.fix_quality_text(1200).find("2DRMS") == std::string::npos);
  CHECK(dispersion.fix_quality_text(2200).find("2DRMS") == std::string::npos);

  // R1: una risposta parziale VALGET lascia in coda solo le chiavi mancanti.
  ubx::GnssDiag partial;
  CHECK(partial.build_cfg_poll(0, out) == 36);
  send(partial, valget({{0x40520001, 230400}}), 1000);
  CHECK(partial.next_cfg_group() == 0);
  CHECK(partial.build_cfg_poll(0, out) == 32);
  CHECK(ubx::u4(out + 10) == 0x30210001);  // non ripetere la chiave gia' letta
  send(partial, valget({{0x30210001, 40}}), 2000);
  CHECK(partial.next_cfg_group() == 0);
  CHECK(partial.build_cfg_poll(0, out) == 28);
  CHECK(partial.next_cfg_group() == 1);  // massimo tre tentativi, nessuna starvation
  CHECK(partial.config_text().find("non letto") != std::string::npos);
  CHECK(partial.build_cfg_poll(0, out) == 0);
  CHECK(partial.build_cfg_poll(-1, out) == 0);
  CHECK(partial.build_cfg_poll(3, out) == 0);
  partial.restart_queries();
  CHECK(partial.next_cfg_group() == 0);
  CHECK(partial.build_cfg_poll(0, out) == 36);
  send(partial, valget({{0x40520001, 230400}, {0x30210001, 40}, {0x30210002, 1},
                      {0x10740001, 1}, {0x10740002, 0}, {0x20910007, 1}}), 3000);
  CHECK(partial.next_cfg_group() == 1);

  // R1: satelliti visti basati su C/N0, assenza/staleness distinta da zero.
  CHECK(partial.sv_seen(3000) == -1);
  send(partial, navsat(), 3000);
  CHECK(partial.sv_seen(3000) == 34);
  CHECK(partial.sv_seen(8000) == -1);

  // 11) fuzz: byte casuali e frame troncati con checksum validi di lunghezza qualsiasi
  static ubx::GnssDiag f;
  f.reset_stats(0);
  const uint8_t ids[][2] = {{1, 7}, {1, 0x35}, {1, 4}, {1, 3}, {0x0A, 4}, {0x0A, 0x38}, {6, 0x8B}, {5, 0}, {9, 9}};
  for (int k = 0; k < 40000; k++) {
    Bytes p(rand() % 300);
    for (auto &b : p)
      b = rand() & 0xFF;
    const uint8_t *id = ids[rand() % 9];
    Bytes fr = frame(id[0], id[1], p);
    if (rand() % 5 == 0)
      fr.resize(rand() % fr.size());
    send(f, fr, k);
    f.tick(k);
    if (k % 1000 == 0) {
      f.header_text(k);
      f.sat_summary_text(k);
      f.sat_list_text(k, 0);
      f.module_text(k);
      f.config_text();
      f.link_messages_text();
      f.link_stats_text(k);
      f.fix_quality_text(k);
      f.fix_position_text(k);
    }
  }
  CHECK(f.parser_stats().frames_ok > 1000);

  // Con argomento "dump": stampa i testi delle pagine (scenario 9).
  if (argc > 1) {
    d.reset_stats(t);
    itow = 3000000;
    run(d, t, itow, 8000);
    send(d, navsat(), t);
    send(d, monver(), t);
    send(d, monrf(), t);
    send(d, frame(0x01, 0x04, dop), t);
    send(d, frame(0x01, 0x03, st), t);
    d.build_cfg_poll(0, out);
    send(d, valget({{0x40520001, 230400}, {0x30210001, 40}, {0x30210002, 1}, {0x10740001, 1}, {0x10740002, 0},
                    {0x20910007, 1}}),
         t);
    d.build_cfg_poll(1, out);
    send(d, valget({{0x1031001f, 1}, {0x10310025, 1}, {0x10310021, 1}, {0x10310022, 1}, {0x10310020, 1},
                    {0x10310024, 0}}),
         t);
    d.build_cfg_poll(2, out);
    send(d, valget({{0x20110021, 4}}), t);
    auto sec = [](const char *k, const std::string &v) { std::cout << "@@" << k << "\n" << v << "\n"; };
    sec("header", d.header_text(t));
    sec("link", d.link_text(t));
    sec("fix_type", d.fix_text(t));
    sec("pos", d.fix_position_text(t));
    sec("qual", d.fix_quality_text(t));
    sec("stats", d.link_stats_text(t));
    sec("msgs", d.link_messages_text());
    sec("sat_sum", d.sat_summary_text(t));
    sec("sat_a", d.sat_list_text(t, 0));
    sec("sat_b", d.sat_list_text(t, 1));
    sec("cfg", d.config_text());
    sec("module", d.module_text(t));
    return failures != 0;
  }
  std::cout << checks - failures << "/" << checks << " verifiche superate\n";
  return failures != 0;
}
