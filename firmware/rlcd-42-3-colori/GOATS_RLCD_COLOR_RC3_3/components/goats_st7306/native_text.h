#pragma once
#include "native_glyphs.h"
#include <algorithm>
#include <string>

namespace esphome::goats_st7306::native {
// GTC3 names use UTF-8. Latin-1 characters have native glyphs in the small faces;
// unsupported codepoints consume the whole UTF-8 sequence and render one '?'.
inline unsigned next_codepoint(const char *&s) {
  const auto first = static_cast<uint8_t>(*s++);
  if (first < 128) return first;
  unsigned code = first & (first < 224 ? 31 : first < 240 ? 15 : 7);
  const int count = first >= 194 && first < 224 ? 1 : first < 240 && first >= 224 ? 2 :
                    first >= 240 && first <= 244 ? 3 : 0;
  if (!count) return '?';
  for (int i = 0; i < count; ++i) {
    const auto c = static_cast<uint8_t>(*s);
    if ((c & 0xC0) != 0x80) return '?';
    ++s; code = (code << 6) | (c & 63);
  }
  return code;
}
inline const Glyph &glyph(const Face &face, unsigned code) {
  if (code < 32 || code > static_cast<unsigned>(face.last)) code = '?';
  return face.glyphs[code - 32];
}
struct Bounds { int left{0}, top{0}, width{0}, height{0}; };
inline Bounds measure(const Face &face, const char *s) {
  int cursor = 0, left = 0, top = 0, right = 0, bottom = 0;
  bool have_ink = false;
  while (*s) {
    const auto &g = glyph(face, next_codepoint(s));
    if (g.width && g.height) {
      const int x = cursor + g.left;
      if (!have_ink) { left=x; top=g.top; right=x+g.width; bottom=g.top+g.height; have_ink=true; }
      else { left=std::min(left,x); top=std::min(top,int(g.top));
             right=std::max(right,x+g.width); bottom=std::max(bottom,g.top+g.height); }
    }
    cursor += g.advance;
  }
  return {left, top, right-left, bottom-top};
}
inline const Face *fit(const char *text, int w, int h, int max_size) {
  for (const auto &face : faces) {
    if (face.size > max_size) continue;
    const auto bounds = measure(face, text);
    if (bounds.width <= w && bounds.height <= h) return &face;
  }
  return nullptr;
}
// The glyph is rasterized at the selected size. No horizontal squeezing,
// enlarged pixels, isolated-hole filling, temporal dithering or anti-aliasing.
template<typename Pixel> bool draw(const char *text, int x, int y, int w, int h,
                                  int max_size, Pixel pixel) {
  const auto *face = fit(text, w, h, max_size);
  if (!face) return false;
  const auto b = measure(*face, text);
  int cursor = x + (w-b.width)/2 - b.left;
  const int baseline = y + (h-b.height)/2 - b.top;
  const char *s = text;
  while (*s) {
    const auto &g = glyph(*face, next_codepoint(s));
    for (int yy = 0; yy < g.height; ++yy) for (int xx = 0; xx < g.width; ++xx) {
      const unsigned at = yy*g.width+xx;
      if (face->bits[g.offset + at/8] & (0x80 >> (at&7)))
        pixel(cursor+g.left+xx, baseline+g.top+yy);
    }
    cursor += g.advance;
  }
  return true;
}
}  // namespace esphome::goats_st7306::native
