"""Validate the two resolved ESPHome profiles used for the physical A/B test."""
from pathlib import Path
import subprocess
import sys
import yaml

root = Path(__file__).resolve().parents[1]


class Loader(yaml.SafeLoader):
    pass


Loader.add_multi_constructor("!", lambda loader, tag, node: loader.construct_scalar(node))


def resolve(name):
    result = subprocess.run(
        [sys.executable, "-m", "esphome", "config", str(root.parent / name)],
        text=True, capture_output=True, check=True,
    )
    return yaml.load(result.stdout, Loader=Loader)


on = resolve("goats_5_transflettivo_rf_rgb_on.yaml")
off = resolve("goats_5_transflettivo_rf_rgb_off.yaml")
normal = resolve("goats_5_transflettivo.yaml")
assert on["uart"] == off["uart"] == normal["uart"]
assert on["goats_core"] == off["goats_core"] == normal["goats_core"]
assert on["esphome"]["project"] == off["esphome"]["project"] == normal["esphome"]["project"]
assert len(on["display"]) == 1 and on["display"] == normal["display"]
assert on["font"] == normal["font"]
assert not off.get("display") and not off.get("font") and not off["esphome"].get("on_boot")
assert on["esphome"]["on_boot"] == normal["esphome"]["on_boot"]
assert on["esphome"]["on_boot"][0]["then"][0]["light.turn_on"]["brightness"] == 0.5
assert on["output"] == off["output"] == normal["output"]
assert on["light"] == off["light"] == normal["light"]
assert off["light"][0]["restore_mode"] == "ALWAYS_OFF"
assert on["logger"] == off["logger"]
assert on["logger"]["baud_rate"] == 115200 and on["logger"]["hardware_uart"] == "UART0"
assert normal["logger"]["baud_rate"] == 0


def neutralize(value):
    if isinstance(value, str):
        return value.replace("RGB_ON", "RGB_TEST").replace("RGB_OFF", "RGB_TEST")
    if isinstance(value, list):
        return [neutralize(item) for item in value]
    if isinstance(value, dict):
        return {key: neutralize(item) for key, item in value.items()}
    return value


assert neutralize(on["interval"]) == neutralize(off["interval"])
assert len(on["interval"]) == len(normal.get("interval", [])) + 1
for config in (on, off):
    assert not any(key in config for key in ("wifi", "ota", "api", "touchscreen", "i2c"))
print("PASS: RGB ON/OFF differ in display/boot only; same passive GNSS, version and USB diagnostics; normal profile unchanged")
