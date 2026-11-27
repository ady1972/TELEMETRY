import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.const import CONF_ID
ns = cg.esphome_ns.namespace('goats_gnss_scan')
GnssScan = ns.class_('GnssScan', cg.Component)
CONFIG_SCHEMA = cv.All(cv.Schema({cv.GenerateID(): cv.declare_id(GnssScan)}).extend(cv.COMPONENT_SCHEMA), cv.only_with_arduino)
async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
