"""Import the actual GLB into the authored review lighting; render and record checks."""
import argparse
import hashlib
import json
import sys
from pathlib import Path
import bpy
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

args=sys.argv[sys.argv.index('--')+1:]
p=argparse.ArgumentParser();p.add_argument('--output-dir',required=True);opts=p.parse_args(args)
out=Path(opts.output_dir)
source=out/'garden-naturalized.blend'
if not source.exists():source=out/'garden.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
for ob in list(bpy.data.objects):
    if ob.type=='MESH' and not ob.name.startswith('PREVIEW_'):
        bpy.data.objects.remove(ob,do_unlink=True)
bpy.ops.import_scene.gltf(filepath=str(out/'garden.glb'))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH' and not o.name.startswith('PREVIEW_')]
missing_uv=[o.name for o in meshes if not o.data.uv_layers]
missing_mat=[o.name for o in meshes if not o.data.materials]
images=sorted({n.image for ob in meshes for mat in ob.data.materials if mat and mat.node_tree
               for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image},key=lambda i:i.name)
report={'sourceGlbSha256':hashlib.sha256((out/'garden.glb').read_bytes()).hexdigest(),
        'meshes':len(meshes),'vertices':sum(len(o.data.vertices) for o in meshes),
        'triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in meshes),
        'missingUV':missing_uv,'missingMaterials':missing_mat,
        'embeddedImages':[{'name':i.name,'size':list(i.size)} for i in images if i.packed_file],
        'scope':'GLB import and render under matching Blender review lighting; not PICO runtime'}
assert not missing_mat,missing_mat
# Firefly icospheres do not use image textures; other meshes require UVs.
assert all(name.startswith('firefly') for name in missing_uv),missing_uv
(out/'roundtrip-report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
prefs=bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type='OPTIX';prefs.get_devices()
for device in prefs.devices:device.use=device.type=='OPTIX'
sc=bpy.context.scene;sc.cycles.device='GPU';sc.render.filepath=str(out/'garden-roundtrip.png');sc.cycles.samples=64
bpy.ops.wm.save_as_mainfile(filepath=str(out/'garden-roundtrip.blend'))
bpy.ops.render.render(write_still=True)
print(json.dumps(report,indent=2))

# A separate, explicitly labelled composition preview uses the actual reviewed
# insect GLBs. These preview actors are never written into garden.glb.
wood=next(o for o in meshes if o.name.startswith('CC0_foreground_fallen_log'))
tree=BVHTree.FromPolygons([wood.matrix_world@v.co for v in wood.data.vertices],
                         [list(p.vertices) for p in wood.data.polygons])
composition=[]
for species,xy,width,spin in [('butterfly',(-1.62,-1.40),.54,-.20),
                              ('ladybug',(-.53,-2.03),.33,-.65)]:
    hit,normal,_,_=tree.ray_cast(Vector((*xy,3)),Vector((0,0,-1)))
    assert hit is not None,(species,xy)
    before=set(bpy.data.objects)
    asset=out.parent/species/(species+'.glb')
    bpy.ops.import_scene.gltf(filepath=str(asset))
    owned=set(bpy.data.objects)-before
    actual=[]
    for ob in owned:
        if ob.type=='ARMATURE':
            ob.animation_data_clear()
            for bone in ob.pose.bones:bone.matrix_basis=Matrix.Identity(4)
            clip='idle' if species=='ladybug' else 'butterfly_idle_perch'
            action=next(a for a in bpy.data.actions if a.name==clip)
            ob.animation_data_create();ob.animation_data.action=action
            if action.slots:ob.animation_data.action_slot=action.slots[0]
        if ob.type=='MESH':
            if not ob.vertex_groups:ob.hide_render=True
            else:actual.append(ob)
    sc.frame_set(1);bpy.context.view_layer.update()
    pts=[ob.matrix_world@Vector(corner) for ob in actual for corner in ob.bound_box]
    lo=Vector(tuple(min(v[i] for v in pts) for i in range(3)))
    hi=Vector(tuple(max(v[i] for v in pts) for i in range(3)))
    scale=width/max(hi.x-lo.x,hi.y-lo.y)
    pivot=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
    orient=Vector((0,0,1)).rotation_difference(normal)
    orient=orient@Matrix.Rotation(spin,4,'Z').to_quaternion()
    parent=bpy.data.objects.new('PREVIEW_INSECT_'+species,None);bpy.context.collection.objects.link(parent)
    for ob in owned:
        if ob.parent not in owned:ob.parent=parent
    parent.scale=(scale,)*3;parent.rotation_mode='QUATERNION';parent.rotation_quaternion=orient
    parent.location=hit+normal*.002-orient@(pivot*scale)
    composition.append({'species':species,'glbSha256':hashlib.sha256(asset.read_bytes()).hexdigest(),
                        'scale':scale,'location':list(parent.location),'rotation':list(orient)})
sc.render.filepath=str(out/'garden-populated.png')
bpy.ops.render.render(write_still=True)
(out/'composition-preview.json').write_text(json.dumps({'scope':'real asset assembly preview; no application logic; insects excluded from environment GLB','actors':composition},indent=2),encoding='utf8')
