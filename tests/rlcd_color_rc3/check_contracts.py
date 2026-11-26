"""The COLOR port consumes the actual RC3.3 core and preserves its scheduling."""
from pathlib import Path
import re
import subprocess
import tempfile
import sys

ROOT=Path(__file__).resolve().parents[2]
REF=ROOT/'firmware/rlcd-42/GOATS_RLCD_RC3_3'
PORT=ROOT/'firmware/rlcd-42-3-colori/GOATS_RLCD_COLOR_RC3_3'
for path in REF.glob('*.h'):
    assert path.read_bytes()==(PORT/path.name).read_bytes(),path.name

def section(text,name):
    return re.search(r'^'+name+r':\n.*?(?=^[a-z_]+:|\Z)',text,re.M|re.S)[0]

mono=(REF.parent/'goats_rlcd_rc3_3.yaml').read_text()
color=(PORT.parent/'goats_42_color_rc3_3.yaml').read_text()
for name in ['uart','esp32','logger']:
    assert section(mono,name)==section(color,name),name
assert section(color,'interval')==section(mono,'interval').replace(
    '!id(key_button).state,!id(boot_button).state',
    '!id(key_button).state && !id(up_button).state && !id(back_button).state,!id(boot_button).state')
assert not re.search(r'^(psram|wifi|ota|api|web_server):',color,re.M)
assert 'platform: adc' not in color and 'tx_pin:' not in color
for pin in ['GPIO10','GPIO9','GPIO8','GPIO11','GPIO12','GPIO4','GPIO5','GPIO6','GPIO7']:
    assert pin in color,pin
assert 'name: goats_rt.rlcd42_color' in color and 'firmware_version: "RC3.3"' in color
assert 'FW: COLOR ${firmware_version}' in color and 'COLOR ${firmware_version}' in color
assert 'race.delta_mode=goats_screen_mode::delta()' in color
assert 'best_active(now)' in color and 'text_visible' in color
old=PORT.parent/'GOATS_V0406_TEST26/components/goats_st7306'
assert (PORT/'components/goats_st7306/pixel_pack.h').read_bytes()==(old/'pixel_pack.h').read_bytes()
def init(text):
    start=text.index('void GoatsST7306::controller_init_()');end=text.index('\n}',start)
    return text[start:end+2]
assert init((PORT/'components/goats_st7306/goats_st7306.cpp').read_text())==init((old/'goats_st7306.cpp').read_text())

with tempfile.TemporaryDirectory() as temp:
    for name,stubs in [('test_clock.cpp','tests/rc2/stubs'),('test_dates.cpp','tests/rc2/stubs'),
                       ('test_screen_mode.cpp','tests/rc2/screen_mode_stubs'),
                       ('test_rlcd_summary.cpp','tests/guition_port/stubs')]:
        exe=Path(temp)/name.removesuffix('.cpp')
        subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror','-Wno-misleading-indentation',
            '-I',str(ROOT/stubs),'-I',str(ROOT/'tests/guition_port/stubs'),
            '-I',str(PORT),str(ROOT/'tests/rc2'/name),'-o',str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    exe=Path(temp)/'pixel_pack'
    subprocess.run(['g++','-std=c++17','-Wall','-Wextra','-Werror',
        '-I',str(PORT/'components/goats_st7306'),str(ROOT/'tests/rlcd_color/test_pixel_pack.cpp'),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
subprocess.run([sys.executable,str(ROOT/'tests/rc2/test_rlcd_restart.py'),str(PORT.relative_to(ROOT))],check=True)
print('PASS: RC3.3 core parity, GNSS/UART, lifecycle scheduling, pinout, native colors,')
print('date/DST, persistent mode, maximum speed/BEST and repeated save/discard/rearm')
