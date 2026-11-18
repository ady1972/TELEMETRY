"""GOATS GNSS: direct UART u-blox identification and conservative CFG-VALSET."""
import struct, time
import serial
from serial.tools import list_ports

BAUDS=(9600,38400,57600,115200,230400,460800)

def ports():
    return [p.device for p in list_ports.comports()]

def packet(cls, msg, payload=b''):
    body=bytes((cls,msg))+struct.pack('<H',len(payload))+payload
    a=b=0
    for x in body:
        a=(a+x)&255;b=(b+a)&255
    return b'\xb5\x62'+body+bytes((a,b))

def receive(s, timeout=1.5):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        if s.read(1)!=b'\xb5' or s.read(1)!=b'\x62':continue
        h=s.read(4)
        if len(h)!=4:continue
        n=struct.unpack('<H',h[2:])[0]
        if n>4096:continue
        raw=s.read(n+2)
        if len(raw)!=n+2:continue
        if packet(h[0],h[1],raw[:-2])[-2:]==raw[-2:]:
            return h[0],h[1],raw[:-2]
    return None

def identify(port, baud):
    with serial.Serial(port,baud,timeout=.12,write_timeout=1) as s:
        s.reset_input_buffer()
        s.write(packet(0x0a,0x04)) # MON-VER
        for _ in range(12):
            result=receive(s,.25)
            if result and result[:2]==(0x0a,0x04):
                p=result[2]
                lines=[p[:30].split(b'\0')[0].decode('ascii','replace'),p[30:40].split(b'\0')[0].decode('ascii','replace')]
                lines += [p[i:i+30].split(b'\0')[0].decode('ascii','replace') for i in range(40,len(p),30)]
                return '\n'.join(x for x in lines if x)
    raise RuntimeError('Nessuna risposta UBX MON-VER: controlla porta, baud e collegamenti.')

def valset(port, baud, key, encoded, persistent=False):
    # UBX-CFG-VALSET v0; RAM first, BBR/Flash only when explicitly requested.
    layers=7 if persistent else 1
    payload=bytes((0,layers,0,0))+struct.pack('<I',key)+encoded
    with serial.Serial(port,baud,timeout=.15,write_timeout=1) as s:
        s.reset_input_buffer();s.write(packet(0x06,0x8a,payload))
        for _ in range(12):
            r=receive(s,.2)
            if r and r[:2]==(0x05,0x01) and r[2][:2]==b'\x06\x8a':return True
            if r and r[:2]==(0x05,0x00) and r[2][:2]==b'\x06\x8a':raise RuntimeError('Il ricevitore ha rifiutato CFG-VALSET (NAK).')
    raise RuntimeError('Nessuna conferma ACK: configurazione non verificata.')

CFG_RATE_MEAS=0x30210001
CFG_UART1_BAUDRATE=0x40520001
