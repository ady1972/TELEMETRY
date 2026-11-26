#pragma once
#include <cstdint>
#include <cstddef>
#include <vector>
namespace esphome::uart {
struct UARTComponent {
 uint32_t baud=38400, reads=0;size_t at=0;
 std::vector<uint8_t> rx;
 std::vector<uint32_t> bauds;
 std::vector<std::vector<uint8_t>> writes;
 void set_baud_rate(uint32_t b){baud=b;}
 uint32_t get_baud_rate(){return baud;}
 void load_settings(){bauds.push_back(baud);}
 void write_array(const uint8_t*p,size_t n){writes.emplace_back(p,p+n);}
 void flush(){}
 size_t available()const{return rx.size()-at;}
 bool read_byte(uint8_t*p){if(!available())return false;*p=rx[at++];++reads;return true;}
};
struct UARTDevice {
 virtual ~UARTDevice()=default;
 void set_uart_parent(UARTComponent*p){parent_=p;}
 protected:UARTComponent*parent_{nullptr};
};
}
