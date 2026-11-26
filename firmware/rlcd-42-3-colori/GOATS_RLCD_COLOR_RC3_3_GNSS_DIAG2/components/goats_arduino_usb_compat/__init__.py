"""Keep RC3.3's esp_tinyusb MSC implementation when using the Arduino core."""
from pathlib import Path
import esphome.config_validation as cv
from esphome.components import esp32

CONFIG_SCHEMA = cv.All(cv.Schema({}), cv.only_with_arduino)

async def to_code(config):
    esp32.add_idf_component(
        name="goats_arduino_usb_compat",
        path=str(Path(__file__).resolve().parent),
    )
