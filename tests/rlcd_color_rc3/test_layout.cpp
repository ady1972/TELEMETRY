#include "layout_host.h"
#include "generated_fonts.h"
#include "goats_st7306.h"
#include "generated_render.h"
struct Probe:esphome::goats_st7306::GoatsST7306 {using GoatsST7306::framebuffer_;};
static int pixel(const Probe &d,int x,int y){
 const int px=299-y,py=x,high=7-((px&1)*4+(py&1));const auto b=d.framebuffer_[py/2*150+px/2];
 return (((b>>high)&1)<<1)|((b>>(high-2))&1);
}
static void save(const char *path,const Probe &d){
 std::ofstream out(path,std::ios::binary);out<<"P6\n400 300\n255\n";
 for(int y=0;y<300;y++)for(int x=0;x<400;x++){
  int code=pixel(d,x,y);const unsigned char rgb[3]={static_cast<unsigned char>(code==3?0:255),static_cast<unsigned char>(code==2?255:0),static_cast<unsigned char>(code==2?255:0)};
  out.write(reinterpret_cast<const char*>(rgb),3);
 }
}
int main(int argc,char**argv){
 Probe mono,color;esphome::GPIOPin dc,reset;
 for(auto*d:{&mono,&color}){d->set_dc_pin(&dc);d->set_reset_pin(&reset);d->setup();}
 mono.writer=[&](){render_mono(mono);};color.writer=[&](){render_color(color);};
 mono.update();color.update();now_ms=14000;
 unsigned cases=0;
 for(int page=0;page<=16;page++)for(int mode=0;mode<2;mode++)for(int cursor=0;cursor<6;cursor++){
  goats_menu::page=page;goats_menu::position=cursor;goats_screen_mode::value=mode;
  mono.update();color.update();assert(mono.trace==color.trace);
  // Red is an intentional ink substitution; identities and help texts differ.
  const int bottom=page==0?300:page==4?220:250;
  for(int y=0;y<bottom;y++)for(int x=0;x<400;x++){
   int a=pixel(mono,x,y),b=pixel(color,x,y);if(b==1)b=3;
   if(a!=b){fprintf(stderr,"Mismatch page=%d mode=%d cursor=%d pixel=%d,%d mono=%d color=%d\n",page,mode,cursor,x,y,a,b);assert(false);}
  }
  ++cases;
 }
 goats_menu::page=0;goats_menu::position=0;goats_screen_mode::value=false;
 mono.update();color.update();assert(mono.trace==color.trace);
 assert(std::find(color.trace.begin(),color.trace.end(),"rect:1,1,398,128,1")!=color.trace.end());
 assert(std::find(color.trace.begin(),color.trace.end(),"rect:189,133,210,131,1")!=color.trace.end());
 if(argc>1)save(argv[1],color);
 goats_screen_mode::value=true;color.update();if(argc>2)save(argv[2],color);
 for(bool layout:{false,true})for(bool post:{false,true})for(bool best:{false,true})for(int mode=0;mode<3;mode++)for(bool lit:{false,true})for(float delta:{-0.119f,0.f,0.123f,NAN}){
  goats_screen_mode::value=layout;goats_ui::post=post;goats_ui::best=best;goats_ui::selected_mode=mode;goats_ui::visible=lit;live_delta=delta;
  mono.update();color.update();assert(mono.trace==color.trace);++cases;
 }
 goats_usb_msc::usb=true;mono.update();color.update();assert(mono.trace==color.trace);++cases;
 printf("PASS: %u reference/COLOR layout scenarios, exact drawing anchors, native ESPHome Font raster and matching logical pixels\n",cases);
}
