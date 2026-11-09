"""Pose the approved rigs on sampled contacts for native visual review only."""
import argparse
import json
import sys
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--output-dir', required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
out = Path(args.output_dir)
out.mkdir(parents=True, exist_ok=True)
report = json.loads((ROOT/'assets-src/emerald-forest-v2/build-report.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True)
for anchor in report['anchors']:
    before = set(bpy.data.objects)
    source = ROOT/'assets-src/stage111-geometry'/(anchor['species']+'.glb')
    bpy.ops.import_scene.gltf(filepath=str(source))
    added = [o for o in bpy.data.objects if o not in before]
    rig = next(o for o in added if o.type == 'ARMATURE')
    rig.animation_data.action = None
    for track in rig.animation_data.nla_tracks:
        track.mute = 'idle' not in track.name
    bpy.context.scene.frame_set(5)
    bpy.context.view_layer.update()
    meshes = [o for o in added if o.type == 'MESH' and not o.hide_render and o.visible_get()]
    pts = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    low = Vector(tuple(min(v[i] for v in pts) for i in range(3)))
    high = Vector(tuple(max(v[i] for v in pts) for i in range(3)))
    factor = anchor['span']/max(high.x-low.x, high.y-low.y)
    centre = Vector(((high.x+low.x)/2, (high.y+low.y)/2, low.z))
    normal = Vector(anchor['normal'])
    q = Vector((0,0,1)).rotation_difference(normal)
    transform = (Matrix.Translation(Vector(anchor['point']) + normal*.004)
                 @ q.to_matrix().to_4x4() @ Matrix.Scale(factor,4) @ Matrix.Translation(-centre))
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for ob in meshes:
        evaluated = ob.evaluated_get(depsgraph)
        mesh = bpy.data.meshes.new_from_object(evaluated, depsgraph=depsgraph)
        posed = bpy.data.objects.new('review_'+anchor['species']+'_'+ob.name, mesh)
        bpy.context.collection.objects.link(posed)
        posed.matrix_world = transform @ ob.matrix_world
    for ob in added:
        bpy.data.objects.remove(ob, do_unlink=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.gltf(filepath=str(out/'insect-contact-review.glb'), export_format='GLB',
    use_selection=True, export_yup=True, export_animations=False, export_cameras=False, export_lights=False)
print('POSED_APPROVED_ASSETS', out/'insect-contact-review.glb')
