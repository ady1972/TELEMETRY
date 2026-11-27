#!/usr/bin/env python3
"""Comandi banco STEP3 sulla stessa COM USB del GOATS Manager (nessun UART GPS)."""
import argparse,time
import serial

def connect(name):
    port=serial.Serial(port=None,baudrate=115200,timeout=.2,write_timeout=3)
    port.dtr=False;port.rts=False;port.port=name;port.open()
    port.reset_input_buffer()
    return port

def exchange(port,command,timeout=5):
    port.write((command+'\n').encode('ascii'));port.flush()
    until=time.monotonic()+timeout
    while time.monotonic()<until:
        line=port.readline().decode('ascii',errors='replace').strip()
        if line.startswith(('GREC_','GSD_')):return line
    raise TimeoutError('Nessuna risposta: chiudere ESPHome Web/log e il Manager sulla stessa COM')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',required=True,help='COM USB nativa del laptimer, ad esempio COM5')
    parser.add_argument('command',choices=['status','record','stop','arm','erase'])
    args=parser.parse_args()
    commands={'status':'GREC_STATUS','record':'GREC_START','stop':'GREC_STOP','arm':'GREC_ARM','erase':'GREC_ERASE'}
    if args.command=='erase':print('Cancello tutte le tracce STEP3 nella flash interna; i circuiti rimangono.')
    with connect(args.port) as port:
        answer=exchange(port,commands[args.command]);print(answer)
        if '_ERR ' in answer:raise SystemExit(1)
        if answer=='GREC_ERASING':
            until=time.monotonic()+120
            while time.monotonic()<until:
                time.sleep(1);answer=exchange(port,'GREC_STATUS');print(answer)
                if 'READY=1' in answer:
                    if 'STATE=PRONTA' not in answer:raise RuntimeError(answer)
                    return
            raise TimeoutError('Cancellazione non completata: controllare stato sulla DIAG3')
if __name__=='__main__':main()
