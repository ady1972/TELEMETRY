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
constexpr int HIGH=1;
constexpr int MOCK_CS=10,MOCK_DC=9;
struct Wire {
 bool cs_high=true,dc_high=false,ram=false,closed=true;
 size_t position=0;unsigned chunks=0,largest=0;
 std::vector<uint16_t> commands;
 std::vector<uint8_t> payload;
 uint8_t panel[30000]{};
 void reset(){*this=Wire{};}
 void byte(uint8_t v){
  assert(!cs_high);
  if(!dc_high){
   assert(closed);ram=false;
   if(v==0x2C){
    const std::vector<uint16_t> full={0x2A,0x105,0x136,0x2B,0x100,0x1C7};
    assert(commands.size()>=6);
    assert(std::equal(full.begin(),full.end(),commands.end()-6));
    ram=true;position=0;payload.clear();
   }
  }
  commands.push_back((dc_high?0x100:0)|v);
 }
 void bytes(const uint8_t *p,size_t n){
  assert(!cs_high&&dc_high&&ram&&position+n<=30000);
  largest=std::max<unsigned>(largest,n);++chunks;closed=false;
  memcpy(panel+position,p,n);position+=n;payload.insert(payload.end(),p,p+n);
 }
} wire;
void digitalWrite(int pin,int value){
 if(pin==MOCK_CS){wire.cs_high=value==HIGH;if(wire.cs_high)wire.closed=true;}
 else if(pin==MOCK_DC)wire.dc_high=value==HIGH;else assert(false);
}
uint32_t micros(){return test_now*1000;}
struct MockSPI {
 void transfer(uint8_t v){wire.byte(v);}
 void transferBytes(const uint8_t*p,uint8_t *out,unsigned n){assert(!out);wire.bytes(p,n);}
};
struct GoatsSpiDiag {
 static constexpr uint8_t WHITE=0,BLACK=1,RED=2;
 static constexpr int CS=MOCK_CS,DC=MOCK_DC,TW=50,TH=200;
 MockSPI spi_;
 struct Canvas : display::Display {
  GoatsSpiDiag *owner;
  explicit Canvas(GoatsSpiDiag *p):owner(p){}
  void draw_pixel_at(int x,int y,Color c) override {
   owner->pixel_(x,y,c.is_on()?BLACK:WHITE);
   display::Display::draw_pixel_at(x,y,c);
  }
 } canvas_{this};
 font::Font *fonts_[13];
 uint8_t framebuffer_[30000]{},sent_frame_[30000]{};
 uint16_t flush_row_=200;bool sent_valid_=false;
 bool diagnostics_=false,delta_screen_=false,boot_down_=false;
 uint32_t boot_since_=0,boot_changed_=0,last_ui_=0;
 uint32_t updates_=0,bytes_=0,spi_us_=0,max_us_=0;
 GoatsSpiDiag(){std::copy(std::begin(::fonts),std::end(::fonts),fonts_);}
 void pixel_(int,int,uint8_t);void racing_draw_();void racing_flush_();void racing_cancel_();void boot_key_();
 void cmd_(uint8_t);void data_(uint8_t);uint32_t region_(int,int,int,int,const char*);
 void gps_diag_draw_(){memset(framebuffer_,0x0F,sizeof(framebuffer_));region_(0,0,400,300,"DIAG");}
 void drain(){unsigned guard=0;while(flush_row_<200){racing_flush_();assert(++guard<=13);}assert(wire.cs_high&&sent_valid_&&!memcmp(wire.panel,framebuffer_,30000));}
};
ACTUAL_PIXEL
ACTUAL_WIRE
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
 memset(c.framebuffer_,0xAA,30000);
 wire.reset();c.region_(0,0,400,300,"D3-REFERENCE");
 const auto reference_header=wire.commands;const auto reference_bytes=wire.payload;
 assert(reference_bytes.size()==30000&&wire.chunks==200&&wire.cs_high);
 wire.reset();c.flush_row_=0;c.drain();
 assert(wire.commands==reference_header&&wire.payload==reference_bytes);
 assert(wire.chunks==13&&wire.largest==2400);
 goats_ui::show_until()=0;goats_ui::best_until()=0;
 c.racing_draw_();c.drain();
 unsigned sent=wire.chunks;c.racing_draw_();assert(c.flush_row_==200);assert(wire.chunks==sent);
 c.pixel_(399,299,GoatsSpiDiag::BLACK);c.flush_row_=0;c.drain();assert(wire.chunks==sent+13);
 // Packing round-trip covers every logical pixel in a native 400x300 preview.
 for(int y=0;y<300;y++)for(int x=0;x<400;x++)c.pixel_(x,y,a[y*400+x]?c.BLACK:c.WHITE);
 for(int y=0;y<300;y++)for(int x=0;x<400;x++){
  int px=299-y,py=x,idx=(py/2)*150+px/2,bit=7-((px&1)*4+(py&1));
  unsigned value=((c.framebuffer_[idx]>>bit)&1)*2+((c.framebuffer_[idx]>>(bit-2))&1);
  assert(value==(a[y*400+x]?3:2));
 }
 c.flush_row_=0;c.drain();
 display::Display wire_picture;
 for(int y=0;y<300;y++)for(int x=0;x<400;x++){
  int px=299-y,py=x,idx=(py/2)*150+px/2,bit=7-((px&1)*4+(py&1));
  unsigned code=((wire.panel[idx]>>bit)&1)*2+((wire.panel[idx]>>(bit-2))&1);
  wire_picture.pixels[y*400+x]=code==3;
 }
 assert(wire_picture.pixels==a);wire_picture.save(out+"/racing_wire_full.pgm");
 // Interrupt an open stream: BOOT must close CS before diagnostic commands.
 live_delta=.123f;c.racing_draw_();c.racing_flush_();assert(!wire.cs_high&&c.flush_row_==16);
 // Short BOOT toggles diagnostics; transition baseline must include diagnostic ink.
 boot_level=0;test_now=1100;c.boot_key_();boot_level=1;test_now=1200;c.boot_key_();assert(c.diagnostics_);
 boot_level=0;test_now=1300;c.boot_key_();boot_level=1;test_now=1400;c.boot_key_();assert(!c.diagnostics_);c.drain();
 // Long BOOT selects Delta in RAM, keeping Racing and the GNSS/core untouched.
 boot_level=0;test_now=1500;c.boot_key_();boot_level=1;test_now=2800;c.boot_key_();assert(c.delta_screen_&&!c.diagnostics_);c.drain();
 puts("PASS: production renderer, pixel packing, full wire stream identical to DIAG3, SPI chunks <=2400 bytes, unchanged frame skipped, aborted stream/diagnostic restoration and BOOT switching");
}
