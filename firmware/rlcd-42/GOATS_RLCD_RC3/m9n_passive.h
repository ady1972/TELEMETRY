#pragma once
#include "esphome.h"
#include <stdint.h>

namespace goats_b { void on_pvt(const uint8_t *, uint16_t); }
namespace goats_diag {
struct State {
 uint8_t state=0,cls=0,id=0,checkA=0,checkB=0,rxA=0;
 uint16_t len=0,pos=0;
 uint8_t buf[1200]={};
 uint32_t bytes=0,good=0,bad=0,pvt_count=0,first_window=0;
 uint32_t last_byte=0,last_valid=0,last_pvt=0,last_sat=0,last_dop=0;
 uint32_t rate=460800, change_at=0, detect_last=0, scan_bytes=0;
 uint32_t nmea_valid=0;
 uint8_t scan_index=0, nmea_phase=0, nmea_ck=0, nmea_read_ck=0, nmea_digits=0;
 uint8_t hits_ubx=0,hits_nmea=0;
 bool locked=false, found_ubx=false;
 uint8_t seen=0,used=0,fix_type=0,gps=0,gal=0,bds=0,glo=0,sbas=0;
 float hdop=-1.0f, pvt_hz=0.0f, speed_kmh=0.0f;
};
inline State &data(){static State s;return s;}
inline float trace_hdop(){return data().hdop;}
inline uint16_t le16(const uint8_t *p){return (uint16_t)p[0] | ((uint16_t)p[1]<<8);}
inline int32_t le32s(const uint8_t *p){return (int32_t)((uint32_t)p[0] | ((uint32_t)p[1]<<8) | ((uint32_t)p[2]<<16) | ((uint32_t)p[3]<<24));}
inline void frame(State &s){
 uint32_t now=millis();s.good++;s.last_valid=now;
 if(!s.locked){if(s.hits_ubx<255)s.hits_ubx++;if(s.hits_ubx>=2){s.locked=true;s.found_ubx=true;s.detect_last=now;}}
 if(s.cls!=0x01)return;
 if(s.id==0x07 && s.len>=92){
   s.fix_type=s.buf[20];s.used=s.buf[23];s.speed_kmh=le32s(s.buf+60)*0.0036f;
   s.last_pvt=now;s.pvt_count++;
   goats_b::on_pvt(s.buf,s.len);
 } else if(s.id==0x04 && s.len>=18){
   s.hdop=le16(s.buf+12)/100.0f;s.last_dop=now;
 } else if(s.id==0x35 && s.len>=8){
   s.last_sat=now;s.seen=s.gps=s.gal=s.bds=s.glo=s.sbas=0;
   uint8_t count=s.buf[5];
   for(unsigned n=0;n<count && (8u+12u*n+12u)<=s.len;n++){
     const uint8_t *v=s.buf+8u+12u*n;
     // Tracked/seen: C/N0 > 0; not necessarily used in navigation solution.
     if(v[2]==0)continue;
     if(s.seen<255)s.seen++;
     switch(v[0]){
       case 0:s.gps++;break;
       case 1:s.sbas++;break;
       case 2:s.gal++;break;
       case 3:s.bds++;break;
       case 6:s.glo++;break;
       default:break;
     }
   }
 }
}
inline void byte(State &s,uint8_t c){
 switch(s.state){
  case 0:s.state=c==0xB5?1:0;break;
  case 1:s.state=c==0x62?2:(c==0xB5?1:0);s.checkA=0;s.checkB=0;break;
  case 2:s.cls=c;s.checkA+=c;s.checkB+=s.checkA;s.state=3;break;
  case 3:s.id=c;s.checkA+=c;s.checkB+=s.checkA;s.state=4;break;
  case 4:s.len=c;s.checkA+=c;s.checkB+=s.checkA;s.state=5;break;
  case 5:s.len|=(uint16_t)c<<8;s.checkA+=c;s.checkB+=s.checkA;s.pos=0;
         s.state=s.len>sizeof(s.buf)?0:(s.len?6:7);break;
  case 6:s.buf[s.pos++]=c;s.checkA+=c;s.checkB+=s.checkA;
         if(s.pos==s.len)s.state=7;break;
  case 7:s.rxA=c;s.state=8;break;
  case 8:if(s.rxA==s.checkA && c==s.checkB)frame(s);else s.bad++;
         s.state=0;break;
 }
}
// Baud detection uses validated UBX packets or checksum-verified NMEA lines.
// The UART is RX-only; no bytes are ever sent to the receiver.
inline void nmea_byte(State &s, uint8_t c) {
 if(c=='$') {s.nmea_phase=1;s.nmea_ck=0;s.nmea_digits=0;return;}
 if(s.nmea_phase==1){
   if(c=='*'){s.nmea_phase=2;s.nmea_digits=0;return;}
   if(c=='\r'||c=='\n'||c<32||c>126){s.nmea_phase=0;return;}
   s.nmea_ck^=c;return;
 }
 if(s.nmea_phase==2){
   int val=(c>='0'&&c<='9')?c-'0':(c>='A'&&c<='F')?c-'A'+10:(c>='a'&&c<='f')?c-'a'+10:-1;
   if(val<0){s.nmea_phase=0;return;}
   s.nmea_read_ck=(s.nmea_digits==0)?val:(uint8_t)(s.nmea_read_ck*16+val);
   if(++s.nmea_digits==2){
     if(s.nmea_ck==s.nmea_read_ck){s.nmea_valid++;if(s.hits_nmea<255)s.hits_nmea++;}
     s.nmea_phase=0;
   }
 }
}
// TEST C4: Fixed UART. No auto-baud scanning, no receiver configuration.
static constexpr uint32_t GPS_FIXED_BAUD=230400;
inline void poll(esphome::uart::UARTComponent *uart){
 State &s=data();uint8_t v;int budget=4096;
 uint32_t now=millis();
  if(!s.change_at){s.change_at=now;s.rate=GPS_FIXED_BAUD;s.first_window=now;}
 while(budget-- && uart->available()){
   if(!uart->read_byte(&v))break;
   s.bytes++;s.scan_bytes++;s.last_byte=millis();
   byte(s,v);nmea_byte(s,v);
 }
 now=millis();
 if(!s.locked && s.hits_nmea>=3 && s.hits_ubx==0){
   s.locked=true;s.found_ubx=false;s.detect_last=now;
 }
  // Keep UART fixed regardless of signal state. Never send commands to M9N.
  if(s.locked){
    bool active=s.found_ubx?(s.last_valid && now-s.last_valid<6500):
      (s.last_byte && now-s.last_byte<6500);
    if(!active){
      ESP_LOGW("m9n", "Segnale GPS assente: UART resta a 230400");
      s.locked=false;s.found_ubx=false;s.hits_ubx=0;s.hits_nmea=0;
      s.state=0;s.nmea_phase=0;
      s.last_valid=0;s.last_byte=0;
    }
  }
 if(now-s.first_window>=2000){
   s.pvt_hz=(1000.0f*s.pvt_count)/(now-s.first_window);
   s.pvt_count=0;s.first_window=now;
 }
}
}
