import binascii
import time
from pathlib import Path
import serial
from serial.tools import list_ports

BAUD = 115200  # USB native CDC/JTAG: symbolic setting, not the GNSS baud.


def exchange_readline(port, timeout=12):
    port.timeout = timeout
    data = port.readline()
    if not data:
        raise TimeoutError('Risposta USB scaduta')
    return data.decode('ascii', errors='strict').strip()


def send(port, command):
    port.write((command + '\n').encode('ascii'))
    port.flush()


def decode_filename(hexname):
    return bytes.fromhex(hexname).decode('utf-8', errors='replace')


def connect_port(port_name, diagnostic=None):
    # Do not pulse DTR/RTS: USB-Serial-JTAG devices can reset on port activation.
    p = serial.Serial(port=None, baudrate=BAUD, timeout=0.6, write_timeout=3)
    p.dtr = False
    p.rts = False
    p.port = port_name
    p.open()
    try:
        p.setDTR(False)
        p.setRTS(False)
        p.reset_input_buffer()
        if diagnostic: diagnostic('Porta aperta. Invio GSD_PING; attendo risposta GSD_PONG')
        seen = []
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            send(p, 'GSD_PING')
            for _ in range(4):
                line = p.readline().decode('ascii', errors='replace').strip()
                if line and line not in seen:
                    seen.append(line)
                    if diagnostic: diagnostic('RX: '+repr(line[:160]))
                if line.startswith('GSD_PONG ') and line.split()[-1].startswith('TEST'):
                    p.timeout = 12
                    return p
            time.sleep(0.25)
        raise RuntimeError('Nessuna risposta GSD_PONG compatibile. RX ricevuti: '+repr(seen[:5])+'; verificare firmware e porta COM')
    except Exception:
        p.close()
        raise


def fetch_list(p):
    send(p, 'GSD_STATUS')
    status = exchange_readline(p)
    if not status.startswith('GSD_STATUS '):
        raise RuntimeError('Stato SD inatteso: ' + status)
    if 'READY=0' in status:
        raise RuntimeError(status + ' - MicroSD non pronta')
    if 'LIVE=1' in status or 'SESSION=1' in status:
        raise RuntimeError(status + ' - Terminare prima la sessione')
    send(p, 'GSD_LIST')
    items = []
    seen_begin = False
    for _ in range(10000):
        line = exchange_readline(p)
        if line == 'GSD_LIST_BEGIN':
            seen_begin = True
            continue
        if line.startswith('GSD_LIST_END'):
            if not seen_begin: raise RuntimeError('GSD_LIST_END senza inizio elenco')
            count = line.split()
            if len(count) > 1 and int(count[1]) != len(items):
                raise RuntimeError('Elenco incompleto: ricevuti %d, attesi %s' % (len(items),count[1]))
            return items
        if line.startswith('GSD_ITEM '):
            parts = line.split()
            if len(parts) == 3:
                items.append((decode_filename(parts[1]), int(parts[2])))
        elif line.startswith('GSD_ERR'):
            raise RuntimeError(line)
        elif line:
            raise RuntimeError('Risposta inattesa: ' + line)
    raise RuntimeError('Elenco file troppo lungo')


def fetch_file(p, remote_name, target, callback):
    send(p, 'GSD_GET ' + remote_name.encode('utf-8').hex().upper())
    start = exchange_readline(p)
    if not start.startswith('GSD_BEGIN '):
        raise RuntimeError('Impossibile aprire il file: '+start)
    size = int(start.split()[1])
    received, checksum, last_progress = 0, 0, 0
    # Feature negotiation: older firmware keeps the original single-chunk protocol.
    burst4 = False
    try:
        send(p, 'GSD_CAPS')
        p.timeout = 0.6
        response = p.readline().decode('ascii', errors='replace').strip()
        burst4 = response.startswith('GSD_CAPS ') and 'BURST4=1' in response
    finally:
        p.timeout = 12
    temp = target.with_name(target.name + '.part')
    try:
        with temp.open('wb') as output:
            while True:
                count = min(4, (size - received + 1023) // 1024) if burst4 and received < size else 1
                send(p, 'GSD_NEXT4' if burst4 and received < size else 'GSD_NEXT')
                completed = False
                for _ in range(count):
                    line = exchange_readline(p)
                    if line.startswith('GSD_END '):
                        expected = int(line.split()[1], 16)
                        if received != size or checksum != expected:
                            raise RuntimeError(f'CRC/dimensione errati: {received}/{size} byte')
                        completed = True
                        break
                    if not line.startswith('GSD '):
                        raise RuntimeError('Risposta inattesa: '+line)
                    data = bytes.fromhex(line[4:])
                    output.write(data)
                    checksum = binascii.crc32(data, checksum) & 0xffffffff
                    received += len(data)
                    if received > size:
                        raise RuntimeError('File maggiore della dimensione dichiarata')
                    if received - last_progress >= 1024 * 64 or received == size:
                        callback(remote_name, received, size)
                        last_progress = received
                if completed:
                    break
        temp.replace(target)
    except Exception:
        temp.unlink(missing_ok=True)
        try: send(p, 'GSD_CANCEL')
        except Exception: pass
        raise




def delete_file(p, remote_name):
    """Delete one confirmed session file from the laptimer SD (TEST24+)."""
    if not remote_name or not remote_name.upper().endswith(('.CSV', '.GSA3')):
        raise ValueError('Eliminazione consentita solo per sessioni CSV/GSA3')
    send(p, 'GSD_DELETE ' + remote_name.encode('utf-8').hex().upper())
    answer = exchange_readline(p)
    if answer != 'GSD_DELETE_OK':
        raise RuntimeError(f'Eliminazione {remote_name}: {answer} (richiede firmware TEST24)')
