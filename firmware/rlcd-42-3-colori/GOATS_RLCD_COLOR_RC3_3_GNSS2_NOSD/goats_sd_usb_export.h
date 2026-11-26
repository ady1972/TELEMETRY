#pragma once
#include "goats_sd_storage.h"
#include <string>
#include <cstring>
#include "driver/usb_serial_jtag.h"
namespace goats_sd_usb_export {
inline bool handle_command(const std::string &command){
  if(command.rfind("GSD",0)!=0)return false;
  const char *reply="GSD_ERR SD_DISABLED\n";
  usb_serial_jtag_write_bytes(reply,std::strlen(reply),0);
  return true;
}
inline void tick(){}
}
