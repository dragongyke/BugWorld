"""Derive a review candidate from approved v3 GLB; never overwrite approved or runtime assets."""
import argparse
import collections
import hashlib
import json
import math
import struct
import sys
import time
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'assets-src/v3-review/garden/garden.glb'
PROTECTED={'CC0_foreground_fallen_log','hero_leaf_07','hero_leaf_08','pond_water'}
SHIFTS={'CC0_foreground_fallen_log':-.34,'CC0_right_fallen_log':-.19}


def patch_mask(path):
    raw=path.read_bytes(); length=struct.unpack_from('<I',raw,12)[0]
    doc=json.loads(raw[20:20+length]); binary=raw[20+length:]
    moss=next(m for m in doc['materials'] if m['name']=='moss_01')
    moss['alphaMode']='MASK'; moss['alphaCutoff']=.35
    data=json.dumps(doc,separators=(',',':')).encode(); data+=b' '*((-len(data))%4)
    path.write_bytes(struct.pack('<4sII',b'glTF',2,20+len(data)+len(binary))+
                     struct.pack('<I4s',len(data),b'JSON')+data+binary)


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]); out=args.output_dir.resolve()
    for protected in [ROOT/'assets-src/v3-review',ROOT/'app/src/main/assets']:
        assert out!=protected and protected not in out.parents, 'Candidate output must not overwrite approved/runtime assets'
    out.mkdir(parents=True,exist_ok=True)
    start=time.perf_counter()
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(SOURCE))
    # Assign entire connected moss cards to the nearest original support before moving logs.
    trees={}
    for name in [*SHIFTS,'CC0_hero_weathered_stump']:
        ob=bpy.data.objects[name]
        trees[name]=BVHTree.FromPolygons([ob.matrix_world@v.co for v in ob.data.vertices],
                                       [list(p.vertices) for p in ob.data.polygons])
    moss=bpy.data.objects['CC0_moss_on_branches']
    parent=list(range(len(moss.data.vertices)))
    def find(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]]; i=parent[i]
        return i
    for edge in moss.data.edges:
        a,b=edge.vertices; parent[find(a)]=find(b)
    groups=collections.defaultdict(list)
    for v in moss.data.vertices: groups[find(v.index)].append(v.index)
    shifted=collections.Counter()
    inverse=moss.matrix_world.inverted()
    for indices in groups.values():
        centre=sum((moss.matrix_world@moss.data.vertices[i].co for i in indices),Vector())/len(indices)
        name=min(trees,key=lambda name:trees[name].find_nearest(centre)[3])
        shift=SHIFTS.get(name,0)
        for i in indices:
            moss.data.vertices[i].co=inverse@(moss.matrix_world@moss.data.vertices[i].co+Vector((0,0,shift)))
        shifted[name]+=len(indices)
    for name,shift in SHIFTS.items(): bpy.data.objects[name].location.z+=shift

    # Preserve nearby contact geometry. Only non-contact wood and dense flower interiors are simplified.
    reductions={'CC0_hero_weathered_stump':.45,'CC0_right_fallen_log':.40,
                'CC0_mossy_root_base':.40,'CC0_near_small_stump':.40,'detail_lotus_petal':.55,
                'detail_grass_flower':.65,'detail_dew':.65}
    decimated=[]
    for name,ratio in reductions.items():
        ob=bpy.data.objects.get(name)
        if ob is None: raise ValueError('Missing expected mesh '+name)
        before=len(ob.data.polygons)
        bpy.context.view_layer.objects.active=ob
        mod=ob.modifiers.new('Stage non-contact simplification','DECIMATE'); mod.ratio=ratio
        bpy.ops.object.modifier_apply(modifier=mod.name)
        decimated.append(dict(name=name,ratio=ratio,before=before,after=len(ob.data.polygons)))

    # The old 16 cm grid undersampled 30 cm waves, making the geometric normals stripe sharply.
    # Broad sub-millimetre swells plus a low-amplitude normal texture avoid that aliasing.
    water=bpy.data.objects['pond_water']; material=water.data.materials[0]
    vertices=[]; faces=[]; n=32
    for j in range(n+1):
        y=-9+28*j/n
        for i in range(n+1):
            x=-14+28*i/n
            vertices.append((x,y,-.10+.0008*math.sin(x*.8+y*.45)+.0005*math.sin(x*.4-y*.7)))
    for j in range(n):
        for i in range(n):
            a=j*(n+1)+i; faces.append((a,a+1,a+n+2,a+n+1))
    mesh=bpy.data.meshes.new('Stage calm pond'); mesh.from_pydata(vertices,[],faces); mesh.materials.append(material)
    uv=mesh.uv_layers.new(name='UVMap')
    for polygon in mesh.polygons:
        polygon.use_smooth=True
        for loop in polygon.loop_indices:
            point=mesh.vertices[mesh.loops[loop].vertex_index].co
            uv.data[loop].uv=(point.x*.2,point.y*.2)
    water.data=mesh
    principled=next(node for node in material.node_tree.nodes if node.type=='BSDF_PRINCIPLED')
    principled.inputs['Base Color'].default_value=(.018,.045,.060,1)
    principled.inputs['Metallic'].default_value=0; principled.inputs['Roughness'].default_value=.17
    principled.inputs['IOR'].default_value=1.333
    tex=next(node for node in material.node_tree.nodes if node.type=='TEX_IMAGE')
    y,x=np.mgrid[0:512,0:512]/512
    dx=np.zeros_like(x); dy=np.zeros_like(y)
    for kx,ky,strength,phase in [(1,2,.15,.2),(3,-1,.08,1.7),(2,5,.04,3.6),(13,-7,.012,2.2)]:
        wave=np.cos(2*np.pi*(x*kx+y*ky)+phase)
        dx+=strength*kx/math.hypot(kx,ky)*wave; dy+=strength*ky/math.hypot(kx,ky)*wave
    normals=np.stack([-dx,-dy,np.ones_like(dx)],axis=2); normals/=np.linalg.norm(normals,axis=2)[:,:,None]
    rgba=np.ones((512,512,4),dtype=np.float32); rgba[:,:,:3]=normals*.5+.5
    image=bpy.data.images.new('stage_water_normal',512,512,alpha=False)
    image.colorspace_settings.name='Non-Color'; image.pixels.foreach_set(rgba.ravel()); image.pack(); tex.image=image
    normal=next(node for node in material.node_tree.nodes if node.type=='NORMAL_MAP')
    normal.inputs['Strength'].default_value=.65

    # Keep close bark colour/normal detail; reduce low-frequency ARM and distant stump textures.
    resized=[]
    used={node.image for ob in bpy.context.scene.objects if ob.type=='MESH' for mat in ob.data.materials
          for node in mat.node_tree.nodes if node.type=='TEX_IMAGE' and node.image}
    for image in used:
        if max(image.size)>1024 and ('_arm_' in image.name or image.name.startswith('tree_stump_01')):
            before=list(image.size); image.scale(1024,1024); resized.append(dict(name=image.name,before=before,after=list(image.size)))
        image.pack()

    # Coarse spatial cells reduce submissions while retaining separate culled regions.
    batches=collections.defaultdict(list)
    for ob in list(bpy.context.scene.objects):
        if ob.type!='MESH' or ob.name in PROTECTED or ob.name.startswith(('CC0_','detail_')): continue
        if len(ob.data.materials)!=1: continue
        centre=sum((ob.matrix_world@Vector(corner) for corner in ob.bound_box),Vector())/8
        material_name=ob.data.materials[0].name
        cell=(math.floor(centre.x/4),math.floor(centre.y/4))
        batches[(material_name,cell)].append(ob)
    for (material_name,cell),objects in batches.items():
        if len(objects)<2: continue
        bpy.ops.object.select_all(action='DESELECT')
        for ob in objects: ob.select_set(True)
        bpy.context.view_layer.objects.active=objects[0]
        bpy.ops.object.join(); objects[0].name=f'batch_{material_name}_{cell[0]}_{cell[1]}'
    bpy.ops.object.select_all(action='SELECT')
    glb=out/'garden.glb'
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_yup=True,
                             export_cameras=False,export_lights=False,export_animations=False)
    patch_mask(glb)
    # Save an editable clean roundtrip, so its material alpha exactly matches the exported candidate.
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(glb))
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'garden-stage-candidate.blend'))
    report=dict(sourceSha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),sha256=hashlib.sha256(glb.read_bytes()).hexdigest(),
                elapsedSeconds=time.perf_counter()-start,shiftsMetres=SHIFTS,mossAssignedVertices=dict(shifted),
                decimation=decimated,resizedTextures=resized,waterTriangles=2048,mossAlphaMode='MASK',mossAlphaCutoff=.35,
                scope='Review candidate, not approved source or deployed runtime. No dynamic waves or planar reflection.')
    (out/'build-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report),flush=True)


if __name__=='__main__': main()
