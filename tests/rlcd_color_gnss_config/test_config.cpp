#include <cassert>
#include <vector>
#include <string>
#include <map>
#include "esphome/components/uart/uart.h"
#define goats_cfg original_cfg
#include ORIGINAL_CFG_HEADER
#undef goats_cfg
#include "goats_m9n_cfg.h"
using esphome::uart::UARTComponent;
static uint32_t value(const std::vector<uint8_t>&p,size_t at,unsigned bytes){
 uint32_t v=0;for(unsigned i=0;i<bytes;i++)v|=uint32_t(p.at(at+i))<<(8*i);return v;
}
static void verify_frames(const UARTComponent &uart){
 assert(uart.frames.size()==17&&uart.flushes==17);
 assert((uart.bauds==std::vector<uint32_t>{38400,9600,115200,230400,230400}));
 assert(uart.baud==230400&&test_ms==2430);
 for(const auto &frame:uart.frames){
  const auto &f=frame.bytes;
  assert(f[0]==0xB5&&f[1]==0x62&&f[2]==6);
  const auto len=value(f,4,2);assert(f.size()==len+8);
  uint8_t a=0,b=0;for(size_t i=2;i<f.size()-2;i++){a+=f[i];b+=a;}
  assert(f[f.size()-2]==a&&f.back()==b);
  assert(f[3]==0x8A||f[3]==0x01); // No CFG-CFG save or receiver-reset command.
  if(f[3]==0x8A)assert(f[6]==0&&f[7]==1&&f[8]==0&&f[9]==0); // RAM layer only.
 }
}
// Model an already-running receiver's baud: only matching-baud frames are read.
static void verify_bootstrap(const UARTComponent&uart,uint32_t receiver_baud){
 std::map<uint32_t,uint32_t> keys;std::map<unsigned,unsigned> rates;
 for(const auto &frame:uart.frames){
  if(frame.baud!=receiver_baud)continue;
  const auto &f=frame.bytes;
  if(f[3]==0x8A){
   for(size_t at=10;at<f.size()-2;){
    const uint32_t key=value(f,at,4);at+=4;
    const unsigned type=(key>>28)&7;
    const unsigned length=type==1||type==2?1:type==3?2:type==4?4:0;
    assert(length&&at+length<=f.size()-2);
    const auto v=value(f,at,length);at+=length;keys[key]=v;
    if(key==0x40520001u)receiver_baud=v;
   }
  }else{
   assert(f[3]==1&&value(f,4,2)==8);
   rates[(unsigned(f[6])<<8)|f[7]]=f[9];
  }
 }
 assert(receiver_baud==230400);
 assert(keys.at(0x30210001u)==40&&keys.at(0x30210002u)==1);
 assert(keys.at(0x10520005u)==1&&keys.at(0x10730001u)==1&&keys.at(0x10740001u)==1&&keys.at(0x10740002u)==1);
 for(auto key:{0x1031001Fu,0x10310001u,0x10310021u,0x10310007u,0x10310022u,
               0x1031000Du,0x10310025u,0x10310018u,0x10310020u,0x10310005u})assert(keys.at(key)==1);
 assert(keys.at(0x10310024u)==0&&keys.at(0x10310012u)==0);
 assert(keys.at(0x201100A2u)==32);
 assert(rates.at(0x0107)==1&&rates.at(0x0104)==25&&rates.at(0x0135)==25);
 for(auto msg:{0xF000,0xF002,0xF003,0xF004})assert(rates.at(msg)==25);
 for(auto msg:{0xF001,0xF005,0xF008})assert(rates.at(msg)==0);
}
inline bool usb_mode=false;
namespace goats_usb_msc {bool boot_if_requested(){return usb_mode;}}
namespace goats_b {unsigned calls=0;void setup(){calls++;}}
namespace goats_archive {unsigned calls=0;void setup(){calls++;}}
namespace goats_menu {unsigned calls=0;void init(){calls++;}}
namespace goats_dates {unsigned calls=0;void setup(){calls++;}}
namespace goats_screen_mode {unsigned calls=0;void load(){calls++;}}
#define id(x) x
#define ESP_LOGI(...) do{}while(0)
inline UARTComponent active;
inline auto *gps_uart=&active;
void run_actual_boot(){
ACTUAL_BOOT_LAMBDA
}
int main(){
 UARTComponent old_uart,new_uart;
 test_ms=0;original_cfg::configure(old_uart);verify_frames(old_uart);
 test_ms=0;goats_cfg::configure(new_uart);verify_frames(new_uart);
 assert(old_uart.frames==new_uart.frames&&old_uart.bauds==new_uart.bauds);
 for(auto baud:{38400U,9600U,115200U,230400U})verify_bootstrap(new_uart,baud);
 for(unsigned boot=0;boot<2;boot++){
  active=UARTComponent{};test_ms=0;usb_mode=false;run_actual_boot();
  verify_frames(active);assert(active.frames==new_uart.frames);
  assert(goats_dates::calls==boot+1&&goats_screen_mode::calls==boot+1);
  assert(goats_b::calls==boot+1&&goats_archive::calls==boot+1&&goats_menu::calls==boot+1);
 }
 active=UARTComponent{};test_ms=0;usb_mode=true;run_actual_boot();
 assert(active.frames.empty()&&active.bauds.empty()&&test_ms==0);
 assert(goats_b::calls==2&&goats_archive::calls==2&&goats_menu::calls==2);
 assert(goats_dates::calls==2&&goats_screen_mode::calls==2);
}
