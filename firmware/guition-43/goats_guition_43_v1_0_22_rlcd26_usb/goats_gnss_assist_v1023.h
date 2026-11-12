#pragma once
#include "esphome.h"
#include "nvs.h"
#include "nvs_flash.h"
#include <algorithm>
#include <string>
#include <vector>
namespace goats_gnss_assist {
static esphome::uart::UARTComponent *identity_uart=nullptr;
static inline void set_uart(esphome::uart::UARTComponent *u){identity_uart=u;}
static inline void ubx_send(esphome::uart::UARTComponent *u,const std::vector<uint8_t>&f){if(u&&!f.empty())u->write_array(f.data(),f.size());}
static inline bool save_blob(const std::vector<uint8_t>&b){if(b.empty()||b.size()>32768)return false;nvs_handle_t h;if(nvs_open("goats_gnss",NVS_READWRITE,&h)!=ESP_OK)return false;esp_err_t e=nvs_set_blob(h,"dbd",b.data(),b.size());if(e==ESP_OK)e=nvs_commit(h);nvs_close(h);return e==ESP_OK;}
static inline std::vector<uint8_t> load_blob(){std::vector<uint8_t>b;nvs_handle_t h;if(nvs_open("goats_gnss",NVS_READONLY,&h)!=ESP_OK)return b;size_t n=0;if(nvs_get_blob(h,"dbd",nullptr,&n)==ESP_OK&&n>=8&&n<=32768){b.resize(n);if(nvs_get_blob(h,"dbd",b.data(),&n)!=ESP_OK)b.clear();}nvs_close(h);return b;}
static inline bool save_assistnow(const std::vector<uint8_t>&b){if(b.empty()||b.size()>196608)return false;nvs_handle_t h;if(nvs_open("goats_gnss",NVS_READWRITE,&h)!=ESP_OK)return false;esp_err_t e=nvs_set_blob(h,"assist",b.data(),b.size());if(e==ESP_OK)e=nvs_commit(h);nvs_close(h);return e==ESP_OK;}
static inline std::vector<uint8_t> load_assistnow(){std::vector<uint8_t>b;nvs_handle_t h;if(nvs_open("goats_gnss",NVS_READONLY,&h)!=ESP_OK)return b;size_t n=0;if(nvs_get_blob(h,"assist",nullptr,&n)==ESP_OK&&n>=8&&n<=196608){b.resize(n);if(nvs_get_blob(h,"assist",b.data(),&n)!=ESP_OK)b.clear();}nvs_close(h);return b;}
static inline bool clear_assistnow(){nvs_handle_t h;if(nvs_open("goats_gnss",NVS_READWRITE,&h)!=ESP_OK)return false;esp_err_t e=nvs_erase_key(h,"assist");if(e==ESP_ERR_NVS_NOT_FOUND)e=ESP_OK;if(e==ESP_OK)e=nvs_commit(h);nvs_close(h);return e==ESP_OK;}
static inline void inject_stream(esphome::uart::UARTComponent*u,const std::vector<uint8_t>&b){if(!u||b.empty())return;size_t p=0;while(p<b.size()){size_t n=std::min<size_t>(128,b.size()-p);u->write_array(b.data()+p,n);p+=n;delay(6);}}
static inline bool read_ubx(esphome::uart::UARTComponent*u,uint8_t cls,uint8_t id,std::vector<uint8_t>&out,uint32_t timeout_ms=1200){
 out.clear();if(!u)return false;std::vector<uint8_t>rx;uint32_t start=millis();
 while(millis()-start<timeout_ms){while(u->available()){uint8_t c=0;if(u->read_byte(&c))rx.push_back(c);if(rx.size()>2048)rx.erase(rx.begin(),rx.begin()+512);}
  for(size_t p=0;p+8<=rx.size();++p){if(rx[p]!=0xB5||rx[p+1]!=0x62)continue;uint16_t len=uint16_t(rx[p+4])|(uint16_t(rx[p+5])<<8);size_t total=size_t(len)+8;if(p+total>rx.size())continue;if(rx[p+2]!=cls||rx[p+3]!=id)continue;uint8_t a=0,b=0;for(size_t i=p+2;i<p+total-2;++i){a=uint8_t(a+rx[i]);b=uint8_t(b+a);}if(a!=rx[p+total-2]||b!=rx[p+total-1])continue;out.assign(rx.begin()+p,rx.begin()+p+total);return true;}delay(2);}return false;}
static inline std::string hex(const std::vector<uint8_t>&b){static const char h[]="0123456789ABCDEF";std::string s;s.reserve(b.size()*2);for(uint8_t v:b){s.push_back(h[v>>4]);s.push_back(h[v&15]);}return s;}
static inline std::string identity_hex(esphome::uart::UARTComponent *uart){
 identity_uart=uart;
 if(!identity_uart)return "";const uint8_t uq[]={0xB5,0x62,0x27,0x03,0x00,0x00,0x2A,0xA5};const uint8_t mv[]={0xB5,0x62,0x0A,0x04,0x00,0x00,0x0E,0x34};std::vector<uint8_t>u,v;
 while(identity_uart->available()){uint8_t c;identity_uart->read_byte(&c);}identity_uart->write_array(uq,sizeof(uq));if(!read_ubx(identity_uart,0x27,0x03,u))return "";identity_uart->write_array(mv,sizeof(mv));if(!read_ubx(identity_uart,0x0A,0x04,v))return "";return hex(u)+" "+hex(v);}

// ---------------- AssistNow MGA flow control V10.2.9.4.1 ----------------
// u-blox M9: CFG-NAVSPG-ACKAIDING key 0x10110025.
// With ACKAIDING enabled the receiver emits UBX-MGA-ACK-DATA0 (13 60)
// for each assistance message. The ACK payload identifies the original
// message by msgId and the first four bytes of its payload.

struct MgaInjectStats {
  uint32_t total{0};
  uint32_t accepted{0};
  uint32_t retries{0};
  uint32_t rejected{0};
  uint32_t timeouts{0};
  uint32_t malformed{0};
  bool ack_enabled{false};
};

static inline void ubx_checksum_(const uint8_t *data, size_t n, uint8_t &a, uint8_t &b) {
  a=0; b=0;
  for(size_t i=0;i<n;i++){ a=uint8_t(a+data[i]); b=uint8_t(b+a); }
}

static inline std::vector<uint8_t> ubx_frame_(uint8_t cls,uint8_t id,const std::vector<uint8_t>&payload){
  std::vector<uint8_t> f;
  f.reserve(payload.size()+8);
  f.push_back(0xB5); f.push_back(0x62); f.push_back(cls); f.push_back(id);
  uint16_t n=static_cast<uint16_t>(payload.size());
  f.push_back(uint8_t(n)); f.push_back(uint8_t(n>>8));
  f.insert(f.end(),payload.begin(),payload.end());
  uint8_t a=0,b=0; ubx_checksum_(f.data()+2,f.size()-2,a,b);
  f.push_back(a); f.push_back(b);
  return f;
}

static inline void drain_uart_(esphome::uart::UARTComponent *u,uint32_t quiet_ms=15){
  if(!u)return;
  uint32_t last=millis();
  while(millis()-last<quiet_ms){
    bool got=false;
    while(u->available()){
      uint8_t c=0;
      if(u->read_byte(&c)){got=true;last=millis();}
    }
    if(!got) delay(1);
  }
}

static inline bool set_ack_aiding_(esphome::uart::UARTComponent *u,bool enabled){
  if(!u)return false;
  // UBX-CFG-VALSET: version=0, layers=RAM(1), transaction=0, reserved=0
  // key CFG-NAVSPG-ACKAIDING = 0x10110025 (L), value 0/1.
  std::vector<uint8_t> p = {
    0x00,0x01,0x00,0x00,
    0x25,0x00,0x11,0x10,
    uint8_t(enabled ? 1 : 0)
  };
  auto f=ubx_frame_(0x06,0x8A,p);
  drain_uart_(u,8);
  u->write_array(f.data(),f.size());
  // The setting is RAM-only. Allow the receiver to apply it before MGA traffic.
  delay(80);
  return true;
}

static inline bool valid_ubx_frame_(const uint8_t *f,size_t n){
  if(!f||n<8||f[0]!=0xB5||f[1]!=0x62)return false;
  uint16_t len=uint16_t(f[4])|(uint16_t(f[5])<<8);
  if(size_t(len)+8!=n)return false;
  uint8_t a=0,b=0; ubx_checksum_(f+2,n-4,a,b);
  return a==f[n-2] && b==f[n-1];
}

static inline bool wait_mga_ack_(esphome::uart::UARTComponent *u,
                                 uint8_t sent_id,
                                 const uint8_t payload4[4],
                                 uint8_t &info_code,
                                 uint32_t timeout_ms=500){
  info_code=0xFF;
  if(!u)return false;
  std::vector<uint8_t> rx;
  rx.reserve(512);
  uint32_t start=millis();
  while(millis()-start<timeout_ms){
    while(u->available()){
      uint8_t c=0;
      if(u->read_byte(&c)) rx.push_back(c);
      if(rx.size()>1024) rx.erase(rx.begin(),rx.begin()+512);
    }
    for(size_t p=0;p+16<=rx.size();++p){
      if(rx[p]!=0xB5||rx[p+1]!=0x62||rx[p+2]!=0x13||rx[p+3]!=0x60)continue;
      uint16_t len=uint16_t(rx[p+4])|(uint16_t(rx[p+5])<<8);
      size_t total=size_t(len)+8;
      if(p+total>rx.size())continue;
      if(len<8)continue;
      if(!valid_ubx_frame_(rx.data()+p,total))continue;
      const uint8_t *pl=rx.data()+p+6;
      // DATA0: type, version, infoCode, msgId, msgPayloadStart[4]
      if(pl[3]!=sent_id)continue;
      if(pl[4]!=payload4[0]||pl[5]!=payload4[1]||
         pl[6]!=payload4[2]||pl[7]!=payload4[3])continue;
      info_code=pl[2];
      return true;
    }
    delay(2);
  }
  return false;
}

static inline MgaInjectStats inject_stream_mga_ack(esphome::uart::UARTComponent *u,
                                                    const std::vector<uint8_t>&stream,
                                                    uint8_t max_retries=2){
  MgaInjectStats st;
  if(!u||stream.empty())return st;

  st.ack_enabled=set_ack_aiding_(u,true);
  size_t p=0;

  while(p+8<=stream.size()){
    // Resync to next UBX frame if necessary.
    if(stream[p]!=0xB5||stream[p+1]!=0x62){
      ++p; ++st.malformed; continue;
    }
    uint16_t len=uint16_t(stream[p+4])|(uint16_t(stream[p+5])<<8);
    size_t total=size_t(len)+8;
    if(total<8||p+total>stream.size()){ ++st.malformed; break; }
    if(!valid_ubx_frame_(stream.data()+p,total)){
      ++st.malformed; ++p; continue;
    }

    const uint8_t cls=stream[p+2], id=stream[p+3];
    // Predictive/AssistNow payload should be MGA. Non-MGA UBX records are
    // still forwarded once, but no MGA ACK is expected for them.
    if(cls!=0x13){
      u->write_array(stream.data()+p,total);
      ++st.total; ++st.accepted;
      p+=total; delay(8); continue;
    }

    uint8_t payload4[4]={0,0,0,0};
    for(size_t i=0;i<4 && i<len;i++) payload4[i]=stream[p+6+i];

    bool ok=false;
    uint8_t info=0xFF;
    for(uint8_t attempt=0; attempt<=max_retries && !ok; ++attempt){
      // Clear stale output before each message so the ACK correlation is deterministic.
      drain_uart_(u,5);
      u->write_array(stream.data()+p,total);
      ++st.total;
      if(wait_mga_ack_(u,id,payload4,info,550)){
        // infoCode 0 = accepted.
        if(info==0){
          ok=true; ++st.accepted;
        }else{
          // 5 = receiver not ready: a short retry is useful.
          ++st.rejected;
          if(attempt<max_retries){
            ++st.retries;
            delay(info==5 ? 120 : 50);
          }
        }
      }else{
        ++st.timeouts;
        if(attempt<max_retries){ ++st.retries; delay(60); }
      }
    }

    // Do not abort the complete package for one bad satellite record:
    // continue with the next valid UBX-MGA record after retries.
    p+=total;
    delay(3);
  }

  // ACKAIDING is RAM-only, but restore the previous project behaviour
  // (no continuous MGA ACK traffic) after injection.
  set_ack_aiding_(u,false);
  return st;
}


static inline MgaInjectStats apply_saved_assistnow_mga_ack(esphome::uart::UARTComponent *u) {
  auto b = load_assistnow();
  if (b.size() < 8 || b[0] != 0xB5 || b[1] != 0x62) return MgaInjectStats{};
  return inject_stream_mga_ack(u, b, 2);
}
}
