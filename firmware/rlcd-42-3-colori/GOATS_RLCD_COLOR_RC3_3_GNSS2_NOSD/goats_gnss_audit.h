#pragma once
#include "esphome/components/uart/uart_component_esp_idf.h"
#include "esphome/core/version.h"
#include "driver/uart.h"
#include "driver/gpio.h"
#include "esp_heap_caps.h"
#include "esp_idf_version.h"
namespace goats_gnss_audit {
struct Hardware {
  uint8_t port{255};uint32_t baud{0};int32_t read_error{-1};
  bool installed{false},failed{false};
  size_t buffered{0},free_internal{0},largest_internal{0};int rx_level{0};
};
inline Hardware inspect(esphome::uart::UARTComponent &bus){
  Hardware s;
  auto &hw=static_cast<esphome::uart::IDFUARTComponent &>(bus);
  s.port=hw.get_hw_serial_number();
  s.failed=hw.is_failed();
  if(s.port<SOC_UART_NUM){
    auto port=static_cast<uart_port_t>(s.port);
    s.installed=uart_is_driver_installed(port);
    if(s.installed){
      s.read_error=uart_get_baudrate(port,&s.baud);
      uart_get_buffered_data_len(port,&s.buffered);
    }
  }
  s.free_internal=heap_caps_get_free_size(MALLOC_CAP_INTERNAL);
  s.largest_internal=heap_caps_get_largest_free_block(MALLOC_CAP_INTERNAL);
  s.rx_level=gpio_get_level(GPIO_NUM_1);
  return s;
}
inline const char *status(bool msc,bool attached,bool configured,bool uart_error,
 uint32_t polls,uint32_t bytes,uint32_t good,bool fresh,uint32_t core,bool fix){
  if(msc)return "USB MSC: GPS SOSPESO";
  if(!attached)return "GNSS NON ATTIVATO AL BOOT";
  if(!polls)return "POLL NON ESEGUITO";
  if(!configured)return "CONFIGURAZIONE NON TERMINATA";
  if(uart_error)return "ERRORE DRIVER UART";
  if(!bytes)return "NESSUN BYTE DAL GPS";
  if(!good)return "BYTE RX, NESSUN UBX VALIDO";
  if(!fresh)return "UBX OK, NAV-PVT ASSENTE";
  if(!core)return "NAV-PVT NON ARRIVA AL CORE";
  return fix?"CORE RC3.3: FIX PRESENTE":"CORE RC3.3: ATTESA FIX";
}
} // namespace goats_gnss_audit
