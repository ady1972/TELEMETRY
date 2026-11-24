#include <cassert>
#include <iostream>
#include <vector>
#include "esphome/core/hal.h"
#include "goats_core.h"

using esphome::goats_core::GoatsCore;
using esphome::goats_core::UartDiagnostics;

static std::vector<uint8_t> pvt(uint32_t itow) {
  std::vector<uint8_t> b{0xB5,0x62,1,7,92,0};b.resize(98,0);
  for(unsigned i=0;i<4;++i)b[6+i]=uint8_t(itow>>(8*i));
  b[26]=3;b[27]=1;b[29]=7;
  uint8_t a=0,c=0;for(size_t i=2;i<b.size();++i){a+=b[i];c+=a;}
  b.push_back(a);b.push_back(c);return b;
}

int main() {
  esphome::uart::UARTComponent uart;
  GoatsCore app;app.set_uart_parent(&uart);
  const auto &rx=app.uart_diagnostics();
  assert(app.uart_buffer_capacity()==8192);
  esphome::simulated_ms=0;app.loop();
  assert(rx.polls==1 && rx.max_poll_gap_ms==0 && rx.max_pending_bytes==0);

  uart.feed(std::vector<uint8_t>(5000,0));
  esphome::simulated_ms=20;app.loop();
  assert(rx.max_pending_bytes==5000 && rx.pending_bytes==904 && rx.bytes_read==4096);
  assert(rx.limited_polls==1 && rx.max_poll_gap_ms==20);
  esphome::simulated_ms=25;app.loop();
  assert(rx.pending_bytes==0 && rx.bytes_read==5000 && rx.limited_polls==1);
  assert(rx.poll_gap_ms==5 && rx.max_poll_gap_ms==20);

  uart.feed(pvt(1040));esphome::simulated_ms=100;app.loop();
  assert(app.has_sample() && app.sample_count()==1 && app.latest_sample().valid_fix);
  assert(app.latest_sample().fix_ok && app.latest_sample().received_ms==100);
  assert(app.latest_sample().itow_ms==1040 && app.latest_sample().satellites==7);
  uart.feed(pvt(1040));esphome::simulated_ms=116;app.loop();
  assert(app.sample_count()==1 && app.diagnostics().duplicates()==1);
  assert(app.latest_sample().received_ms==100 && rx.max_poll_gap_ms==75);
  esphome::simulated_ms=916;app.loop();assert(rx.max_poll_gap_ms==800);

  UartDiagnostics wrap;
  wrap.begin_poll(0xFFFFFFF0U,10);wrap.end_poll(0,10,false);
  wrap.begin_poll(0x10,20);wrap.end_poll(30,0,false);
  assert(wrap.poll_gap_ms==32 && wrap.max_poll_gap_ms==32 && wrap.max_pending_bytes==30);
  wrap.begin_poll(0x11,4096);wrap.end_poll(0,4096,true);
  assert(wrap.limited_polls==0); // Full budget alone does not imply backlog/loss.
  wrap.begin_poll(0x12,4097);wrap.end_poll(1,4096,true);assert(wrap.limited_polls==1);
  std::cout<<"PASS: actual core polling, observed queue peak, budget/backlog, gap/rollover and unchanged PVT delivery\n";
}
