#pragma once
#ifdef GOATS_ARDUINO_CORE_USB_COMPAT
#include "sdkconfig.h"
// Arduino must not create a second TinyUSB stack or MSC callback owner.
#if defined(CONFIG_TINYUSB_ENABLED) && CONFIG_TINYUSB_ENABLED
#error "RC3.3 uses esp_tinyusb; Arduino TinyUSB must remain disabled"
#endif
// esp_tinyusb still sees the original enabled setting. Only Arduino core
// translation units get this forced include; no framework files are patched.
#undef CONFIG_TINYUSB_MSC_ENABLED

#endif  // GOATS_ARDUINO_CORE_USB_COMPAT
