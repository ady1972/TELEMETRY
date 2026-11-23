#pragma once

#include "esphome.h"
#include "goats_sd_storage.h"

#include <cstdio>
#include <cstring>
#include <string>

#include "tinyusb.h"
#include "tinyusb_default_config.h"
#include "tinyusb_msc.h"
#include "esp_err.h"

// Defined in goats_usb_tracks_v1025.h
void goats_usb_suspend_for_msc();

namespace goats_usb_sd_msc {

static bool g_active = false;
static std::string g_error = "NON AVVIATA";
static tinyusb_msc_storage_handle_t g_storage = nullptr;

static inline const char *last_error() {
  return g_error.c_str();
}

static inline bool active() {
  return g_active;
}

static inline void set_err_(const char *stage, esp_err_t err) {
  char b[128];
  std::snprintf(
      b, sizeof(b), "%s: %s (0x%X)",
      stage ? stage : "USB_SD",
      esp_err_to_name(err),
      static_cast<unsigned>(err));
  g_error = b;
}

static inline bool start() {
  if (g_active) return true;

  sdmmc_card_t *card = goats_sd_storage::card_handle();
  if (card == nullptr) {
    g_error = "SD NON INIZIALIZZATA: card_handle nullo";
    return false;
  }

  // Stop the proprietary Serial/JTAG protocol before switching the shared
  // native USB connection to TinyUSB device mode.
  goats_usb_suspend_for_msc();
  delay(100);

  // Application must not access FAT while Windows owns the card.
  if (!goats_sd_storage::prepare_for_usb_msc()) {
    g_error = std::string("RILASCIO FAT FALLITO: ") +
              goats_sd_storage::last_stage();
    return false;
  }
  delay(100);

  tinyusb_config_t tusb_cfg = TINYUSB_DEFAULT_CONFIG();
  esp_err_t err = tinyusb_driver_install(&tusb_cfg);
  if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) {
    set_err_("TINYUSB", err);
    return false;
  }

  tinyusb_msc_storage_config_t storage_cfg{};
  storage_cfg.medium.card = card;
  storage_cfg.mount_point = TINYUSB_MSC_STORAGE_MOUNT_USB;
  storage_cfg.fat_fs.base_path = "/usbmsc";
  storage_cfg.fat_fs.config.max_files = 2;
  storage_cfg.fat_fs.do_not_format = true;
  storage_cfg.fat_fs.format_flags = 0;

  err = tinyusb_msc_new_storage_sdmmc(&storage_cfg, &g_storage);
  if (err != ESP_OK) {
    set_err_("MSC_SD", err);
    return false;
  }

  g_active = true;
  g_error = "OK";
  return true;
}

}  // namespace goats_usb_sd_msc
