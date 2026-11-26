#include "goats_st7306.h"
#include "pixel_pack.h"

#include <cmath>
#include <cstdio>
#include <cstring>
namespace esphome::goats_st7306 {
static const char *const TAG="goats_st7306";
void GoatsST7306::cmd_(uint8_t value) {
 dc_pin_->digital_write(false); this->enable(); this->write_byte(value); this->disable();
}
void GoatsST7306::data_(uint8_t value) {
 dc_pin_->digital_write(true); this->enable(); this->write_byte(value); this->disable();
}
void GoatsST7306::controller_init_() {
  ESP_LOGI(TAG, "INIT: sequenza ST7306 LPM, inizio");
  cmd_(0xD6); data_(0x17); data_(0x02);
  cmd_(0xD1); data_(0x01);
  cmd_(0xC0); data_(0x08); data_(0x00);
  cmd_(0xC1); for (int i=0;i<4;i++) data_(0x2C);
  cmd_(0xC2); for (int i=0;i<4;i++) data_(0x26);
  cmd_(0xC4); for (int i=0;i<4;i++) data_(0x42);
  cmd_(0xC5); for (int i=0;i<4;i++) data_(0x32);
  cmd_(0xB2); data_(0x12);
  const uint8_t b3[] = {0xE5,0xF6,0x05,0x46,0x77,0x77,0x77,0x77,0x76,0x45};
  cmd_(0xB3); for (uint8_t v : b3) data_(v);
  const uint8_t b4[] = {0x05,0x46,0x77,0x77,0x77,0x77,0x77,0x76,0x45};
  cmd_(0xB4); for (uint8_t v : b4) data_(v);
  cmd_(0xB7); data_(0x13);
  cmd_(0xB0); data_(0x64);
  cmd_(0xC9); data_(0x00);
  cmd_(0x11); delay(400);
  cmd_(0x36); data_(0x80);
  cmd_(0x3A); data_(0x11);
  cmd_(0xB9); data_(0x20);
  cmd_(0xB8); data_(0x09);
  cmd_(0xD0); data_(0xFF);
  cmd_(0x72); data_(0x13);
  cmd_(0x39);
  cmd_(0x29); delay(200);
  ESP_LOGI(TAG, "INIT: sequenza comandi trasmessa; nessun ACK LCD disponibile");
}
#include "goats_font_bitmap.h"
#include "goats_speed_95.h"
#include "goats_layout39_font.h"
static int font_width_(const char* str,int size) {
 auto t=goats_font::table(size);int w=0;
 for(int i=0;str[i];i++)w+=t.g[goats_font::idx(str[i])].advance;
 return w;
}
void GoatsST7306::font_text_(int x,int y,const char* str,int size,uint8_t color,int align) {
 auto t=goats_font::table(size);int xx=x;
 const int w=font_width_(str,size);
 if(align==1)xx-=w/2;else if(align==2)xx-=w;
 for(int k=0;str[k];k++){
  const auto &g=t.g[goats_font::idx(str[k])];
  const uint8_t *pix=t.data+g.off;
  for(int yy=0;yy<g.h;yy++)for(int col=0;col<g.w;col++){
   int j=yy*g.w+col;
   if(pix[j>>3]&(0x80>>(j&7)))pixel_(xx+col,y+g.top+yy,color);
  }
  xx+=g.advance;
 }
}
// V039: speed bitmap native-size; no enlarged 2x2 pixels.
// Glyphs are rasterized once from Roboto Condensed Bold 95pt.
void GoatsST7306::speed_native_(int cx,int cy,const char *value,uint8_t color){
  int width=0,height=0;
  for(int i=0;value[i];i++){
    int ix=goats_speed_font::index(value[i]);if(ix<0)continue;
    auto g=goats_speed_font::glyphs[ix];
    width+=g.w+2;
    if(g.h>height)height=g.h;
  }
  if(width<=0)return;
  width-=2;
  const int left=cx-width/2;
  const int top=cy-height/2;
  int cursor=0;
  for(int i=0;value[i];i++){
    int ix=goats_speed_font::index(value[i]);if(ix<0)continue;
    auto g=goats_speed_font::glyphs[ix];
    const uint8_t *bits=goats_speed_font::bitmap+g.offset;
    const int yy0=top+((value[i]=='.') ? (height-g.h-2) : (height-g.h)/2);
    for(int yy=0;yy<g.h;yy++)for(int xx=0;xx<g.w;xx++){
      const int j=yy*g.w+xx;
      const bool on=(bits[j>>3]&(0x80>>(j&7)))!=0;
      // V039: rifinitura conservativa SOLO del font velocita' a 95px.
      // Completa un foro di un singolo pixel quando tutti gli 8 vicini
      // appartengono al tratto. Non interviene su spigoli, segni o decimali.
      bool repair=false;
      if(!on && xx>0 && yy>0 && xx+1<g.w && yy+1<g.h){
        repair=true;
        for(int dy=-1;dy<=1 && repair;dy++)for(int dx=-1;dx<=1;dx++){
          if(dx==0 && dy==0)continue;
          const int k=(yy+dy)*g.w+(xx+dx);
          if(!(bits[k>>3]&(0x80>>(k&7)))){repair=false;break;}
        }
      }
      if(on || repair){
        const int tx=left+cursor+xx,ty=yy0+yy;
        if(tx>=7&&tx<=222&&ty>=62&&ty<=162)pixel_(tx,ty,color);
      }
    }
    cursor+=g.w+2;
  }
}
// Etichette verticali: bitmap trasferite dal firmware RLCD Layout 8 originale.
// Layout logico 400x300 (coordinate RLCD Layout 8).
// Il pannello fisico 300x400 e' ruotato: px=299-y, py=x.
// Manteniamo l'impacchettamento sperimentale V018, ora confermato leggibile.
// V039: conversione ST7306 RBW da TomatoGFX, ST7306_4P2_RBW_Driver::writePoint().
// Conferma colori: Zephyr drivers/display/display_st730x.c: 0=off, 1=red,
// 2=white, 3=black. Non utilizzare dithering alternato px%2.
// UN BYTE = 2x2 pixel fisici; sequenza bit:
//   x pari, y pari: bit 7 (color bit1), bit 5 (color bit0)
//   x pari, y disp: bit 6, bit 4
//   x disp, y pari: bit 3, bit 1
//   x disp, y disp: bit 2, bit 0
// L'indirizzo di memoria resta 150 byte/riga * 200 righe = 30000 byte.
void GoatsST7306::pixel_(int x,int y,uint8_t color) {
 pack_pixel(framebuffer_.data(),x,y,color);
}
void GoatsST7306::rect_(int x,int y,int w,int h,uint8_t color){
 int x0=x<0?0:x,y0=y<0?0:y,x1=x+w>400?400:x+w,y1=y+h>300?300:y+h;
 for(int yy=y0;yy<y1;yy++)for(int xx=x0;xx<x1;xx++)pixel_(xx,yy,color);
}
void GoatsST7306::border_(int x,int y,int w,int h,uint8_t col){
 rect_(x,y,w,2,col);rect_(x,y+h-2,w,2,col);rect_(x,y,2,h,col);rect_(x+w-2,y,2,h,col);
}
void GoatsST7306::text_(int x,int y,const char *str,uint8_t col,int sz){font_text_(x,y,str,sz,col,0);}
void GoatsST7306::vertical_(int x,int y,const char *str,uint8_t col,int sz){
 // Backwards-compatible fallback for short vertical labels (rotated native font).
 auto t=goats_font::table(sz);int off=0;
 for(int i=0;str[i];i++){
  const auto &g=t.g[goats_font::idx(str[i])];const uint8_t *bits=t.data+g.off;
  for(int yy=0;yy<g.h;yy++)for(int xx=0;xx<g.w;xx++){
   int j=yy*g.w+xx;if(bits[j>>3]&(0x80>>(j&7)))pixel_(x+yy,y+off+xx,col);
  }off+=g.advance;
 }
}
// Disegna +/- centrato sull'altezza dei numeri (anziche' allineato in alto).
// V0.40.4: fix ordine include; Delta Lap, punto decimale in basso come quello della velocita'.
// Disegno font nativo, senza ridimensionamenti: un pixel rimane un pixel.
// Ripara esclusivamente eventuali fori isolati di 1px dentro i tratti pieni;
// nessun filtro su contorni, decimale o segno +/-.
void GoatsST7306::signed_delta_(int center_x,int y,const char* value,int size,uint8_t color) {
  auto t=goats_font::table(size);
  const int total=font_width_(value,size);
  int xx=center_x-total/2;
  const int digit_h=t.g[goats_font::idx('0')].h;
  for(int k=0;value[k];k++){
    const char c=value[k];
    const auto &g=t.g[goats_font::idx(c)];
    const uint8_t *pix=t.data+g.off;
    const bool sign=(k==0 && (c=='+' || c=='-'));
    const int center_adjust=sign ? (digit_h-g.h)/2 : 0;
    const int dot_shift=(c=='.') ? 8 : 0;
    for(int yy=0;yy<g.h;yy++)for(int col=0;col<g.w;col++){
      const int j=yy*g.w+col;
      const bool on=(pix[j>>3]&(0x80>>(j&7)))!=0;
      bool fix=false;
      if(!on && c>='0' && c<='9' && col>0 && yy>0 && col+1<g.w && yy+1<g.h){
        fix=true;
        for(int dy=-1;dy<=1 && fix;dy++)for(int dx=-1;dx<=1;dx++){
          if(dx==0 && dy==0)continue;
          const int q=(yy+dy)*g.w+(col+dx);
          if(!(pix[q>>3]&(0x80>>(q&7)))){fix=false;break;}
        }
      }
      if(on||fix){
        const int tx=xx+col,ty=y+g.top+center_adjust+dot_shift+yy;
        if(tx>=246 && tx<396 && ty>=36 && ty<105)pixel_(tx,ty,color);
      }
    }
    xx+=g.advance;
  }
}

void GoatsST7306::native_label_(int x,int y,const uint8_t *bitmap,int w,int h,uint8_t col){
 for(int yy=0;yy<h;yy++)for(int xx=0;xx<w;xx++){
  const int j=yy*w+xx;if(bitmap[j>>3]&(0x80>>(j&7)))pixel_(x+xx,y+yy,col);
 }
}
static const uint8_t label_delta_original[] = {0x00,0x00,0xE0,0x3F,0x87,0xBC,0x60,0xC6,0x04,0x60,0xC3,0xFC,0x3F,0x80,0x00,0x00,0x43,0x9C,0x7F,0x86,0x60,0x66,0x07,0xFC,0x7F,0xC0,0x00,0x00,0x07,0xFC,0x7F,0xC0,0x00,0x00,0x02,0x7C,0x67,0xC6,0x64,0x60,0xC6,0x0C,0x3F,0xC1,0xF8,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x0C,0x07,0xC3,0xF0,0x71,0x07,0x90,0x1F,0x80,0x3C,0x00,0x46,0x00,0x60,0x07,0xFC,0x7F,0xC6,0x00,0x60,0xC6,0x0C,0x00,0xC0,0x0C,0x7F,0xC7,0xFC,0x00,0x00,0x0C,0x64,0xC6,0x4C,0x64,0xC7,0xFC,0x7F,0xC0,0x00,0x00,0x01,0xF8,0x3F,0x86,0x0C,0x60,0xC6,0x0C,0x7F,0xC7,0xFC,0x00,0x00,0x00};
static const uint8_t label_best_original[] = {0x00,0x00,0x00,0x3C,0x07,0xE0,0x66,0x06,0x60,0x7F,0xC7,0xFC,0x00,0x00,0x00,0x00,0xC0,0x7C,0x3F,0x07,0x10,0x79,0x01,0xF8,0x03,0xC0,0x0C,0x00,0xC0,0x0C,0x00,0xC7,0xFC,0x7F,0xC0,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x06,0x00,0x60,0x07,0xFC,0x7F,0xC6,0x00,0x60,0x06,0x00,0x03,0x86,0x7C,0x66,0xC6,0xC4,0x7C,0xC3,0xCC,0x00,0x00,0x00,0x00,0xC6,0x4C,0x64,0xC6,0x4C,0x7F,0xC7,0xFC,0x00,0x00,0x00,0x3F,0xC7,0xFC,0x64,0xC6,0x4C,0x7F,0xC7,0xFC,0x00,0x00,0x00};
// V021: blocchi laterali invertiti rispettando l'orientamento che ha gia' funzionato.
// Limiti disegno: 0..399 x 0..299. Larghezza minima 2 px per bordi.
void GoatsST7306::static_layout_(){
 rect_(0,0,400,300,WHITE);
 rect_(0,29,400,2,BLACK);
 font_text_(7,7,"GPS --/--",16,BLACK,0);
 font_text_(394,7,"GPS INIT",16,BLACK,2);
 // V039: velocita' pulita, senza sottoriquadro/etichetta inferiore.
 border_(1,33,227,137,BLACK);
 // Delta e Best sul lato sinistro della vista fisica.
 border_(230,33,169,75,BLACK);
 border_(230,111,169,59,BLACK);
 // Cronometro a tutta larghezza
 border_(1,173,398,80,BLACK);
 font_text_(10,176,"LAP TIME",16,BLACK,0);
 for(int i=0;i<3;i++)border_(1+133*i,256,132,21,BLACK);
 font_text_(67,258,"S1",16,BLACK,1);
 font_text_(200,258,"S2",16,BLACK,1);
 font_text_(333,258,"S3",16,BLACK,1);
 font_text_(394,282,"AUTO",16,BLACK,2);
}
// V039: font numerico nativo 82px, progressioni X corrette e baseline unica.
void GoatsST7306::lap_big_(int center,int y,const char* value,uint8_t color){
  using namespace goats_layout39_font;
  int width=0;
  for(int i=0;value[i];i++){int n=index(value[i]);if(n>=0)width+=lap_glyphs[n].advance;}
  int cur=center-width/2;
  for(int i=0;value[i];i++){
    const int n=index(value[i]);if(n<0)continue;
    const auto &g=lap_glyphs[n];
    const uint8_t* bits=lap_bits+g.offset;
    for(int yy=0; yy<g.h; yy++)for(int xx=0; xx<g.w; xx++){
      const int j=yy*g.w+xx;
      if((bits[j>>3]>>(7-(j&7)))&1){
         const int tx=cur+xx,ty=y+g.yshift+yy;
         if(tx>=6 && tx<396 && ty>=188 && ty<251)pixel_(tx,ty,color);
      }
    }
    cur+=g.advance;
  }
}
// V039: BEST LAP rasterizzato a 57px, ristretto solo orizzontalmente
// per mantenere la dimensione verticale e rispettare la label laterale.
void GoatsST7306::best_big_(int center_x,int center_y,uint8_t color){
  using namespace goats_layout39_font;
  const int left=center_x-best_width/2;
  const int top=center_y-best_height/2;
  for(int yy=0; yy<best_height; yy++)for(int xx=0; xx<best_width; xx++){
    const int j=yy*best_width+xx;
    if((best_bits[j>>3]>>(7-(j&7)))&1){
      const int tx=left+xx,ty=top+yy;
      if(tx>=247 && tx<396 && ty>=114 && ty<168)pixel_(tx,ty,color);
    }
  }
}

// BEST LAP dinamico, ingrandito e centrato come nella V039.
// Riduce eventualmente la sola larghezza del testo per la fascia da 149 px.
void GoatsST7306::best_dynamic_(int cx,int cy,const char *value,uint8_t color){
 auto t=goats_font::table(60);
 int width=0,min_y=999,max_y=-999;
 for(int k=0;value[k];k++){
   const auto &g=t.g[goats_font::idx(value[k])];
   width+=g.advance;
   if(g.top<min_y)min_y=g.top;
   if(g.top+g.h>max_y)max_y=g.top+g.h;
 }
 if(width<=0||min_y>max_y)return;
 const int height=max_y-min_y;
 const int shown_w=(width>149)?149:width;
 const int start_x=cx-shown_w/2;
 const int shown_h=(height>50)?50:height;
 const int start_y=cy-shown_h/2;
 int cursor=0;
 for(int k=0;value[k];k++){
   const auto &g=t.g[goats_font::idx(value[k])];
   const uint8_t *bits=t.data+g.off;
   for(int yy=0;yy<g.h;yy++)for(int xx=0;xx<g.w;xx++){
     const int j=yy*g.w+xx;
     if(!(bits[j>>3]&(0x80>>(j&7))))continue;
     const int tx=start_x+(cursor+xx)*shown_w/width;
     const int ty=start_y+(g.top+yy-min_y)*shown_h/height;
     if(tx>=246&&tx<396&&ty>=114&&ty<167)pixel_(tx,ty,color);
   }
   cursor+=g.advance;
 }
}
void GoatsST7306::clock_(){
 const uint32_t ms=racing_.clock_ms;
 char b[24];snprintf(b,sizeof(b),"%lu:%02lu.%03lu",
  (unsigned long)(ms/60000),(unsigned long)((ms/1000)%60),(unsigned long)(ms%1000));
 static constexpr int CLOCK_Y=188,CLOCK_H=63;
 rect_(6,CLOCK_Y,390,CLOCK_H,WHITE);
 if(!(racing_.blink_clock && !racing_.lit)) lap_big_(200,CLOCK_Y,b,BLACK);
 region_(6,CLOCK_Y,390,CLOCK_H,"LAP20");
}
void GoatsST7306::status_draw_(){

 rect_(3,3,394,24,WHITE);
 char b[64];
 const auto &g=racing_;
 snprintf(b,sizeof(b),"GPS %u/%u",(unsigned)g.used,(unsigned)g.seen);
 font_text_(7,7,b,16,BLACK,0);
 const char *name=racing_.track.c_str();
 char short_name[26];snprintf(short_name,sizeof(short_name),"%.21s",name);
 // Font 16px nativo; riduci solo se la pista invade l'area GPS.
 int track_font=16;
 while(short_name[0] && font_width_(short_name,track_font)>196){
   const size_t len=strlen(short_name);
   if(len<=1)break;
   short_name[len-1]='\0';
 }
 font_text_(394,7,short_name,track_font,BLACK,2);
 region_(3,3,394,24,"GPS-TOP");
}
void GoatsST7306::auxiliaries_(){

 char b[40];
 const bool blink=racing_.blink_delta;
 const float delta=racing_.delta;
 const bool have_delta=std::isfinite(delta);
 const bool worse=have_delta && delta>0.f; // positivo = giro piu lento.
 const uint8_t bg=(have_delta && !worse && (!blink || racing_.lit))?RED:WHITE;
 const uint8_t fg=(bg==RED)?WHITE:BLACK;
 rect_(232,35,165,71,bg);
 native_label_(233,35,label_delta_original,12,72,fg);
 if(have_delta){snprintf(b,sizeof(b),"%+0.3f",(double)delta);}else{strcpy(b,"--.---");}
 const int fs=font_width_(b,52)<=148?52:44;
 if(!blink || racing_.lit) signed_delta_(322,48,b,fs,fg);
 region_(232,35,165,71,"DELTA");
 rect_(232,113,165,55,WHITE);
 native_label_(233,113,label_best_original,12,60,BLACK);
 if(racing_.best_ms){
   // Best font V039 e' bitmap prerenderizzato del campione 1:22.987.
   // Per i dati veri usiamo un font dinamico, per non mostrare un tempo falso.
   const std::string t=racing_.best;
   best_dynamic_(322,140,t.c_str(),BLACK);
 } else font_text_(322,124,"--:--.---",28,BLACK,1);
 region_(232,113,165,55,"BEST");
 rect_(3,35,223,133,WHITE);
 const float raw=racing_.speed;
 const float speed=(raw>=3.f)?raw:0.f;
 snprintf(b,sizeof(b),"%.1f",(double)speed);
 speed_native_(114,112,b,BLACK);
 font_text_(10,39,"VELOCITA'",16,BLACK,0);
 region_(3,35,223,133,"SPEED");
 rect_(3,280,394,18,WHITE);
 snprintf(b,sizeof(b),"GIRI %lu",(unsigned long)racing_.laps);
 font_text_(5,280,b,16,BLACK,0);
 font_text_(394,280,!racing_.manual?"AUTO":"MANUALE",16,BLACK,2);
 region_(3,280,394,18,"GIRI");
 // Settori: delta visualizzato solo se realmente calcolato dall'engine.
 for(int i=0;i<3;i++){
   const int x=2+i*133;
   rect_(x+2,258,126,16,WHITE);
   const float d=racing_.sectors[i];
   if(std::isfinite(d)){snprintf(b,sizeof(b),"S%d %+0.2f",i+1,(double)d);}
   else{snprintf(b,sizeof(b),"S%d --",i+1);}
   font_text_(x+66,258,b,16,BLACK,1);
 }
 region_(2,256,396,21,"SECTORS");
}

void GoatsST7306::setup() {
 this->spi_setup(); dc_pin_->setup(); reset_pin_->setup();
 reset_pin_->digital_write(false); delay(200); reset_pin_->digital_write(true);
 controller_init_();
 framebuffer_.fill(0xFF); sent_.fill(0);
}
void GoatsST7306::draw_absolute_pixel_internal(int x,int y,Color color) {
 const bool red=color.red>color.green && color.red>color.blue;
 pixel_(x,y,red?RED:((color.red||color.green||color.blue)?BLACK:WHITE));
}
void GoatsST7306::draw_racing(const RacingData &data) {
 racing_=data;
 static_layout_(); status_draw_(); clock_(); auxiliaries_();
}
void GoatsST7306::update() {
 this->do_update_();
 // Trasmette solo i blocchi cambiati, allineati a gruppi di 6x2 pixel fisici.
 for(int row=0;row<TH;row++) {
   int left=TW, right=-1;
   for(int col=0;col<TW;col++) {
     const int at=(row*TW+col)*3;
     if(first_frame_ || std::memcmp(framebuffer_.data()+at,sent_.data()+at,3)!=0){
       left=std::min(left,col); right=col;
     }
   }
   if(right<left)continue;
   cmd_(0x2A); data_(0x05+left); data_(0x05+right);
   cmd_(0x2B); data_(row); data_(row); cmd_(0x2C);
   const int offset=(row*TW+left)*3, length=(right-left+1)*3;
   dc_pin_->digital_write(true); this->enable();
   this->write_array(framebuffer_.data()+offset,length); this->disable();
   std::memcpy(sent_.data()+offset,framebuffer_.data()+offset,length);
 }
 first_frame_=false;
}
}
