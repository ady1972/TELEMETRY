#pragma once
// TEST27 - second core exclusively for completed-lap CSV writes.
// No GNSS parser, UART, lap detector or display changes.
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <atomic>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/queue.h"
#include "freertos/semphr.h"
#include "goats_sd_r14_bridge.h"
namespace goats_dual_core {
struct LapJob {uint32_t session,lap,lap_ms,best_ms;float avg;char track[40];};
inline QueueHandle_t &jobs(){static QueueHandle_t q=nullptr;return q;}
inline SemaphoreHandle_t &sd_mutex(){static SemaphoreHandle_t m=nullptr;return m;}
inline TaskHandle_t &worker_handle(){static TaskHandle_t t=nullptr;return t;}
inline std::atomic<uint32_t> &inflight(){static std::atomic<uint32_t> v{0};return v;}
inline uint32_t &enqueued(){static uint32_t v=0;return v;}
inline uint32_t &fallbacks(){static uint32_t v=0;return v;}
inline bool lock(TickType_t ticks){return !sd_mutex() || xSemaphoreTake(sd_mutex(),ticks)==pdTRUE;}
inline void unlock(){if(sd_mutex())xSemaphoreGive(sd_mutex());}
inline void worker(void *){
 LapJob job{};
 for(;;){
  if(xQueueReceive(jobs(),&job,portMAX_DELAY)==pdTRUE){

   if(lock(portMAX_DELAY)){
    goats_sd_r14_bridge::save_lap(job.session,job.lap,job.lap_ms,job.best_ms,job.avg,job.track);
    unlock();
   }
   inflight().fetch_sub(1,std::memory_order_release);
  }
 }
}
inline void start(){
 if(worker_handle())return;
 if(!sd_mutex())sd_mutex()=xSemaphoreCreateMutex();
 if(!jobs())jobs()=xQueueCreate(16,sizeof(LapJob));
 if(!sd_mutex() || !jobs()){ESP_LOGE("DUAL_CORE","Creation of SD sync objects failed");return;}
 BaseType_t ok=xTaskCreatePinnedToCore(worker,"goats_sd_writer",6144,nullptr,1,&worker_handle(),0);
 if(ok!=pdPASS){worker_handle()=nullptr;ESP_LOGE("DUAL_CORE","Core 0 task creation failed");}
 else ESP_LOGI("DUAL_CORE","Lap SD worker started on Core 0; app on Core %d",xPortGetCoreID());
}
inline void enqueue_lap(uint32_t session,uint32_t lap,uint32_t lap_ms,uint32_t best_ms,float avg,const char*track){
 LapJob job{session,lap,lap_ms,best_ms,avg,{}};
 std::snprintf(job.track,sizeof(job.track),"%s",track?track:"AUTO");
 if(worker_handle()){
  inflight().fetch_add(1,std::memory_order_release);
  if(xQueueSend(jobs(),&job,0)==pdTRUE){++enqueued();return;}
  inflight().fetch_sub(1,std::memory_order_release);
 }
 // Never silently lose a lap if a queue is full or the worker failed to start.
 ++fallbacks();
 if(lock(portMAX_DELAY)){
  goats_sd_r14_bridge::save_lap(job.session,job.lap,job.lap_ms,job.best_ms,job.avg,job.track);
  unlock();
 }
}
inline bool wait_idle(uint32_t timeout_ms=3000){
 if(!worker_handle())return true;
 const TickType_t started=xTaskGetTickCount();
 do {
  if(inflight().load(std::memory_order_acquire)==0)return true;
  vTaskDelay(pdMS_TO_TICKS(5));
 }while((xTaskGetTickCount()-started)<pdMS_TO_TICKS(timeout_ms));
 ESP_LOGE("DUAL_CORE","SD writes still pending; refusing session closure");
 return false;
}
} // namespace goats_dual_core
