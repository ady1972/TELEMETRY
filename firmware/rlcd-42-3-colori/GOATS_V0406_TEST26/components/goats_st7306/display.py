import esphome.codegen as cg
import esphome.config_validation as cv
from esphome import pins
from esphome.components import display, spi
from esphome.const import CONF_ID, CONF_DC_PIN, CONF_RESET_PIN, CONF_LAMBDA
DEPENDENCIES = ["spi"]
ns = cg.esphome_ns.namespace("goats_st7306")
GoatsST7306 = ns.class_("GoatsST7306", display.DisplayBuffer, spi.SPIDevice)
CONFIG_SCHEMA = display.FULL_DISPLAY_SCHEMA.extend({
    cv.GenerateID(): cv.declare_id(GoatsST7306),
    cv.Required(CONF_DC_PIN): pins.gpio_output_pin_schema,
    cv.Required(CONF_RESET_PIN): pins.gpio_output_pin_schema,
}).extend(cv.polling_component_schema("100ms")).extend(spi.spi_device_schema(cs_pin_required=True, default_data_rate=4000000))
async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await display.register_display(var, config)
    await spi.register_spi_device(var, config)
    cg.add(var.set_dc_pin(await cg.gpio_pin_expression(config[CONF_DC_PIN])))
    cg.add(var.set_reset_pin(await cg.gpio_pin_expression(config[CONF_RESET_PIN])))
    if CONF_LAMBDA in config:
        writer = await cg.process_lambda(config[CONF_LAMBDA], [(display.DisplayRef, "it")], return_type=cg.void)
        cg.add(var.set_writer(writer))
