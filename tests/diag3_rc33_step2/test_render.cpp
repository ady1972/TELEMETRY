#define GOATS_RC33_STEP1_IMPL
#include "graphics.h"
using namespace esphome;
#include "glyphs.h"
uint32_t test_now=1000;
uint32_t millis(){return test_now;}
int boot_level=1;
constexpr int LOW=0;
int digitalRead(int pin){assert(pin==0);return boot_level;}
namespace goats_m9n {
struct {float hdop=.62f,speed_kmh=84;unsigned used_sats=18,visible_sats=29;}state;
}
namespace goats_gps_diag {struct {bool fresh=true;bool pvt_fresh(uint32_t)const{return fresh;}bool dop_fresh(uint32_t)const{return fresh;}bool sat_fresh(uint32_t)const{return fresh;}}stability;}
namespace goats_b {struct Track{std::string name;};struct State{int active_track=0;std::vector<Track>tracks{{"LONATO"}};};inline State &state(){static State s;return s;}}
uint32_t best_ms=82987,current_ms=83432;
float live_delta=-.247f;
bool best_event=false,lap_event=false;
bool goats_laptimer_consume_new_best_event(){bool v=best_event;best_event=false;return v;}
bool goats_laptimer_consume_lap_completed_event(){bool v=lap_event;lap_event=false;return v;}
uint32_t goats_laptimer_best_lap_ms(){return best_ms;}
uint32_t goats_laptimer_current_ms(uint32_t){return current_ms;}
uint32_t goats_laptimer_last_lap_ms(){return 83432;}
float goats_laptimer_post_lap_best_delta_seconds(){return .445f;}
float goats_laptimer_live_delta_seconds(){return live_delta;}
float goats_laptimer_sector_display_delta_seconds(size_t n,uint32_t){return n==0?-.12f:n==1?.18f:NAN;}
#include "rc33_goats_postlap_ui.h"
#include "goats_racing_step2.h"
struct GoatsSpiDiag {
 static constexpr uint8_t WHITE=0,BLACK=1,RED=2;
 uint8_t framebuffer_[30000]{},sent_frame_[30000]{},panel[30000]{};
 uint16_t flush_row_=200;
 bool diagnostics_=false,delta_screen_=false,boot_down_=false;
 uint32_t boot_since_=0,boot_changed_=0,last_ui_=0;
 unsigned transfers=0,largest=0;
 void pixel_(int,int,uint8_t);void racing_flush_();void boot_key_();
 uint32_t region_(int x,int y,int w,int h,const char*){
  assert(x%2==0&&w%2==0&&y==0&&h==300&&w<=32);
  const unsigned size=w/2*150;largest=std::max(largest,size);++transfers;
  memcpy(panel+x/2*150,framebuffer_+x/2*150,size);return 0;
 }
 void gps_diag_draw_(){memset(framebuffer_,0x0F,sizeof(framebuffer_));memcpy(panel,framebuffer_,30000);}
 void racing_draw_(){memset(framebuffer_,delta_screen_?0xAC:0xCA,sizeof(framebuffer_));flush_row_=0;}
 void drain(){unsigned guard=0;while(flush_row_<200){racing_flush_();assert(++guard<=201);}assert(!memcmp(panel,framebuffer_,30000));}
};
ACTUAL_PIXEL
ACTUAL_FLUSH_AND_BOOT
int main(int argc,char**argv){
 assert(argc==2);std::string out=argv[1];display::Display canvas;
 goats_step2_render::draw(canvas,fonts,1000,false);
 assert(canvas.has("LAP TIME")&&canvas.has("1:23.432")&&canvas.has("-0.247")&&canvas.has("1:22.987")&&canvas.has("84")&&canvas.has("GPS 18/29 - H:0.62"));
 for(auto xy:std::vector<std::pair<int,int>>{{1,1},{398,128},{1,200},{185,263},{189,133},{398,263},{0,267}})assert(canvas.pixels[xy.second*400+xy.first]);
 canvas.save(out+"/racing_lap_time.pgm");
 const auto a=canvas.pixels;
 goats_step2_render::draw(canvas,fonts,1000,true);assert(canvas.has("DELTA")&&canvas.pixels!=a);canvas.save(out+"/racing_delta.pgm");
 goats_gps_diag::stability.fresh=false;
 best_ms=current_ms=0;live_delta=NAN;
 goats_step2_render::draw(canvas,fonts,2000,false);assert(canvas.has("GPS --/-- - H:--")&&canvas.has("0")&&canvas.has("--:--.---"));canvas.save(out+"/racing_attesa_gps.pgm");
 best_ms=82987;best_event=lap_event=true;goats_ui::capture(3000);
 assert(!best_event&&!lap_event&&goats_ui::best_active(3000)&&goats_ui::last_ms()==83432);
 goats_step2_render::draw(canvas,fonts,3000,false);assert(canvas.has("NEW BEST LAP"));canvas.save(out+"/racing_new_best.pgm");
 goats_step2_render::draw(canvas,fonts,3500,false);assert(!canvas.has("NEW BEST LAP"));
 goats_ui::best_until()=0;goats_step2_render::draw(canvas,fonts,4000,false);assert(canvas.has("LAST LAP")&&canvas.has("1:23.432")&&canvas.has("+0.445"));
 GoatsSpiDiag c;
 memset(c.framebuffer_,0xAA,30000);c.flush_row_=0;c.drain();assert(c.transfers==13&&c.largest==2400);
 unsigned sent=c.transfers;c.flush_row_=0;c.drain();assert(c.transfers==sent);
 c.pixel_(399,299,GoatsSpiDiag::BLACK);c.flush_row_=0;c.drain();assert(c.transfers==sent+1);
 // Packing round-trip covers every logical pixel in a native 400x300 preview.
 for(int y=0;y<300;y++)for(int x=0;x<400;x++)c.pixel_(x,y,a[y*400+x]?c.BLACK:c.WHITE);
 for(int y=0;y<300;y++)for(int x=0;x<400;x++){
  int px=299-y,py=x,idx=(py/2)*150+px/2,bit=7-((px&1)*4+(py&1));
  unsigned value=((c.framebuffer_[idx]>>bit)&1)*2+((c.framebuffer_[idx]>>(bit-2))&1);
  assert(value==(a[y*400+x]?3:2));
 }
 c.flush_row_=0;c.drain();
 // Short BOOT toggles diagnostics; transition baseline must include diagnostic ink.
 boot_level=0;test_now=1100;c.boot_key_();boot_level=1;test_now=1200;c.boot_key_();assert(c.diagnostics_);
 boot_level=0;test_now=1300;c.boot_key_();boot_level=1;test_now=1400;c.boot_key_();assert(!c.diagnostics_);c.drain();
 // Long BOOT selects Delta in RAM, keeping Racing and the GNSS/core untouched.
 boot_level=0;test_now=1500;c.boot_key_();boot_level=1;test_now=2800;c.boot_key_();assert(c.delta_screen_&&!c.diagnostics_);c.drain();
 puts("PASS: production renderer with generated fonts, modes/stale GPS/alerts, pixel packing, SPI <=2400 bytes, no unchanged transfer, diagnostic restoration and BOOT switching");
}
