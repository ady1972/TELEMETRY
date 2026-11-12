#pragma once
namespace goats5::ui {
// Geometry contract only. RLCD's actual Racing renderer is not copied here.
constexpr int REFERENCE_WIDTH = 400;
constexpr int REFERENCE_HEIGHT = 300;
constexpr int PANEL_WIDTH = 800;
constexpr int PANEL_HEIGHT = 480;
constexpr int map_x(int x) { return x * PANEL_WIDTH / REFERENCE_WIDTH; }
constexpr int map_y(int y) { return y * PANEL_HEIGHT / REFERENCE_HEIGHT; }
}  // namespace goats5::ui
