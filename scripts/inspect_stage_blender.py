"""Inspect the actual approved GLB in Blender, without altering approved sources."""
import argparse
import json
import sys
import time
from pathlib import Path
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--output-dir', type=Path, required=True)
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
args.output_dir.mkdir(parents=True, exist_ok=True)
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
start = time.perf_counter()
bpy.ops.import_scene.gltf(filepath=str(ROOT/'app/src/main/assets/v3/models/garden.glb'))
elapsed = time.perf_counter()-start
objects=[]
for ob in bpy.context.scene.objects:
    if ob.type != 'MESH': continue
    points=[ob.matrix_world@v.co for v in ob.data.vertices]
    lo=[min(p[i] for p in points) for i in range(3)]
    hi=[max(p[i] for p in points) for i in range(3)]
    objects.append(dict(name=ob.name, vertices=len(points), triangles=sum(len(p.vertices)-2 for p in ob.data.polygons),
                        minimum=lo, maximum=hi, materials=[m.name for m in ob.data.materials]))
report=dict(desktopBlenderImportSeconds=elapsed,scope='Host import includes Blender importer; not Android parse, native upload or GPU frame time',objects=objects)
(args.output_dir/'blender-baseline.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(dict(importSeconds=elapsed,wood=[o for o in objects if o['name'].startswith('CC0_')],water=[o for o in objects if o['name']=='pond_water'])),flush=True)
