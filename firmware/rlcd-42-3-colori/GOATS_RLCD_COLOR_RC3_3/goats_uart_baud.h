#pragma once
#include "esphome/components/uart/uart.h"
#include <cstdint>
#if defined(USE_ESP32) && (defined(USE_ESP_IDF) || defined(USE_ARDUINO))
#include "esphome/components/uart/uart_component_esp_idf.h"
#include "driver/uart.h"
#endif

// GNSS baud bootstrap: keep ESPHome's installed UART and GPIO routing alive.
// load_settings() tears down/reinstalls the ESP-IDF driver on every baud step.
namespace goats_uart_baud {
inline uint32_t actual_baud{0};
inline int32_t apply_error{0}, readback_error{0};
inline uint8_t port{255};
inline void refresh(esphome::uart::UARTComponent &uart) {
#if defined(USE_ESP32) && (defined(USE_ESP_IDF) || defined(USE_ARDUINO))
  auto &hw = static_cast<esphome::uart::IDFUARTComponent &>(uart);
  port = hw.get_hw_serial_number();
  uint32_t baud = 0;
  readback_error = uart_get_baudrate(static_cast<uart_port_t>(port), &baud);
  actual_baud = readback_error == ESP_OK ? baud : 0;
#else
  actual_baud = uart.get_baud_rate();
#endif
}
inline void apply(esphome::uart::UARTComponent &uart, uint32_t baud) {
#if defined(USE_ESP32) && defined(USE_ESP_IDF)
  auto &hw = static_cast<esphome::uart::IDFUARTComponent &>(uart);
  port = hw.get_hw_serial_number();
  // Every preceding UBX write already calls flush() before this baud switch.
  apply_error = uart_set_baudrate(static_cast<uart_port_t>(port), baud);
  if (apply_error == ESP_OK) uart.set_baud_rate(baud);
  refresh(uart);
#else
  uart.set_baud_rate(baud);
  uart.load_settings();
  refresh(uart);
#endif
}
}  // namespace goats_uart_baud
