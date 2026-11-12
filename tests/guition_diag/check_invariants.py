"""Run from any directory: python tests/guition_diag/check_invariants.py."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]
base = root / 'firmware/guition-43'
old = 'goats_guition_43_v1_0_20_rlcd26_usb'
new = 'goats_guition_43_v1_0_21_diag_usb'
a, b = base / old, base / new
assert (a / 'goats_laptimer.h').read_bytes() == (b / 'goats_laptimer.h').read_bytes()
modified = {'goats_version.h', 'goats_sd_storage.h', 'goats_nav_sample_queue.h',
            'goats_sessions.h', 'goats_usb_tracks_v1025.h', 'LEGGIMI_V1_0_10.txt'}
for p in a.iterdir():
    if p.name not in modified:
        assert p.read_bytes() == (b / p.name).read_bytes(), p.name

original = (base / (old + '.yaml')).read_text(encoding='utf-8')
diag = (base / (new + '.yaml')).read_text(encoding='utf-8')
def section(text, key):
    return re.search(r'^' + key + r':\n.*?(?=^[A-Za-z_]+:|\Z)', text, re.M | re.S)[0]
for key in ['uart', 'esp32', 'logger', 'display', 'globals']:
    assert section(original, key) == section(diag, key), key
# All LVGL structure and content preserved except firmware/build identification.
expected_ui = section(original, 'lvgl').replace('V1.0.20 RLCD26 USB', 'V1.0.21 DIAG USB')
expected_ui = expected_ui.replace('Build: 05/11/2026 LAYOUT8', 'Build: 12/11/2026 DIAG USB')
assert expected_ui == section(diag, 'lvgl')
for text in [original, diag]:
    assert not re.search(r'^(wifi|ota|web_server|api):', text, re.M)
for name in ['goats_sd_storage.h', 'goats_sessions.h']:
    before = (a / name).read_text(encoding='utf-8')
    after = (b / name).read_text(encoding='utf-8')
    after = '\n'.join(line for line in after.split('\n') if 'goats_diag_v1021::' not in line and '#include "goats_diagnostics.h"' not in line)
    assert before == after, name + ': non-diagnostic difference'
before = (a / 'goats_usb_tracks_v1025.h').read_text(encoding='utf-8')
after = (b / 'goats_usb_tracks_v1025.h').read_text(encoding='utf-8')
after = re.sub(r'  // Read-only guard:.*?\n  void suspend_for_msc', '  void suspend_for_msc', after, flags=re.S)
assert before == after, 'USB protocol implementation changed'
print('PASS: byte-identical laptimer and untouched dependencies; identical UART/GNSS setup, logger, Racing UI, storage/session logic and USB protocol after removing diagnostic hooks')
