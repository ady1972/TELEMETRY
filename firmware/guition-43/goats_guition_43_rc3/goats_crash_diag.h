#pragma once

#include <cstdint>
#include "esp_attr.h"
#include "esp_system.h"

namespace goats_crash_diag {

static constexpr uint32_t MAGIC = 0x47525425UL;  // "GRT%"

enum Breadcrumb : uint32_t {
  BC_NONE = 0,
  BC_BOOT = 1,
  BC_START_CLICK = 10,
  BC_SESSION_RAM_OK = 20,
  BC_SD_DEFER_BEGIN = 30,
  BC_SD_OPEN_BEGIN = 40,
  BC_SD_OPEN_OK = 50,
  BC_SD_OPEN_FAIL = 60,
  BC_RECORDING = 70,
  BC_STOP_CLICK = 80
};

RTC_NOINIT_ATTR static uint32_t rtc_magic;
RTC_NOINIT_ATTR static uint32_t rtc_breadcrumb;
RTC_NOINIT_ATTR static uint32_t rtc_counter;

static uint32_t previous_breadcrumb = BC_NONE;
static uint32_t previous_counter = 0;
static esp_reset_reason_t boot_reset_reason = ESP_RST_UNKNOWN;

static inline const char *breadcrumb_name(uint32_t bc) {
  switch (bc) {
    case BC_BOOT: return "BOOT";
    case BC_START_CLICK: return "START_CLICK";
    case BC_SESSION_RAM_OK: return "SESSION_RAM_OK";
    case BC_SD_DEFER_BEGIN: return "SD_DEFER_BEGIN";
    case BC_SD_OPEN_BEGIN: return "SD_OPEN_BEGIN";
    case BC_SD_OPEN_OK: return "SD_OPEN_OK";
    case BC_SD_OPEN_FAIL: return "SD_OPEN_FAIL";
    case BC_RECORDING: return "RECORDING";
    case BC_STOP_CLICK: return "STOP_CLICK";
    default: return "NONE";
  }
}

static inline const char *reset_name(esp_reset_reason_t r) {
  switch (r) {
    case ESP_RST_POWERON: return "POWERON";
    case ESP_RST_EXT: return "EXT";
    case ESP_RST_SW: return "SW";
    case ESP_RST_PANIC: return "PANIC";
    case ESP_RST_INT_WDT: return "INT_WDT";
    case ESP_RST_TASK_WDT: return "TASK_WDT";
    case ESP_RST_WDT: return "WDT";
    case ESP_RST_DEEPSLEEP: return "DEEPSLEEP";
    case ESP_RST_BROWNOUT: return "BROWNOUT";
    case ESP_RST_SDIO: return "SDIO";
    case ESP_RST_USB: return "USB";
    case ESP_RST_JTAG: return "JTAG";
    case ESP_RST_EFUSE: return "EFUSE";
    case ESP_RST_PWR_GLITCH: return "PWR_GLITCH";
    case ESP_RST_CPU_LOCKUP: return "CPU_LOCKUP";
    default: return "UNKNOWN";
  }
}

static inline void boot_capture() {
  boot_reset_reason = esp_reset_reason();
  if (rtc_magic == MAGIC) {
    previous_breadcrumb = rtc_breadcrumb;
    previous_counter = rtc_counter;
  } else {
    previous_breadcrumb = BC_NONE;
    previous_counter = 0;
    rtc_magic = MAGIC;
    rtc_counter = 0;
  }
  rtc_breadcrumb = BC_BOOT;
}

static inline void mark(Breadcrumb bc) {
  rtc_magic = MAGIC;
  rtc_breadcrumb = static_cast<uint32_t>(bc);
  ++rtc_counter;
}

static inline const char *previous_breadcrumb_name() {
  return breadcrumb_name(previous_breadcrumb);
}

static inline const char *boot_reset_name() {
  return reset_name(boot_reset_reason);
}

}  // namespace goats_crash_diag
