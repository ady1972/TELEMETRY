#include "goats_gnss_scan.h"
#include "esphome/core/hal.h"
#include "esphome/core/application.h"
#include "driver/uart.h"
#include "driver/gpio.h"
#include "esp_intr_alloc.h"
namespace esphome::goats_gnss_scan {
static constexpr gpio_num_t RX=GPIO_NUM_1;
void GnssScan::setup(){
  App.set_loop_interval(5);
  const auto e=gpio_install_isr_service(ESP_INTR_FLAG_IRAM);
  if(e!=ESP_OK&&e!=ESP_ERR_INVALID_STATE)monitor_error_=e;
  engine_.start(millis());
}
void IRAM_ATTR GnssScan::edge_isr_(void *arg){
  static_cast<GnssScan*>(arg)->edges_.fetch_add(1,std::memory_order_relaxed);
}
bool GnssScan::open(const goats_scan::Candidate &c){
  gpio_intr_disable(RX);gpio_isr_handler_remove(RX);edge_active_=false;
  if(serial_){serial_->end();serial_.reset();}
  serial_=std::make_unique<HardwareSerial>(c.port);
  serial_->setRxBufferSize(16384);
  serial_->setTimeout(0);
  static constexpr uint32_t modes[]={SERIAL_8N1,SERIAL_8N2,SERIAL_8E1,SERIAL_8O1,SERIAL_8E2,SERIAL_8O2};
  serial_->begin(c.baud,modes[c.format],1,2,false);
  if(!*serial_||!serial_->baudRate())return false;
  serial_->setRxFIFOFull(16);serial_->setRxTimeout(2);
  serial_->onReceiveError([this](hardwareSerial_error_t error){
    if(error!=UART_NO_ERROR)io_errors_.fetch_add(1,std::memory_order_relaxed);
  });
  if(uart_set_line_inverse(static_cast<uart_port_t>(c.port),c.inverted?UART_SIGNAL_RXD_INV:0)!=ESP_OK)return false;
  if(!monitor_error_){
    auto e=gpio_isr_handler_add(RX,edge_isr_,this);
    if(e==ESP_OK)e=gpio_set_intr_type(RX,GPIO_INTR_ANYEDGE);
    if(e==ESP_OK)e=gpio_intr_enable(RX);
    if(e==ESP_OK)edge_active_=true;else monitor_error_=e;
  }
  return true;
}
size_t GnssScan::read(uint8_t *out,size_t n){
  if(!serial_)return 0;
  const auto available=serial_->available();if(available<=0)return 0;
  // Once bytes arrive, line activity is established. Stop extra GPIO interrupts.
  if(edge_active_){gpio_intr_disable(RX);edge_active_=false;}
  return serial_->read(out,std::min<size_t>(n,available));
}
void GnssScan::write(const uint8_t *p,size_t n){if(serial_)serial_->write(p,n);}
int GnssScan::rx_level() const{return gpio_get_level(RX);}
void GnssScan::loop(){
  ++loop_calls_;const auto now=millis();
  engine_.note_io_errors(io_errors_.load(std::memory_order_relaxed),now);
  engine_.tick(now);
}
}
