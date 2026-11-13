#include <array>
#include <cassert>
#include "pixel_pack.h"
using esphome::goats_st7306::pack_pixel;
int main() {
  std::array<uint8_t,30000> buffer{};
  // All physical pixels are covered once, with all three controller codes.
  for(int color=0;color<3;color++) {
    buffer.fill(0);
    for(int x=0;x<400;x++)for(int y=0;y<300;y++)pack_pixel(buffer.data(),x,y,color);
    const uint8_t expected=color==0?0xCC:(color==1?0xFF:0x33);
    for(auto byte:buffer)assert(byte==expected);
  }
  // Independently decode mixed pixels in physical panel coordinates.
  buffer.fill(0);
  for(int x=0;x<400;x++)for(int y=0;y<300;y++)pack_pixel(buffer.data(),x,y,(x+y)%3);
  for(int py=0;py<400;py++)for(int px=0;px<300;px++){
    const uint8_t b=buffer[py/2*150+px/2];
    const int high=(px%2==0?7:3)-py%2;
    const int code=(((b>>high)&1)<<1)|((b>>(high-2))&1);
    const int color=(py+299-px)%3;
    assert(code==(color==0?2:(color==1?3:1)));
  }
  const auto saved=buffer;
  for(auto x:{-1,400})pack_pixel(buffer.data(),x,0,1);
  for(auto y:{-1,300})pack_pixel(buffer.data(),0,y,1);
  assert(buffer==saved);
}
