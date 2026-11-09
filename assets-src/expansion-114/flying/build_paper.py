"""Generate runtime sheets, registered crayon albedo, region index, and PNG review."""
from pathlib import Path
import json
from math import cos, sin, pi
import random
import numpy as np
from PIL import Image, ImageDraw, ImageColor, ImageFilter
from pattern import *
ROOT=Path(__file__).resolve().parents[3]
SOURCE=ROOT/'assets-src/expansion-114'
V3=ROOT/'app/src/main/assets/v3'
N=2

def legs_and_marks(slug):
    # Fixed ink lives outside the paint mask. Legs are behind the paper body.
    legs=[]; marks=[]
    if slug=='dragonfly':
        for s in (-1,1):
            legs.append(([(320+s*9,190),(320+s*18,200),(320+s*15,216)],1.4))
            marks.append((ellipse(320+s*24,137,13.2,17.1,-s*29),False,2.5))
            legs.append((path(((320+s*4,128),(320+s*7,119),(320+s*13,108),(320+s*23,103))),2))
    else:
        for xy in [[(329,646),(312,658),(298,686),(293,708),(277,739),(273,750),(265,768),(253,773),(249,779)],
                   [(352,652),(354,668),(365,694),(370,712),(378,742),(384,755),(393,760),(396,768)],
                   [(389,641),(398,661),(416,676),(424,696),(436,714),(445,730),(452,736),(460,739),(463,744)]]:
            pts=xy
            for j,(a,b) in enumerate(zip(pts,pts[1:])):
                dx,dy=b[0]-a[0],b[1]-a[1]; ll=(dx*dx+dy*dy)**.5
                radius=([5,9.3,7.0,7.3,3.2,2.7,2,1.6] if xy[0][0]==329 else [4.6,6.7,5.7,6.5,3.2,2.5,1.9,1.3])[j]
                nx,ny=dy/ll,-dx/ll
                pts2=[]
                for k in range(17):
                    t=k/16; w=radius*(.29+.71*sin(pi*t)**.67)
                    pts2.append((a[0]+dx*t+w*nx,a[1]+dy*t+w*ny))
                for k in range(16,-1,-1):
                    t=k/16; w=radius*(.29+.71*sin(pi*t)**.67)
                    pts2.append((a[0]+dx*t-w*nx,a[1]+dy*t-w*ny))
                legs.append((pts2,0))
        for points in [[(458,614),(473,604),(486,592),(499,596),(516,601),(528,609)],[(459,622),(484,617),(494,632),(500,647),(506,665)]]:
            legs.append((points,5.7))
        marks.append((ellipse(435.5,626,11.7,22.5,-7),True,1.5))
        legs.append(([(430,650),(438,669),(444,679),(451,662)],2.2))
    return legs,marks

def render(slug):
    out=SOURCE/slug; out.mkdir(exist_ok=True)
    items=specs(slug); legs,marks=legs_and_marks(slug)
    mask=Image.new('L',(1024,1024)); md=ImageDraw.Draw(mask)
    lines=Image.new('RGBA',(1024*N,1024*N)); d=ImageDraw.Draw(lines)
    def pts(points,n=1):return [tuple(round(i*n) for i in sheet(slug,p)) for p in points]
    sc=896/max(BOX[slug][2]-BOX[slug][0],BOX[slug][3]-BOX[slug][1])
    def width(w):return max(1,round(sc*N*w))
    for poly,w in legs:
        p=pts(poly,N)
        if w:d.line(p,fill=INK,width=width(w),joint='curve')
        else:
            d.polygon(p,fill=(0,0,0,0));d.line(p+[p[0]],fill=INK,width=width(2.35),joint='curve')
    for j,(label,poly,color,part) in enumerate(items,1):
        p=pts(poly,N);md.polygon(pts(poly),fill=j)
        d.polygon(p,fill=(0,0,0,0));d.line(p+[p[0]],fill=INK,width=width(1.4 if part=='wing' else 2.15),joint='curve')
    for kind,side in ([('fore',-1),('fore',1),('hind',-1),('hind',1)] if slug=='dragonfly' else []):
        # Avoid redrawing the buried wing roots across the body.
        for q in [0,1]:
            p=pts([wing(slug,kind,side,.057+.943*i/70,q) for i in range(71)],N)
            d.line(p,fill=INK,width=width(2.4),joint='curve')
    for poly,solid,w in marks:
        p=pts(poly,N);md.polygon(pts(poly),fill=0)
        d.polygon(p,fill=INK if solid else (0,0,0,0));d.line(p+[p[0]],fill=INK,width=width(w),joint='curve')
        if solid:
            d.line(pts(path(((434,610),(438,610),(441,616),(441,621))),N),fill='#fffcf4',width=width(2.3))
    # Static pixel flood on each region ensures it has exactly one reachable area.
    raw=np.array(mask); cleaned=raw.copy();counts={}
    from sys import path as pythonpath
    pythonpath.insert(0,str(ROOT/'scripts'))
    from assets_v3_lineart import component_sizes
    for j in range(1,len(items)+1):
        sizes=component_sizes(cleaned,j)
        if len(sizes)>1:
            check=Image.fromarray((cleaned==j).astype('uint8')*255)
            yy,xx=np.where(cleaned==j)
            order=np.random.default_rng(21).permutation(len(yy))
            for idx in order:
                x,y=int(xx[idx]),int(yy[idx])
                if check.getpixel((x,y))!=255:continue
                ImageDraw.floodfill(check,(x,y),128)
                comp=np.asarray(check)==128
                if int(comp.sum())==sizes[0]:
                    cleaned[(cleaned==j)&~comp]=0
                    break
                check.paste(0,(0,0,1024,1024),Image.fromarray(comp))
        counts[j]=int(np.count_nonzero(cleaned==j))
        assert counts[j]>80,(slug,j,counts[j])
    raw=cleaned.copy(); rgb=np.zeros((1024,1024,3),np.uint8);rgb[:,:,0]=raw
    Image.fromarray(rgb).save(V3/'templates'/f'{slug}-mask.png',optimize=True)
    lines=lines.resize((1024,1024),Image.Resampling.LANCZOS)
    lines.save(V3/'templates'/f'{slug}-lines.png',optimize=True)
    icon=lines.resize((96,96),Image.Resampling.LANCZOS); alpha=icon.getchannel('A')
    # Increase optical stroke weight at the small 96px native size.
    alpha=alpha.filter(ImageFilter.MaxFilter(3))
    icon=Image.new('RGBA',(96,96),'#594771');icon.putalpha(alpha)
    icon.save(V3/'ui/species'/f'{slug}-96.png',optimize=True)
    # Fine, directional pencil marks are registered to the editable sheet; only
    # the default sample receives this pigment. User artwork replaces its albedo.
    rr=np.random.default_rng(7401); yy,xx=np.mgrid[:1024,:1024]; arr=np.full((1024,1024,3),235.,float)
    colors=[ImageColor.getrgb(c) for _,_,c,_ in items]
    for j,color in enumerate(colors,1):
        inside=raw==j; base=np.array(color,float)
        name,_,_,part=items[j-1]
        # Sample-internal local pencil variations on segment bands and the cell fields.
        if part=='wing':
            phase=(.63*xx+(1 if (j//3)%2 else -1)*yy*.75)
            amount=7*np.cos(phase*.6)+6*np.sin(.025*xx+.07*yy)+3*np.cos(phase*.16)
            grain=rr.normal(0,6,raw.shape)
            arr[inside]=base+(amount+grain)[inside,None]
        else:
            ys,xs=np.where(inside); mid=(xs.min()+xs.max())/2; rx=max(1,(xs.max()-xs.min())/2)
            if slug=='dragonfly':
                stripe=np.exp(-(((xx-mid)/rx-.16)/.42)**2)*(.53+.36*np.sin(yy*.08+xx*.015))
                gold=np.array([225,188,80]) if name.startswith('tail') else np.array([188,180,84])
                arr[inside]=base+(gold-base)*stripe[inside,None]
            else: arr[inside]=base
            grain=6*np.sin((yy+xx*.44)*.64)+rr.normal(0,8,raw.shape)
            arr[inside]+=grain[inside,None]
    # Individual translucent pencil marks follow the sweep of a wing or the fall
    # of the body pile. Clip each brush layer to the actual registered polygons.
    paint=Image.fromarray(np.uint8(np.clip(arr,0,255))); rng=random.Random(831)
    for kind,side in ([('fore',-1),('fore',1),('hind',-1),('hind',1)] if slug=='dragonfly' else [('fore',1),('hind',-1),('fore',-1)]):
        layer=paint.copy();brush=ImageDraw.Draw(layer,'RGBA')
        ids=[i for i,(n,*_) in enumerate(items,1) if n.startswith(f'{kind}_{side}_')]
        for i in range(600):
            t=rng.uniform(.03,.98);q=rng.random();delta=rng.uniform(.018,.13);bend=rng.uniform(-.055,.055)
            points=[sheet(slug,wing(slug,kind,side,min(1,t+delta*f/4),max(0,min(1,q+bend*f/4)))) for f in range(5)]
            palette=([(245,220,113),(255,238,183),(67,120,160),(91,140,173)] if slug=='dragonfly' else [(222,179,133),(249,223,162),(156,140,173),(213,173,158)])
            brush.line(points,fill=(*rng.choice(palette),rng.randrange(65,168)),width=rng.choice([1,1,2,3]))
        paint.paste(layer,mask=Image.fromarray(np.isin(cleaned,ids).astype('uint8')*255))
    if slug=='honeybee':
        regionid=next(i for i,(name,*_) in enumerate(items,1) if name=='thorax')
        yr,xr=np.where(cleaned==regionid);cx=xr.mean();cy=yr.mean()
        layer=paint.copy();brush=ImageDraw.Draw(layer,'RGBA')
        for k in range(3400):
            i=rng.randrange(len(yr));x,y=xr[i],yr[i]
            # Diverging tan and gold hairs wrap over a darker, warm thorax.
            dx=(x-cx)*.016-.58;dy=(y-cy)*.009+.78
            length=rng.uniform(3.5,9.0); norm=(dx*dx+dy*dy)**.5
            dx*=length/max(.1,norm);dy*=length/max(.1,norm)
            hue=rng.choice([(241,192,94),(234,170,66),(122,78,40),(86,54,32),(255,217,133)])
            brush.line([(x,y),(x+dx*.58-.38,y+dy*.43),(x+dx,y+dy)],fill=(*hue,rng.randrange(104,205)),width=rng.choice([1,1,2]))
        paint.paste(layer,mask=Image.fromarray((cleaned==regionid).astype('uint8')*255))
    arr=np.array(paint,float)
    # Edge bleed for UV interpolation and bilinear filtering.
    for _ in range(40 if slug=='honeybee' else 4):
        alive=raw!=0; pending=~alive
        for dy,dx in [(-1,0),(1,0),(0,-1),(0,1)]:
            take=pending & np.roll(alive,(dy,dx),(0,1))
            arr[take]=np.roll(arr,(dy,dx),(0,1))[take]
            raw[take]=255; pending[take]=False
    albedo=Image.fromarray(np.uint8(np.clip(arr,0,255))).resize((768,768),Image.Resampling.LANCZOS)
    albedo.save(out/'crayon-albedo.jpg',quality=91,subsampling=0,optimize=True)
    sample=Image.new('RGBA',(1024,1024),'#fffcf4')
    colored=albedo.resize((1024,1024)).convert('RGBA'); colored.putalpha(Image.fromarray((cleaned>0).astype('uint8')*255))
    sample.alpha_composite(colored);sample.alpha_composite(lines)
    sample.resize((640,640),Image.Resampling.LANCZOS).convert('RGB').save(out/'paper-sample.png',optimize=True)
    # Repeating hexagonal ommatidia, independently textured from paintable paper.
    ey=Image.new('RGB',(256,256),'#386774' if slug=='dragonfly' else '#39281f');ed=ImageDraw.Draw(ey)
    rng=random.Random(90)
    for row in range(-2,29):
        for col in range(-2,29):
            x=col*10+(row%2)*5;y=row*9
            shade=rng.randrange(-13,15)
            base=[85,143,154] if slug=='dragonfly' else [94,64,45]
            color=tuple(max(0,min(255,c+shade)) for c in base)
            pp=[(x+5.1*cos(pi/6+k*pi/3),y+5.1*sin(pi/6+k*pi/3)) for k in range(6)]
            ed.polygon(pp,fill=color)
    ey.save(out/'compound-eye.jpg',quality=88)
    report=[{'id':j,'name':entry[0],'pixels':counts[j]} for j,entry in enumerate(items,1)]
    (out/'regions.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    print(slug,len(items),counts,flush=True)
if __name__=='__main__':
    for species in BOX:render(species)
