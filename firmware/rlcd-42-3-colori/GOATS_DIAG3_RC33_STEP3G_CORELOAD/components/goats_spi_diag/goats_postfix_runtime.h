#pragma once
#ifdef GOATS_RC33_STEP1_IMPL
#include <cstdint>
// Startup-only isolation. Never switches receivers or changes GNSS parameters.
namespace goats_postfix {
enum Mode : uint8_t { GPS_ONLY=0, CORE_ONLY=1, FULL=2, STORE_ONLY=3, USB_ONLY=4 };
inline Mode mode=FULL;
inline void set(uint8_t value){mode=static_cast<Mode>(value);}
inline const char* name(){return mode==GPS_ONLY?"GPS ONLY":mode==CORE_ONLY?"CORE ONLY":mode==STORE_ONLY?"CORE+FLASH":mode==USB_ONLY?"CORE+USB":"FULL";}
inline const char* title(){return mode==GPS_ONLY?"STEP3G - GPS ONLY":mode==CORE_ONLY?"STEP3G - CORE ONLY":mode==STORE_ONLY?"STEP3G - CORE+FLASH":mode==USB_ONLY?"STEP3G - CORE+USB":(goats_core_cache::enabled?"STEP3G - FULL CACHE":"STEP3G - FULL REF");}
inline const char* detail(){return mode==GPS_ONLY?"CORE / FLASH / USB MANAGER ESCLUSI":mode==CORE_ONLY?"CORE ATTIVO - FLASH / USB ESCLUSI":mode==STORE_ONLY?"CORE E FLASH ON - USB MANAGER OFF":mode==USB_ONLY?"CORE E USB ON - TELEMETRIA FLASH OFF":"CORE / FLASH / USB MANAGER ATTIVI";}
inline bool storage(){return mode==FULL||mode==STORE_ONLY;}
inline bool usb(){return mode==FULL||mode==USB_ONLY;}
inline bool backend(){return storage()||usb();}
inline bool full(){return mode==FULL;}
inline void prepare(){if(storage())goats_lap_storage::begin();}
inline void start(){
 if(mode==GPS_ONLY){goats_gps_diag::frame_observer=nullptr;return;}
 goats_rc33_step1::attach();
 if(backend())goats_step3::start(storage(),usb());
}
inline void tick(){
 if(backend())goats_step3::tick();
 if(mode!=GPS_ONLY)goats_ui::capture(::millis());
}
inline void record_toggle(){
 if(!storage())return;
 if(goats_step3_store::state().active)goats_step3::stop();else goats_step3::free_start();
}
}
#endif
