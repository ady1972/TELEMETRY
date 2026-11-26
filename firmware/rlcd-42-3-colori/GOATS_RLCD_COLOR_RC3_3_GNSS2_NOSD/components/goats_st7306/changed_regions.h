#pragma once
#include <cstddef>
#include <cstdint>
#include <cstring>

namespace esphome::goats_st7306 {
// One controller group = 6x2 physical pixels = 3 bytes. Never transmit an
// unchanged group between unrelated dirty runs. Coalesce adjacent rows while
// every group in the rectangle is dirty; sent is updated only after the write.
template<typename Write> void flush_changed(const uint8_t *frame, uint8_t *sent,
                                            bool first, Write write) {
  constexpr int COLS = 50, ROWS = 200, STRIDE = COLS * 3;
  if (first) {
    write(0, COLS, 0, ROWS);
    std::memcpy(sent, frame, STRIDE * ROWS);
    return;
  }
  auto dirty = [&](int row, int col) {
    const int at = row * STRIDE + col * 3;
    return std::memcmp(frame + at, sent + at, 3) != 0;
  };
  for (int row = 0; row < ROWS; ++row) {
    for (int col = 0; col < COLS;) {
      if (!dirty(row, col)) { ++col; continue; }
      const int left = col;
      while (col < COLS && dirty(row, col)) ++col;
      int bottom = row + 1;
      while (bottom < ROWS) {
        bool complete = true;
        for (int x = left; x < col; ++x) {
          if (!dirty(bottom, x)) { complete = false; break; }
        }
        if (!complete) break;
        ++bottom;
      }
      write(left, col, row, bottom);
      for (int y = row; y < bottom; ++y)
        std::memcpy(sent + y * STRIDE + left * 3, frame + y * STRIDE + left * 3, (col - left) * 3);
    }
  }
}
}  // namespace esphome::goats_st7306
