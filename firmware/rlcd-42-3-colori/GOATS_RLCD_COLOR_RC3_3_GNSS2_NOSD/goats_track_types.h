#pragma once
#include <string>
#include <vector>
#include <cstdint>
// Tipi condivisi per i circuiti; nessuna dipendenza dalla UART GPS.
struct GoatsSectorUsb {
 std::string name; double lat1{},lon1{},lat2{},lon2{};
};
struct GoatsTrackUsb {
 std::string name; double start_lat{},start_lon{},finish_lat{},finish_lon{};
 float trigger_radius_m{20.0f}; uint8_t direction{0};
 std::vector<GoatsSectorUsb> sectors;
};
