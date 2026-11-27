#include "goats_st7306.h"
#include "changed_regions.h"
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
int main(){
 test_regions();
 Probe d;esphome::GPIOPin dc,reset;d.set_dc_pin(&dc);d.set_reset_pin(&reset);d.setup();
 bool changed=false;
 d.writer=[&](){
  for(int y=0;y<300;y++)for(int x=0;x<400;x++)
   d.draw_absolute_pixel_internal(x,y,esphome::Color(0,0,0));
  if(changed){d.draw_absolute_pixel_internal(10,10,esphome::Color(255,0,0));
              d.draw_absolute_pixel_internal(390,290,esphome::Color(255,255,255));}
 };
 d.update();assert(d.last_transfer_bytes()==30000&&d.last_windows()==1&&d.framebuffer_==d.sent_);
 d.update();assert(d.last_transfer_bytes()==0&&d.last_windows()==0);
 const auto before=d.framebuffer_;
 changed=true;d.update();assert(d.framebuffer_==d.sent_);
 assert(d.last_transfer_bytes()==dirty_bytes(before,d.framebuffer_));
 assert(d.last_transfer_bytes()<=old_row_bytes(before,d.framebuffer_));
 assert(d.last_transfer_bytes()==6);
 d.update();assert(d.last_transfer_bytes()==0);
}
