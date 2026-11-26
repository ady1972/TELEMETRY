#pragma once
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <algorithm>
#include "nvs.h"
#include "nvs_flash.h"
// FASE2 A: NVS flash journal, writes ONLY on completed laps, not at 25Hz.
// Up to 80 laps retained. Session identifier increments at each boot.
namespace goats_archive {
struct Record { uint32_t session, lap, lap_ms, best_ms; float avg_kmh; uint32_t sector_ms[3]; char track[40]; };
inline uint32_t &session(){static uint32_t n=0;return n;}
inline uint32_t &count(){static uint32_t n=0;return n;}
inline uint32_t &head(){static uint32_t n=0;return n;}
inline bool &ready(){static bool b=false;return b;}
// TEST26: snapshot NVS in RAM: drawing/navigation never reopens NVS.
inline bool &cache_valid(){static bool b=false;return b;}
inline Record *cache_records(){static Record items[80]{};return items;}
inline bool *cache_present(){static bool present[80]{};return present;}
inline void invalidate_cache(){cache_valid()=false;}
inline void setup(){
 invalidate_cache();
 nvs_handle_t h;
 if(nvs_open("goats_sess",NVS_READWRITE,&h)!=ESP_OK)return;
 uint32_t n=0; nvs_get_u32(h,"session",&n);session()=n+1;
 nvs_get_u32(h,"count",&count());count()=std::min<uint32_t>(count(),80);
 nvs_get_u32(h,"head",&head());head()%=80;
 if(nvs_set_u32(h,"session",session())==ESP_OK && nvs_commit(h)==ESP_OK)ready()=true;
 nvs_close(h);
}
inline bool save(uint32_t lap,uint32_t lap_ms,uint32_t best_ms,float avg,const char*track){
 if(!ready()||!lap_ms)return false;
 Record r{};r.session=session();r.lap=lap;r.lap_ms=lap_ms;r.best_ms=best_ms;r.avg_kmh=avg;
 std::snprintf(r.track,sizeof(r.track),"%s",track?track:"AUTO");
 for(size_t i=0;i<3;++i)r.sector_ms[i]=GOATS_LAPTIMER.last_timing_sector_ms(i);
 nvs_handle_t h;if(nvs_open("goats_sess",NVS_READWRITE,&h)!=ESP_OK)return false;
 char key[12];std::snprintf(key,sizeof(key),"lap%02lu",(unsigned long)head());
 esp_err_t e=nvs_set_blob(h,key,&r,sizeof(r));
 uint32_t next=(head()+1)%80, n=std::min<uint32_t>(80,count()+1);
 if(e==ESP_OK)e=nvs_set_u32(h,"head",next);
 if(e==ESP_OK)e=nvs_set_u32(h,"count",n);
 if(e==ESP_OK)e=nvs_commit(h);
 nvs_close(h);
 if(e==ESP_OK){head()=next;count()=n;invalidate_cache();return true;}return false;
}
// Discard only records belonging to the active session; preserve previous sessions.
inline bool discard_current(){
 if(!ready())return false;
 Record keep[80];uint32_t kept=0;
 for(uint32_t i=0;i<count();++i){
   uint32_t slot=(head()+80-count()+i)%80;
   char key[12];std::snprintf(key,sizeof(key),"lap%02lu",(unsigned long)slot);
   nvs_handle_t h;if(nvs_open("goats_sess",NVS_READONLY,&h)!=ESP_OK)return false;
   Record r{};size_t size=sizeof(r);esp_err_t e=nvs_get_blob(h,key,&r,&size);nvs_close(h);
   if(e==ESP_OK && size==sizeof(r) && r.session!=session())keep[kept++]=r;
 }
 nvs_handle_t h;if(nvs_open("goats_sess",NVS_READWRITE,&h)!=ESP_OK)return false;
 esp_err_t e=ESP_OK;
 for(uint32_t i=0;i<80 && e==ESP_OK;++i){char key[12];std::snprintf(key,sizeof(key),"lap%02lu",(unsigned long)i);
   if(i<kept)e=nvs_set_blob(h,key,&keep[i],sizeof(Record));
   else {esp_err_t del=nvs_erase_key(h,key);if(del!=ESP_OK && del!=ESP_ERR_NVS_NOT_FOUND)e=del;}
 }
 if(e==ESP_OK)e=nvs_set_u32(h,"count",kept);
 if(e==ESP_OK)e=nvs_set_u32(h,"head",kept%80);
 if(e==ESP_OK)e=nvs_commit(h);
 nvs_close(h);if(e!=ESP_OK)return false;
 count()=kept;head()=kept%80;invalidate_cache();return true;
}
inline bool next_session(){
 nvs_handle_t h;if(nvs_open("goats_sess",NVS_READWRITE,&h)!=ESP_OK)return false;
 uint32_t next=session()+1;
 esp_err_t e=nvs_set_u32(h,"session",next);
 if(e==ESP_OK)e=nvs_commit(h);nvs_close(h);
 if(e==ESP_OK){session()=next;return true;}return false;
}
inline bool read_from_nvs(uint32_t index,Record &r){
 if(!ready()||index>=count())return false;
 uint32_t slot=(head()+80-count()+index)%80;
 char key[12];std::snprintf(key,sizeof(key),"lap%02lu",(unsigned long)slot);
 nvs_handle_t h;if(nvs_open("goats_sess",NVS_READONLY,&h)!=ESP_OK)return false;
 size_t size=sizeof(r);esp_err_t e=nvs_get_blob(h,key,&r,&size);nvs_close(h);
 return e==ESP_OK && size==sizeof(r);
}
inline void build_cache(){
 if(cache_valid())return;
 for(uint32_t i=0;i<80;++i)cache_present()[i]=false;
 for(uint32_t i=0;i<count();++i)
   cache_present()[i]=read_from_nvs(i,cache_records()[i]);
 cache_valid()=true;
}
inline bool read(uint32_t index,Record &r){
 if(!ready() || index>=count() || index>=80)return false;
 build_cache();
 if(!cache_present()[index])return false;
 r=cache_records()[index];return true;
}
// Read-only on-device archive browser. Index 0 is the most recent session.
inline int session_count(){
 uint32_t prev=0;int total=0;
 for(int i=(int)count()-1;i>=0;--i){Record r{};if(!read((uint32_t)i,r))continue;
  if(!total||r.session!=prev){++total;prev=r.session;}}
 return total;
}
inline bool session_at(int index,uint32_t &sid,Record &last){
 if(index<0)return false;uint32_t prev=0;int n=-1;
 for(int i=(int)count()-1;i>=0;--i){Record r{};if(!read((uint32_t)i,r))continue;
  if(n<0||r.session!=prev){++n;prev=r.session;}
  if(n==index){sid=r.session;last=r;return true;}}
 return false;
}
inline int laps_in_session(int index){
 uint32_t sid;Record last{};if(!session_at(index,sid,last))return 0;
 int n=0;for(uint32_t i=0;i<count();++i){Record r{};if(read(i,r)&&r.session==sid)++n;}return n;
}
inline bool lap_in_session(int index,int lap_index,Record &out){
 uint32_t sid;Record last{};if(!session_at(index,sid,last)||lap_index<0)return false;
 int n=0;for(uint32_t i=0;i<count();++i){Record r{};if(read(i,r)&&r.session==sid){if(n++==lap_index){out=r;return true;}}}return false;
}
inline void export_csv(){
 goats_b::reply("GSES_CSV_BEGIN session,lap,lap_ms,best_ms,avg_kmh,s1_ms,s2_ms,s3_ms,track");
 for(uint32_t i=0;i<count();++i){Record r{};if(!read(i,r))continue;
 char line[180];std::snprintf(line,sizeof(line),"%lu,%lu,%lu,%lu,%.2f,%lu,%lu,%lu,%s",
 (unsigned long)r.session,(unsigned long)r.lap,(unsigned long)r.lap_ms,
 (unsigned long)r.best_ms,(double)r.avg_kmh,
 (unsigned long)r.sector_ms[0],(unsigned long)r.sector_ms[1],(unsigned long)r.sector_ms[2],r.track);
 goats_b::reply(line);
 }
 goats_b::reply("GSES_CSV_END");
}
} // namespace goats_archive
