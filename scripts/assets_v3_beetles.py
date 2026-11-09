"""Original Blender review assets only. Does not write application assets or code.

Blender --background --factory-startup --disable-autoexec --python this.py --
  --species ladybug|beetle --output-dir assets-src/v3-review/<species>
  [--mode build|render|poses|setting|roundtrip|validate|reanimate]
  [--quick] [--gpu] [--first-only] [--no-render] [--resolution 960]

Run render jobs serially. `build --no-render` writes the editable asset and GLB;
`render` reads the blend and creates review images; `roundtrip` imports the GLB
in a fresh Blender process, checks 214 animation samples, and renders it.
"""
import argparse
import hashlib
import json
import math
import random
import re
import struct
import sys
import zlib
from pathlib import Path

import bpy
import bmesh
import numpy as np
from mathutils import Vector, Matrix, Euler
from mathutils.bvhtree import BVHTree

TAU = math.tau
EXPORT = []
BONES = {}
SCENE_OBJECTS = []
MATERIALS = {}
LINEART = Path(__file__).resolve().parents[1]/'assets-src/v3-review/lineart/manifest.json'


def approved_beetle_profile(index):
    region=json.loads(LINEART.read_text(encoding='utf-8'))['species']['beetle']['regions'][index]
    tokens=re.findall(r'[MCZ]|[-+]?\d*\.?\d+',region['d'])
    i=0;current=None;points=[]
    while i<len(tokens):
        command=tokens[i];i+=1
        if command=='M':
            current=np.array([float(tokens[i]),float(tokens[i+1])]);i+=2;points.append(current)
        elif command=='C':
            control=np.array([float(x) for x in tokens[i:i+6]]).reshape(3,2);i+=6
            a=current.copy();b,c,d=control
            for t in np.linspace(0,1,21)[1:]:points.append((1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d)
            current=d
        elif command=='Z':break
    return [((p[0]-289)*.00072+.020,(350-p[1])*.00072) for p in points]


def profile_span(points,x):
    hits=[]
    for a,b in zip(points,points[1:]+points[:1]):
        if min(a[0],b[0])<=x<=max(a[0],b[0]) and abs(b[0]-a[0])>1e-9:
            t=(x-a[0])/(b[0]-a[0]);hits.append(a[1]+t*(b[1]-a[1]))
    return (min(hits),max(hits)) if hits else (points[0][1],points[0][1])


def sculpt_profile(name,index,width,mat,group='body_root'):
    points=approved_beetle_profile(index)
    verts=[]
    for side in (-1,1):
        for x,z in points:
            taper=max(.10,min(1,(.245-z)/(.10 if index==2 else .085)))
            verts.append((x,side*width*taper,z))
    n=len(points)
    faces=[tuple(reversed(range(n))),tuple(n+i for i in range(n))]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    obj=mesh(name,verts,faces,mat,group)
    # Tessellate the concave profile, then bow each cross section continuously.
    # This creates a rounded solid shield and recurved horn, not a flat extruded cutout.
    bm=bmesh.new();bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
    bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=3,use_grid_fill=True)
    points_array=np.array(points);ends=np.roll(points_array,-1,axis=0)
    delta=ends-points_array;length=np.maximum(np.sum(delta*delta,axis=1),1e-12)
    for vert in bm.verts:
        x,y,z=vert.co
        q=np.array([x,z]);t=np.clip(np.sum((q-points_array)*delta,axis=1)/length,0,1)
        distance=float(np.sqrt(np.min(np.sum((q-points_array-t[:,None]*delta)**2,axis=1))))
        vert.co.y=y*(.20+.80*(1-math.exp(-distance/(.0045 if index==2 else .009))))
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
    for p in obj.data.polygons:p.use_smooth=True
    return obj


def smooth(t):
    t = max(0., min(1., t))
    return t*t*(3-2*t)


def noise(size, cells, seed):
    rng = np.random.default_rng(seed)
    grid = rng.random((cells+1, cells+1), dtype=np.float32)
    p = np.linspace(0, cells-.0001, size, dtype=np.float32)
    i = p.astype(np.int32)
    f = p-i
    f = f*f*(3-2*f)
    a = grid[i[:, None], i[None, :]]
    b = grid[i[:, None]+1, i[None, :]]
    c = grid[i[:, None], i[None, :]+1]
    d = grid[i[:, None]+1, i[None, :]+1]
    return (a*(1-f[:, None])+b*f[:, None])*(1-f[None, :])+(c*(1-f[:, None])+d*f[:, None])*f[None, :]


def image_file(name, array, directory, noncolor=False, linear_pixels=False):
    h,w = array.shape[:2]
    rgba = np.ones((h,w,4), dtype=np.float32)
    if array.ndim == 2:
        rgba[:,:,:3] = array[:,:,None]
    else:
        rgba[:,:,:array.shape[2]] = array
    if linear_pixels and not noncolor:
        rgb = np.maximum(rgba[:,:,:3],0)
        rgba[:,:,:3] = np.where(rgb <= .0031308,12.92*rgb,1.055*rgb**(1/2.4)-.055)
    # Palettes are authored sRGB values. Write those bytes directly; assigning them to
    # Blender's linear pixel buffer and saving would gamma-lift every color twice.
    pixels = np.round(np.clip(rgba,0,1)*255).astype(np.uint8)[::-1]
    def chunk(kind,data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    payload=b''.join(b'\x00'+row.tobytes() for row in pixels)
    path=directory/(name+'.png')
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(payload,6))+chunk(b'IEND',b''))
    image = bpy.data.images.load(str(path),check_existing=False)
    image.name=name
    image.colorspace_settings.name = 'Non-Color' if noncolor else 'sRGB'
    image.pack()
    return image


def material(name, palette, out, kind='wax', spot=False, size=1024):
    if name in MATERIALS:
        return MATERIALS[name]
    seed = sum(ord(c) for c in name)*3
    v,u = np.mgrid[0:1:complex(size),0:1:complex(size)]
    coarse = noise(size, 6, seed)
    mid = noise(size, 42, seed+1)
    fine = noise(size, 340, seed+2)
    paper = np.array([.93,.897,.82],dtype=np.float32)
    color = np.empty((size,size,3),dtype=np.float32)
    p0,p1 = np.array(palette[0]),np.array(palette[-1])
    mix = np.clip(.5+.25*np.sin(u*8-v*5)+.35*(coarse-.5),0,1)
    pigment = p0[None,None,:]*(1-mix[:,:,None])+p1[None,None,:]*mix[:,:,None]
    if kind in ('wax','collar'):
        scribble = .5+.5*np.sin((u*.77+v)*198+mid*6+coarse*2)
        coverage = np.clip(.64+.24*mid+.15*scribble,0,1)
        grain_holes = np.clip((fine-.70)*1.8,0,.27)
        coverage -= grain_holes
        color[:] = pigment*coverage[:,:,None]+paper*(1-coverage[:,:,None])
        stroke = np.maximum(0,np.sin((u*.68-v)*241+coarse*9))**7
        color *= (1-.10*stroke[:,:,None])
        if name=='right_mint_wax':
            yellow=(np.maximum(0,np.sin((u*.8+v)*105+coarse*7+mid*2))**9*.28)[:,:,None]
            color=color*(1-yellow)+np.array([.90,.80,.41])[None,None,:]*yellow
        height = .5*mid+.27*fine+.23*scribble
        rough = .58+.17*mid+.06*fine
        if spot:
            # Exactly one large lengthwise oval per shell. No generated extra dots.
            distance = ((u-.45)/.230)**2+((v-.60)/.125)**2
            edge = np.clip((1-distance)*28+(.5-mid)*.8,0,1)
            ink = np.stack((.20+.08*mid,.115+.065*mid,.084+.045*mid),axis=-1)
            ink = ink*(1-grain_holes[:,:,None]*.52)+paper*grain_holes[:,:,None]*.52
            color = color*(1-edge[:,:,None])+ink*edge[:,:,None]
            rough = rough*(1-edge)+(.67+.12*mid)*edge
        if kind=='collar':
            edge=np.clip((1-((u-.50)/.50)**6-((v-.5)/.145)**4)*18+(.5-mid)*.7,0,1)
            ink=np.stack((.15+.075*mid,.085+.045*mid,.052+.035*mid),axis=-1)
            color=color*(1-edge[:,:,None])+ink*edge[:,:,None]
    elif kind == 'cuticle':
        color[:] = pigment*(.76+.28*mid[:,:,None])
        pores = np.maximum(0,(fine-.75))*2
        height = .5*mid+.42*fine-.13*pores
        rough = .43+.18*mid
    elif kind == 'leaf':
        vein = np.maximum(0,1-abs(v-.5)*190)
        ribs = np.exp(-np.abs(np.sin((u*.75+abs(v-.5))*71))*15)
        color[:] = pigment*(.83+.24*coarse[:,:,None])
        color += (vein*.045+ribs*.022)[:,:,None]
        height = .6*mid+.15*fine+.15*ribs
        rough = .52+.12*mid
    elif kind == 'bark':
        ridges = np.sin(u*118+mid*5+coarse*5)
        cracks = np.maximum(0,ridges)**12
        color[:] = pigment*(.68+.38*mid[:,:,None])*(1-cracks[:,:,None]*.38)
        height = .40*mid+.25*fine-.35*cracks
        rough = .83+.09*mid
    else:
        color[:] = pigment
        height = fine*.2
        rough = np.full((size,size),.23,dtype=np.float32)
    gy,gx = np.gradient(height.astype(np.float32))
    strength = 1.4 if kind=='wax' else 2.2 if kind in ('bark','cuticle') else .7
    normal = np.stack((-gx*strength,-gy*strength,np.ones_like(gx)),axis=-1)
    normal /= np.linalg.norm(normal,axis=-1)[:,:,None]
    normal = normal*.5+.5
    texdir = out/'textures'
    texdir.mkdir(parents=True,exist_ok=True)
    base = image_file(name+'_basecolor',np.clip(color,0,1),texdir)
    roughness = image_file(name+'_roughness',np.clip(rough,0,1),texdir,True)
    normals = image_file(name+'_normal',normal,texdir,True)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bs = mat.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Metallic'].default_value = 0
    bs.inputs['IOR'].default_value = 1.47
    bs.inputs['Coat Weight'].default_value = .035 if kind=='wax' else 0
    for image,target in [(base,'Base Color'),(roughness,'Roughness')]:
        node = mat.node_tree.nodes.new('ShaderNodeTexImage'); node.image=image
        mat.node_tree.links.new(node.outputs['Color'],bs.inputs[target])
    node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=normals
    n=mat.node_tree.nodes.new('ShaderNodeNormalMap');n.inputs['Strength'].default_value=.75
    mat.node_tree.links.new(node.outputs['Color'],n.inputs['Color'])
    mat.node_tree.links.new(n.outputs['Normal'],bs.inputs['Normal'])
    MATERIALS[name]=mat
    return mat


def bone(name, position, parent='body_root'):
    BONES[name]=(tuple(position),parent)
    return name


def mesh(name, vertices, faces, mat, group='body_root', uv=None, export=True):
    data=bpy.data.meshes.new(name)
    data.from_pydata(vertices,[],faces); data.update()
    if uv is None:
        xyz=np.array(vertices)
        lo=xyz.min(axis=0); span=np.maximum(xyz.max(axis=0)-lo,1e-6)
        uv=[((p[0]-lo[0])/span[0],(p[2]-lo[2])/span[2]) for p in vertices]
    layer=data.uv_layers.new(name='ArtSurfaceUV')
    for poly in data.polygons:
        poly.use_smooth=True
        for li in poly.loop_indices:
            layer.data[li].uv=uv[data.loops[li].vertex_index]
    bm=bmesh.new();bm.from_mesh(data)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(data);bm.free()
    obj=bpy.data.objects.new(name,data);bpy.context.scene.collection.objects.link(obj)
    data.materials.append(mat)
    if export:
        obj['rig_bone']=group
        EXPORT.append(obj)
    else: SCENE_OBJECTS.append(obj)
    return obj


def ellipsoid(name,center,radius,mat,group='body_root',rings=22,sides=40,export=True):
    verts=[];uv=[]
    for i in range(1,rings):
        a=math.pi*i/rings
        for j in range(sides):
            b=TAU*j/sides
            q=(math.cos(a),math.sin(a)*math.cos(b),math.sin(a)*math.sin(b))
            verts.append(tuple(center[k]+q[k]*radius[k] for k in range(3)))
            uv.append((j/sides,i/rings))
    first=len(verts);verts.append((center[0]+radius[0],center[1],center[2]));uv.append((.5,0))
    last=len(verts);verts.append((center[0]-radius[0],center[1],center[2]));uv.append((.5,1))
    faces=[]
    for i in range(rings-2):
        for j in range(sides):
            a=i*sides+j;b=i*sides+(j+1)%sides
            faces.append((a,b,b+sides,a+sides))
    for j in range(sides):
        faces.append((first,(j+1)%sides,j))
        faces.append((last,(rings-2)*sides+j,(rings-2)*sides+(j+1)%sides))
    return mesh(name,verts,faces,mat,group,uv,export)


def smooth_path(points,radii,steps=7):
    points=[Vector(p) for p in points]
    out=[];rr=[]
    for i in range(len(points)-1):
        a,b,c,d=points[max(0,i-1)],points[i],points[i+1],points[min(len(points)-1,i+2)]
        for j in range(steps):
            t=j/steps
            out.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
            rr.append(radii[i]*(1-t)+radii[i+1]*t)
    out.append(points[-1]);rr.append(radii[-1])
    return out,rr


def tube(name,path,radii,mat,group='body_root',sides=12,steps=7,export=True,flatten=1):
    points,rr=smooth_path(path,radii,steps)
    verts=[];uv=[]
    for i,p in enumerate(points):
        direction=(points[min(i+1,len(points)-1)]-points[max(0,i-1)]).normalized()
        ref=Vector((0,0,1)) if abs(direction.z)<.9 else Vector((0,1,0))
        n=direction.cross(ref).normalized();b=direction.cross(n).normalized()
        for j in range(sides):
            a=TAU*j/sides
            v=p+rr[i]*(math.cos(a)*n+math.sin(a)*b*flatten)
            verts.append(v);uv.append((j/sides,i/(len(points)-1)))
    faces=[]
    for i in range(len(points)-1):
        for j in range(sides):
            a=i*sides+j;n=i*sides+(j+1)%sides
            faces.append((a,n,n+sides,a+sides))
    faces.extend([tuple(reversed(range(sides))),tuple((len(points)-1)*sides+j for j in range(sides))])
    return mesh(name,verts,faces,mat,group,uv,export)


def elytron(species,side,mat,rim,edge):
    lady=species=='ladybug'
    cx,rx,ry,base,height=(-.019,.087,.066,.037,.061) if lady else (-.080,.115,.066,.046,.052)
    nlong,narch=72,44
    gap=.00135
    silhouette=approved_beetle_profile(0) if not lady else None
    if silhouette:
        xlow=min(p[0] for p in silhouette)+.00015;xhigh=max(p[0] for p in silhouette)-.00015
        cx=(xlow+xhigh)/2;rx=(xhigh-xlow)/2
    verts=[];uv=[]
    # Shells have an actual underside and rolled boundary, not two painted half-spheres.
    for inside in (False,True):
        for i in range(nlong+1):
            u=-.998+1.996*i/nlong
            profile=max(0,1-u*u)
            width=ry*profile**(.49 if lady else .34)*(1-.10*u)
            for j in range(narch+1):
                a=(math.pi/2)*j/narch
                x=cx+rx*u
                y=side*(gap/2+width*math.sin(a))
                # The beetle has a long shoulder ridge and a flatter, tapered rear.
                dome=height*profile**(.57 if lady else .38)
                z=base+dome*max(0,math.cos(a))**.94
                if silhouette:
                    bottom,top=profile_span(silhouette,x)
                    z=bottom+(top-bottom)*max(0,math.cos(a))**.94
                z+=.00016*math.sin(u*92+a*26)*math.sin(a)**2
                if inside:z-=.0017
                verts.append((x,y,z))
                # Equal-angle UV avoids compressing the lower half of a spot near the dome apex.
                uv.append(((u+1)/2,j/narch))
    surface=(nlong+1)*(narch+1)
    faces=[]
    for layer in (0,1):
        for i in range(nlong):
            for j in range(narch):
                k=layer*surface+i*(narch+1)+j
                f=(k,k+1,k+narch+2,k+narch+1)
                faces.append(f if layer==0 else tuple(reversed(f)))
    boundary=[i*(narch+1) for i in range(nlong+1)]+[nlong*(narch+1)+j for j in range(1,narch+1)]+[i*(narch+1)+narch for i in range(nlong-1,-1,-1)]+[j for j in range(narch-1,0,-1)]
    for a,b in zip(boundary,boundary[1:]+boundary[:1]):faces.append((a,b,b+surface,a+surface))
    hinge=(cx+rx*.85,side*.020,base+.005) if lady else (.019,side*.019,.085)
    group=bone('elytron_'+('L' if side<0 else 'R'),hinge)
    obj=mesh('elytron_'+('L' if side<0 else 'R'),verts,faces,mat,group,uv)
    lower=[verts[i*(narch+1)+narch] for i in range(0,nlong+1,3)]
    tube('elytron_rolled_edge_'+str(side),lower,[.0009]*len(lower),rim,group,sides=8,steps=2)
    # A fine warm cuticle lip, with a dark cavity visible down the center seam.
    center=[tuple(Vector(verts[i*(narch+1)])+Vector((0,side*.00035,-.0006))) for i in range(1,nlong,3)]
    tube('elytron_suture_lip_'+str(side),center,[.00055]*len(center),edge,group,sides=8,steps=2)
    return obj


def leg(species,side,index,cuticle,joint,claw):
    lady=species=='ladybug'
    xs=[.048,-.012,-.072] if lady else [.076,-.012,-.113]
    roots=[(x,side*(.038 if lady else .040),.030 if lady else [.075,.069,.046][i]) for i,x in enumerate(xs)]
    a=Vector(roots[index])
    b=Vector((xs[index]+([.016,.008,-.028][index]),side*(.064 if lady else .086),.026 if lady else [.055,.044,.032][index]))
    c=Vector((b.x+[.014,.006,-.012][index],side*(.082 if lady else .119),.006))
    d=Vector((c.x+.010,side*(.091 if lady else .134),.0020))
    label=('L' if side<0 else 'R')+str(index+1)
    thick=.0035 if lady else .0063
    hip=bone('coxa_'+label,a)
    femur=bone('femur_'+label,a,hip)
    tibia=bone('tibia_'+label,b,femur)
    tarsus=bone('tarsus_'+label,c,tibia)
    ellipsoid('coxa_socket_'+label,a,(thick*1.6,thick*1.4,thick*1.5),joint,hip,rings=12,sides=20)
    tube('femur_'+label,[a,(a+b)*.5,b],[thick*.86,thick*1.10,thick*.7],cuticle,femur,sides=14)
    ellipsoid('knee_'+label,b,(thick*.95,thick*.93,thick),joint,tibia,rings=12,sides=20)
    tube('tibia_'+label,[b,b*.55+c*.45,c],[thick*.64,thick*.71,thick*.37],cuticle,tibia,sides=14)
    tube('tarsus_'+label,[c,c*.65+d*.35,c*.32+d*.68,d],[thick*.42,thick*.38,thick*.28,thick*.19],joint,tarsus,sides=12,steps=4)
    # Tarsal cuff plates and paired recurved claws.
    for k in range(1,4):
        p=c.lerp(d,k/4)
        ellipsoid('tarsal_plate_'+label+'_'+str(k),p,(thick*.34,thick*.34,thick*.27),cuticle,tarsus,rings=8,sides=12)
    for sign in (-1,1):
        end=d+Vector((.0055,sign*.0032,-.0009))
        tube('claw_'+label+'_'+str(sign),[d,d+Vector((.002,sign*.002,.0018)),end],[thick*.17,thick*.14,.00016],claw,tarsus,sides=8,steps=5)
    for k in range(3 if lady else 5):
        p=b.lerp(c,.20+k*.13)
        offset=Vector((-.003,side*.0022,.0005))*(.65 if lady else 1)
        tube('tibial_spine_'+label+'_'+str(k),[p,p+offset],[thick*.14,.00007],claw,tibia,sides=5,steps=2)
    return a,b,c,d


def wing(species,side,membrane,vein):
    lady=species=='ladybug'
    root=Vector((.026 if lady else .002,side*.025,.054 if lady else .118))
    direction=Vector((-.73,side*.683,0))
    across=Vector((side*.683,.73,0))
    proximal=.077 if lady else .106
    distal=.079 if lady else .105
    width=.022 if lady else .027
    label='L' if side<0 else 'R'
    rootbone=bone('wing_root_'+label,root)
    tipcenter=root+direction*proximal+Vector((0,0,.0009))
    tipbone=bone('wing_fold_'+label,tipcenter,rootbone)
    for part,start,length,bn in [('prox',root,proximal,rootbone),('dist',tipcenter,distal,tipbone)]:
        verts=[];uv=[];faces=[]
        for i in range(23):
            t=i/22
            w=width*(.35+.65*math.sin(math.pi*t*.92))*(1 if part=='dist' else .66)
            if part=='dist':w*=max(.045,(1-t)**.35)
            for j in range(9):
                q=(j/8-.5)*2
                p=start+direction*(t*length)+across*(q*w)
                p.z+=.0003*(1-q*q)*math.sin(t*math.pi)
                verts.append(p);uv.append((j/8,t))
        for i in range(22):
            for j in range(8):
                k=i*9+j;faces.append((k,k+1,k+10,k+9))
        mesh('flight_membrane_'+label+'_'+part,verts,faces,membrane,bn,uv)
        for j in (0,4,8):
            points=[verts[i*9+j] for i in range(0,23,2)]
            tube('wing_vein_'+label+'_'+part+'_'+str(j),points,[.00021 if j==4 else .00013]*len(points),vein,bn,sides=5,steps=1)
        for i in (6,12,17):
            points=[verts[i*9+j] for j in range(0,9,2)]
            tube('wing_crossvein_'+label+'_'+part+'_'+str(i),points,[.00010]*len(points),vein,bn,sides=5,steps=1)


def ladybug_collar(mat,rim):
    verts=[];uv=[];faces=[];nu,nv=18,64
    for inner in (0,1):
        for i in range(nu+1):
            u=i/nu
            for j in range(nv+1):
                a=-math.pi/2+math.pi*j/nv
                x=.058+.026*u+.004*math.sin(a)**2*(1-2*u)
                y=(.041-.011*u)*math.sin(a)
                z=.035+(.034-.013*u)*math.cos(a)-inner*.0014
                verts.append((x,y,z));uv.append((u,j/nv))
    count=(nu+1)*(nv+1)
    for inner in (0,1):
        for i in range(nu):
            for j in range(nv):
                k=inner*count+i*(nv+1)+j;f=(k,k+1,k+nv+2,k+nv+1)
                faces.append(f if not inner else tuple(reversed(f)))
    perimeter=[j for j in range(nv+1)]+[i*(nv+1)+nv for i in range(1,nu+1)]+[nu*(nv+1)+j for j in range(nv-1,-1,-1)]+[i*(nv+1) for i in range(nu-1,0,-1)]
    for a,b in zip(perimeter,perimeter[1:]+perimeter[:1]):faces.append((a,b,b+count,a+count))
    mesh('pronotum',verts,faces,mat,uv=uv)
    front=[verts[nu*(nv+1)+j] for j in range(0,nv+1,2)]
    tube('pronotum_lower_lip',front,[.00055]*len(front),rim,sides=8,steps=2)


def beetle_abdomen(mat,joint):
    profile=approved_beetle_profile(0)
    verts=[];uv=[];faces=[];nlong,nring=56,40
    xlow=-.178;xhigh=max(p[0] for p in profile)-.0002
    for i in range(nlong+1):
        x=xlow+(xhigh-xlow)*i/nlong;u=-.98+1.96*i/nlong
        lower,upper=profile_span(profile,x)
        w=.059*max(.06,1-u*u)**.40
        for j in range(nring):
            a=TAU*j/nring
            verts.append((x,w*math.sin(a),lower-.014+.019*math.cos(a)))
            uv.append((i/nlong,j/nring))
    for i in range(nlong):
        for j in range(nring):
            a=i*nring+j;b=i*nring+(j+1)%nring;faces.append((a,b,b+nring,a+nring))
    faces.extend([tuple(reversed(range(nring))),tuple(nlong*nring+j for j in range(nring))])
    mesh('abdomen',verts,faces,mat,uv=uv)
    for i in range(9):
        x=-.165+i*.021;lower,upper=profile_span(profile,x)
        w=.053*math.sqrt(max(.15,1-((x+.075)/.112)**2))
        ellipsoid('sternite_'+str(i),(x,0,lower-.030),(.014,w,.009),joint,rings=14,sides=30)


def build_insect(species,out):
    lady=species=='ladybug'
    BONES['body_root']=((0,0,0),None)
    dark=material('warm_brown_cuticle',[(.21,.112,.061),(.31,.185,.096)],out,'cuticle',size=512)
    joint=material('articulated_cuticle',[(.27,.145,.075),(.36,.218,.120)],out,'cuticle',size=512)
    black=material('dark_chitin',[(.068,.039,.024),(.108,.066,.036)],out,'cuticle',size=512)
    eye=material('dark_gloss_eyes',[(.023,.021,.017),(.035,.030,.022)],out,'gloss',size=128)
    cream=material('warm_ivory_wax',[(.77,.64,.40),(.94,.88,.68)],out,'wax')
    vein=material('wing_vein',[(.30,.204,.115),(.45,.33,.17)],out,'cuticle',size=256)
    membrane=material('flight_membrane',[(.59,.48,.29),(.83,.74,.48)],out,'gloss',size=512)
    membrane.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.42
    if lady:
        left=material('left_pink_wax',[(.85,.24,.43),(.97,.53,.64)],out,spot=True)
        right=material('right_mint_wax',[(.24,.60,.64),(.57,.80,.64)],out,spot=True)
        ellipsoid('abdomen',( -.019,0,.027),(.079,.060,.020),dark)
        for i in range(7):
            x=-.090+i*.023
            w=.050*math.sqrt(max(.15,1-((x+.016)/.10)**2))
            ellipsoid('sternite_'+str(i),(x,0,.021),(.016,w,.009),joint,rings=12,sides=28)
        ellipsoid('thorax_underplate',(.059,0,.030),(.035,.044,.017),black)
        h=bone('head',(.073,0,.039))
        collar=material('ivory_collar_with_brown_smudge',[(.77,.64,.40),(.94,.88,.68)],out,'collar')
        ladybug_collar(collar,black)
        ellipsoid('head',(.095,0,.034),(.019,.025,.017),dark,h)
        tube('clypeus_edge',[(.106,-.018,.029),(.113,0,.024),(.106,.018,.029)],[.0016,.0022,.0016],joint,h)
        for side in (-1,1):
            tube('cheek_suture_'+str(side),[(.093,side*.023,.039),(.103,side*.021,.034),(.110,side*.013,.026)],[.00045,.00040,.00030],black,h,sides=6)
        eye_x,eye_y,eye_z=.100,.024,.039
        antenna_root=(.108,.016,.030)
    else:
        left=material('left_green_elytron',[(.24,.59,.46),(.71,.80,.46)],out)
        right=material('right_green_elytron',[(.25,.58,.52),(.68,.79,.53)],out)
        blue=material('lavender_pronotum',[(.40,.45,.76),(.67,.72,.91)],out)
        beetle_abdomen(dark,joint)
        ellipsoid('thorax_underplate',(.063,0,.079),(.059,.043,.027),dark)
        ellipsoid('neck_cuticle',(.113,0,.077),(.026,.025,.019),black)
        sculpt_profile('pronotum_and_short_horn',1,.044,blue)
        h=bone('head',(.105,0,.074))
        sculpt_profile('head_and_recurved_horn',2,.013,cream,h)
        eye_x,eye_y,eye_z=.109,.014,.075
        antenna_root=(.123,.013,.068)
    for side in (-1,1):
        elytron(species,side,left if side<0 else right,cream,black)
        ellipsoid('eye_'+str(side),(eye_x,side*eye_y,eye_z),(.009 if not lady else .0052, .0045 if not lady else .0032,.007 if not lady else .0045),eye,h,rings=20,sides=28)
        root=Vector((antenna_root[0],side*antenna_root[1],antenna_root[2]))
        ab=bone('antenna_'+('L' if side<0 else 'R'),root,h)
        end=root+Vector((.025,side*.017,.005))
        tube('antenna_'+str(side),[root,root+Vector((.011,side*.007,.009)),end],[.0015,.0011,.00085],dark,ab,sides=10)
        for i in range(3):
            ellipsoid('antenna_club_'+str(side)+'_'+str(i),end+Vector((i*.0015,side*i*.0007,0)),(.003,.0018,.002),joint,ab,rings=10,sides=16)
        tube('mandible_'+str(side),[(eye_x+.010,side*.009,.027 if lady else .069),(eye_x+.021,side*.009,.020 if lady else .054),(eye_x+.024,side*.002,.023 if lady else .057)],
            [.003,.002,.0005],black,h,sides=10)
        for i in range(3):leg(species,side,i,dark,joint,black)
        wing(species,side,membrane,vein)
    if lady:
        for name,(position,parent) in list(BONES.items()):
            if name=='head' or name.startswith('antenna_'):
                BONES[name]=((position[0],position[1],position[2]+.004),parent)
        for obj in EXPORT:
            if obj['rig_bone']=='head' or obj['rig_bone'].startswith('antenna_'):
                for vertex in obj.data.vertices:vertex.co.z+=.004
    return dark


def rig_and_animate(species):
    arm=bpy.data.armatures.new(species+'_rig')
    rig=bpy.data.objects.new(species+'_rig',arm);bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active=rig;rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    for name,(position,parent) in BONES.items():
        b=arm.edit_bones.new(name);b.head=position;b.tail=Vector(position)+Vector((0,0,.014))
        if parent:b.parent=arm.edit_bones[parent]
    bpy.ops.object.mode_set(mode='OBJECT')
    for obj in EXPORT:
        obj.parent=rig
        vg=obj.vertex_groups.new(name=obj['rig_bone']);vg.add(list(range(len(obj.data.vertices))),1,'REPLACE')
        mod=obj.modifiers.new('Articulated insect skin','ARMATURE');mod.object=rig
    rig.animation_data_create()
    basis=arm.bones['body_root'].matrix_local.to_3x3()
    invbasis=basis.inverted()
    def pose(name,xyz=(0,0,0),translation=(0,0,0)):
        p=rig.pose.bones[name]
        p.rotation_mode='QUATERNION'
        p.rotation_quaternion=(invbasis @ Euler(tuple(math.radians(v) for v in xyz),'XYZ').to_matrix() @ basis).to_quaternion()
        p.location=invbasis @ Vector(translation)
    clips={'idle':72,'walk':36,'touch':42,'takeoff':60,'flight':48}
    for clip,end in clips.items():
        action=bpy.data.actions.new(clip);action.use_fake_user=True
        rig.animation_data.action=action
        for f in range(1,end+1):
            t=(f-1)/(end-1)
            for p in rig.pose.bones:
                p.rotation_mode='QUATERNION';p.rotation_quaternion=(1,0,0,0);p.location=(0,0,0);p.scale=(1,1,1)
            opened=unfold=lift=winglift=0
            flap=0
            if clip=='takeoff':
                opened=smooth((t-.07)/.35)
                winglift=smooth((t-.43)/.08)
                unfold=smooth((t-.52)/.24)
                lift=smooth((t-.78)/.22)
                flap=math.sin((t-.76)/.24*TAU*2)*14*smooth((t-.76)/.15)
            elif clip=='flight':
                opened=unfold=lift=winglift=1
                flap=math.sin(t*TAU*4)*14
            pose('body_root',(0,-lift*5,0),(0,0,lift*(.09 if species=='ladybug' else .12)))
            for side,label in [(-1,'L'),(1,'R')]:
                # Open the cases first. Membranes then lift above the body and unfold into free air.
                pose('elytron_'+label,(side*opened*22,opened*55,-side*opened*38))
                pose('wing_root_'+label,(side*(unfold*27+flap),0,side*(1-unfold)*43.1),
                    (0,0,winglift*.020))
                pose('wing_fold_'+label,(0,0,side*(1-unfold)*172))
                antenna=math.sin(t*TAU*(1 if clip=='idle' else 2)+side)*4
                pose('antenna_'+label,(0,side*antenna,side*antenna*.6))
                for i in range(3):
                    phase=t*TAU*2+(0 if (i+(side>0))%2==0 else math.pi)
                    walk=1 if clip=='walk' else 0
                    pose('coxa_'+label+str(i+1),(0,0,math.sin(phase)*walk*8))
                    pose('femur_'+label+str(i+1),(side*(max(0,math.sin(phase))*walk*9-lift*17),0,0))
                    pose('tibia_'+label+str(i+1),(side*(-max(0,math.sin(phase))*walk*10+lift*24),0,0))
                    pose('tarsus_'+label+str(i+1),(side*lift*12,0,0))
            if clip=='touch':
                response=math.sin(math.pi*t)**2
                pose('head',(0,-response*7,0))
                for side,label in [(-1,'L'),(1,'R')]:pose('antenna_'+label,(0,side*response*12,0))
            elif clip=='idle':pose('head',(0,math.sin(t*TAU)*1.5,math.sin(t*TAU)*1.0))
            for p in rig.pose.bones:
                p.keyframe_insert('rotation_quaternion',frame=f,group=p.name)
                p.keyframe_insert('location',frame=f,group=p.name)
        action['description']='Original articulated review asset; world locomotion is intentionally in place.'
    rig.animation_data.action=bpy.data.actions['idle']
    bpy.context.scene.frame_set(1)
    return rig,clips


def stage_material(color,roughness=.8):
    m=bpy.data.materials.new('review_stage_material');m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=roughness
    return m


def stage(species,out,natural=False):
    for obj in list(SCENE_OBJECTS):
        if obj.name in bpy.data.objects:bpy.data.objects.remove(obj,do_unlink=True)
    SCENE_OBJECTS.clear()
    if natural and species=='ladybug':
        mat=material('leaf_setting',[(.11,.25,.052),(.27,.42,.11)],out,'leaf')
        verts=[];uv=[];faces=[]
        for i in range(65):
            u=-.98+1.96*i/64
            for j in range(25):
                v=-1+2*j/24
                x=u*.22;y=v*.13*(1-u*u)**.5
                z=-.002+.0012*math.sin(u*15+v*11)+.0025*v*v
                verts.append((x,y,z));uv.append(((u+1)/2,(v+1)/2))
        for i in range(64):
            for j in range(24):
                k=i*25+j;faces.append((k,k+1,k+26,k+25))
        mesh('setting_leaf',verts,faces,mat,uv=uv,export=False)
        veinmat=stage_material((.22,.33,.065))
        for side in (-1,1):
            for i in range(7):
                x=-.17+i*.046
                edge=.119*math.sqrt(max(.03,1-((x+.035)/.22)**2))
                tube('setting_leaf_vein',[(x,0,-.0007),(x+.020,side*edge*.52,-.0009),(x+.035,side*edge,-.0006)],
                    [.00055,.00035,.00012],veinmat,sides=6,export=False)
        backdrop=stage_material((.035,.073,.018))
        mesh('soft_green_backdrop',[(-3,-3,-.045),(3,-3,-.045),(3,3,-.045),(-3,3,-.045)],[(0,1,2,3)],backdrop,export=False)
        glass=stage_material((.79,.91,.73),.075)
        glass.node_tree.nodes.get('Principled BSDF').inputs['Transmission Weight'].default_value=.94
        glass.node_tree.nodes.get('Principled BSDF').inputs['IOR'].default_value=1.333
        for i,(x,y,r) in enumerate([(-.145,-.035,.003),(-.130,.065,.0045),(.055,.106,.0028),(.137,-.075,.0032)]):
            ellipsoid('leaf_dewdrop_'+str(i),(x,y,.0008+r*.45),(r,r*.88,r*.61),glass,rings=14,sides=22,export=False)
    elif natural:
        mat=material('bark_setting',[(.27,.16,.075),(.50,.35,.19)],out,'bark')
        verts=[];uv=[];faces=[]
        coarse=noise(201,14,731);fine=noise(201,77,811)
        feet=[(x+.038,y) for x,y in [(.076,-.134),(.076,.134),(-.012,-.134),(-.012,.134),(-.141,-.134),(-.141,.134)]]
        for i in range(201):
            for j in range(161):
                u=i/200;v=j/160
                x=(u-.5)*.85;y=(v-.5)*.58
                height=.007*(coarse[i,j]-.5)+.003*(fine[i,j]-.5)+.0017*math.sin(v*181+coarse[i,j]*8)
                contact=min(math.hypot(x-fx,y-fy) for fx,fy in feet)
                z=-.002+height*smooth(contact/.018)
                verts.append((x,y,z));uv.append((v,u))
        for i in range(200):
            for j in range(160):
                k=i*161+j;faces.append((k,k+1,k+162,k+161))
        mesh('setting_bark',verts,faces,mat,uv=uv,export=False)
        moss=stage_material((.055,.12,.014));rng=random.Random(127)
        blades=[];leaves=[]
        for i in range(24):
            x=rng.uniform(-.34,.30);y=rng.choice([-1,1])*rng.uniform(.15,.23)
            for j in range(70):
                angle=rng.random()*TAU;rad=rng.random()*.012
                root=Vector((x+math.cos(angle)*rad,y+math.sin(angle)*rad,.0005))
                height=rng.uniform(.002,.008);bend=Vector((math.cos(angle),math.sin(angle),0))*height*.38
                width=Vector((-math.sin(angle),math.cos(angle),0))*rng.uniform(.0003,.00065)
                k=len(blades);blades.extend([root-width,root+width,root+Vector((0,0,height*.7))+bend*.65+width*.4,root+Vector((0,0,height))+bend,root+Vector((0,0,height*.7))+bend*.65-width*.4])
                leaves.extend([(k,k+1,k+2,k+4),(k+4,k+2,k+3)])
        mesh('setting_moss_leaves',blades,leaves,moss,export=False)
    else:
        mesh('neutral_floor',[(-3,-3,-.001),(3,-3,-.001),(3,3,-.001),(-3,3,-.001)],[(0,1,2,3)],stage_material((.37,.35,.30)),export=False)


def setup_render(species,quick,gpu=False):
    scene=bpy.context.scene
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=24 if quick else 48
    scene.cycles.use_denoising=True
    if gpu:
        prefs=bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type='OPTIX';prefs.get_devices()
        for device in prefs.devices:device.use=device.type=='OPTIX'
        if not any(device.use for device in prefs.devices):raise RuntimeError('No OptiX device available')
        scene.cycles.device='GPU'
    scene.render.threads_mode='FIXED';scene.render.threads=4
    scene.render.resolution_x=960;scene.render.resolution_y=960;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.render.fps=24
    scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.34,.39,.46,1)
    scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.28
    scene.view_settings.view_transform='AgX'
    scene.view_settings.look='AgX - Medium High Contrast'
    scene.view_settings.exposure=-.15
    for name,loc,energy,size,color in [
        ('large_soft_key',(.03,-.31,.48),2.8,.34,(1,.88,.73)),
        ('cool_fill',(.13,.30,.28),1.7,.28,(.75,.87,1)),
        ('shell_rim',(-.26,.10,.37),2.4,.23,(1,.95,.80))]:
        data=bpy.data.lights.new(name,'AREA');data.energy=energy;data.shape='DISK';data.size=size;data.color=color
        obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=loc
        obj.rotation_euler=(Vector((0,0,.055))-obj.location).to_track_quat('-Z','Y').to_euler()
    data=bpy.data.cameras.new('review_camera');camera=bpy.data.objects.new('review_camera',data);scene.collection.objects.link(camera)
    camera.location=(.38,-.22,.35) if species=='ladybug' else (.39,-.63,.29)
    target=Vector((-.005,0,.048)) if species=='ladybug' else Vector((-.012,0,.098))
    camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    data.type='ORTHO';data.ortho_scale=.285 if species=='ladybug' else .475
    scene.camera=camera
    return camera


def set_clip(rig,name,frame):
    rig.animation_data.action=next(a for a in bpy.data.actions if a.name==name or a.name.startswith(name+'_'))
    if rig.animation_data.action.slots:
        rig.animation_data.action_slot=rig.animation_data.action.slots[0]
    for track in rig.animation_data.nla_tracks:track.mute=True
    bpy.context.scene.frame_set(frame)


def render(path):
    bpy.context.scene.render.filepath=str(path)
    bpy.ops.render.render(write_still=True)


def contact_sheet(paths,out):
    rows=[]
    for path in paths:
        raw=path.read_bytes();offset=8;compressed=b''
        while offset<len(raw):
            length=struct.unpack_from('>I',raw,offset)[0];kind=raw[offset+4:offset+8];data=raw[offset+8:offset+8+length];offset+=length+12
            if kind==b'IHDR':w,h,depth,color,_,_,interlace=struct.unpack('>IIBBBBB',data)
            elif kind==b'IDAT':compressed+=data
        if depth!=8 or color not in (2,6) or interlace:raise ValueError('Contact sheet requires regular RGB/RGBA 8-bit PNGs')
        channels=4 if color==6 else 3;stride=w*channels;decoded=zlib.decompress(compressed)
        arr=np.zeros((h,stride),dtype=np.uint8)
        for y in range(h):
            f=decoded[y*(stride+1)];row=decoded[y*(stride+1)+1:(y+1)*(stride+1)]
            for x,value in enumerate(row):
                a=int(arr[y,x-channels]) if x>=channels else 0;b=int(arr[y-1,x]) if y else 0;c=int(arr[y-1,x-channels]) if y and x>=channels else 0
                if f==1:value+=a
                elif f==2:value+=b
                elif f==3:value+=(a+b)//2
                elif f==4:
                    p=a+b-c;pa,pb,pc=abs(p-a),abs(p-b),abs(p-c)
                    value+=a if pa<=pb and pa<=pc else b if pb<=pc else c
                arr[y,x]=value&255
        rgba=np.ones((h,w,4),dtype=np.float32);rgba[:,:,:channels]=arr.reshape(h,w,channels)/255.
        rows.append(rgba[::-1])
    h,w=rows[0].shape[:2]
    canvas=np.ones((h*2,w*3,4),dtype=np.float32)*.2
    for i,p in enumerate(rows):
        # Pixel array origin is bottom left; top row lists idle, walk, touch.
        y=(1-i//3)*h;x=(i%3)*w;canvas[y:y+h,x:x+w]=p
    image_file('animation_contact_sheet',canvas,out)


def glb_summary(path):
    raw=path.read_bytes();size,kind=struct.unpack_from('<II',raw,12);doc=json.loads(raw[20:20+size])
    return {'bytes':len(raw),'meshes':len(doc.get('meshes',[])),'skins':len(doc.get('skins',[])),
        'animations':[a.get('name') for a in doc.get('animations',[])],
        'images':len(doc.get('images',[])),'materials':len(doc.get('materials',[]))}


def stats(rig,clips,out,species):
    triangles=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in EXPORT)
    data={'species':species,'blender':bpy.app.version_string,'mesh_objects':len(EXPORT),
        'vertices':sum(len(o.data.vertices) for o in EXPORT),'triangles':triangles,
        'bones':len(rig.data.bones),'actions':clips,'all_meshes_have_uv':all(bool(o.data.uv_layers) for o in EXPORT),
        'all_meshes_have_weights':all(bool(o.vertex_groups) for o in EXPORT),
        'materials':len({m.name for o in EXPORT for m in o.data.materials}),
        'glb':glb_summary(out/(species+'.glb')),'runtime_tested':False}
    (out/'asset-validation.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    return data


def clearance_report(rig,out):
    """Check actual evaluated triangles for every takeoff/flight frame, including interpolation midpoints."""
    wings=[o for o in bpy.context.scene.objects if o.type=='MESH' and o.name.startswith('flight_membrane_')]
    solids=[o for o in bpy.context.scene.objects if o.type=='MESH' and
        (o.name in ('abdomen','thorax_underplate','pronotum','pronotum_and_short_horn') or
        (o.name.startswith('elytron_') and not any(x in o.name for x in ('edge','lip'))))]
    records=[]
    deps=bpy.context.evaluated_depsgraph_get()
    def tree(obj):
        evaluated=obj.evaluated_get(deps);data=evaluated.to_mesh()
        data.calc_loop_triangles()
        vertices=[evaluated.matrix_world@v.co for v in data.vertices]
        faces=[tuple(t.vertices) for t in data.loop_triangles]
        result=BVHTree.FromPolygons(vertices,faces,all_triangles=True,epsilon=.00003)
        evaluated.to_mesh_clear()
        return result
    for clip,end in [('takeoff',60),('flight',48)]:
        set_clip(rig,clip,1)
        for f in np.arange(1,end+.01,.5):
            bpy.context.scene.frame_set(int(f),subframe=float(f%1));deps.update()
            solidtrees=[(o.name,tree(o)) for o in solids]
            for wingobj in wings:
                wt=tree(wingobj)
                for name,st in solidtrees:
                    count=len(wt.overlap(st))
                    if count:records.append({'clip':clip,'frame':float(f),'wing':wingobj.name,'solid':name,'triangle_pairs':count})
    glb=next(out.glob('*.glb'))
    result={'source_glb_sha256':hashlib.sha256(glb.read_bytes()).hexdigest(),
        'method':'evaluated GLB triangle surface BVH overlap at every half frame, epsilon 0.03 mm',
        'sampled_frames':214,'intersection_records':records,'clear':not records,
        'tested_wings':[o.name for o in wings],'tested_solids':[o.name for o in solids],
        'limitation':'Surface intersection test, not volumetric signed distance; visual pose review is also required.'}
    (out/'flight-clearance.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'clear':not records,'intersection_records':len(records)}))


def render_bundle(rig,camera,species,out,first_only=False,preview=False):
    set_clip(rig,'idle',1)
    render(out/('preview_neutral.png' if preview else 'neutral_three_quarter.png'))
    if first_only:return
    render_setting(camera,species,out)
    stage(species,out)
    pose_gallery(rig,camera,species,out)


def render_setting(camera,species,out):
    stage(species,out,True)
    camera.data.type='PERSP';camera.data.lens=65 if species=='ladybug' else 60
    camera.data.dof.use_dof=True;camera.data.dof.aperture_fstop=8
    camera.data.dof.focus_distance=(camera.location-Vector((.015,0,.060 if species=='ladybug' else .115))).length
    bpy.ops.wm.save_as_mainfile(filepath=str(out/(species+'-natural-setting.blend')))
    render(out/'natural_setting.png')
    camera.data.type='ORTHO';camera.data.dof.use_dof=False


def pose_gallery(rig,camera,species,out,only_flight=False):
    scene=bpy.context.scene;scene.render.resolution_x=400;scene.render.resolution_y=400;scene.cycles.samples=24
    camera.data.ortho_scale*=1.32
    target=Vector((-.005,0,.048)) if species=='ladybug' else Vector((-.012,0,.098))
    if species=='beetle':
        camera.location=(.44,-.48,.52)
        camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.location=target+(camera.location-target)*1.7
    paths=[]
    for name,frame in [('idle',1),('walk',6),('touch',18),('takeoff',22),('takeoff',43),('flight',9)]:
        set_clip(rig,name,frame)
        lift=.09 if species=='ladybug' else .12
        if name=='flight':camera.location.z+=lift
        path=out/f'pose_{name}_{frame:02d}.png'
        if not only_flight or name=='flight':render(path)
        elif not path.exists():raise FileNotFoundError(path)
        paths.append(path)
        if name=='flight':camera.location.z-=lift
    contact_sheet(paths,out)


def export_asset(rig,clips,species,out):
    set_clip(rig,'idle',1)
    bpy.context.scene.frame_start=1;bpy.context.scene.frame_end=72
    bpy.ops.wm.save_as_mainfile(filepath=str(out/(species+'.blend')))
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True)
    for obj in EXPORT:obj.select_set(True)
    bpy.context.view_layer.objects.active=rig
    bpy.ops.export_scene.gltf(filepath=str(out/(species+'.glb')),export_format='GLB',use_selection=True,
        export_animations=True,export_animation_mode='ACTIONS',export_skins=True,
        export_force_sampling=True,export_all_influences=False,export_materials='EXPORT',export_yup=True)
    return stats(rig,clips,out,species)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output-dir',required=True)
    parser.add_argument('--species',choices=['ladybug','beetle'],required=True)
    parser.add_argument('--mode',choices=['build','roundtrip','flight','validate','render','poses','pose-flight','setting','reanimate'],default='build')
    parser.add_argument('--quick',action='store_true')
    parser.add_argument('--first-only',action='store_true')
    parser.add_argument('--no-render',action='store_true')
    parser.add_argument('--gpu',action='store_true')
    parser.add_argument('--resolution',type=int,default=960)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    out=Path(args.output_dir).resolve();out.mkdir(parents=True,exist_ok=True)
    if args.mode=='reanimate':
        bpy.ops.wm.open_mainfile(filepath=str(out/(args.species+'.blend')))
        oldrig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
        for b in oldrig.data.bones:BONES[b.name]=(tuple(b.head_local),b.parent.name if b.parent else None)
        for side,label in [(-1,'L'),(1,'R')]:
            BONES['elytron_'+label]=((.05495,side*.020,.042) if args.species=='ladybug' else (.019,side*.019,.085),'body_root')
        wing_delta=(.118-BONES['wing_root_L'][0][2]) if args.species=='beetle' else 0
        if abs(wing_delta)>1e-6:
            for name,(pos,parent) in list(BONES.items()):
                if name.startswith('wing_'):BONES[name]=((pos[0],pos[1],pos[2]+wing_delta),parent)
        for obj in list(bpy.context.scene.objects):
            if obj.type=='MESH' and 'rig_bone' in obj:
                if obj['rig_bone'].startswith('wing_'):
                    for vertex in obj.data.vertices:vertex.co.z+=wing_delta
                obj.parent=None;obj.vertex_groups.clear()
                for mod in list(obj.modifiers):
                    if mod.type=='ARMATURE':obj.modifiers.remove(mod)
                EXPORT.append(obj)
        bpy.data.objects.remove(oldrig,do_unlink=True)
        for a in list(bpy.data.actions):bpy.data.actions.remove(a)
        bpy.ops.object.select_all(action='DESELECT')
        rig,clips=rig_and_animate(args.species)
        export_asset(rig,clips,args.species,out)
        return
    if args.mode in ('render','poses','pose-flight','setting'):
        bpy.ops.wm.open_mainfile(filepath=str(out/(args.species+'.blend')))
        rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
        for obj in list(bpy.context.scene.objects):
            if obj!=rig and 'rig_bone' not in obj:bpy.data.objects.remove(obj,do_unlink=True)
        camera=setup_render(args.species,args.quick,args.gpu);stage(args.species,out)
        bpy.context.scene.render.resolution_x=args.resolution;bpy.context.scene.render.resolution_y=args.resolution
        if args.mode=='poses':pose_gallery(rig,camera,args.species,out)
        elif args.mode=='pose-flight':pose_gallery(rig,camera,args.species,out,True)
        elif args.mode=='setting':render_setting(camera,args.species,out)
        else:render_bundle(rig,camera,args.species,out,args.first_only,args.resolution<960)
        return
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
    if args.mode in ('roundtrip','validate','flight'):
        bpy.ops.import_scene.gltf(filepath=str(out/(args.species+'.glb')))
        rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
        if args.mode=='validate':
            clearance_report(rig,out);return
        if args.mode=='roundtrip':clearance_report(rig,out)
        setup_render(args.species,args.quick,args.gpu);stage(args.species,out)
        set_clip(rig,'idle',1)
        if args.mode=='roundtrip':render(out/'roundtrip_neutral.png')
        set_clip(rig,'flight',9)
        bpy.context.scene.camera.data.ortho_scale*=1.4
        target=Vector((-.005,0,.048)) if args.species=='ladybug' else Vector((-.012,0,.098))
        if args.species=='beetle':
            bpy.context.scene.camera.location=(.44,-.48,.52)
            bpy.context.scene.camera.rotation_euler=(target-bpy.context.scene.camera.location).to_track_quat('-Z','Y').to_euler()
        bpy.context.scene.camera.location=target+(bpy.context.scene.camera.location-target)*1.7
        bpy.context.scene.camera.location.z+=.09 if args.species=='ladybug' else .12
        render(out/'roundtrip_flight.png')
        report={'status':'imported_and_rendered','bones':len(rig.data.bones),
            'actions':[a.name for a in bpy.data.actions], 'glb':glb_summary(out/(args.species+'.glb'))}
        (out/('roundtrip-validation.json' if args.mode=='roundtrip' else 'flight-review-validation.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
        return
    build_insect(args.species,out)
    rig,clips=rig_and_animate(args.species)
    camera=setup_render(args.species,args.quick,args.gpu)
    stage(args.species,out)
    set_clip(rig,'idle',1)
    report=export_asset(rig,clips,args.species,out)
    if args.no_render:return
    render_bundle(rig,camera,args.species,out,args.first_only)
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
