#pragma once
#include "esphome/components/goats_gnss_color/goats_gnss_color.h"
namespace goats_b { void on_pvt(const uint8_t *,uint16_t); }
namespace goats_diag {
using State=esphome::goats_gnss_color::State;
inline esphome::goats_gnss_color::GoatsGnssColor *receiver{nullptr};
inline State &data(){static State empty;return receiver?receiver->data():empty;}
inline float trace_hdop(){return data().hdop;}
inline void begin(esphome::goats_gnss_color::GoatsGnssColor *component){
  receiver=component;
  if(receiver){receiver->set_pvt_callback(goats_b::on_pvt);receiver->enable();}
}
inline void poll(esphome::uart::UARTComponent *){
  // Keep the RC3.3 scheduling/API; the separate Arduino component owns UART.
  if(receiver)receiver->poll();
}
} // namespace goats_diag
