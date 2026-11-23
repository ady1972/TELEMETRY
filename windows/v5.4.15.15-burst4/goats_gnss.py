"""GOATS GNSS: direct UART u-blox identification and conservative CFG-VALSET."""
import struct, time, math
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

CFG_RATE_MEAS=0x30210001
CFG_RATE_NAV=0x30210002
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
    values.update({key:int(ubx and name in ('NAV-PVT','NAV-DOP','NAV-SAT')) for name,key in UBX_UART1.items()})
    values.update({key:int(nmea and name in ('GGA','RMC')) for name,key in NMEA_UART1.items()})
    return values


class GnssAckTimeout(RuntimeError):
    pass


def _ack(link, message, timeout=4.0):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        reply=receive(link,min(.3,max(0,deadline-time.monotonic())))
        if reply and reply[0]==0x05 and reply[2][:2]==message:
            if reply[1]==0x01:return
            if reply[1]==0x00:raise RuntimeError('Configurazione rifiutata dal ricevitore (NAK). Verificare modello e firmware M9N.')
    raise GnssAckTimeout('Nessun ACK: configurazione non verificata. Il ricevitore potrebbe aver cambiato uscita; rileggere i parametri.')


def _valget(link, keys, layer=0):
    if layer not in (0,1,2,7):raise ValueError('Layer CFG-VALGET non valido.')
    if not 1<=len(keys)<=64:raise ValueError('CFG-VALGET richiede da 1 a 64 chiavi.')
    payload=bytes((0,layer,0,0))+b''.join(struct.pack('<I',key) for key in keys)
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
        if data[0]!=1:raise RuntimeError('Versione CFG-VALGET non riconosciuta.')
        if data[1]!=layer or data[2:4]!=b'\x00\x00':continue
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
    keys=list(navigation_profile(('GPS',),'UBX'))+[CFG_RATE_MEAS,CFG_RATE_NAV,CFG_UART1_BAUDRATE]
    with serial.Serial(port,baud,timeout=.1,write_timeout=2) as link:
        link.reset_input_buffer();values=_valget(link,keys)
    ubx=bool(values[CFG_UART1OUTPROT_UBX]);nmea=bool(values[CFG_UART1OUTPROT_NMEA])
    protocol='UBX+NMEA' if ubx and nmea else ('UBX' if ubx else ('NMEA' if nmea else ''))
    return dict(constellations=[name for name,(key,_signal) in CONSTELLATIONS.items() if values[key]],
                protocol=protocol,values=values,uart1_baudrate=values[CFG_UART1_BAUDRATE],**_rate_info(values),**_nav_sat_info(values))


def _key_size(key):
    size={1:1,2:1,3:2,4:4,5:8}.get((key>>28)&7)
    if size is None:raise ValueError('Tipo chiave GNSS non supportato.')
    return size


def _verify_layers(link, values, persistent):
    layers=((0,'RAM'),(2,'FLASH'),(1,'BBR')) if persistent else ((0,'RAM'),)
    for layer,name in layers:
        try:
            actual=_valget(link,values,layer)
            if any(actual[key]!=value for key,value in values.items()):
                raise RuntimeError('I valori riletti non coincidono con quelli richiesti.')
        except RuntimeError as exc:
            raise RuntimeError(f'Salvataggio {name} non verificato: {exc}') from exc


def _write_verified(port, baud, values, persistent=True, new_baud=None, prepare=None):
    if not values:raise ValueError('Nessun parametro GNSS da impostare.')
    changing_baud=new_baud is not None and new_baud!=baud
    with serial.Serial(port,baud,timeout=.1,write_timeout=2) as link:
        link.reset_input_buffer()
        if prepare is not None:values=prepare(link,dict(values))
        payload=bytes((0,7 if persistent else 1,0,0))
        for key,value in values.items():
            payload+=struct.pack('<I',key)+int(value).to_bytes(_key_size(key),'little')
        link.write(packet(0x06,0x8a,payload));link.flush()
        try:
            _ack(link,b'\x06\x8a',timeout=.6 if changing_baud else 4.0)
        except GnssAckTimeout:
            # On a baud change the receiver may send its ACK at the new speed.
            # Only verified readback at that speed can confirm this operation.
            if not changing_baud:raise
        if not changing_baud:_verify_layers(link,values,persistent)
    if changing_baud:
        with serial.Serial(port,new_baud,timeout=.1,write_timeout=2) as link:
            link.reset_input_buffer();_verify_layers(link,values,persistent)
    return values


def valset(port, baud, key, encoded, persistent=True):
    if len(encoded)!=_key_size(key):raise ValueError('Dimensione valore GNSS non valida.')
    value=int.from_bytes(encoded,'little')
    _write_verified(port,baud,{key:value},persistent,
                    new_baud=value if key==CFG_UART1_BAUDRATE else None)
    return True


def _rate_info(values):
    measurement_ms=values[CFG_RATE_MEAS];nav_cycles=values[CFG_RATE_NAV]
    if not 1<=measurement_ms<=65535 or not 1<=nav_cycles<=65535:
        raise RuntimeError('Configurazione frequenza GNSS non valida (intervallo o divisore nullo).')
    return dict(measurement_ms=measurement_ms,nav_cycles=nav_cycles,
                measurement_hz=1000.0/measurement_ms,
                navigation_hz=1000.0/(measurement_ms*nav_cycles))


def _nav_sat_divisor(rates):
    # CFG-MSGOUT rates count navigation solutions; ceil limits the diagnostic
    # stream to ~1 Hz without altering the navigation/measurement frequency.
    return max(1,min(255,math.ceil(_rate_info(rates)['navigation_hz'])))


def _nav_sat_info(values):
    divisor=values[UBX_UART1['NAV-SAT']]
    enabled=bool(values[CFG_UART1OUTPROT_UBX] and divisor)
    return dict(nav_sat_enabled=enabled,nav_sat_divisor=divisor,
                nav_sat_hz=_rate_info(values)['navigation_hz']/divisor if enabled else 0.0)


def set_navigation_rate(port, baud, measurement_ms, nav_cycles=1):
    if (any(isinstance(x,bool) or not isinstance(x,int) for x in (measurement_ms,nav_cycles))
            or not 25<=measurement_ms<=65535 or not 1<=nav_cycles<=127):
        raise ValueError('M9N: intervallo misure da 25 a 65535 ms e divisore NAV da 1 a 127, entrambi interi.')
    values={CFG_RATE_MEAS:measurement_ms,CFG_RATE_NAV:nav_cycles}
    def prepare(link,requested):
        current=_valget(link,[CFG_UART1OUTPROT_UBX,UBX_UART1['NAV-SAT']])
        if current[CFG_UART1OUTPROT_UBX] and current[UBX_UART1['NAV-SAT']]:
            requested[UBX_UART1['NAV-SAT']]=_nav_sat_divisor(requested)
        return requested
    _write_verified(port,baud,values,prepare=prepare)
    return _rate_info(values)


def set_uart1_baud(port, baud, new_baud):
    if new_baud not in BAUDS:raise ValueError('Baud UART1 non supportato dalla pagina GNSS.')
    _write_verified(port,baud,{CFG_UART1_BAUDRATE:new_baud},new_baud=new_baud)
    return new_baud


def apply_navigation_profile(port, baud, constellations, protocol, persistent=True):
    values=navigation_profile(constellations,protocol)
    def prepare(link,requested):
        if requested[CFG_UART1OUTPROT_UBX]:
            rates=_valget(link,[CFG_RATE_MEAS,CFG_RATE_NAV])
            requested[UBX_UART1['NAV-SAT']]=_nav_sat_divisor(rates)
        return requested
    return _write_verified(port,baud,values,persistent,prepare=prepare)
