#include "goats_st7306.h"
#include "changed_regions.h"
#include "native_text.h"
#include <cassert>
#include <cstdio>
#include <fstream>
#include <limits>
#include <random>
#include <vector>
#include <set>
using namespace esphome::goats_st7306;
using Buffer=std::array<uint8_t,30000>;
struct Probe : GoatsST7306 {
  using GoatsST7306::framebuffer_;
  using GoatsST7306::sent_;
};
static unsigned dirty_bytes(const Buffer &a,const Buffer &b){
 unsigned result=0;for(size_t i=0;i<a.size();i+=3)if(std::memcmp(a.data()+i,b.data()+i,3))result+=3;
 return result;
}
static unsigned old_row_bytes(const Buffer &a,const Buffer &b){
 unsigned result=0;
 for(int row=0;row<200;row++){
  int first=50,last=-1;
  for(int col=0;col<50;col++)if(std::memcmp(a.data()+row*150+col*3,b.data()+row*150+col*3,3)){
   first=std::min(first,col);last=col;
  }
  if(last>=first)result+=(last-first+1)*3;
 }
 return result;
}
static void test_regions(){
 Buffer frame{},sent{};
 unsigned writes=0,bytes=0;
 auto check=[&](int l,int r,int t,int b){
  assert(l>=0&&l<r&&r<=50&&t>=0&&t<b&&b<=200);
  ++writes;bytes+=(r-l)*(b-t)*3;
 };
 flush_changed(frame.data(),sent.data(),true,check);
 assert(writes==1&&bytes==30000);
 writes=bytes=0;flush_changed(frame.data(),sent.data(),false,check);
 assert(writes==0&&bytes==0);
 // Simultaneous opposite corners must not retransmit any unchanged middle.
 frame[0]=1;frame[147]=2;
 writes=bytes=0;flush_changed(frame.data(),sent.data(),false,check);
 assert(writes==2&&bytes==6&&frame==sent);
 // A full-height narrow region is one address window, not 200.
 for(int row=0;row<200;row++)frame[row*150+30]=42;
 writes=bytes=0;flush_changed(frame.data(),sent.data(),false,check);
 assert(writes==1&&bytes==600&&frame==sent);
 std::mt19937 rng(33);
 for(int trial=0;trial<120;trial++){
  for(int n=0;n<trial*3;n++)frame[rng()%frame.size()]=rng()%256;
  const unsigned expected=dirty_bytes(frame,sent);
  const Buffer before=sent;
  std::array<bool,10000> covered{};
  writes=bytes=0;
  flush_changed(frame.data(),sent.data(),false,[&](int l,int r,int t,int b){
   check(l,r,t,b);
   for(int y=t;y<b;y++)for(int x=l;x<r;x++){
    const int at=y*50+x;assert(!covered[at]);covered[at]=true;
    assert(std::memcmp(frame.data()+at*3,before.data()+at*3,3)!=0);
   }
  });
  assert(bytes==expected&&frame==sent);
 }
}
static void test_fonts(){
 for(const char *text:{"0:00.000","1:22.987","12:59.999","-0.001","+123.456","--:--.---","--.---","199.9"}){
  for(auto box:{std::array<int,3>{388,60,95},{148,61,60},{148,49,60}}){
   const auto *font=native::fit(text,box[0],box[1],box[2]);assert(font);
   unsigned count=0;
   assert(native::draw(text,10,20,box[0],box[1],box[2],[&](int x,int y){
    assert(x>=10&&x<10+box[0]&&y>=20&&y<20+box[1]);++count;
   }));
   assert(count>0);
  }
 }
 assert(!native::draw("TEST",0,0,1,1,95,[](int,int){assert(false);}));
 // All large numeric outlines are unchanged native glyph bits: exact ink count.
 const char *s="+1:22.987";
 const auto *face=native::fit(s,388,60,95);assert(face);
 unsigned expected=0;
 for(const char *p=s;*p;){
  const auto &g=native::glyph(*face,native::next_codepoint(p));
  for(int k=0;k<g.width*g.height;k++)if(face->bits[g.offset+k/8]&(0x80>>(k&7)))++expected;
 }
 unsigned actual=0;
 native::draw(s,0,0,388,60,95,[&](int,int){++actual;});assert(actual==expected);
 for(const char *sample:{"Città","Évora","Straße","A\xF0\x9F\x8F\x81", "\xF0", "\x80"}){
  const char *p=sample;
  while(*p){const char *before=p;native::next_codepoint(p);assert(p>before);}
 }
}
static void preview(const char *path, const Buffer &buffer){
 std::ofstream f(path,std::ios::binary);f<<"P6\n400 300\n255\n";
 for(int y=0;y<300;y++)for(int x=0;x<400;x++){
  const int px=299-y,py=x,high=7-((px&1)*4+(py&1));
  const auto b=buffer[py/2*150+px/2];
  const int code=(((b>>high)&1)<<1)|((b>>(high-2))&1);
  const unsigned char rgb[3]={static_cast<unsigned char>(code==3?0:255),static_cast<unsigned char>(code==2?255:0),static_cast<unsigned char>(code==2?255:0)};
  f.write(reinterpret_cast<const char*>(rgb),3);
 }
}
int main(int argc,char **argv){
 test_regions();test_fonts();
 Probe d;esphome::GPIOPin dc,reset;d.set_dc_pin(&dc);d.set_reset_pin(&reset);d.setup();
 RacingData race;race.clock_ms=82987;race.best_ms=82456;race.speed=87.6;race.delta=-0.123;
 race.used=18;race.seen=25;race.laps=7;race.track="LONATO";
 race.sectors={-0.12,0.23,std::numeric_limits<float>::quiet_NaN()};
 d.writer=[&](){d.draw_racing(race);};
 d.update();assert(d.last_transfer_bytes()==30000&&d.last_windows()==1&&d.framebuffer_==d.sent_);
 const auto lap=d.framebuffer_;
 d.update();assert(d.last_transfer_bytes()==0&&d.last_windows()==0);
 race.clock_ms+=100;race.speed=88.1;race.delta=-0.119;
 d.update();
 assert(d.last_transfer_bytes()==dirty_bytes(lap,d.framebuffer_));
 assert(d.last_transfer_bytes()<=old_row_bytes(lap,d.framebuffer_));
 std::printf("Changing time/speed/delta: %u bytes vs old row envelope %u bytes, %u windows\n",
 d.last_transfer_bytes(),old_row_bytes(lap,d.framebuffer_),d.last_windows());
 if(argc>1)preview(argv[1],d.framebuffer_);
 race.delta_mode=true;d.update();assert(d.framebuffer_!=lap&&d.framebuffer_==d.sent_);
 if(argc>2)preview(argv[2],d.framebuffer_);
 d.update();assert(d.last_transfer_bytes()==0);
 race.blink_clock=race.blink_delta=true;race.lit=false;d.update();
 const auto hidden=d.framebuffer_;d.update();assert(d.last_transfer_bytes()==0);
 race.lit=true;d.update();assert(d.framebuffer_!=hidden);
 race.track="Una pista con un nome molto lungo àèìòù";d.update();
 assert(d.sent_==d.framebuffer_);
 // Page change followed by a static page causes no periodic write.
 d.writer=[&](){for(int y=0;y<300;y++)for(int x=0;x<400;x++)d.draw_absolute_pixel_internal(x,y,esphome::Color(0,0,0));};
 d.update();d.update();assert(d.last_transfer_bytes()==0);
}
