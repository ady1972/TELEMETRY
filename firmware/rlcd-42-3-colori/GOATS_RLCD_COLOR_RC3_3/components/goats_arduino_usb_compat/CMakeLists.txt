# The application uses esp_tinyusb, not Arduino's USBMSC wrapper. Both wrappers
# share CONFIG_TINYUSB_MSC_ENABLED, so scope the compatibility override strictly
# to the Arduino library. Never change sdkconfig or the application target.
idf_component_register(REQUIRES espressif__arduino-esp32)
idf_component_get_property(arduino_lib espressif__arduino-esp32 COMPONENT_LIB)
target_compile_definitions(${arduino_lib} PRIVATE GOATS_ARDUINO_CORE_USB_COMPAT=1)
target_compile_options(${arduino_lib} PRIVATE
    "-include${CMAKE_CURRENT_LIST_DIR}/arduino_usb_owner.h")
