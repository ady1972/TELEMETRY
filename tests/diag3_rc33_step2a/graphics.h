#pragma once
#include <algorithm>
#include <cstdint>
#include <cstddef>
#include <string>
#include <vector>
#include <cstring>
#include <cstdio>
#include <cstdarg>
#include <fstream>
#include <cmath>
#include <cassert>
namespace esphome {
struct Color {bool on;bool is_on()const{return on;}};
namespace display {
constexpr Color COLOR_ON{true},COLOR_OFF{false};
// Same alignment values and font measure/position rules as ESPHome Display.
enum class TextAlign {TOP=0,CENTER_VERTICAL=1,BASELINE=2,BOTTOM=4,LEFT=0,CENTER_HORIZONTAL=8,RIGHT=16,TOP_LEFT=0,TOP_CENTER=8,CENTER=9,BOTTOM_RIGHT=20};
class Display;
}
namespace font {
struct Glyph {uint32_t code_point;const uint8_t *data;int advance,offset_x,offset_y,width,height;};
class Font {
 const Glyph *g_;int count_,baseline_,height_;
 public:
 Font(const Glyph*g,int n,int base,int h,int,int,int,int):g_(g),count_(n),baseline_(base),height_(h){}
 const Glyph *find_glyph(uint32_t c){for(int i=0;i<count_;i++)if(g_[i].code_point==c)return g_+i;return nullptr;}
 void measure(const char *s,int *w,int *xo,int *b,int *h){
  *b=baseline_;*h=height_;int x=0,min_x=0;bool first=true;
  for(;*s;s++){const Glyph *g=find_glyph(uint8_t(*s));if(!g){x+=g_[0].advance;continue;}
   min_x=first?g->offset_x:std::min(min_x,x+g->offset_x);first=false;x+=g->advance;}
  *xo=min_x;*w=x-min_x;
 }
 void print(int x,int y,display::Display *d,Color c,const char *s);
};
}
namespace display {
struct Display {
 std::vector<uint8_t> pixels=std::vector<uint8_t>(400*300);
 std::vector<std::string> strings;
 virtual void draw_pixel_at(int x,int y,Color c){if(x>=0&&x<400&&y>=0&&y<300)pixels[y*400+x]=c.on;}
 void fill(Color c){for(int y=0;y<300;y++)for(int x=0;x<400;x++)draw_pixel_at(x,y,c);strings.clear();}
 void filled_rectangle(int x,int y,int w,int h,Color c){for(int j=0;j<h;j++)for(int i=0;i<w;i++)draw_pixel_at(x+i,y+j,c);}
 void rectangle(int x,int y,int w,int h,Color c){for(int i=0;i<w;i++){draw_pixel_at(x+i,y,c);draw_pixel_at(x+i,y+h-1,c);}for(int j=0;j<h;j++){draw_pixel_at(x,y+j,c);draw_pixel_at(x+w-1,y+j,c);}}
 void line(int x,int y,int xx,int yy,Color c){assert(y==yy);filled_rectangle(x,y,xx-x+1,1,c);}
 void get_text_bounds(int x,int y,const char *s,font::Font *f,TextAlign a,int *ox,int *oy,int *w,int *h){
  int xo,base;f->measure(s,w,&xo,&base,h);
  const int ax=int(a)&0x18,ay=int(a)&7;
  *ox=ax==16?x-*w-xo:ax==8?x-(*w+xo)/2:x;
  *oy=ay==4?y-*h:ay==2?y-base:ay==1?y-*h/2:y;
 }
 void print(int x,int y,font::Font*f,Color c,TextAlign a,const char *s){
  int ox,oy,w,h;get_text_bounds(x,y,s,f,a,&ox,&oy,&w,&h);f->print(ox,oy,this,c,s);strings.emplace_back(s);
 }
 void printf(int x,int y,font::Font*f,Color c,TextAlign a,const char *fmt,...){
  char s[256];va_list args;va_start(args,fmt);vsnprintf(s,sizeof(s),fmt,args);va_end(args);print(x,y,f,c,a,s);
 }
 bool has(const char *s)const{return std::find(strings.begin(),strings.end(),s)!=strings.end();}
 void save(const std::string &path){std::ofstream o(path,std::ios::binary);o<<"P5\n400 300\n255\n";for(auto p:pixels)o.put(p?0:255);}
};
}
inline void font::Font::print(int x,int y,display::Display *d,Color c,const char *s){
 for(;*s;++s){auto *g=find_glyph(uint8_t(*s));if(!g){x+=g_[0].advance;continue;}
  for(int j=0;j<g->height;j++)for(int i=0;i<g->width;i++){int bit=j*g->width+i;if(g->data[bit/8]&(0x80>>(bit&7)))d->draw_pixel_at(x+g->offset_x+i,y+g->offset_y+j,c);}
  x+=g->advance;
 }
}
}
