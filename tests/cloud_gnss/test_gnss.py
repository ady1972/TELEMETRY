import os
import importlib.util
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('gnss',ROOT/('windows/v'+os.environ.get('GOATS_WINDOWS_VERSION','5.4.15.6')+'-burst4/goats_gnss.py'))
gnss=importlib.util.module_from_spec(spec);spec.loader.exec_module(gnss)


class Receiver:
    def __init__(self,nak=False,mismatch=False):
        self.buffer=bytearray();self.values={};self.sent=[];self.nak=nak;self.mismatch=mismatch
        if hasattr(gnss,'_nav_sat_divisor'):
            self.values.update({gnss.CFG_RATE_MEAS:40,gnss.CFG_RATE_NAV:1})
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def reset_input_buffer(self):self.buffer.clear()
    def flush(self):pass
    def read(self,n):
        data=bytes(self.buffer[:n]);del self.buffer[:n];return data
    def write(self,data):
        self.sent.append(data)
        assert data==gnss.packet(data[2],data[3],data[6:-2])
        payload=data[6:-2]
        if data[2:4]==b'\x06\x8a':
            if not self.nak:
                for off in range(4,len(payload),5):
                    key,value=struct.unpack_from('<IB',payload,off);self.values[key]=value
            self.buffer+=b'$GNRMC,synthetic\r\n'+gnss.packet(5,0 if self.nak else 1,b'\x06\x8a')
        elif data[2:4]==b'\x06\x8b':
            reply=bytes((1,payload[1],0,0))
            for off in range(4,len(payload),4):
                key=struct.unpack_from('<I',payload,off)[0];value=self.values[key]
                if self.mismatch and key==gnss.CFG_UART1OUTPROT_NMEA:value=1-value
                size={1:1,2:1,3:2,4:4,5:8}[(key>>28)&7]
                reply+=struct.pack('<I',key)+value.to_bytes(size,'little')
            self.buffer+=gnss.packet(6,0x8b,reply)
        return len(data)


class GnssTests(unittest.TestCase):
    def test_presets_enable_essential_messages_without_rate_or_baud_changes(self):
        for protocol,ubx,nmea in (('UBX',1,0),('NMEA',0,1),('UBX+NMEA',1,1)):
            with self.subTest(protocol=protocol):
                values=gnss.navigation_profile(('GPS','Galileo','GLONASS','BeiDou','SBAS'),protocol)
                self.assertNotIn(gnss.CFG_RATE_MEAS,values);self.assertNotIn(gnss.CFG_UART1_BAUDRATE,values)
                self.assertEqual(values[gnss.CFG_UART1INPROT_UBX],1)
                self.assertEqual(values[gnss.CFG_UART1OUTPROT_UBX],ubx)
                self.assertEqual(values[gnss.CFG_UART1OUTPROT_NMEA],nmea)
                self.assertEqual(values[gnss.UBX_UART1['NAV-PVT']],ubx)
                for name,key in gnss.NMEA_UART1.items():
                    self.assertEqual(values[key],int(bool(nmea) and name in ('GGA','RMC')))

    def test_invalid_constellation_combinations_do_not_open_serial(self):
        for names,protocol in (([], 'UBX'),(['SBAS'],'NMEA'),(['Galileo','QZSS'],'UBX'),(['IMES'],'UBX'),(['GPS'],'RTCM')):
            with self.subTest(names=names,protocol=protocol),patch.object(gnss.serial,'Serial') as serial:
                with self.assertRaises(ValueError):gnss.apply_navigation_profile('COM1',230400,names,protocol)
                serial.assert_not_called()

    def test_all_constellations_and_signal_bands_follow_selection(self):
        values=gnss.navigation_profile(('Galileo',),'UBX')
        for name,keys in gnss.CONSTELLATIONS.items():
            for key in keys:self.assertEqual(values[key],int(name=='Galileo'))

    def test_ack_and_readback_are_required_for_success(self):
        receiver=Receiver()
        with patch.object(gnss.serial,'Serial',return_value=receiver):
            result=gnss.apply_navigation_profile('COM1',230400,('GPS','SBAS'),'UBX+NMEA',persistent=False)
        self.assertEqual(result,{key:receiver.values[key] for key in result})
        expected=[b'\x06\x8a',b'\x06\x8b']
        if hasattr(gnss,'_nav_sat_divisor'):expected.insert(0,b'\x06\x8b')
        self.assertEqual([frame[2:4] for frame in receiver.sent],expected)
        written=next(frame for frame in receiver.sent if frame[3]==0x8a)
        self.assertEqual(written[6:10],bytes((0,1,0,0)))

    def test_explicit_persistence_writes_all_layers(self):
        receiver=Receiver()
        with patch.object(gnss.serial,'Serial',return_value=receiver):
            gnss.apply_navigation_profile('COM1',230400,('GPS',),'NMEA',persistent=True)
        self.assertEqual(next(f for f in receiver.sent if f[3]==0x8a)[7],7)

    def test_nak_and_mismatched_readback_are_not_reported_as_applied(self):
        for receiver in (Receiver(nak=True),Receiver(mismatch=True)):
            with self.subTest(receiver=receiver),patch.object(gnss.serial,'Serial',return_value=receiver):
                with self.assertRaises(RuntimeError):gnss.apply_navigation_profile('COM1',230400,('GPS',),'UBX')

    def test_timeout_is_not_success(self):
        with patch.object(gnss,'receive',return_value=None),patch.object(gnss.time,'monotonic',side_effect=[0,5]):
            with self.assertRaisesRegex(RuntimeError,'Nessun ACK'):gnss._ack(Receiver(),b'\x06\x8a')

    def test_read_configuration(self):
        receiver=Receiver();receiver.values=gnss.navigation_profile(('GPS','Galileo'),'UBX')
        if hasattr(gnss,'CFG_RATE_NAV'):
            receiver.values.update({gnss.CFG_RATE_MEAS:40,gnss.CFG_RATE_NAV:1,gnss.CFG_UART1_BAUDRATE:230400})
        with patch.object(gnss.serial,'Serial',return_value=receiver):state=gnss.read_navigation_profile('COM1',230400)
        self.assertEqual(state['protocol'],'UBX');self.assertEqual(state['constellations'],['GPS','Galileo'])


if __name__=='__main__':unittest.main(verbosity=2)
