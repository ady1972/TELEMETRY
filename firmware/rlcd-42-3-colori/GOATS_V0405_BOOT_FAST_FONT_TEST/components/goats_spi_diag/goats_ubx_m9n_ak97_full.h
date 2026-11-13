#pragma once
#include "esphome/components/uart/uart.h"
#include <Arduino.h>

#include <vector>
#include <string>
#include <cstdint>
#include <cmath>
#include <algorithm>

namespace goats_m9n {

struct NavSample {
  uint32_t now_ms{0};
  uint32_t gnss_itow_ms{0};
  bool fix{false};
  uint8_t satellites{0};
  double latitude{0.0};
  double longitude{0.0};
  float speed_kmh{0.0f};
  float heading_deg{0.0f};
};

struct GnssState {
  bool fix{false};
  uint8_t used_sats{0};
  uint8_t visible_sats{0};
  float speed_kmh{0.0f};
  float heading_deg{0.0f};
  float hdop{99.9f};
  double latitude{0.0};
  double longitude{0.0};
  float pvt_hz{0.0f};
  uint32_t last_pvt_ms{0};
  uint32_t rate_window_ms{0};
  uint32_t rate_count{0};
  std::string date_text{"--/--/----"};
  std::string time_text{"--:--"};
};

inline GnssState state;
inline std::vector<NavSample> pending_samples;
inline bool nav_timebase_set{false};
inline uint32_t nav_timebase_offset{0};
inline uint32_t last_itow{0};

inline bool dbd_capture{false};
inline uint32_t dbd_started_ms{0};
inline std::vector<std::vector<uint8_t>> dbd_frames;

static inline uint16_t u2(const std::vector<uint8_t> &p, size_t o) {
  return (o + 2 <= p.size()) ? uint16_t(p[o]) | (uint16_t(p[o+1]) << 8) : 0;
}
static inline uint32_t u4(const std::vector<uint8_t> &p, size_t o) {
  return (o + 4 <= p.size()) ? uint32_t(p[o]) | (uint32_t(p[o+1]) << 8) |
      (uint32_t(p[o+2]) << 16) | (uint32_t(p[o+3]) << 24) : 0;
}
static inline int32_t i4(const std::vector<uint8_t> &p, size_t o) {
  return static_cast<int32_t>(u4(p,o));
}
static inline void checksum(const uint8_t *p, size_t n, uint8_t &a, uint8_t &b) {
  a=0; b=0; for(size_t i=0;i<n;i++){ a=uint8_t(a+p[i]); b=uint8_t(b+a); }
}
static inline std::vector<uint8_t> frame(uint8_t cls,uint8_t id,const std::vector<uint8_t>&pl){
  std::vector<uint8_t> f{0xB5,0x62,cls,id,uint8_t(pl.size()),uint8_t(pl.size()>>8)};
  f.insert(f.end(),pl.begin(),pl.end()); uint8_t a=0,b=0;
  checksum(f.data()+2,f.size()-2,a,b); f.push_back(a); f.push_back(b); return f;
}
static inline void send(esphome::uart::UARTComponent *u,const std::vector<uint8_t>&f){
  if(u && !f.empty()){ u->write_array(f.data(),f.size()); u->flush(); }
}
static inline void put_l(std::vector<uint8_t>&p,uint32_t k,bool v){
  p.insert(p.end(),{uint8_t(k),uint8_t(k>>8),uint8_t(k>>16),uint8_t(k>>24),uint8_t(v?1:0)});
}
static inline void put_u1(std::vector<uint8_t>&p,uint32_t k,uint8_t v){
  p.insert(p.end(),{uint8_t(k),uint8_t(k>>8),uint8_t(k>>16),uint8_t(k>>24),v});
}
static inline void put_u2(std::vector<uint8_t>&p,uint32_t k,uint16_t v){
  p.insert(p.end(),{uint8_t(k),uint8_t(k>>8),uint8_t(k>>16),uint8_t(k>>24),uint8_t(v),uint8_t(v>>8)});
}
static inline void put_u4(std::vector<uint8_t>&p,uint32_t k,uint32_t v){
  p.insert(p.end(),{uint8_t(k),uint8_t(k>>8),uint8_t(k>>16),uint8_t(k>>24),
                    uint8_t(v),uint8_t(v>>8),uint8_t(v>>16),uint8_t(v>>24)});
}
static inline std::vector<uint8_t> valset(){ return {0x00,0x01,0x00,0x00}; }
static inline void host_baud(esphome::uart::UARTComponent*u,uint32_t b){
  u->set_baud_rate(b); u->load_settings(); delay(80);
}
static inline void request_230400(esphome::uart::UARTComponent*u){
  auto p=valset();
  put_u4(p,0x40520001u,230400u); // CFG-UART1-BAUDRATE
  put_l(p,0x10520005u,true);     // UART1 enabled
  put_l(p,0x10730001u,true);     // UBX input
  put_l(p,0x10740001u,true);     // UBX output
  send(u,frame(0x06,0x8A,p)); delay(130);
}
static inline void bootstrap_baud(esphome::uart::UARTComponent*u){
  const uint32_t r[]={38400u,9600u,115200u,230400u};
  for(auto b:r){host_baud(u,b);request_230400(u);} host_baud(u,230400u);
}
static inline void configure_signals(esphome::uart::UARTComponent*u){
  auto p=valset();
  // GPS + Galileo + BeiDou + GLONASS + SBAS; QZSS disabled.
  put_l(p,0x1031001Fu,true); put_l(p,0x10310001u,true);  // GPS L1CA
  put_l(p,0x10310021u,true); put_l(p,0x10310007u,true);  // GAL E1
  put_l(p,0x10310022u,true); put_l(p,0x1031000Du,true);  // BDS B1I
  put_l(p,0x10310025u,true); put_l(p,0x10310018u,true);  // GLO L1
  put_l(p,0x10310020u,true); put_l(p,0x10310005u,true);  // SBAS L1CA
  put_l(p,0x10310024u,false); put_l(p,0x10310012u,false); // QZSS off
  send(u,frame(0x06,0x8A,p)); delay(800);
}
static inline void configure_runtime(esphome::uart::UARTComponent*u){
  // Parametri GNSS verificati sul Guition V1.5.0, applicati solo in RAM.
  // La telemetria RLCD continua a ricevere esclusivamente UBX.
  auto p=valset();
  put_u1(p,0x201100A2u,32);       // MAXSVS
  put_l(p,0x10360002u,false);    // SBAS TESTMODE OFF (Guition)
  put_l(p,0x10360003u,true);     // SBAS RANGING ON
  put_l(p,0x10360004u,true);     // SBAS DIFFCORR ON
  put_l(p,0x10360005u,false);    // SBAS INTEGRITY OFF
  put_u4(p,0x40520001u,230400u);
  put_l(p,0x10520005u,true);
  put_l(p,0x10730001u,true); put_l(p,0x10730002u,false); put_l(p,0x10730004u,false);
  put_l(p,0x10740001u,true); put_l(p,0x10740002u,false);
  send(u,frame(0x06,0x8A,p)); delay(120);
  // Prima limitiamo il traffico seriale, poi impostiamo 25 Hz come nel Guition.
  auto msg=[&](uint8_t c,uint8_t i,uint8_t rate){
    std::vector<uint8_t> m{c,i,0,rate,0,0,0,0}; send(u,frame(0x06,0x01,m)); delay(35);
  };
  msg(0xF0,0x00,0);  // GGA off: RLCD usa solo UBX
  msg(0xF0,0x01,0);  // GLL off
  msg(0xF0,0x02,0);  // GSA off
  msg(0xF0,0x03,0);  // GSV off
  msg(0xF0,0x04,0);  // RMC off
  msg(0xF0,0x05,0);  // VTG off
  msg(0xF0,0x08,0);  // ZDA off
  msg(0x01,0x07,1);  // NAV-PVT a ogni epoca (25 Hz)
  msg(0x01,0x04,25); // NAV-DOP a 1 Hz (Guition)
  msg(0x01,0x35,25); // NAV-SAT a 1 Hz (Guition)
  p=valset();
  put_u2(p,0x30210001u,40);  // 40 ms = 25 Hz
  put_u2(p,0x30210002u,1);   // 1 soluzione per misura
  send(u,frame(0x06,0x8A,p)); delay(150);
}
static inline void configure(esphome::uart::UARTComponent*u){
  if(!u)return; bootstrap_baud(u); configure_signals(u); configure_runtime(u);
  state=GnssState{};
  pending_samples.clear();
  nav_timebase_set=false;
  last_itow=0;
  dbd_capture=false;
  dbd_started_ms=0;
  dbd_frames.clear();
  state.rate_window_ms=millis();
}

static inline bool leap(int y){ return (y%4==0 && y%100!=0)||(y%400==0); }
static inline int dim(int y,int m){ static const int md[12]={31,28,31,30,31,30,31,31,30,31,30,31}; return m==2&&leap(y)?29:md[m-1]; }
static inline int weekday(int y,int m,int d){ if(m<3){m+=12;y--;} int k=y%100,j=y/100; int h=(d+(13*(m+1))/5+k+k/4+j/4+5*j)%7; return (h+6)%7; }
static inline int last_sunday(int y,int m){ int last=dim(y,m); return last-weekday(y,m,last); }
static inline void update_rome_time(const std::vector<uint8_t>&p){
  int y=int(u2(p,4)), m=int(p[6]), d=int(p[7]), h=int(p[8]), mi=int(p[9]);
  uint8_t valid=p[11]; if((valid&0x03u)!=0x03u || y<2020 || m<1 || m>12) return;
  bool dst=false;
  if(m>3&&m<10) dst=true;
  else if(m==3){int ls=last_sunday(y,3); dst=(d>ls)||(d==ls&&h>=1);}
  else if(m==10){int ls=last_sunday(y,10); dst=(d<ls)||(d==ls&&h<1);}
  h += dst?2:1;
  if(h>=24){h-=24;d++;if(d>dim(y,m)){d=1;m++;if(m>12){m=1;y++;}}}
  char db[16],tb[8]; snprintf(db,sizeof(db),"%02d/%02d/%04d",d,m,y); snprintf(tb,sizeof(tb),"%02d:%02d",h,mi);
  state.date_text=db; state.time_text=tb;
}
static inline uint32_t mapped_nav_ms(uint32_t itow){
  const uint32_t now=millis();
  if(!nav_timebase_set || (itow<last_itow && (last_itow-itow)>1000000UL)){
    nav_timebase_offset=now-itow; nav_timebase_set=true;
  }
  last_itow=itow; return nav_timebase_offset+itow;
}

struct Parser {
  uint8_t st{0},cls{0},id{0},cka{0},ckb{0},rxa{0}; uint16_t len{0},pos{0}; std::vector<uint8_t> p;
  void ck(uint8_t v){cka=uint8_t(cka+v);ckb=uint8_t(ckb+cka);}
  void reset(){st=0;cls=id=cka=ckb=rxa=0;len=pos=0;p.clear();}
  void dispatch(){
    if(cls==0x01&&id==0x07&&p.size()>=92){
      bool fix=((p[21]&0x01u)!=0u)&&p[20]>=2;
      state.fix=fix; state.used_sats=p[23]; state.longitude=i4(p,24)*1e-7; state.latitude=i4(p,28)*1e-7;
      state.speed_kmh=i4(p,60)*0.0036f; state.heading_deg=i4(p,64)*1e-5f;
      state.last_pvt_ms=millis(); state.rate_count++; update_rome_time(p);
      const uint32_t itow=u4(p,0);
      NavSample s; s.now_ms=mapped_nav_ms(itow); s.gnss_itow_ms=itow;
      s.fix=fix; s.satellites=p[23]; s.latitude=state.latitude; s.longitude=state.longitude;
      s.speed_kmh=state.speed_kmh; s.heading_deg=state.heading_deg;
      if(pending_samples.size()>=64) pending_samples.erase(pending_samples.begin());
      pending_samples.push_back(s);
    } else if(cls==0x01&&id==0x04&&p.size()>=18){
      state.hdop=u2(p,12)*0.01f;
    } else if(cls==0x01&&id==0x35&&p.size()>=8){
      state.visible_sats=p[5];
    } else if(dbd_capture && cls==0x13 && id==0x80 &&
              p.size()>=12 && p.size()<=164){
      dbd_frames.push_back(frame(cls,id,p));
    } else if(dbd_capture && cls==0x13 && id==0x60){
      std::vector<uint8_t> blob={'G','D','B','1'};
      const uint16_t n=static_cast<uint16_t>(
          std::min<size_t>(dbd_frames.size(),65535));
      blob.push_back(uint8_t(n));
      blob.push_back(uint8_t(n>>8));
      for(size_t i=0;i<n;i++){
        const auto &f=dbd_frames[i];
        const uint16_t l=static_cast<uint16_t>(
            std::min<size_t>(f.size(),65535));
        blob.push_back(uint8_t(l));
        blob.push_back(uint8_t(l>>8));
        blob.insert(blob.end(),f.begin(),f.begin()+l);
      }
      if(!dbd_frames.empty())
        // AssistNow/DBD disabilitato in V040: nessuna persistenza automatica.
      dbd_capture=false;
      dbd_frames.clear();
    }
  }
  void feed(uint8_t c){
    switch(st){
      case 0: if(c==0xB5)st=1; break;
      case 1: if(c==0x62){st=2;cka=ckb=0;p.clear();}else st=0; break;
      case 2: cls=c;ck(c);st=3;break; case 3:id=c;ck(c);st=4;break;
      case 4:len=c;ck(c);st=5;break;
      case 5:len|=uint16_t(c)<<8;ck(c);pos=0;if(len>1024)reset();else{p.clear();p.reserve(len);st=len?6:7;}break;
      case 6:p.push_back(c);ck(c);if(++pos>=len)st=7;break;
      case 7:rxa=c;st=8;break;
      case 8:if(rxa==cka&&c==ckb)dispatch();reset();break; default:reset();break;
    }
  }
};
inline Parser parser;
static inline void poll(esphome::uart::UARTComponent*u){
  if(!u)return; uint8_t c; while(u->available()){if(!u->read_byte(&c))break;

    parser.feed(c);}
  uint32_t now=millis();
  if(state.rate_window_ms==0)state.rate_window_ms=now; uint32_t e=now-state.rate_window_ms;
  if(e>=1000){state.pvt_hz=e?1000.0f*float(state.rate_count)/float(e):0;state.rate_count=0;state.rate_window_ms=now;}
  if(state.last_pvt_ms==0||now-state.last_pvt_ms>1500){
    state.fix=false;
    if(state.last_pvt_ms==0||now-state.last_pvt_ms>3000){
      state.pvt_hz=0;
      state.speed_kmh=0;
    }
  }
  if(dbd_capture &&
     static_cast<uint32_t>(now-dbd_started_ms)>8000UL){
    dbd_capture=false;
    dbd_frames.clear();
  }
}

static inline void take_samples(
    std::vector<NavSample>&out,size_t max_count=64){
  out.clear();
  const size_t n=std::min(max_count,pending_samples.size());
  if(n==0) return;
  out.insert(out.end(),pending_samples.begin(),pending_samples.begin()+n);
  pending_samples.erase(pending_samples.begin(),pending_samples.begin()+n);
}

static inline bool dbd_capture_active(){
  return dbd_capture;
}

static inline void request_dbd_backup(
    esphome::uart::UARTComponent*u){
  if(!u || dbd_capture) return;
  dbd_frames.clear();
  dbd_capture=true;
  dbd_started_ms=millis();
  send(u,frame(0x13,0x80,{}));
}

} // namespace goats_m9n
