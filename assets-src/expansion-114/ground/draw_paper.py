"""Build the transparent ink, integer mask, species icon and actual default GLB pigment.

Run with desktop Python (Pillow and NumPy); profiles.py is shared with Blender.
"""
from pathlib import Path
import math
import random
import sys
import numpy as np
from PIL import Image, ImageDraw
from profiles import ANT, GRASS, LEGS, GASTER_SEAMS, GRASS_SEAMS, curve, ellipse, page, antennae

BASE=Path(__file__).resolve().parents[1]
RUNTIME=BASE.parents[1]/'app/src/main/assets/v3'
PALETTE={
    'ant': [(171,75,36),(179,77,34),(149,61,31),(151,65,33),(135,57,31),(121,55,31),(111,51,32)],
    'grasshopper': [(161,158,51),(130,154,45),(135,135,49),(148,159,66),(196,151,42)]
}
INK=(66,48,36)


def tapered(points,radii):
    left=[];right=[]
    for i,((x,y),r) in enumerate(zip(points,radii)):
        x1,y1=points[max(0,i-1)];x2,y2=points[min(len(points)-1,i+1)]
        size=math.hypot(x2-x1,y2-y1)
        dx=r*(y2-y1)/size;dy=-r*(x2-x1)/size
        left.append((x+dx,y+dy));right.append((x-dx,y-dy))
    return left+right[::-1]


def make(kind):
    shapes=ANT if kind=='ant' else GRASS
    out=BASE/kind; out.mkdir(exist_ok=True)
    scale=3
    ink=Image.new('RGB',(1024*scale,1024*scale),'white')
    mask=Image.new('L',(1024,1024),0)
    silhouette=Image.new('L',(1024,1024),0);silpen=ImageDraw.Draw(silhouette)
    pen=ImageDraw.Draw(ink)
    ids=ImageDraw.Draw(mask)
    def xy(pts,s=scale):
        return [(round(a*s),round(b*s)) for a,b in (page(kind,x,y) for x,y in pts)]
    def shape(pts,region=0,fill=(255,255,255),width=2.8):
        pen.polygon(xy(pts),fill=fill)
        pen.line(xy(pts+[pts[0]]),fill=INK,width=round(width*2.05*scale),joint='curve')
        ids.polygon(xy(pts,1),fill=region)
        silpen.polygon(xy(pts,1),fill=255)
    def detail(pts,width=1.25):
        pen.line(xy(pts),fill=INK,width=round(width*2.05*scale),joint='curve')
    def legs(far,foreground):
        for i,leg in enumerate(LEGS[kind]):
            if (i==2) != foreground:continue
            dx,dy=((-14,-10) if far else (0,0))
            if far and i==2 and kind=='grasshopper':dx,dy=2,-4
            p=[(x+dx,y+dy) for x,_,y in leg]
            widths=[3.3,5.3,3.2,2.5,1.8,.8]
            if kind=='grasshopper' and i==2:
                widths=[4.1,5.3,5,4.2,4.0,2.4,.9]
            for j in range(len(p)-1):
                if kind=='grasshopper' and i==2 and j==2:continue
                a,b=p[j:j+2]
                r=widths[j]; s=widths[j+1]
                if kind=='grasshopper' and i==2 and j==3:
                    spikes=[]
                    for t in [.20,.32,.44,.57,.69,.81,.92]:
                        x=a[0]*(1-t)+b[0]*t;y=a[1]*(1-t)+b[1]*t
                        spikes.append([(x+2,y-2),(x+7,y-6),(x+2,y+5)])
                    for triangle in spikes:shape(triangle,width=1.55)
                pts=tapered([a,((a[0]+b[0])*.5,(a[1]+b[1])*.5),b],[r*.8,r*1.07,s*.82])
                shape(pts,width=1.75 if far else 2.1)
            if kind=='grasshopper' and i==2:
                pts=[(x+dx,y+dy) for x,y in curve(GRASS['thigh'])]
                shape(pts,0 if far else 5)
    # Slight parallax makes six legs countable, while the front three explain the gait.
    legs(True,False);legs(True,True);legs(False,False)
    for antenna in antennae(kind):
        p=[(x,y) for x,lat,y in antenna]
        for i,(a,b) in enumerate(zip(p,p[1:])):
            shape(tapered([a,b],[1.55-i*.10,1.50-i*.14]),width=1.25)
    for key in (['gaster','petiole','thorax','head'] if kind=='ant' else ['abdomen','tegmen','pronotum','head']):
        ident=(list(shapes).index(key)+1)
        shape(curve(shapes[key]),ident)
        if key=='tegmen':
            for i in (1,2,3):detail(curve(GRASS_SEAMS[i]),1.05)
        if key=='abdomen':
            for i in (4,5,6):detail(curve(GRASS_SEAMS[i]),1.28)
        if key=='pronotum':detail(curve(GRASS_SEAMS[0]),1.22)
    if kind=='ant':
        legs(False,True)
        area=np.asarray(mask).copy()
        ys,xs=np.where(area==4)
        for seam in GASTER_SEAMS:
            pts=np.array(xy(curve(seam),1))
            thresholds=np.interp(ys,pts[:,1],pts[:,0])
            area[ys[xs>thresholds],xs[xs>thresholds]]+=1
            detail(curve(seam),1.60)
        mask=Image.fromarray(area);ids=ImageDraw.Draw(mask)
        eye=ellipse(160,77,6.7,13.1,31)
        detail(curve('M125 123 C127 117 129 114 132 110'),1.5)
    else:
        legs(False,True)
        eye=ellipse(113,104,8.9,16,17)
        detail(curve('M94 141 C100 135 102 135 106 137 L119 151'),1.6)
    shape(eye,fill=INK,width=.8)
    # Specular dot is visible as a knockout of ink and remains locked.
    white=ellipse(159 if kind=='ant' else 112,73 if kind=='ant' else 98,1.6,3.0,29)
    pen.polygon(xy(white),fill='white')
    antialias=ink.resize((1024,1024),Image.Resampling.LANCZOS)
    alpha=np.rint((255-np.asarray(antialias)[:,:,1].astype(float))/(255-INK[1])*255).clip(0,255).astype('uint8')
    outline=Image.new('RGBA',(1024,1024),INK+(255,))
    outline.putalpha(Image.fromarray(alpha))
    m=np.asarray(mask)
    rgb=np.zeros((1024,1024,3),dtype=np.uint8);rgb[:,:,0]=m
    region_image = Image.fromarray(rgb)
    region_image.save(RUNTIME/f'templates/{kind}-mask.png')
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from finish_outline import finish_outline
    outline = finish_outline(outline, region_image)
    outline.save(RUNTIME/f'templates/{kind}-lines.png', optimize=True)
    # Colored pencil with broken directional strokes, cross-grain, flecks and darker fibres.
    rng=random.Random(346 if kind=='ant' else 899)
    palette=np.array([(151,119,76),*PALETTE[kind]],dtype=float)
    grain=rng.randrange(10000)
    np_rng=np.random.default_rng(grain)
    pigment=Image.fromarray(np.uint8(palette[m]))
    strokes=Image.new('RGBA',(1024,1024)); brush=ImageDraw.Draw(strokes)
    for i in range(33000):
        x=rng.randrange(1024);y=rng.randrange(1024);ident=m[y,x]
        if not ident:continue
        length=rng.uniform(3,25); angle=(-.65 if kind=='ant' or ident==5 else -.17)+rng.uniform(-.38,.38)
        if i%7==0:angle+=1.2
        dx=length*math.cos(angle);dy=length*math.sin(angle)
        c=(247,218,140,rng.randrange(27,84)) if i%3 else (87,56,26,rng.randrange(32,77))
        brush.line([(x,y),(x+dx*.5,y+dy*.52+rng.uniform(-1,1)),(x+dx,y+dy)],fill=c,width=rng.choice([1,2,2,3]))
    pigment=Image.alpha_composite(pigment.convert('RGBA'),strokes).convert('RGB')
    fine=np_rng.normal(0,4.6,(1024,1024,1))
    result=Image.fromarray((np.asarray(pigment).astype(float)+fine).clip(0,255).astype('uint8'))
    # Use a high-quality JPEG for a compact embedded texture; mask/ink stay lossless.
    result.save(out/'pigment.jpg',quality=90,subsampling=0)
    art=Image.new('RGB',(1024,1024),(255,253,245))
    art.paste((165,103,60) if kind=='ant' else (181,158,68),(0,0,1024,1024),silhouette)
    art.paste(result,(0,0),mask.point(lambda x:255 if x else 0))
    art.paste(outline,(0,0),outline);art.save(out/'paper-example.png')
    # Optical master: fewer legs/veins, strong line weights at 40dp. Body
    # outlines knock out background linework behind them, as in the older icons.
    small=Image.new('RGBA',(576,576));ip=ImageDraw.Draw(small)
    purple=(89,71,113,255)
    def icon_points(pts):
        return [(round((48+(x-254)*.197)*6),round((48+(y-119)*.207)*6)) for x,y in pts]
    def stroke(pts,width=2):
        ip.line(icon_points(pts),fill=purple,width=round(width*6),joint='curve')
    def island(pts):
        ip.polygon(icon_points(pts),fill=(0,0,0,0));stroke(pts+[pts[0]],2.45)
    for leg in LEGS[kind]:
        stroke([(x,y) for x,_,y in leg],2.45)
    for feel in antennae(kind):stroke([(x,y) for x,_,y in feel],1.78)
    for key in (['gaster','petiole','thorax','head'] if kind=='ant' else ['abdomen','tegmen','pronotum','head','thigh']):
        island(curve(shapes[key]))
        if key=='gaster':
            for d in GASTER_SEAMS[:2]:stroke(curve(d),1.45)
        if key=='tegmen':stroke(curve(GRASS_SEAMS[3]),1.40)
    ip.polygon(icon_points(eye),fill=purple)
    small.resize((96,96),Image.Resampling.LANCZOS).save(RUNTIME/f'ui/species/{kind}-96.png')
    print(kind,{int(i):int((m==i).sum()) for i in np.unique(m)})

if __name__=='__main__':
    for k in sys.argv[1:] or ['ant','grasshopper']:make(k)
