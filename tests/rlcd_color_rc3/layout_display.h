#pragma once
#include <algorithm>
#include <cstdarg>
#include <cstdio>
#include <functional>
#include <string>
#include <vector>
#include "esphome/core/color.h"
namespace esphome {
class GPIOPin {public:void setup(){}void digital_write(bool){}};
inline void delay(int){}
namespace display {
enum class TextAlign {
 TOP=0,CENTER_VERTICAL=1,BASELINE=2,BOTTOM=4,LEFT=0,CENTER_HORIZONTAL=8,RIGHT=16,
 TOP_LEFT=0,TOP_CENTER=8,TOP_RIGHT=16,CENTER_LEFT=1,CENTER=9,CENTER_RIGHT=17,
 BOTTOM_LEFT=4,BOTTOM_CENTER=12,BOTTOM_RIGHT=20
};
enum class DisplayType {DISPLAY_TYPE_COLOR};
class Display;
class BaseFont {public:virtual void measure(const char*,int*,int*,int*,int*)=0;
 virtual void print(int,int,Display*,Color,const char*,Color)=0;};
class Display {
 public:
 std::vector<std::string> trace;
 virtual void draw_absolute_pixel_internal(int,int,Color)=0;
 void draw_pixel_at(int x,int y,Color c){if(x>=0&&x<400&&y>=0&&y<300)draw_absolute_pixel_internal(x,y,c);}
 static std::string identity(std::string s){
  if(s=="FW: COLOR RC3.3")return "FW: MG902 RC3.3";
  if(s=="COLOR RC3.3")return "RLCD RC3.3";
  if(s=="SU/GIU: SCORRI  OK: CONFERMA  BACK: INDIETRO"||s=="KEY: SCORRI/LUNGO ANNULLA  BOOT: OK"||s=="KEY: AVANTI   BOOT: OK   BOOT LUNGO: INDIETRO")return "HELP";
  return s;
 }
 void record(const char *kind,int x,int y,int w,int h,Color c){
  trace.push_back(std::string(kind)+":"+std::to_string(x)+","+std::to_string(y)+","+std::to_string(w)+","+std::to_string(h)+","+(c.is_on()?"1":"0"));
 }
 void fill(Color c){record("fill",0,0,400,300,c);for(int y=0;y<300;y++)for(int x=0;x<400;x++)draw_pixel_at(x,y,c);}
 void line(int x,int y,int a,int b,Color c){
  record("line",x,y,a,b,c);
  int dx=abs(a-x),sx=x<a?1:-1,dy=-abs(b-y),sy=y<b?1:-1,error=dx+dy;
  for(;;){draw_pixel_at(x,y,c);if(x==a&&y==b)break;int twice=2*error;if(twice>=dy){error+=dy;x+=sx;}if(twice<=dx){error+=dx;y+=sy;}}
 }
 void rectangle(int x,int y,int w,int h,Color c){
  record("rect",x,y,w,h,c);
  for(int xx=x;xx<x+w;xx++){draw_pixel_at(xx,y,c);draw_pixel_at(xx,y+h-1,c);}
  for(int yy=y;yy<y+h;yy++){draw_pixel_at(x,yy,c);draw_pixel_at(x+w-1,yy,c);}
 }
 void filled_rectangle(int x,int y,int w,int h,Color c){
  record("filled",x,y,w,h,c);for(int yy=y;yy<y+h;yy++)for(int xx=x;xx<x+w;xx++)draw_pixel_at(xx,yy,c);
 }
 template<typename Image>void image(int x,int y,const Image&,Color,Color){record("image",x,y,400,300,Color());}
 void get_text_bounds(int x,int y,const char *s,BaseFont *f,TextAlign align,int *x1,int *y1,int *w,int *h){
  int offset,baseline;f->measure(s,w,&offset,&baseline,h);
  switch(int(align)&0x18){case 16:*x1=x-*w-offset;break;case 8:*x1=x-(*w+offset)/2;break;default:*x1=x;}
  switch(int(align)&7){case 4:*y1=y-*h;break;case 2:*y1=y-baseline;break;case 1:*y1=y-*h/2;break;default:*y1=y;}
 }
 void print(int x,int y,BaseFont *f,Color c,TextAlign align,const char *s){
  int xx,yy,w,h;get_text_bounds(x,y,s,f,align,&xx,&yy,&w,&h);
  // Trace nominal anchor and font height; only model/help strings may differ.
  int dummy,baseline,height;f->measure("X",&dummy,&dummy,&baseline,&height);
  record("print",x,y,height,int(align),c);trace.push_back(identity(s));
  f->print(xx,yy,this,c,s,Color());
 }
 void printf(int x,int y,BaseFont*f,Color c,TextAlign align,const char *fmt,...){
  char text[256];va_list ap;va_start(ap,fmt);vsnprintf(text,sizeof(text),fmt,ap);va_end(ap);print(x,y,f,c,align,text);
 }
};
class DisplayBuffer:public Display {public:
 std::function<void()> writer;virtual void setup(){}virtual void update(){}
 virtual DisplayType get_display_type()=0;
 protected:virtual int get_width_internal()=0;virtual int get_height_internal()=0;
 void do_update_(){trace.clear();writer();}
};
} // namespace display
} // namespace esphome
