"""Build the worker ant and adult grasshopper with one skin and one paint mesh each.

blender -b -t 3 -P build_ground.py -- --species ant|grasshopper
Sources and outputs live in the BugWorld repository alongside this script.
"""
from pathlib import Path
import argparse
import math
import random
import sys
import bpy
import bmesh
import numpy as np
from mathutils import Vector, Quaternion
sys.path.insert(0,str(Path(__file__).resolve().parent))
from profiles import ANT, GRASS, LEGS, antennae, curve, span, page, GASTER_SEAMS

p=argparse.ArgumentParser()
p.add_argument('--species',choices=['ant','grasshopper'],required=True)
args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
K=args.species
ANT_MODE=K=='ant'
OUT=Path(__file__).resolve().parents[1]/K
RUNTIME=OUT.parents[2]/'app/src/main/assets/v3'
UNIT=.00050 if ANT_MODE else .00069
FLOOR=224 if ANT_MODE else 232
SPEC=ANT if ANT_MODE else GRASS
PAPER='Paper_'+K
ROOT='Thoracic carriage'
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.render.threads_mode='FIXED'; scene.render.threads=3
scene.render.fps=24
bpy.context.preferences.filepaths.save_version=0


def wp(p):
    x,l,y=p
    return Vector(((252-x)*UNIT,l*UNIT,(FLOOR-y)*UNIT))


def material(name, color, rough, metallic=0):
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    node=mat.node_tree.nodes.get('Principled BSDF')
    node.inputs['Base Color'].default_value=(*color,1)
    node.inputs['Roughness'].default_value=rough
    node.inputs['Metallic'].default_value=metallic
    mat.diffuse_color=(*color,1)
    return mat


mats={}
mats[PAPER]=material(PAPER,(1,1,1),.64)
pig=mats[PAPER].node_tree.nodes.new('ShaderNodeTexImage')
pig.image=bpy.data.images.load(str(OUT/'pigment.jpg'))
pig.image.name=K+' · sampled paper pigment'; pig.image.pack()
mats[PAPER].node_tree.links.new(pig.outputs['Color'],mats[PAPER].node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
for name,col,rough in [
    ('Cuticle',(.28,.084,.025) if ANT_MODE else (.33,.28,.053),.48),
    ('Joint',(.102,.039,.015) if ANT_MODE else (.15,.125,.034),.56),
    ('Compound eye',(.055,.025,.013) if ANT_MODE else (.115,.073,.020),.29),
    ('Amber rib',(.38,.145,.052) if ANT_MODE else (.40,.33,.077),.50),
    ('Hindwing membrane',(.54,.45,.18),.52),
]:
    mats[name]=material(name,col,rough)

# The template is the whole normalized page. Pixels directly behind locked or
# occluding structures sample the closest available pixel in that same body part.
mi=bpy.data.images.load(str(RUNTIME/f'templates/{K}-mask.png'))
mi.colorspace_settings.name='Non-Color'
raw=np.empty(4*1024*1024,dtype=np.float32);mi.pixels.foreach_get(raw)
mask=(raw.reshape(1024,1024,4)[::-1,:,0]*255).round().astype(np.uint8)
bpy.data.images.remove(mi)
lookups={}
def sheet_uv(p,region):
    x,y=page(K,p[0],p[2])
    if region not in lookups:
        keep=np.isin(mask,region)
        # A margin suppresses bilinear interpolation with a locked pixel.
        for _ in range(2):
            keep=keep & np.roll(keep,1,0) & np.roll(keep,-1,0) & np.roll(keep,1,1) & np.roll(keep,-1,1)
        yy,xx=np.where(keep)
        lookups[region]=keep,xx,yy
    keep,xx,yy=lookups[region]
    ix=max(0,min(1023,round(x)));iy=max(0,min(1023,round(y)))
    if not keep[iy,ix]:
        j=np.argmin((xx-ix)**2+(yy-iy)**2);x=float(xx[j]);y=float(yy[j])
    return ((x+.5)/1024,1-(y+.5)/1024)


# Accumulate meshes by material; the editable master retains named bone groups
# and the rig pivots. No per-article transform or draw call is needed at runtime.
batches={}
bones={}
def bone(name,p,parent=None):
    bones[name]=(wp(p),parent)
    return name


def part(points,faces,mat,group,region=None):
    b=batches.setdefault(mat,{'v':[],'f':[],'g':[],'uv':[],'regions':[]})
    at=len(b['v'])
    b['v'].extend(wp(v) for v in points)
    for f in faces:
        for j in range(1,len(f)-1):
            b['f'].append((at+f[0],at+f[j],at+f[j+1]))
            if mat==PAPER:b['regions'].append(region)
    b['g'].extend([group]*len(points))
    if mat==PAPER:b['uv'].extend(sheet_uv(v,region) for v in points)


def rings(rows,mat,group,region=None):
    n=len(rows[0]);faces=[]
    for i in range(len(rows)-1):
        for j in range(n):faces.append((i*n+j,i*n+(j+1)%n,(i+1)*n+(j+1)%n,(i+1)*n+j))
    faces += [tuple(range(n-1,-1,-1)),tuple((len(rows)-1)*n+i for i in range(n))]
    part([p for row in rows for p in row],faces,mat,group,region)


def tube(points,radii,mat,group,sides=7,region=None):
    vectors=list(map(Vector,points));rows=[]
    for i,(pt,r) in enumerate(zip(vectors,radii)):
        aim=(vectors[min(i+1,len(vectors)-1)]-vectors[max(i-1,0)]).normalized()
        axis=aim.cross(Vector((0,1,0)))
        if axis.length<.001:axis=aim.cross(Vector((1,0,0)))
        axis.normalize();other=aim.cross(axis).normalized()
        rows.append([tuple(pt+(axis*math.cos(j*math.tau/sides)+other*math.sin(j*math.tau/sides))*r) for j in range(sides)])
    rings(rows,mat,group,region)


def ovoid(center,rx,rl,ry,mat,group,angle=0):
    rows=[];a=math.radians(angle)
    bands,meridians=(11,16) if mat=='Compound eye' else (6,8)
    for i in range(bands+1):
        pitch=math.pi*(i+.02)/(bands+.04)
        radial=math.sin(pitch); along=-rx*math.cos(pitch)
        row=[]
        for j in range(meridians):
            t=j*math.tau/meridians; vertical=ry*radial*math.cos(t)
            row.append((center[0]+along*math.cos(a)-vertical*math.sin(a),
                        center[1]+rl*radial*math.sin(t),
                        center[2]+along*math.sin(a)+vertical*math.cos(a)))
        rows.append(row)
    rings(rows,mat,group)


def loft(key,width,group,regions,steps=29):
    pts=curve(SPEC[key]);xs=[p[0] for p in pts]
    lo,hi=min(xs),max(xs); rows=[]
    abounds=[span(pts,lo+(hi-lo)*(.00015+.99970*(.5-.5*math.cos(i*math.pi/steps)))) for i in range(steps+1)]
    fattest=max((b-a)/2 for a,b in abounds)
    for i,(a,b) in enumerate(abounds):
        x=lo+(hi-lo)*(.00015+.99970*(.5-.5*math.cos(i*math.pi/steps)))
        r=(b-a)*.5;mid=(a+b)*.5
        lateral=width*(r/fattest)**.79
        row=[]
        for j in range(20):
            theta=j*math.tau/20;sy=mid+r*math.cos(theta)
            # Gentle physical cuts around the gaster, corresponding to ink seams.
            groove=1
            if key=='gaster':
                for seam in GASTER_SEAMS:
                    q=curve(seam);sx=np.interp(sy,[v[1] for v in q],[v[0] for v in q])
                    groove-=.035*math.exp(-((x-sx)/2.4)**2)
            row.append((x,lateral*math.sin(theta)*groove,mid+(sy-mid)*groove))
        rows.append(row)
    rings(rows,PAPER,group,regions)


root=bone(ROOT,(240,0,92))
head=bone('Head articulation',(200 if ANT_MODE else 141,0,85 if ANT_MODE else 119),root)
abd=bone('Gaster flexion' if ANT_MODE else 'Abdominal flexion',(309 if ANT_MODE else 199,0,92 if ANT_MODE else 141),root)
if ANT_MODE:
    loft('thorax',24,root,(2,));loft('head',27,head,(1,));loft('petiole',13,abd,(3,))
    loft('gaster',39,abd,(4,5,6,7),43)
else:
    loft('head',29,head,(1,));loft('pronotum',36,root,(2,));loft('abdomen',36,abd,(3,),37)

def seg(a,b,r,tip,mat,group):
    a=Vector(a);b=Vector(b)
    tube([tuple(a.lerp(b,t)) for t in [0,.12,.40,.79,1]],
         [r*.72,r*.96,r,tip*1.12,tip],mat,group)


legs=[]
for side in (-1,1):
    tag='L' if side>0 else 'R'
    for number,rest in enumerate(LEGS[K]):
        points=[(x,side*l,y) for x,l,y in rest]
        # Each side's toe pad sits on the same tangent plane in the resting rig.
        for j in range(len(points)-2,len(points)):
            x,l,y=points[j];points[j]=(x,l,FLOOR-(2.5 if j==len(points)-2 else 1.25))
        jump_leg=(not ANT_MODE and number==2)
        if jump_leg:
            points=[(x,l+side*(20 if j>=2 else 7 if j==1 else 0),y) for j,(x,l,y) in enumerate(points)]
        fidx=2 if jump_leg else 1;tidx=fidx+1; aidx=4
        prefix=f'{tag}{number+1}'
        coxa=bone(prefix+' coxa',points[0],root)
        femur=bone(prefix+' femur',points[fidx],coxa)
        tibia=bone(prefix+' tibia',points[tidx],femur)
        toe=bone(prefix+' tarsus',points[aidx],tibia)
        legs.append((side,number,points,fidx,tidx,aidx,coxa,femur,tibia,toe))
        for j,(a,b) in enumerate(zip(points,points[1:])):
            name=coxa if j<fidx else femur if j<tidx else tibia if j<aidx else toe
            radius=([5.8,6.25,4.20,2.85,1.55][j] if not jump_leg else [5.8,6.5,8.2,3.9,3.0,2.1][j])
            if j==fidx and jump_leg:continue
            seg(a,b,radius,max(.65,radius*.57),'Cuticle',name)
            if j<len(points)-2:
                ovoid(b,radius*.76,radius*.70,radius*.76,'Joint',name)
        end=points[-1]
        for split in (-1,1):
            tube([end,(end[0]+(-2 if number<2 else 2),end[1]+split*1.1,FLOOR-.75),
                  (end[0]+(-4 if number<2 else 4),end[1]+split*1.8,FLOOR-.2)],[1.25,.8,.19],'Joint',toe,6)
        if jump_leg:
            # The large jumping femur forms a curved, flattened muscular solid.
            pts=curve(GRASS['thigh']);xs=[q[0] for q in pts];mi=min(xs);ma=max(xs)
            rows=[]
            for j in range(33):
                u=(.5-.5*math.cos(math.pi*j/32)); x=mi+(ma-mi)*(.0001+u*.9998)
                a,b=span(pts,x); center=(a+b)*.5; radius=(b-a)*.5
                lat=side*(61+16*u);width=8.8*(1-u*.52)*min(1,radius/8)**.7
                rows.append([(x,lat+math.sin(t*math.tau/14)*width,center+radius*math.cos(t*math.tau/14)) for t in range(14)])
            rings(rows,PAPER,femur,(5,))
            # Slender paired ranks of tibial spines point back towards the knee.
            a,b=map(Vector,[points[3],points[4]])
            for t in [.15,.25,.35,.46,.57,.69,.82,.91]:
                p=a.lerp(b,t)
                tube([p,p+Vector((2.8,side*1.1,-2.5)),p+Vector((6.3,side*2.8,-5.5))],
                     [1.25,.75,.13],'Amber rib',tibia,6)

for index,feel in enumerate(antennae(K)):
    s=1 if feel[0][1]>0 else -1
    prox=bone('Scape '+str(s),feel[0],head)
    distal=bone('Flagellum '+str(s),feel[1],prox)
    for j,(a,b) in enumerate(zip(feel,feel[1:])):
        grp=prox if j==0 else distal
        r=(2.15 if ANT_MODE else 1.75)*(1-.06*j)
        seg(a,b,r,r*.65,'Cuticle',grp)
        ovoid(b,r*.78,r*.78,r*.78,'Joint',grp)
for s in (-1,1):
    eye=(158,s*24,76) if ANT_MODE else (112,s*25.0,103)
    ovoid(eye,12 if ANT_MODE else 15.5,5 if ANT_MODE else 7,7 if ANT_MODE else 10,'Compound eye',head,-52 if ANT_MODE else -72)
    if ANT_MODE:
        tube([(132,s*12,114),(124,s*9,127),(126,s*5.0,133),(131,s*3,127)],
             [4.0,3.0,1.8,.28],'Joint',head,9)
    else:
        ovoid((108,s*12,145),9,6.8,8,'Cuticle',head,-38)
        tube([(119,s*16,147),(125,s*19,155),(121,s*19,159)],[2.2,2.0,.8],'Joint',head)


def vane(s,grp):
    pts=curve(GRASS['tegmen']);xs=[q[0] for q in pts];lo=min(xs);hi=max(xs)
    rows=[]
    row_count=29
    for i in range(row_count):
        u=(1-math.cos(i*math.pi/(row_count-1)))*.5;x=lo+(hi-lo)*(.00012+.99976*u)
        a,b=span(pts,x);row=[]
        for j in range(13):
            v=j/12
            y=a+(b-a)*v
            # Along the folded shell the medial margin lies high on the dorsum
            # while the lower rim wraps around the abdomen on the same side.
            lat=3.8+v*(24.0+11.0*math.sin(math.pi*u)) + 13.0*math.sin(math.pi*v)*math.sin(math.pi*u)
            row.append((x,s*lat,y))
        rows.append(row)
    verts=[v for row in rows for v in row];faces=[]
    for i in range(row_count-1):
        for j in range(12):n=i*13+j;faces.append((n,n+1,n+14,n+13))
    part(verts,faces,PAPER,grp,(4,))
    # Low relief longitudinal veins and sparse cross-veins are rigidly attached
    # to their own wing bone. The cuticle stays readable under custom paint.
    for j in [0,3,7,12]:
        line=[(r[j][0],r[j][1]+s*.46,r[j][2]-.25) for r in rows[2:-2:2]]
        radius=1.05 if j in (0,12) else .67
        tube(line,[radius*(1-.65*k/(len(line)-1)) for k in range(len(line))],'Amber rib',grp,6)
    for i in [8,14,19,23]:
        for a,b in [(3,7),(7,12)]:
            line=[(rows[i+(j-a)//2][j][0],rows[i+(j-a)//2][j][1]+s*.55,
                   rows[i+(j-a)//2][j][2]-.25) for j in range(a,b+1)]
            tube(line,[.43]*len(line),'Amber rib',grp,5)


def pleated_hindwing(side):
    # Adjacent rails share a membrane. Separate bone weights widen the fan like
    # a pleated grasshopper wing without creating gaps between the rays.
    fanbones=[bone(f'Fan {side} sector {j}',(222,side*10,93),root) for j in range(3)]
    batch=batches.setdefault('Hindwing membrane',{'v':[],'f':[],'g':[],'uv':[],'regions':[]})
    for j,length in enumerate([213,215,208,202,181,157,128]):
        row=[];weight=fanbones[min(2,j//2)]
        for i in range(12):
            t=i/11
            point=(222+t*length,side*(10+t*(3+j*2.15)+2.1*math.sin(math.pi*t)),
                   93+t*(4+j*2.5)+1.6*math.sin(math.pi*t)*(-1)**j)
            row.append(point)
        base=len(batch['v']);batch['v'].extend(wp(v) for v in row);batch['g'].extend([weight]*len(row))
        if j:
            for i in range(11):
                a=base-12+i;b=base+i
                batch['f'].extend([(a,a+1,b),(a+1,b+1,b)])
        if j%2==0:
            tube(row[1:],[.53*(1-.58*i/10) for i in range(11)],'Amber rib',weight,5)


if not ANT_MODE:
    for side in (-1,1):
        wing=bone('Tegmen '+str(side),(216,side*9,86),root);vane(side,wing)
        pleated_hindwing(side)

# Modest setae catch glancing light on the ant's gaster and the jumping femora.
rng=random.Random(802)
if ANT_MODE:
    pts=curve(ANT['gaster'])
    for _ in range(50):
        x=rng.uniform(335,460);a,b=span(pts,x);r=(b-a)*.5;mid=(a+b)*.5
        t=rng.uniform(0,math.tau);lat=39*(r/54.5)**.79*math.sin(t)
        y=mid+r*math.cos(t)
        tube([(x,lat,y),(x+1.5,lat+1.3*math.sin(t),y+1.3*math.cos(t)),
              (x+3.0,lat+2.2*math.sin(t),y+2.2*math.cos(t))],[.44,.28,.06],'Amber rib',abd,5)

rig_data=bpy.data.armatures.new(K+' anatomical rig');rig=bpy.data.objects.new(K+' skeleton',rig_data)
scene.collection.objects.link(rig);bpy.context.view_layer.objects.active=rig;rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for name,(pt,parent) in bones.items():
    b=rig_data.edit_bones.new(name);b.head=pt;b.tail=pt+Vector((0,.008,0))
    if parent:b.parent=rig_data.edit_bones[parent]
bpy.ops.object.mode_set(mode='OBJECT')
for mat,batch in batches.items():
    name='PaperSurface' if mat==PAPER else mat
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(batch['v'],[],batch['f'])
    mesh.materials.append(mats[mat]);mesh.update()
    if mat==PAPER:
        layer=mesh.uv_layers.new(name='Paper coordinates')
        uvs=np.asarray(batch['uv'])
        weights=np.asarray([(i/6,j/6,(6-i-j)/6) for i in range(7) for j in range(7-i)])
        for poly,region in zip(mesh.polygons,batch['regions']):
            coords=uvs[list(poly.vertices)].copy()
            keep,xx,yy=lookups[region]
            def allowed(c):
                sample=weights@c
                x=(sample[:,0]*1024).astype(int);y=((1-sample[:,1])*1024).astype(int)
                return keep[y,x].all()
            if not allowed(coords):
                # Occluders split the visible side of a part (eye in the head,
                # thigh across wing). Keep triangle interiors in their own ink area.
                avg=coords.mean(axis=0)
                x=int(avg[0]*1024);y=int((1-avg[1])*1024)
                j=np.argmin((xx-x)**2+(yy-y)**2)
                pivot=np.array([(xx[j]+.5)/1024,1-(yy[j]+.5)/1024])
                for shrink in [.8,.6,.4,.2,.08,.025,0]:
                    candidate=pivot+(coords-avg)*shrink
                    if allowed(candidate):coords=candidate;break
            for loop,uv in zip(poly.loop_indices,coords):layer.data[loop].uv=uv
    bm=bmesh.new();bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    for poly in mesh.polygons:poly.use_smooth=True
    obj=bpy.data.objects.new(name,mesh);scene.collection.objects.link(obj)
    for group in sorted(set(batch['g'])):
        vg=obj.vertex_groups.new(name=group)
        vg.add([i for i,g in enumerate(batch['g']) if g==group],1,'REPLACE')
    mod=obj.modifiers.new('Anatomical articulation','ARMATURE');mod.object=rig;obj.parent=rig

# Motions are authored in drawing-space amplitudes, then solved in meters.
exec(compile((Path(__file__).parent/'ground_motion.py').read_text(encoding='utf-8'),'ground_motion.py','exec'))
scene.frame_set(1);scene.frame_end=73
scene.render.fps=24
rig.animation_data.action=None
for track in rig.animation_data.nla_tracks:track.mute=True
bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/f'{K}.blend'),compress=True)
bpy.ops.export_scene.gltf(filepath=str(RUNTIME/f'models/{K}.glb'),export_format='GLB',
    export_animation_mode='ACTIONS',export_animations=True,export_skins=True,
    export_force_sampling=True,export_frame_step=1,export_anim_slide_to_zero=True,
    export_optimize_animation_size=True,export_yup=True,export_cameras=False,export_lights=False,
    export_materials='EXPORT')
print('GROUND BUILT',K,flush=True)
