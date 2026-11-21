import esphome.codegen as cg
import esphome.config_validation as cv
from esphome import pins
from esphome.components import spi
from esphome.const import CONF_ID, CONF_DC_PIN, CONF_RESET_PIN

DEPENDENCIES = ["esp32", "spi"]
ns = cg.esphome_ns.namespace("goats_power_test")
GoatsPowerTest = ns.class_("GoatsPowerTest", cg.PollingComponent, spi.SPIDevice)

CONFIG_SCHEMA = cv.Schema({
    cv.GenerateID(): cv.declare_id(GoatsPowerTest),
    cv.Required(CONF_DC_PIN): pins.gpio_output_pin_schema,
    cv.Required(CONF_RESET_PIN): pins.gpio_output_pin_schema,
}).extend(cv.polling_component_schema("1s")).extend(
    spi.spi_device_schema(cs_pin_required=True, default_data_rate=4000000)
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await spi.register_spi_device(var, config)
    cg.add(var.set_dc_pin(await cg.gpio_pin_expression(config[CONF_DC_PIN])))
    cg.add(var.set_reset_pin(await cg.gpio_pin_expression(config[CONF_RESET_PIN])))
