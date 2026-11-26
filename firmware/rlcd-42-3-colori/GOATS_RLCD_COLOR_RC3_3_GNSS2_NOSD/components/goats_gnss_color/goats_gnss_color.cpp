#define GOATS_GNSS_COLOR_IMPLEMENTATION
#include "goats_gnss_color.h"
// Deliberately compile the proven Arduino code outside generated main.cpp.
// main.cpp's millis/delay compatibility macros must never reach these headers.
#include "goats_m9n_cfg.h"
#include "goats_ubx_m9n_ak97_full.h"
#include "esphome/core/hal.h"

namespace esphome::goats_gnss_color {
GoatsGnssColor *GoatsGnssColor::active_=nullptr;
void GoatsGnssColor::setup(){started_ms_=::millis();}
void GoatsGnssColor::frame_(uint8_t cls,uint8_t id,const uint8_t *p,size_t n){
  if(active_==nullptr)return;
  auto &self=*active_;
  auto &s=self.data_;
  const uint32_t now=esphome::millis();
  ++s.good;s.last_valid=now;
  if(cls==5 && n>=2 && p[0]==6){
    if(id==1)++s.cfg_ack;else if(id==0)++s.cfg_nak;
  }
  if(cls!=1)return;
  if(id==7 && n>=92){
    s.last_pvt=now;s.fix_type=p[20];s.used=p[23];
    if(self.callback_)self.callback_(p,static_cast<uint16_t>(n));
  }else if(id==4 && n>=18){
    s.last_dop=now;s.hdop=(uint16_t(p[12])|(uint16_t(p[13])<<8))*0.01f;
  }else if(id==0x35 && n>=8){s.last_sat=now;s.seen=p[5];}
}
void GoatsGnssColor::poll(){
  if(!enabled_ || gps_uart_==nullptr)return;
  ++data_.poll_calls;
  if(!configured_){
    // Same 900ms minimum startup wait as DIAG2; the RC3.3 LCD is already set up.
    if(uint32_t(::millis()-started_ms_)<900)return;
    goats_cfg::configure(*gps_uart_); // Identical header: including load_settings().
    configured_=true;
  }
  active_=this;
  goats_m9n::frame_observer=[](uint8_t cls,uint8_t id,const std::vector<uint8_t> &p){
    frame_(cls,id,p.data(),p.size());
  };
  goats_m9n::poll(gps_uart_); // Sole UART reader, original parser and timeouts.
  const auto &original=goats_m9n::state;
  const auto &counts=goats_gps_diag::counters;
  data_.bytes=counts.bytes;data_.bad=counts.checksum_errors;
  data_.rate=gps_uart_->get_baud_rate();
  data_.used=original.used_sats;data_.seen=original.visible_sats;
  data_.speed_kmh=original.speed_kmh;data_.pvt_hz=original.pvt_hz;
  // Do not copy original.last_pvt_ms: its Arduino epoch differs from ESPHome.
  data_.locked=data_.good>=2 && uint32_t(esphome::millis()-data_.last_valid)<6500;
  data_.found_ubx=data_.locked;
  // Every validated raw NAV-PVT was delivered once, synchronously, above.
  goats_m9n::pending_samples.clear();
}
} // namespace esphome::goats_gnss_color
