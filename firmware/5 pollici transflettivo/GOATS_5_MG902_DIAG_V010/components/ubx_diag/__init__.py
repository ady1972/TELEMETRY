import esphome.codegen as cg
from esphome.components import uart
import esphome.config_validation as cv
from esphome.const import CONF_ID

DEPENDENCIES = ["uart"]

CONF_POLL = "poll"
CONF_EXPECTED_RATE = "expected_rate"
CONF_EXPECTED_BAUD = "expected_baud"

ubx_diag_ns = cg.esphome_ns.namespace("ubx_diag")
UbxDiag = ubx_diag_ns.class_("UbxDiag", cg.Component, uart.UARTDevice)

CONFIG_SCHEMA = (
    cv.Schema(
        {
            cv.GenerateID(): cv.declare_id(UbxDiag),
            cv.Optional(CONF_POLL, default=False): cv.boolean,
            cv.Optional(CONF_EXPECTED_RATE, default=25): cv.int_range(min=1, max=50),
            cv.Optional(CONF_EXPECTED_BAUD, default=230400): cv.positive_int,
        }
    )
    .extend(cv.COMPONENT_SCHEMA)
    .extend(uart.UART_DEVICE_SCHEMA)
)

def FINAL_VALIDATE_SCHEMA(config):
    return uart.final_validate_device_schema(
        "ubx_diag", require_rx=True, require_tx=config[CONF_POLL],
        baud_rate=config[CONF_EXPECTED_BAUD], data_bits=8, parity="NONE", stop_bits=1,
    )(config)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await uart.register_uart_device(var, config)
    cg.add(var.set_poll(config[CONF_POLL]))
    cg.add(
        var.set_expected(config[CONF_EXPECTED_RATE], config[CONF_EXPECTED_BAUD])
    )
