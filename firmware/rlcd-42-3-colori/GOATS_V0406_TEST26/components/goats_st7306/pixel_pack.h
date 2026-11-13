#pragma once
#include <cstdint>
namespace esphome::goats_st7306 {
// Logical 400x300 -> physical 300x400; ST7306 RBW 2x2 packed format.
inline void pack_pixel(uint8_t *buffer, int x, int y, uint8_t color) {
 if(x<0||x>=400||y<0||y>=300)return;
 const int px=299-y, py=x;
 const int index=(py/2)*150+px/2;
 const int high=7-((px&1)*4+(py&1)), low=high-2;
 const uint8_t code=color==1?3:(color==2?1:2); // white=0, black=1, red=2
 const uint8_t mask=(1U<<high)|(1U<<low);
 buffer[index]=(buffer[index]&uint8_t(~mask))|(((code>>1)&1U)<<high)|((code&1U)<<low);
}
}
