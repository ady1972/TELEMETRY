from pathlib import Path
import subprocess,json,shlex,tempfile,re
ROOT=Path(__file__).resolve().parents[2]
BUILD=ROOT/'firmware/rlcd-42-3-colori/.esphome/build/goats-rc33-step3f-backend/build'
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
with tempfile.TemporaryDirectory(prefix='step3f-backend-scope-') as tmp:
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

main_source=Path(main['file']).read_text()
assert main_source.count('App.register_component_(')==4
assert 'register_component_(canvas' not in main_source
assert 'set_start_in_diagnostics(true)' in main_source
assert 'set_delta_screen(false)' in main_source
assert main_source.count('new(gps_uart)')==1
print('PASS: one hardware controller and UART; Canvas is never registered, boot defaults to GPS information')

assert 'goats_step3_store::tick()' in b or 'goats_step3_store' in b
assert 'esp_partition_write' in symbols and 'usb_serial_jtag_driver_install' in symbols
print('PASS: native USB-JTAG and reserved partition linked; no SD mount, MSC/TinyUSB or second GNSS owner')

assert 'set_lcd_data_swap(true)' in main_source and 'set_alignment_test(false)' in main_source
print('PASS: main firmware enables XDE compensation and preserves Racing renderer; no font subsystem changes')

assert 'set_fast_display(true)' in main_source
assert 'HighFrequencyLoopRequester::start()' in symbols and 'HighFrequencyLoopRequester::stop()' in symbols
print('PASS: fast display configured and native scoped high-frequency requester linked')

assert 'set_lcd_high_power(false)' in main_source
print('PASS: main defaults to LPM and preserves UI timing, GNSS and scoped requester')

assert 'set_flicker_test(true)' in main_source
print('PASS: factory starts GPS information; BOOT opens the preserved A/B test')

assert 'set_post_fix_mode(3)' in main_source
print('PASS: factory selects STORE_ONLY: core/telemetry active, Manager init/tick excluded')
