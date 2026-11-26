#!/usr/bin/env python3
"""Run from the source folder or the extracted ESPHome ZIP; no git/network needed."""
from pathlib import Path
import hashlib,json,subprocess,tempfile
BASE=Path(__file__).resolve().parents[1]
TEST=BASE/'tests'
COMP=BASE/'components/goats_diag3'
manifest=json.loads((BASE/'ORIGINE.json').read_text())
for name,digest in manifest['files'].items():
    original=(COMP/name).read_bytes().replace(b'#include "goats_diag3_clock.h"',b'#include <Arduino.h>')
    assert hashlib.sha256(original).hexdigest()==digest,name
with tempfile.TemporaryDirectory(prefix='goats-5-diag3-') as folder:
    folder=Path(folder)
    flags=['g++','-std=c++17','-Wall','-Wextra','-Wno-misleading-indentation',
           '-fsanitize=address,undefined','-fno-omit-frame-pointer',
           '-I'+str(TEST/'stubs'),'-I'+str(COMP)]
    trace=folder/'trace'
    subprocess.run(flags+[str(TEST/'trace.cpp'),'-o',str(trace)],check=True)
    actual=subprocess.check_output([str(trace)])
    assert actual==(TEST/'rlcd_diag3_trace.txt').read_bytes()
    lines=actual.decode().splitlines()
    assert len([x for x in lines if x.startswith('F ')])==17
    assert [int(x[2:]) for x in lines if x.startswith('B ')]==[38400,9600,115200,230400,230400]
    assert sum(int(x[2:]) for x in lines if x.startswith('D '))==2430
    print('PASS: source hashes, 17 byte-identical DIAG3 frames, five baud changes and 2430 ms delays')
    for source in ['test_stability.cpp','test_component.cpp']:
        exe=folder/source.replace('.cpp','')
        extra=[str(COMP/'goats_diag3.cpp')] if source=='test_component.cpp' else []
        subprocess.run(flags+[str(TEST/source)]+extra+['-o',str(exe)],check=True)
        subprocess.run([str(exe)],check=True)
    print('PASS: original stability observer, fix/data losses, stale values, week and timer rollover')
