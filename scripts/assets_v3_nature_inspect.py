import argparse,json,sys
from pathlib import Path
import bpy
from mathutils import Vector
p=argparse.ArgumentParser();p.add_argument('--output-dir',required=True);out=Path(p.parse_args(sys.argv[sys.argv.index('--')+1:]).output_dir)
rows=[]
for name,res in [('dead_tree_trunk_02','2k'),('tree_stump_01','2k'),('moss_01','1k'),('dead_tree_trunk','2k')]:
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
 bpy.ops.import_scene.gltf(filepath=str(out/'sources'/name/f'{name}_{res}.gltf'))
 meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
 for o in meshes:
  co=[o.matrix_world@Vector(p) for p in o.bound_box]
  rows.append({'asset':name,'object':o.name,'dimensions':list(o.dimensions),'min':[min(v[i] for v in co) for i in range(3)],'max':[max(v[i] for v in co) for i in range(3)],'triangles':sum(len(p.vertices)-2 for p in o.data.polygons)})
print(json.dumps(rows,indent=2));(out/'sources-inspection.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
