#pragma once
#include "esphome/core/component.h"
#include "scan_engine.h"
#include <HardwareSerial.h>
#include <atomic>
#include <memory>

namespace esphome::goats_gnss_scan {
class GnssScan : public Component, public goats_scan::Transport {
 public:
  void setup() override;
  void loop() override;
  const goats_scan::View &data() const { return engine_.view(); }
  const char *status() const { return engine_.status(); }
  uint32_t actual_baud() const override { return serial_?serial_->baudRate():0; }
  uint32_t edges() const { return edges_.load(std::memory_order_relaxed); }
  uint32_t errors() const { return io_errors_.load(std::memory_order_relaxed); }
  uint32_t polls() const { return loop_calls_; }
  int rx_level() const;
  int monitor_error() const {return monitor_error_;}
 private:
  bool open(const goats_scan::Candidate&) override;
  size_t read(uint8_t*,size_t) override;
  void write(const uint8_t*,size_t) override;
  static void IRAM_ATTR edge_isr_(void*);
  std::unique_ptr<HardwareSerial> serial_;
  goats_scan::Engine engine_{*this};
  std::atomic<uint32_t> edges_{0},io_errors_{0};
  uint32_t loop_calls_{0};int monitor_error_{0};bool edge_active_{false};
};
}
