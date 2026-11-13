#pragma once
#include "goats_recording_clock.h"
#include "nvs.h"
#include "esphome/core/hal.h"
#include <string>
namespace goats_dates {
struct Entry {uint32_t id{};goats_clock::DateTime date{};};
inline Entry entries[80]{};
inline bool pending=false;
inline bool dirty[80]{};
inline int find(uint32_t id){for(int i=0;i<80;i++)if(entries[i].id==id)return i;return -1;}
inline goats_clock::DateTime date(uint32_t id){const int slot=find(id);return slot>=0?entries[slot].date:goats_clock::DateTime{};}
inline uint32_t active=0,retry_at=0;
inline void key(unsigned index,char *out){std::snprintf(out,12,"S%02u",index);}
inline void setup(){
 nvs_handle_t h;if(nvs_open("goats_dates2",NVS_READONLY,&h)!=ESP_OK)return;
 for(unsigned i=0;i<80;++i){char k[12];key(i,k);size_t n=sizeof(Entry);Entry e{};
  if(nvs_get_blob(h,k,&e,&n)==ESP_OK&&n==sizeof(e)&&e.id!=0)entries[i]=e;
 }nvs_close(h);
}
// First sample of a session only. No filesystem/NVS in the NAV consumer.
inline void capture(uint32_t id,const goats_clock::DateTime &date){
 if(!id||id==active)return;active=id;
 if(find(id)>=0)return; // A recorded start timestamp is immutable.
 int slot=0;for(int i=0;i<80;i++)if(entries[i].id<entries[slot].id)slot=i;
 entries[slot]={id,date};dirty[slot]=true;pending=true;retry_at=0;
}
inline void tick(){
 if(!pending||(retry_at!=0&&int32_t(esphome::millis()-retry_at)<0))return;
 retry_at=esphome::millis()+1000;
 nvs_handle_t h;if(nvs_open("goats_dates2",NVS_READWRITE,&h)!=ESP_OK)return;
 int slot=0;while(slot<80&&!dirty[slot])++slot;
 if(slot==80){nvs_close(h);pending=false;return;}
 char k[12];key(slot,k);const auto&e=entries[slot];
 esp_err_t err=nvs_set_blob(h,k,&e,sizeof(e));if(err==ESP_OK)err=nvs_commit(h);
 nvs_close(h);if(err==ESP_OK){dirty[slot]=false;retry_at=0;pending=false;
  for(bool d:dirty)pending=pending||d;
 }
}
inline std::string text(uint32_t id){
 const int slot=find(id);if(slot<0||!goats_clock::valid(entries[slot].date))return "DATA NON DISPONIBILE";
 const auto&e=entries[slot];
 char d[16],t[16];goats_clock::format(e.date,d,sizeof(d),t,sizeof(t));return std::string(d)+" "+t+" IT";
}
}
