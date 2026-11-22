#pragma once
// Fixed 80-lap NVS cache, serviced outside the GNSS consumer.
#include "goats_port_types.h"
#include "nvs.h"
#include <algorithm>
#include <cstdio>
#include <cstddef>
namespace goats_lap_journal {
struct Record {
  uint32_t magic{0x324A5247},sequence{0},session{0},duration{0};
  uint16_t number{0};uint8_t sector_count{0},reserved{0};
  uint32_t lap_ms{0},best_ms{0},sectors[13]{};
  float max_speed{0},average_speed{0};
  char date[16]{},time[12]{},track[64]{};
  uint32_t checksum{0};
};
static std::array<Record,80> cache{};
static uint32_t sequence=0,max_session=0;
static bool ready=false;
inline bool valid(const Record&r){
  return r.magic==0x324A5247&&r.session&&r.number&&r.lap_ms&&r.sector_count<=13&&
    r.date[15]==0&&r.time[11]==0&&r.track[63]==0&&r.checksum==
    goats_port::crc32(reinterpret_cast<const uint8_t*>(&r),offsetof(Record,checksum));
}
inline void setup(){
  nvs_handle_t h;if(nvs_open("goats_j22",NVS_READWRITE,&h)!=ESP_OK)return;
  (void)nvs_get_u32(h,"max_sid",&max_session);
  for(unsigned i=0;i<80;++i){
    char key[12];std::snprintf(key,sizeof(key),"lap%02u",i);Record r{};size_t n=sizeof(r);
    if(nvs_get_blob(h,key,&r,&n)==ESP_OK&&n==sizeof(r)&&valid(r)){
      std::memcpy(&cache[i],&r,sizeof(r));sequence=std::max(sequence,r.sequence);max_session=std::max(max_session,r.session);
    }
  }
  nvs_close(h);ready=true;
}
inline bool save(Record r){
  if(!ready)return false;r.sequence=sequence+1;
  r.checksum=goats_port::crc32(reinterpret_cast<const uint8_t*>(&r),offsetof(Record,checksum));
  const unsigned slot=sequence%80;char key[12];std::snprintf(key,sizeof(key),"lap%02u",slot);
  nvs_handle_t h;if(nvs_open("goats_j22",NVS_READWRITE,&h)!=ESP_OK)return false;
  auto e=nvs_set_blob(h,key,&r,sizeof(r));
  if(e==ESP_OK)e=nvs_set_u32(h,"max_sid",std::max(max_session,r.session));
  if(e==ESP_OK)e=nvs_commit(h);nvs_close(h);
  if(e!=ESP_OK)return false;std::memcpy(&cache[slot],&r,sizeof(r));sequence=r.sequence;max_session=std::max(max_session,r.session);return true;
}
inline bool erase_session(uint32_t sid){
  if(!ready)return false;nvs_handle_t h;if(nvs_open("goats_j22",NVS_READWRITE,&h)!=ESP_OK)return false;
  bool ok=true;
  for(unsigned i=0;i<80;++i)if(cache[i].session==sid||sid==0){
    char key[12];std::snprintf(key,sizeof(key),"lap%02u",i);auto e=nvs_erase_key(h,key);
    if(e!=ESP_OK&&e!=ESP_ERR_NVS_NOT_FOUND)ok=false;
  }
  if(nvs_commit(h)!=ESP_OK)ok=false;nvs_close(h);
  if(ok)for(auto&r:cache)if(r.session==sid||sid==0)r={};return ok;
}
}
