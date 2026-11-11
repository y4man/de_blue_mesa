#!/usr/bin/env python3
"""Render the actual map's faces in software. Not an in-game screenshot.

Pillow and NumPy required. Z buffering and perspective-correct texture
coordinates; simple directional shading approximates the material palette.
"""
import importlib.util
import json
import math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('builder',ROOT/'source/generate_map.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
builder.make_textures()
TEX={k:np.array(v,dtype=float) for k,v in builder.TEX.items()}
M=json.loads((ROOT/'source/geometry.json').read_text())


def normalize(v):return v/np.linalg.norm(v)


def render(camera,target,path,width=1400,height=850,fov=72,cutaway=False):
    camera=np.array(camera,float);forward=normalize(np.array(target,float)-camera)
    right=normalize(np.cross(forward,[0,0,1]));up=np.cross(right,forward)
    rotation=np.array([right,up,forward]);focal=width/(2*math.tan(math.radians(fov)/2))
    top=np.array([59,114,127]);bottom=np.array([208,189,135]);rows=np.linspace(0,1,height)[:,None,None]
    canvas=np.broadcast_to(top[None,None,:]*(1-rows)+bottom[None,None,:]*rows,(height,width,3)).copy()
    zbuffer=np.full((height,width),np.inf)
    sun=normalize(np.array([-.4,-.65,1.]));draw_count=0
    # hlcsg strips these at compile time, so the preview must ignore them too.
    hidden={'NULL','CLIP','AAATRIGGER'}
    for brush in M['brushes']:
        if not brush['solid'] or brush['tag'] in ('sky enclosure','clip'):continue
        if cutaway and any(s in brush['tag'] for s in ['roof','header','lintel','overhead','sky']):continue
        for face in brush['faces']:
            if face['texture'] in hidden:continue
            points=np.array(face['points'],float);normal=np.array(face['normal'])
            if normal@(camera-points[0])<0:continue
            if 'uv' in face:u,v,su,sv=face['uv']
            else:
                axis=np.argmax(np.abs(normal))
                u=[1,0,0,0] if axis!=0 else [0,1,0,0]
                v=[0,-1,0,0] if axis==2 else [0,0,-1,0]
                su=sv=1
            uv=np.column_stack((points@np.array(u[:3])/su+u[3],points@np.array(v[:3])/sv+v[3]))
            positions=(points-camera)@rotation.T
            verts=np.concatenate((positions,uv),axis=1).tolist()
            # Near-plane clip with UV interpolation.
            clipped=[]
            for i,a0 in enumerate(verts):
                a=np.array(a0);b=np.array(verts[(i+1)%len(verts)])
                ia=a[2]>=8;ib=b[2]>=8
                if ia:clipped.append(a)
                if ia!=ib:
                    t=(8-a[2])/(b[2]-a[2]);clipped.append(a+t*(b-a))
            if len(clipped)<3:continue
            verts=np.array(clipped);depth=verts[:,2]
            projected=np.column_stack((width/2+focal*verts[:,0]/depth,height/2-focal*verts[:,1]/depth))
            shade=.59+.41*max(0,float(normal@sun))
            texture=TEX[face['texture']];th,tw=texture.shape[:2]
            for j in range(1,len(verts)-1):
                ids=[0,j,j+1];p=projected[ids];z=depth[ids];tex=verts[ids,3:]
                x0=max(0,int(math.floor(p[:,0].min())));x1=min(width-1,int(math.ceil(p[:,0].max())))
                y0=max(0,int(math.floor(p[:,1].min())));y1=min(height-1,int(math.ceil(p[:,1].max())))
                if x1<x0 or y1<y0:continue
                xx,yy=np.meshgrid(np.arange(x0,x1+1)+.5,np.arange(y0,y1+1)+.5)
                denom=(p[1,1]-p[2,1])*(p[0,0]-p[2,0])+(p[2,0]-p[1,0])*(p[0,1]-p[2,1])
                if abs(denom)<1e-10:continue
                a=((p[1,1]-p[2,1])*(xx-p[2,0])+(p[2,0]-p[1,0])*(yy-p[2,1]))/denom
                b=((p[2,1]-p[0,1])*(xx-p[2,0])+(p[0,0]-p[2,0])*(yy-p[2,1]))/denom
                c=1-a-b;inside=(a>=-1e-7)&(b>=-1e-7)&(c>=-1e-7)
                reciprocal=a/z[0]+b/z[1]+c/z[2]
                zz=1/np.maximum(reciprocal,1e-9)
                zb=zbuffer[y0:y1+1,x0:x1+1];visible=inside&(zz<zb)
                if not visible.any():continue
                tu=(a*tex[0,0]/z[0]+b*tex[1,0]/z[1]+c*tex[2,0]/z[2])*zz
                tv=(a*tex[0,1]/z[0]+b*tex[1,1]/z[1]+c*tex[2,1]/z[2])*zz
                color=texture[np.floor(tv).astype(int)%th,np.floor(tu).astype(int)%tw]*shade
                fog=np.clip((zz-1800)/4500,0,.5)[...,None]
                color=color*(1-fog)+np.array([173,158,118])*fog
                view=canvas[y0:y1+1,x0:x1+1];view[visible]=color[visible];zb[visible]=zz[visible]
                draw_count+=1
    im=Image.fromarray(np.uint8(np.clip(canvas,0,255)))
    im.save(path)
    print(path.name,draw_count)
    return im


if __name__=='__main__':
    rv=render((-1680,336,276),(-1136,976,116),ROOT/'preview/rv_yard.png')
    lab=render((1104,376,106),(1056,984,96),ROOT/'preview/laundry_lab.png',fov=83)
    # A presentation sheet of two actual geometry views.
    out=Image.new('RGB',(1500,2030),(18,29,28));d=ImageDraw.Draw(out)
    d.text((50,36),'BLUE MESA',font=builder.font(68),fill=(235,215,163))
    d.text((54,126),'COUNTER-STRIKE 1.6  /  ORIGINAL DESERT DEFUSAL MAP  /  BY YAMAN',font=builder.font(21),fill=(159,187,172))
    out.paste(rv,(50,190));out.paste(lab,(50,1098))
    d.text((52,1045),'A  /  RV COMPOUND',font=builder.font(23),fill=(229,166,106))
    d.text((52,1954),'B  /  INDUSTRIAL LAUNDRY',font=builder.font(23),fill=(123,208,210))
    d.text((690,1958),'SOURCE GEOMETRY PREVIEW / NOT AN IN-GAME SCREENSHOT',font=builder.font(14,False),fill=(154,177,161))
    out.save(ROOT/'preview/blue_mesa_preview.png')
    # The three named landmarks, rendered from inside with the roofs removed.
    shots=[('superlab.png','THE SUPERLAB  /  BOMB SITE B, 288 UNITS DOWN',(1400,468,-190),(1060,872,-244),82),
           ('hermanos.png','HERMANOS  /  CT SIDE',(0,838,116),(-210,1150,104),74),
           ('law_office.png','LAW OFFICES  /  MOTEL ROW',(-576,300,118),(-950,286,78),76),
           ('residence.png','THE RESIDENCE  /  WEST LANE',(-1232,-1384,120),(-1352,-1000,104),78)]
    rendered=[]
    for name,label,cam,tgt,fov in shots:
        rendered.append((label,render(cam,tgt,ROOT/'preview'/name,width=1300,height=760,fov=fov,cutaway=True)))
    sheet=Image.new('RGB',(1400,3350),(18,29,28));sd=ImageDraw.Draw(sheet)
    sd.text((50,34),'BLUE MESA  /  LANDMARKS',font=builder.font(54),fill=(235,215,163))
    sd.text((54,106),'ORIGINAL HOMAGE ART  /  SOURCE GEOMETRY, NOT IN-GAME SCREENSHOTS',
            font=builder.font(18),fill=(159,187,172))
    for i,(label,im) in enumerate(rendered):
        top=170+i*790
        sd.text((52,top),label,font=builder.font(23),fill=(229,166,106))
        sheet.paste(im,(50,top+34))
    sheet.save(ROOT/'preview/landmarks.png')
    # The chokepoints and the way down, as a player approaching them sees them.
    shots=[('long_doors.png','LONG DOORS  /  FROM OUTSIDE LONG',(-1400,-560,64),(-1436,-40,70),76),
           ('mid_doors.png','MID DOORS  /  FROM THE T SIDE',(-200,-760,64),(96,-160,64),72),
           ('stairs.png','THE STAIR TO B  /  FROM THE LAUNDRY SOUTH DOOR',(952,300,64),(1024,760,-160),80),
           ('lift.png','THE LIFT  /  PRESS E ON THE WASHER, CALL BUTTON ON THE WALL',(900,930,70),(690,1050,20),78),
           ('east_stair.png','THE EAST STAIR  /  INSIDE THE BLOCKHOUSE, FROM THE SCRAPYARD',(1216,-190,64),(1216,300,-200),78),
           ('hatch.png','THE CT HATCH  /  ONE WAY DOWN ONTO B, BESIDE THE LAUNDRY NORTH DOOR',(1144,1190,64),(1296,1060,-20),80)]
    rendered=[(label,render(cam,tgt,ROOT/'preview'/name,width=1300,height=760,fov=fov))
              for name,label,cam,tgt,fov in shots]
    sheet=Image.new('RGB',(1400,170+790*len(rendered)),(18,29,28));sd=ImageDraw.Draw(sheet)
    sd.text((50,34),'BLUE MESA  /  LANES',font=builder.font(54),fill=(235,215,163))
    sd.text((54,106),'SOURCE GEOMETRY, NOT IN-GAME SCREENSHOTS',font=builder.font(18),fill=(159,187,172))
    for i,(label,im) in enumerate(rendered):
        top=170+i*790
        sd.text((52,top),label,font=builder.font(23),fill=(229,166,106))
        sheet.paste(im,(50,top+34))
    sheet.save(ROOT/'preview/lanes.png')
