#pragma once
#include "goats_recording_clock.h"
#include "esphome/core/hal.h"
#include <sys/time.h>
#include <ctime>
#include <cstdlib>
namespace goats_clock_runtime {
inline void tick(){
 static bool initialized=false;static uint32_t last=0;
 const uint32_t now=esphome::millis(),age=now-goats_clock::observed_ms;
 if(!goats_clock::valid(goats_clock::utc_latest)||age>3000||(initialized&&now-last<60000))return;
 // POSIX TZ uses reversed signs. FAT creation timestamps use localtime_r().
 if(!initialized){setenv("TZ","CET-1CEST,M3.5.0/2,M10.5.0/3",1);tzset();}
 timeval tv{};tv.tv_sec=goats_clock::epoch(goats_clock::utc_latest)+age/1000;
 tv.tv_usec=(age%1000)*1000;
 if(settimeofday(&tv,nullptr)==0){initialized=true;last=now;}
}
}
