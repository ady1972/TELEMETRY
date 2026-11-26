#include <cassert>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>
#include <algorithm>
#include "goats_ubx_m9n_ak97_full.h"
#include "goats_font_bitmap.h"
namespace esphome {
inline uint32_t millis(){return clock_ms-500;}
namespace goats_spi_diag {
FONT_WIDTH_FUNCTION
struct Draw {std::string text;int x,y,size;};
class GoatsSpiDiag {
 public:
 static constexpr uint8_t WHITE=0,BLACK=1;
 esphome::uart::UARTComponent bus;
 esphome::uart::UARTComponent *gps_uart_{&bus};
 std::vector<Draw> draws;std::vector<uint8_t> pixels=std::vector<uint8_t>(400*300,255);
 void gps_diag_draw_();
 void rect_(int,int,int,int,uint8_t){draws.clear();std::fill(pixels.begin(),pixels.end(),255);}
 void font_text_(int x,int y,const char *s,int size,uint8_t,int align){
  const int width=font_width_(s,size);if(align==1)x-=width/2;else if(align==2)x-=width;
  assert(x>=0 && x+width<=400);auto table=goats_font::table(size);
  draws.push_back({s,x,y,size});
  for(unsigned at=0;s[at];at++){
   const auto &g=table.g[goats_font::idx(s[at])];assert(y+g.top>=0 && y+g.top+g.h<=300);
   for(int yy=0;yy<g.h;yy++)for(int xx=0;xx<g.w;xx++){
    const int bit=yy*g.w+xx;
    if(table.data[g.off+(bit>>3)]&(0x80>>(bit&7)))pixels[(y+g.top+yy)*400+x+xx]=0;
   }
   x+=g.advance;
  }
 }
 uint32_t region_(int,int,int,int,const char*){return 0;}
 bool speed(const char *s)const{
  std::string value;for(const auto &d:draws)if(d.size>=42 && d.y>=94 && d.y<145)value+=d.text;
  return value==s;
 }
 bool has(const char *s)const{for(const auto &d:draws)if(d.text==s)return true;return false;}
};
PANEL_FUNCTION
} }
using esphome::goats_spi_diag::GoatsSpiDiag;
int main(int argc,char **argv){
 GoatsSpiDiag page;auto &d=goats_gps_diag::counters;auto &m=goats_gps_diag::stability;auto &g=goats_m9n::state;
 clock_ms=0;page.gps_diag_draw_();
 assert(page.has("VISTI --") && page.has("USATI --") && page.has("HDOP --") && page.speed("--"));
 clock_ms=20000;
 d.bytes=100000;d.frames=1000;d.pvt=1000;d.last_pvt_ms=19960;d.last_byte_ms=19960;
 m.have_pvt=m.have_dop=m.have_sat=m.link_active=m.fix_active=m.have_step=true;
 m.fix_type=3;m.last_pvt=19960;m.last_dop=19900;m.last_sat=19000;
 m.fix_since=1000;m.last_fix_pvt=19960;m.step_ms=40;m.max_gap_ms=151;
 g.used_sats=13;g.visible_sats=29;g.hdop=0.7f;g.speed_kmh=72;g.fix=true;g.pvt_hz=25;
 page.gps_diag_draw_();
 assert(page.has("VISTI 29") && page.has("USATI 13") && page.has("HDOP 0.70") && page.speed("72.0"));
 assert(page.has("KM/H"));
 unsigned big_digits=0;for(const auto &text:page.draws)if(text.size==60)++big_digits;assert(big_digits==4);
 bool decimal_at_baseline=false;for(const auto &text:page.draws)if(text.text=="." && text.size==60 && text.y>120)decimal_at_baseline=true;assert(decimal_at_baseline);
 assert(page.has("DATI OK - FIX 3D") && page.has("PVT 25.0 Hz   ETA 40 ms"));
 assert(page.has("FIX CONT 0:18   PERSI 0"));
 if(argc>1){std::ofstream out(argv[1],std::ios::binary);out<<"P5\n400 300\n255\n";out.write(reinterpret_cast<const char*>(page.pixels.data()),page.pixels.size());}
 m.last_sat=14000;page.gps_diag_draw_();assert(page.has("VISTI --") && page.has("USATI 13") && page.has("HDOP 0.70"));
 m.have_dop=false;page.gps_diag_draw_();assert(page.has("HDOP --"));
 clock_ms=26001;m.tick(clock_ms);page.gps_diag_draw_();
 assert(page.has("VISTI --") && page.has("USATI --") && page.has("HDOP --") && page.speed("--"));
 assert(m.fix_losses==1 && m.stream_losses==1);
 auto p=std::vector<uint8_t>(92);p[20]=0;p[21]=0;m.frame(1,7,p.data(),p.size(),27000);clock_ms=27000;
 page.gps_diag_draw_();assert(page.has("DATI OK - ATTESA FIX") && page.speed("--"));
 p[20]=2;p[21]=1;m.frame(1,7,p.data(),p.size(),27040);clock_ms=27040;
 page.gps_diag_draw_();assert(page.has("DATI OK - FIX 2D") && page.speed("72.0"));
 p[20]=5;m.frame(1,7,p.data(),p.size(),27080);clock_ms=27080;
 page.gps_diag_draw_();assert(page.has("DATI OK - SOLO TEMPO") && page.speed("--"));
}
