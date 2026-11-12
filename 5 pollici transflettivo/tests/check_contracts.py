from pathlib import Path
import re

root=Path(__file__).resolve().parents[1]
gnss=(root/'config/gnss_passivo.yaml').read_text(encoding='utf-8')
assert 'rx_pin: GPIO17' in gnss and 'baud_rate: 230400' in gnss
assert 'rx_buffer_size: 8192' in gnss and 'tx_pin:' not in gnss
for path in [*root.glob('*.yaml'),*root.glob('config/*.yaml')]:
    text=path.read_text(encoding='utf-8')
    assert not re.search(r'^(wifi|ota|api|web_server|touchscreen|i2c):',text,re.M),path
cpp=(root/'components/goats_core/goats_core.cpp').read_text(encoding='utf-8')
assert 'read_byte' in cpp and 'budget = 4096' in cpp
for forbidden in ['write_array','write_byte','delay(','f_write','f_sync','nvs_commit']:
    assert forbidden not in cpp,forbidden
assert not list(root.rglob('goats_laptimer.h'))
print('PASS: scaffold autonomo, GNSS RX17/230400 passivo, nessun touch/rete/OTA o motore copiato')
