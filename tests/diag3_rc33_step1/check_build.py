from pathlib import Path
import subprocess,json,shlex,tempfile,re
ROOT=Path(__file__).resolve().parents[2]
BUILD=ROOT/'firmware/rlcd-42-3-colori/.esphome/build/goats-diag3-rc33-step1/build'
commands=json.loads((BUILD/'compile_commands.json').read_text())
main=next(c for c in commands if c['file'].endswith('/src/main.cpp'))
impl=next(c for c in commands if c['file'].endswith('/goats_spi_diag/goats_spi_diag.cpp'))
def pp(c,out):
 args=shlex.split(c['command']);clean=[];at=0
 while at<len(args):
  if args[at] in ['-o','-MF','-MT','-MQ']:at+=2;continue
  if args[at] in ['-c','-MD','-MMD','-MP']:at+=1;continue
  clean.append(args[at]);at+=1
 subprocess.run(clean+['-E','-P','-o',str(out)],cwd=c['directory'],capture_output=True,text=True,check=True)
 return out.read_text()
with tempfile.TemporaryDirectory(prefix='step1-scope-') as tmp:
 t=Path(tmp);a=pp(main,t/'main.ii');b=pp(impl,t/'impl.ii')
 assert 'class GoatsLaptimerEngine' not in a and 'namespace goats_b {' not in a
 assert b.count('class GoatsLaptimerEngine')==1 and 'namespace goats_b {' in b
 assert 'goats_hal_millis' not in b
 assert 'uint32_t now=::millis()' in b
 assert 'goats_m9n::poll(gps_uart_)' in b
 compiler=Path(shlex.split(impl['command'])[0]);nm=compiler.with_name(compiler.name.removesuffix('g++')+'nm')
 symbols=subprocess.check_output([str(nm),'--defined-only','-C',str(next(BUILD.glob('*.elf')))],text=True)
 for forbidden in ['goats_b::setup()','goats_b::tick_usb()','esp_vfs_fat_sdmmc_mount','tinyusb_driver_install','sdmmc_card_init']:
  assert forbidden not in symbols,forbidden
print('PASS: real preprocessing shows one private RC3.3 engine, original DIAG3 clocks/polling, no linked RC3.3 USB setup or SD/TinyUSB activation')
