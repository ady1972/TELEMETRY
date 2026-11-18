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

# u-blox M9 SPG 4.04 interface description UBX-21022436, CFG-SIGNAL,
# CFG-UART1{IN,OUT}PROT and CFG-MSGOUT. UART1 only: USB/SPI/I2C untouched.
CONSTELLATIONS = {
    'GPS': (0x1031001f, 0x10310001),
    'Galileo': (0x10310021, 0x10310007),
    'GLONASS': (0x10310025, 0x10310018),
    'BeiDou': (0x10310022, 0x1031000d),
    'SBAS': (0x10310020, 0x10310005),
    'QZSS': (0x10310024, 0x10310012),
}
NMEA_UART1 = {
    'DTM':0x209100a7, 'GBS':0x209100de, 'GGA':0x209100bb,
    'GLL':0x209100ca, 'GNS':0x209100b6, 'GRS':0x209100cf,
    'GSA':0x209100c0, 'GST':0x209100d4, 'GSV':0x209100c5,
    'RMC':0x209100ac, 'VTG':0x209100b1, 'ZDA':0x209100d9,
}
UBX_UART1 = {'NAV-PVT':0x20910007,'NAV-DOP':0x20910039,
             'NAV-SAT':0x20910016,'NAV-STATUS':0x2091001b}
CFG_UART1INPROT_UBX=0x10730001
CFG_UART1OUTPROT_UBX=0x10740001
CFG_UART1OUTPROT_NMEA=0x10740002


def navigation_profile(constellations, protocol):
    """Build an explicit UART1 preset without changing rate or baud."""
    selected=set(constellations)
    if protocol not in ('UBX','NMEA','UBX+NMEA'):
        raise ValueError('Selezionare UBX, NMEA oppure UBX+NMEA.')
    if selected-set(CONSTELLATIONS):
        raise ValueError('Costellazione non supportata dal profilo M9N.')
    if not selected.intersection(('GPS','Galileo','GLONASS','BeiDou')):
        raise ValueError('Selezionare almeno una costellazione principale.')
    if selected.intersection(('SBAS','QZSS')) and 'GPS' not in selected:
        raise ValueError('SBAS e QZSS richiedono GPS in questo profilo.')
    ubx=protocol in ('UBX','UBX+NMEA');nmea=protocol in ('NMEA','UBX+NMEA')
    values={key:int(name in selected) for name,keys in CONSTELLATIONS.items() for key in keys}
    # Keep the configuration input available even with NMEA-only output.
    values[CFG_UART1INPROT_UBX]=1
    values[CFG_UART1OUTPROT_UBX]=int(ubx)
    values[CFG_UART1OUTPROT_NMEA]=int(nmea)
    values.update({key:int(ubx and name=='NAV-PVT') for name,key in UBX_UART1.items()})
    values.update({key:int(nmea and name in ('GGA','RMC')) for name,key in NMEA_UART1.items()})
    return values


def _ack(link, message, timeout=4.0):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        reply=receive(link,min(.3,max(0,deadline-time.monotonic())))
        if reply and reply[0]==0x05 and reply[2][:2]==message:
            if reply[1]==0x01:return
            if reply[1]==0x00:raise RuntimeError('Configurazione rifiutata dal ricevitore (NAK). Verificare modello e firmware M9N.')
    raise RuntimeError('Nessun ACK: configurazione non verificata. Il ricevitore potrebbe aver cambiato uscita; rileggere i parametri.')


def _valget(link, keys):
    payload=bytes((0,0,0,0))+b''.join(struct.pack('<I',key) for key in keys)
    link.write(packet(0x06,0x8b,payload));link.flush()
    deadline=time.monotonic()+4
    while time.monotonic()<deadline:
        reply=receive(link,.3)
        if not reply:continue
        if reply[:2]==(0x05,0x00) and reply[2][:2]==b'\x06\x8b':
            raise RuntimeError('Lettura CFG-VALGET rifiutata dal ricevitore.')
        if reply[:2]!=(0x06,0x8b):continue
        data=reply[2]
        if len(data)<4:raise RuntimeError('Risposta CFG-VALGET troncata.')
        values={};offset=4
        while offset<len(data):
            if offset+4>len(data):raise RuntimeError('Chiave CFG-VALGET troncata.')
            key=struct.unpack_from('<I',data,offset)[0];offset+=4
            size={1:1,2:1,3:2,4:4,5:8}.get((key>>28)&7)
            if size is None or offset+size>len(data):raise RuntimeError('Valore CFG-VALGET non valido.')
            values[key]=int.from_bytes(data[offset:offset+size],'little');offset+=size
        if not set(keys).issubset(values):raise RuntimeError('CFG-VALGET non contiene tutti i parametri richiesti.')
        return values
    raise RuntimeError('Nessuna risposta CFG-VALGET; controllare porta e baud.')


def read_navigation_profile(port, baud):
    keys=navigation_profile(('GPS',),'UBX')
    with serial.Serial(port,baud,timeout=.1,write_timeout=2) as link:
        link.reset_input_buffer();values=_valget(link,keys)
    ubx=bool(values[CFG_UART1OUTPROT_UBX]);nmea=bool(values[CFG_UART1OUTPROT_NMEA])
    protocol='UBX+NMEA' if ubx and nmea else ('UBX' if ubx else ('NMEA' if nmea else ''))
    return dict(constellations=[name for name,(key,_signal) in CONSTELLATIONS.items() if values[key]],
                protocol=protocol,values=values)


def apply_navigation_profile(port, baud, constellations, protocol, persistent=False):
    values=navigation_profile(constellations,protocol)
    # One CFG-VALSET message; management UBX input stays on. No automatic reset.
    payload=bytes((0,7 if persistent else 1,0,0))
    payload+=b''.join(struct.pack('<IB',key,value) for key,value in values.items())
    with serial.Serial(port,baud,timeout=.1,write_timeout=2) as link:
        link.reset_input_buffer();link.write(packet(0x06,0x8a,payload));link.flush()
        _ack(link,b'\x06\x8a')
        actual=_valget(link,values)
    if any(actual[key]!=value for key,value in values.items()):
        raise RuntimeError('ACK ricevuto, ma la rilettura non coincide: configurazione non verificata.')
    return values
