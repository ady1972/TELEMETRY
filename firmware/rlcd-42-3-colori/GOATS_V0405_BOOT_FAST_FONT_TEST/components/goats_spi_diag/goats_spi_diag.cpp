#include "goats_spi_diag.h"
#include "esphome/core/log.h"
#include "goats_track_catalog.h"
#include "goats_laptimer.h"
#include "goats_m9n_cfg.h"
#include "goats_ubx_m9n_ak97_full.h"
#include "goats_lap_storage.h"
#include <cmath>
#include <stdio.h>
#include <string.h>
namespace esphome { namespace goats_spi_diag {
static const char *const TAG="goats_spi_diag";
void GoatsSpiDiag::cmd_(uint8_t v) {
  digitalWrite(DC, LOW);
  digitalWrite(CS, LOW);
  spi_.transfer(v);
  digitalWrite(CS, HIGH);
}
void GoatsSpiDiag::data_(uint8_t v) {
  digitalWrite(DC, HIGH);
  digitalWrite(CS, LOW);
  spi_.transfer(v);
  digitalWrite(CS, HIGH);
}
void GoatsSpiDiag::controller_init_() {
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
void GoatsSpiDiag::font_text_(int x,int y,const char* str,int size,uint8_t color,int align) {
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
void GoatsSpiDiag::speed_native_(int cx,int cy,const char *value,uint8_t color){
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
void GoatsSpiDiag::pixel_(int x,int y,uint8_t color) {
 if(x<0||x>=400||y<0||y>=300)return;
 const int px=299-y,py=x;
 const int idx=(py/2)*150+(px/2);
 const int parity_y=py&1,parity_x=px&1;
 const int bit1=7-(parity_x*4+parity_y);
 const int bit0=bit1-2;
 uint8_t c=(color==BLACK)?3:((color==RED)?1:2);
 const uint8_t mask=uint8_t((1U<<bit1)|(1U<<bit0));
 const uint8_t v=uint8_t((((c>>1)&1U)<<bit1)|((c&1U)<<bit0));
 framebuffer_[idx]=(framebuffer_[idx]&uint8_t(~mask))|v;
}
void GoatsSpiDiag::rect_(int x,int y,int w,int h,uint8_t color){
 int x0=x<0?0:x,y0=y<0?0:y,x1=x+w>400?400:x+w,y1=y+h>300?300:y+h;
 for(int yy=y0;yy<y1;yy++)for(int xx=x0;xx<x1;xx++)pixel_(xx,yy,color);
}
void GoatsSpiDiag::border_(int x,int y,int w,int h,uint8_t col){
 rect_(x,y,w,2,col);rect_(x,y+h-2,w,2,col);rect_(x,y,2,h,col);rect_(x+w-2,y,2,h,col);
}
void GoatsSpiDiag::text_(int x,int y,const char *str,uint8_t col,int sz){font_text_(x,y,str,sz,col,0);}
void GoatsSpiDiag::vertical_(int x,int y,const char *str,uint8_t col,int sz){
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
void GoatsSpiDiag::signed_delta_(int center_x,int y,const char* value,int size,uint8_t color) {
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

void GoatsSpiDiag::native_label_(int x,int y,const uint8_t *bitmap,int w,int h,uint8_t col){
 for(int yy=0;yy<h;yy++)for(int xx=0;xx<w;xx++){
  const int j=yy*w+xx;if(bitmap[j>>3]&(0x80>>(j&7)))pixel_(x+xx,y+yy,col);
 }
}
uint32_t GoatsSpiDiag::region_(int x,int y,int w,int h,const char *label){
 // BBox trasformata: fisico X=299-logico Y, Y=logico X.
 int px=300-(y+h),py=x,pw=h,ph=w;
 int x0=(px<0?0:px)/6,x1=(px+pw+5)/6;
 int y0=(py<0?0:py)/2,y1=(py+ph+1)/2;
 if(x1>TW)x1=TW;if(y1>TH)y1=TH;
 if(x1<=x0||y1<=y0)return 0;
 uint32_t start=micros();
 cmd_(0x2A);data_(uint8_t(0x05+x0));data_(uint8_t(0x05+x1-1));
 cmd_(0x2B);data_(uint8_t(y0));data_(uint8_t(y1-1));cmd_(0x2C);
 digitalWrite(DC,HIGH);digitalWrite(CS,LOW);
 for(int yy=y0;yy<y1;yy++)spi_.transferBytes(framebuffer_+(yy*TW+x0)*3,nullptr,(x1-x0)*3);
 digitalWrite(CS,HIGH);
 uint32_t t=micros()-start;updates_++;bytes_+=(x1-x0)*(y1-y0)*3;spi_us_+=t;
 if(t>max_us_)max_us_=t;return t;
}
static const uint8_t label_delta_original[] = {0x00,0x00,0xE0,0x3F,0x87,0xBC,0x60,0xC6,0x04,0x60,0xC3,0xFC,0x3F,0x80,0x00,0x00,0x43,0x9C,0x7F,0x86,0x60,0x66,0x07,0xFC,0x7F,0xC0,0x00,0x00,0x07,0xFC,0x7F,0xC0,0x00,0x00,0x02,0x7C,0x67,0xC6,0x64,0x60,0xC6,0x0C,0x3F,0xC1,0xF8,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x0C,0x07,0xC3,0xF0,0x71,0x07,0x90,0x1F,0x80,0x3C,0x00,0x46,0x00,0x60,0x07,0xFC,0x7F,0xC6,0x00,0x60,0xC6,0x0C,0x00,0xC0,0x0C,0x7F,0xC7,0xFC,0x00,0x00,0x0C,0x64,0xC6,0x4C,0x64,0xC7,0xFC,0x7F,0xC0,0x00,0x00,0x01,0xF8,0x3F,0x86,0x0C,0x60,0xC6,0x0C,0x7F,0xC7,0xFC,0x00,0x00,0x00};
static const uint8_t label_best_original[] = {0x00,0x00,0x00,0x3C,0x07,0xE0,0x66,0x06,0x60,0x7F,0xC7,0xFC,0x00,0x00,0x00,0x00,0xC0,0x7C,0x3F,0x07,0x10,0x79,0x01,0xF8,0x03,0xC0,0x0C,0x00,0xC0,0x0C,0x00,0xC7,0xFC,0x7F,0xC0,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x06,0x00,0x60,0x07,0xFC,0x7F,0xC6,0x00,0x60,0x06,0x00,0x03,0x86,0x7C,0x66,0xC6,0xC4,0x7C,0xC3,0xCC,0x00,0x00,0x00,0x00,0xC6,0x4C,0x64,0xC6,0x4C,0x7F,0xC7,0xFC,0x00,0x00,0x00,0x3F,0xC7,0xFC,0x64,0xC6,0x4C,0x7F,0xC7,0xFC,0x00,0x00,0x00};
// V021: blocchi laterali invertiti rispettando l'orientamento che ha gia' funzionato.
// Limiti disegno: 0..399 x 0..299. Larghezza minima 2 px per bordi.
void GoatsSpiDiag::static_layout_(){
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
void GoatsSpiDiag::lap_big_(int center,int y,const char* value,uint8_t color){
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
void GoatsSpiDiag::best_big_(int center_x,int center_y,uint8_t color){
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
void GoatsSpiDiag::best_dynamic_(int cx,int cy,const char *value,uint8_t color){
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
void GoatsSpiDiag::clock_(){
 const uint32_t ms=goats_laptimer_display_current_ms(millis());
 char b[24];snprintf(b,sizeof(b),"%lu:%02lu.%03lu",
  (unsigned long)(ms/60000),(unsigned long)((ms/1000)%60),(unsigned long)(ms%1000));
 static constexpr int CLOCK_Y=188,CLOCK_H=63;
 rect_(6,CLOCK_Y,390,CLOCK_H,WHITE);
 lap_big_(200,CLOCK_Y,b,BLACK);
 region_(6,CLOCK_Y,390,CLOCK_H,"LAP20");
}
void GoatsSpiDiag::status_draw_(){
 if(screen_!=0)return;
 rect_(3,3,394,24,WHITE);
 char b[64];
 const auto &g=goats_m9n::state;
 snprintf(b,sizeof(b),"GPS %u/%u",(unsigned)g.used_sats,(unsigned)g.visible_sats);
 font_text_(7,7,b,16,BLACK,0);
 const auto *t=goats_tracks::get(track_index_);
 const char *name=t?t->name.c_str():"NO TRACK";
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
void GoatsSpiDiag::auxiliaries_(){
 if(screen_!=0)return;
 char b[40];
 const uint32_t now=millis();
 const float delta=goats_laptimer_display_delta_seconds(now);
 const bool have_delta=std::isfinite(delta);
 const bool worse=have_delta && delta>0.f; // positivo = giro piu lento.
 const uint8_t bg=(have_delta && !worse)?RED:WHITE;
 const uint8_t fg=(bg==RED)?WHITE:BLACK;
 rect_(232,35,165,71,bg);
 native_label_(233,35,label_delta_original,12,72,fg);
 if(have_delta){snprintf(b,sizeof(b),"%+0.3f",(double)delta);}else{strcpy(b,"--.---");}
 const int fs=font_width_(b,52)<=148?52:44;
 signed_delta_(322,48,b,fs,fg);
 region_(232,35,165,71,"DELTA");
 rect_(232,113,165,55,WHITE);
 native_label_(233,113,label_best_original,12,60,BLACK);
 if(goats_laptimer_best_lap_ms()){
   // Best font V039 e' bitmap prerenderizzato del campione 1:22.987.
   // Per i dati veri usiamo un font dinamico, per non mostrare un tempo falso.
   const std::string t=goats_laptimer_best_text();
   best_dynamic_(322,140,t.c_str(),BLACK);
 } else font_text_(322,124,"--:--.---",28,BLACK,1);
 region_(232,113,165,55,"BEST");
 rect_(3,35,223,133,WHITE);
 const float raw=goats_m9n::state.fix?goats_m9n::state.speed_kmh:0.f;
 const float speed=(raw>=3.f)?raw:0.f;
 snprintf(b,sizeof(b),"%.1f",(double)speed);
 speed_native_(114,112,b,BLACK);
 font_text_(10,39,"VELOCITA'",16,BLACK,0);
 region_(3,35,223,133,"SPEED");
 rect_(3,280,394,18,WHITE);
 snprintf(b,sizeof(b),"GIRI %lu",(unsigned long)goats_laptimer_lap_number());
 font_text_(5,280,b,16,BLACK,0);
 font_text_(394,280,auto_track_?"AUTO":"MANUALE",16,BLACK,2);
 region_(3,280,394,18,"GIRI");
 // Settori: delta visualizzato solo se realmente calcolato dall'engine.
 for(int i=0;i<3;i++){
   const int x=2+i*133;
   rect_(x+2,258,126,16,WHITE);
   const float d=goats_laptimer_sector_display_delta_seconds(i,now);
   if(std::isfinite(d)){snprintf(b,sizeof(b),"S%d %+0.2f",i+1,(double)d);}
   else{snprintf(b,sizeof(b),"S%d --",i+1);}
   font_text_(x+66,258,b,16,BLACK,1);
 }
 region_(2,256,396,21,"SECTORS");
}
void GoatsSpiDiag::choose_track_(int idx){
 if(idx==track_index_)return;
 track_index_=idx;goats_laptimer_reset();goats_lap_storage::end();was_running_=false;
 ESP_LOGI(TAG,"Circuito: %s",goats_tracks::get(idx)?goats_tracks::get(idx)->name.c_str():"nessuno");
}
void GoatsSpiDiag::clear_session_(){goats_laptimer_reset();goats_lap_storage::end();was_running_=false;}
void GoatsSpiDiag::gps_poll_(){
 if(!gps_uart_||!gps_configured_)return;
 // Una sola lettura UART e campioni GNSS ordinati (motore originale RLCD).
 goats_m9n::poll(gps_uart_);
 static std::vector<goats_m9n::NavSample> batch;
 goats_m9n::take_samples(batch,8);
 for(const auto &sm:batch){
   if(auto_track_ && sm.fix && track_index_<0 && millis()-last_circuit_scan_>=1000){
     last_circuit_scan_=millis();int idx=goats_tracks::nearest(sm.latitude,sm.longitude);
     if(idx>=0)choose_track_(idx);
   }
   goats_laptimer_update(goats_tracks::get(track_index_),sm.fix,sm.latitude,sm.longitude,
                         sm.speed_kmh,sm.now_ms,sm.gnss_itow_ms);
   bool running=goats_laptimer_running();
   if(running&&!was_running_){
     const auto*track=goats_tracks::get(track_index_);
     goats_lap_storage::new_session(track?track->name.c_str():"?",
        goats_m9n::state.date_text.c_str(),goats_m9n::state.time_text.c_str());
   }
   was_running_=running;
   if(goats_laptimer_consume_lap_completed_event()){
     goats_lap_storage::lap(goats_laptimer_lap_number(),goats_laptimer_last_lap_ms(),
       goats_laptimer_best_lap_ms(),goats_m9n::state.speed_kmh);
     ESP_LOGI(TAG,"LAP %u %lums best=%lums",(unsigned)goats_laptimer_lap_number(),
       (unsigned long)goats_laptimer_last_lap_ms(),(unsigned long)goats_laptimer_best_lap_ms());
   }
 }
}
void GoatsSpiDiag::menu_draw_(){
 rect_(0,0,400,300,WHITE);
 const char *name=screen_==1?"MENU":"CIRCUITI";
 font_text_(200,8,name,28,BLACK,1);
 rect_(4,39,392,2,BLACK);
 if(screen_==1){
   const char *labels[]={"GPS STATUS","CIRCUITO","AUTOTRACK","FINE SESSIONE","INFO","INDIETRO"};
   for(int i=0;i<6;i++){
     int y=48+i*37;
     if(menu_item_==i){rect_(10,y,378,34,BLACK);font_text_(24,y+4,labels[i],20,WHITE,0);}
     else font_text_(24,y+4,labels[i],20,BLACK,0);
   }
 }else if(screen_==2){
   const auto &g=goats_m9n::state;char b[64];
   snprintf(b,sizeof(b),"FIX %s  SAT %u/%u",g.fix?"SI":"NO",g.used_sats,g.visible_sats);
   font_text_(16,68,b,20,BLACK,0);
   snprintf(b,sizeof(b),"HDOP %.1f  UBX %.1f Hz",(double)g.hdop,(double)g.pvt_hz);
   font_text_(16,108,b,20,BLACK,0);
   snprintf(b,sizeof(b),"SPEED %.1f km/h",(double)g.speed_kmh);
   font_text_(16,148,b,20,BLACK,0);
 }else if(screen_==3){
   const int n=goats_tracks::tracks.size();
   if(n==0)font_text_(200,105,"NESSUN CIRCUITO",20,BLACK,1);
   else{
     for(int r=0;r<5;r++){
       int k=menu_item_-2+r;
       if(k<0||k>=n)continue;
       const int y=65+r*37;
       const bool selected=k==menu_item_;
       if(selected)rect_(10,y,378,34,BLACK);
       char b[40];snprintf(b,sizeof(b),"%s%.26s",k==track_index_?"* ":"  ",goats_tracks::tracks[k].name.c_str());
       font_text_(20,y+4,b,20,selected?WHITE:BLACK,0);
     }
   }
 }else if(screen_==4){
   font_text_(200,72,"GOATS 4.2 COLOR",28,BLACK,1);
   font_text_(200,124,"V0.40.4 RC - 28/10/26",20,BLACK,1);
   font_text_(200,162,"MG902 / M9N 25Hz",20,BLACK,1);
   font_text_(200,203,goats_lap_storage::ready?"NVS GIRI OK":"NVS GIRI NON DISP.",16,BLACK,1);
 }
 font_text_(200,279,"SU/GIU  INDIETRO  OK",16,BLACK,1);
 region_(0,0,400,300,"MENU");
}
void GoatsSpiDiag::menu_action_(){
 if(screen_==1){
   switch(menu_item_){
     case 0:screen_=2;break;
     case 1:screen_=3;menu_item_=track_index_>=0?track_index_:0;break;
     case 2:auto_track_=!auto_track_;break;
     case 3:clear_session_();screen_=0;static_layout_();break;
     case 4:screen_=4;break;
     default:screen_=0;static_layout_();break;
   }
 } else if(screen_==3){
   if(goats_tracks::get(menu_item_)){choose_track_(menu_item_);auto_track_=false;}
   screen_=0;static_layout_();
 }else{screen_=1;menu_item_=0;}
 if(screen_!=0)menu_draw_();else{status_draw_();clock_();auxiliaries_();}
}
void GoatsSpiDiag::buttons_(){
 const uint32_t now=millis();if(now-last_keys_<45)return;last_keys_=now;
 const int pins[]={KEY_UP,KEY_DOWN,KEY_BACK,KEY_OK};
 uint8_t keys=0;for(int i=0;i<4;i++)if(digitalRead(pins[i]))keys|=1u<<i;
 const uint8_t pressed=old_keys_ & (uint8_t)~keys;old_keys_=keys;
 if(!pressed)return;
 if(screen_==0){
   // Durante la gara solo SU/GIU riservati a luminosita' futura: senza BL non agiscono.
   // OK apre il menu solo a kart fermo, BACK non altera il lap timer.
   if((pressed&8) && goats_m9n::state.speed_kmh<3.f){screen_=1;menu_item_=0;menu_draw_();}
   return;
 }
 if(pressed&4){if(screen_==1){screen_=0;static_layout_();status_draw_();clock_();auxiliaries_();}
   else{screen_=1;menu_item_=0;menu_draw_();}return;}
 int n=(screen_==1)?6:(screen_==3?(int)goats_tracks::tracks.size():0);
 if(n){if(pressed&1)menu_item_=(menu_item_+n-1)%n;if(pressed&2)menu_item_=(menu_item_+1)%n;}
 if(pressed&8)menu_action_();else menu_draw_();
}

void GoatsSpiDiag::setup(){
 started_=millis();heartbeat_=started_;
 for(int pin:{KEY_UP,KEY_DOWN,KEY_BACK,KEY_OK})pinMode(pin,INPUT_PULLUP);
 old_keys_=0x0F;
 goats_tracks::load();
 ESP_LOGI(TAG,"V0402 RC: laptimer RLCD originale, UBX M9N, 4 keys; circuiti=%u",
   (unsigned)goats_tracks::tracks.size());
}
void GoatsSpiDiag::loop(){
 uint32_t now=millis(),elapsed=now-started_;
 if(now-heartbeat_>=10000){heartbeat_=now;
   ESP_LOGI(TAG,"V0402 uptime=%lu stage=%u fix=%u sats=%u pvt=%.1f Hz track=%d",
    (unsigned long)(elapsed/1000),stage_,goats_m9n::state.fix,goats_m9n::state.used_sats,
    (double)goats_m9n::state.pvt_hz,track_index_);}
 if(stage_==0&&elapsed>=0){pinMode(CS,OUTPUT);digitalWrite(CS,HIGH);stage_=1;}
 if(stage_==1&&elapsed>=10){pinMode(DC,OUTPUT);digitalWrite(DC,HIGH);stage_=2;}
 if(stage_==2&&elapsed>=20){pinMode(RES,OUTPUT);digitalWrite(RES,HIGH);stage_=3;}
 if(stage_==3&&elapsed>=30){digitalWrite(RES,LOW);delay(200);digitalWrite(RES,HIGH);stage_=4;}
 if(stage_==4&&elapsed>=250){spi_.begin(SCLK,-1,MOSI,CS);
   spi_.beginTransaction(SPISettings(4000000,MSBFIRST,SPI_MODE0));stage_=5;}
 if(stage_==5&&elapsed>=300){controller_init_();stage_=6;}
 if(stage_==6&&elapsed>=900){
   static_layout_();region_(0,0,400,300,"INITIAL");
   goats_lap_storage::begin();
   if(gps_uart_){goats_cfg::configure(*gps_uart_);gps_configured_=true;}
   last_lap_=last_aux_=stat_start_=millis();stage_=7;
   status_draw_();clock_();auxiliaries_();
 }
 if(stage_!=7)return;
 buttons_();gps_poll_();
 if(screen_==0){
   now=millis();
   if(now-last_lap_>=20){uint32_t dt=now-last_lap_;if(dt>=40)missed_+=dt/20-1;
     last_lap_=now;clock_();}
   if(now-last_aux_>=400){last_aux_=now;auxiliaries_();status_draw_();}
 }else if(screen_==2&&millis()-last_ui_>800){last_ui_=millis();menu_draw_();}
 if(millis()-stat_start_>=10000){ESP_LOGI(TAG,"V0402 PERF regions=%lu bytes=%lu spi=%luus max=%luus missed=%lu",
  (unsigned long)updates_,(unsigned long)bytes_,(unsigned long)spi_us_,
  (unsigned long)max_us_,(unsigned long)missed_);
  stat_start_=millis();updates_=bytes_=spi_us_=max_us_=missed_=0;}
}
void GoatsSpiDiag::dump_config(){ESP_LOGCONFIG(TAG,"GOATS V0402 RC: 400x300, MG902/M9N UBX, buttons 4/5/6/7");}
}}
