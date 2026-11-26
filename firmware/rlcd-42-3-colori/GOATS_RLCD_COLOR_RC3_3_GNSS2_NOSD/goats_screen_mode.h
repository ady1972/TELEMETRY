#pragma once
#include <cstdint>
#include "nvs.h"
// Display preference only: no acquisition, session or lap-engine state.
namespace goats_screen_mode {
inline bool &delta(){static bool value=false;return value;}
inline void load(){
 delta()=false;
 nvs_handle_t handle;
 if(nvs_open("goats_display",NVS_READWRITE,&handle)!=ESP_OK)return;
 uint32_t value=0;
 if(nvs_get_u32(handle,"screen_mode",&value)==ESP_OK && value<=1)delta()=value==1;
 nvs_close(handle);
}
inline bool select(bool use_delta){
 nvs_handle_t handle;
 if(nvs_open("goats_display",NVS_READWRITE,&handle)!=ESP_OK)return false;
 const bool ok=nvs_set_u32(handle,"screen_mode",use_delta?1:0)==ESP_OK && nvs_commit(handle)==ESP_OK;
 nvs_close(handle);
 if(ok)delta()=use_delta;
 return ok;
}
}
