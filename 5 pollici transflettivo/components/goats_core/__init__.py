import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import uart
from esphome.const import CONF_ID

DEPENDENCIES = ["uart"]
namespace = cg.esphome_ns.namespace("goats_core")
GoatsCore = namespace.class_("GoatsCore", cg.Component, uart.UARTDevice)
CONF_FIRMWARE_VERSION = "firmware_version"

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(GoatsCore),
        cv.Required(CONF_FIRMWARE_VERSION): cv.string,
    }
).extend(cv.COMPONENT_SCHEMA).extend(uart.UART_DEVICE_SCHEMA)

FINAL_VALIDATE_SCHEMA = uart.final_validate_device_schema(
    "goats_core", baud_rate=230400, require_rx=True,
    data_bits=8, parity="NONE", stop_bits=1,
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await uart.register_uart_device(var, config)
    cg.add(var.set_firmware_version(config[CONF_FIRMWARE_VERSION]))
