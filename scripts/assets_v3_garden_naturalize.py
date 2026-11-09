"""Replace rejected procedural wood/moss with verified CC0 scanned source geometry."""
import argparse,json,math,random,sys
from pathlib import Path
import bpy
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree

p=argparse.ArgumentParser();p.add_argument('--output-dir',required=True);opts=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(opts.output_dir)
random.seed(2738)
bpy.ops.wm.open_mainfile(filepath=str(out/'garden.blend'))
for ob in list(bpy.context.scene.objects):
    if ob.type!='MESH':continue
    if any(m and m.name in ['bark','wood'] for m in ob.data.materials) or ob.name.startswith('detail_moss_'):
        bpy.data.objects.remove(ob,do_unlink=True)

def load(name,res):
    before=set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(out/'sources'/name/f'{name}_{res}.gltf'))
    return [o for o in bpy.data.objects if o not in before and o.type=='MESH']

log_source=load('dead_tree_trunk_02','2k')[0]
root_source=load('tree_stump_01','2k')[0]
moss_sources=load('moss_01','1k')
# The publisher glTF references a JPEG diffuse atlas despite alphaMode=BLEND.
# Restore the separate, hash-verified publisher alpha image before re-export.
moss_mat=moss_sources[0].data.materials[0]
alpha=moss_mat.node_tree.nodes.new('ShaderNodeTexImage')
alpha.image=bpy.data.images.load(str(out/'sources/moss_01/textures/moss_01_alpha_1k.png'))
alpha.image.colorspace_settings.name='Non-Color'
principled=next(n for n in moss_mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
moss_mat.node_tree.links.new(alpha.outputs['Color'],principled.inputs['Alpha'])

def oriented_log(name,start,end,thickness):
    mesh=log_source.data.copy();ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob)
    start,end=Vector(start),Vector(end);axis=end-start;q=Vector((1,0,0)).rotation_difference(axis.normalized())
    pts=[log_source.matrix_world@v.co for v in mesh.vertices]
    lo=[min(v[i] for v in pts) for i in range(3)];hi=[max(v[i] for v in pts) for i in range(3)]
    for v,co in zip(mesh.vertices,pts):
        t=(co.x-lo[0])/(hi[0]-lo[0])
        local=Vector((t*axis.length,(co.y-(hi[1]+lo[1])/2)*thickness,(co.z-(hi[2]+lo[2])/2)*thickness))
        v.co=start+q@local
    mesh.update()
    if mesh.has_custom_normals:mesh.normals_split_custom_set([(0.,0.,0.)]*len(mesh.loops))
    return ob

hero=load('dead_tree_trunk','2k')[0]
hero.name='CC0_hero_weathered_stump'
pts=[hero.matrix_world@v.co for v in hero.data.vertices]
lo=Vector(tuple(min(v[i] for v in pts) for i in range(3)));hi=Vector(tuple(max(v[i] for v in pts) for i in range(3)))
axis=Vector((-.05,.03,3.40));q=Vector((1,0,0)).rotation_difference(axis.normalized())
for vertex,point in zip(hero.data.vertices,pts):
    t=(point.x-lo.x)/(hi.x-lo.x)
    taper=1.0+.5*(1-t)**2
    yy=point.y-(lo.y+hi.y)/2;zz=point.z-(lo.z+hi.z)/2
    angle=math.atan2(zz,yy)
    tip=max(0,(t-.80)/.20)**2
    height=t*axis.length-.38*(.5+.5*math.sin(3*angle+.8))*tip
    local=Vector((height,yy*2.45*taper,zz*2.45*taper))
    vertex.co=Vector((1.05,1.95,-.10))+q@local
hero.matrix_world=Matrix.Identity(4);hero.data.update()
if hero.data.has_custom_normals:hero.data.normals_split_custom_set([(0.,0.,0.)]*len(hero.data.loops))
logs=[hero,
      oriented_log('CC0_foreground_fallen_log',(-2.95,-.65,1.18),(.7,-2.85,.15),.90),
      oriented_log('CC0_right_fallen_log',(3.9,-.25,1.16),(1.7,2.2,.05),.65)]
root_source.name='CC0_mossy_root_base';root_source.scale=(.98,.98,1.1);root_source.location=(1.05,1.95,-.14)
small=root_source.copy();small.data=root_source.data.copy();small.name='CC0_near_small_stump';bpy.context.collection.objects.link(small);small.location=(-1.2,2.75,-.12);small.scale=(.42,.42,1.25)
bpy.data.objects.remove(log_source,do_unlink=True)

prototypes=[]
for ob in moss_sources:
    # All imported variations are small original tufts. Keep geometry and UVs exactly.
    if not ob.name.endswith('LOD0'):continue
    mat=ob.data.materials[0]
    verts=[ob.matrix_world@v.co for v in ob.data.vertices]
    center=Vector(((min(v.x for v in verts)+max(v.x for v in verts))/2,(min(v.y for v in verts)+max(v.y for v in verts))/2,min(v.z for v in verts)))
    verts=[v-center for v in verts]
    polygons=[list(poly.vertices) for poly in ob.data.polygons]
    uvs=[tuple(x.uv) for x in ob.data.uv_layers.active.data]
    prototypes.append((verts,polygons,uvs,mat))

groups={}
for index,log in enumerate(logs[1:]):
    pts=[v.co for v in log.data.vertices];bbox=[(min(v[i] for v in pts),max(v[i] for v in pts)) for i in range(3)]
    tree=BVHTree.FromPolygons(pts,[list(p.vertices) for p in log.data.polygons])
    target=6500 if index==0 else 3600;placed=0
    for trial in range(target*8):
        if placed>=target:break
        x=random.uniform(*bbox[0]);y=random.uniform(*bbox[1])
        hit,normal,face,dist=tree.ray_cast(Vector((x,y,bbox[2][1]+1)),Vector((0,0,-1)))
        if hit is None or normal.z<.38:continue
        # Break cover into organic irregular patches rather than an even carpet.
        patch=.5+.22*math.sin(x*12+math.sin(y*17))+.21*math.sin(y*24+x*3)
        if random.random()>patch:continue
        vs,fs,uv,mat=random.choice(prototypes)
        dstv,dstf,dstu=groups.setdefault(mat.name,([],[],[]));off=len(dstv)
        q=Vector((0,0,1)).rotation_difference(normal)
        spin=Matrix.Rotation(random.random()*math.tau,4,'Z').to_quaternion()
        scale=random.uniform(.75,1.7)
        dstv.extend(tuple(hit+q@(spin@(v*scale))) for v in vs)
        dstf.extend(tuple(off+i for i in f) for f in fs);dstu.extend(uv);placed+=1
    print('Moss tufts on',log.name,placed,flush=True)
# Sparse living patches around the damp base of the upright wood.
verts=[v.co for v in hero.data.vertices]
tree=BVHTree.FromPolygons(verts,[list(p.vertices) for p in hero.data.polygons])
for trial in range(5000):
    x=random.uniform(.55,1.52);z=random.uniform(.10,1.64)
    hit,normal,_,_=tree.ray_cast(Vector((x,-1,z)),Vector((0,1,0)))
    if hit is None or random.random()>.28*(1-z/2):continue
    vs,fs,uv,mat=random.choice(prototypes)
    dstv,dstf,dstu=groups.setdefault(mat.name,([],[],[]));off=len(dstv)
    q=Vector((0,0,1)).rotation_difference(normal)
    spin=Matrix.Rotation(random.random()*math.tau,4,'Z').to_quaternion()
    scale=random.uniform(.9,1.5)
    dstv.extend(tuple(hit+q@(spin@(v*scale))) for v in vs)
    dstf.extend(tuple(off+i for i in f) for f in fs);dstu.extend(uv)
for name,(vs,fs,uv) in groups.items():
    mesh=bpy.data.meshes.new('CC0_moss_patch');mesh.from_pydata(vs,[],fs);mesh.update()
    ob=bpy.data.objects.new('CC0_moss_on_branches',mesh);bpy.context.collection.objects.link(ob);mesh.materials.append(bpy.data.materials[name])
    layer=mesh.uv_layers.new(name='UVMap')
    assert len(uv)==len(layer.data)
    for loop,tex in zip(layer.data,uv):loop.uv=tex
for ob in moss_sources:bpy.data.objects.remove(ob,do_unlink=True)

for img in bpy.data.images:
    if img.type=='IMAGE' and img.source=='FILE':
        try:img.pack()
        except RuntimeError:pass
sc=bpy.context.scene
# A modest raking edge emphasizes the scanned bark without flattening its color.
if bpy.data.objects.get('trunk_raking'):bpy.data.objects['trunk_raking'].data.energy=155
if bpy.data.objects.get('trunk_raking'):bpy.data.objects['trunk_raking'].data.color=(1,.78,.53)
if bpy.data.objects.get('warm_near_leaf'):
    key=bpy.data.objects['warm_near_leaf'];key.data.energy=320;key.location=(-3.7,.7,3.3)
    key.rotation_euler=(Vector((-1.4,.1,1.3))-key.location).to_track_quat('-Z','Y').to_euler()
if bpy.data.objects.get('moon_rim'):bpy.data.objects['moon_rim'].data.energy=650
if bpy.data.objects.get('cool_front'):bpy.data.objects['cool_front'].data.energy=95
if bpy.data.objects.get('soft_blue_water'):bpy.data.objects['soft_blue_water'].data.energy=120
if bpy.data.objects.get('warm_moss_edge'):
    edge=bpy.data.objects['warm_moss_edge'];edge.data.energy=320;edge.location=(-3.5,.3,2.0)
    edge.rotation_euler=(Vector((-1,-1.8,.4))-edge.location).to_track_quat('-Z','Y').to_euler()
leaf_mat=bpy.data.materials.get('lotus_leaf')
if leaf_mat:
    leaf_mat.node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value=.08
    for link in list(leaf_mat.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].links):leaf_mat.node_tree.links.remove(link)
    leaf_mat.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value=.58
# Keep the nearby surfaces clear, reserving haze for the distant reed layers.
if bpy.data.objects.get('PREVIEW_atmosphere'):
    haze=bpy.data.objects['PREVIEW_atmosphere'];haze.location.y=13;haze.scale.y=18
sc.camera.data.dof.use_dof=True
sc.camera.data.dof.focus_distance=5.2
sc.camera.data.dof.aperture_fstop=1.6
bpy.ops.object.select_all(action='DESELECT')
obs=[o for o in sc.objects if o.type=='MESH' and not o.name.startswith('PREVIEW_')]
for ob in obs:ob.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(out/'garden.glb'),export_format='GLB',use_selection=True,export_yup=True,export_cameras=False,export_lights=False,export_animations=False)
report={'revision':'scanned wood and true moss tuft geometry','sourceAssets':['dead_tree_trunk','dead_tree_trunk_02','tree_stump_01','moss_01'],'sourceLicense':'CC0','meshCount':len(obs),'triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in obs),'vertices':sum(len(o.data.vertices) for o in obs),'glbBytes':(out/'garden.glb').stat().st_size,'reviewStatus':'requires actual render comparison','previewOnly':['world environment','area lighting','volumetric atmosphere','compositor glow']}
(out/'garden-report.json').write_text(json.dumps(report,indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(out/'garden-naturalized.blend'))
print(json.dumps(report,indent=2))
