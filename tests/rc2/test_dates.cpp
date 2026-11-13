#include <cassert>
#define NVS_READONLY 1
using esp_err_t=int;
#include "goats_recording_dates.h"
int main(){
 using namespace goats_dates;
 capture(12,{2026,11,6,13,5,6});assert(fake_nvs.empty());
 capture(12,{2026,11,7,1,1,1});assert(date(12).day==6);
 tick();assert(!pending && !fake_nvs.empty());
 for(auto &e:entries)e={};active=0;setup();
 assert(text(12)=="2026-11-06 13:05:06 IT");assert(text(11)=="DATA NON DISPONIBILE");
 capture(13,{});tick();assert(text(13)=="DATA NON DISPONIBILE");
 capture(92,{2026,11,8,12,0,0});tick(); // sparse IDs must not evict session 12.
 assert(text(12)=="2026-11-06 13:05:06 IT");
 fake_millis=0x80000001U;capture(93,{2026,11,9,12,0,0});tick();assert(!pending);
 fake_nvs_fail=true;capture(14,{2026,11,7,14,0,0});tick();assert(pending);
 fake_nvs_fail=false;fake_millis+=1000;tick();assert(!pending);
}
