#pragma once
#include <cstdint>
#include <string>
#include <cassert>
using nvs_handle_t=int;
constexpr int ESP_OK=0, NVS_READWRITE=0;
inline bool fail_open=false,fail_set=false,fail_commit=false,exists=false;
inline uint32_t durable=0,pending=0;
inline int commits=0;
inline int nvs_open(const char* name,int,nvs_handle_t* h){assert(std::string(name)=="goats_display");*h=1;pending=durable;return fail_open?1:0;}
inline int nvs_get_u32(nvs_handle_t,const char* key,uint32_t* value){assert(std::string(key)=="screen_mode");if(!exists)return 1;*value=durable;return 0;}
inline int nvs_set_u32(nvs_handle_t,const char*,uint32_t value){pending=value;return fail_set?1:0;}
inline int nvs_commit(nvs_handle_t){if(fail_commit)return 1;durable=pending;exists=true;++commits;return 0;}
inline void nvs_close(nvs_handle_t){}
