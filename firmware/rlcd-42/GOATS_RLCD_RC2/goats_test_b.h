#pragma once
#include "esphome.h"
#include "goats_recording_clock.h"
#include <stdint.h>
#include <string>
#include <vector>
#include <cmath>
#include <algorithm>
#include <cstring>
#include <cstdio>
#include "driver/usb_serial_jtag.h"
#include "nvs.h"
#include "nvs_flash.h"
#include "goats_sd_usb_export.h"
namespace goats_diag { float trace_hdop(); }
namespace goats_racing { void consume(bool,double,double,float,uint32_t); }
namespace goats_gps_trace { void on_pvt(const uint8_t*,bool,double,double,float,uint32_t,uint8_t,float,const char*); }
namespace goats_archive { void export_csv(); }
namespace goats_b {
struct Sector {std::string name; double a,b,c,d;};
struct Track {std::string name; double a,b,c,d; float radius=20; uint8_t direction=0; std::vector<Sector> sectors;};
struct State {
 std::vector<Track> tracks;
 std::vector<uint8_t> raw;
 std::vector<uint8_t> incoming;
 std::string command;
 bool usb=false, receiving=false, tx_active=false, have_prev=false, armed=true, running=false;
 size_t need=0,tx_at=0; uint32_t expected_crc=0, last_tx=0, last_sample_itow=0;
 uint32_t laps=0, last_lap=0,best_lap=0,lap_start=0, last_cross=0, pvt_samples=0;
 double prev_lat=0,prev_lon=0,lat=0,lon=0; float speed=0;
 uint8_t fix_type=0,fix_ok=0,num_sv=0; int active_track=-1; bool manual_track=false; int auto_candidate=-1; uint8_t auto_hits=0;
};
inline State &state(){static State s;return s;}
inline uint16_t u16(const uint8_t*p){return uint16_t(p[0])|(uint16_t(p[1])<<8);}
inline uint32_t u32(const uint8_t*p){return uint32_t(p[0])|(uint32_t(p[1])<<8)|(uint32_t(p[2])<<16)|(uint32_t(p[3])<<24);}
inline int32_t i32(const uint8_t*p){return static_cast<int32_t>(u32(p));}
inline uint32_t crc32(const uint8_t *d,size_t n){uint32_t c=~0u;for(size_t i=0;i<n;i++){c^=d[i];for(int b=0;b<8;b++)c=(c>>1)^(0xEDB88320u & (0u-(c&1u)));}return ~c;}
inline void reply(const char *line){usb_serial_jtag_write_bytes(line,strlen(line),pdMS_TO_TICKS(40));usb_serial_jtag_write_bytes("\n",1,pdMS_TO_TICKS(40));}
// Track binary layout GTC3 v1, identical to GOATS RT Manager catalog.
template<typename T> inline bool read(const std::vector<uint8_t>&b,size_t &pos,T &v){if(pos+sizeof(T)>b.size())return false;memcpy(&v,b.data()+pos,sizeof(T));pos+=sizeof(T);return true;}
inline bool read_name(const std::vector<uint8_t>&b,size_t &pos,std::string &v){uint8_t n=0;if(!read(b,pos,n)||pos+n>b.size())return false;v.assign((const char*)b.data()+pos,n);pos+=n;return true;}
inline bool parse_catalog(const std::vector<uint8_t>&raw,std::vector<Track>&tracks){
 if(raw.size()<8||memcmp(raw.data(),"GTC3",4)!=0)return false;
 size_t pos=4; uint16_t ver=0,count=0;if(!read(raw,pos,ver)||!read(raw,pos,count)||ver!=1||count>50)return false;
 std::vector<Track> t;t.reserve(count);
 for(uint16_t i=0;i<count;i++){
  Track v;uint8_t sectors=0;
  if(!read_name(raw,pos,v.name)||!read(raw,pos,v.a)||!read(raw,pos,v.b)||!read(raw,pos,v.c)||!read(raw,pos,v.d)||!read(raw,pos,v.radius)||!read(raw,pos,v.direction)||!read(raw,pos,sectors)||sectors>12)return false;
  if(v.name.empty()||std::abs(v.a)>90||std::abs(v.c)>90||std::abs(v.b)>180||std::abs(v.d)>180)return false;
  for(int k=0;k<sectors;k++){Sector sector;if(!read_name(raw,pos,sector.name)||!read(raw,pos,sector.a)||!read(raw,pos,sector.b)||!read(raw,pos,sector.c)||!read(raw,pos,sector.d))return false;v.sectors.push_back(sector);}
  t.push_back(v);
 }
 if(pos!=raw.size())return false;
 tracks=std::move(t);return true;
}
inline bool save(const std::vector<uint8_t> &raw){nvs_handle_t h;if(nvs_open("goats_tracks",NVS_READWRITE,&h)!=ESP_OK)return false;esp_err_t e=nvs_set_blob(h,"catalog",raw.data(),raw.size());if(e==ESP_OK)e=nvs_set_u32(h,"catalog_crc",crc32(raw.data(),raw.size()));if(e==ESP_OK)e=nvs_commit(h);nvs_close(h);return e==ESP_OK;}
inline void setup(){auto &s=state();nvs_handle_t h;
 if(nvs_open("goats_tracks",NVS_READONLY,&h)==ESP_OK){size_t n=0;if(nvs_get_blob(h,"catalog",nullptr,&n)==ESP_OK&&n>=8&&n<=60000){std::vector<uint8_t> b(n);uint32_t stored=0;if(nvs_get_blob(h,"catalog",b.data(),&n)==ESP_OK&&nvs_get_u32(h,"catalog_crc",&stored)==ESP_OK&&stored==crc32(b.data(),b.size())&&parse_catalog(b,s.tracks)){s.raw=std::move(b);}}nvs_close(h);}
 usb_serial_jtag_driver_config_t cfg={};cfg.rx_buffer_size=8192;cfg.tx_buffer_size=4096;auto e=usb_serial_jtag_driver_install(&cfg);s.usb=e==ESP_OK||e==ESP_ERR_INVALID_STATE;
 // AUTO: nessuna pista selezionata finche non viene confermata la posizione GPS.
}
inline void command(std::string c){auto &s=state();if(goats_sd_usb_export::handle_command(c))return;if(c=="GSES_GET"){goats_archive::export_csv();return;}if(c=="GTRK_GET"){
 if(s.raw.empty()){s.raw={'G','T','C','3',1,0,0,0};}
 char msg[70];snprintf(msg,sizeof(msg),"GTRK_DATA %u %08lX",(unsigned)s.raw.size(),(unsigned long)crc32(s.raw.data(),s.raw.size()));reply(msg);s.tx_at=0;s.tx_active=true;s.last_tx=millis();return;
 }
 if(c=="GTRK_CLEAR"){std::vector<uint8_t> empty={'G','T','C','3',1,0,0,0};if(save(empty)){s.raw=empty;s.tracks.clear();s.active_track=-1;s.manual_track=false;s.laps=0;s.running=false;reply("GTRK_CLEAR_OK");}else reply("GTRK_ERR STORAGE");return;}
 unsigned long n=0,crc=0;if(sscanf(c.c_str(),"GTRK_BEGIN %lu %lx",&n,&crc)==2&&n>=8&&n<=60000){s.need=n;s.expected_crc=crc;s.incoming.clear();s.incoming.reserve(n);s.receiving=true;reply("GTRK_READY");return;}
 reply("GTRK_ERR COMMAND");
}
inline void tick_usb(){auto &s=state();if(!s.usb)return;
 uint8_t bytes[256];int n=usb_serial_jtag_read_bytes(bytes,sizeof(bytes),0);
 for(int i=0;i<n;i++){uint8_t b=bytes[i];if(s.receiving){s.incoming.push_back(b);if(s.incoming.size()==s.need){s.receiving=false;std::vector<Track> tracks;if(crc32(s.incoming.data(),s.incoming.size())!=s.expected_crc)reply("GTRK_ERR CRC");else if(!parse_catalog(s.incoming,tracks))reply("GTRK_ERR FORMAT");else if(!save(s.incoming))reply("GTRK_ERR STORAGE");else{s.raw=std::move(s.incoming);s.tracks=std::move(tracks);s.active_track=-1;s.manual_track=false;s.auto_candidate=-1;s.auto_hits=0;s.have_prev=false;s.running=false;s.laps=0;s.best_lap=s.last_lap=0;char ack[45];snprintf(ack,sizeof(ack),"GTRK_OK %u",(unsigned)s.tracks.size());reply(ack);}}}else if(b=='\n'){command(s.command);s.command.clear();}else if(b!='\r'&&s.command.size()<127)s.command.push_back((char)b);}
 if(s.tx_active){if(millis()-s.last_tx>12000){s.tx_active=false;reply("GTRK_ERR TX_TIMEOUT");}else if(s.tx_at<s.raw.size()){size_t n=std::min<size_t>(512,s.raw.size()-s.tx_at);int written=usb_serial_jtag_write_bytes(s.raw.data()+s.tx_at,n,0);if(written>0){s.tx_at+=(size_t)written;s.last_tx=millis();}}else{s.tx_active=false;reply("GTRK_END");}}
}
// Equirectangular local coordinates in meters: sufficient at kart circuit scale.
inline void xy(double lat,double lon,double ref,double &x,double &y){constexpr double R=6371000.0;double r=ref*0.017453292519943295; x=lon*0.017453292519943295*R*cos(r);y=lat*0.017453292519943295*R;}
inline bool crosses(const Track&t,double old_lat,double old_lon,double lat,double lon){double ref=(t.a+t.c)*0.5;double ax,ay,bx,by,px,py,qx,qy;xy(t.a,t.b,ref,ax,ay);xy(t.c,t.d,ref,bx,by);xy(old_lat,old_lon,ref,px,py);xy(lat,lon,ref,qx,qy);
 double dx=bx-ax,dy=by-ay,den=dx*dx+dy*dy;if(den<1)return false;
 auto side=[&](double x,double y){return dx*(y-ay)-dy*(x-ax);};double oldside=side(px,py),newside=side(qx,qy);
 if(!(oldside<0&&newside>=0)&&!(t.direction==0&&oldside>0&&newside<=0))return false;
 double frac=oldside/(oldside-newside);if(frac<0||frac>1)return false;
 double xx=px+frac*(qx-px),yy=py+frac*(qy-py);double along=((xx-ax)*dx+(yy-ay)*dy)/den;
 return along>=-0.15&&along<=1.15;
}
inline void on_pvt(const uint8_t *p,uint16_t len){if(len<92)return;auto&s=state();
 goats_clock::observe_pvt(p,millis());
 uint32_t itow=u32(p);if(s.pvt_samples&&itow==s.last_sample_itow)return;s.last_sample_itow=itow;s.pvt_samples++;
 s.fix_type=p[20];s.fix_ok=(p[21]&1)?1:0;s.num_sv=p[23];s.lon=i32(p+24)*1e-7;s.lat=i32(p+28)*1e-7;s.speed=i32(p+60)*0.0036f;
 bool valid=s.fix_type>=3&&s.fix_ok&&s.num_sv>=4&&std::abs(s.lat)<=90&&std::abs(s.lon)<=180;
 goats_racing::consume(valid,s.lat,s.lon,s.speed,itow);
 if(goats_session_ctl::paused()){s.have_prev=false;return;}
 if(!valid){s.have_prev=false;return;}
 // Riconoscimento automatico: entro 2 km dal centro traguardo, 3 fix consecutivi.
 // Non cambiare circuito durante un giro e rispettare la scelta manuale.
 if(!s.manual_track && !s.running && !s.tracks.empty()) {
   constexpr double rad=0.017453292519943295, earth=6371000.0;
   int nearest=-1; double best=2000.0;
   for(size_t i=0;i<s.tracks.size();++i){
     const auto &t=s.tracks[i];
     double clat=(t.a+t.c)*0.5, clon=(t.b+t.d)*0.5;
     double dy=(s.lat-clat)*rad*earth;
     double dx=(s.lon-clon)*rad*earth*cos(clat*rad);
     double dist=hypot(dx,dy);
     if(dist<best){best=dist;nearest=(int)i;}
   }
   if(nearest!=s.auto_candidate){s.auto_candidate=nearest;s.auto_hits=0;}
   if(nearest>=0 && s.auto_hits<3)++s.auto_hits;
   if(nearest>=0 && s.auto_hits>=3 && nearest!=s.active_track){
     s.active_track=nearest;s.have_prev=false;s.armed=true;
     s.last_cross=0;s.laps=0;s.last_lap=s.best_lap=0;
   }
 }
 const char *trace_track=(s.active_track>=0 && s.active_track<(int)s.tracks.size())
   ?s.tracks[s.active_track].name.c_str():"AUTO";
 goats_gps_trace::on_pvt(p,valid,s.lat,s.lon,s.speed,itow,s.num_sv,
   goats_diag::trace_hdop(),trace_track);
 if(s.active_track<0||s.active_track>=(int)s.tracks.size()){s.have_prev=false;return;}
 const Track&t=s.tracks[(size_t)s.active_track];
 if(s.have_prev){if(s.speed>=5.0f&&crosses(t,s.prev_lat,s.prev_lon,s.lat,s.lon)){
  if(s.armed&&(s.last_cross==0||itow-s.last_cross>12000)){if(s.running){uint32_t lap=itow-s.lap_start;if(lap>12000&&lap<3600000){s.last_lap=lap;if(!s.best_lap||lap<s.best_lap)s.best_lap=lap;s.laps++;}}s.lap_start=itow;s.running=true;s.last_cross=itow;s.armed=false;}
 }else{
  // Rearm once more than 25m away from the finish line midpoint.
  double ax,ay,bx,by,x,y,ref=(t.a+t.c)*.5;xy(t.a,t.b,ref,ax,ay);xy(t.c,t.d,ref,bx,by);xy(s.lat,s.lon,ref,x,y);
  if(hypot(x-(ax+bx)*.5,y-(ay+by)*.5)>std::max(25.0,(double)t.radius))s.armed=true;
 }}
 s.prev_lat=s.lat;s.prev_lon=s.lon;s.have_prev=true;
}
inline void fmt_time(char *out,size_t n,uint32_t ms){if(!ms){snprintf(out,n,"--:--.--");return;}snprintf(out,n,"%02lu:%02lu.%02lu",(unsigned long)(ms/60000),(unsigned long)(ms/1000%60),(unsigned long)((ms%1000)/10));}
} // namespace goats_b
