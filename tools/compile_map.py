#!/usr/bin/env python3
"""Run an installed GoldSrc toolchain without altering the editable source.

Python standard library only. Compilers are a separate user installation.
Outputs go to build/ and, after all stages succeed, cstrike/maps/.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
SOURCE_NAME='de_blue_mesa'
# The release name, with its version, is whatever the generator last exported.
NAME=json.loads((ROOT/'source/geometry.json').read_text())['name']


def find_tool(folder,stage):
    stem='hl'+stage
    names=[stem,stem+'.exe',stem+'_x64.exe','sdHL'+stage.upper(),'sdHL'+stage.upper()+'.exe','sdHL'+stage.upper()+'_x64.exe']
    files={p.name.lower():p for p in folder.iterdir() if p.is_file()}
    # Prefer 64-bit builds on Windows, then normal builds.
    for name in reversed(names):
        if name.lower() in files:return files[name.lower()].resolve()
    raise FileNotFoundError(f'No {stage.upper()} compiler found in {folder}. Expected hl{stage} or sdHL{stage.upper()}.')


def validate_bsp(path):
    raw=path.read_bytes()
    if len(raw)<124 or struct.unpack_from('<i',raw)[0]!=30:
        raise ValueError('Output is not a GoldSrc BSP version 30 file.')
    for i in range(15):
        offset,length=struct.unpack_from('<ii',raw,4+i*8)
        if offset<0 or length<0 or offset+length>len(raw):
            raise ValueError(f'Invalid BSP lump {i}.')
    ent_off,ent_len=struct.unpack_from('<ii',raw,4)
    ent=raw[ent_off:ent_off+ent_len]
    if ent.count(b'"func_bomb_target"')!=2:raise ValueError('Compiled entity data is missing a bomb site.')
    # Geometry, visibility, lighting, clipnodes and models should all exist.
    for i,label in [(3,'vertices'),(4,'visibility'),(7,'faces'),(8,'lighting'),(9,'clipnodes'),(14,'models')]:
        off,length=struct.unpack_from('<ii',raw,4+i*8)
        if length==0:raise ValueError(f'BSP has no {label} data; compilation is incomplete.')


def main():
    parser=argparse.ArgumentParser(description='Compile Blue Mesa with installed VHLT / SDHLT tools.')
    parser.add_argument('--tools',type=Path,help='Directory containing all four compiler executables')
    parser.add_argument('--dry-run',action='store_true',help='Show commands only; no build or file changes')
    args=parser.parse_args()
    folder=args.tools
    if folder is None:
        folder=Path(input('Folder containing CSG, BSP, VIS and RAD compilers: ').strip().strip('"'))
    folder=folder.expanduser().resolve()
    if not folder.is_dir():raise FileNotFoundError(f'Compiler directory does not exist: {folder}')
    stages=[(find_tool(folder,'csg'),['-nowadtextures',NAME]),
            (find_tool(folder,'bsp'),[NAME]),
            (find_tool(folder,'vis'),['-full',NAME]),
            (find_tool(folder,'rad'),['-extra','-bounce','2',NAME])]
    if args.dry_run:
        for exe,options in stages:print(subprocess.list2cmdline([str(exe),*options]))
        print('Working directory:',ROOT/'build')
        return
    build=ROOT/'build';build.mkdir(exist_ok=True)
    original=(ROOT/'source'/f'{SOURCE_NAME}.map').read_text()
    shutil.copy2(ROOT/'source/bluemesa.wad',build/'bluemesa.wad')
    wads=['bluemesa.wad']
    # SDHLT documents sdhlt.wad as a tool WAD. Include it when supplied by
    # the compiler distribution; the original source remains unchanged.
    extra=next((p for p in folder.iterdir() if p.name.lower()=='sdhlt.wad'),None)
    if extra:
        shutil.copy2(extra,build/'sdhlt.wad');wads.append('sdhlt.wad')
    if any('sdhl' in p.name.lower() for p,a in stages) and extra is None:
        raise FileNotFoundError('This SDHLT distribution needs sdhlt.wad next to its compiler executables.')
    text=re.sub(r'"wad"\s+"[^"]*"','"wad" "'+';'.join(wads)+'"',original,count=1)
    (build/f'{NAME}.map').write_text(text)
    # Remove only stale outputs for this map, preventing accidental reuse.
    for ext in ['bsp','err','log','pts','lin','p0','p1','p2','p3','b0','b1','b2','b3','prt','wa_','hsz']:
        (build/f'{NAME}.{ext}').unlink(missing_ok=True)
    for index,(exe,options) in enumerate(stages,1):
        print(f'\n[{index}/4] {exe.name}',flush=True)
        result=subprocess.run([str(exe),*options],cwd=build,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace')
        print(result.stdout,flush=True)
        (build/f'{index}_{exe.stem}.log').write_text(result.stdout)
        err=build/f'{NAME}.err'
        if result.returncode!=0 or (err.exists() and err.stat().st_size):
            raise RuntimeError(f'{exe.name} failed. Read the logs in {build}.')
        if re.search(r'\bLEAK\s+LEAK\s+LEAK\b|\bLEAK in hull\b',result.stdout,re.I):
            raise RuntimeError('Compiler reported a leak. Resolve it before continuing.')
    bsp=build/f'{NAME}.bsp';validate_bsp(bsp)
    dest=ROOT/'cstrike/maps'/bsp.name;shutil.copy2(bsp,dest)
    # A previous release's BSP under another name isn't part of this package.
    for stale in (ROOT/'cstrike/maps').glob('de_blue_mesa*.bsp'):
        if stale.stem!=NAME:stale.unlink()
    print('\nCompilation finished:',dest)
    print('Merge the package cstrike folder into your CS 1.6 cstrike folder.')
    print('Then open the game console and enter: map',NAME)
    print('Run the playtest checklist in README.md before using it on a server.')


if __name__=='__main__':
    try:main()
    except (OSError,ValueError,RuntimeError) as exc:
        print('\nCompilation stopped:',exc,file=sys.stderr);sys.exit(1)
