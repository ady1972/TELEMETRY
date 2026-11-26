#pragma once
// SD and Mass Storage deliberately unavailable. No NVS reboot request, TinyUSB,
// SDMMC or pin initialization, regardless of flags left by older firmware.
namespace goats_usb_msc {
inline bool active(){return false;}
inline bool failed(){return false;}
inline bool boot_if_requested(){return false;}
inline bool request_reboot(){return false;}
}
