import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import uart
from esphome.const import CONF_ID
DEPENDENCIES=["esp32","uart"]
ns=cg.esphome_ns.namespace("goats_spi_diag")
GoatsSpiDiag=ns.class_("GoatsSpiDiag",cg.Component)
CONFIG_SCHEMA=cv.Schema({cv.GenerateID():cv.declare_id(GoatsSpiDiag), cv.Required("gps_uart_id"):cv.use_id(uart.UARTComponent)}).extend(cv.COMPONENT_SCHEMA)
async def to_code(config):
    var=cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var,config)
    u=await cg.get_variable(config["gps_uart_id"])
    cg.add(var.set_gps_uart(u))
    cg.add_library("SPI",None)
