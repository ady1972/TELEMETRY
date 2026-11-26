#pragma once
#include <algorithm>
#include <array>
#include <cassert>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>
#include "esphome/components/font/font.h"
using esphome::Color;
using esphome::COLOR_ON;
using esphome::COLOR_OFF;
using esphome::display::TextAlign;
inline uint32_t now_ms=10000;
inline uint32_t millis(){return now_ms;}
#define id(x) x
struct Image {Color get_pixel(int,int,Color,Color){return Color(0,0,0);}};
inline Image goats_splash_static;
struct Sensor {float state=NAN;bool has_state(){return false;}};
inline Sensor bat_percent;
namespace goats_usb_msc {inline bool usb=false;inline bool active(){return usb;}inline bool failed(){return false;}}
namespace goats_diag {
struct State {uint32_t last_pvt=9999,last_dop=9999,last_sat=9999;uint8_t used=18,seen=25;float hdop=0.8,pvt_hz=25,speed_kmh=88.1;};
inline State gps;inline State &data(){gps.last_pvt=gps.last_dop=gps.last_sat=now_ms-1;return gps;}}
namespace goats_b {
struct Track {std::string name;};
struct State {int active_track=0;std::vector<Track> tracks{{"LONATO"},{"CIRCUITO 2"},{"CIRCUITO 3"},{"CIRCUITO 4"},{"CIRCUITO 5"},{"CIRCUITO 6"}};};
inline State value;inline State &state(){return value;}}
namespace goats_ui {
inline bool post=false,best=false,visible=true;inline int selected_mode=2;
inline bool active(uint32_t){return post;}inline int mode(){return selected_mode;}
inline bool best_active(uint32_t){return best;}inline bool lit(uint32_t){return visible;}
inline bool settings(){return false;}inline int content(){return 0;}
inline uint32_t last_ms(){return 82456;}inline float last_delta(){return -0.123;}
inline uint32_t duration_ms(){return 3000;}inline bool best_enabled(){return true;}
inline uint32_t best_until(){return 16900;}inline uint32_t best_duration_ms(){return 3000;}
inline uint32_t best_time_ms(){return 82456;}}
namespace goats_menu {
inline int page=0,position=0;inline constexpr int CLOSING_SCREEN=16;
inline int screen(){return page;}inline int cursor(){return position;}
inline int selected_session(){return 0;}inline int selected_lap(){return 0;}
inline bool save_requested(){return true;}}
namespace goats_screen_mode {inline bool value=false;inline bool delta(){return value;}}
namespace goats_archive {
struct Record {uint32_t session=1,lap=1,lap_ms=82456;float avg_kmh=75;char track[32]="LONATO";};
inline int session_count(){return 6;}inline bool ready(){return true;}
inline int laps_in_session(int){return 6;}inline uint32_t best_retained_ms(int){return 82456;}
inline bool session_at(int i,uint32_t &sid,Record &r){sid=i+1;r=Record{};return true;}
inline bool lap_in_session(int,int i,Record &r){r=Record{};r.lap=i+1;r.lap_ms+=i*1000;return true;}
inline bool maximum_for(const Record&,float &v){v=98.1;return true;}}
namespace goats_dates {inline std::string text(uint32_t){return "26/11/2026 09:30";}}
namespace goats_clock {struct DateTime{};inline DateTime latest;inline uint32_t observed_ms=14000;
inline void format(DateTime,char *d,size_t dn,char *t,size_t tn){snprintf(d,dn,"26/11/2026");snprintf(t,tn,"09:30:00");}}
inline float live_delta=-0.119;
inline float goats_laptimer_live_delta_seconds(){return live_delta;}
inline uint32_t goats_laptimer_current_ms(uint32_t){return 83087;}
inline uint32_t goats_laptimer_best_lap_ms(){return 82456;}
inline float goats_laptimer_sector_display_delta_seconds(size_t i,uint32_t){return i==0?-0.12f:i==1?0.23f:NAN;}
