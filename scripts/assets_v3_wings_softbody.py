"""Original Blender butterfly/caterpillar review assets, isolated from the app.

Host --textures writes original pigment / PBR maps. Blender --species builds,
exports, renders, and clean-imports the GLB. No concept image is used as geometry,
texture or background. UV coordinates of the butterfly preserve the drawing view.
"""
import argparse, ast, json, math, random, re, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets-src/v3-review'
TAU=math.tau

def bez(start, curves, steps=28):
    pts=[start]; a=start
    for b,c,d in curves:
        for j in range(1,steps+1):
            t=j/steps
            pts.append(tuple((1-t)**3*a[k]+3*(1-t)**2*t*b[k]+3*(1-t)*t*t*c[k]+t**3*d[k] for k in range(len(a))))
        a=d
    return pts

# Authored from the approved drawing silhouettes; no raster cutout or decal plane.
FORE=bez((.487,.493),[
    ((.441,.350),(.232,.133),(.124,.142)),
    ((.079,.139),(.085,.172),(.106,.242)),
    ((.135,.334),(.074,.458),(.200,.481)),
    ((.305,.502),(.409,.479),(.487,.493))])
HIND=bez((.489,.499),[
    ((.358,.479),(.174,.490),(.158,.553)),
    ((.143,.612),(.203,.716),(.276,.795)),
    ((.315,.838),(.350,.846),(.391,.812)),
    ((.451,.764),(.474,.626),(.489,.499))])
PALETTE=[(141,195,168),(240,206,105),(231,149,167),(173,153,211),
         (159,199,132),(242,207,109),(235,155,177),(176,151,211),(244,224,179)]

def drawing_path(d):
    tokens=re.findall(r'[MCLZ]|-?\d+(?:\.\d+)?',d);i=0;points=[];cur=None;start=None
    def norm(p):return (.5+(p[0]-251)/600,.495+(p[1]-190)/600)
    while i<len(tokens):
        cmd=tokens[i];i+=1
        if cmd in ['M','L']:
            cur=(float(tokens[i]),float(tokens[i+1]));i+=2;points.append(cur)
            if cmd=='M':start=cur
        elif cmd=='C':
            a=tuple(map(float,tokens[i:i+2]));b=tuple(map(float,tokens[i+2:i+4]));c=tuple(map(float,tokens[i+4:i+6]));i+=6
            points.extend(bez(cur,[(a,b,c)],18)[1:]);cur=c
        elif cmd=='Z':points.append(start)
        else:raise ValueError(cmd)
    return [norm(p) for p in points]

# Shared hand-authored 2D contours, read without executing the other asset script.
source=ast.parse((ROOT/'scripts/assets_v3_lineart.py').read_text(encoding='utf8'))
DRAWING={n.targets[0].id:ast.literal_eval(n.value) for n in source.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id.startswith('BUTTERFLY_')}
FORE=drawing_path(DRAWING['BUTTERFLY_UPPER']);HIND=drawing_path(DRAWING['BUTTERFLY_LOWER'])
CAP=drawing_path(DRAWING['BUTTERFLY_TIP']);EDGE=drawing_path(DRAWING['BUTTERFLY_EDGE'])
VEINS=[drawing_path(d) for d in DRAWING['BUTTERFLY_VEINS']]
DOTS=[(.5+(x-251)/600,.495+(y-190)/600,rx/600,ry/600) for x,y,rx,ry in [(66,244,4,4.6),(83,271,4.7,5.4),(97,292,5,6.2),(116,310,6.7,8.4),(140,330,6.6,8.6),(168,332,4.5,6.6)]]

def maps():
    import numpy as np
    from PIL import Image,ImageDraw,ImageFilter
    rng=np.random.default_rng(17231); rr=random.Random(4738)
    def save_maps(folder,name,base,height,rough,normal_strength=2.0):
        folder.mkdir(parents=True,exist_ok=True)
        Image.fromarray(np.uint8(np.clip(base,0,255))).save(folder/f'{name}-basecolor.png')
        h=np.asarray(height,dtype=float)/255
        gy,gx=np.gradient(h)
        n=np.stack((-gx*normal_strength,-gy*normal_strength,np.ones_like(h)),axis=-1)
        n/=np.linalg.norm(n,axis=2)[...,None]
        Image.fromarray(np.uint8(np.clip((n*.5+.5)*255,0,255))).save(folder/f'{name}-normal.png')
        Image.fromarray(np.uint8(np.clip(rough,0,255))).save(folder/f'{name}-roughness.png')
    S=2048; yy,xx=np.mgrid[0:S,0:S];u=xx/S;v=yy/S
    cream=np.array([247,232,212.]);pink=np.array([221,57,132.]);purple=np.array([127,90,191.])
    root=np.exp(-((np.abs(u-.5)/.23)**2+((v-.49)/.25)**2))
    hind=(v>.498).astype(float)
    wave=(np.sin(22*u+19*v)+np.sin(47*u-8*v))*.055
    mix=np.clip(root*.92+hind*.42+wave,0,1)
    pigment=pink[None,None,:]*(1-mix[...,None])+purple[None,None,:]*mix[...,None]
    fiber=np.array(Image.fromarray(np.uint8(rng.random((S//4,S//4))*255)).resize((S,S),Image.Resampling.BICUBIC))/255
    coverage=.63+.28*fiber+.055*rng.random((S,S))
    base=pigment*coverage[...,None]+cream*(1-coverage[...,None])
    im=Image.fromarray(np.uint8(base));d=ImageDraw.Draw(im,'RGBA')
    height=Image.new('L',(S,S),128);hd=ImageDraw.Draw(height)
    # Layered short, irregular wax hatching follows the radiating cells, leaving
    # narrow broken pale streaks; this is not a binary speckle/noise overlay.
    for i in range(48500):
        x=rr.randrange(S);y=rr.randrange(S)
        dx=x-S*.5;dy=y-S*.493
        a=math.atan2(dy,dx)+rr.uniform(-.55,.55)
        le=rr.uniform(6,57);w=rr.choice([1,1,2,2,3,4])
        p=[(x,y),(x+math.cos(a)*le*.5+rr.uniform(-3,3),y+math.sin(a)*le*.5),(x+math.cos(a)*le,y+math.sin(a)*le)]
        light=i%5!=0
        col=(255,240,215,rr.randint(25,85)) if light else (133,69,166,rr.randint(22,65))
        d.line(p,fill=col,width=w,joint='curve');hd.line(p,fill=rr.randint(130,207),width=w)
    def pts(p):return [(x*S,y*S) for x,y in p]
    def mirror(p):return [(1-x,y) for x,y in p]
    dark=(63,39,33,255)
    cap=CAP;veins=VEINS
    for side in [0,1]:
        tr=mirror if side else lambda p:p
        d.polygon(pts(tr(cap)),fill=dark)
        d.polygon(pts(tr(EDGE)),fill=dark)
        for poly in [FORE,HIND]:d.line(pts(tr(poly)),fill=dark,width=7,joint='curve')
        for x,y,rx,ry in DOTS:
            x=1-x if side else x
            d.ellipse(((x-rx)*S,(y-ry)*S,(x+rx)*S,(y+ry)*S),fill=dark)
        for vein in veins:
            p=pts(tr(vein));d.line(p,fill=(101,75,104,84),width=3,joint='curve');hd.line(p,fill=170,width=3)
        # Subtle branching vein architecture, visible in a close-up, not heavy cartoon lines.
    arr=np.array(im);h=np.array(height)
    rough=184+np.array(fiber)*36+(h-128)*.1
    save_maps(OUT/'butterfly/textures','wing',arr,h,rough,3.3)
    # Caterpillar: circumferential body UV. Pigment is continuous across folds,
    # with cream valleys and visible mixed crayon streaks instead of printed noise.
    W=2048;H=1024;yy,xx=np.mgrid[0:H,0:W];t=xx/(W-1);a=yy/H*TAU
    palette=np.array(PALETTE,dtype=float);q=np.clip((t-.06)/.84*8,0,7.999)
    ix=np.floor(q).astype(int);f=q-ix
    # broad colored segments, blend narrowly across their organic junctions
    blend=np.clip((f-.76)/.24,0,1);blend=blend*blend*(3-2*blend)
    col=palette[ix]*(1-blend[...,None])+palette[np.minimum(ix+1,8)]*blend[...,None]
    belly=.12+.19*np.maximum(0,-np.sin(a))
    fiber=np.array(Image.fromarray(np.uint8(rng.random((H//4,W//4))*255)).resize((W,H),Image.Resampling.BICUBIC))/255
    cover=.72+.19*fiber-belly
    img=Image.fromarray(np.uint8(col*cover[...,None]+cream*(1-cover[...,None])))
    d=ImageDraw.Draw(img,'RGBA');hi=Image.new('L',(W,H),126);hd=ImageDraw.Draw(hi)
    for i in range(52000):
        x=rr.randrange(W);y=rr.randrange(H);le=rr.uniform(3,19)
        dx=rr.uniform(-.7,.7)*le;dy=le
        p=[(x,y),(x+dx*.5+rr.uniform(-3,3),y+dy*.48),(x+dx,y+dy)]
        w=rr.choice([1,1,2,2,3]);value=rr.randint(143,205)
        d.line(p,fill=(255,245,213,rr.randint(28,112)) if i%4 else (151,125,91,rr.randint(15,42)),width=w)
        hd.line(p,fill=value,width=w)
    # Fine oblique creases and pigment lodged in them; these complement sculpted folds.
    for i in range(215):
        x=rr.randrange(W);y=rr.randrange(H);length=rr.randrange(9,80)
        p=[(x,y),(x+rr.randrange(-7,8),y+length*.5),(x+rr.randrange(-9,10),y+length)]
        d.line(p,fill=(160,132,97,26),width=1);hd.line(p,fill=94,width=2)
    save_maps(OUT/'caterpillar/textures','skin',np.array(img),np.array(hi),194+fiber*29,2.0)
    # Shared editable cuticle / leaf textures are copied inside each self-contained asset.
    for species in ['butterfly','caterpillar']:
        S=512;grain=rng.random((S,S));fine=np.array(Image.fromarray(np.uint8(grain*255)).filter(ImageFilter.GaussianBlur(.6)))
        yy,xx=np.mgrid[0:S,0:S]
        c=np.array([77,53,37.]) if species=='butterfly' else np.array([161,130,83.])
        val=.72+.36*fine/255
        save_maps(OUT/species/'textures','cuticle',c*val[...,None],fine,175+grain*47,1.5)
        S=1024; yy,xx=np.mgrid[0:S,0:S];u=xx/S;v=yy/S
        grain=rng.random((S,S));val=.75+.28*grain+.12*np.sin(u*TAU*4)*np.sin(v*TAU*7)
        leaf=np.zeros((S,S,3))+np.array([65,110,56]);leaf*=val[...,None]
        veins=np.zeros((S,S),dtype=float)
        for i in range(1,10):
            target=i/10
            dist=np.abs(v-(.5+np.sign(u-.5)*(u-.5)*1.1+target-.5))
            veins=np.maximum(veins,np.exp(-dist**2/.000006))
        veins=np.maximum(veins,np.exp(-(u-.5)**2/.000028))
        leaf+=veins[...,None]*np.array([20,29,2])
        save_maps(OUT/species/'textures','review-leaf',leaf,128+grain*35+veins*68,125+grain*37,3.0)
    print('Original image-based PBR maps written to v3-review species folders')

def build(args):
    import bpy, numpy as np
    from mathutils import Vector, Matrix
    species=args.species;out=args.output_dir.resolve();out.mkdir(parents=True,exist_ok=True)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.render.engine='CYCLES';scene.render.use_persistent_data=True
    scene.cycles.device='CPU';scene.cycles.samples=32;scene.cycles.use_denoising=True
    if args.gpu:
        prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
        for device in prefs.devices:device.use=device.type=='OPTIX'
        scene.cycles.device='GPU';scene.cycles.samples=64
    scene.render.threads_mode='FIXED';scene.render.threads=4
    scene.render.resolution_x=1080;scene.render.resolution_y=900;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
    scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
    scene.render.fps=24;scene.world.color=(.23,.23,.23)
    world=scene.world;world.use_nodes=True;world.node_tree.nodes['Background'].inputs['Color'].default_value=(.63,.68,.63,1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value=.30
    asset=bpy.data.collections.new(species.upper()+'_ASSET');scene.collection.children.link(asset)
    stage=bpy.data.collections.new('REVIEW_STAGING_not_exported');scene.collection.children.link(stage)
    obs=[];bone_specs=[];weights={}
    def to_collection(obj,col):
        for c in list(obj.users_collection):c.objects.unlink(obj)
        col.objects.link(obj)
    def mat(name,color=(.2,.1,.05,1),rough=.72,texture=None,subs=0):
        m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;links=m.node_tree.links;p=n.get('Principled BSDF')
        p.inputs['Base Color'].default_value=color;p.inputs['Roughness'].default_value=rough
        p.inputs['Specular IOR Level'].default_value=.25;p.inputs['Subsurface Weight'].default_value=subs
        if texture:
            for kind,inputname in [('basecolor','Base Color'),('roughness','Roughness'),('normal','Normal')]:
                im=bpy.data.images.load(str(out/'textures'/f'{texture}-{kind}.png'),check_existing=True)
                if kind!='basecolor':im.colorspace_settings.name='Non-Color'
                im.pack();tex=n.new('ShaderNodeTexImage');tex.image=im;tex.label=kind
                if kind=='normal':
                    normal=n.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.50 if texture=='wing' else (.38 if texture=='skin' else .55)
                    links.new(tex.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],p.inputs[inputname])
                else:links.new(tex.outputs['Color'],p.inputs[inputname])
        return m
    cut=mat('Warm matte chitin • image PBR',texture='cuticle')
    eye=mat('Dark compound eye',(.028,.020,.014,1),.28)
    hairmat=mat('Fine pale setae',(.13,.082,.039,1),.87)
    painted=mat('Continuous wax pigment • image PBR',texture='wing' if species=='butterfly' else 'skin',subs=0)
    veinmat=mat('Subtle raised veins',(.21,.12,.15,1),.86)
    cream=mat('Soft cream cuticle',(.72,.61,.39,1),.82)
    def mesh(name,verts,faces,material,uv=None,bone='root',skinweights=None,col=asset):
        me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
        obj=bpy.data.objects.new(name,me);col.objects.link(obj);me.materials.append(material)
        for p in me.polygons:p.use_smooth=True
        uvlay=me.uv_layers.new(name='UVMap')
        for loop in me.loops:
            uvlay.data[loop.index].uv=uv[loop.vertex_index] if uv else (me.vertices[loop.vertex_index].co.x*8+.5,me.vertices[loop.vertex_index].co.z*8+.5)
        if col==asset:
            obs.append(obj);weights[obj.name]=skinweights or bone
        # Recalculate connected orientable surfaces; important for lower wing surface.
        bpy.context.view_layer.objects.active=obj;obj.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT');obj.select_set(False)
        return obj
    def tube(name,path,radii,material=cut,bone='root',sides=8,col=asset):
        vv=[];uv=[];path=[Vector(p) for p in path]
        for i,p in enumerate(path):
            tangent=(path[min(i+1,len(path)-1)]-path[max(0,i-1)]).normalized()
            ref=Vector((0,0,1)) if abs(tangent.z)<.85 else Vector((0,1,0))
            n=tangent.cross(ref).normalized();b=tangent.cross(n).normalized();r=radii[i] if isinstance(radii,list) else radii
            for j in range(sides+1):
                a=TAU*j/sides;vv.append(p+r*(math.cos(a)*n+math.sin(a)*b));uv.append((j/sides,i/(len(path)-1)))
        ff=[]
        for i in range(len(path)-1):
            for j in range(sides):k=i*(sides+1)+j;ff.append((k,k+1,k+sides+2,k+sides+1))
        ff.extend([tuple(reversed(range(sides+1))),tuple((len(path)-1)*(sides+1)+j for j in range(sides+1))])
        return mesh(name,vv,ff,material,uv,bone,col=col)
    def sphere(name,center,scale,material=cut,bone='root',segments=24,rings=16):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=rings,location=center)
        ob=bpy.context.object;ob.name=name;ob.scale=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        ob.data.materials.append(material);to_collection(ob,asset)
        for p in ob.data.polygons:p.use_smooth=True
        obs.append(ob);weights[ob.name]=bone;ob.select_set(False);return ob
    def bone(name,head,tail,parent='root'):
        bone_specs.append((name,head,tail,parent));return name
    def setae(name,points,material=hairmat,bone_name='root'):
        vv=[];ff=[]
        for p,n,length,radius in points:
            p=Vector(p);n=Vector(n).normalized();cross=n.cross(Vector((0,0,1)))
            if cross.length<.01:cross=n.cross(Vector((0,1,0)))
            a=cross.normalized();b=n.cross(a);base=len(vv)
            for j in range(3):vv.append(p+radius*(math.cos(TAU*j/3)*a+math.sin(TAU*j/3)*b))
            vv.append(p+n*length+Vector((0,0,length*.16)))
            for j in range(3):ff.append((base+j,base+(j+1)%3,base+3))
        return mesh(name,vv,ff,material,bone=bone_name)
    rr=random.Random(945)
    if species=='butterfly':
        bone('root',(0,0,.042),(0,.017,.042),None)
        wingbones=[]
        for side in [-1,1]:
            for isfore,outline in [(True,FORE),(False,HIND)]:
                label=('L' if side<0 else 'R')+('_forewing' if isfore else '_hindwing')
                bn=bone(label,(side*.002,0,.047),(side*.060,0,.047));wingbones.append(bn)
                poly=outline[:-1];center=np.mean(poly,axis=0);ns=len(poly);nr=15;vv=[];uv=[]
                for face in [1,-1]:
                    for j in range(nr+1):
                        r=(j+.002)/(nr+.002)
                        for u0,v0 in poly:
                            u,v=center+(np.array((u0,v0))-center)*r
                            x=(u-.5)*.38*(-side);y=(.495-v)*.38
                            # Arched thin membranes; no thick cookie rim.
                            z=.047+abs(x)*.45+.0036*math.sin((v-.13)*7)*math.sin(abs(x)*19)+face*.00012
                            vv.append((x,y,z));uv.append((u if side<0 else 1-u,1-v))
                ff=[];stride=(nr+1)*ns
                for off in [0,stride]:
                    for j in range(nr):
                        for k in range(ns):
                            ids=(off+j*ns+k,off+j*ns+(k+1)%ns,off+(j+1)*ns+(k+1)%ns,off+(j+1)*ns+k)
                            ff.append(ids if off==0 else tuple(reversed(ids)))
                    ff.append(tuple(off+k for k in range(ns)))
                for k in range(ns):ff.append((nr*ns+k,nr*ns+(k+1)%ns,stride+nr*ns+(k+1)%ns,stride+nr*ns+k))
                mesh(label+'_closed_membrane',vv,ff,painted,uv,bn)
                # Fine modeled main vein ridge complements texture branching.
                for vi,curve in enumerate(VEINS[:5] if isfore else VEINS[5:]):
                    path=[]
                    for u,v in curve:
                        x=(u-.5)*.38*(-side);y=(.495-v)*.38
                        z=.047+abs(x)*.45+.0036*math.sin((v-.13)*7)*math.sin(abs(x)*19)+.00019
                        path.append((x,y,z))
                    tube(label+f'_vein_{vi}',path,[.00023*(1-.73*j/(len(path)-1)) for j in range(len(path))],veinmat,bn,5)
        sphere('Setose thorax',(0,.001,.047),(.007,.014,.009))
        sphere('Head',(0,.019,.051),(.0072,.0065,.007))
        # One tapered abdomen with soft overlapping cuticular annuli.
        vv=[];uv=[];N=112;K=40
        for i in range(N+1):
            t=i/N;r=(.0059*(1-t)**.55+.0002)*(.965-.035*math.cos(TAU*t*8))
            for j in range(K+1):
                a=TAU*j/K;vv.append((r*math.cos(a),-.007-t*.047,.045-t*.024+r*.85*math.sin(a)))
                uv.append((j/K,t))
        ff=[(i*(K+1)+j,i*(K+1)+j+1,(i+1)*(K+1)+j+1,(i+1)*(K+1)+j) for i in range(N) for j in range(K)]
        mesh('Tapered eight-annulus abdomen',vv,ff,cut,uv)
        hairs=[]
        for i in range(1700):
            t=rr.uniform(-1,1);a=rr.uniform(0,TAU);p=(.007*math.sqrt(1-t*t)*math.cos(a),.001+.014*t,.047+.009*math.sqrt(1-t*t)*math.sin(a))
            hairs.append((p,(math.cos(a),t*.4,math.sin(a)),rr.uniform(.0008,.0024),rr.uniform(.000035,.000065)))
        setae('1700 thoracic setae',hairs)
        for side in [-1,1]:
            sphere(f'Compound eye {side}',(side*.006,.022,.053),(.003,.0035,.0037),eye,segments=28,rings=18)
            start=(side*.003,.022,.057);end=(side*.019,.064,.076)
            bn=bone(f'Antenna_{side}',start,end)
            p=bez(start,[((side*.007,.037,.066),(side*.014,.055,.073),end)],32)
            tube(f'Fine clubbed antenna {side}',p,[.00044*(1-.45*i/(len(p)-1)) for i in range(len(p))],cut,bn,8)
            sphere(f'Antenna club {side}',end,(.00085,.0016,.0008),cut,bn,16,12)
            for i,y in enumerate([.012,.002,-.009]):
                root=(side*.004,y,.044)
                knee=(side*(.015 if i<2 else .018),y+(.006 if i==0 else -.003),.034)
                ankle=(side*(.020 if i==0 else .025),y+(.019 if i==0 else -.015),.008)
                tip=(side*(.026 if i==0 else .034),ankle[1]+.006,.001)
                fem=bone(f'Leg_{side}_{i}_femur',root,knee);tib=bone(f'Leg_{side}_{i}_tibia',knee,ankle,fem);tar=bone(f'Leg_{side}_{i}_tarsus',ankle,tip,tib)
                tube(f'Leg {side}/{i} femur',[root,knee],[.00125,.00095],cut,fem,10)
                sphere(f'Leg {side}/{i} knee',knee,(.00106,)*3,cut,tib,12,8)
                tube(f'Leg {side}/{i} tibia',[knee,ankle],[.00074,.00038],cut,tib,8)
                path=[ankle,((ankle[0]+tip[0])/2,(ankle[1]+tip[1])/2,.0025),tip]
                tube(f'Leg {side}/{i} segmented tarsus',path,[.00036,.00026,.00018],cut,tar,7)
                for sign in [-1,1]:tube(f'Leg {side}/{i} claw {sign}',[tip,(tip[0]+sign*.0013,tip[1]+.0018,.0003)],[.00016,.000055],cut,tar,5)
        target=(0,.014,.067);campos=(.045,-.30,.37);camscale=.405
    else:
        bone('root',(-.16,0,.041),(-.14,0,.041),None)
        def center(t):return Vector((-.163+.322*t,.006*math.sin(t*TAU*.65),.034+.008*math.sin(t*math.pi)+.032*math.exp(-((t-.985)/.16)**2)))
        def radius(t,a):
            # A single continuous surface, broad shallow rolling folds, a soft tapered tail.
            taper=math.sqrt(max(.00001,1-((t-.060)/.060)**2)) if t<.060 else 1
            if t>.91:taper*=math.sqrt(max(.005,1-((t-.91)/.095)**2))
            base=.0355*(.92+.08*math.sin(t*math.pi))
            phase=(t-.060)/.84*8
            folds=.930-.095*math.cos(TAU*phase)
            folds-=.025*(.5+.5*math.cos(TAU*phase))**12
            if t<.09:
                blend=max(0,min(1,(t-.025)/.065));blend=blend*blend*(3-2*blend);folds=1+(folds-1)*blend
            minor=.008*math.sin(t*TAU*55+a*2)+.005*math.sin(t*TAU*94+a*6)
            if t>.88:folds=1;minor*=.45
            return base*taper*(folds+minor)
        for i in range(12):
            t=i/11;p=center(t);bone(f'Softbody_{i:02}',p,p+Vector((.02,0,0)))
        def softweights(t):
            q=max(0,min(11,t*11));i=min(10,int(q));f=q-i
            # smooth weights in longitudinal direction avoid hard bands at bone transitions
            f=f*f*(3-2*f)
            return [(f'Softbody_{i:02}',1-f),(f'Softbody_{i+1:02}',f)]
        N=432;K=96;vv=[];uv=[];sw=[]
        for i in range(N+1):
            t=.001+.998*i/N;c=center(t)
            tangent=(center(min(1,t+.001))-center(max(0,t-.001))).normalized()
            cross=Vector((0,1,0));up=tangent.cross(cross).normalized()
            for j in range(K+1):
                a=TAU*j/K;r=radius(t,a)
                p=c+r*(math.cos(a)*cross+math.sin(a)*up)
                vv.append(p);uv.append((t,1-j/K));sw.append(softweights(t))
        ff=[(i*(K+1)+j,i*(K+1)+j+1,(i+1)*(K+1)+j+1,(i+1)*(K+1)+j) for i in range(N) for j in range(K)]
        ff.extend([tuple(reversed(range(K+1))),tuple(N*(K+1)+j for j in range(K+1))])
        mesh('ONE continuous wrinkled soft cuticle',vv,ff,painted,uv,skinweights=sw)
        for i,t in enumerate([.13,.23,.34,.45,.56,.67,.78,.86]):
            c=center(t);bn=f'Softbody_{round(t*11):02}'
            for side in [-1,1]:
                p=c+Vector((0,side*.018,-.026));q=Vector((c.x+.002,c.y+side*.022,.006));e=Vector((c.x+.006,c.y+side*.024,.0008))
                # Soft prolegs blend under the cuticle; tiny crochet hooks meet the leaf.
                middle=(p+q)*.5
                if i>=6:
                    knee=Vector((c.x+.009,c.y+side*.026,max(.009,c.z-.030)))
                    ankle=Vector((c.x+.015,c.y+side*.025,.002))
                    e=Vector((c.x+.021,c.y+side*.026,.0008))
                    tube(f'Articulated anterior leg {i}/{side}',[p,knee,ankle,e],[.0030,.0022,.0012,.0008],cut,bn,12)
                    sphere(f'Anterior leg knee {i}/{side}',knee,(.0023,)*3,cut,bn,20,12)
                    sphere(f'Anterior soft pad {i}/{side}',e+Vector((0,0,.0007)),(.0018,.0019,.0013),cut,bn,20,12)
                else:
                    bulb=Vector((c.x+.001,c.y+side*.021,.0078))
                    pad=Vector((c.x+.004,c.y+side*.024,.0024))
                    sphere(f'Fleshy rounded proleg {i}/{side}',bulb,(.0048,.0045,.0065),cut,bn,28,20)
                    sphere(f'Soft crochet pad {i}/{side}',pad,(.0048,.0052,.0025),cut,bn,28,16)
                    e=Vector((c.x+.007,c.y+side*.025,.001))
                for claw in [-1,0,1]:
                    end=e+Vector((.0024,claw*.0013,-.0007));tube(f'Crochet {i}/{side}/{claw}',[e,end,end+Vector((-.0003,0,.0008))],[.0006,.00036,.00016],cut,bn,6)
        for side in [-1,1]:
            t=.950;c=center(t);bn='Softbody_10'
            eyeplace=c+Vector((.001,side*(radius(t,0)*.98),.005))
            sphere(f'Simple dark eye {side}',eyeplace,(.0031,.0014,.0036),eye,bn,24,16)
            start=center(.968)+Vector((0,side*.012,.028));end=start+Vector((.007,side*.004,.027))
            ant=bone(f'Antenna_{side}',start,end,'Softbody_11')
            path=bez(tuple(start),[(tuple(start+Vector((.003,0,.010))),tuple(end-Vector((.001,0,.007))),tuple(end))],28)
            tube(f'Antenna {side}',path,[.00053*(1-.4*j/(len(path)-1)) for j in range(len(path))],cream,ant,8)
            sphere(f'Antenna tip {side}',end,(.0013,.0015,.0017),cream,ant,16,12)
        # Short sparse setae and soft micro-wrinkles, not a fuzzy toy coat.
        hairs=[]
        for i in range(850):
            t=rr.uniform(.025,.975);a=rr.uniform(0,TAU);c=center(t);r=radius(t,a);n=Vector((0,math.cos(a),math.sin(a)))
            hairs.append((c+n*r,n,rr.uniform(.00025,.00065),rr.uniform(.000015,.000027)))
        ob=setae('850 sparse skin setae',hairs,cream)
        weights[ob.name]=[softweights(max(0,min(1,(v.co.x+.163)/.322))) for v in ob.data.vertices]
        target=(0,0,.042);campos=(.16,-.48,.22);camscale=.401
    # Real editable armature and weighted skin. Every mesh has a skinned transform.
    armdata=bpy.data.armatures.new(species+'_anatomical_rig');rig=bpy.data.objects.new(species+'_RIG',armdata);asset.objects.link(rig)
    bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
    for name,head,tail,parent in bone_specs:
        b=armdata.edit_bones.new(name);b.head=head;b.tail=tail
        if parent:b.parent=armdata.edit_bones[parent]
    bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False);rig.show_in_front=True
    for ob in obs:
        spec=weights[ob.name]
        if isinstance(spec,str):
            vg=ob.vertex_groups.new(name=spec);vg.add(list(range(len(ob.data.vertices))),1,'REPLACE')
        else:
            groups={}
            for i,pairs in enumerate(spec):
                for name,value in pairs:
                    if value<.00001:continue
                    if name not in groups:groups[name]=ob.vertex_groups.new(name=name)
                    groups[name].add([i],value,'REPLACE')
        mod=ob.modifiers.new('Portable skinning','ARMATURE');mod.object=rig;ob.parent=rig
    acts=[]
    def reset_pose():
        for p in rig.pose.bones:p.location=(0,0,0);p.rotation_mode='XYZ';p.rotation_euler=(0,0,0);p.scale=(1,1,1)
    for name,duration in ([('idle_perch',96),('fly',24),('perch_touch',64),('antenna_groom',72),('startle',48)] if species=='butterfly' else [('crawl',72),('explore',96),('recoil',48),('idle_breathe',96),('touch_curiosity',72)]):
        reset_pose();act=bpy.data.actions.new(species+'_'+name);rig.animation_data_create();rig.animation_data.action=act
        for frame in range(1,duration+1,2):
            reset_pose();phase=(frame-1)/(duration-1)*TAU
            if species=='butterfly':
                for bn in wingbones:
                    isfore='fore' in bn
                    if name=='idle_perch':angle=.06*math.sin(phase)+.015*math.sin(phase*3)
                    elif name=='fly':angle=.125+.675*math.sin(phase*2)
                    elif name=='startle':angle=.65*math.sin(phase/2)**8
                    elif name=='antenna_groom':angle=.025*math.sin(phase)
                    else:angle=.30*math.sin(phase/2)**4
                    rig.pose.bones[bn].rotation_euler.x=angle*(1 if isfore else .87)
                for p in rig.pose.bones:
                    if p.name.startswith('Antenna'):p.rotation_euler.y=.07*math.sin(phase+(1 if p.name.endswith('1') else 0))
                    if p.name.startswith('Antenna') and name=='antenna_groom':p.rotation_euler.x=.35*math.sin(phase/2)**2
                    if p.name.startswith('Leg') and 'femur' in p.name:
                        p.rotation_euler.x=(.28 if name=='fly' else 0)+(.23*math.sin(phase/2)**4 if name=='perch_touch' and '_0_' in p.name else 0)
                        if name=='antenna_groom' and '_0_' in p.name:p.rotation_euler.x=.62*math.sin(phase/2)**4
                rig.pose.bones['root'].location.z=.001*math.sin(phase) if name=='fly' else 0
            else:
                for i in range(12):
                    p=rig.pose.bones[f'Softbody_{i:02}'];t=i/11
                    if name=='crawl':
                        p.location.x=.0012*math.cos(phase-t*TAU*1.3);p.location.z=.0021*math.sin(phase-t*TAU*1.3)
                    elif name=='explore':
                        p.location.z=.010*max(0,(t-.65)/.35)*math.sin(phase/2)**2
                        p.rotation_euler.x=.11*max(0,t-.6)*math.sin(phase)
                    elif name=='recoil':
                        pulse=math.sin(phase/2)**6;p.location.y=-.017*t*pulse;p.location.z=.003*t*pulse
                    elif name=='idle_breathe':
                        p.scale.x=1+.012*math.sin(phase-t*.4);p.scale.z=1+.012*math.sin(phase-t*.4)
                    else:
                        pulse=math.sin(phase/2)**2;p.location.z=.006*max(0,(t-.5)/.5)*pulse;p.location.x=.012*t*t*math.sin(phase)
                for p in rig.pose.bones:
                    if p.name.startswith('Antenna'):p.rotation_euler.x=.16*math.sin(phase)
            for p in rig.pose.bones:
                p.keyframe_insert('location',frame=frame);p.keyframe_insert('rotation_euler',frame=frame);p.keyframe_insert('scale',frame=frame)
        # Explicit end keyframe makes each action start/end deterministic.
        scene.frame_set(1)
        for p in rig.pose.bones:p.keyframe_insert('location',frame=duration);p.keyframe_insert('rotation_euler',frame=duration);p.keyframe_insert('scale',frame=duration)
        track=rig.animation_data.nla_tracks.new();track.name=act.name;track.strips.new(act.name,1,act);track.mute=True
        acts.append(act)
    rig.animation_data.action=None;reset_pose();scene.frame_set(1)
    # Export contains only original insect objects/rig, with embedded images.
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
    for ob in obs:ob.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(out/f'{species}.glb'),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_skins=True,export_extras=True,export_yup=True,export_apply=False)
    def area(name,location,energy,size,color):
        data=bpy.data.lights.new(name,'AREA');data.energy=energy;data.shape='DISK';data.size=size;data.color=color
        ob=bpy.data.objects.new(name,data);stage.objects.link(ob);ob.location=location;ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler();return ob
    area('Soft window key',(-.25,-.24,.40),1.7,.25,(1,.87,.69))
    area('Blue sky fill',(.23,.12,.32),.9,.30,(.79,.88,1))
    area('Warm edge light',(.03,.30,.24),2.0,.18,(1,.92,.68))
    floormat=mat('Neutral warm grey',(.68,.66,.60,1),.92)
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,0));floor=bpy.context.object;floor.name='Review floor';to_collection(floor,stage);floor.data.materials.append(floormat)
    data=bpy.data.cameras.new('Review camera');camera=bpy.data.objects.new('Review camera',data);stage.objects.link(camera);scene.camera=camera;data.type='ORTHO'
    def set_camera(pos=campos,tar=target,scale=camscale):
        camera.location=pos;camera.rotation_euler=(Vector(tar)-camera.location).to_track_quat('-Z','Y').to_euler();data.ortho_scale=scale
    def render(name):scene.render.filepath=str(out/name);bpy.ops.render.render(write_still=True)
    set_camera();scene['review_note']='Actual mesh + portable image materials. Staging leaf and lights excluded from GLB. Approval pending.'
    bpy.ops.wm.save_as_mainfile(filepath=str(out/f'{species}.blend'))
    render('01-neutral-three-quarter.png')
    if args.first_only:
        print('First-frame anatomy review only; GLB and editable source saved, full QA pending.')
        return
    if species=='butterfly':set_camera((0,-.005,.6),(0,0,.045),.394)
    else:set_camera((.03,-.6,.068),(0,0,.048),.39)
    render('02-shape-check.png');set_camera()
    # Sculpted real staging leaf, central/secondary raised veins, tiny beads of dew.
    leafmat=mat('Review leaf image PBR',texture='review-leaf',subs=.025)
    leafobs=[];verts=[];luv=[];faces=[];Nx=90;Ny=36
    def leafpoint(u,v):
        x=(u-.5)*.62;w=.17*max(.008,math.sin(math.pi*u))**.73
        y=v*w;z=.0001+.010*abs(v)**1.7+.004*math.sin(u*math.pi*3)*v
        return (x,y,z)
    for i in range(Nx+1):
        for j in range(Ny+1):
            u=i/Nx;v=-1+2*j/Ny;verts.append(leafpoint(u,v));luv.append(((v+1)/2,u))
    for i in range(Nx):
        for j in range(Ny):k=i*(Ny+1)+j;faces.append((k,k+1,k+Ny+2,k+Ny+1))
    leafobs.append(mesh('Real sculpted review leaf',verts,faces,leafmat,luv,col=stage))
    veinleaf=mat('Leaf veins',(.13,.23,.06,1),.67)
    leafobs.append(tube('Leaf midrib',[leafpoint(i/100,0) for i in range(101)],[.0008*(.8+.2*math.sin(i/100*math.pi)) for i in range(101)],veinleaf,col=stage))
    for i in range(2,10):
        u=i/11
        for side in [-1,1]:
            p=[]
            for j in range(20):
                q=j/19;point=list(leafpoint(min(.98,u+.105*q),side*q*.98));point[2]+=.00018;p.append(point)
            leafobs.append(tube(f'Leaf raised vein {i}/{side}',p,[.00047*(1-.80*j/19) for j in range(20)],veinleaf,col=stage,sides=5))
    dew=mat('Water droplets',(.88,.96,.90,1),.05);pbs=dew.node_tree.nodes['Principled BSDF'];pbs.inputs['Transmission Weight'].default_value=1;pbs.inputs['IOR'].default_value=1.333
    for i in range(53):
        u=rr.uniform(.10,.90);v=rr.choice([-1,1])*rr.uniform(.38,.92);p=leafpoint(u,v);r=rr.uniform(.0006,.0024)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=14,ring_count=10,location=(p[0],p[1],p[2]+r*.46));ob=bpy.context.object;ob.name='Review dew';ob.scale=(r,r,r*.70);ob.data.materials.append(dew);to_collection(ob,stage);leafobs.append(ob)
        for f in ob.data.polygons:f.use_smooth=True
    # Actual curved foliage geometry over a softly shaded procedural backdrop.
    # This review environment is excluded from the exported insect asset.
    leafobs.extend(distant_foliage(stage,leafobs[0]))
    floor.hide_render=True;data.type='PERSP';data.lens=48
    if species=='butterfly':set_camera((.09,-.43,.24),(0,0,.048),camscale)
    else:set_camera((.14,-.53,.20),(0,0,.05),camscale)
    data.dof.use_dof=True;data.dof.focus_distance=(camera.location-Vector(target)).length;data.dof.aperture_fstop=6.3
    render('03-natural-leaf-closeup.png')
    for ob in leafobs:ob.hide_render=True
    floor.hide_render=False;data.type='ORTHO';data.dof.use_dof=False;set_camera()
    bpy.ops.wm.save_as_mainfile(filepath=str(out/f'{species}.blend'))
    # Independent GLB round-trip: remove source asset collection and unused actions,
    # retaining only neutral QA camera/lighting. Render the imported materials and rig.
    source_stats={'species':species,'triangles':sum(sum(len(p.vertices)-2 for p in ob.data.polygons) for ob in obs),'vertices':sum(len(ob.data.vertices) for ob in obs),'mesh_objects':len(obs),'bones':len(armdata.bones),'actions':[a.name for a in acts],'glb_bytes':(out/f'{species}.glb').stat().st_size,'body_continuous':species=='caterpillar','images':[{'name':im.name,'width':im.size[0],'height':im.size[1]} for im in bpy.data.images if im.type=='IMAGE' and 'review-leaf' not in im.name]}
    for ob in list(asset.objects):bpy.data.objects.remove(ob,do_unlink=True)
    for a in list(bpy.data.actions):bpy.data.actions.remove(a)
    bpy.ops.import_scene.gltf(filepath=str(out/f'{species}.glb'),disable_bone_shape=True)
    imported=[ob for ob in scene.objects if ob.type=='ARMATURE'];irig=imported[0]
    for tr in irig.animation_data.nla_tracks:tr.mute=True
    irig.animation_data.action=None
    for p in irig.pose.bones:p.matrix_basis=Matrix.Identity(4)
    scene.frame_set(1);bpy.context.view_layer.update();render('04-glb-roundtrip.png')
    imported_actions=list(bpy.data.actions)
    source_stats['roundtrip_actions']=[a.name for a in imported_actions]
    source_stats['roundtrip_bones']=len(irig.data.bones)
    scene.render.resolution_x=540;scene.render.resolution_y=450;scene.cycles.samples=12
    samples=[]
    for action in imported_actions:
        irig.animation_data.action=action
        start,end=action.frame_range
        for j,f in enumerate([start,start+(end-start)*.28,start+(end-start)*.56]):
            scene.frame_set(round(f));fn=f'animation-{action.name}-{j}.png';render(fn);samples.append({'action':action.name,'frame':round(f),'image':fn})
    source_stats['animation_samples']=samples
    (out/'statistics.json').write_text(json.dumps(source_stats,indent=2),encoding='utf8')
    print(json.dumps(source_stats,indent=2))

def distant_foliage(stage,leaf):
    import bpy
    rr=random.Random(392);objects=[]
    for i in range(24):
        ob=leaf.copy();ob.data=leaf.data;ob.name='Review distant curved leaf';stage.objects.link(ob)
        ob.location=(rr.uniform(-.85,.85),rr.uniform(.55,1.4),rr.uniform(-.1,.64))
        s=rr.uniform(.65,1.25);ob.scale=(s,s,s);ob.rotation_euler=(rr.uniform(.5,1.5),rr.uniform(-.7,.7),rr.uniform(-math.pi,math.pi));ob.hide_render=False
        objects.append(ob)
    bpy.ops.mesh.primitive_plane_add(size=6,location=(0,1.7,.5),rotation=(math.pi/2,0,0));ob=bpy.context.object;ob.name='Review distant soft foliage light'
    for c in list(ob.users_collection):c.objects.unlink(ob)
    stage.objects.link(ob);m=bpy.data.materials.new('Review softly shaded garden distance');m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;n.clear()
    tex=n.new('ShaderNodeTexNoise');tex.inputs['Scale'].default_value=4.5;tex.inputs['Detail'].default_value=1.2;tex.inputs['Roughness'].default_value=.45
    ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].position=.22;ramp.color_ramp.elements[0].color=(.06,.11,.034,1);ramp.color_ramp.elements[1].position=.76;ramp.color_ramp.elements[1].color=(.40,.45,.21,1)
    em=n.new('ShaderNodeEmission');em.inputs['Strength'].default_value=.72;out=n.new('ShaderNodeOutputMaterial');l.new(tex.outputs['Fac'],ramp.inputs['Fac']);l.new(ramp.outputs['Color'],em.inputs['Color']);l.new(em.outputs[0],out.inputs['Surface']);ob.data.materials.append(m);objects.append(ob)
    return objects

def review_only(args):
    import bpy
    from mathutils import Vector
    folder=args.output_dir;species=args.species;bpy.ops.wm.open_mainfile(filepath=str(folder/f'{species}.blend'))
    scene=bpy.context.scene;stage=bpy.data.collections['REVIEW_STAGING_not_exported'];leaf=bpy.data.objects['Real sculpted review leaf']
    for ob in list(stage.objects):
        if ob.name.startswith('Gentle warm body fill'):bpy.data.objects.remove(ob,do_unlink=True)
    if args.gpu:
        prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
        for device in prefs.devices:device.use=device.type=='OPTIX'
        scene.cycles.device='GPU'
    scene.render.use_persistent_data=True;scene.cycles.samples=64
    for material in bpy.data.materials:
        if material.name.startswith('Continuous wax pigment'):
            material.node_tree.nodes['Principled BSDF'].inputs['Subsurface Weight'].default_value=0
    camera=scene.camera;data=camera.data;data.type='ORTHO';data.dof.use_dof=False
    target=(0,.014,.067) if species=='butterfly' else (0,0,.042)
    camera.location=(.045,-.30,.37) if species=='butterfly' else (.16,-.48,.22);camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();data.ortho_scale=.405 if species=='butterfly' else .401
    for ob in stage.objects:
        if ob.type=='MESH':ob.hide_render=ob.name!='Review floor'
    scene.render.filepath=str(folder/'01-neutral-three-quarter.png');bpy.ops.render.render(write_still=True)
    if species=='butterfly':camera.location=(0,-.005,.6);target=(0,0,.045);data.ortho_scale=.394
    else:camera.location=(.03,-.6,.068);target=(0,0,.048);data.ortho_scale=.39
    camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(folder/'02-shape-check.png');bpy.ops.render.render(write_still=True)
    for ob in list(stage.objects):
        if ob.name.startswith('Review distant'):bpy.data.objects.remove(ob,do_unlink=True)
    distant_foliage(stage,leaf)
    if species=='butterfly':
        light=bpy.data.lights.new('Gentle warm body fill','AREA');light.energy=.055;light.size=.07;light.color=(1,.76,.48)
        ob=bpy.data.objects.new('Gentle warm body fill',light);stage.objects.link(ob);ob.location=(.035,-.08,.09);ob.rotation_euler=(Vector((0,0,.04))-ob.location).to_track_quat('-Z','Y').to_euler()
    for ob in stage.objects:
        if ob.type=='MESH':ob.hide_render=ob.name=='Review floor'
    camera=scene.camera;data=camera.data;data.type='PERSP';data.lens=48
    target=(0,0,.048) if species=='butterfly' else (0,0,.05)
    camera.location=(.09,-.43,.24) if species=='butterfly' else (.14,-.53,.20)
    camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();data.dof.use_dof=True;data.dof.focus_distance=(camera.location-Vector(target)).length;data.dof.aperture_fstop=6.3
    scene.cycles.samples=64;scene.render.resolution_x=1080;scene.render.resolution_y=900
    if args.gpu:
        prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
        for device in prefs.devices:device.use=device.type=='OPTIX'
        scene.cycles.device='GPU'
    scene.render.filepath=str(folder/'03-natural-leaf-closeup.png');bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(folder/f'{species}.blend'))

def contact(args):
    from PIL import Image,ImageDraw,ImageFont
    folder=args.output_dir;stats=json.loads((folder/'statistics.json').read_text())
    sheet=Image.new('RGB',(1620,len(stats['roundtrip_actions'])*500),(245,240,230));d=ImageDraw.Draw(sheet)
    try:f=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',23)
    except:f=ImageFont.load_default()
    for i,s in enumerate(stats['animation_samples']):
        im=Image.open(folder/s['image']).convert('RGB');x=(i%3)*540;y=(i//3)*500;sheet.paste(im,(x,y));d.text((x+16,y+460),f"{s['action']} · frame {s['frame']}",font=f,fill=(61,44,33))
    sheet.save(folder/'05-exported-animation-contact-sheet.png')

def fresh_verify(args):
    """Run in a new factory-startup process, with no source materials or images."""
    import bpy
    from mathutils import Vector, Matrix
    folder=args.output_dir;species=args.species
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    for materials in [bpy.data.materials,bpy.data.images,bpy.data.actions]:
        for item in list(materials):
            if getattr(item,'type',None)=='RENDER_RESULT':continue
            materials.remove(item)
    bpy.ops.import_scene.gltf(filepath=str(folder/f'{species}.glb'),disable_bone_shape=True)
    meshes=[ob for ob in bpy.context.scene.objects if ob.type=='MESH'];rigs=[ob for ob in bpy.context.scene.objects if ob.type=='ARMATURE']
    assert len(rigs)==1 and len(bpy.data.actions)==5,(len(rigs),len(bpy.data.actions))
    rig=rigs[0];rig.animation_data.action=None
    for tr in rig.animation_data.nla_tracks:tr.mute=True
    # Importer automatically activates alphabetically first animation; muting it
    # leaves its first-frame bone values in place. Reset basis for a rest-pose QA.
    for p in rig.pose.bones:p.matrix_basis=Matrix.Identity(4)
    bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
    assert all(len(ob.data.uv_layers)>0 for ob in meshes)
    assert all(len(ob.vertex_groups)>0 for ob in meshes)
    report={'fresh_process':True,'imported_mesh_objects':len(meshes),'bones':len(rig.data.bones),'actions':[a.name for a in bpy.data.actions],
      'images':[{'name':im.name,'size':list(im.size),'packed':bool(im.packed_file)} for im in bpy.data.images if im.type=='IMAGE'],
      'materials':len(bpy.data.materials),'triangles':sum(sum(len(p.vertices)-2 for p in ob.data.polygons) for ob in meshes)}
    corners=[ob.matrix_world@Vector(corner) for ob in meshes for corner in ob.bound_box]
    report['dimensions_m']=[max(c[i] for c in corners)-min(c[i] for c in corners) for i in range(3)]
    assert all(im['size'][0]>0 for im in report['images'])
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24;scene.cycles.use_denoising=True;scene.cycles.device='CPU'
    if args.gpu:
        prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
        for device in prefs.devices:device.use=device.type=='OPTIX'
        scene.cycles.device='GPU';scene.cycles.samples=64
    scene.render.threads_mode='FIXED';scene.render.threads=4;scene.render.resolution_x=1080;scene.render.resolution_y=900;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast'
    scene.world.use_nodes=True;world=scene.world.node_tree.nodes['Background'];world.inputs['Color'].default_value=(.63,.68,.63,1);world.inputs['Strength'].default_value=.30
    target=(0,.014,.067) if species=='butterfly' else (0,0,.042)
    for name,location,energy,size,color in [('key',(-.25,-.24,.40),1.7,.25,(1,.87,.69)),('fill',(.23,.12,.32),.9,.30,(.79,.88,1)),('edge',(.03,.30,.24),2,.18,(1,.92,.68))]:
        data=bpy.data.lights.new(name,'AREA');data.energy=energy;data.shape='DISK';data.size=size;data.color=color
        ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob);ob.location=location;ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,0));floor=bpy.context.object
    m=bpy.data.materials.new('Verification floor');m.use_nodes=True;m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(.68,.66,.60,1);m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.92;floor.data.materials.append(m)
    data=bpy.data.cameras.new('Fresh process camera');camera=bpy.data.objects.new('Fresh process camera',data);scene.collection.objects.link(camera);scene.camera=camera;data.type='ORTHO'
    camera.location=(.045,-.30,.37) if species=='butterfly' else (.16,-.48,.22);camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();data.ortho_scale=.405 if species=='butterfly' else .401
    scene.render.filepath=str(folder/'06-fresh-process-roundtrip.png');scene.frame_set(1);bpy.ops.render.render(write_still=True)
    (folder/'fresh-process-verification.json').write_text(json.dumps(report,indent=2),encoding='utf8');print(json.dumps(report,indent=2))

if __name__=='__main__':
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
    p=argparse.ArgumentParser();p.add_argument('--textures',action='store_true');p.add_argument('--contact',action='store_true');p.add_argument('--fresh-verify',action='store_true');p.add_argument('--review-only',action='store_true');p.add_argument('--first-only',action='store_true');p.add_argument('--gpu',action='store_true');p.add_argument('--species',choices=['butterfly','caterpillar']);p.add_argument('--output-dir',type=Path,default=OUT)
    args=p.parse_args(argv)
    if args.textures:maps()
    elif args.contact:contact(args)
    elif args.fresh_verify:fresh_verify(args)
    elif args.review_only:review_only(args)
    else:build(args)
