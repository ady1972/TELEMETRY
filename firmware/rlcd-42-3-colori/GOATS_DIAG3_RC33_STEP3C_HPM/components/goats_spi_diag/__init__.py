import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import uart, font
from esphome.const import CONF_ID
DEPENDENCIES=["esp32","uart"]
AUTO_LOAD=["display","font"]
ns=cg.esphome_ns.namespace("goats_spi_diag")
GoatsSpiDiag=ns.class_("GoatsSpiDiag",cg.Component)
SIZES=[13,16,20,28,36,42,44,52,60,64,72,78,82]
CONFIG_SCHEMA=cv.Schema({cv.GenerateID():cv.declare_id(GoatsSpiDiag), cv.Required("gps_uart_id"):cv.use_id(uart.UARTComponent),
 cv.Optional("start_in_diagnostics",default=False):cv.boolean,cv.Optional("delta_screen",default=False):cv.boolean,
 cv.Optional("lcd_data_swap",default=True):cv.boolean,cv.Optional("alignment_test",default=False):cv.boolean,cv.Optional("fast_display",default=True):cv.boolean,cv.Optional("lcd_high_power",default=True):cv.boolean,
 **{cv.Required(f"font_{s}"):cv.use_id(font.Font) for s in SIZES}}).extend(cv.COMPONENT_SCHEMA)
async def to_code(config):
    var=cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var,config)
    u=await cg.get_variable(config["gps_uart_id"])
    cg.add(var.set_gps_uart(u))
    cg.add(var.set_start_in_diagnostics(config["start_in_diagnostics"]))
    cg.add(var.set_delta_screen(config["delta_screen"]))
    cg.add(var.set_lcd_data_swap(config["lcd_data_swap"]))
    cg.add(var.set_alignment_test(config["alignment_test"]))
    cg.add(var.set_fast_display(config["fast_display"]))
    cg.add(var.set_lcd_high_power(config["lcd_high_power"]))
    for i,s in enumerate(SIZES):cg.add(var.set_racing_font(i,await cg.get_variable(config[f"font_{s}"])))
    cg.add_library("SPI",None)
