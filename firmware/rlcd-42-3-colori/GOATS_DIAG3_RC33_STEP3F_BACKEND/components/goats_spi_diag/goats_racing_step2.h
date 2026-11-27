#pragma once
#ifdef GOATS_RC33_STEP1_IMPL
// Racing body from firmware/rlcd-42/goats_rlcd_rc3_3.yaml; coordinate/font parity
// checked by tests. Canvas only paints the DIAG3 framebuffer, no hardware owner.
namespace goats_step2_render {
template<class Canvas,class Font> void draw(Canvas &it,Font **fonts,uint32_t now,bool screen_delta_mode){
 using esphome::Color;using esphome::display::TextAlign;
 const auto W=esphome::display::COLOR_ON;
 const auto B=esphome::display::COLOR_OFF;
 it.fill(B);
 const auto &g=goats_m9n::state;const auto &m=goats_gps_diag::stability;
 struct Snapshot {float hdop,speed_kmh;unsigned used,seen;};
 const Snapshot s{g.hdop,g.speed_kmh,g.used_sats,g.visible_sats};
 const auto &b=goats_b::state();
 const bool fresh_pvt=m.pvt_fresh(now),fresh_dop=m.dop_fresh(now),fresh_sat=m.sat_fresh(now);
 auto fmt_ms=[](uint32_t ms)->std::string {
  if(!ms)return "--:--.---";
  char t[24];snprintf(t,sizeof(t),"%lu:%02lu.%03lu",(unsigned long)(ms/60000U),(unsigned long)((ms/1000U)%60U),(unsigned long)(ms%1000U));return std::string(t);
 };
 auto choose_font=[&](const char *txt,int max_w,int max_h)->Font*{
  for(int i:{12,11,10,9,8,7,6,5,4,3,2}){
   int x,y,w,h;it.get_text_bounds(0,0,txt,fonts[i],TextAlign::TOP_LEFT,&x,&y,&w,&h);
   if(w<=max_w && h<=max_h)return fonts[i];
  }return fonts[2];
 };
// Barra inferiore: GPS a sinistra, circuito al centro, batteria ingrandita a destra.
// Solo rendering: nessuna modifica a UART/UBX/GPS.
it.line(0,267,399,267,W);
char gps_label[48];
if(fresh_pvt && fresh_sat && fresh_dop && s.hdop>=0.0f && s.hdop<99.0f)
  snprintf(gps_label,sizeof(gps_label),"GPS %u/%u - H:%.2f",(unsigned)s.used,(unsigned)s.seen,s.hdop);
else if(fresh_pvt && fresh_sat)
  snprintf(gps_label,sizeof(gps_label),"GPS %u/%u - H:--",(unsigned)s.used,(unsigned)s.seen);
else snprintf(gps_label,sizeof(gps_label),"GPS --/-- - H:--");
// FASE1 R04: GPS 20 px e circuito centrato fisicamente su x=200.
// Il GPS occupa la fascia sinistra; AUTO/nome e centrato nell'area libera.
it.print(2,271,fonts[2],W,TextAlign::TOP_LEFT,gps_label);
std::string top_track="AUTO";
if(b.active_track>=0 && b.active_track<(int)b.tracks.size())
  top_track=b.tracks[b.active_track].name;
// Centro reale dello schermo: x=200. Testo adattato allo spazio
// libero, senza coprire GPS o batteria.
const int gps_w=([&](){int x1,y1,w,h; fonts[2]->measure(gps_label,&x1,&y1,&w,&h);return w;})();
const int track_left=std::max(170, 2+gps_w+5);
const int track_right=365;
if(track_left<track_right) {
  const int track_center=std::max(200,(track_left+track_right)/2);
  const int max_width=2*std::min(track_center-track_left,track_right-track_center);
  while(!top_track.empty() && ([&](){int x1,y1,w,h; fonts[2]->measure(top_track.c_str(),&x1,&y1,&w,&h);return w;})()>max_width)
    top_track.pop_back();
  it.print(track_center,271,fonts[2],W,TextAlign::TOP_CENTER,top_track.c_str());
}
// Icona batteria maggiorata, entro i 400 px del display.
const int bx=369,by=272,bw=25,bh=19;
it.rectangle(bx,by,bw,bh,W);
it.filled_rectangle(bx+bw,by+6,4,7,W);
// Battery level deliberately unknown: no ADC or power wiring assumed.
// Delta live del motore racing.
// R08: il post-giro usa lo stesso clock del LAP TIME.
// Nessun valore live puo' sovrascrivere il delta dell'ultimo giro.
const bool post_blink=goats_ui::active(now) && goats_ui::mode()==2
                      && !goats_ui::best_active(now);
const bool post_visible=!post_blink || goats_ui::lit(now);
const float delta=post_blink ? goats_ui::last_delta()
                             : goats_laptimer_live_delta_seconds();
const bool delta_negative=std::isfinite(delta) && delta<0.0f;
// R10: inversione basata sul delta LIVE effettivo, non sul valore
// trattenuto dal riepilogo del giro precedente.
// Riempimento completo del riquadro 1..185 x 133..196.
const bool screen_delta=screen_delta_mode;
const bool post=goats_ui::active(now);
const uint32_t lap_ms=(post && goats_ui::mode()==2 && !goats_ui::best_active(now))?goats_ui::last_ms():goats_laptimer_current_ms(now);
const std::string lap=fmt_ms(lap_ms);
if(!screen_delta){
const bool invert_delta=delta_negative && (!post_blink || post_visible);
if(invert_delta) it.filled_rectangle(1,133,185,64,W);
else it.rectangle(1,133,185,64,W);
const Color delta_ink=invert_delta?B:W;
static const uint8_t label_delta[] = {0x00,0x00,0xE0,0x3F,0x87,0xBC,0x60,0xC6,0x04,0x60,0xC3,0xFC,0x3F,0x80,0x00,0x00,0x43,0x9C,0x7F,0x86,0x60,0x66,0x07,0xFC,0x7F,0xC0,0x00,0x00,0x07,0xFC,0x7F,0xC0,0x00,0x00,0x02,0x7C,0x67,0xC6,0x64,0x60,0xC6,0x0C,0x3F,0xC1,0xF8,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x0C,0x07,0xC3,0xF0,0x71,0x07,0x90,0x1F,0x80,0x3C,0x00,0x46,0x00,0x60,0x07,0xFC,0x7F,0xC6,0x00,0x60,0xC6,0x0C,0x00,0xC0,0x0C,0x7F,0xC7,0xFC,0x00,0x00,0x0C,0x64,0xC6,0x4C,0x64,0xC7,0xFC,0x7F,0xC0,0x00,0x00,0x01,0xF8,0x3F,0x86,0x0C,0x60,0xC6,0x0C,0x7F,0xC7,0xFC,0x00,0x00,0x00};
for(int py=0;py<72;++py) for(int px=0;px<12;++px){
  const int bi=py*12+px;
  if(label_delta[bi>>3] & (0x80>>(bi&7))) it.draw_pixel_at(5+px,131+py,delta_ink);
}
if(post_visible){
  if(std::isfinite(delta)){
    char delta_text[24];
    snprintf(delta_text,sizeof(delta_text),"%+.3f",delta);
    // Centro geometrico dell'area numerica x=24..183, y=134..195.
    // Calcolo dei limiti reali del font per centrare anche verticalmente.
    auto *df=choose_font(delta_text,155,58);
    int tx,ty,tw,th;
    it.get_text_bounds(0,0,delta_text,df,TextAlign::TOP_LEFT,&tx,&ty,&tw,&th);
    const int delta_x=24+(160-tw)/2-tx;
    const int delta_y=134+(62-th)/2-ty;
    it.print(delta_x,delta_y,df,delta_ink,TextAlign::TOP_LEFT,delta_text);
  } else if(!post_blink) {
    it.print(109,165,fonts[7],W,TextAlign::CENTER,"--.---");
  }
}
}else{
  it.rectangle(1,133,185,64,W);
  // LAP TIME ruotato a sinistra, allineato alla stessa fascia di BEST LAP.
  static const uint8_t label_lap_time[] = {0x00,0x00,0x00,0xC0,0x6C,0xC6,0xCC,0x6C,0xC6,0xFF,0xEF,0xFE,0x00,0x0F,0xFE,0xFF,0xEF,0xFE,0x7E,0x00,0x7E,0x01,0xE1,0xFC,0xFC,0x0F,0xFE,0xFF,0xE0,0x00,0x00,0x0F,0xFE,0xFF,0xE0,0x00,0xC0,0x0C,0x00,0xC0,0x0F,0xFE,0xFF,0xEC,0x00,0xC0,0x08,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x38,0x07,0xC0,0xC6,0x0C,0x60,0xC6,0x0F,0xFE,0xFF,0xE0,0x00,0x00,0x20,0x1E,0x1F,0xEF,0xF8,0xF1,0x8F,0xF8,0x1F,0xE0,0x1E,0x00,0x20,0x06,0x00,0x60,0x06,0x00,0x6F,0xFE,0xFF,0xE0,0x00};
  for(int py=0;py<60;++py) for(int px=0;px<12;++px){
    const int bi=py*12+px;
    if(label_lap_time[bi>>3] & (0x80>>(bi&7))) it.draw_pixel_at(5+px,135+py,W);
  }
  if(post_visible){
    // Area numerica x=24..183, y=134..195: font massimo senza tagli.
    auto *lf=choose_font(lap.c_str(),158,60);
    int tx,ty,tw,th;
    it.get_text_bounds(0,0,lap.c_str(),lf,TextAlign::TOP_LEFT,&tx,&ty,&tw,&th);
    const int lap_x=24+(160-tw)/2-tx;
    const int lap_y=134+(62-th)/2-ty;
    it.print(lap_x,lap_y,lf,W,TextAlign::TOP_LEFT,lap.c_str());
  }
}
// Best Lap: identico riquadro/layout, tempo preso dal motore giri TEST B.
it.rectangle(1,200,185,64,W);
static const uint8_t label_best[] = {0x00,0x00,0x00,0x3C,0x07,0xE0,0x66,0x06,0x60,0x7F,0xC7,0xFC,0x00,0x00,0x00,0x00,0xC0,0x7C,0x3F,0x07,0x10,0x79,0x01,0xF8,0x03,0xC0,0x0C,0x00,0xC0,0x0C,0x00,0xC7,0xFC,0x7F,0xC0,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x06,0x00,0x60,0x07,0xFC,0x7F,0xC6,0x00,0x60,0x06,0x00,0x03,0x86,0x7C,0x66,0xC6,0xC4,0x7C,0xC3,0xCC,0x00,0x00,0x00,0x00,0xC6,0x4C,0x64,0xC6,0x4C,0x7F,0xC7,0xFC,0x00,0x00,0x00,0x3F,0xC7,0xFC,0x64,0xC6,0x4C,0x7F,0xC7,0xFC,0x00,0x00,0x00};
for(int py=0;py<60;++py) for(int px=0;px<12;++px){
  const int bi=py*12+px;
  if(label_best[bi>>3] & (0x80>>(bi&7))) it.draw_pixel_at(5+px,201+py,W);
}
const std::string best=fmt_ms(goats_laptimer_best_lap_ms());
it.print(108,232,choose_font(best.c_str(),150,56),W,TextAlign::CENTER,best.c_str());
// Velocita' piu stretta, DELTA e BEST di pari altezza.
it.rectangle(189,133,210,131,W);
it.print(197,138,fonts[1],W,TextAlign::TOP_LEFT,"VELOCITA'");
char speed_text[20];
const float speed=fresh_pvt? (s.speed_kmh<3.0f?0.0f:s.speed_kmh):0.0f;
snprintf(speed_text,sizeof(speed_text),"%.0f",speed);
it.print(294,201,choose_font(speed_text,194,102),W,TextAlign::CENTER,speed_text);
it.print(389,258,fonts[1],W,TextAlign::BOTTOM_RIGHT,"km/h");
// Lap time esteso fino al bordo inferiore, settori inclusi: usa iTOW letti dalla TEST B per il tempo.
it.rectangle(1,1,398,128,W);
if(!screen_delta){
  it.print(9,4,fonts[0],W,TextAlign::TOP_LEFT,"LAP TIME");
  if(post_visible)it.print(202,50,choose_font(lap.c_str(),382,87),W,TextAlign::CENTER,lap.c_str());
  if(post && goats_ui::mode()==2 && !goats_ui::best_active(now))
    it.print(12,83,fonts[0],W,TextAlign::TOP_LEFT,"LAST LAP");
}else{
  const Color ink=delta_negative?B:W;
  if(delta_negative)it.filled_rectangle(2,2,396,88,W);
  it.print(9,4,fonts[0],ink,TextAlign::TOP_LEFT,"DELTA");
  char text[24];
  if(std::isfinite(delta))snprintf(text,sizeof(text),"%+.3f",(double)delta);
  else snprintf(text,sizeof(text),"--.---");
  if(post_visible)it.print(202,50,choose_font(text,382,87),ink,TextAlign::CENTER,text);
}
// TEST 13: riquadri settore piu alti e delta molto piu leggibile.
// Quando il delta e' disponibile, S1/S2/S3 scompare per lasciare tutto lo spazio al valore.
for(int i=0;i<3;++i){
  const int left=1+i*133;
  const int width=(i==2)?132:131;
  const int top=91, height=37;
  const float delta=goats_laptimer_sector_display_delta_seconds((size_t)i,now);
  const bool valid=std::isfinite(delta);
  const bool faster=valid && delta < -0.0005f;
  it.rectangle(left,top,width,height,W);
  if(faster) it.filled_rectangle(left+1,top+1,width-2,height-2,W);
  const auto ink=faster?B:W;
  if(valid){
    char delta_text[20];
    snprintf(delta_text,sizeof(delta_text),"%+.2f",(double)delta);
    it.print(left+width/2,top+height/2,fonts[3],ink,TextAlign::CENTER,delta_text);
  } else {
    it.printf(left+width/2,top+height/2,fonts[2],ink,TextAlign::CENTER,"S%d",i+1);
  }
}
const char *track="NO TRACK";
if(b.active_track>=0 && b.active_track<(int)b.tracks.size())
  track=b.tracks[b.active_track].name.c_str();
// Nome circuito gia presente nella barra superiore.
// Post-giro popup (non confondere con il timer in-line).
if(post && goats_ui::mode()==1 && !goats_ui::settings() && !goats_ui::best_active(now)){
  it.filled_rectangle(34,90,332,130,B);
  it.rectangle(34,90,332,130,W);
  it.print(200,98,fonts[2],W,TextAlign::TOP_CENTER,"ULTIMO GIRO");
  char tt[24]; snprintf(tt,sizeof(tt),"%lu:%02lu.%03lu",
    (unsigned long)(goats_ui::last_ms()/60000U),
    (unsigned long)((goats_ui::last_ms()/1000U)%60U),
    (unsigned long)(goats_ui::last_ms()%1000U));
  it.print(200,151,fonts[5],W,TextAlign::CENTER,tt);
  if(goats_ui::content()==0 && std::isfinite(goats_ui::last_delta())){
    const bool better=goats_ui::last_delta()<0.0f;
    if(better) it.filled_rectangle(85,175,230,32,W);
    it.printf(200,190,fonts[2],better?B:W,TextAlign::CENTER,"DELTA %+.3f",goats_ui::last_delta());
  }
}

// Best Lap a schermo intero: lampeggia solo il testo, come sul Guition.
if(goats_ui::best_active(now)){
  it.fill(B);
  const uint32_t started_at=goats_ui::best_until()-goats_ui::best_duration_ms();
  const bool text_visible=(((now-started_at)/500U)&1U)==0;
  if(text_visible){
    it.print(200,78,choose_font("NEW BEST LAP",376,68),W,TextAlign::CENTER,"NEW BEST LAP");
    const std::string record=fmt_ms(goats_ui::best_time_ms());
    it.print(200,182,choose_font(record.c_str(),376,112),W,TextAlign::CENTER,record.c_str());
  }
}
}
}
#endif // GOATS_RC33_STEP1_IMPL
