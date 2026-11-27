#pragma once
// GOATS V0.40.2: storage di collaudo basato su NVS IDF.
// Non richiede LittleFS.h, che non e' visibile nel build ESPHome 2026.9.1.
// Un record per giro; NON e' un file CSV e NON offre ancora l'export.
#include <Arduino.h>
#include <nvs.h>
#include <nvs_flash.h>
#include <esp_system.h>
#include <stdio.h>
namespace goats_lap_storage {
inline bool ready=false;
inline String current_file;
inline uint32_t session_id=0;
inline bool begin(){
  nvs_handle_t h{};
  const esp_err_t err=nvs_open("goats_laps",NVS_READWRITE,&h);
  if(err!=ESP_OK){ready=false;return false;}
  nvs_close(h);ready=true;return true;
}
inline void new_session(const char* name,const char* date,const char* time){
  current_file="";
  if(!ready)return;
  nvs_handle_t h{};
  if(nvs_open("goats_laps",NVS_READWRITE,&h)!=ESP_OK)return;
  session_id=esp_random();
  char key[16],val[110];
  snprintf(key,sizeof(key),"S%08lX",(unsigned long)session_id);
  snprintf(val,sizeof(val),"%s|%s|%s",name?name:"?",date?date:"?",time?time:"?");
  const esp_err_t a=nvs_set_str(h,key,val);
  const esp_err_t b=(a==ESP_OK)?nvs_commit(h):a;
  nvs_close(h);
  if(b==ESP_OK){char id[16];snprintf(id,sizeof(id),"%08lX",(unsigned long)session_id);current_file=id;}
}
struct LapRecord {uint32_t lap;uint32_t lap_ms;uint32_t best_ms;float speed_kmh;};
inline void lap(unsigned n,unsigned ms,unsigned best,float speed){
  if(!ready||current_file.isEmpty())return;
  nvs_handle_t h{};
  if(nvs_open("goats_laps",NVS_READWRITE,&h)!=ESP_OK)return;
  char key[16];snprintf(key,sizeof(key),"L%08lX%02X",(unsigned long)session_id,unsigned(n)&0xffu);
  const LapRecord rec{n,ms,best,speed};
  const esp_err_t e=nvs_set_blob(h,key,&rec,sizeof(rec));
  if(e==ESP_OK)nvs_commit(h);
  nvs_close(h);
}
inline void end(){current_file="";}
}
