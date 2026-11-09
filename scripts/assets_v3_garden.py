"""Asset-only lotus garden study. No application files are written.

All visible near/midground features are real geometry, PBR images and lights.
The authored scene retains its lighting; GLB contains portable geometry/materials.
"""
import argparse
import json
import math
import random
import shutil
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'assets-src/v3-review/garden/sources/project-original-textures'
random.seed(85279)
TAU = math.tau
MATS = {}
BATCH = {}


def material(name, color, roughness=.7, metallic=0, emission=0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = roughness
    p.inputs['Metallic'].default_value = metallic
    p.inputs['Specular IOR Level'].default_value = .32
    if emission:
        p.inputs['Emission Color'].default_value = (*color, 1)
        p.inputs['Emission Strength'].default_value = emission
    MATS[name] = m
    return m


def image_array(name, array, out, noncolor=False):
    h, w = array.shape[:2]
    img = bpy.data.images.new(name, w, h, alpha=True)
    if noncolor:
        img.colorspace_settings.name = 'Non-Color'
    if array.shape[2] == 3:
        array = np.concatenate([array, np.ones((h, w, 1), dtype=np.float32)], axis=2)
    img.pixels.foreach_set(np.ascontiguousarray(array, dtype=np.float32).ravel())
    img.filepath_raw = str(out / 'textures' / (name + '.png'))
    img.file_format = 'PNG'
    img.save()
    img.pack()
    return img


def texture_material(name, source, roughness, bump_distance, out):
    """Bake a tangent-space normal map using Blender's normal bake, not a color tint."""
    m = material(name, (1, 1, 1), roughness)
    ns, ls = m.node_tree.nodes, m.node_tree.links
    p = ns.get('Principled BSDF')
    albedo_path = out / 'textures' / (name + '_albedo.png')
    shutil.copy2(source, albedo_path)
    img = bpy.data.images.load(str(albedo_path))
    img.name = name + '_albedo'
    img.pack()
    tex = ns.new('ShaderNodeTexImage'); tex.image = img
    ls.new(tex.outputs['Color'], p.inputs['Base Color'])
    bump = ns.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = .55
    bump.inputs['Distance'].default_value = bump_distance
    ls.new(tex.outputs['Color'], bump.inputs['Height'])
    ls.new(bump.outputs['Normal'], p.inputs['Normal'])
    bpy.ops.mesh.primitive_plane_add(size=2)
    plane = bpy.context.object; plane.data.materials.append(m)
    normal = bpy.data.images.new(name + '_normal', 1024, 1024)
    normal.colorspace_settings.name = 'Non-Color'
    target = ns.new('ShaderNodeTexImage'); target.image = normal
    ns.active = target
    bpy.context.scene.render.engine = 'CYCLES'
    bpy.context.scene.cycles.samples = 4
    bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT', margin=8)
    normal.filepath_raw = str(out / 'textures' / (name + '_normal.png'))
    normal.file_format = 'PNG'; normal.save(); normal.pack()
    ls.remove(p.inputs['Normal'].links[0]); ns.remove(bump)
    nmap = ns.new('ShaderNodeNormalMap')
    nmap.inputs['Strength'].default_value = .8
    ls.new(target.outputs['Color'], nmap.inputs['Color']); ls.new(nmap.outputs['Normal'], p.inputs['Normal'])
    bpy.data.objects.remove(plane, do_unlink=True)
    if name == 'lotus_leaf':
        # Bake the authored pigment treatment to the portable base-color map.
        # Surface lighting remains entirely separate from this albedo bake.
        bpy.ops.mesh.primitive_plane_add(size=2)
        leaf_plane=bpy.context.object; leaf_plane.data.materials.append(m)
        mul=ns.new('ShaderNodeMixRGB');mul.blend_type='MULTIPLY';mul.inputs[0].default_value=1
        mul.inputs[2].default_value=(.42,.60,.49,1);ls.new(tex.outputs['Color'],mul.inputs[1])
        emit=ns.new('ShaderNodeEmission');ls.new(mul.outputs['Color'],emit.inputs['Color'])
        output=ns.get('Material Output');ls.new(emit.outputs[0],output.inputs['Surface'])
        toned=bpy.data.images.new('lotus_leaf_albedo_authored',1254,1254)
        dst=ns.new('ShaderNodeTexImage');dst.image=toned;ns.active=dst
        bpy.ops.object.bake(type='EMIT',margin=8)
        toned.filepath_raw=str(out/'textures'/'lotus_leaf_albedo.png');toned.file_format='PNG';toned.save();toned.pack()
        ls.new(p.outputs[0],output.inputs['Surface']);ls.new(dst.outputs['Color'],p.inputs['Base Color'])
        ns.remove(mul);ns.remove(emit);ns.remove(tex)
        bpy.data.objects.remove(leaf_plane,do_unlink=True)
    # Authored roughness map contains varied grain; it is independent of albedo lighting.
    y, x = np.mgrid[0:512, 0:512] / 512
    grain = np.random.default_rng(92).random((512, 512))
    rough = np.clip(roughness + .12*(grain-.5) + .045*np.sin(x*190+np.sin(y*37)), .25, .98)
    rt = ns.new('ShaderNodeTexImage')
    rt.image = image_array(name+'_roughness', np.repeat(rough[:, :, None], 3, axis=2), out, True)
    ls.new(rt.outputs['Color'], p.inputs['Roughness'])
    return m


def addmesh(name, verts, faces, mat, uv=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces); data.update()
    ob = bpy.data.objects.new(name, data); bpy.context.collection.objects.link(ob)
    data.materials.append(MATS[mat])
    for face in data.polygons: face.use_smooth = True
    layer = data.uv_layers.new(name='UVMap')
    for poly in data.polygons:
        for k in poly.loop_indices:
            idx = data.loops[k].vertex_index
            layer.data[k].uv = uv[idx] if uv else (verts[idx][0], verts[idx][1])
    return ob


def batch(mat, verts, faces, uv=None):
    v, f, u = BATCH.setdefault(mat, ([], [], []))
    offset = len(v); v.extend(verts); f.extend(tuple(offset+i for i in face) for face in faces)
    u.extend(uv if uv else [(p[0], p[1]) for p in verts])


def tube(name, points, radii, mat, sides=10, batch_only=False):
    vs, fs, uv = [], [], []
    dist = 0
    for j, point in enumerate(points):
        p = Vector(point)
        tangent = Vector(points[min(j+1,len(points)-1)])-Vector(points[max(j-1,0)])
        tangent.normalize()
        ref = Vector((0, 0, 1)) if abs(tangent.z)<.95 else Vector((1,0,0))
        n = tangent.cross(ref).normalized(); b = tangent.cross(n)
        if j: dist += (p-Vector(points[j-1])).length
        r = radii[j] if isinstance(radii,list) else radii
        for i in range(sides+1):
            a = i*TAU/sides
            relief = 1+.045*math.sin(a*9+j*.5)+.02*math.sin(a*23)
            vs.append(tuple(p+r*relief*(n*math.cos(a)+b*math.sin(a))))
            uv.append((i/sides,dist/1.7))
    for j in range(len(points)-1):
        for i in range(sides):
            a=j*(sides+1)+i; fs.append((a,a+1,a+sides+2,a+sides+1))
    if batch_only: batch(mat,vs,fs,uv)
    else: return addmesh(name,vs,fs,mat,uv)


def leaf_surface(radius, variant, r, a):
    edge = 1+.045*math.sin(7*a+variant)+.024*math.sin(13*a+variant*.4)
    x = radius*r*edge*math.cos(a); y = radius*r*edge*math.sin(a)
    z = radius*(.16*r*r + .090*math.sin(a*7+variant)*r**5 + .13*math.sin(a*2+variant)*r*r)
    z += radius*.010*math.cos(a*22+math.sin(r*7))*r**1.6
    return Vector((x,y,z))


def leaf(name, center, radius, tilt, variant=0, details=True):
    vs, uv, fs = [], [], []
    rings, sectors = (22,112) if details else (10,56)
    quat = Vector(tilt).to_track_quat('Z','Y')
    def at(r,a,offset=0):
        p=leaf_surface(radius,variant,r,a); p.z+=offset
        return Vector(center)+quat@p
    # A tiny central fan, avoiding a ring of degenerate triangles.
    vs.append(tuple(at(0,0))); uv.append((.5,.5))
    for j in range(1,rings+1):
        r=j/rings
        for i in range(sectors):
            a=TAU*i/sectors
            vs.append(tuple(at(r,a))); uv.append((.5+.475*r*math.cos(a),.5+.475*r*math.sin(a)))
    for i in range(sectors): fs.append((0,1+i,1+(i+1)%sectors))
    for j in range(rings-1):
        for i in range(sectors):
            a=1+j*sectors+i; b=1+j*sectors+(i+1)%sectors
            fs.append((a,a+sectors,b+sectors,b))
    ob=addmesh(name,vs,fs,'lotus_leaf',uv)
    # Fine folded lip; thickness is explicit geometry so survives export.
    lip=[]
    for i in range(sectors+1): lip.append(tuple(at(1,TAU*i/sectors)))
    tube(name+'_rim',lip,radius*.0015,'leaf_vein',4,True)
    if details:
        for k in range(14):
            a=TAU*k/14+.12
            tube(name+'_vein',[tuple(at(.02+.94*j/18,a,.0016)) for j in range(19)],
                 [radius*.0026*(1-.84*j/18) for j in range(19)],'leaf_vein',5,True)
        # Small real droplets catch light; only a sparse foreground scattering.
        for k in range(20):
            r=random.uniform(.2,.95); a=random.random()*TAU; p=at(r,a,.006)
            droplet(p,random.uniform(.005,.012)*radius)
    cx,cy,cz=center
    tube(name+'_stem',[(cx+.12,cy+.08,-.14),(cx+.06,cy+.04,cz*.55),center],
         [radius*.030,radius*.025,radius*.018],'stem',14)
    return ob


def droplet(p,r):
    vs=[]; fs=[]; n=8; rings=5
    for j in range(rings+1):
        a=math.pi*j/rings
        for i in range(n):
            b=TAU*i/n
            vs.append((p.x+r*math.sin(a)*math.cos(b),p.y+r*math.sin(a)*math.sin(b),p.z+r*.7*math.cos(a)))
    for j in range(rings):
        for i in range(n): fs.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
    batch('dew',vs,fs)


def petal(center, angle, length, width, rise, mat):
    vs, fs, uv=[],[],[]; steps=18; across=8
    for j in range(steps+1):
        t=j/steps
        w=width*max(.008,math.sin(math.pi*t)**.72)*(1-.22*t)
        for k in range(across+1):
            s=2*k/across-1
            x=w*s; y=length*t
            z=rise*(t**1.6)+width*.38*s*s*math.sin(math.pi*t)
            vs.append((center[0]+x*math.cos(angle)+y*math.sin(angle),center[1]-x*math.sin(angle)+y*math.cos(angle),center[2]+z))
            uv.append((k/across,t))
    for j in range(steps):
        for k in range(across):
            i=j*(across+1)+k; fs.append((i,i+1,i+across+2,i+across+1))
    batch(mat,vs,fs,uv)


def flower(center, scale=1, bud=False):
    x,y,z=center
    tube('lotus_flower_stem',[(x+.02,y,-.10),(x,y,z)],.014*scale,'stem',10)
    for layer in range(4):
        for i in range(9):
            a=TAU*(i+layer*.4)/9
            if bud:
                le=(.07-.01*layer)*scale; rise=(.45-.06*layer)*scale
            else:
                le=(.42-.085*layer)*scale; rise=(.14+.045*layer)*scale
            petal(center,a,le,(.12-.02*layer)*scale,rise,'lotus_petal')
    if not bud:
        for k in range(55):
            a=k*2.399; r=.046*math.sqrt(k/55)*scale
            p=(x+r*math.cos(a),y+r*math.sin(a),z+.04)
            tube('stamen',[p,(p[0],p[1],p[2]+.07*scale)],[.002*scale,.004*scale],'gold',4,True)


def reed(x,y,height,angle,shade, flowered=False):
    width=random.uniform(.012,.040); bend=random.uniform(.50,1.65)
    vs=[]; fs=[]; uv=[]
    for j in range(11):
        t=j/10; w=width*math.sin(math.pi*(.08+.92*t))
        cx=x+math.sin(angle)*bend*t*t; cy=y+math.cos(angle)*bend*t*t
        for s in [-1,0,1]:
            vs.append((cx+s*w*math.cos(angle),cy-s*w*math.sin(angle),height*t+(.003 if s==0 else 0)))
            uv.append(((s+1)*.5,t))
    for j in range(10):
        for i in range(2):
            a=j*3+i; fs.append((a,a+1,a+4,a+3))
    batch('reed_'+str(shade),vs,fs,uv)
    if flowered:
        for k in range(7):
            t=.76+k*.032; cx=x+math.sin(angle)*bend*t*t; cy=y+math.cos(angle)*bend*t*t
            for n in range(3):
                a=k*2.4+n*2.09
                p=(cx,cy,height*t); q=(cx+.065*math.cos(a),cy+.065*math.sin(a),height*t+.03)
                tube('grass_floret',[p,q],[.003,.008],'grass_flower',4,True)


def moss_tuft(p,size,phase):
    # A short branched stem with paired tapered micro-leaves, rather than broad flat petals.
    x,y,z=p
    for stem in range(3):
        a=phase+stem*2.09; h=size*(.65+.35*random.random())
        dx=math.cos(a)*h*.27; dy=math.sin(a)*h*.27
        for k in range(4):
            t=.2+k*.20
            for sign in [-1,1]:
                b=a+sign*1.4
                start=Vector((x+dx*t,y+dy*t,z+h*t))
                tip=start+Vector((math.cos(b)*h*.35,math.sin(b)*h*.35,h*.2))
                cross=Vector((-math.sin(b),math.cos(b),0))*h*.065
                batch('moss_'+str(int((phase*13)%3)),[tuple(start),tuple((start+tip)*.5+cross),tuple(tip),tuple((start+tip)*.5-cross)],[(0,1,2,3)])


def moss_cushion(p,radius):
    vs=[];fs=[];sectors=12;rings=4
    for j in range(rings+1):
        t=j/rings
        for i in range(sectors):
            a=i*TAU/sectors
            r=radius*t*(1+.13*math.sin(a*5))
            vs.append((p[0]+r*math.cos(a),p[1]+r*math.sin(a),p[2]+radius*.75*(1-t*t)+radius*.12*math.sin(a*5+j)))
    for j in range(rings):
        for i in range(sectors):fs.append((j*sectors+i,j*sectors+(i+1)%sectors,(j+1)*sectors+(i+1)%sectors,(j+1)*sectors+i))
    batch('moss_'+str(random.randrange(3)),vs,fs)


def log(name, start, end, radius, count=1100):
    start,end=Vector(start),Vector(end); axis=end-start
    points=[tuple(start+axis*(j/24)+Vector((0,.02*math.sin(j*.25),.035*math.sin(j*.31)))) for j in range(25)]
    ob=tube(name,points,[radius*(1-.22*j/24) for j in range(25)],'bark',64)
    tangent=axis.normalized(); n=tangent.cross(Vector((0,0,1))).normalized(); b=tangent.cross(n)
    for k in range(count):
        t=random.random(); a=random.uniform(.03,math.pi-.03)
        # b points downward for this frame convention; use world-positive half.
        side=n*math.cos(a)-b*math.sin(a)
        if side.z<0: side=-side
        p=start+axis*t+side*(radius*(1-.22*t))
        moss_tuft(tuple(p),random.uniform(.025,.069),random.random()*TAU)
        if k%4==0:moss_cushion(tuple(p),random.uniform(.02,.043))
    return ob


def stump(center,height,radius):
    x,y,z=center; vs=[]; fs=[]; uv=[]; rings=52; sectors=96
    for j in range(rings+1):
        t=j/rings
        for i in range(sectors+1):
            a=i*TAU/sectors
            top=height*(.91+.055*math.sin(a*3+.4)+.025*math.sin(a*7+1.7))
            rr=radius*(1-.36*t+.38*math.exp(-t*8))
            rr*=1+.09*math.sin(a*13+t*1.4)+.035*math.sin(a*31+t*9)
            vs.append((x+rr*math.cos(a)+.09*t*t,y+rr*math.sin(a),z+top*t))
            uv.append((i/sectors*1.25,t*2.7))
    for j in range(rings):
        for i in range(sectors):
            a=j*(sectors+1)+i;fs.append((a,a+1,a+sectors+2,a+sectors+1))
    addmesh('hero_broken_trunk',vs,fs,'bark',uv)
    for k in range(14):
        a=k*TAU/14
        tube('root_flare',[(x,y,z+.55),(x+radius*.7*math.cos(a),y+radius*.7*math.sin(a),z+.2),(x+radius*1.6*math.cos(a),y+radius*1.6*math.sin(a),z-.04)],
             [radius*.19,radius*.17,.005],'bark',12)
    cap_v=[];cap_f=[]
    for j in range(5):
        r=radius*.67*j/4
        for i in range(48):
            a=i*TAU/48;edge=height*(.91+.055*math.sin(a*3+.4)+.025*math.sin(a*7+1.7))
            cap_v.append((x+r*math.cos(a)+.09,y+r*math.sin(a),z+edge-.10*(1-j/4)))
    for j in range(4):
        for i in range(48):cap_f.append((j*48+i,j*48+(i+1)%48,(j+1)*48+(i+1)%48,(j+1)*48+i))
    addmesh('broken_wood_interior',cap_v,cap_f,'wood')
    for k in range(5):
        a=k*TAU/5+.3;r=radius*.49
        tube('exposed_splinter',[(x+r*math.cos(a)+.09,y+r*math.sin(a),z+height*.83),(x+r*.70*math.cos(a)+.13,y+r*.9*math.sin(a),z+height*(.93+random.random()*.06))],[.038,.002],'wood',7)
    for k in range(700):
        a=random.random()*TAU; t=random.uniform(.01,.42)
        rr=radius*(1-.46*t+.38*math.exp(-t*8))
        p=(x+rr*math.cos(a),y+rr*math.sin(a),z+height*t*.83)
        if k%3: moss_tuft(p,random.uniform(.015,.035),a)


def water():
    vs=[];fs=[];uv=[]; n=170; span=28
    for j in range(n+1):
        y=-9+span*j/n
        for i in range(n+1):
            x=-span/2+span*i/n
            z=-.10+.006*math.sin(x*13+y*8+math.sin(y*3))+.004*math.sin(x*21-y*17+math.sin(x*2))
            vs.append((x,y,z));uv.append((x*.35,y*.35))
    for j in range(n):
        for i in range(n):
            a=j*(n+1)+i;fs.append((a,a+1,a+n+2,a+n+1))
    addmesh('pond_water',vs,fs,'water',uv)


def materials(out):
    texture_material('lotus_leaf',SOURCE/'leaf.png',.47,.035,out)
    texture_material('bark',SOURCE/'bark.png',.87,.13,out)
    material('wood',(.29,.21,.135),.92)
    material('leaf_vein',(.18,.27,.065),.6)
    material('stem',(.055,.16,.075),.58)
    for i,c in enumerate([(.048,.13,.065),(.095,.19,.055),(.19,.28,.072)]): material('moss_'+str(i),c,.92)
    for i,c in enumerate([(.034,.105,.082),(.065,.16,.085),(.12,.21,.075)]): material('reed_'+str(i),c,.68)
    material('grass_flower',(.31,.15,.23),.78)
    material('gold',(.72,.39,.055),.52)
    m=material('dew',(.8,.95,1),.08)
    p=m.node_tree.nodes.get('Principled BSDF'); p.inputs['Transmission Weight'].default_value=.88; p.inputs['IOR'].default_value=1.33
    m=material('water',(.009,.027,.047),.10,.04)
    p=m.node_tree.nodes.get('Principled BSDF'); p.inputs['IOR'].default_value=1.333
    # Portable tangent-space ripples, independently generated rather than painted highlights.
    y,x=np.mgrid[0:512,0:512]/512
    dx=np.zeros_like(x);dy=np.zeros_like(y)
    for i,(kx,ky) in enumerate([(3,7),(11,-4),(17,13),(-9,23),(27,7),(6,-31),(43,19),(-37,33)]):
        phase=TAU*(x*kx+y*ky)+i*1.734
        strength=.11/(1+i*.55);dx+=strength*np.cos(phase);dy+=strength*(ky/(abs(kx)+abs(ky)))*np.cos(phase)
    nn=np.stack([-dx,-dy,np.ones_like(dx)],axis=2);nn/=np.linalg.norm(nn,axis=2)[:,:,None]
    tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=image_array('water_normal',nn*.5+.5,out,True)
    nm=m.node_tree.nodes.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.40
    m.node_tree.links.new(tex.outputs['Color'],nm.inputs['Color']);m.node_tree.links.new(nm.outputs['Normal'],p.inputs['Normal'])
    m=material('lotus_petal',(1,1,1),.48)
    y,x=np.mgrid[0:512,0:512]/512
    base=np.array([1,.71,.69])[None,None,:]*(1-y[:,:,None])+np.array([.91,.25,.49])[None,None,:]*y[:,:,None]
    vein=.04*np.sin(x*190+np.sin(y*12))+.015*np.sin(x*451)
    base=np.clip(base+vein[:,:,None],0,1)
    tx=m.node_tree.nodes.new('ShaderNodeTexImage');tx.image=image_array('lotus_petal_albedo',base,out)
    p=m.node_tree.nodes.get('Principled BSDF');m.node_tree.links.new(tx.outputs['Color'],p.inputs['Base Color'])
    p.inputs['Subsurface Weight'].default_value=.10
    m.node_tree.links.new(tx.outputs['Color'],p.inputs['Emission Color']);p.inputs['Emission Strength'].default_value=.18
    material('firefly',(.8,.55,.13),.5,emission=30)


def scene_geometry():
    # The opening between midground trunks and leaves gives the eye a calm resting area.
    layout=[(-1.92,.10,1.98,1.40,(.1,-.26,1)),(2.9,1.25,2.6,1.25,(-.18,-.35,1)),
            (-.72,2.2,1.2,.91,(.12,-.30,1)),(-2.6,3.5,3.7,1.55,(.1,-.62,1)),
            (.12,6.2,3.65,1.45,(.1,-.40,1)),(2.3,5.5,2.05,1.06,(-.2,-.48,1)),
            (3.65,-1.4,.68,1.0,(.20,.10,1)),(-2.9,-2.8,.35,1.30,(.1,-.4,1)),
            (1.35,-3.2,.12,.93,(-.2,-.12,1))]
    for i,(x,y,z,r,normal) in enumerate(layout):leaf('hero_leaf_%02d'%i,(x,y,z),r,normal,i, i<4)
    for i in range(28):
        x=random.uniform(-8,8); y=random.uniform(4.2,13); z=random.uniform(.8,4.8)
        if abs(x)<1.5 and y<7:continue
        leaf('background_leaf_%02d'%i,(x,y,z),random.uniform(.58,1.35),(random.uniform(-.4,.4),random.uniform(-.5,.15),1),i,False)
    # Pads give readable scale and break up the water reflections.
    for i in range(13):
        x=random.uniform(-4,4);y=random.uniform(-.4,8)
        leaf('water_pad_%02d'%i,(x,y,-.065),random.uniform(.2,.47),(0,0,1),i,False)
    stump((1.05,2.4,-.12),3.28,.39)
    stump((-1.22,2.75,-.12),1.1,.17)
    log('foreground_moss_log',(-2.95,-.65,1.28),(.70,-2.85,.30),.28,2600)
    log('right_moss_log',(3.9,-.25,1.16),(1.7,2.2,.05),.20,1000)
    flowers=[((-.13,1.55,.19),1,False),((-2.72,.08,.95),.9,True),((2.66,3.3,.34),.88,False),
             ((-.78,6.3,.10),.75,False),((-3.3,4.25,.24),.75,False),((3.7,7,.4),.7,True)]
    for p,s,b in flowers:flower(p,s,b)
    for layer in range(3):
        for cluster in range(15):
            cx=-9+cluster*1.3+random.uniform(-.5,.5);cy=4.8+layer*4+random.uniform(-.7,.7)
            base_h=random.uniform(1.3,4.2)*(1-.12*layer)
            for k in range(23):
                x=cx+random.gauss(0,.30);y=cy+random.gauss(0,.35)
                if -.3<x<.9 and y<8:continue
                h=base_h*random.uniform(.55,1.1)
                reed(x,y,h,random.uniform(-1.2,1.2)+(cluster%2)*math.pi,(cluster+layer)%3,k%16==0)
    water()
    for i in range(33):
        p=(random.uniform(-3.4,3.6),random.uniform(-.2,7),random.uniform(.5,2.75))
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=random.uniform(.005,.010),location=p)
        ob=bpy.context.object;ob.name='firefly';ob.data.materials.append(MATS['firefly'])
    for mat,(vs,fs,uv) in BATCH.items():addmesh('detail_'+mat,vs,fs,mat,uv)


def light(name,pos,target,color,energy,size=1,kind='AREA'):
    data=bpy.data.lights.new(name,kind);data.energy=energy;data.color=color
    if kind=='AREA':data.shape='DISK';data.size=size
    ob=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(ob);ob.location=pos
    ob.rotation_euler=(Vector(target)-ob.location).to_track_quat('-Z','Y').to_euler()
    return ob


def presentation(out, resolution, render=True):
    sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.samples=48
    sc.cycles.use_denoising=True;sc.cycles.max_bounces=9;sc.cycles.transparent_max_bounces=32
    sc.render.threads_mode='FIXED';sc.render.threads=4
    sc.render.resolution_x=resolution;sc.render.resolution_y=round(resolution*9/16);sc.render.resolution_percentage=100
    sc.view_settings.view_transform='AgX';sc.view_settings.look='AgX - Medium High Contrast';sc.view_settings.exposure=.15
    world=sc.world;world.use_nodes=True
    ns=world.node_tree.nodes;ls=world.node_tree.links;ns.clear()
    tx=ns.new('ShaderNodeTexEnvironment');tx.image=bpy.data.images.load(str(SOURCE/'sky.png'));tx.image.pack()
    bg=ns.new('ShaderNodeBackground');bg.inputs['Strength'].default_value=.10
    end=ns.new('ShaderNodeOutputWorld');ls.new(tx.outputs['Color'],bg.inputs['Color']);ls.new(bg.outputs[0],end.inputs[0])
    light('moon_rim',(1.2,6.8,7),(0,1,1),(.31,.57,1),1000,4.2)
    light('warm_near_leaf',(-3.7,-.9,3.5),(-1.4,.1,1.1),(1,.76,.43),450,1.1)
    light('warm_moss_edge',(-2.6,-1.6,2.2),(-1.0,-1.8,.4),(1,.85,.55),110,.65)
    light('cool_front',(0,-4,3),(0,2,1),(.52,.68,1),65,4)
    light('trunk_raking',(0,.0,3.8),(1,2.4,1.7),(1,.78,.53),190,1.35)
    light('soft_blue_water',(0,8,1.6),(0,1,0),(.15,.42,1),48,5)
    light('lotus_bounce',(-.13,1.55,.55),(-.13,1.55,0),(1,.24,.45),8,.28,'POINT')
    light('lotus_soft_front',(-.9,.1,1.8),(-.13,1.55,.25),(1,.58,.69),20,1.2)
    # A sparse physically shaded atmosphere; separate from exportable meshes.
    fog=bpy.data.materials.new('PREVIEW_atmosphere');fog.use_nodes=True
    fn=fog.node_tree.nodes;fn.clear();fo=fn.new('ShaderNodeOutputMaterial');v=fn.new('ShaderNodeVolumePrincipled')
    v.inputs['Density'].default_value=.014;v.inputs['Color'].default_value=(.31,.45,.67,1);v.inputs['Anisotropy'].default_value=.20
    fog.node_tree.links.new(v.outputs['Volume'],fo.inputs['Volume'])
    bpy.ops.mesh.primitive_cube_add(size=1,location=(0,9,4));o=bpy.context.object;o.name='PREVIEW_atmosphere';o.scale=(24,25,12);o.data.materials.append(fog)
    camera_data=bpy.data.cameras.new('Garden_review_camera');cam=bpy.data.objects.new('Garden_review_camera',camera_data);bpy.context.collection.objects.link(cam)
    cam.location=(0,-4.75,1.24);target=Vector((0,2.4,1.44));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler()
    camera_data.lens=31;camera_data.clip_end=150;camera_data.dof.use_dof=False;sc.camera=cam
    sc.render.image_settings.file_format='PNG';sc.render.filepath=str(out/'garden-actual.png')
    # Compositor glow is authored scene presentation, not baked into albedo.
    sc.use_nodes=True
    tree=bpy.data.node_groups.new('GardenReviewCompositor','CompositorNodeTree')
    tree.interface.new_socket(name='Image',in_out='OUTPUT',socket_type='NodeSocketColor')
    sc.compositing_node_group=tree
    rl=tree.nodes.new('CompositorNodeRLayers');gl=tree.nodes.new('CompositorNodeGlare')
    gl.inputs['Type'].default_value='Fog Glow';gl.inputs['Quality'].default_value='High';gl.inputs['Threshold'].default_value=1.4
    go=tree.nodes.new('NodeGroupOutput');tree.links.new(rl.outputs['Image'],gl.inputs['Image']);tree.links.new(gl.outputs['Image'],go.inputs['Image'])
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'garden.blend'))
    if render:bpy.ops.render.render(write_still=True)


def export(out):
    bpy.ops.object.select_all(action='DESELECT')
    obs=[o for o in bpy.context.scene.objects if o.type=='MESH' and not o.name.startswith('PREVIEW_')]
    for o in obs:o.select_set(True)
    # Batch per material for export, but retain individual editable source meshes in .blend.
    report={'source':'authored geometry; existing project original generated albedo; baked normal maps',
            'units':'metres; Blender Z up, GLB Y up','render':'Cycles actual scene; GLB lighting parity not assumed',
            'meshCount':len(obs),'vertices':sum(len(o.data.vertices) for o in obs),
            'triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in obs),
            'materials':len(MATS),'textures':[p.name for p in (out/'textures').glob('*.png')],
            'previewOnly':['volumetric atmosphere','area lights','compositor glow','world panorama'],
            'needsRuntimeEquivalent':['environment illumination/reflection','contact and directional shadows','water reflection','subsurface leaf/petal light transport']}
    bpy.ops.export_scene.gltf(filepath=str(out/'garden.glb'),export_format='GLB',use_selection=True,export_yup=True,export_cameras=False,export_lights=False,export_animations=False)
    report['glbBytes']=(out/'garden.glb').stat().st_size
    (out/'garden-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    p=argparse.ArgumentParser();p.add_argument('--output-dir',default=str(ROOT/'assets-src/v3-review/garden'));p.add_argument('--resolution',type=int,default=1440);p.add_argument('--build-only',action='store_true')
    opts=p.parse_args(args);out=Path(opts.output_dir);(out/'textures').mkdir(parents=True,exist_ok=True)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.context.scene.render.threads_mode='FIXED';bpy.context.scene.render.threads=4
    materials(out);scene_geometry();export(out);presentation(out,opts.resolution,not opts.build_only)
