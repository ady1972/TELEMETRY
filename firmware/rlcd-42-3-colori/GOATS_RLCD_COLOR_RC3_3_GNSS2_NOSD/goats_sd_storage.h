#pragma once
// Explicit no-SD build. No SDMMC, GPIO, filesystem or mount calls are compiled.
namespace goats_sd_storage {
inline bool ready(){return false;}
inline bool writable(){return false;}
inline bool live_open(){return false;}
inline const char *last_stage(){return "SD_DISABLED";}
inline int last_mount_error(){return 0;}
}
