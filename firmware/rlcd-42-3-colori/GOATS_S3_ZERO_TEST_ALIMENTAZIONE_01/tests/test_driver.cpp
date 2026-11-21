// Executes the real display-only implementation against an ESP/SPI stub.
#include "goats_power_test.h"
#include "esp_system.h"
#include <cassert>
#include <cstring>
#include <fstream>
#include <limits>
using esphome::goats_power_test::GoatsPowerTest;
struct Probe : GoatsPowerTest {
  using GoatsPowerTest::framebuffer_;
  using GoatsPowerTest::pixel_;
  using GoatsPowerTest::render_;
  using GoatsPowerTest::reset_label_;
  using GoatsPowerTest::reset_reason_;
};
int main(int argc, char **argv) {
  Probe display;
  for (int color=0; color<3; ++color) {
    display.framebuffer_.fill(0);
    for (int x=0;x<400;++x) for (int y=0;y<300;++y) display.pixel_(x,y,color);
    for (auto b:display.framebuffer_) assert(b==(color==0?0xCC:color==1?0xFF:0x33));
  }
  for (int x=0;x<400;++x) for (int y=0;y<300;++y) display.pixel_(x,y,(x+y)%3);
  for (int py=0;py<400;++py) for (int px=0;px<300;++px) {
    const auto b=display.framebuffer_[py/2*150+px/2];
    const int high=(px%2==0?7:3)-py%2;
    const int code=(((b>>high)&1)<<1)|((b>>(high-2))&1);
    const int color=(py+299-px)%3;
    assert(code==(color==0?2:color==1?3:1));
  }
  const auto saved=display.framebuffer_;
  for (int x:{-1,400}) display.pixel_(x,0,1);
  for (int y:{-1,300}) display.pixel_(0,y,1);
  assert(saved==display.framebuffer_);

  esphome::GPIOPin dc, reset;
  display.set_dc_pin(&dc); display.set_reset_pin(&reset);
  test_now_us=0; test_reason=ESP_RST_POWERON;
  display.setup();
  assert(display.reset_reason_==ESP_RST_POWERON);
  assert(std::strcmp(display.reset_label_,"ACCENSIONE")==0);
  const auto zero=display.framebuffer_;
  assert(test_now_us==800000);  // 200 ms reset + 400/200 ms original init.
  assert(reset.level);
  assert(reset.history==std::vector<bool>({true,false,true}));
  assert(display.write_sizes.back()==30000);
  const auto initial_commands=display.written_bytes;
  const std::vector<uint8_t> window{0x2A,0x05,0x36,0x2B,0,199,0x2C};
  assert(std::equal(window.rbegin(),window.rend(),initial_commands.rbegin()));

  for (uint64_t seconds:{1ULL,2ULL,60ULL,4294968ULL,9999999999ULL}) {
    test_now_us=800000+static_cast<int64_t>(seconds)*1000000;
    display.update();
    const auto actual=display.framebuffer_;
    display.render_(seconds);
    assert(actual==display.framebuffer_);
    assert(actual!=zero);
    assert(display.write_sizes.back()==30000);
  }
  test_reason=ESP_RST_BROWNOUT; test_now_us=0;
  display.setup();
  assert(std::strcmp(display.reset_label_,"BROWNOUT")==0);
  const auto brownout_zero=display.framebuffer_;
  display.render_(0); assert(display.framebuffer_==brownout_zero);
  display.render_(1); assert(display.framebuffer_!=brownout_zero);
  test_reason=ESP_RST_SW; test_now_us=0; display.setup();
  assert(std::strcmp(display.reset_label_,"SOFTWARE")==0);
  test_reason=ESP_RST_POWERON; test_now_us=0; display.setup();
  assert(display.framebuffer_==zero);  // No persisted counter or run state.

  if(argc>1) {
    display.render_(123);
    std::ofstream f(argv[1],std::ios::binary);
    f<<"P6\n400 300\n255\n";
    for(int y=0;y<300;++y)for(int x=0;x<400;++x){
      const int px=299-y,py=x,high=7-((px&1)*4+(py&1));
      const auto b=display.framebuffer_[py/2*150+px/2];
      const int code=(((b>>high)&1)<<1)|((b>>(high-2))&1);
      const unsigned char rgb[3]={static_cast<unsigned char>(code==3?0:255),
        static_cast<unsigned char>(code==2?255:0),static_cast<unsigned char>(code==2?255:0)};
      f.write(reinterpret_cast<const char*>(rgb),3);
    }
  }
}
