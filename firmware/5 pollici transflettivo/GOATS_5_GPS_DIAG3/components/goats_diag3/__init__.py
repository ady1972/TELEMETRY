import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import uart
from esphome.const import CONF_ID

DEPENDENCIES = ["uart"]
ns = cg.esphome_ns.namespace("goats_diag3")
GoatsDiag3 = ns.class_("GoatsDiag3", cg.Component, uart.UARTDevice)
CONFIG_SCHEMA = cv.Schema({cv.GenerateID(): cv.declare_id(GoatsDiag3)}).extend(
    cv.COMPONENT_SCHEMA
).extend(uart.UART_DEVICE_SCHEMA)
FINAL_VALIDATE_SCHEMA = uart.final_validate_device_schema(
    "goats_diag3", require_rx=True, require_tx=True, baud_rate=38400,
    data_bits=8, parity="NONE", stop_bits=1,
)
async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await uart.register_uart_device(var, config)
