import os
"""UBX serial device model with distinct RAM, BBR and flash storage."""
import importlib.util
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
VERSION=os.environ.get('GOATS_WINDOWS_VERSION','5.4.15.8')
APP=ROOT/('windows/v'+VERSION+'-burst4')
spec=importlib.util.spec_from_file_location('gnss_storage',APP/'goats_gnss.py')
gnss=importlib.util.module_from_spec(spec);spec.loader.exec_module(gnss)


def width(key):return {1:1,2:1,3:2,4:4,5:8}[(key>>28)&7]


class Device:
    def __init__(self,unsupported_flash=False,ignore_flash=False,nak=False):
        self.defaults=gnss.navigation_profile(('GPS',),'UBX')
        self.defaults.update({gnss.CFG_RATE_MEAS:1000,gnss.CFG_RATE_NAV:1,gnss.CFG_UART1_BAUDRATE:230400})
        self.ram=dict(self.defaults);self.bbr={};self.flash={}
        self.sent=[];self.connections=[];self.unsupported_flash=unsupported_flash
        self.ignore_flash=ignore_flash;self.nak=nak

    def reboot(self,drop_backup=True):
        if drop_backup:self.bbr.clear()
        self.ram={**self.defaults,**self.flash,**self.bbr}

    def connect(self,port,baud,**kwargs):
        self.connections.append(baud)
        device=self
        class Link:
            def __init__(self):self.buffer=bytearray()
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def reset_input_buffer(self):self.buffer.clear()
            def flush(self):pass
            def read(self,n):
                if baud!=device.ram[gnss.CFG_UART1_BAUDRATE]:return b''
                data=bytes(self.buffer[:n]);del self.buffer[:n];return data
            def write(self,frame):
                assert gnss.packet(frame[2],frame[3],frame[6:-2])==frame
                device.sent.append(frame)
                payload=frame[6:-2];message=frame[2:4]
                if message==b'\x06\x8a':
                    if not device.nak:
                        offset=4
                        while offset<len(payload):
                            key=struct.unpack_from('<I',payload,offset)[0];offset+=4
                            size=width(key);value=int.from_bytes(payload[offset:offset+size],'little');offset+=size
                            for bit,bank in ((1,device.ram),(2,device.bbr),(4,device.flash)):
                                if payload[1]&bit and not (bit==4 and device.ignore_flash):bank[key]=value
                    self.buffer+=gnss.packet(5,0 if device.nak else 1,b'\x06\x8a')
                elif message==b'\x06\x8b':
                    layer=payload[1];bank={0:device.ram,1:device.bbr,2:device.flash}[layer]
                    if layer==2 and device.unsupported_flash:
                        self.buffer+=gnss.packet(5,0,b'\x06\x8b');return len(frame)
                    reply=bytes((1,layer,0,0))
                    for offset in range(4,len(payload),4):
                        key=struct.unpack_from('<I',payload,offset)[0]
                        if key in bank:reply+=struct.pack('<I',key)+bank[key].to_bytes(width(key),'little')
                    self.buffer+=gnss.packet(6,0x8b,reply)
                return len(frame)
        return Link()


class StorageTests(unittest.TestCase):
    def use(self,device):return patch.object(gnss.serial,'Serial',side_effect=device.connect)

    def test_profile_defaults_to_all_storage_layers_and_survives_loss_of_backup(self):
        d=Device()
        with self.use(d):expected=gnss.apply_navigation_profile('COM1',230400,('GPS','Galileo'),'UBX+NMEA')
        self.assertEqual(d.sent[0][7],7)
        self.assertEqual([f[7] for f in d.sent if f[3]==0x8b],[0,2,1])
        d.reboot()
        for key,value in expected.items():self.assertEqual(d.ram[key],value)
        self.assertEqual(d.bbr,{})

    def test_flash_mismatch_does_not_report_persistent_success(self):
        d=Device(ignore_flash=True)
        with self.use(d),self.assertRaisesRegex(RuntimeError,'FLASH non verificato'):
            gnss.apply_navigation_profile('COM1',230400,('GPS','Galileo'),'UBX+NMEA')

    def test_unsupported_flash_is_an_error_without_ram_only_fallback(self):
        d=Device(unsupported_flash=True)
        with self.use(d),self.assertRaisesRegex(RuntimeError,'FLASH non verificato'):
            gnss.set_navigation_rate('COM1',230400,40)
        self.assertEqual([f[7] for f in d.sent if f[3]==0x8a],[7])

    def test_read_includes_measurement_period_divisor_and_navigation_hz(self):
        d=Device();d.ram.update({gnss.CFG_RATE_MEAS:40,gnss.CFG_RATE_NAV:2})
        with self.use(d):state=gnss.read_navigation_profile('COM1',230400)
        self.assertEqual((state['measurement_ms'],state['nav_cycles']),(40,2))
        self.assertEqual((state['measurement_hz'],state['navigation_hz']),(25,12.5))
        self.assertEqual(state['uart1_baudrate'],230400)
        self.assertTrue(all(f[3]==0x8b for f in d.sent))

    def test_25_hz_is_40_ms_and_navigation_divisor_one_after_reboot(self):
        d=Device();d.ram[gnss.CFG_RATE_NAV]=4
        with self.use(d):state=gnss.set_navigation_rate('COM1',230400,40,1)
        self.assertEqual(state['navigation_hz'],25)
        d.reboot()
        self.assertEqual((d.ram[gnss.CFG_RATE_MEAS],d.ram[gnss.CFG_RATE_NAV]),(40,1))

    def test_custom_rate_retains_exact_period_and_divisor(self):
        d=Device()
        with self.use(d):state=gnss.set_navigation_rate('COM1',230400,80,3)
        d.reboot()
        self.assertAlmostEqual(state['navigation_hz'],1000/240)
        self.assertEqual((d.ram[gnss.CFG_RATE_MEAS],d.ram[gnss.CFG_RATE_NAV]),(80,3))

    def test_invalid_rate_does_not_open_serial(self):
        for values in ((0,1),(24,1),(40,0),(40,128),(65536,1),(40,1.5),(True,1)):
            with self.subTest(values=values),patch.object(gnss.serial,'Serial') as serial:
                with self.assertRaises(ValueError):gnss.set_navigation_rate('COM1',230400,*values)
                serial.assert_not_called()

    def test_zero_rate_from_receiver_is_not_displayed_as_valid(self):
        d=Device();d.ram[gnss.CFG_RATE_NAV]=0
        with self.use(d),self.assertRaisesRegex(RuntimeError,'frequenza GNSS non valida'):
            gnss.read_navigation_profile('COM1',230400)

    def test_baud_is_verified_at_new_speed_even_when_old_speed_ack_is_lost(self):
        d=Device()
        with self.use(d),patch.object(gnss,'_ack',side_effect=gnss.GnssAckTimeout('ACK at new baud')):
            gnss.set_uart1_baud('COM1',230400,115200)
        self.assertEqual(d.connections,[230400,115200]);d.reboot()
        self.assertEqual(d.ram[gnss.CFG_UART1_BAUDRATE],115200)

    def test_existing_baud_can_be_saved_permanently_without_changing_speed(self):
        d=Device()
        with self.use(d):gnss.set_uart1_baud('COM1',230400,230400)
        self.assertEqual(d.flash[gnss.CFG_UART1_BAUDRATE],230400)
        self.assertEqual(d.connections,[230400])

    def test_nak_does_not_reconnect_or_claim_baud_was_saved(self):
        d=Device(nak=True)
        with self.use(d),self.assertRaisesRegex(RuntimeError,'NAK'):
            gnss.set_uart1_baud('COM1',230400,115200)
        self.assertEqual(d.connections,[230400]);self.assertEqual(d.flash,{})

    def test_valset_defaults_to_flash_and_handles_u2(self):
        d=Device()
        with self.use(d):gnss.valset('COM1',230400,gnss.CFG_RATE_MEAS,struct.pack('<H',40))
        self.assertEqual(d.flash[gnss.CFG_RATE_MEAS],40)

    def test_reply_from_another_layer_is_not_accepted_as_flash_readback(self):
        d=Device();link=d.connect('COM1',230400)
        ram_payload=bytes((1,0,0,0))+struct.pack('<IH',gnss.CFG_RATE_MEAS,40)
        with patch.object(gnss,'receive',return_value=(6,0x8b,ram_payload)), \
             patch.object(gnss.time,'monotonic',side_effect=[0,0,5]):
            with self.assertRaisesRegex(RuntimeError,'Nessuna risposta CFG-VALGET'):
                gnss._valget(link,[gnss.CFG_RATE_MEAS],layer=2)


if __name__=='__main__':unittest.main(verbosity=2)
