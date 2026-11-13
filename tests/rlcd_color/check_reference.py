"""Verify that the port uses the actual TEST26 telemetry, not a rewritten subset."""
from pathlib import Path
import re
root = Path(__file__).resolve().parents[2]
reference = root / 'firmware/rlcd-42/GOATS_RLCD_MG902_R12_1_SD_R14_2_TEST_26'
port = root / 'firmware/rlcd-42-3-colori/GOATS_V0406_TEST26'
for source in reference.glob('*.h'):
    assert source.read_bytes() == (port / source.name).read_bytes(), source.name

def section(text, name):
    return re.search(r'^' + name + r':\n.*?(?=^[a-z_]+:|\Z)', text, re.M | re.S)[0]
original = (reference / (reference.name + '.yaml')).read_text()
current = (port / 'goats_42_color_v0406_test26.yaml').read_text()
for name in ['uart', 'esp32', 'logger']:
    assert section(original, name) == section(current, name), name
expected = section(original, 'interval').replace(
    '!id(key_button).state,!id(boot_button).state',
    '!id(key_button).state && !id(up_button).state && !id(back_button).state,!id(boot_button).state')
assert section(current, 'interval') == expected, 'Telemetry scheduling changed'
assert 'tx_pin:' not in section(current, 'uart')
assert not re.search(r'^(wifi|ota|api|web_server):', current, re.M)
for pin in ['GPIO10', 'GPIO9', 'GPIO8', 'GPIO11', 'GPIO12', 'GPIO4', 'GPIO5', 'GPIO6', 'GPIO7']:
    assert pin in current, pin
assert 'platform: adc' not in current  # GPIO4 belongs to the UP key.
assert 'goats_m9n_cfg' not in current
assert (port / 'splash_assets/goats_splash_static.png').is_file()
print('PASS: TEST26 headers, GNSS/UART, framework, USB and telemetry scheduling preserved')
