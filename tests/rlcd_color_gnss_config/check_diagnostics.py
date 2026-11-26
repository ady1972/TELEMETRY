"""Ensure the buttonless diagnostic screen does not change UART/GNSS/core behavior.
Run with the ESPHome Python environment.
"""
from pathlib import Path
import subprocess
import sys
import yaml
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'firmware/rlcd-42-3-colori'
class Loader(yaml.SafeLoader):pass
Loader.add_multi_constructor('!',lambda loader,tag,node:loader.construct_scalar(node))
def resolved(name):
    result=subprocess.run([sys.executable,'-m','esphome','config',str(BASE/name)],
                          text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    assert result.returncode==0,result.stderr
    return yaml.load(result.stdout,Loader=Loader)
normal=resolved('goats_42_color_rc3_3.yaml')
diag=resolved('goats_42_color_rc3_3_gps_diag.yaml')
for key in normal:
    if key not in ('esphome','display'):
        assert normal[key]==diag[key],key
for key in normal['esphome']:
    if key not in ('friendly_name','comment'):
        assert normal['esphome'][key]==diag['esphome'][key],key
assert len(normal['display'])==len(diag['display'])==1
for key in normal['display'][0]:
    if key!='lambda':assert normal['display'][0][key]==diag['display'][0][key],key
assert 'DIAG GPS' in diag['display'][0]['lambda']
print('PASS: buttonless diagnostic changes only display lambda, friendly name and comment;')
print('identical resolved UART, boot configurator, GNSS includes, intervals, core, SPI, fonts and buttons')
