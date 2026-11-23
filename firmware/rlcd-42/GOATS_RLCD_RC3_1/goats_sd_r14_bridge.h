#pragma once
#include "goats_sd_storage.h"
#include "ff.h"
#include <cstdio>
namespace goats_sd_r14_bridge {
static bool initialized=false;
static bool last_write_ok=false;
static uint32_t writes=0;
static uint32_t errors=0;
static uint32_t last_ms=0;
inline void begin(){
  if(initialized && goats_sd_storage::ready()) return;
  bool ok=goats_sd_storage::setup();
  initialized=ok && goats_sd_storage::ready();
  ESP_LOGI("SD_R14","SD init=%d ready=%d writable=%d stage=%s err=%d",ok,goats_sd_storage::ready(),goats_sd_storage::writable(),goats_sd_storage::last_stage(),goats_sd_storage::last_mount_error());
}
inline void save_lap(uint32_t session,uint32_t lap,uint32_t lap_ms,uint32_t best_ms,float avg,const char*track){
  if(!initialized || !goats_sd_storage::ready() || !goats_sd_storage::writable()){
    ++errors; last_write_ok=false;
    ESP_LOGW("SD_R14","lap=%lu skipped: initialized=%d ready=%d writable=%d stage=%s",
      (unsigned long)lap, initialized, goats_sd_storage::ready(), goats_sd_storage::writable(), goats_sd_storage::last_stage());
    return;
  }
  const uint32_t start=millis();
  // 8.3 filename for maximum FAT compatibility, one file per boot session.
  char filename[32]; snprintf(filename,sizeof(filename),"0:/G%06lu.CSV",(unsigned long)(session%1000000UL));
  FIL file{}; FRESULT fr=f_open(&file,filename,FA_OPEN_ALWAYS|FA_WRITE);
  if(fr!=FR_OK){++errors;ESP_LOGW("SD_R14","open failed FR=%d",(int)fr);return;}
  fr=f_lseek(&file,f_size(&file));
  if(fr==FR_OK){
    char line[160];int n=snprintf(line,sizeof(line),"%lu,%lu,%lu,%lu,%.2f,%s\n",(unsigned long)session,(unsigned long)lap,(unsigned long)lap_ms,(unsigned long)best_ms,(double)avg,track?track:"AUTO");
    if(n<0 || n>=(int)sizeof(line)){fr=FR_INVALID_PARAMETER;}
    UINT written=0;if(fr==FR_OK)fr=f_write(&file,line,(UINT)n,&written);
    if(fr==FR_OK && written!=(UINT)n)fr=FR_DISK_ERR;
  }
  if(fr==FR_OK)fr=f_sync(&file);
  FRESULT close_result=f_close(&file);
  if(fr==FR_OK)fr=close_result;
  last_ms=millis()-start;
  last_write_ok=fr==FR_OK;
  if(last_write_ok)++writes;else {++errors;ESP_LOGW("SD_R14","write failed FR=%d",(int)fr);}
  ESP_LOGI("SD_R14","lap=%lu write=%d duration=%lums",(unsigned long)lap,last_write_ok,(unsigned long)last_ms);
}
}
