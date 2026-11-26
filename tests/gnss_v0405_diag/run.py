#!/usr/bin/env python3
"""Reference comparison: config trace and parser outputs versus original V0.40.5."""
from pathlib import Path
import subprocess
import tempfile
import sys
import re
import yaml

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'firmware/rlcd-42-3-colori'
REF = BASE / 'GOATS_V0405_BOOT_FAST_FONT_TEST/components/goats_spi_diag'
VERSION = sys.argv[1] if len(sys.argv)>1 else '2'
assert VERSION in ['1','2','3']
DIAG = BASE / f'GOATS_V0405_GPS_DIAG{VERSION}/components/goats_spi_diag'
assert (REF/'goats_m9n_cfg.h').read_bytes() == (DIAG/'goats_m9n_cfg.h').read_bytes()
for filename in ['goats_laptimer.h','goats_lap_storage.h','goats_track_catalog.h',
                 'goats_font_bitmap.h','goats_layout39_font.h','goats_speed_95.h','__init__.py']:
    assert (REF/filename).read_bytes() == (DIAG/filename).read_bytes(), filename
old = yaml.safe_load((BASE/'GOATS_V0405_BOOT_FAST_FONT_TEST/v0405_boot_fast_font_test.yaml').read_text())
new = yaml.safe_load((BASE/f'goats_42_v0405_gps_diag{VERSION}.yaml').read_text())
for section in ['esp32','logger','uart','goats_spi_diag']:
    assert old[section] == new[section], section
src = (REF/'goats_spi_diag.cpp').read_text()
dst = (DIAG/'goats_spi_diag.cpp').read_text()
for first, last in [('void GoatsSpiDiag::controller_init_()', '#include "goats_font_bitmap.h"'),
                    ('void GoatsSpiDiag::gps_poll_()', 'void GoatsSpiDiag::menu_draw_()'),
                    ('void GoatsSpiDiag::setup()', 'void GoatsSpiDiag::loop()')]:
    assert src[src.index(first):src.index(last)] == dst[dst.index(first):dst.index(last)], first
# Preserve initial screen, NVS begin, UART config and original order/timing.
first = 'void GoatsSpiDiag::loop()'
last = '   status_draw_();clock_();auxiliaries_();\n }\n if(stage_!=7)return;'
assert src[src.index(first):src.index(last)] == dst[dst.index(first):dst.index('   gps_diag_draw_();last_ui_=millis();\n }\n if(stage_!=7)return;')]

with tempfile.TemporaryDirectory(prefix='v0405-diag-test-') as tmp:
    p = Path(tmp)
    (p/'esphome/components/uart').mkdir(parents=True)
    (p/'Arduino.h').write_text('''#pragma once
#include <cstdint>
#include <cstdio>
#include <vector>
inline uint32_t clock_ms=0;
inline std::vector<uint32_t> delays;
inline uint32_t millis(){return clock_ms;}
inline void delay(uint32_t ms){delays.push_back(ms);clock_ms+=ms;}
''')
    (p/'esphome/components/uart/uart.h').write_text('''#pragma once
#include <cstdint>
#include <cstddef>
#include <vector>
namespace esphome { namespace uart {
struct UARTComponent {
  uint32_t baud=38400, reads=0; size_t at=0;
  std::vector<uint8_t> rx;
  std::vector<uint32_t> bauds;
  std::vector<std::vector<uint8_t>> writes;
  void set_baud_rate(uint32_t b){baud=b;}
  void load_settings(){bauds.push_back(baud);}
  void write_array(const uint8_t *p,size_t n){writes.emplace_back(p,p+n);}
  void flush(){}
  size_t available()const{return rx.size()-at;}
  bool read_byte(uint8_t *p){if(!available())return false;*p=rx[at++];++reads;return true;}
}; }}
''')
    source = r'''
#include <cassert>
#include <cstring>
#include <iostream>
#define goats_cfg reference_cfg
#include "REF/goats_m9n_cfg.h"
#undef goats_cfg
#include "DIAG/goats_m9n_cfg.h"
#define goats_m9n reference_m9n
#include "REF/goats_ubx_m9n_ak97_full.h"
#undef goats_m9n
#include "DIAG/goats_ubx_m9n_ak97_full.h"
using UART=esphome::uart::UARTComponent;
namespace esphome {
 uint32_t millis(){return clock_ms-500;}
 namespace goats_spi_diag { uint32_t display_now(){return DISPLAY_NOW_EXPR;} }
}

void compare_state(){
 const auto &a=reference_m9n::state;const auto &b=goats_m9n::state;
 assert(a.fix==b.fix && a.used_sats==b.used_sats && a.visible_sats==b.visible_sats);
 assert(a.speed_kmh==b.speed_kmh && a.heading_deg==b.heading_deg && a.hdop==b.hdop);
 assert(a.latitude==b.latitude && a.longitude==b.longitude && a.pvt_hz==b.pvt_hz);
 assert(a.last_pvt_ms==b.last_pvt_ms && a.date_text==b.date_text && a.time_text==b.time_text);
 assert(reference_m9n::pending_samples.size()==goats_m9n::pending_samples.size());
 for(size_t i=0;i<goats_m9n::pending_samples.size();i++){
  const auto &x=reference_m9n::pending_samples[i];const auto &y=goats_m9n::pending_samples[i];
  assert(x.now_ms==y.now_ms && x.gnss_itow_ms==y.gnss_itow_ms && x.fix==y.fix);
  assert(x.satellites==y.satellites && x.latitude==y.latitude && x.longitude==y.longitude);
  assert(x.speed_kmh==y.speed_kmh && x.heading_deg==y.heading_deg);
 }
}
void feed(const std::vector<uint8_t>& bytes,uint32_t now){
 clock_ms=now;
 UART a,b;a.rx=b.rx=bytes;
 reference_m9n::poll(&a);goats_m9n::poll(&b);
 assert(a.reads==b.reads && b.reads==bytes.size());
 assert(a.writes.empty() && b.writes.empty());compare_state();
}
int main(){
 // Regression: both APIs exist, but ESPHome tick epoch differs from Arduino's.
 clock_ms=1000;
 goats_gps_diag::Counters timing;
 timing.byte(0xb5,::millis());
 std::vector<uint8_t> dummy(92);
 timing.frame(1,7,dummy.data(),dummy.size(),::millis());
 const auto display_now=esphome::goats_spi_diag::display_now();
 if(TEST_CLOCK_FIXED){
   assert(display_now==1000 && display_now-timing.last_pvt_ms==0);
   assert(std::strcmp(timing.status(display_now,false),"COMUNICAZIONE OK - NO FIX")==0);
 }else{
   assert(display_now==500 && uint32_t(display_now-timing.last_pvt_ms)>3000);
   assert(std::strcmp(timing.status(display_now,false),"FLUSSO INTERROTTO")==0);
 }
 clock_ms=0;
 UART a,b;
 reference_cfg::configure(a);const auto expected_delays=delays;
 delays.clear();clock_ms=0;goats_cfg::configure(b);
 assert(a.writes==b.writes && a.bauds==b.bauds && delays==expected_delays);
 assert(b.bauds==std::vector<uint32_t>({38400,9600,115200,230400,230400}));
 assert(b.writes.size()==17 && clock_ms==2430);
 auto &d=goats_gps_diag::counters;
 assert(std::strcmp(d.status(0,false),"NESSUN BYTE DAL GPS")==0);
 // NMEA/noise bytes are observed but do not become valid UBX.
 feed({'$','G','P','G','G','A',',','0','*','0','0','\r','\n'},100);
 assert(d.bytes==13 && d.frames==0 && d.raw_size==12);
 assert(std::strcmp(d.status(100,false),"BYTE RX, NESSUN UBX VALIDO")==0);
 auto ack=goats_m9n::frame(5,1,{6,0x8a});
 feed(ack,200);assert(d.ack==1 && d.frames==1 && d.ack_class==6 && d.ack_id==0x8a);
 auto nak=goats_m9n::frame(5,0,{6,1});feed(nak,210);assert(d.nak==1 && !d.last_ack_positive);
 auto broken=ack;broken.back()^=1;feed(broken,220);assert(d.checksum_errors==1 && d.frames==2);
 feed({0xb5,0x62,1,7,0xff,0xff},230);assert(d.oversize==1);
 assert(std::strcmp(d.status(230,false),"UBX OK, NAV-PVT ASSENTE")==0);
 std::vector<uint8_t> nav(92);nav[4]=0xea;nav[5]=7;nav[6]=11;nav[7]=26;nav[8]=12;nav[11]=3;
 // Same NAV-PVT burst fed through both parsers, including fragmentation, no fix and fix.
 for(unsigned i=0;i<80;i++){
  uint32_t tow=1000+40*i;for(unsigned j=0;j<4;j++)nav[j]=uint8_t(tow>>(8*j));
  nav[20]=i<4?0:3;nav[21]=i<4?0:1;nav[23]=i<4?0:12;
  auto f=goats_m9n::frame(1,7,nav);
  feed(std::vector<uint8_t>(f.begin(),f.begin()+3),1000+40*i);
  feed(std::vector<uint8_t>(f.begin()+3,f.end()),1000+40*i);
  if(i==0)assert(std::strcmp(d.status(1000,false),"COMUNICAZIONE OK - NO FIX")==0);
 }
 assert(d.pvt==80 && d.max_pvt_gap_ms==40 && goats_m9n::pending_samples.size()==64);
 assert(std::strcmp(d.status(clock_ms,true),"COMUNICAZIONE OK - FIX SI")==0);
 std::vector<uint8_t> dop(18);dop[12]=75;feed(goats_m9n::frame(1,4,dop),4200);
 std::vector<uint8_t> sat(8);sat[5]=21;feed(goats_m9n::frame(1,0x35,sat),4200);
 assert(d.dop==1 && d.sat==1 && goats_m9n::state.hdop==0.75f && goats_m9n::state.visible_sats==21);
 feed({},6000);assert(!goats_m9n::state.fix);
 assert(std::strcmp(d.status(6000,false),"NAV-PVT INTERROTTO")==0);
 feed({},8000);assert(std::strcmp(d.status(8000,false),"FLUSSO INTERROTTO")==0);
 assert(goats_m9n::state.pvt_hz==0);
 d={};d.byte(0,0xfffffff0);d.frame(1,7,nav.data(),nav.size(),0xfffffff0);
 assert(std::strcmp(d.status(20,false),"COMUNICAZIONE OK - NO FIX")==0);
 d.frame(1,7,nav.data(),nav.size(),24);assert(d.max_pvt_gap_ms==40);
 std::cout<<"PASS: original config trace, identical navigation/parser outputs, single reader, counters, malformed frames, stale/no-fix, timer wrap and separate Arduino/ESPHome clock epochs\n";
}
'''.replace('REF/',str(REF)+'/').replace('DIAG/',str(DIAG)+'/')
    clock_expr=re.search(r'const uint32_t now=([^;]+);',dst[dst.index('void GoatsSpiDiag::gps_diag_draw_()'):]).group(1)
    source=source.replace('DISPLAY_NOW_EXPR',clock_expr).replace('TEST_CLOCK_FIXED','true' if VERSION in ['2','3'] else 'false')
    (p/'reference_cfg.h').write_text((REF/'goats_m9n_cfg.h').read_text().replace('#pragma once', ''))
    source=source.replace(str(REF/'goats_m9n_cfg.h'),str(p/'reference_cfg.h'))
    (p/'test.cpp').write_text(source)
    subprocess.run(['g++','-std=c++17','-g','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I',str(p),str(p/'test.cpp'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True)
print('PASS: original UART/framework/logger/partitions, config, boot order, GPS loop, graphics driver and inherited files')
