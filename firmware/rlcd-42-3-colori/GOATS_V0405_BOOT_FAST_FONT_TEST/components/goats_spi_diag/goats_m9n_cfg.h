// GOATS GUITION M9N GNSS TEST V1.5.0 - configure M9N in RAM only.
#pragma once
#include "esphome/components/uart/uart.h"
#include <Arduino.h>
#include <cstdint>
#include <vector>
namespace goats_cfg {
using UART = esphome::uart::UARTComponent;
static void write_frame(UART &u,uint8_t cls,uint8_t id,const std::vector<uint8_t> &payload){
  uint16_t size=payload.size();
  std::vector<uint8_t> f={0xB5,0x62,cls,id,(uint8_t)size,(uint8_t)(size>>8)};
  f.insert(f.end(),payload.begin(),payload.end());
  uint8_t a=0,b=0;
  for(size_t i=2;i<f.size();++i){a=(uint8_t)(a+f[i]);b=(uint8_t)(b+a);}
  f.push_back(a);f.push_back(b);
  u.write_array(f.data(),f.size());
  u.flush();
}
static std::vector<uint8_t> ram(){return {0,1,0,0};} // VALSET RAM only (bit0)
static void key_l(std::vector<uint8_t>&p,uint32_t key,bool v){
  for(int i=0;i<4;++i) p.push_back(uint8_t(key>>(8*i)));p.push_back(v?1:0);
}
static void key_u1(std::vector<uint8_t>&p,uint32_t key,uint8_t v){
  for(int i=0;i<4;++i) p.push_back(uint8_t(key>>(8*i)));p.push_back(v);
}
static void key_u2(std::vector<uint8_t>&p,uint32_t key,uint16_t v){
  for(int i=0;i<4;++i) p.push_back(uint8_t(key>>(8*i)));
  p.push_back((uint8_t)v);p.push_back((uint8_t)(v>>8));
}
static void key_u4(std::vector<uint8_t>&p,uint32_t key,uint32_t v){
  for(int i=0;i<4;++i) p.push_back(uint8_t(key>>(8*i)));
  for(int i=0;i<4;++i) p.push_back(uint8_t(v>>(8*i)));
}
static void valset(UART &u,const std::vector<uint8_t>&p){write_frame(u,0x06,0x8A,p);}
static void host_baud(UART &u,uint32_t b){u.set_baud_rate(b);u.load_settings();delay(100);}
static void change_receiver_to_230400(UART &u){
  auto p=ram();
  key_u4(p,0x40520001u,230400u); // UART1 baud
  key_l(p,0x10520005u,true);    // enable UART1
  key_l(p,0x10730001u,true);    // UBX input
  key_l(p,0x10740001u,true);    // UBX output
  key_l(p,0x10740002u,true);    // NMEA output for GGA/RMC diagnostics
  valset(u,p);
}
static void cfg_msg(UART&u,uint8_t cls,uint8_t msg,uint8_t rate){
  // 8-byte legacy CFG-MSG: I2C, UART1, UART2, USB, SPI, reserved.
  write_frame(u,0x06,0x01,{cls,msg,0,rate,0,0,0,0});
  delay(35);
}
static void configure(UART &u){
  // If GNSS was already running at 230400 after an ESP reboot, also recover it.
  const uint32_t rates[]={38400u,9600u,115200u,230400u};
  for(uint32_t rate:rates){host_baud(u,rate);change_receiver_to_230400(u);delay(140);}
  host_baud(u,230400u);
  // Signal changes can restart GNSS subsystem. Config applies to RAM, never flash/BBR.
  {auto p=ram();
    key_l(p,0x1031001Fu,true);key_l(p,0x10310001u,true); // GPS L1
    key_l(p,0x10310021u,true);key_l(p,0x10310007u,true); // Galileo E1
    key_l(p,0x10310022u,true);key_l(p,0x1031000Du,true); // BeiDou B1
    key_l(p,0x10310025u,true);key_l(p,0x10310018u,true); // GLONASS L1
    key_l(p,0x10310020u,true);key_l(p,0x10310005u,true); // SBAS L1
    key_l(p,0x10310024u,false);key_l(p,0x10310012u,false); // QZSS off
    valset(u,p);
  }
  delay(900);
  {auto p=ram();
    // These four SBAS IDs are from official u-blox M9 interface specification.
    key_l(p,0x10360002u,false); // TESTMODE off
    key_l(p,0x10360003u,true);  // RANGING on
    key_l(p,0x10360004u,true);  // DIFFCORR on
    key_l(p,0x10360005u,false); // INTEGRITY off (avoid constellation restriction)
    key_u1(p,0x201100A2u,32);   // MAXSVS; effective NAV cap can be 16 at >=10Hz
    valset(u,p);
  }
  delay(120);
  // Limit serial traffic BEFORE requesting 25Hz. Each UART1 rate is in nav epochs.
  cfg_msg(u,0xF0,0x00,25); // GGA 1 Hz
  cfg_msg(u,0xF0,0x01,0);  // GLL off
  cfg_msg(u,0xF0,0x02,25); // GSA 1 Hz
  cfg_msg(u,0xF0,0x03,25); // GSV 1 Hz
  cfg_msg(u,0xF0,0x04,25); // RMC 1 Hz
  cfg_msg(u,0xF0,0x05,0);  // VTG off
  cfg_msg(u,0xF0,0x08,0);  // ZDA off
  cfg_msg(u,0x01,0x07,1);  // NAV-PVT 25 Hz
  cfg_msg(u,0x01,0x04,25); // NAV-DOP 1 Hz
  cfg_msg(u,0x01,0x35,25); // NAV-SAT 1 Hz
  {auto p=ram();
    key_u2(p,0x30210001u,40); // CFG-RATE-MEAS 40 ms
    key_u2(p,0x30210002u,1);  // CFG-RATE-NAV 1
    valset(u,p);
  }
}
} // namespace goats_cfg
