#!/usr/bin/env python3
"""Independent checks of the exported MAP and WAD, not the generator's objects.

Requires NumPy and SciPy. This is NOT a replacement for CSG/BSP/VIS/RAD or
testing the map inside Counter-Strike 1.6.
"""
import argparse
import heapq
import itertools
import json
import math
import re
import struct
from collections import Counter
from pathlib import Path

import numpy as np
from scipy import ndimage
from scipy.spatial import ConvexHull

ROOT=Path(__file__).resolve().parents[1]
# The release name, with its version, as the generator last exported it.
MAP_NAME=json.loads((ROOT/'source/geometry.json').read_text())['name']
NUM=r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?'
FACE=re.compile(r'^\(\s*('+NUM+r')\s+('+NUM+r')\s+('+NUM+r')\s*\)\s*'
                r'\(\s*('+NUM+r')\s+('+NUM+r')\s+('+NUM+r')\s*\)\s*'
                r'\(\s*('+NUM+r')\s+('+NUM+r')\s+('+NUM+r')\s*\)\s*(\S+)\s+'
                r'\[([^]]+)\]\s+\[([^]]+)\]\s+('+NUM+r')\s+('+NUM+r')\s+('+NUM+r')$')


def parse_map(path):
    entities=[];depth=0;current=None;brush=None
    for line_no,raw in enumerate(path.read_text().splitlines(),1):
        line=raw.split('//',1)[0].strip()
        if not line:continue
        if line=='{':
            depth+=1
            if depth==1:current={'keys':{},'brushes':[]}
            elif depth==2:brush={'planes':[],'textures':[],'line':line_no}
            else:raise ValueError(f'Bad nesting at {line_no}')
        elif line=='}':
            if depth==2:current['brushes'].append(brush)
            elif depth==1:entities.append(current)
            else:raise ValueError(f'Unmatched closing brace at {line_no}')
            depth-=1
        elif line.startswith('"'):
            m=re.fullmatch(r'"([^"\n]+)"\s+"([^"\n]*)"',line)
            assert depth==1 and m,f'Invalid keyvalue line {line_no}'
            current['keys'][m[1]]=m[2]
        else:
            m=FACE.fullmatch(line)
            assert depth==2 and m,f'Invalid face at line {line_no}'
            pts=np.array([float(m[i]) for i in range(1,10)]).reshape(3,3)
            normal=np.cross(pts[0]-pts[1],pts[2]-pts[1]);size=np.linalg.norm(normal)
            assert size>1e-6,f'Degenerate face at {line_no}'
            normal/=size
            brush['planes'].append((normal,float(normal@pts[1])))
            brush['textures'].append(m[10])
            assert len(m[11].split())==4 and len(m[12].split())==4
            assert float(m[14])>0 and float(m[15])>0
    assert depth==0 and entities[0]['keys']['classname']=='worldspawn'
    for ent in entities:
        for b in ent['brushes']:
            normals=np.array([a for a,d in b['planes']]);dist=np.array([d for a,d in b['planes']]);vertices=[]
            for ids in itertools.combinations(range(len(dist)),3):
                a=normals[list(ids)];d=dist[list(ids)]
                if abs(np.linalg.det(a))<1e-8:continue
                p=np.linalg.solve(a,d)
                if np.all(normals@p-dist<.005):vertices.append(p)
            assert len(vertices)>=4,f'Empty / inverted brush at {b["line"]}'
            v=np.unique(np.round(vertices,3),axis=0)
            assert ConvexHull(v).volume>.01,f'Zero volume at {b["line"]}'
            center=v.mean(axis=0)
            assert np.all(normals@center-dist<-.001),f'Non-convex brush {b["line"]}'
            assert np.max(np.abs(v))<=4096,'Classic map bounds exceeded'
            b.update(min=v.min(axis=0),max=v.max(axis=0),vertices=v,classname=ent['keys']['classname'])
    return entities


def read_wad(path):
    raw=path.read_bytes();magic,count,directory=struct.unpack_from('<4sii',raw)
    assert magic==b'WAD3' and 0<count<512
    assert directory+count*32==len(raw)
    names=[]
    for i in range(count):
        off,disk,size,kind,comp,pad,name=struct.unpack_from('<iiiBBH16s',raw,directory+i*32)
        name=name.split(b'\0')[0].decode('ascii');assert comp==0 and kind==0x43 and disk==size
        assert off>=12 and off+size<=directory
        data=raw[off:off+size]
        tex,w,h,*mips=struct.unpack_from('<16s6I',data)
        assert tex.split(b'\0')[0].decode()==name and w%16==h%16==0
        end=40
        for level,offset in enumerate(mips):
            assert offset==end
            end+=((w>>level)*(h>>level))
        assert struct.unpack_from('<H',data,end)[0]==256 and end+2+768<=size
        names.append(name)
    assert len(set(names))==len(names)
    return set(names)


def overlap(lo,hi,b,epsilon=.01):
    return bool(np.all(hi>b['min']+epsilon) and np.all(lo<b['max']-epsilon))


def check_clean(entities):
    """No slots, no crawl-spaces, no planting on the RV roof.

    A slot is a gap of 1-47 units between two solids at standing height that
    opens onto the floor: too narrow to walk into, wide enough for a dropped
    gun or the bomb to fall in and be lost. Every object should either touch
    what is beside it or leave 48 units, room to walk. Player clip doesn't
    count as solid here (a dropped gun falls straight through it), but a slot
    inside clip is out of anyone's reach, so it is not reported.
    A crawl-space is floor with something overhead 36-72 units up: a crouching
    player (36) fits where a standing one (72) cannot.
    """
    skip=('func_buyzone','func_bomb_target','func_ladder','func_door','func_button')
    allb=[b for e in entities if e['keys']['classname'] not in skip for b in e['brushes']]
    clip=[b for b in allb if set(b['textures'])=={'CLIP'}]
    # Wall art: a plate at most 4 thick whose back is left undrawn against what it hangs on.
    plate=lambda b:'NULL' in b['textures'] and min(b['max'][:2]-b['min'][:2])<=4
    clip_ids={id(b) for b in clip}
    solid=[b for b in allb if id(b) not in clip_ids and not plate(b) and 'AAATRIGGER' not in b['textures']
           and set(b['textures'])!={'sky'}]
    mn=np.array([b['min'] for b in solid]);mx=np.array([b['max'] for b in solid])
    def filled(p,boxes_mn,boxes_mx):
        return bool(((boxes_mn[:,0]<=p[0])&(boxes_mx[:,0]>=p[0])&(boxes_mn[:,1]<=p[1])&(boxes_mx[:,1]>=p[1])
                     &(boxes_mn[:,2]<=p[2])&(boxes_mx[:,2]>=p[2])).any())
    cmn=np.array([b['min'] for b in clip]);cmx=np.array([b['max'] for b in clip])
    slots=[]
    for floor in (0.,-288.):
        # Anything a player can step onto (up to 24 above the floor) is floor, not a wall.
        band=[k for k in range(len(solid)) if mn[k,2]<floor+72 and mx[k,2]>floor+24]
        for i,j in itertools.combinations(band,2):
            g=np.maximum(mn[i,:2]-mx[j,:2],mn[j,:2]-mx[i,:2])
            for a in (0,1):
                gap,ov=g[a],-g[1-a]
                if not(0.5<gap<48 and ov>=24):continue
                lo=max(mn[i,1-a],mn[j,1-a]);hi=min(mx[i,1-a],mx[j,1-a])
                c=np.zeros(3);c[a]=(min(mx[i,a],mx[j,a])+max(mn[i,a],mn[j,a]))/2;c[2]=floor+40
                along=[]
                for t in np.linspace(lo+4,hi-4,6):
                    p=c.copy();p[1-a]=t;along.append(p)
                if sum(filled(p,mn,mx) for p in along)>=4:continue       # a third solid fills it
                if len(clip) and all(filled(p,cmn,cmx) for p in along):continue   # inside clip: unreachable
                ends=[]
                for t in (lo-20,hi+20):
                    p=c.copy();p[1-a]=t;ends.append(not filled(p,mn,mx))
                if any(ends):
                    mid=c.copy();mid[1-a]=(lo+hi)/2
                    slots.append(f'{gap:.0f}u slot at ({mid[0]:.0f},{mid[1]:.0f},{floor:.0f})')
    slots=sorted(set(slots))
    assert not slots,f'Slots where guns or the bomb get lost: {slots}'
    # Crawl-spaces, on an 8-unit grid at both floor levels.
    step=8;xs=np.arange(-1712,1712,step)+4;ys=np.arange(-1664,1664,step)+4;X,Y=np.meshgrid(xs,ys)
    crawl=[]
    for floor in (0.,-288.):
        low=np.zeros(X.shape,bool);over=np.full(X.shape,1e9)
        for k in range(len(solid)):
            m=(X>=mn[k,0])&(X<=mx[k,0])&(Y>=mn[k,1])&(Y<=mx[k,1])
            if mn[k,2]<=floor+18 and mx[k,2]>floor+18:low|=m
            elif floor+18<mn[k,2]<floor+200:over=np.where(m,np.minimum(over,mn[k,2]),over)
        room=(~low)&(over-floor>=36)&(over-floor<72)
        room=ndimage.binary_erosion(room,iterations=2)          # at least a player's width
        lab,n=ndimage.label(room)
        for k in range(1,n+1):
            yy,xx=np.where(lab==k);crawl.append(f'({xs[xx].mean():.0f},{ys[yy].mean():.0f},{floor:.0f})')
    assert not crawl,f'Crawl-spaces a crouching player fits into: {crawl}'
    # Planting: the A zone must stop below the RV roof, the one high place in it.
    a_zone=[b for e in entities if e['keys']['classname']=='func_bomb_target' for b in e['brushes'] if b['max'][2]>0]
    rv_roof=max((b['max'][2] for b in solid if -1424<=b['min'][0]<=-912 and 856<=b['min'][1]<=1072
                 and b['max'][2]>150 and b['max'][2]<200),default=None)
    if rv_roof:assert all(z['max'][2]<rv_roof for z in a_zone),'Bomb site A reaches the RV roof'
    return {'slots_where_items_get_lost':0,'crawl_spaces':0,'plant_zone_stops_below_rv_roof':bool(rv_roof)}


def check_hidden_faces(entities):
    """No undrawn face where a player can see it.

    NULL faces are not drawn. Buried against a wall that is free lightmap space;
    anywhere else GoldSrc shows a see-through smear, with players visible
    through it like a wallhack. Each NULL face is probed one unit in front of
    itself, at its centre and near each corner, and must find a solid there.
    """
    tools={'NULL','CLIP','AAATRIGGER','sky'}
    occ=[b for e in entities if e['keys']['classname'] in ('worldspawn','func_wall') for b in e['brushes']
         if not set(b['textures'])<=tools]
    mn=np.array([b['min'] for b in occ]);mx=np.array([b['max'] for b in occ])
    def covered(p):
        for k in np.where(np.all((mn-.01<=p)&(p<=mx+.01),axis=1))[0]:
            if all(n@p-d<.01 for n,d in occ[k]['planes']):return True
        return False
    exposed=[]
    for e in entities:
        for b in e['brushes']:
            for (n,d),tex in zip(b['planes'],b['textures']):
                if tex!='NULL':continue
                on=b['vertices'][np.abs(b['vertices']@n-d)<.01]
                c=on.mean(axis=0)
                if not all(covered(q+n) for q in [c,*(c+.9*(v-c) for v in on)]):
                    exposed.append(f'({c[0]:.0f},{c[1]:.0f},{c[2]:.0f}) facing {tuple(int(round(x)) for x in n)}')
    assert not exposed,f'{len(exposed)} undrawn (NULL) faces are exposed, first: {exposed[:8]}'
    return 0


def check_overview(starts,entities):
    """Read the overview the way the game does and check players land on the map.

    With ROTATED 1 the 1024x768 image spans 8192/ZOOM units across and 6144/ZOOM
    down, centred on ORIGIN. Every spawn and both bomb sites must map onto drawn
    plan rather than the green void, or dots would float off the map.
    """
    text=(ROOT/f'cstrike/overviews/{MAP_NAME}.txt').read_text()
    zoom=float(re.search(r'ZOOM\s+(\S+)',text)[1])
    ox,oy,oz=(float(v) for v in re.search(r'ORIGIN\s+(\S+)\s+(\S+)\s+(\S+)',text).groups())
    assert int(re.search(r'ROTATED\s+(\S+)',text)[1])==1,'Overview check assumes ROTATED 1'
    image=re.search(r'IMAGE\s+"([^"]+)"',text)[1]
    assert image=='overviews/'+MAP_NAME+'.bmp'
    raw=(ROOT/'cstrike'/image).read_bytes()
    offset=struct.unpack_from('<I',raw,10)[0];w,h=struct.unpack_from('<ii',raw,18)
    bpp,comp=struct.unpack_from('<HI',raw,28)
    # The stock overviews are all exactly this: 8-bit, uncompressed, bottom-up.
    assert raw[:2]==b'BM' and (w,h,bpp,comp)==(1024,768,8,0),'Overview must be a 1024x768 8-bit BMP'
    palette=np.frombuffer(raw[54:54+1024],np.uint8).reshape(256,4)[:,2::-1]
    rgb=palette[np.frombuffer(raw[offset:offset+w*h],np.uint8).reshape(h,w)[::-1]]
    void=np.all(rgb==[0,255,0],axis=2)
    def pixel(x,y):return 512+(x-ox)*zoom/8,384-(y-oy)*zoom/8
    for x,y in [(-1792,-1728),(1792,1728)]:
        px,py=pixel(x,y);assert 0<=px<=w and 0<=py<=h,'World bounds fall outside the overview image'
    points=[p[:2] for _,p in starts]
    for e in entities:
        if e['keys']['classname']=='func_bomb_target':
            b=e['brushes'][0];points.append((b['min'][:2]+b['max'][:2])/2)
    for x,y in points:
        px,py=pixel(x,y)
        assert not void[int(py),int(px)],f'({x:.0f}, {y:.0f}) lands on the overview void'
    return {'image':'1024x768 8-bit BMP','zoom':zoom,'origin':[ox,oy,oz],'rotated':1,
            'units_per_pixel':round(8/zoom,3),'spawns_and_sites_on_drawn_map':len(points)}


def check_sounds(entities,game=None):
    """Ambient emitters sit in open air inside the sealed world; doors use GoldSrc keys."""
    world=[b for e in entities if not e['keys']['classname'].startswith(('trigger','func_buyzone',
           'func_bomb_target','func_ladder')) for b in e['brushes']]
    lo=np.array([b['min'] for b in world]);hi=np.array([b['max'] for b in world])
    sounds=[];looping={}
    for e in entities:
        k=e['keys']
        if k['classname']!='ambient_generic':continue
        p=np.array([float(v) for v in k['origin'].split()])
        flags=int(k['spawnflags'])
        # Exactly one radius flag (everywhere / small / medium / large), plus
        # optionally start-silent (16) and not-looped (32).
        assert 1<=float(k['health'])<=10 and bin(flags&15).count('1')==1 and not flags&~63,\
            f'Bad ambient at {p}'
        # A sound some ambient loops needs a cue point; one only ever played as a
        # one-shot must not have one, or it would repeat until stopped.
        looping[k['message']]=looping.get(k['message'],False) or not flags&32
        for b in world:
            normals=np.array([a for a,d in b['planes']]);dist=np.array([d for a,d in b['planes']])
            assert not np.all(normals@p-dist<0),f'Ambient {k["message"]} at {p} is inside solid geometry'
        # A point entity out in the void leaks the compile. Enclosed means geometry
        # in all six axis directions - true inside the superlab, false in the rock
        # beneath the desert where nothing lies below.
        for axis in range(3):
            others=[i for i in range(3) if i!=axis]
            across=np.all((lo[:,others]<=p[others])&(hi[:,others]>=p[others]),axis=1)
            assert np.any(across&(hi[:,axis]<=p[axis])) and np.any(across&(lo[:,axis]>=p[axis])),\
                f'Ambient {k["message"]} at {p} is not enclosed by world geometry'
        sounds.append(k['message'])
    # A sound the map ships itself must be in the package, named in the .res so
    # servers send it, and in a format GoldSrc plays and loops.
    shipped=sorted(s for s in set(sounds) if (ROOT/'cstrike/sound'/s).is_file())
    res=(ROOT/f'cstrike/maps/{MAP_NAME}.res').read_text()
    for s in shipped:
        assert 'sound/'+s in res,f'{s} ships with the map but is not in {MAP_NAME}.res'
        raw=(ROOT/'cstrike/sound'/s).read_bytes();pos=12;chunks={}
        assert raw[:4]==b'RIFF' and raw[8:12]==b'WAVE',f'{s} is not a WAV'
        while pos+8<=len(raw):
            cid=raw[pos:pos+4];size=struct.unpack_from('<I',raw,pos+4)[0]
            chunks[cid]=(pos,size);pos+=8+size+(size&1)
        tag,ch,rate,_,_,bits=struct.unpack_from('<HHIIHH',raw,chunks[b'fmt '][0]+8)
        assert (tag,ch)==(1,1) and bits in (8,16) and rate in (11025,22050,44100),\
            f'{s}: GoldSrc needs mono 8/16-bit PCM at 11, 22 or 44 kHz'
        if looping[s]:
            assert b'cue ' in chunks,f'{s} has no cue point, so GoldSrc would play it once and stop'
            assert struct.unpack_from('<i',raw,chunks[b'cue '][0]+32)[0]==0,f'{s} loops from mid-file'
        else:
            assert b'cue ' not in chunks,f'{s} is a one-shot but has a cue point, so it would loop forever'
    if game:
        missing=[s for s in set(sounds)-set(shipped)
                 if not any((game/d/'sound'/s).is_file() for d in ('cstrike','valve'))]
        assert not missing,f'Not in the game install at {game}: {missing}'
    doors=[]
    for e in entities:
        if e['keys']['classname']!='func_door':continue
        # `sounds` is Quake's key; GoldSrc's func_door ignores it and stays silent.
        assert 'sounds' not in e['keys'] and 'movesnd' in e['keys'],'func_door needs movesnd, not sounds'
        doors.append({'movesnd':e['keys']['movesnd'],'stopsnd':e['keys'].get('stopsnd','0')})
    named=lambda n:[e for e in entities if e['keys'].get('targetname')==n]
    death=[e['keys']['message'] for e in named('game_playerdie')]
    blast=[]
    for e in entities:
        t=e['keys'].get('target')
        if e['keys']['classname']=='func_bomb_target' and t:
            assert named(t),f'A bomb site fires "{t}" on detonation, but nothing has that name'
            blast+=[x['keys']['message'] for x in named(t) if x['keys']['classname']=='ambient_generic']
    return {'ambient_generic_count':len(sounds),'distinct_files':sorted(set(sounds)),
            'shipped_with_the_map':shipped,'played_on_every_death':death,
            'played_when_the_bomb_explodes':sorted(set(blast)),
            'all_enclosed_and_clear_of_solids':True,'door_sounds':doors,
            'files_confirmed_in_game_install':bool(game)}


def main():
    parser=argparse.ArgumentParser(description='Static checks of the Blue Mesa source.')
    parser.add_argument('--game',type=Path,help='A CS 1.6 folder (holding cstrike/ and valve/); '
                        'confirms every ambient sound file exists in it')
    args=parser.parse_args()
    entities=parse_map(ROOT/'source/de_blue_mesa.map');textures=read_wad(ROOT/'source/bluemesa.wad')
    brushes=[b for e in entities for b in e['brushes']]
    missing=sorted({t for b in brushes for t in b['textures']}-textures)
    assert not missing,f'Missing textures: {missing}'
    classes=Counter(e['keys']['classname'] for e in entities)
    assert classes['func_bomb_target']==2
    assert classes['func_buyzone']==2
    assert classes['info_player_start']==classes['info_player_deathmatch']==16
    # func_door is excluded so a closed door is not mistaken for a permanent wall
    # when the reachability check below looks for a ground route.
    ignored={'func_buyzone','func_bomb_target','func_ladder','func_door'}
    # A sloped CLIP brush is a ramp laid over stair treads to smooth them. The
    # navigation below models brushes as boxes, which would turn the ramp into a
    # solid block over the whole flight; its surface is never more than one
    # step above the treads it covers, so the treads alone stand in for it.
    def ramp(b):
        return set(b['textures'])=={'CLIP'} and any(
            0.01<abs(n[i])<0.99 for n,_ in b['planes'] for i in range(3))
    solids=[b for b in brushes if b['classname'] not in ignored and not ramp(b)]
    ramps=[b for b in brushes if ramp(b)]
    for r in ramps:
        normals=np.array([a for a,d in r['planes']])
        slope=max(n[2] for n in normals if 0.01<n[2]<0.99)
        assert slope>=0.7,f'Ramp at line {r["line"]} is too steep to walk (normal z {slope:.2f})'
    starts=[]
    for e in entities:
        cl=e['keys']['classname']
        if cl not in ('info_player_start','info_player_deathmatch'):continue
        p=np.array(list(map(float,e['keys']['origin'].split())))
        lo=p-[16,16,36];hi=p+[16,16,36]
        bad=[b['line'] for b in solids if overlap(lo,hi,b)]
        assert not bad,f'Spawn {p} overlaps brushes {bad}'
        support=[b for b in solids if abs(b['max'][2]-lo[2])<.1 and
                 np.all(p[:2]>=b['min'][:2]) and np.all(p[:2]<=b['max'][:2])]
        assert support,f'Unsupported spawn {p}'
        team='2' if cl=='info_player_start' else '1'
        zones=[b for q in entities if q['keys']['classname']=='func_buyzone' and q['keys'].get('team')==team for b in q['brushes']]
        assert any(np.all(p>b['min']) and np.all(p<b['max']) for b in zones)
        starts.append((team,p))
    for (_,a),(_,b) in itertools.combinations(starts,2):
        assert not (np.all(np.abs(a-b)<np.array([32,32,72]))),'Overlapping player spawns'
    # Analytic check of the six exported world enclosure slabs. These are located by
    # texture and extent rather than by their index in the brush list, so adding new
    # world geometry cannot silently shift which brushes get checked.
    world=entities[0]['brushes']
    sky=[b for b in world if set(b['textures'])=={'sky'}]
    assert len(sky)==5,f'Expected 5 sky slabs, found {len(sky)}'
    # The ground slab is emitted as several pieces around the descent shafts, so
    # its extent is the union of them rather than any single brush.
    pieces=[b for b in world if 'bm_sand' in b['textures'] and b['max'][2]==0]
    assert pieces,'No ground slab found'
    ground={'min':np.min([b['min'] for b in pieces],axis=0),
            'max':np.max([b['max'] for b in pieces],axis=0)}
    roof=next(b for b in sky if b['min'][2]==768)
    left=next(b for b in sky if b['max'][0]==ground['min'][0])
    right=next(b for b in sky if b['min'][0]==ground['max'][0])
    south=next(b for b in sky if b['max'][1]==ground['min'][1])
    north=next(b for b in sky if b['min'][1]==ground['max'][1])
    assert ground['max'][2]==0 and roof['min'][2]==768
    for b in [left,right,south,north]:assert b['min'][2]<=ground['min'][2] and b['max'][2]>=roof['max'][2]
    assert np.all(roof['min'][:2]==ground['min'][:2]) and np.all(roof['max'][:2]==ground['max'][:2])
    # Navigation for a 32x72 standing player across every floor in the map, not
    # just the desert surface: the superlab sits 288 units down, and the stairs
    # between them are neither one level nor the other. Each grid cell therefore
    # carries every height a player could stand at, and two cells connect when
    # their floors are within one step of each other - which is what makes a
    # staircase traversable in the model instead of a wall.
    step=16;xs=np.arange(-1680,1681,step);ys=np.arange(-1632,1633,step)
    X,Y=np.meshgrid(xs,ys)
    STAND,STEP_UP=72.,18.
    prints={id(b):(X>=b['min'][0])&(X<=b['max'][0])&(Y>=b['min'][1])&(Y<=b['max'][1]) for b in solids}
    wide={id(b):(X>b['min'][0]-17)&(X<b['max'][0]+17)&(Y>b['min'][1]-17)&(Y<b['max'][1]+17)
          for b in solids}
    # Lift platforms carry players, so their tops count as floors even though a
    # moving door is never treated as an obstacle.
    platforms=[b for e in entities if e['keys']['classname']=='func_door' for b in e['brushes']]
    tops={}
    for b in solids+platforms:
        z=round(float(b['max'][2])/4)*4.
        m=(X>=b['min'][0])&(X<=b['max'][0])&(Y>=b['min'][1])&(Y<=b['max'][1])
        tops[z]=m if z not in tops else (tops[z]|m)
    # A floor counts only where a standing player actually fits above it.
    levels_at={}
    for z,mask in sorted(tops.items()):
        blocked=np.zeros(X.shape,dtype=bool)
        for b in solids:
            if b['max'][2]<=z+STEP_UP or b['min'][2]>=z+STAND:continue
            # Only something taller than the player gets the body-radius margin.
            # Waist-high geometry - a counter, or the tread two steps up a
            # staircase - is something you stand beside, not inside.
            blocked|=wide[id(b)] if b['max'][2]>=z+STAND else prints[id(b)]
        for yy,xx in np.argwhere(mask&~blocked):
            levels_at.setdefault((int(yy),int(xx)),[]).append(z)
    # Ladders and lifts move a player vertically, which no step-height rule can
    # express, so the cells they occupy join the floors within their own vertical
    # reach: a ladder its height, a lift its travel. A door that slides or swings
    # lifts nobody. Without the bound, a doorway would join the ground to the top
    # of the sky enclosure and the route check would walk across the roof of the world.
    climb_at={}
    for e in entities:
        cl=e['keys']['classname']
        if cl not in ('func_ladder','func_door'):continue
        lo=np.min([b['min'] for b in e['brushes']],axis=0);hi=np.max([b['max'] for b in e['brushes']],axis=0)
        if cl=='func_door':
            if e['keys'].get('angle') not in ('-1','-2'):continue
            # A door travels its own height minus its lip.
            travel=(hi[2]-lo[2])-float(e['keys'].get('lip',0))
            lo,hi=lo.copy(),hi.copy()
            if e['keys']['angle']=='-2':lo[2]-=travel
            else:hi[2]+=travel
        mask=(X>lo[0]-17)&(X<hi[0]+17)&(Y>lo[1]-17)&(Y<hi[1]+17)
        for yy,xx in np.argwhere(mask):
            climb_at.setdefault((int(yy),int(xx)),[]).append((lo[2]-STEP_UP,hi[2]+STEP_UP))
    def lifts(y,x,z,z2):
        return any(a<=min(z,z2) and max(z,z2)<=b for a,b in climb_at.get((y,x),()))

    def walk(start,blocked_nodes=frozenset()):
        """Dijkstra over (cell, floor height) nodes."""
        dist={start:0.};heap=[(0.,start)]
        while heap:
            d,node=heapq.heappop(heap)
            if d>dist.get(node,math.inf):continue
            y,x,z=node
            for dy,dx in [(-1,0),(1,0),(0,-1),(0,1),(-1,-1),(-1,1),(1,-1),(1,1)]:
                yy,xx=y+dy,x+dx
                if not(0<=yy<len(ys) and 0<=xx<len(xs)):continue
                nd=d+step*(math.sqrt(2) if dx and dy else 1)
                for z2 in levels_at.get((yy,xx),()):
                    if (yy,xx,z2) in blocked_nodes:continue
                    if abs(z2-z)>STEP_UP and not(lifts(y,x,z,z2) or lifts(yy,xx,z,z2)):continue
                    if nd<dist.get((yy,xx,z2),math.inf):
                        dist[(yy,xx,z2)]=nd;heapq.heappush(heap,(nd,(yy,xx,z2)))
            if (y,x) in climb_at:
                for z2 in levels_at.get((y,x),()):
                    if z2==z or (y,x,z2) in blocked_nodes or not lifts(y,x,z,z2):continue
                    nd=d+abs(z2-z)
                    if nd<dist.get((y,x,z2),math.inf):
                        dist[(y,x,z2)]=nd;heapq.heappush(heap,(nd,(y,x,z2)))
        return dist

    def cell(x,y):return (int(np.argmin(abs(ys-y))),int(np.argmin(abs(xs-x))))
    def node(x,y,z):
        c=cell(x,y);opts=levels_at.get(c,[])
        assert opts,f'No floor at {(x,y)}'
        return (*c,min(opts,key=lambda t:abs(t-z)))
    # The descents are the gaps in the ground slab, so they are found from the
    # exported geometry rather than taken on trust from the generator.
    covered=np.zeros(X.shape,dtype=bool)
    for b in pieces:
        covered|=(X>=b['min'][0])&(X<=b['max'][0])&(Y>=b['min'][1])&(Y<=b['max'][1])
    inner=(X>ground['min'][0])&(X<ground['max'][0])&(Y>ground['min'][1])&(Y<ground['max'][1])
    shafts=inner&~covered
    labels,shaft_count=ndimage.label(shafts)
    assert shaft_count>=1,'No descent shafts found in the ground slab'
    # Route through one descent at a time, so a sealed or blocked shaft is
    # reported rather than masked by the others. A bomb site with a single way
    # in is a deathtrap to attack, so two working descents is the floor. The CT
    # hatch is a one-way drop, so this walk - which only steps - never counts it.
    site_b=(1290,860,-288.)          # plant floor, in the superlab, east of the reactor
    spawn_probe=node(0,-1536,38)
    working=[]
    for k in range(1,shaft_count+1):
        # Sever the other descents above the ground plane only - blocking their
        # whole column would also wall off the superlab floor beneath them.
        # Dilated, because a stairwell's treads spill a little wider than the
        # hole they drop through - without this its edge column stays walkable
        # and the descent under test gets credit for someone else's stairs.
        cut=ndimage.binary_dilation(shafts&(labels!=k),iterations=2)&~(labels==k)
        others={(int(y),int(x),z) for y,x in np.argwhere(cut)
                for z in levels_at.get((int(y),int(x)),()) if z>-64}
        if spawn_probe in walk(node(*site_b),others):working.append(int(k))
    def shaft_box(k):
        yy,xx=np.where(labels==k)
        return f'x {xs[xx.min()]}..{xs[xx.max()]} y {ys[yy.min()]}..{ys[yy.max()]}'
    assert len(working)>=2,('Only %d of %d descents reach bomb site B; an underground site '
                            'needs at least two ways in. Working: %s. Blocked: %s'%(
        len(working),shaft_count,
        [shaft_box(k) for k in working] or 'none',
        [shaft_box(k) for k in range(1,shaft_count+1) if k not in working]))
    # The lanes. Each chokepoint is a doorway (x0, y0, x1, y1); shutting it
    # removes its surface cells from the walk. A site must be cut off when all of
    # its entrances are shut, and reachable through each one on its own - which
    # proves the walls leave no way round, and that no entrance is blocked.
    CHOKE={'Long Doors':(-1500,-64,-1372,-32),'Short A':(-880,480,-752,496),
           'Hermanos west door':(-432,944,-416,1088),'CT Gate':(-1028,1248,-900,1280),
           'Mid Doors':(32,-176,160,-144),'Scrapyard Gate':(928,-640,1056,-608)}
    def shut(names):
        cells=set()
        for n in names:
            x0,y0,x1,y1=CHOKE[n]
            for yy in np.where((ys>=y0-16)&(ys<=y1+16))[0]:
                for xx in np.where((xs>=x0)&(xs<=x1))[0]:
                    cells|={(int(yy),int(xx),z) for z in levels_at.get((int(yy),int(xx)),()) if z>-64}
        return frozenset(cells)
    def t_reaches(goal,closed):return spawn_probe in walk(node(*goal),shut(closed))
    a_goal=(-1200,736,0)
    lanes={}
    for site,goal,entries,always in [
            ('A',a_goal,['Long Doors','Short A','Hermanos west door','CT Gate'],[]),
            # Long Doors stay shut for B: the way round through A is real but not a B lane.
            ('B',site_b,['Mid Doors','Scrapyard Gate'],['Long Doors'])]:
        assert not t_reaches(goal,entries+always),f'Ts reach {site} with all of {entries} shut'
        for e in entries:
            assert t_reaches(goal,[o for o in entries if o!=e]+always),f'{site} is not reachable through {e}'
        lanes[site]={'entrances':entries,'cut_off_when_all_shut':True,'each_entrance_open_alone_works':True}
    routes={}
    for site,goal in [('A',a_goal),('B',site_b)]:
        dist=walk(node(*goal))
        for team in ['1','2']:
            lengths=[]
            for t,p in starts:
                if t!=team:continue
                d=dist.get(node(p[0],p[1],p[2]-36))
                assert d is not None,f'No route from {p} to {site}'
                lengths.append(round(float(d)))
            routes[('T' if team=='1' else 'CT')+' to '+site]={
                'all_16_spawns_reachable':True,'floor_height':goal[2],
                'estimated_shortest_path_units':[min(lengths),max(lengths)],
                # 250 u/s is CS 1.6 running speed with a knife or pistol; rifles are slower.
                'seconds_at_250_units_per_second':[round(min(lengths)/250,1),round(max(lengths)/250,1)]}
    # RV staircase and doorway clearances in the exported source.
    stair=[b for b in solids if np.allclose(b['min'][:2],[-1120,800])]
    assert stair and stair[0]['max'][2]==16
    rv_position=np.array([-1080,920,100.0])
    assert not any(overlap(rv_position-[16,16,36],rv_position+[16,16,36],b) for b in solids)
    assert (ROOT/'cstrike/gfx/env').is_dir()
    for side in ['rt','bk','lf','ft','up','dn']:
        raw=(ROOT/'cstrike/gfx/env'/('bmesa'+side+'.tga')).read_bytes()
        w,h=struct.unpack_from('<HH',raw,12);assert (w,h)==(256,256)
    resources=[]
    for raw in (ROOT/f'cstrike/maps/{MAP_NAME}.res').read_text().splitlines():
        resource=raw.split('//',1)[0].strip()
        if resource:assert (ROOT/'cstrike'/resource).is_file(),f'Missing server resource: {resource}'
        resources.append(resource)
    # Clients only fetch the overview from a server if the resource list names it.
    for needed in ('overviews/'+MAP_NAME+'.bmp','overviews/'+MAP_NAME+'.txt'):
        assert needed in resources,f'{needed} is not in {MAP_NAME}.res'
    clean=check_clean(entities)
    clean['exposed_undrawn_faces']=check_hidden_faces(entities)
    overview=check_overview(starts,entities)
    sound=check_sounds(entities,args.game)
    report={
        'status':'PASS: static source checks only',
        'map':MAP_NAME,'brush_count':len(brushes),'entity_count_including_worldspawn':len(entities),
        'custom_texture_count':len(textures),'missing_textures':missing,
        'convex_brushes_with_positive_volume':len(brushes),
        'spawn_counts':{'T':16,'CT':16},'all_spawns_clear_and_supported':True,
        'all_spawns_inside_correct_buy_zones':True,'six_sided_source_enclosure':True,
        'walkable_floor_levels':len(levels_at and set(z for v in levels_at.values() for z in v)),
        'descent_shafts':int(shaft_count),'descents_reaching_site_b':working,
        'objective_count':2,'site_b_floor_height':site_b[2],
        'conservative_ground_route_checks':routes,'lanes':lanes,
        'rv_interior_standing_clearance':True,'skybox_faces':6,'all_resource_list_files_present':True,
        'overview':overview,'sound':sound,'clean':clean,
        'not_verified':['CSG/BSP compilation','VIS visibility and engine limits','RAD lighting',
                        'In-game loading, collisions, doors, ladders and objective behavior',
                        'Skybox orientation in GoldSrc','Match balance, frame rate and bot navigation',
                        'Ambient sound levels and mix in-game',
                        'Overview alignment in-game (the mapping is checked against stock overviews, '
                        'not yet on this map)'],
        'compiled_bsp_included':(ROOT/f'cstrike/maps/{MAP_NAME}.bsp').is_file(),
    }
    out=ROOT/'validation/source_report.json';out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
