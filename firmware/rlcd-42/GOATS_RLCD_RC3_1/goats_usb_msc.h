#pragma once
// GOATS MG902 TEST25 -- USB Mass Storage with deliberate double confirmation.
// The mode transition uses a reboot so native USB Serial/JTAG is never
// initialized concurrently with the ESP32-S3 USB-OTG/TinyUSB controller.
#include "nvs.h"
#include "esp_system.h"
#include "esp_err.h"
#include "driver/gpio.h"
#include "driver/sdmmc_host.h"
#include "sdmmc_cmd.h"
#include "tinyusb.h"
#include "tinyusb_default_config.h"
#include "tinyusb_msc.h"
#include <cstdlib>

namespace goats_usb_msc {
inline bool &active(){static bool a=false;return a;}
inline bool &failed(){static bool a=false;return a;}
inline const char *key_space(){return "goats_usb";}
inline bool take_boot_request(){
  nvs_handle_t h;
  if(nvs_open(key_space(),NVS_READWRITE,&h)!=ESP_OK)return false;
  uint8_t flag=0;
  (void)nvs_get_u8(h,"msc_next",&flag);
  // Clear the flag before attempting MSC: a restart always recovers normal mode.
  (void)nvs_erase_key(h,"msc_next");
  (void)nvs_commit(h);
  nvs_close(h);
  return flag==1;
}
inline bool request_reboot(){
  // Caller checks that no kart session is active; do not touch live files.
  nvs_handle_t h;
  if(nvs_open(key_space(),NVS_READWRITE,&h)!=ESP_OK)return false;
  esp_err_t e=nvs_set_u8(h,"msc_next",1);
  if(e==ESP_OK)e=nvs_commit(h);
  nvs_close(h);
  if(e!=ESP_OK)return false;
  esp_restart();
  return true;
}
inline bool start_sdmmc(){
  // Native 1-bit SDMMC, exactly matching the working TEST24 pins.
  gpio_pullup_en(GPIO_NUM_21);
  gpio_pullup_en(GPIO_NUM_39);
  sdmmc_host_t host=SDMMC_HOST_DEFAULT();
  host.max_freq_khz=SDMMC_FREQ_DEFAULT;
  sdmmc_slot_config_t slot=SDMMC_SLOT_CONFIG_DEFAULT();
  slot.width=1;
  slot.clk=GPIO_NUM_38; slot.cmd=GPIO_NUM_21; slot.d0=GPIO_NUM_39;
  slot.d1=GPIO_NUM_NC; slot.d2=GPIO_NUM_NC; slot.d3=GPIO_NUM_NC;
  esp_err_t e=sdmmc_host_init();
  if(e!=ESP_OK){ESP_LOGE("GOATS_MSC","SDMMC host %s",esp_err_to_name(e));return false;}
  e=sdmmc_host_init_slot(host.slot,&slot);
  if(e!=ESP_OK){ESP_LOGE("GOATS_MSC","SDMMC slot %s",esp_err_to_name(e));return false;}
  static sdmmc_card_t *card=(sdmmc_card_t*)calloc(1,sizeof(sdmmc_card_t));
  if(!card)return false;
  e=sdmmc_card_init(&host,card);
  if(e!=ESP_OK){ESP_LOGE("GOATS_MSC","Card init %s",esp_err_to_name(e));return false;}
  tinyusb_msc_storage_handle_t storage{};
  tinyusb_msc_storage_config_t cfg{};
  cfg.medium.card=card;
  e=tinyusb_msc_new_storage_sdmmc(&cfg,&storage);
  if(e!=ESP_OK){ESP_LOGE("GOATS_MSC","MSC storage %s",esp_err_to_name(e));return false;}
  const tinyusb_config_t tusb_cfg=TINYUSB_DEFAULT_CONFIG();
  e=tinyusb_driver_install(&tusb_cfg);
  if(e!=ESP_OK){ESP_LOGE("GOATS_MSC","TinyUSB %s",esp_err_to_name(e));return false;}
  ESP_LOGI("GOATS_MSC","USB Mass Storage started. Eject in Windows then restart laptimer.");
  return true;
}
inline bool boot_if_requested(){
  if(!take_boot_request())return false;
  active()=true;
  failed()=!start_sdmmc();
  return true;
}
}
